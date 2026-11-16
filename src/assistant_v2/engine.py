"""The conversation engine: one call per user turn.

Per turn:
 1. check_input      - reject empty / gibberish / other printers (fixed rules)
 2. understand       - intent, facts, measurements (model + rules; button answers skip the model, so they are instant)
 3. update the case  - the "case file": everything known so far
 4. calculations     - engineering.run on the measurements + engineering.context (what changes at that moment)
 5. base scores      - card search + failure graph + error messages + calculations + the part the technician names
 6. probabilities    - reasoner.posterior: base scores x likelihood of every answer given
 7. next step        - reasoner.next_step: ask the ONE question with the highest information gain per effort,
                       or name the cause as soon as one part is clearly most likely
This version names the cause only. It does not give repair steps.
"""
import json, os, re, sys, time, pathlib, uuid
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tools import card_text, compact_text, IDX                     # noqa: E402
from retrieval import HybridIndex                                    # noqa: E402
from graph_rag import FailureGraph                                   # noqa: E402
from . import engineering as eng
from .questions import Q, EVIDENCE, TEXT_EVIDENCE
from . import reasoner as R
from .extra_parts import EXTRA, EDGES
from . import knowledge as K
from .understand import check_input, understand, validate_measurements
from .llm import ask_json, STUB, LLM_MODEL

A = pathlib.Path(__file__).resolve().parents[2]
KG = json.loads((A / "data/kg/kg.json").read_text(encoding="utf-8"))
KG.update(EXTRA)          # 28 evaluation parts + 3 power parts used only by the assistant
NAME = {k: v["name"] for k, v in KG.items()}
MAX_ROUNDS = R.MAX_TURNS
_index = _graph = None

def _load():
    global _index, _graph
    if _index is None:
        # own index name ("V2"), so the cached embeddings of the evaluation arms are never touched
        _index = HybridIndex("V2", [{"id": k, "text": card_text(v)} for k, v in KG.items()], IDX)
        _graph = FailureGraph()
        for c in EXTRA: _graph.nodes[c] = {"id": c, "name": NAME[c]}; _graph.out.setdefault(c, []); _graph.inc.setdefault(c, [])
        for s_, d_, rel in EDGES:
            e = {"src": s_, "dst": d_, "rel": rel}; _graph.edges.append(e); _graph.out[s_].append(e); _graph.inc[d_].append(e)
        _graph.reach = {n: _graph._down(n) for n in _graph.nodes}
        R.WIDE = expand_evidence(EVIDENCE, _graph)

# A fault travels from cause to effect along the graph: if an answer is expected when part d is faulty, it is
# also expected when a part that powers / feeds / carries d is faulty. So every answer -> parts list is widened by
# one step upstream. Settings edges (configures, commands, triggers) are not used: they do not carry a fault.
SIGNAL_RELS = {"powers", "feeds", "carries_power_to", "carries_signal_of", "drives", "reads_signal_of", "in_series_with", "turns",
               "moves", "guides", "carries", "feeds_filament_to", "heats", "cools", "controls"}
def expand_evidence(ev, g):
    out = {}
    for key, ids in ev.items():
        wide = []
        for d in ids:
            for e in g.inc.get(d, []):
                if e["rel"] in SIGNAL_RELS and e["src"] not in ids and e["src"] not in wide and e["src"] not in SETTINGS: wide.append(e["src"])
        out[key] = wide
    return out

def new_case():
    return {"id": uuid.uuid4().hex[:8], "notes": [], "facts": {}, "measurements": {}, "asked_ids": [], "pending": [],
            "dont_know": [], "rounds": 0, "status": "gathering", "hyps": [], "calcs": [], "log": []}

# ------------------------------------------------------------------------------------------------------
def case_text(case):
    parts = list(case["notes"])
    parts += [f"{k.replace('_', ' ')}: {v}" for k, v in case["facts"].items() if k != "what_happens"]
    return " ".join(parts)

# words a technician uses for a part -> component ids (used to start from the part they name)
ALIASES = [
 (("power cord", "power cable", "mains", "plug", "socket", "inlet", "extension lead", "power strip"), ["mains_power_input"]),
 (("crimp", "24v wire", "24 v wire", "power wire"), ["dc_power_wiring"]), (("thermal fuse", "fuse"), ["bed_thermal_fuse"]),
 (("nozzle",), ["nozzle"]), (("hotend", "hot end"), ["nozzle", "hotend_heater", "hotend_thermistor"]),
 (("heater cartridge", "heater block", "cartridge"), ["hotend_heater"]), (("thermistor",), ["hotend_thermistor"]),
 (("heatbreak", "ptfe", "bowden"), ["heatbreak_ptfe"]), (("extruder", "extrusion", "extrudes", "extruding"), ["extruder_motor", "extruder_gears_guidler"]),
 (("drive gear", "gears", "guidler", "idler arm"), ["extruder_gears_guidler"]), (("hotend fan", "heatsink fan"), ["hotend_fan"]),
 (("part fan", "part cooling", "blower"), ["part_cooling_fan"]), ((" fan ", " fans "), ["hotend_fan", "part_cooling_fan"]), (("belt",), ["xy_belts"]), (("pulley", "idler"), ["xy_pulleys_idlers"]),
 (("x rail", "x axis", "x-axis"), ["x_linear_rail"]), (("y rail", "y axis", "y-axis"), ["y_linear_rails"]), (("toolhead", "print head"), ["toolhead"]),
 (("z axis", "z-axis", "lead screw", "leadscrew", "z motor"), ["z_motor_leadscrew"]), (("z rail",), ["z_rails"]), (("endstop", "homing"), ["z_endstop"]),
 (("bed heater", "heated bed", "bed not heat", "bed does not heat", "bed won't heat"), ["bed_heater"]), (("bed thermistor",), ["bed_thermistor"]),
 (("bed", "build plate"), ["bed_plate_carrier"]), (("board", "skr", "pico", "mcu"), ["controller_board"]), (("umbilical", "cable", "wire"), ["umbilical_wiring"]),
 (("power supply", "psu"), ["power_supply"]), (("raspberry", " pi ", "mainsail", "fluidd"), ["host_computer"]), (("runout",), ["filament_runout_sensor"]),
 (("config", "macro", "klipper"), ["firmware_config_macros"]), (("slicer", "gcode"), ["slicer_settings"]), (("filament", "pla", "petg", "abs"), ["filament_material"]),
]
SETTINGS = {"firmware_config_macros", "slicer_settings"}

