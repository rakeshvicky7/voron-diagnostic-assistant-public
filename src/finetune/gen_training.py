"""Generate fine-tuning conversations from the Voron 0.2 knowledge base (no API calls, no test cases).

For every failure mode on every part card (31 parts, 56 failure modes):
 1. OPENERS: the technician's first message in ~10 styles (vague, symptom, timing, numbers, typos, casual,
    wrong part named, ...), built from the card's symptom text and word lists. Optional: more natural wording
    from the local model (--paraphrase), cached in data/finetune/paraphrases.json.
 2. CONVERSATION: the assistant engine runs its normal policy (probabilities, information-gain questions,
    stop rule). A SIMULATED TECHNICIAN answers every question as a printer with exactly that fault would:
    choice answers from the answer -> part table, measurements from the design values (e.g. an open heater
    reads "open", a weak power supply 21 V, a slipping extruder feeds 62 of 100 mm). Healthy parts give
    healthy answers.
 3. TARGETS (what the model learns):
    - role "reading": description -> likely parts, the true one first, with physical reasons;
    - role "lead": conversation so far -> ask the most useful question, or name the cause with its chain.
      The truth is never used to pick a question (the engine's policy picks it); it is only used to correct
      a wrong conclusion into "ask one more question".
Nothing from the 58 test cases or their sources is used. 15 % of the failure modes are held out (val.jsonl).

Run on the laptop (Ollama running, for the search embeddings):  py -3.12 src\\finetune\\gen_training.py
Options: --per-fault 10  --paraphrase (adds local-model wording, slow)  --seed 7
Output: data/finetune/train.jsonl, val.jsonl, stats.json  (chat format: {"messages": [system, user, assistant]})
"""
import os, sys, json, random, re, argparse, pathlib
# The generator must never call a language model: switch every model-based step off, whatever this window has set
# (a leftover PROVIDER / FT_MODEL / KB_MODE from the chat would make every message wait for a model or a cloud limit).
for _k, _v in {"AGENT_PRIOR": "0", "KB_MODE": "off", "FT_MODEL": "", "LEAD": "rules", "SELF_CHECK": "0", "PROVIDER": "ollama"}.items():
    os.environ[_k] = _v
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from assistant_v2 import engine as E, reasoner as R            # noqa: E402
from assistant_v2 import engineering as eng                    # noqa: E402
from assistant_v2.questions import Q, EVIDENCE, AREA           # noqa: E402
from assistant_v2.understand import keyword_facts, rule_extract, validate_measurements   # noqa: E402
from tools import compact_text                                  # noqa: E402
from twin import heat_power as TWIN_HEAT                        # noqa: E402  stage 1 (data v2)
from twin import virtual_printer as TWIN_FULL                    # noqa: E402  stage 2, all 31 parts (data v3)
TWIN = TWIN_FULL

OUT = E.A / "data" / "finetune"
from finetune.fmt import SYSTEM_LEAD, SYSTEM_READ, lead_context, read_context   # noqa: E402

