"""Assembly guide chat: answers questions about how the Voron 0.2 is built and how its parts connect and work.

Knowledge used (all local): data/assembly_steps.json (14 steps in the order of the assembly manual, with page numbers),
the part cards (what each part does), the part graph (which part drives / powers / carries which), and the text of the
assembly manual (word search). The answer is composed from these facts. When Ollama is running, the local model only
rewrites the facts into a clearer answer; if it is off or fails, the composed answer is returned as it is.

answer(message) -> {"answer": text, "actions": {"step": n or None, "highlight": [part ids], "replay": bool}, "sources": [..]}
"""
import json, re, pathlib, sys
A = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(A / "src"))
STEPS = json.loads((A / "data" / "assembly_steps.json").read_text(encoding="utf-8"))
STEP_OF = {}                      # part id -> step (the first step that fits it)
for _s in STEPS:
    for _p in _s["parts"]: STEP_OF.setdefault(_p, _s)

PART_WORDS = [  # words people use -> part id (checked in order; longer phrases first)
 ("thermal fuse", "bed_thermal_fuse"), ("bed thermistor", "bed_thermistor"), ("bed heater", "bed_heater"), ("heater pad", "bed_heater"), ("heat pad", "bed_heater"),
 ("hotend fan", "hotend_fan"), ("heatsink fan", "hotend_fan"), ("part cooling", "part_cooling_fan"), ("part fan", "part_cooling_fan"), ("blower", "part_cooling_fan"),
 ("hotend thermistor", "hotend_thermistor"), ("thermistor", "hotend_thermistor"), ("heater cartridge", "hotend_heater"), ("hotend heater", "hotend_heater"), ("heater block", "hotend_heater"),
 ("heatbreak", "heatbreak_ptfe"), ("heat break", "heatbreak_ptfe"), ("ptfe", "heatbreak_ptfe"), ("nozzle", "nozzle"), ("hotend", "hotend_heater"), ("hot end", "hotend_heater"),
 ("extruder motor", "extruder_motor"), ("pancake", "extruder_motor"), ("guidler", "extruder_gears_guidler"), ("drive gear", "extruder_gears_guidler"), ("bmg", "extruder_gears_guidler"),
 ("extruder", "extruder_gears_guidler"), ("lead screw", "z_motor_leadscrew"), ("leadscrew", "z_motor_leadscrew"), ("z motor", "z_motor_leadscrew"), ("z endstop", "z_endstop"),
 ("endstop", "z_endstop"), ("z rail", "z_rails"), ("y rail", "y_linear_rails"), ("x rail", "x_linear_rail"), ("x axis", "x_linear_rail"), ("gantry", "x_linear_rail"),
 ("linear rail", "y_linear_rails"), ("rails", "y_linear_rails"), ("belt", "xy_belts"), ("pulley", "xy_pulleys_idlers"), ("idler", "xy_pulleys_idlers"), ("bearing", "xy_pulleys_idlers"),
 ("a/b motor", "xy_motors_drivers"), ("ab motor", "xy_motors_drivers"), ("xy motor", "xy_motors_drivers"), ("a motor", "xy_motors_drivers"), ("b motor", "xy_motors_drivers"),
 ("stepper driver", "xy_motors_drivers"), ("a/b drive", "xy_motors_drivers"), ("ab drive", "xy_motors_drivers"), ("motors", "xy_motors_drivers"),
 ("print head", "toolhead"), ("printhead", "toolhead"), ("toolhead cable", "umbilical_wiring"), ("umbilical", "umbilical_wiring"), ("toolhead", "toolhead"), ("stealthburner", "toolhead"),
 ("x carriage", "toolhead"), ("carriage", "toolhead"), ("build plate", "bed_plate_carrier"), ("print bed", "bed_plate_carrier"), ("bed", "bed_plate_carrier"),
 ("power supply", "power_supply"), ("psu", "power_supply"), ("power cord", "mains_power_input"), ("mains", "mains_power_input"), ("inlet", "mains_power_input"),
 ("controller board", "controller_board"), ("skr", "controller_board"), ("pico", "controller_board"), ("mainboard", "controller_board"), ("controller", "controller_board"),
 ("raspberry", "host_computer"), (" pi ", "host_computer"), ("klipper", "firmware_config_macros"), ("firmware", "firmware_config_macros"), ("config", "firmware_config_macros"),
 ("24 v wir", "dc_power_wiring"), ("24v wir", "dc_power_wiring"), ("crimp", "dc_power_wiring"), ("runout", "filament_runout_sensor"), ("spool", "filament_material"), ("filament", "filament_material"),
]
STEP_WORDS = [("frame", "frame"), ("extrusion", "frame"), ("skirt", "skirts"), ("feet", "skirts"), ("foot", "skirts"), ("display", "skirts"), ("screen", "skirts"), ("panel", "panels"), ("door", "panels"),
              ("tophat", "tophat"), ("top hat", "tophat"), ("lid", "tophat"), ("spool holder", "spool"), ("electronics", "electronics"), ("wiring", "electronics"), ("wire", "electronics")]