KB_SYS = """You are a senior mechanical and electrical engineer who knows the Voron 0.2 3D printer from its design documents,
given in full below. A technician describes a fault. Using the part cards, the failure graph (how a fault travels from part
to part), the design values and engineering physics, list the parts that could cause it, most likely first. Think about
shared upstream causes (one part that explains several symptoms). Use only component ids from the cards. Do not give repair
steps. Return JSON only: {"candidates": [{"id": "<component id>", "p": <0..1>, "why": "<one short physical reason>"}]}
with 3 to 6 candidates whose p values add up to about 1."""
_kb_cache = {}
FT_MODEL = os.environ.get("FT_MODEL", "")   # name of the fine-tuned model in Ollama, e.g. voron-qwen
_ft_cache = {}
def ft_reading(text):
    """Role 'reading' of the fine-tuned model (same prompt format as its training data)."""
    if not FT_MODEL or STUB or not text.strip(): return []
    if text not in _ft_cache:
        try:
            from finetune.fmt import SYSTEM_READ, read_context
            from .llm import ask_local
            r = ask_local(FT_MODEL, SYSTEM_READ, read_context(text, _search(text, 8), KG, compact_text)) or {}
            _ft_cache[text] = [{"id": c["id"], "p": float(c.get("p", 0.3)), "why": str(c.get("why", ""))[:160]}
                               for c in (r.get("candidates") or []) if isinstance(c, dict) and c.get("id") in KG][:6]
        except Exception as e:
            print("fine-tuned reading skipped:", e); _ft_cache[text] = []
    return _ft_cache[text]
def kb_reading(text):
    """Full-knowledge reading of the description (cached per description): [{id, p, why}] or [] when the mode is off."""
    kb = K.knowledge(KG, _graph) if not STUB else ""
    if not kb or not text.strip(): return []
    if text not in _kb_cache:
        try:
            r = ask_json(KB_SYS + "\n\n" + kb, f"Technician's description: \"{text}\"", max_tokens=600) or {}
            out = []
            for c in r.get("candidates") or []:
                if isinstance(c, dict) and c.get("id") in KG and c["id"] not in [o["id"] for o in out]:
                    try: p = max(0.0, min(1.0, float(c.get("p", 0))))
                    except (TypeError, ValueError): p = 0.0
                    out.append({"id": c["id"], "p": p, "why": str(c.get("why") or "")[:160]})
            _kb_cache[text] = out[:6]
        except Exception as e:
            print("full-knowledge reading skipped:", e); _kb_cache[text] = []
    return _kb_cache[text]

_agent_cache, _toolbox = {}, None
def agent_top3(text):
    """Run the evaluated agent (arm G) once per description; cached, so answers to questions do not re-run it."""
    global _toolbox
    if not text.strip() or USE_AGENT_PRIOR is False: return []
    if text not in _agent_cache:
        try:
            from agent import diagnose as agent_diagnose
            from tools import Toolbox
            if _toolbox is None: _toolbox = Toolbox("G")
            r = agent_diagnose(text, "G", _toolbox, lambda q: "The technician has not answered yet.")
            _agent_cache[text] = [c["component_id"] for c in r["candidates"]][:3]
        except Exception as e:
            print("graph agent not available:", e); _agent_cache[text] = []
    return _agent_cache[text]

import os
USE_AGENT_PRIOR = os.environ.get("AGENT_PRIOR", "1") != "0"
SELF_CHECK = os.environ.get("SELF_CHECK", "1") != "0"   # second opinion + verifier before naming a cause
_cache = {}
def _search(text, k=6):
    """Card search with a cache: the embedding call to Ollama is only made when the technician's words change."""
    if text not in _cache: _cache[text] = [d["id"] for d in _index.search(text, k, SEARCH_MODE)]
    return _cache[text]

KLIPPER_NAMES = [(re.compile(r"heater[ _]heater_bed|heater_bed"), " "), (re.compile(r"heater[ _]extruder|extruder not heating"), " not heating "),
                 (re.compile(r"mcu ['\"]?\w+['\"]?"), " mcu ")]
# Klipper's error names a heater CIRCUIT, not a part the technician pointed at: every part of that circuit gets a small share
KLIPPER_CIRCUITS = [(re.compile(r"heater[ _]heater_bed|heater_bed"), ["bed_heater", "bed_thermal_fuse", "bed_thermistor"]),
                    (re.compile(r"heater[ _]extruder|extruder not heating"), ["hotend_heater", "hotend_thermistor", "umbilical_wiring"])]

def mentioned(text):
    low = text.lower()
    for rx, rep in KLIPPER_NAMES: low = rx.sub(rep, low)     # Klipper's names: 'Heater extruder' is the hotend heater, not the extruder
    low = " " + low + " "; out = []
    for words, ids in ALIASES:
        if any(w in low for w in words):
            for i in ids:
                if i not in out: out.append(i)
    return out

def neighbours_up(cid):
    """Parts whose fault can show up at cid (one step upstream in the failure graph, without the settings hubs)."""
    _load(); return [e["src"] for e in _graph.inc[cid] if e["src"] not in SETTINGS]

SEARCH_W = float(os.environ.get("SEARCH_W", "1.0"))
SEARCH_MODE = os.environ.get("SEARCH_MODE", "bm25")    # "bm25": card search on words only (same result offline and on the laptop)

def hypotheses(case, calcs):
    """Score every component from all evidence; return the ranked list with the reasons."""
    _load(); text = case_text(case); score, why = {}, {}
    def add(c, s, reason):
        if c not in KG: return
        score[c] = score.get(c, 0) + s; why.setdefault(c, []).append(reason)
    # the tested graph agent (arm G, best top-3 in the evaluation) reads the technician's words once and proposes
    # its top 3; this is the starting belief, and the questions then confirm or change it
    ids, _ = part_prior(case["facts"].get("which_part", ""))
    for c in ids or []: add(c, 3.5, f"the part you pointed to: {case['facts']['which_part']}")
    kbr = ft_reading(" ".join(case["notes"])) or kb_reading(" ".join(case["notes"]))
    if kbr:   # full-knowledge mode: the model read every card and the whole graph
        for r in kbr: add(r["id"], 3.0 * r["p"] + 0.3, f"model reading all part cards: {r['why']}" if r.get("why") else "model reading all part cards")
    else:
        for i, c in enumerate(agent_top3(" ".join(case["notes"]))):
            add(c, (2.0, 1.4, 1.0)[i], f"graph agent's reading of your description (rank {i + 1})")
    for rx, ids in KLIPPER_CIRCUITS:
        if rx.search(" ".join(case["notes"]).lower()):
            for c in ids: add(c, 0.6, "on the heater circuit named in Klipper's error")
    for i, c in enumerate(mentioned(" ".join(case["notes"]))[:4]):   # the part the technician names, and what feeds/heats/drives it
        add(c, 1.2 - 0.1 * i, "the part you mentioned")
        for u in neighbours_up(c): add(u, 0.6, f"connected upstream of {NAME[c]} ({_graph.path(u, c)})")
    if text.strip():
        seeds = _search(" ".join(case["notes"]) or text)
        for i, s in enumerate(seeds): add(s, SEARCH_W / (i + 1), "matches the description")
        for u in _graph.upstream(seeds[:5])[:3]:
            add(u["id"], SEARCH_W * min(0.8, 2 * u["score"]), "upstream in the failure graph of " + ", ".join(NAME[e] for e in u["explains"][:3]))
    for h in eng.error_hits(case["facts"].get("error_message", "") + " " + text):
        for i, c in enumerate(h["points_to"]): add(c, 1.2 - 0.2 * i, f"error message '{h['pattern']}' ({h['source']})")
    for (slot, opt), ids in EVIDENCE.items():          # only the reason text; the weight comes from reasoner.posterior
        if case["facts"].get(slot) == opt:
            for c in ids: why.setdefault(c, []).append(f"your answer: {opt}"); score.setdefault(c, 0.0)
    low = text.lower()
    for words, ids in TEXT_EVIDENCE:
        hit = next((w for w in words if re.search(r"(?<!no )(?<!not )(?<!without )" + re.escape(w), low)), None)   # "no popping" is not popping
        if hit:
            for c in ids: add(c, 0.6, "described: " + hit)
    for k in calcs:
        # "info" checks explain the timing; the same fact is already counted through the answer it comes from,
        # so they get no weight here (counting it twice would make the assistant overconfident)
        w = {"fault": 2.0, "warn": 0.8}.get(k["verdict"], 0)
        for i, c in enumerate(k["points_to"]): add(c, w * (1 - 0.15 * i), f"calculation: {k['title']} = {k['result']}")
        if k["verdict"] == "ok":   # a passing check is evidence AGAINST the parts it tests
            for c in {"heater_r": ["hotend_heater"], "bed_r": ["bed_heater"], "hotend_thermistor_ohm": ["hotend_thermistor"],
                      "bed_thermistor_ohm": ["bed_thermistor"], "e_len": ["extruder_gears_guidler", "nozzle"], "psu": ["power_supply"],
                      "belt_A": ["xy_belts"], "belt_B": ["xy_belts"], "fanv": ["umbilical_wiring", "controller_board"]}.get(k["id"], []):
                if c in score: score[c] -= 0.8; why.setdefault(c, []).append(f"less likely: {k['title']} is OK")
    return score, why