# ---------- 0. part-specific fault wording ----------------------------------------------------------------
# The cards use 12 class templates (all motors share one text, all sensors another). For training, identical symptom
# text on different parts would teach contradictions, and some template lines do not fit a part (a switch has no
# 'ADC out of range'). These part-specific lines are general FDM / Voron knowledge written by the researcher,
# consistent with the cards and the documents; none comes from the 58 test cases.
SPECIFIC = {
 "filament_runout_sensor": [("switch stuck or wired wrong", "print pauses by itself although filament is loaded"),
                            ("sensor never triggers", "filament runs out but the print keeps going in the air")],
 "z_endstop": [("switch not triggering or wired open", "Z does not stop when homing and the bed crashes"),
               ("position_endstop wrong", "first layer is too high or too squished everywhere"),
               ("loose switch or bracket", "first layer height changes from print to print")],
 "hotend_fan": [("heatsink fan not spinning", "the heatsink fan does not spin and the filament jams after some minutes")],
 "part_cooling_fan": [("part cooling fan not spinning", "overhangs droop and bridges sag, the part fan does not blow")],
 "nozzle": [("clogged nozzle", "nothing or very little comes out from the start and the extruder clicks"),
            ("nozzle not tightened against the heatbreak", "plastic leaks around the nozzle and the heater block")],
 "heatbreak_ptfe": [("heat creep in the heatbreak", "extrusion stops after some minutes of printing, filament stuck in the hotend"),
                    ("gap at the PTFE tube", "intermittent jams and blobs, filament has a bulge when pulled out")],
 "extruder_gears_guidler": [("gears slipping or worn", "extruder clicks, filament is chewed, under-extrusion"),
                            ("idler tension wrong", "gears turn but the filament does not move")],
 "extruder_motor": [("motor or driver not working", "extruder motor does not turn or only hums"),
                    ("rotation_distance or current wrong", "always too much or too little plastic, also on slow prints")],
 "xy_belts": [("belt loose or tensions unequal", "layer shifts, ghosting, prints come out of square"),
              ("belt rubbing or misrouted", "periodic marks on walls and a rubbing noise when the head moves")],
 "xy_pulleys_idlers": [("pulley grub screw loose", "layer shifts in one direction and positions drift during the print"),
                       ("idler bearing worn", "grinding noise from the corners when the head moves fast")],
 "xy_motors_drivers": [("motor current or acceleration too high for the motor", "layer shifts at high speed and a motor clicks"),
                       ("sensorless homing badly tuned", "X or Y homing stops early or bangs into the end")],
 "x_linear_rail": [("X rail dirty or binding", "the head moves roughly left-right, ringing in X")],
 "y_linear_rails": [("Y rails binding or not parallel", "front-back movement feels tight, layer shifts in Y")],
 "z_rails": [("Z rails binding", "regular horizontal lines on the walls, bed moves unevenly")],
 "z_motor_leadscrew": [("lead screw or nut binding", "Z banding and layers with uneven height"),
                       ("Z motor not moving", "the bed does not move up or down")],
 "bed_plate_carrier": [("bed not level / springs loose", "first layer good on one side and too high on the other")],
 "toolhead": [("hotend or toolhead loose", "ringing and wobbly walls, the nozzle moves when touched")],
 "controller_board": [("board not connected or not starting", "'MCU unable to connect' at start"),
                      ("TMC driver communication fault", "'TMC UART' error and the motors do not move")],
 "power_supply": [("power supply weak or overloaded", "the printer switches off when the bed heats"),
                  ("5 V rail low", "the Raspberry Pi reboots and the web page disconnects")],
 "host_computer": [("Raspberry Pi or its SD card failing", "the web page does not load or disconnects with 'Lost communication'"),
                   ("Pi overloaded", "'Timer too close' error during prints")],
 "firmware_config_macros": [("config limits wrong", "'Move out of range' error on a normal print"),
                            ("extruder rotation_distance wrong in the config", "every print over-extrudes")],
 "slicer_settings": [("print too fast for the hotend", "under-extrusion only at high speed, fine when slow"),
                     ("retraction and temperature too high", "strings and blobs between parts")],
}
def fault_list():
    out = []
    for cid, c in E.KG.items():
        modes = [{"mode": m, "symptom": sy} for m, sy in SPECIFIC[cid]] if cid in SPECIFIC else c["failure_modes"]
        out += [(cid, i, f) for i, f in enumerate(modes)]
    return out

# ---------- 1. openers ------------------------------------------------------------------------------------
def part_word(cid):
    for words, ids in E.ALIASES:
        if cid in ids: return words[0].strip()
    return E.short(E.NAME[cid]).lower()

TIMING = {"Only when the head moves": "it only happens when the head moves", "Only while heating": "it happens while heating up",
          "Right after the first layer": "it happens right after the first layer", "After some minutes of printing": "it starts after a few minutes of printing"}
CASUAL = ["hey, {s}. any idea?", "help! {s}", "{s}, what could it be?", "so {s}...", "my voron: {s}"]