STEP_BY_ID = {s["id"]: s for s in STEPS}
REL = {"drives": "drives", "powers": "powers", "carries_power_to": "carries power to", "reads_signal_of": "reads the signal of", "commands": "commands", "feeds": "feeds filament to",
       "moves": "moves", "guides": "guides", "carries": "carries", "controls": "controls", "heats": "heats", "cools": "cools", "configures": "is configured for", "in_series_with": "is wired in series with",
       "runs_over": "runs over", "measures": "measures"}

_E = None
def _engine():
    global _E
    if _E is None:
        from assistant_v2 import engine as E
        E._load(); _E = E
    return _E

def name(pid):
    E = _engine()
    from assistant_v2.extra_parts import EXTRA
    return (E.KG.get(pid) or EXTRA.get(pid) or {}).get("name", pid.replace("_", " "))

def card(pid):
    E = _engine()
    from assistant_v2.extra_parts import EXTRA
    return E.KG.get(pid) or EXTRA.get(pid) or {}

def find_parts(text):
    low = " " + text.lower().replace("-", " ") + " "; out = []; used = []
    for w, pid in PART_WORDS:
        i = low.find(w)
        if i >= 0 and not any(a <= i < b for a, b in used):
            used.append((i, i + len(w)))
            if pid not in [p for _, p in out]: out.append((i, pid))
    return [p for _, p in sorted(out)]

def find_step(text):
    low = text.lower()
    m = re.search(r"\bstep\s*(\d{1,2})\b", low)
    if m and 1 <= int(m.group(1)) <= len(STEPS): return STEPS[int(m.group(1)) - 1]
    for w, sid in STEP_WORDS:
        if w in low: return STEP_BY_ID[sid]
    return None

def edges_between(a, b):
    """Direct links between two parts in the part graph, as sentences with their source."""
    E = _engine(); out = []
    for x, y in ((a, b), (b, a)):
        for e in E._graph.out.get(x, []):
            if e["dst"] == y: out.append(f"{name(x)} {REL.get(e['rel'], e['rel'].replace('_', ' '))} {name(y)} (source: {e.get('source', 'part graph')})")
    return out

def links_of(pid, limit=5):
    E = _engine(); out = []
    for e in E._graph.inc.get(pid, []):
        if e["rel"] != "configures": out.append(f"{name(e['src'])} {REL.get(e['rel'], e['rel'].replace('_', ' '))} it")
    for e in E._graph.out.get(pid, []):
        if e["rel"] != "configures": out.append(f"it {REL.get(e['rel'], e['rel'].replace('_', ' '))} {name(e['dst'])}")
    return out[:limit]

def chain(a, b, max_len=4):
    """Shortest chain of physical links from a to b (either direction of each link), as sentences."""
    E = _engine(); nb = {}
    for src, es in E._graph.out.items():
        for e in es:
            if e["rel"] == "configures": continue
            nb.setdefault(src, []).append((e["dst"], f"{name(src)} {REL.get(e['rel'], e['rel'].replace('_', ' '))} {name(e['dst'])}"))
            nb.setdefault(e["dst"], []).append((src, f"{name(src)} {REL.get(e['rel'], e['rel'].replace('_', ' '))} {name(e['dst'])}"))
    seen = {a}; queue = [(a, [])]
    while queue:
        x, path = queue.pop(0)
        if x == b: return path
        if len(path) >= max_len: continue
        for y, sent in nb.get(x, []):
            if y not in seen: seen.add(y); queue.append((y, path + [sent]))
    return []

_BM = None
def manual_hits(q, k=2):
    """Word search in the assembly manual text (pages), for facts the steps do not cover."""
    global _BM
    try:
        if _BM is None:
            from retrieval import BM25
            f = A / "data" / "indexes" / "chunks_B.jsonl"
            docs = [json.loads(l) for l in open(f, encoding="utf-8")]
            docs = [d for d in docs if "Assembly_Manual" in d.get("source", "") and len(d.get("text", "")) > 80]
            _BM = (BM25([d["text"] for d in docs]), docs)
        bm, docs = _BM; sc = bm.scores(q); idx = sorted(range(len(docs)), key=lambda i: -sc[i])[:k]
        return [(docs[i]["section"].replace("page", "p."), docs[i]["text"]) for i in idx if sc[i] > 4]
    except Exception:
        return []

def step_text(s, short=False):
    t = f"**Step {s['n']}: {s['title']}** (manual p. {s['pages']})\n{s['what']}\n**How it connects:** {s['connect']}"
    return t if short else t + f"\n**Tip:** {s['tip']}"

OVERVIEW = re.compile(r"\b(order|sequence|overview|all steps|which steps|what steps|first step|where do i start|how (do i|to) (assemble|build)( it| the printer| a voron)?\s*\??$)", re.I)
CONNECT = re.compile(r"\b(connect\w*|attach\w*|mount\w*|join\w*|fix\w*|fasten\w*|install\w*|fit\w*|wired?|wiring|plug\w*|screw\w*|goes? (on|in|into|to)|link\w*|between)\b", re.I)
WORK = re.compile(r"\b(how does|how do|what is|what are|what does|function|purpose|why|works?|job|role|explain)\b", re.I)
SHOW = re.compile(r"\b(show|where is|where are|highlight|point|see|locate|find)\b", re.I)
NEXT = re.compile(r"\b(next|after (that|this)|then what)\b", re.I)