def ranked_hyps(P, why, n=8):
    ranked = sorted(P, key=lambda c: -P[c])
    return [{"id": c, "name": NAME[c], "p": round(P[c], 3), "score": round(P[c], 3), "why": why.get(c, [])[:5]} for c in ranked[:n]]

def evidence_count(case):
    """Discriminating information: non-generic facts, measurements, error messages."""
    generic = {"what_happens", "onset", "recent_change", "other_load"}
    n = sum(1 for k, v in case["facts"].items() if k not in generic and v and v.lower() not in ("none", "nothing", "no"))
    return n + len(case["measurements"])

def is_vague(case):
    words = len(" ".join(case["notes"]).split())
    return evidence_count(case) == 0 and words < 15

# ------------------------------------------------------------------------------------------------------
DECIDE_SYS = """You are a senior mechanical and electrical engineer diagnosing a Voron 0.2 3D printer for a technician.
You reason like an engineer: from the system structure (which part feeds, drives, powers or cools which), physics, and the
exact calculations given to you. You never guess from one vague sentence; you ask for the specific observations or
measurements that separate the possible causes. Use only the evidence given. Return JSON only."""

DIAG_SYS = DECIDE_SYS + """
Now name the most likely faulty component. Explain the cause as a chain of physical cause and effect
(what failed -> what that does -> what the technician observes), cite the calculations and facts that support it,
and say why the next alternatives are less likely. Do NOT give repair steps. Use only component ids from the list."""

def short(name):
    """Drop only a trailing '( ... )' part: 'Hotend (heatsink) fan' stays whole, 'Nozzle (x)' -> 'Nozzle'."""
    return re.sub(r" \([^)]*\)$", "", name)

def readable(path):
    """'power_supply --powers--> host_computer' -> 'Power supply (powers) → Host computer'"""
    parts = re.split(r" --([a-z_]+)--> ", path); out = short(NAME.get(parts[0], parts[0]))
    for i in range(1, len(parts) - 1, 2):
        out += f" ({parts[i].replace('_', ' ')}) → " + NAME.get(parts[i + 1], parts[i + 1]).split(" (")[0]
    return out

def diagnose_fast(case, hyps, calcs):
    """Instant answer from the probabilities, evidence and calculations (no language model)."""
    if not hyps: return None
    h = hyps[0]; p = h["p"]
    conf = "high" if p >= 0.8 else ("medium" if p >= 0.5 else "low")
    ev = [w.replace("graph agent's reading of your description", "your description, read against the parts graph")
          for w in h["why"] if not w.startswith("matches the description")][:4]
    ev += [f"{k['title']}: {k['result']} ({k['meaning']})" for k in calcs if h["id"] in k["points_to"] and k["verdict"] in ("fault", "warn", "info")][:2]
    path = next((_graph.path(h["id"], s) for s in _search(" ".join(case["notes"]))[:3] if s != h["id"] and _graph.path(h["id"], s)), "")
    chain = f"{h['name']} is the most likely cause ({p:.0%})." + (f" A fault there can travel along: {readable(path)}." if path else "")
    return {"cause": h["id"], "confidence": conf, "chain": chain, "evidence": ev or h["why"][:3],
            "alternatives": [{"id": x["id"], "why_less": "; ".join(x["why"][:2]) or "less supported by your answers"} for x in hyps[1:3] if x["p"] >= 0.03],
            "ruled_out": [], "missing": "", "explained": False}

EXPLAIN_SYS = """You are a senior mechanical and electrical engineer. The diagnosis below was found by the system from the
technician's answers, the failure graph and exact calculations. Explain it in simple English. Do NOT change the cause and
do NOT give repair steps. Return JSON only."""

def explain(case):
    """Model-written explanation of the cause the system already chose (called by the page after the fast answer)."""
    if STUB or not case.get("hyps"): return {}
    hyps = case["hyps"]; cause = hyps[0]["id"]; others = [h["id"] for h in hyps[1:4]]
    cards = "\n---\n".join(compact_text(KG[i]) for i in [cause] + others)
    paths = [p for j in others + _search(" ".join(case["notes"]))[:3] for p in [_graph.path(cause, j)] if p and j != cause and p.count("-->") <= 2]
    calc_txt = "\n".join(f"- {k['title']}: {k['result']} => {k['verdict'].upper()}: {k['meaning']}" for k in case.get("calcs", [])) or "- none"
    user = f"""Technician's words: {" | ".join(case["notes"])}
Answers: {json.dumps(case["facts"])}
Measurements: {json.dumps(case["measurements"])}
Calculations:
{calc_txt}
Failure paths from the cause: {"; ".join(paths[:4]) or "-"}
CAUSE: {cause} ({hyps[0]["p"]:.0%})   OTHER CANDIDATES: {", ".join(f"{h['id']} ({h['p']:.0%})" for h in hyps[1:4])}
Cards:
{cards}
Return JSON: {{"chain": "what failed -> what that does -> what the technician sees (2-3 sentences)",
 "evidence": ["up to 4 short points from the answers/calculations"],
 "alternatives": [{{"id": "<one of the other candidates>", "why_less": "one short reason"}}],
 "missing": "one observation that would make it certain (no repair steps)"}}"""
    kb = K.knowledge(KG, _graph)
    r = ask_json(EXPLAIN_SYS + ("\n\n" + kb if kb else ""), user, max_tokens=450) or {}
    out = {"chain": str(r.get("chain") or ""), "evidence": [str(e) for e in (r.get("evidence") or [])][:4], "missing": str(r.get("missing") or "")}
    alts = [a for a in (r.get("alternatives") or []) if isinstance(a, dict) and a.get("id") in KG and a["id"] != cause][:2]
    for a in alts: a["name"] = NAME[a["id"]]; a["p"] = next((h["p"] for h in hyps if h["id"] == a["id"]), 0)
    if alts: out["alternatives"] = alts
    return out