def typos(text, rnd):
    w = text.split()
    for _ in range(max(1, len(w) // 5)):
        i = rnd.randrange(len(w))
        if len(w[i]) > 3:
            j = rnd.randrange(1, len(w[i]) - 1); w[i] = w[i][:j] + w[i][j + 1:] if rnd.random() < .5 else w[i][:j] + w[i][j + 1] + w[i][j] + w[i][j + 2:]
    return " ".join(w)

def symptom_clauses(f):
    return [c.strip(" .") for c in re.split(r";|, or |\bor\b", f["symptom"]) if len(c.strip()) > 6]

NUMBERS = {"hotend_heater": "the hotend only reaches {n} C instead of 220", "bed_heater": "the bed stays at {n} C, target 90",
           "power_supply": "I measured {v} V on the 24 V output", "xy_belts": "belt A plucks at about {hz} Hz",
           "extruder_gears_guidler": "I asked for 100 mm and only {mm} mm went in", "nozzle": "commanded 100 mm, only {mm} mm fed"}

def openers(cid, f, rnd, k):
    sym = symptom_clauses(f) or [f["symptom"]]; pw = part_word(cid); out = []
    out.append(f"my {pw} is not working")                                    # vague
    out.append(sym[0].capitalize())                                           # the symptom
    out.append(f"{sym[0]} on my voron 0.2")
    timing = [TIMING[o] for (s, o), ids in EVIDENCE.items() if s == "when" and cid in ids and o in TIMING]
    if timing: out.append(f"{sym[0]}, {rnd.choice(timing)}")
    if len(sym) > 1: out.append(f"{sym[0]} and {sym[1]}")
    if cid in NUMBERS:
        out.append(f"{sym[0]}; " + NUMBERS[cid].format(n=rnd.choice([60, 120, 150]), v=rnd.choice([21.1, 20.6]), hz=rnd.choice([78, 85]), mm=rnd.choice([55, 62, 70])))
    out.append(typos(sym[0], rnd))                                            # typos
    out.append(rnd.choice(CASUAL).format(s=sym[0]))                           # casual
    neighbour = [e["dst"] for e in E._graph.out.get(cid, []) if e["dst"] in E.KG]
    if neighbour: out.append(f"I think my {part_word(rnd.choice(neighbour))} is broken: {sym[0]}")   # names the wrong part
    out.append(f"{sym[0]}. it started suddenly, nothing changed")
    rnd.shuffle(out); seen, uniq = set(), []
    for o in out:
        if o.lower() not in seen: seen.add(o.lower()); uniq.append(o)
    return uniq[:k]

# ---------- 2. simulated technician ---------------------------------------------------------------------------
HEALTHY = {"hotend_target_c": 220, "hotend_actual_c": 219, "hotend_swing_c": 1, "room_c": 22, "hotend_heater_ohm": 14.4,
           "hotend_thermistor_ohm": 92000, "bed_target_c": 90, "bed_actual_c": 89.6, "bed_heater_ohm": 9.7, "bed_thermistor_ohm": 92000,
           "psu_v": 24.1, "rail_5v_v": 5.05, "fan_v": 24.0, "extrude_cmd_mm": 100, "extrude_act_mm": 98.5, "axis_name": "x",
           "axis_cmd_mm": 100, "axis_act_mm": 99.8, "belt_a_hz": 110, "belt_b_hz": 111, "print_temp_c": 220, "print_speed_mms": 80,
           "layer_height_mm": 0.2, "line_width_mm": 0.45}
FAULTY = {   # what a technician would measure with this part faulty (design values from engineering.SPEC)
 "hotend_heater": {"hotend_heater_ohm": "open", "hotend_actual_c": 25}, "hotend_thermistor": {"hotend_thermistor_ohm": "open", "hotend_swing_c": 35},
 "umbilical_wiring": {"hotend_swing_c": 40, "fan_v": 0}, "bed_heater": {"bed_heater_ohm": "open", "bed_actual_c": 23},
 "bed_thermistor": {"bed_thermistor_ohm": "open"}, "bed_thermal_fuse": {"bed_heater_ohm": "open", "bed_actual_c": 23},
 "power_supply": {"psu_v": 21.0, "rail_5v_v": 4.6}, "hotend_fan": {"fan_v": 24.0}, "part_cooling_fan": {"fan_v": 24.0},
 "controller_board": {"fan_v": 0}, "extruder_gears_guidler": {"extrude_act_mm": 62}, "extruder_motor": {"extrude_act_mm": 5},
 "nozzle": {"extrude_act_mm": 30}, "heatbreak_ptfe": {"extrude_act_mm": 40}, "xy_belts": {"belt_a_hz": 82, "belt_b_hz": 112},
 "xy_pulleys_idlers": {"axis_act_mm": 96.5}, "xy_motors_drivers": {"axis_act_mm": 97.0}, "z_motor_leadscrew": {"axis_name": "z", "axis_act_mm": 96.0},
 "slicer_settings": {"print_speed_mms": 250, "layer_height_mm": 0.3, "line_width_mm": 0.5}, "firmware_config_macros": {"extrude_act_mm": 120},
}

def words(t): return set(re.findall(r"[a-z]{4,}", t.lower()))

def answer(cid, f, qid, sim=None):
    """What a technician at a printer with this fault would answer. Returns (facts, measurements) or None (don't know).
    sim = (facts, measurements) observed in the digital twin for this fault (heat and power parts), used first."""
    q = Q[qid]
    if sim is not None:
        so, sm = sim
        if q["kind"] == "fields":
            m = {}
            for fld in q["fields"]:
                k = fld["key"]; v = sm.get(k, FAULTY.get(cid, {}).get(k, HEALTHY.get(k)))
                if v is None: return None
                m[k] = v
            return {}, m
        if q["kind"] == "choice" and q["slot"] in so: return {q["slot"]: so[q["slot"]]}, {}
        if qid == "error": return {"error_message": so.get("error_message", "none")}, {}
    if q["kind"] == "fields":
        m = {}
        for fld in q["fields"]:
            k = fld["key"]; v = FAULTY.get(cid, {}).get(k, HEALTHY.get(k))
            if v is None: return None
            m[k] = v
        return {}, m
    if q["kind"] == "text":
        if qid == "error":
            hit = [p for p, ids, _ in eng.ERRORS if cid in ids]
            return {"error_message": hit[0] if hit else "none"}, {}
        if qid == "change": return {"recent_change": "nothing"}, {}
        return None
    O = R.opts(qid); slot = q["slot"]; text = words(f["mode"] + " " + f["symptom"])
    listed = [o for o in O if cid in EVIDENCE.get((slot, o), [])] or [o for o in O if cid in R.WIDE.get((slot, o), [])]
    if listed: return {slot: max(listed, key=lambda o: len(words(o) & text))}, {}
    normal = [o for o in O if o in R.NORMAL]
    if normal: return {slot: normal[0]}, {}
    return None

# ---------- 3. one conversation -> training examples ----------------------------------------------------------
def context(case, hyps, cand):
    return lead_context(case, hyps, cand, E.KG, Q, compact_text)

def chain(cid, f, case):
    path = next((E._graph.path(cid, s) for s in E.mentioned(" ".join(case["notes"])) if s != cid and E._graph.path(cid, s)), "")
    return (f"{E.short(E.NAME[cid])}: {f['mode']}. This gives: {f['symptom']}." + (f" The fault travels along {E.readable(path)}." if path else ""))

def ask_message(hyps, qids):
    top = [E.short(h["name"]) for h in hyps[:2] if h["p"] >= 0.05]
    lead = (f"It could be the {top[0]}" + (f" or the {top[1]}" if len(top) > 1 else "") + ". ") if top else ""
    return lead + ("This answer tells them apart." if len(qids) == 1 else "These answers tell them apart.")

def converse(cid, f, opener, max_turns=6, use_twin=True):
    case = E.new_case(); case["notes"] = [opener]
    seed = sum(map(ord, opener)) % 10_000
    sim = TWIN.run_case(cid if cid in TWIN.COVERED else None, seed=seed) if use_twin else None   # physics-based answers
    case["facts"].update(keyword_facts(opener)); good, _ = validate_measurements(rule_extract(opener)); case["measurements"].update(good)
    lead, path = [], []
    for _ in range(max_turns + 2):
        calcs = eng.run(case["measurements"]) + eng.context(case["facts"], case["notes"])
        base, why = E.hypotheses(case, calcs)
        P = R.posterior(base, case["facts"], list(E.KG)); hyps = E.ranked_hyps(P, why)
        top = max(P, key=P.get)
        step, info = R.next_step(case, P, E.evidence_count(case) > 0 or bool(E.mentioned(opener)))
        cand = R.rank_questions(case, P, top if P[top] >= 0.5 else None)[:6]
        if step == "diagnose" and top != cid:      # engine would conclude wrongly: the teacher asks one more question instead
            alt = [c["id"] for c in cand if c["id"] not in case["asked_ids"]]
            if not alt or case["rounds"] >= max_turns: return lead, "unresolved"
            step, info = "ask", alt[:1]
        if step == "diagnose":
            lead.append((context(case, hyps, cand), {"action": "diagnose", "question_ids": [], "cause": cid,
                         "message": chain(cid, f, case), "evidence": [w for w in hyps[0]["why"] if not w.startswith("matches")][:3]}))
            return lead, "solved"
        if not info or info == ["what"]: return lead, "unresolved"
        lead.append((context(case, hyps, cand), {"action": "ask", "question_ids": info, "cause": "", "message": ask_message(hyps, info)}))
        for qid in info:
            case["asked_ids"].append(qid); a = answer(cid, f, qid, sim)
            if a is None: case["dont_know"].append(qid); continue
            facts, meas = a; case["facts"].update(facts); g, _ = validate_measurements(meas); case["measurements"].update(g)
        case["rounds"] += 1
    return lead, "unresolved"

def reading_target(cid, f, opener):
    neigh = [e["src"] for e in E._graph.inc.get(cid, []) if e["src"] not in E.SETTINGS][:2] + \
            [e["dst"] for e in E._graph.out.get(cid, []) if e["dst"] in E.KG][:1]
    cands = [{"id": cid, "p": 0.6, "why": f"{f['mode']} gives {symptom_clauses(f)[0] if symptom_clauses(f) else f['symptom']}"}]
    for n in neigh:
        if n != cid and n not in [c["id"] for c in cands]:
            p = E._graph.path(n, cid) or E._graph.path(cid, n)
            cands.append({"id": n, "p": round(0.4 / max(1, len(neigh)), 2), "why": f"connected: {E.readable(p)}" if p else "connected part"})
    return {"candidates": cands}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--per-fault", type=int, default=10); ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--paraphrase", action="store_true"); ap.add_argument("--no-twin", action="store_true")
    ap.add_argument("--twin", choices=["full", "heat"], default="full", help="full = virtual printer, all parts (v3); heat = stage 1 only (v2)"); a = ap.parse_args()
    global TWIN; TWIN = TWIN_FULL if a.twin == "full" else TWIN_HEAT
    from config import OLLAMA_URL, STUB
    if not STUB:
        import urllib.request
        try: urllib.request.urlopen(OLLAMA_URL + "/api/tags", timeout=5).read()
        except Exception: raise SystemExit("Ollama is not running. Start the Ollama app (Start menu), wait 10 seconds, then run this again.")
    rnd = random.Random(a.seed); E._load(); OUT.mkdir(parents=True, exist_ok=True)
    E.FT_MODEL = ""; E.USE_AGENT_PRIOR = False; E.LEAD_MODEL = False     # rules and simulation only
    import time; t0 = time.time()
    faults = fault_list()
    rnd.shuffle(faults); n_val = max(1, round(0.15 * len(faults)))
    val_ids = {(c, i) for c, i, _ in faults[:n_val]}
    para = json.loads((OUT / "paraphrases.json").read_text()) if (OUT / "paraphrases.json").exists() else {}
    suffix = "" if a.no_twin else ("_v3" if a.twin == "full" else "_v2")
    files = {"train": open(OUT / f"train{suffix}.jsonl", "w", encoding="utf-8"), "val": open(OUT / f"val{suffix}.jsonl", "w", encoding="utf-8")}
    stats = {"faults": len(faults), "val_faults": n_val, "conversations": 0, "solved": 0, "lead_examples": 0, "read_examples": 0}
    for n, (cid, i, f) in enumerate(faults, 1):
        split = "val" if (cid, i) in val_ids else "train"
        print(f"[{n}/{len(faults)}] {cid}: {f['mode'][:50]} ({split})  {time.time() - t0:.0f} s", flush=True)
        ops = openers(cid, f, rnd, a.per_fault)
        if a.paraphrase: ops += paraphrase(cid, f, para, OUT)
        for op in ops:
            ex = []
            sr = [d["id"] for d in E._index.search(op, 8)]
            ex.append({"messages": [{"role": "system", "content": SYSTEM_READ},
                                    {"role": "user", "content": read_context(op, sr, E.KG, compact_text)},
                                    {"role": "assistant", "content": json.dumps(reading_target(cid, f, op))}], "meta": {"part": cid, "mode": i, "role": "reading"}})
            lead, outcome = converse(cid, f, op, use_twin=not a.no_twin)
            for ctx, tgt in lead:
                ex.append({"messages": [{"role": "system", "content": SYSTEM_LEAD}, {"role": "user", "content": ctx},
                                        {"role": "assistant", "content": json.dumps(tgt)}], "meta": {"part": cid, "mode": i, "role": "lead"}})
            stats["conversations"] += 1; stats["solved"] += outcome == "solved"
            stats["lead_examples"] += len(lead); stats["read_examples"] += 1
            for e in ex: files[split].write(json.dumps(e) + "\n")
    for fh in files.values(): fh.close()
    (OUT / f"stats{suffix}.json").write_text(json.dumps(stats, indent=1)); print(json.dumps(stats, indent=1))

def paraphrase(cid, f, cache, out):
    """Optional: 8 natural rewordings of the symptom from the local model, cached (offline, free)."""
    key = f"{cid}|{f['mode']}"
    if key not in cache:
        from assistant_v2.llm import ask_json
        r = ask_json("You write how real 3D-printer owners describe faults in chat: short, informal, sometimes vague, sometimes with typos. "
                     "Never name the faulty part. Return JSON {\"messages\": [8 strings]}.",
                     f"Fault symptom: {f['symptom']}. Write 8 different first messages a Voron 0.2 owner might type.", max_tokens=500) or {}
        cache[key] = [str(m) for m in (r.get("messages") or [])][:8]
        (out / "paraphrases.json").write_text(json.dumps(cache, indent=1))
    return cache[key]

if __name__ == "__main__":
    main()