def compose(message, current_step=None):
    """Deterministic answer from the local knowledge. Returns (text, actions, sources)."""
    parts = find_parts(message); step = find_step(message); act = {"step": None, "highlight": parts[:3], "replay": False}; src = []
    if NEXT.search(message) and current_step and current_step < len(STEPS):
        s = STEPS[current_step]; act.update(step=s["n"], replay=True); return step_text(s), act, [f"Assembly manual p. {s['pages']}"]
    if OVERVIEW.search(message) and not parts:
        lines = [f"{s['n']}. **{s['title']}** (p. {s['pages']})" for s in STEPS]
        return "The printer is assembled in this order (the order of the Voron 0.2 assembly manual):\n" + "\n".join(lines) + "\nPress **Assemble** to watch it, or ask me about any step or part.", act, ["Assembly manual, table of contents"]
    if len(parts) >= 2 and (CONNECT.search(message) or True):
        a, b = parts[0], parts[1]; sa, sb = STEP_OF.get(a), STEP_OF.get(b); out = [f"**{name(a)}** and **{name(b)}**:"]
        ed = edges_between(a, b)
        if ed: out += ["In the machine: " + "; ".join(ed) + "."]
        else:
            ch = chain(a, b)
            if ch: out.append("They are linked through other parts: " + "; ".join(ch) + ".")
            else: out.append("They are not directly linked in the part graph; they meet through the frame.")
        if sa and sb and sa["id"] == sb["id"]: out.append(f"Both are fitted in step {sa['n']} ({sa['title']}). {sa['connect']}"); act.update(step=sa["n"], replay=True)
        else:
            for s, p in ((sa, a), (sb, b)):
                if s: out.append(f"{name(p)} is fitted in step {s['n']} ({s['title']}): {s['connect']}")
            last = max([s for s in (sa, sb) if s], key=lambda s: s["n"], default=None)
            if last: act.update(step=last["n"], replay=True)
        src = [f"Assembly manual p. {s['pages']}" for s in (sa, sb) if s] + (["part graph"] if ed else [])
        return "\n".join(out), act, src
    if parts:
        p = parts[0]; c = card(p); s = STEP_OF.get(p); out = [f"**{name(p)}**"]
        if c.get("function"): out.append("What it does: " + c["function"])
        lk = links_of(p)
        if lk: out.append("In the machine: " + "; ".join(lk) + ".")
        if s:
            out.append(f"It is fitted in step {s['n']} ({s['title']}, manual p. {s['pages']}). {s['connect']}")
            if CONNECT.search(message) or SHOW.search(message): out.append("Tip: " + s["tip"])
            act.update(step=s["n"], replay=bool(CONNECT.search(message) or SHOW.search(message))); src.append(f"Assembly manual p. {s['pages']}")
        if c.get("source"): src.append(str(c["source"])[:80])
        return "\n".join(out), act, src
    if step:
        act.update(step=step["n"], replay=True); return step_text(step), act, [f"Assembly manual p. {step['pages']}"]
    hits = manual_hits(message)
    if hits:
        return "From the assembly manual:\n" + "\n".join(f"- ({pg}) {tx[:320]}{'…' if len(tx) > 320 else ''}" for pg, tx in hits), act, [f"Assembly manual {pg}" for pg, _ in hits]
    return ("I can explain how the Voron 0.2 is assembled. Ask for example: \"what is the order of the steps?\", \"how are the belts connected to the motors?\", "
            "\"how does the extruder work?\", or \"show me how to mount the bed\"."), act, []

SYSTEM = """You are an assembly guide for the Voron 0.2 3D printer. The user knows nothing about the machine.
Rewrite the FACTS into a clear, friendly answer to the QUESTION in simple English (short sentences, at most 120 words).
Use ONLY the facts given. Do not add screw sizes, torque values, page numbers or steps that are not in the facts.
Keep part names and step numbers exactly. Return JSON only: {"answer": "..."}"""

def answer(message, current_step=None, use_model=True):
    text, act, src = compose(message, current_step); by = "rules"
    if use_model and len(text) > 200:
        try:
            from assistant_v2.llm import ask_json
            r = ask_json(SYSTEM, f"QUESTION: {message}\n\nFACTS:\n{text}", max_tokens=260, timeout=90) or {}
            a = str(r.get("answer", "")).strip()
            if len(a) > 60: text, by = a, "model"
        except Exception:
            pass
    return {"answer": text, "actions": act, "sources": src, "by": by}

if __name__ == "__main__":
    import os; os.environ.setdefault("STUB", "1")
    for q in ["what is the order of the steps?", "how are the belts connected to the motors?", "how does the extruder work?", "show me how to mount the bed",
              "how is the power supply connected to the controller board", "what does the hotend fan do", "tell me about the tophat", "what torque for the nozzle?"]:
        r = answer(q, use_model=False); print(f"\nQ: {q}\n{r['answer'][:420]}\n   -> {r['actions']} {r['sources']}")