def diagnose(case, hyps, calcs):
    if STUB or not hyps:
        if not hyps: return None
        h = hyps[0]
        return {"cause": h["id"], "confidence": "medium", "chain": f"{h['name']} — " + "; ".join(h["why"][:3]),
                "evidence": h["why"][:4], "alternatives": [{"id": x["id"], "why_less": "; ".join(x["why"][:2])} for x in hyps[1:3]],
                "ruled_out": [], "missing": ""}
    ids = [h["id"] for h in hyps[:6]]
    cards = "\n---\n".join(card_text(KG[i]) for i in ids)
    paths = []
    for i in ids[:3]:
        for j in ids[:6]:
            p = _graph.path(i, j) if i != j else ""
            if p and p.count("-->") <= 2: paths.append(p)
    calc_txt = "\n".join(f"- {k['title']}: {k['formula']} -> {k['result']} (expected {k['expected']}) => {k['verdict'].upper()}: {k['meaning']} [source: {k['source']}]" for k in calcs) or "- none"
    user = f"""Technician's words: {" | ".join(case["notes"])}
Facts: {json.dumps(case["facts"])}
Measurements: {json.dumps(case["measurements"])}
Could not answer: {", ".join(case["dont_know"]) or "none"}
CALCULATIONS
{calc_txt}
HOW THE PARTS CONNECT (failure graph: a fault in the left part can show up at the right part)
{chr(10).join(paths[:12]) or "-"}
CANDIDATE COMPONENTS (with design values and failure modes)
{cards}
Return JSON: {{"cause": "<id>", "confidence": "high|medium|low",
 "chain": "cause -> effect -> what is observed, 2-3 sentences",
 "evidence": ["fact or calculation that supports it", "..."],
 "alternatives": [{{"id": "<id>", "why_less": "..."}}],
 "ruled_out": [{{"id": "<id>", "because": "..."}}],
 "missing": "what single extra observation would make this certain (one sentence, no repair steps)"}}"""
    r = ask_json(DIAG_SYS, user) or {}
    if r.get("cause") not in KG: r["cause"] = ids[0]
    r["alternatives"] = [a for a in (r.get("alternatives") or []) if isinstance(a, dict) and a.get("id") in KG and a["id"] != r["cause"]][:3]
    r["ruled_out"] = [a for a in (r.get("ruled_out") or []) if isinstance(a, dict) and a.get("id") in KG][:4]
    r["evidence"] = [str(e) for e in (r.get("evidence") or [])][:6]
    if r.get("confidence") not in ("high", "medium", "low"): r["confidence"] = "medium"
    return r

INFO_SYS = """You answer short factual questions about the Voron 0.2 3D printer using ONLY the component cards given.
Cite the source in brackets. If the cards do not contain the answer, say so. 1-3 sentences. Return JSON {"answer": "..."}"""

def info_answer(text):
    _load(); docs = _index.search(text, 3)
    if STUB: return "From the design documents: " + docs[0]["text"].split("\n")[0]
    r = ask_json(INFO_SYS, "Cards:\n" + "\n---\n".join(d["text"] for d in docs) + f"\nQuestion: {text}") or {}
    return r.get("answer") or "I could not find that in the Voron 0.2 documents."

# ------------------------------------------------------------------------------------------------------
INTRO = ("I'm a diagnostic assistant for the **Voron 0.2**. Tell me what the printer is doing and I'll work out which part is at fault.\n\n"
         "A good description says **what** you see, **when** it happens, and **what changed** before. Numbers help a lot "
         "(temperatures, resistances, voltages, lengths). For example:\n\n"
         "> The hotend heats to 215 °C, but during printing the temperature suddenly drops to 150 °C and comes back. "
         "It only happens when the head moves. No error message. I re-routed the toolhead cable last week.")
OFF_TOPIC = ("I can only help with the **Voron 0.2 3D printer**: finding which part causes a fault. "
             "Please describe a problem you see on your Voron 0.2, for example what it does, when it happens, and any error message.")

# ---- scope and "which part?" clarification (asked before any diagnosis) -----------------------------------
VORON_WORDS = re.compile(r"\b(voron|v0\.?2?|klipper|mainsail|fluidd|moonraker|hot ?end|extrud\w*|nozzle|toolhead|tool head|gantry|heatbreak|"
                         r"ptfe|bowden|filament|thermistor|skr|pico|umbilical|picobilical|bed|build plate|layers?|print(ing|ed|s)?|"
                         r"spool|z.?endstop|leadscrew|lead screw|belts?|pulley|idler|slicer|gcode|pla|petg|abs|asa)\b", re.I)
MACHINE_Q = {"id": "machine", "kind": "choice", "slot": "machine", "text": "Is this about your Voron 0.2 3D printer?",
             "options": ["Yes, my Voron 0.2 3D printer", "No, another machine or device"]}
# words that can mean more than one part: option -> parts it means (None = a part the Voron 0.2 documents do not cover)
AMBIGUOUS = [
 (r"\bfans?\b", r"(hot ?end|heatsink|part|cooling|blower|bay|controller|psu) fans?", "Which fan do you mean?", [("Hotend (heatsink) fan, on the print head", ["hotend_fan"]),
     ("Part cooling fan / blower, blows on the print", ["part_cooling_fan"]),
     ("A fan in the electronics bay (board or power supply)", ["controller_board", "power_supply"]),
     ("All fans at once", ["umbilical_wiring", "controller_board", "power_supply", "mains_power_input"])]),
 (r"\b(lights?|leds?|lamp|display|screen)\b", r"(psu|power supply|board|pi) (led|light)", "Which light do you mean?", [("The green LED on the power supply", ["power_supply", "mains_power_input"]),
     ("LEDs on the controller board or the Raspberry Pi", ["controller_board", "host_computer", "dc_power_wiring"]),
     ("Case / LED-strip lighting or a display (an add-on)", None), ("All lights went off together", ["mains_power_input", "power_supply"])]),
 (r"\bmotors?\b", r"(extru\w*|z|x|y|xy|a|b) motors?|motors? (x|y|z)", "Which motor do you mean?", [("X/Y motors (move the print head)", ["xy_motors_drivers"]),
     ("Z motor (moves the bed up and down)", ["z_motor_leadscrew"]), ("Extruder motor (pushes the filament)", ["extruder_motor"]),
     ("All motors at once", ["controller_board", "dc_power_wiring", "power_supply"])]),
 (r"\b(not heat\w*|won'?t heat|no heat|heater)\b", r"bed|hot ?end|nozzle", "Which part does not heat?", [("The hotend / nozzle", ["hotend_heater", "hotend_thermistor"]),
     ("The bed", ["bed_heater", "bed_thermistor", "bed_thermal_fuse"]), ("Both", ["power_supply", "controller_board", "dc_power_wiring"])]),
 (r"\b(cable|wire|wiring|plug|cord)\b", r"umbilical|toolhead cable|power (cord|cable|plug)|mains", "Which cable do you mean?", [
     ("The power cord / plug at the back", ["mains_power_input"]), ("The cable to the print head (umbilical)", ["umbilical_wiring"]),
     ("Wires inside the electronics bay", ["dc_power_wiring", "controller_board"])]),
 (r"\brails?\b", r"\b[xyz] ?rails?\b|rails? [xyz]\b", "Which rail do you mean?", [("X rail (print head left-right)", ["x_linear_rail"]),
     ("Y rails (front-back)", ["y_linear_rails"]), ("Z rails (bed up-down)", ["z_rails"])]),
]

def clarify_needed(case, message):
    """Questions to ask before diagnosing: is it the Voron 0.2, and which part is meant (if a word is ambiguous)."""
    qs = []
    if not case["facts"].get("machine") and not VORON_WORDS.search(" ".join(case["notes"] + [message])):
        qs.append(MACHINE_Q)
    if not case["facts"].get("which_part"):
        for pat, skip, text, opts in AMBIGUOUS:
            if re.search(pat, message, re.I) and not re.search(skip, message, re.I):
                qs.append({"id": "which_part", "kind": "choice", "slot": "which_part", "text": text, "options": [o for o, _ in opts] + ["Something else"]})
                break
    return qs

def part_prior(answer):
    for _, _, _, opts in AMBIGUOUS:
        for o, ids in opts:
            if o == answer: return ids, True
    return None, False

SAME_CASE_Q = {"id": "same_case", "kind": "choice", "slot": "same_case", "text": "Which is it?",
               "options": ["A new problem", "Part of the same problem"]}

def different_problem(case, message):
    """True if the message names parts that are unrelated to the current case."""
    now = set(mentioned(message))
    if not now: return False
    before = set(mentioned(" ".join(case["notes"]))) | {h["id"] for h in case.get("hyps", [])[:2]}
    return not (now & before)   # when unsure, the technician decides (a power cut also stops the fans)

PROBLEM_WORDS = re.compile(r"\b(not working|doesn'?t work|does not work|won'?t|stopped|stops|broken|dead|off|fault\w*|problem|issue|error|noise|smell)\b", re.I)
GREET_OR_SMALL = re.compile(r"^\s*(hi|hello|hey|thanks?|thank you|ok(ay)?|bye)\b", re.I)
FOLLOW_UP = re.compile(r"\b(still|also|again|same|it (also|still|only|happens|is|does|was)|this|you said|that|wrong|not (the|that)|but|when it)\b", re.I)

def turn(case, message=None, form=None):
    """One user turn. Returns {"reply": {...}, "case": case}."""
    t0 = time.time(); invalid = {}
    if message is not None:
        kind, msg = check_input(message, bool(case["pending"]))
        if kind: return _out(case, {"type": "notice", "kind": kind, "text": msg}, t0, message)
    # ---- answer to "new problem or same problem?" ----------------------------------------------------
    if form and (form.get("facts") or {}).get("same_case") and case.get("_held"):
        held = case.pop("_held"); choice = form["facts"]["same_case"]
        if choice == "A new problem":
            prev = case.get("previous", []) + [{k: case[k] for k in ("notes", "facts", "measurements", "asked_ids")}]
            keep = {k: case[k] for k in ("id", "log")}; case.clear(); case.update(new_case()); case.update(keep); case["previous"] = prev
            r = turn(case, held); r["reply"]["new_case"] = True; return r   # a new case checks again: Voron? which part?
        return turn(case, held + " (same problem)")
    # ---- structured answers from the form ----------------------------------------------------------
    if form:
        good, bad = validate_measurements(form.get("measurements") or {})
        case["measurements"].update(good); invalid.update(bad)
        for k, v in (form.get("facts") or {}).items():
            if v: case["facts"][k] = v
        for q in form.get("dont_know") or []:
            if q not in case["dont_know"]: case["dont_know"].append(q)
        for c in form.get("exclude") or []:                    # "I checked this part, it is fine"
            if c in KG and c not in case.setdefault("excluded", []): case["excluded"].append(c)
    # ---- free text -------------------------------------------------------------------------------------
    if message:
        u = understand(message, case); case["_understood"] = u
        if u["intent"] == "off_topic" and PROBLEM_WORDS.search(message) and not case["notes"]:
            u["intent"] = "fault_report"   # "light not working": could be the printer; the machine question decides
        if u["intent"] == "smalltalk":
            again = [{"id": q, **{k: v for k, v in Q[q].items() if k not in ("helps", "generic")}} for q in case["pending"] if q in Q]
            txt = ("I'm fine, thanks. I'm here to help find faults on your Voron 0.2." +
                   (" We were in the middle of a case; could you answer this so I can continue?" if again else
                    " Describe what your printer is doing and I'll work out which part is at fault."))
            if again: return _out(case, {"type": "questions", "intro": txt, "questions": again, "hyps": case.get("hyps", [])[:4]}, t0, message)
            return _out(case, {"type": "text", "text": txt}, t0, message)
        # A free-text message during or after a case that does not answer anything (no fact, no number) and is not a
        # clear follow-up ("still", "also", "same") may be a NEW problem: ask the technician instead of guessing.
        pend_slots = {Q[q]["slot"] for q in case["pending"] if q in Q and "slot" in Q[q]}
        # it informs the current case if it answers a pending question or adds a number / a detail (not just a new complaint)
        informs = bool(set(u["facts"]) & pend_slots) or bool(set(u["facts"]) - {"what_happens", "problem_kind"}) \
            or bool(u["measurements"]) or bool(u["dont_know"])
        if case["pending"] and not informs and len(message.split()) <= 3 and not GREET_OR_SMALL.match(message):
            # a very short reply that does not fit the question ("yes" to a multiple-choice question): ask again
            again = [{"id": q, **{k: v for k, v in Q[q].items() if k not in ("helps", "generic")}} for q in case["pending"] if q in Q]
            if again:
                return _out(case, {"type": "questions", "intro": f"I couldn't match \"{message.strip()}\" to the question. Please pick one of the answers below, "
                                   "or describe it in a few words.", "questions": again, "hyps": case.get("hyps", [])[:4]}, t0, message)
        if u["intent"] in ("fault_report", "answer", "off_topic") and case["notes"] and not form and not informs \
                and not FOLLOW_UP.search(message):
            case["_held"] = message
            what = "the case we just finished" if case["status"] == "diagnosed" else "the problem we are looking at"
            return _out(case, {"type": "questions", "intro": f"Is \"{message.strip()}\" a new problem, or part of {what}?",
                               "questions": [SAME_CASE_Q]}, t0, message)
        if u["intent"] == "greeting" and not case["notes"]:
            return _out(case, {"type": "text", "text": INTRO}, t0, message)
        if u["intent"] == "off_topic":
            return _out(case, {"type": "notice", "kind": "off_topic", "text": OFF_TOPIC}, t0, message)
        if u["intent"] == "other_machine":
            return _out(case, {"type": "notice", "kind": "other_machine", "text": "I only know the design of the **Voron 0.2**, so I can't diagnose other printers reliably. If this is about a Voron 0.2, please describe the problem."}, t0, message)
        if u["intent"] == "info_question" and not case["notes"]:
            return _out(case, {"type": "text", "text": info_answer(message) + "\n\nIf your printer has a problem, describe what it does and I'll help find the faulty part."}, t0, message)
        if u["intent"] == "greeting": return _out(case, {"type": "text", "text": "You're welcome. Tell me if anything else comes up with the printer."}, t0, message)
        case["notes"].append(message.strip())
        good, bad = validate_measurements(u["measurements"]); case["measurements"].update(good); invalid.update(bad)
        for k, v in u["facts"].items():
            if k == "what_happens" and case["facts"].get(k): case["facts"][k] += " | " + v
            else: case["facts"][k] = v
        for q in u["dont_know"]:
            if q not in case["dont_know"]: case["dont_know"].append(q)
    if not case["notes"] and not case["measurements"]:
        return _out(case, {"type": "text", "text": INTRO}, t0, message)
    # ---- scope: only the Voron 0.2; and which part is meant ---------------------------------------------
    if case["facts"].get("machine") == "No, another machine or device":
        notes = case["notes"][:]; keep = {k: case[k] for k in ("id", "log")}; case.clear(); case.update(new_case()); case.update(keep)
        return _out(case, {"type": "notice", "kind": "other_machine", "text": "Thanks for telling me. I can only help with the **Voron 0.2 3D printer**: "
                           "my knowledge comes from its design documents, so answers for other machines would be guesses. "
                           "If you have a problem with a Voron 0.2, describe what it is doing."}, t0, message)
    wp = case["facts"].get("which_part")
    if wp == "Something else" and not case.get("_asked_other_part"):
        case["_asked_other_part"] = True; case["pending"] = ["other_part"]
        return _out(case, {"type": "questions", "intro": "Which part do you mean? Tell me where it sits on the printer and what it does, "
                           "so I can match it to the Voron 0.2 design.",
                           "questions": [{"id": "other_part", "kind": "text", "slot": "what_happens", "text": "The part and what it is doing:",
                                          "hint": "e.g. the small fan under the bed / the motor at the back right"}]}, t0, message)
    if wp and part_prior(wp) == (None, True):
        return _out(case, {"type": "text", "text": f"\"{wp}\" is not part of the Voron 0.2 design documents I work from (it is an add-on), "
                           "so I can't diagnose it reliably. If something else on the printer misbehaves, describe it and I'll help."}, t0, message)
    if message and case["rounds"] == 0 and not case.get("clarified"):
        cq = clarify_needed(case, message)
        if cq:
            case["clarified"] = True; case["pending"] = [q["id"] for q in cq]
            intro = ("Before I look for the cause, I need to be sure what we are talking about. " +
                     ("I only work on the **Voron 0.2 3D printer**. " if any(q["id"] == "machine" for q in cq) else "") +
                     ("Several parts could be meant here." if any(q["id"] == "which_part" for q in cq) else ""))
            return _out(case, {"type": "questions", "intro": intro.strip(), "questions": cq}, t0, message)
    # ---- analysis --------------------------------------------------------------------------------------
    calcs = eng.run(case["measurements"]) + eng.context(case["facts"], case["notes"]); case["calcs"] = calcs
    for k in [k for k in calcs if k["verdict"] == "inconclusive"]:   # a test that cannot decide anything: drop it, ask again
        for key in k["keys"]: case["measurements"].pop(key, None)
        q = next((qid for qid, qq in Q.items() if qq["kind"] == "fields" and any(f["key"] in k["keys"] for f in qq["fields"])), None)
        if q and q in case["asked_ids"]: case["asked_ids"].remove(q)
        case["calcs"] = [x for x in calcs if x is not k]
        qs = [{"id": q, **{kk: vv for kk, vv in Q[q].items() if kk not in ("helps", "generic")}}] if q else []
        case["pending"] = [q] if q else []
        return _out(case, {"type": "questions", "intro": f"I can't use that measurement yet: {k['meaning']}", "questions": qs,
                           "calcs": [k]}, t0, message)
    if invalid:   # numbers that cannot be right: ask again before using them
        fields = [{"key": k, "label": k.replace("_", " "), "unit": "", "given": str(v)} for k, v in invalid.items()]
        return _out(case, {"type": "questions", "intro": "Some values look impossible, maybe a typing mistake: "
                           + ", ".join(f"**{k.replace('_', ' ')} = {v}**" for k, v in invalid.items()) + ". Please check and enter them again.",
                           "questions": [{"id": "recheck", "kind": "fields", "text": "Please re-enter:", "fields": fields}], "calcs": calcs}, t0, message)
    base, why = hypotheses(case, calcs)
    P = R.posterior(base, case["facts"], list(KG)); case["_base"] = base
    ex = [c for c in case.get("excluded", []) if c in P]          # parts the technician checked and found fine (3D twin page)
    if ex and len(ex) < len(P):
        for c in ex: P[c] = 0.0
        tot = sum(P.values()) or 1.0; P = {c: p / tot for c, p in P.items()}
        for c in ex: why.setdefault(c, []).insert(0, "checked by you and found fine")
    hyps = ranked_hyps(P, why); case["hyps"] = hyps
    step, info = R.next_step(case, P, evidence_count(case) > 0 or bool(mentioned(" ".join(case["notes"]))))
    led = conduct(case, hyps, calcs, P, step, info) if LEAD_MODEL else None
    if led: step, info = led["step"], led["info"]
    check = None
    if step == "diagnose" and LEAD_MODEL and SELF_CHECK and info != "question limit reached":
        check = self_check(case, hyps, calcs, P)          # second opinion + verifier before anything is named
        if check and check["verdict"] == "ask" and check.get("question_id"):
            step, info = "ask", [check["question_id"]]
            led = {"message": check["reason"]}
        elif check and check["verdict"] == "switch" and check.get("cause"):
            case["_model_cause"] = {"id": check["cause"], "message": check["reason"]}
    case["_check"] = check
    case["_trace"] = build_trace(case, P, why, calcs, step, info)
    if check: case["_trace"]["check"] = check
    if led and led.get("message"): case["_intro"] = led["message"]
    if step == "ask":
        case["rounds"] += 1; case["status"] = "gathering"; case["pending"] = info
        for q in info:
            if q not in case["asked_ids"]: case["asked_ids"].append(q)
        qs = [{"id": q, **{k: v for k, v in Q[q].items() if k not in ("helps", "generic")}} for q in info]
        return _out(case, {"type": "questions", "intro": case.pop("_intro", None) or ask_intro(case, hyps, info), "questions": qs,
                           "calcs": [k for k in calcs if k["verdict"] != "ok"], "hyps": hyps[:4],
                           "template": is_vague(case) and case["rounds"] == 1}, t0, message)
    mc = case.pop("_model_cause", None)
    if mc:   # put the model's choice first, keep the engine's ranking visible as the alternatives
        hyps = [h for h in hyps if h["id"] == mc["id"]] + [h for h in hyps if h["id"] != mc["id"]]
        if hyps[0]["id"] != mc["id"]: hyps.insert(0, {"id": mc["id"], "name": NAME[mc["id"]], "p": P.get(mc["id"], 0), "score": 0, "why": []})
        hyps[0]["why"] = [f"engineering judgement: {mc['message']}"] + hyps[0]["why"]; case["hyps"] = hyps
    dg = diagnose_fast(case, hyps, calcs)       # instant; the page then asks /api/explain for the model's explanation
    ck = case.pop("_check", None)
    if dg and ck:
        dg["check"] = {"verdict": ck["verdict"], "blind": NAME.get(ck.get("blind"), ck.get("blind")), "agree": ck["agree"], "reason": ck["reason"],
                       "unexplained": ck.get("unexplained", [])}
        if ck["agree"] and ck["verdict"] == "confirm" and hyps[0]["p"] >= 0.6: dg["confidence"] = "high"
        if not ck["agree"] and dg["confidence"] == "high": dg["confidence"] = "medium"
    case["status"] = "diagnosed"; case["pending"] = []
    if dg is None:
        return _out(case, {"type": "text", "text": "I could not link the description to a part of the Voron 0.2. Could you describe what the printer does in more detail?"}, t0, message)
    dg["cause_name"] = NAME[dg["cause"]]; dg["p"] = round(P.get(dg["cause"], 0), 3); dg["stop_reason"] = info
    for a in dg["alternatives"] + dg["ruled_out"]: a["name"] = NAME[a["id"]]; a["p"] = round(P.get(a["id"], 0), 3)
    used = [k for k in calcs if dg["cause"] in k["points_to"] or k["verdict"] != "ok"] or calcs
    return _out(case, {"type": "diagnosis", "diagnosis": dg, "calcs": used, "hyps": hyps[:4],
                       "questions_asked": len(case["asked_ids"]), "forced": info == "question limit reached"}, t0, message)

def ask_intro(case, hyps, ask):
    """Short, honest explanation: what the assistant thinks now and why it asks this."""
    top = [h for h in hyps if h["p"] >= 0.05][:3]
    if is_vague(case) and case["rounds"] == 1:
        m = mentioned(" ".join(case["notes"]))
        ups = [NAME[u] for u in neighbours_up(m[0])] if m else []
        return (f"\"{case['notes'][-1]}\" can have several different causes. "
                + (f"A problem at the **{NAME[m[0]]}** can come from the part itself or from the parts connected to it"
                   + (": " + ", ".join(ups[:5]) + "." if ups else ".") + " " if m else "")
                + "One quick question first, so I don't guess.")
    if not top: return "One quick question to narrow it down."
    now = ", ".join(f"**{short(h['name'])}** ({h['p']:.0%})" for h in top)
    return f"Right now it is most likely {now}. " + ("This answer separates them." if len(ask) == 1 else "These two answers separate them.")

LEAD_MODEL = os.environ.get("LEAD", "auto") == "model" or (os.environ.get("LEAD", "auto") == "auto" and (os.environ.get("PROVIDER", "ollama") == "openai" or bool(os.environ.get("FT_MODEL"))))
CONDUCT_SYS = """You are a senior mechanical and electrical engineer leading a fault-finding conversation with a technician about a
Voron 0.2 3D printer. A probabilistic engine gives you the possible causes with probabilities, exact calculations, the failure
graph, and the questions it could ask with their expected information gain. You decide the next move like an expert would:
- Read the whole conversation. Understand what the technician means even if it is vague or has typos.
- Do not conclude from one vague sentence. Ask the question(s) that best separate the leading causes; prefer quick
  observations over measurements; ask at most 2 questions; choose them ONLY from the given ids.
- Conclude ("diagnose") only when the evidence clearly points to one part and you can explain the physical chain.
- You may disagree with the engine's ranking if engineering reasoning says so, but say why in the message.
- "message": 1-3 short sentences to the technician in simple English: what you understood and why you ask this.
Return JSON only: {"action": "ask" or "diagnose", "question_ids": ["..."], "message": "..."}"""

def conduct(case, hyps, calcs, P, step, info):
    """The language model leads the conversation; the engine's rules stay as guard rails."""
    if STUB: return None
    try:
        top = sorted(P, key=P.get, reverse=True)
        cand = R.rank_questions(case, P, top[0] if P[top[0]] >= 0.5 else None)[:6]
        if not cand: return None
        hist = "\n".join(f"Technician: {n}" for n in case["notes"][-6:])
        ans = "; ".join(f"{k.replace('_', ' ')}: {v}" for k, v in case["facts"].items() if k != "what_happens")
        hy = "\n".join(f"- {h['id']} ({h['p']:.0%}): " + "; ".join(h["why"][:3]) for h in hyps[:6])
        paths = [readable(p) for j in top[1:6] for p in [_graph.path(top[0], j)] if p and p.count("-->") <= 2][:4]
        cl = "\n".join(f"- {k['title']}: {k['result']} => {k['verdict']}: {k['meaning']}" for k in calcs) or "- none"
        qs = "\n".join(f"- {q['id']} (gain {q['gain']:.2f} bits): {Q[q['id']]['text']}" for q in cand)
        user = f"""CONVERSATION
{hist}
ANSWERS SO FAR: {ans or "none"}
MEASUREMENTS: {json.dumps(case["measurements"]) or "none"}
COULD NOT ANSWER: {", ".join(case["dont_know"]) or "none"}
POSSIBLE CAUSES (engine)
{hy}
CALCULATIONS
{cl}
HOW THE LEADING PART CONNECTS: {"; ".join(paths) or "-"}
QUESTIONS AVAILABLE
{qs}
Engine suggestion: {step} {info}. Questions asked so far: {len(case["asked_ids"])}."""
        kb = K.knowledge(KG, _graph)
        sys_ = CONDUCT_SYS + ("\n\nYou may name the cause yourself (\"cause\": component id) if your engineering reasoning over the "
                              "knowledge base disagrees with the engine; explain why in the message.\n\n" + kb if kb else "")
        if FT_MODEL:   # the fine-tuned local model leads, with the exact format it was trained on
            from finetune.fmt import SYSTEM_LEAD, lead_context
            from .llm import ask_local
            r = ask_local(FT_MODEL, SYSTEM_LEAD, lead_context(case, hyps, cand, KG, Q, compact_text)) or {}
        else:
            r = ask_json(sys_, user, max_tokens=400) or {}
        ids = [q for q in (r.get("question_ids") or []) if q in {c["id"] for c in cand}][:2]
        msg = str(r.get("message") or "").strip()
        act = r.get("action")
        # guard rails: never conclude without a confirming answer; stop when the engine's limit is reached
        confirmed = case["rounds"] > 0 or bool(case["measurements"]) or bool(case["facts"].get("error_message"))
        own = r.get("cause") if r.get("cause") in KG else None
        if act == "diagnose" and confirmed and own and own != top[0] and P.get(own, 0) >= 0.1:
            case["_model_cause"] = {"id": own, "message": msg}   # the model overrides the engine's leader, with its reason
            return {"step": "diagnose", "info": "model's engineering judgement over all part cards", "message": msg}
        if act == "diagnose" and confirmed and P[top[0]] >= 0.4: return {"step": "diagnose", "info": "the evidence points clearly to one part (model and engine agree)" if step == "diagnose" else "model judged the evidence sufficient", "message": msg}
        if step == "diagnose" and (case["rounds"] >= R.MAX_TURNS): return None
        if act == "ask" or not confirmed: return {"step": "ask", "info": ids or (info if step == "ask" else [cand[0]["id"]]), "message": msg}
        return None
    except Exception as e:
        print("conductor skipped:", e); return None

BLIND_SYS = KB_SYS.replace("A technician describes a fault.", "A technician describes a fault and has answered some questions.")
VERIFY_SYS = """You are the checking engineer. A diagnosis for a Voron 0.2 3D printer has been proposed. Check it hard, using the
knowledge base below (part cards, failure graph, design values) and physics:
1. List every observation of the technician (each answer, each measurement, the description).
2. For the proposed cause, say which observations it does NOT explain or contradicts.
3. Compare with the independent reading and the alternatives.
Decide one:
- "confirm": the proposed cause explains every observation and nothing argues against it.
- "switch": another candidate clearly explains the observations better (give its id in "cause").
- "ask": two candidates both still fit; give the ONE question id from the list that best separates them.
Never give repair steps. Return JSON only:
{"verdict": "confirm|switch|ask", "cause": "<id or empty>", "question_id": "<id or empty>",
 "unexplained": ["observation the proposed cause does not explain"], "reason": "1-2 sentences in simple English for the technician"}"""

def case_summary(case, calcs):
    ans = "; ".join(f"{k.replace('_', ' ')}: {v}" for k, v in case["facts"].items() if k not in ("what_happens", "machine", "same_case"))
    cl = "; ".join(f"{k['title']}: {k['result']} ({k['verdict']})" for k in calcs) or "none"
    return (f"Description: {' | '.join(case['notes'])}\nAnswers: {ans or 'none'}\nMeasurements: {json.dumps(case['measurements']) or 'none'}\n"
            f"Could not answer: {', '.join(case['dont_know']) or 'none'}\nCalculations: {cl}")

def self_check(case, hyps, calcs, P):
    """Two extra model calls, only when a cause is about to be named:
    (1) a BLIND second opinion: the model reads the whole case and knowledge base without seeing the engine's answer;
    (2) a VERIFIER: checks the proposed cause against every observation, compares with the second opinion, and
        confirms it, switches to a better-fitting part, or asks the one question that separates the two."""
    if STUB: return None
    kb = K.knowledge(KG, _graph)
    if not kb: return None
    try:
        summ = case_summary(case, calcs)
        b = ask_json(BLIND_SYS + "\n\n" + kb, summ, max_tokens=500) or {}
        blind = next((c.get("id") for c in (b.get("candidates") or []) if isinstance(c, dict) and c.get("id") in KG), None)
        proposed = case.get("_model_cause", {}).get("id") or hyps[0]["id"]
        top = sorted(P, key=P.get, reverse=True)
        qs = R.rank_questions(case, P)[:8]
        user = (f"{summ}\n\nPROPOSED CAUSE: {proposed} ({P.get(proposed, 0):.0%} in the engine)\n"
                f"INDEPENDENT READING (did not see the proposal): {blind or 'none'}\n"
                f"ALTERNATIVES: " + ", ".join(f"{c} ({P[c]:.0%})" for c in top[:5] if c != proposed) +
                "\nQUESTIONS AVAILABLE: " + ("; ".join(f"{q['id']}: {Q[q['id']]['text']}" for q in qs) or "none"))
        v = ask_json(VERIFY_SYS + "\n\n" + kb, user, max_tokens=450) or {}
        verdict = v.get("verdict") if v.get("verdict") in ("confirm", "switch", "ask") else "confirm"
        cause = v.get("cause") if v.get("cause") in KG else None
        qid = v.get("question_id") if v.get("question_id") in {q["id"] for q in qs} else None
        if verdict == "switch" and not cause: verdict = "confirm"
        if verdict == "ask" and (not qid or case["rounds"] >= R.MAX_TURNS): verdict = "confirm" if blind == proposed else ("switch" if blind else "confirm"); cause = cause or blind
        return {"verdict": verdict, "proposed": proposed, "blind": blind, "agree": blind == proposed, "cause": cause,
                "question_id": qid, "unexplained": [str(u) for u in (v.get("unexplained") or [])][:4], "reason": str(v.get("reason") or "")}
    except Exception as e:
        print("self-check skipped:", e); return None

def build_trace(case, P, why, calcs, step, info):
    """Everything the assistant used for this turn, so the technician can check its reasoning step by step."""
    u = case.pop("_understood", None) or {}
    top = sorted(P, key=P.get, reverse=True)[:6]
    leader = top[0]
    qs = R.rank_questions(case, P, leader if P[leader] >= 0.5 else None)[:4]
    return {
        "understood": {"intent": u.get("intent"), "facts": u.get("facts", {}), "measurements": u.get("measurements", {}),
                       "dont_know": u.get("dont_know", [])} if u else None,
        "parts": [{"name": NAME[c], "p": round(P[c], 3), "why": why.get(c, [])[:6]} for c in top],
        "calcs": [{"title": k["title"], "result": k["result"], "verdict": k["verdict"], "meaning": k["meaning"]} for k in calcs],
        "questions": [{"text": Q[q["id"]]["text"], "gain": q["gain"], "value": q["value"]} for q in qs],
        "decision": ("ask: " + ", ".join(Q[q]["text"] for q in info)) if step == "ask" else f"name the cause: {info}",
        "model": "offline demo (rules only)" if STUB else LLM_MODEL}

def _out(case, reply, t0, message):
    if "_trace" in case: reply["trace"] = case.pop("_trace")
    if case.pop("_new_case", False): reply["new_case"] = True
    case.pop("_intro", None); case.pop("_check", None)
    case.pop("_understood", None)
    reply["secs"] = round(time.time() - t0, 1); reply["model"] = "offline demo (rules only)" if STUB else LLM_MODEL
    case["log"].append({"time": time.strftime("%H:%M:%S"), "user": message, "reply_type": reply["type"], "secs": reply["secs"]})
    return {"reply": reply, "case": {k: case[k] for k in ("id", "facts", "measurements", "rounds", "status", "dont_know")},
            "_case": case}
