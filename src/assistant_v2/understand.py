import os
"""Step 1 of every turn: is the input valid and about the Voron 0.2? What does it tell us?

check_input()  - fast rules: empty, gibberish, too long, other printers, clearly unrelated topics
understand()   - intent + facts + measurements (local model; rule-based extraction as fallback and in STUB mode)
"""
import re
from .questions import Q, SLOTS, KEYS, RANGE
from .llm import ask_json, STUB

PRINTER_WORDS = set("""voron v0 printer print printing prints printed nozzle hotend hot end extruder extrude extrusion extruding filament spool bed plate
heater heating heat thermistor sensor temperature temp fan fans cooling blower belt belts pulley idler rail rails gantry toolhead head carriage motor motors
stepper steppers driver drivers tmc z x y axis homing home endstop klipper mainsail fluidd moonraker mcu pi raspberry skr pico board controller
psu power supply voltage wire wires wiring cable umbilical connector layer layers shift shifting clog clogged clogging jam jammed under over stringing
warping warp adhesion first squish slicer gcode macro config cfg pid ptfe heatbreak heatsink gears gear guidler clicking grinding skipping pla petg abs asa
tpu error adc runout leak leaking blob blobs retraction flow speed acceleration resonance ringing ghosting tramming level leveling probe
overhang overhangs bridge bridges bridging droop droops sag sags ghost ghosts echo echoes ringing shaper input accelerometer adxl squish band bands
banding walls wall corners corner details cube seam zits elephant curling lines""".split())
OTHER_MACHINES = ["washing machine", "dishwasher", "fridge", "refrigerator", "car", "bike", "phone", "laptop", "television", "tv",
                  "air conditioner", "microwave", "oven", "cnc", "drone", "computer printer", "paper printer", "office printer", "inkjet", "laser printer", "ink", "toner", "paper jam",
                  "hp printer", "epson", "canon", "brother printer", "ender", "prusa", "bambu", "creality", "anycubic", "elegoo", "artillery", "sovol", "qidi", "flashforge", "ultimaker",
                  "voron 2", "v2.4", "trident", "switchwire", "voron 1", "legacy", "x1c", "p1s", "p1p", "k1 max", "cr-10", "mk3", "mk4", "a1 mini"]
SMALLTALK = re.compile(r"^\s*(how are you|how r u|who are you|what are you|what can you do|what'?s up|are you there|"
                       r"good (morning|afternoon|evening|night)|nice|great|cool|ok(ay)?|thanks?( you)?|bye)\b[\s\w,!?.]{0,25}$", re.I)
GREET = re.compile(r"^\s*(hi|hello|hey|good (morning|afternoon|evening)|thanks?|thank you|ok(ay)?|cool)\b[\s!.]*$", re.I)
WORD = re.compile(r"[a-zA-Z]+")

def check_input(text, expecting_answer=False):
    """Returns (kind, message) for input that must be rejected, or (None, None) if it can be processed."""
    t = (text or "").strip()
    if not t: return "empty", "Please type a message describing the problem with your Voron 0.2."
    if len(t) > 4000: return "too_long", "That message is very long. Please describe the problem in a few sentences (under 4000 characters)."
    words = WORD.findall(t.lower())
    has_num = bool(re.search(r"\d", t))
    if not words and not has_num: return "invalid", "I couldn't read that. Please describe what your Voron 0.2 is doing, in words."
    if words:
        vowelless = sum(1 for w in words if len(w) > 3 and not re.search(r"[aeiouy]", w))
        long_junk = sum(1 for w in words if len(w) > 18)
        repeats = bool(re.search(r"(.)\1{5,}", t))
        if (vowelless + long_junk) / len(words) > 0.5 or repeats and len(words) < 4:
            return "invalid", "That doesn't look like a description I can use. Please describe in normal words what the printer is doing."
    low = t.lower()
    for m in OTHER_MACHINES:
        if re.search(r"\b" + re.escape(m) + r"\b", low) and "0.2" not in low and "v0" not in low:
            return "other_machine", (f"It sounds like you are asking about a different printer ({m}). I only know the design documents of the "
                                     "**Voron 0.2**, so my answers would not be reliable for other machines. If your problem is on a Voron 0.2, please describe it.")
    return None, None

import difflib
def _has_printer_words(t):
    words = set(WORD.findall(t.lower()))
    if words & PRINTER_WORDS: return True
    # tolerate typing mistakes ("preinter", "extuder", "nozle")
    return any(difflib.get_close_matches(w, PRINTER_WORDS, n=1, cutoff=0.8) for w in words if len(w) >= 5)

# ---------------------------------------------------------------------------------------------------------
NUM = r"(\d+(?:[.,]\d+)?)"
def _f(x): return float(x.replace(",", "."))
def _near(t, i, words, back=45):
    seg = t[max(0, i - back):i].lower(); return any(w in seg for w in words)

def rule_extract(text):
    """Small rule-based extractor for numbers with units. Used in STUB mode and to fill gaps the model left."""
    t = text; low = t.lower(); m = {}
    for mt in re.finditer(NUM + r"\s*(?:°\s*c|º\s*c|deg(?:rees?)?\s*c?|c\b|celsius)", low):
        val = _f(mt.group(1)); i = mt.start()
        pre = "bed" if _near(low, i, ["bed"]) else "hotend"
        if _near(low, i, ["target", "set to", "set at", "should be", "set it to", "aim"], 30): m.setdefault(f"{pre}_target_c", val)
        elif _near(low, i, ["room", "ambient"], 25): m.setdefault("room_c", val)
        elif _near(low, i, ["swing", "fluctuat", "±", "+/-", "jumps by", "varies by"], 30): m.setdefault("hotend_swing_c", val)
        elif _near(low, i, ["slicer", "print at", "printing at"], 30): m.setdefault("print_temp_c", val)
        else: m.setdefault(f"{pre}_actual_c", val)
    for mt in re.finditer(NUM + r"\s*(k|m)?\s*(?:ohms?|Ω)", low):
        val = _f(mt.group(1)) * {"k": 1e3, "m": 1e6}.get(mt.group(2) or "", 1); i = mt.start()
        if _near(low, i, ["thermistor", "sensor"]): m.setdefault("bed_thermistor_ohm" if _near(low, i, ["bed"]) else "hotend_thermistor_ohm", val)
        elif _near(low, i, ["bed"]): m.setdefault("bed_heater_ohm", val)
        elif _near(low, i, ["heater", "cartridge"]): m.setdefault("hotend_heater_ohm", val)
    for mt in re.finditer(r"(thermistor|heater)[^.,;]{0,40}?\b(ol|open|infinite|no continuity)\b", low):
        bed = _near(low, mt.start(), ["bed"], 15)
        key = ("bed_" if bed else "hotend_") + ("thermistor_ohm" if mt.group(1) == "thermistor" else "heater_ohm")
        m.setdefault(key, "open")
    for mt in re.finditer(NUM + r"\s*v\b", low):
        val = _f(mt.group(1)); i = mt.start()
        if _near(low, i, ["5v", "5 v", "pi ", "raspberry", "5-volt"]) or val < 7: m.setdefault("rail_5v_v", val)
        elif _near(low, i, ["fan"]): m.setdefault("fan_v", val)
        else: m.setdefault("psu_v", val)
    hz = [_f(x) for x in re.findall(NUM + r"\s*hz", low)]
    if hz: m.setdefault("belt_a_hz", hz[0])
    if len(hz) > 1: m.setdefault("belt_b_hz", hz[1])
    sp = re.search(NUM + r"\s*mm/s", low)
    if sp: m.setdefault("print_speed_mms", _f(sp.group(1)))
    lh = re.search(NUM + r"\s*mm\s*(?:layer|layer height)|layer height\s*(?:of|=|:)?\s*" + NUM, low)
    if lh: m.setdefault("layer_height_mm", _f(lh.group(1) or lh.group(2)))
    if re.search(r"extru|feed|fed|pull", low):
        mm = [_f(x) for x in re.findall(NUM + r"\s*mm\b(?!/)", low)]
        if len(mm) >= 2: m.setdefault("extrude_cmd_mm", mm[0]); m.setdefault("extrude_act_mm", mm[1])
    return m

# phrases -> answers, so a technician who already said it is not asked again (used with and without the model)
KEYWORD_SLOTS = [
 ("surface", r"ringing|ghosting|ripples?", "Ringing / ghosting (ripples after corners)"),
 ("surface", r"skew|not square|out of square", "Skewed: squares are not square"),
 ("surface", r"string(s|ing|y)|bubbl|popp", "Stringing, rough or bubbly surface"),
 ("surface", r"overhangs? (droop|sag)|droop|corners? curl|curl(ing|ed)? corners", "Drooping overhangs, curled corners"),
 ("surface", r"\bblobs?\b|over.?extru", "Blobs, too much plastic"),
 ("surface", r"z.?banding|wavy (layer|lines)|uneven layer lines", "Wavy or uneven layer lines (Z banding)"),
 ("when", r"after (the |printing the )?(1st|first) layer", "Right after the first layer"),
 ("when", r"(only )?when (the )?(head|toolhead|it) (moves|is moving)|while moving", "Only when the head moves"),
 ("when", r"(while|during|when) (the )?(bed |hotend |printer |it )?(is )?heat(s|ing)?( up)?", "Only while heating"),
 ("when", r"after (some|a few|\d+) min", "After some minutes of printing"),
 ("problem_kind", r"\b(printer|print|printing|it|machine|everything|voron)\b[^.]{0,25}\b(stops?|stopped|dies|died)\b|\b(switch(es|ed)? off|turns? off|turned off|shuts? (down|off)|restarts?|reboots?|power(s|ed)? (off|down)|goes dead)\b", "The printer stops, switches off or restarts"),
 ("problem_kind", r"\b(error|klipper shutdown|shutdown)\b", "An error message / Klipper shutdown"),
 ("problem_kind", r"no plastic|nothing comes out|under.?extru|clog|blob|leak", "Plastic problem (none, too little, blobs, leaks)"),
 ("problem_kind", r"layer shift|shifted|crash|grinding|skipping", "Movement problem (layer shift, noise, crash)"),
 ("problem_kind", r"temperature|\btemp\b|thermal|won'?t heat|not heat|overheat", "Temperature problem"),
 ("temp_behaviour", r"(temp\w*|reading)[^.]{0,40}(drops?|jumps?|spikes?) (suddenly|randomly)|suddenly (drops?|jumps?|spikes?)", "Jumps suddenly (spikes or drops)"),
 ("stop_type", r"(everything|all|lights?|screen|pi|fans?) (goes|went|go|turns?|turned|switch(es|ed)?) (off|dark|out)|power(s|ed)? off|switch(es|ed)? off|turn(s|ed)? off|went off|goes off|shut off|loses power|lost power|no power|is (turned |switched )?off|won'?t (turn|switch|power) on|does ?n[o']?t (turn|switch|power) on|is dead", "Everything goes off: lights, fans, Raspberry Pi"),
 ("restart", r"won'?t (turn|switch|power) (back )?on|does ?n[o']?t (turn|switch|power) (back )?on|stays? off|is dead|no power at all", "Stays off even when I switch it on"),
 ("stop_type", r"lost communication|mcu (error|disconnect)|pi stays on", "The Pi stays on, but motors and heaters stop ('Lost communication' / MCU error)"),
 ("stop_type", r"\bpaus(e|es|ed)\b", "The print just pauses"),
 ("restart", r"(comes|came|turns?) back on|restarts? (by )?itself|reboots? itself", "Comes back on by itself after a moment"),
 ("cord_wiggle", r"(wiggl|touch|mov)\w* (the )?(power )?(cord|plug|cable)[^.]{0,40}(off|flicker|reset|restart)", "Yes, it flickers or switches off"),
]
NEGATED = re.compile(r"(temperature|temp|reading|heat\w*)[^.,;]{0,25}\b(looks?|is|seems?|stays?|are)\s+(normal|fine|ok|okay|stable|steady|correct)")

def keyword_facts(text):
    low = text.lower(); out = {}
    low = NEGATED.sub(" ", low)          # "the hotend temperature looks normal" is not a temperature problem
    for slot, pat, opt in KEYWORD_SLOTS:
        if slot not in out and re.search(pat, low): out[slot] = opt
    return out

def _match_option(slot, value):
    opts = next((q["options"] for q in Q.values() if q.get("slot") == slot and "options" in q), None)
    if not opts: return str(value).strip() or None
    v = str(value).strip().lower()
    for o in opts:
        if v == o.lower() or v in o.lower() or o.lower() in v: return o
    return None

SYSTEM = """You are the input-understanding step of a diagnostic assistant for ONE machine: the Voron 0.2 3D printer.
Read the technician's latest message (and the questions that were just asked) and return JSON only.
intent: one of
  "fault_report"  - describes a problem or symptom with the printer
  "answer"        - answers the assistant's previous questions
  "info_question" - asks a factual question about the Voron 0.2 (a value, a part, how something works) without reporting a fault
  "greeting"      - greeting, thanks, small talk
  "off_topic"     - not about the Voron 0.2 or 3D printing at all
  "other_machine" - about a different printer model
facts: only slots you can fill from the message; choice slots MUST use one of the given options exactly.
measurements: numbers the message states, using only the given keys; use "open" for an open circuit/OL and "short" for 0 ohm.
dont_know: ids of asked questions the technician says they cannot answer.
Never invent values that are not in the message."""

PROBLEM = re.compile(r"\b(not|n't|no|won'?t|doesn'?t|stops?|stopped|fail\w*|error|problem|issue|broken|wrong|clog\w*|jam\w*|shift\w*|noise|click\w*|"
                     r"grind\w*|under|over|leak\w*|drops?|jumps?|spikes?|stuck|slow|hot|cold|burn\w*|smell)\b", re.I)
INFO_Q = re.compile(r"^\s*(what|which|how (much|many|big|long|hot)|where|is the|does the|what's)\b", re.I)
def looks_like_info_question(text):
    return bool(INFO_Q.match(text)) and text.strip().endswith("?") and not PROBLEM.search(text) and _has_printer_words(text)

YES = re.compile(r"^\s*(yes|yeah|yep|y|it does|correct)\b", re.I); NO = re.compile(r"^\s*(no|nope|n|it doesn'?t|not really)\b", re.I)
def quick_answer(text, pending):
    """Map a short reply ('yes', 'the LED is off', 'only when the head moves') to the pending question, or None."""
    if not pending or len(text.split()) > 12: return None
    low = text.lower().strip(" .!"); facts = {}
    for qid in pending:
        q = Q.get(qid, {})
        if q.get("kind") != "choice": continue
        best = None
        for o in q["options"]:
            ol = o.lower()
            if low == ol or (len(low) >= 4 and (low in ol or ol in low)): best = o; break
        if best is None and (YES.match(low) or NO.match(low)):
            yes_opt = next((o for o in q["options"] if o.lower().startswith("yes")), None)
            no_opt = next((o for o in q["options"] if o.lower().startswith("no")), None)
            best = yes_opt if YES.match(low) else no_opt
        if best: facts[q["slot"]] = best
    meas = rule_extract(text)
    if not facts and not meas: return None
    return {"intent": "answer", "facts": facts, "measurements": meas, "dont_know": []}

# Who reads the technician's free text: "rules" (keywords only), "hybrid" (keywords first, the model fills gaps), "model"
READER = os.environ.get("READER", "rules")   # development step 5: the keyword reader beat Qwen on the dev set (63 % vs 55 % top-1)

def understand(text, case):
    """Returns {"intent", "facts", "measurements", "dont_know"}."""
    pending = [qid for qid in case.get("pending", [])]
    rules = rule_extract(text)
    if STUB or READER == "rules":     # keyword reader only (deterministic; also used offline)
        intent = ("greeting" if GREET.match(text) else
                  "smalltalk" if SMALLTALK.match(text) and not quick_answer(text, pending) else
                  "info_question" if looks_like_info_question(text) and not pending else
                  "answer" if pending and (len(text.split()) < 12 or rules) else
                  "fault_report" if _has_printer_words(text) or rules else "off_topic")
        facts = {}
        if intent in ("fault_report", "answer") and len(text.split()) >= 3: facts["what_happens"] = text.strip()
        if re.search(r"\b(error|adc|mcu|lost communication|unable to connect)\b", text.lower()): facts["error_message"] = text.strip()
        for k, val in keyword_facts(text).items(): facts.setdefault(k, val)
        low = text.lower()
        for (slot, opt) in [(s, o) for q in Q.values() if q.get("slot") for s, o in [(q["slot"], o) for o in q.get("options", [])]]:
            if len(opt) >= 12 and re.search(r"\b" + re.escape(opt.lower()) + r"\b", low) and slot not in facts: facts[slot] = opt
        dk = pending[:] if re.search(r"\b(don'?t know|not sure|no idea)\b|\b(can'?t|cannot|canont|cant|unable to)\b.{0,25}\b(check|measure|read|see|test)", low) else []
        return {"intent": intent, "facts": facts, "measurements": rules, "dont_know": dk}
    if GREET.match(text):   # "hello", "thanks": no need to ask the model
        return {"intent": "greeting", "facts": {}, "measurements": {}, "dont_know": []}
    if SMALLTALK.match(text) and not quick_answer(text, pending):
        return {"intent": "smalltalk", "facts": {}, "measurements": {}, "dont_know": []}
    # fast path: a short reply to the question just asked is matched directly, without the model (instant)
    quick = quick_answer(text, pending)
    if quick is not None: return quick
    # shorter prompt = faster: only the slots of the questions just asked plus the main triage slots
    want = {Q[q]["slot"] for q in pending if "slot" in Q[q]} | {"problem_kind", "when", "stop_type", "error_message", "recent_change", "onset"}
    slot_desc = []
    for q in Q.values():
        if "slot" in q and q["slot"] in want and q["slot"] not in [s.split(":")[0] for s in slot_desc]:
            slot_desc.append(f'{q["slot"]}: ' + (" | ".join(q["options"]) if "options" in q else "free text"))
    asked = "\n".join(f'- {qid}: {Q[qid]["text"]}' for qid in pending) or "- none"
    user = f"""Questions just asked:
{asked}
Fact slots (choice options separated by |):
{chr(10).join(slot_desc)}
what_happens: free text summary of the observed problem
Measurement keys: {", ".join(KEYS)}
Technician message: \"\"\"{text}\"\"\"
Return JSON: {{"intent": "...", "facts": {{}}, "measurements": {{}}, "dont_know": []}}"""
    r = ask_json(SYSTEM, user, max_tokens=250) or {}
    intent = r.get("intent") if r.get("intent") in ("fault_report", "answer", "info_question", "greeting", "off_topic", "other_machine") else None
    if intent is None: intent = "greeting" if GREET.match(text) else "info_question" if looks_like_info_question(text) else ("answer" if pending else ("fault_report" if _has_printer_words(text) else "off_topic"))
    # a model can call a short printer message off-topic; printer words in the text win
    if intent == "off_topic" and (_has_printer_words(text) or rules): intent = "answer" if pending else "fault_report"
    # overnight test: the model called plain fault statements "info_question" or "greeting" (12 of 58 cases lost).
    # A message is only a question if it reads like one, and only a greeting if it is one.
    if intent == "info_question" and not looks_like_info_question(text): intent = "answer" if pending else "fault_report"
    if intent == "greeting" and not GREET.match(text): intent = "answer" if pending else "fault_report"
    facts = {}
    for k, val in (r.get("facts") or {}).items():
        if k in SLOTS or k == "what_happens":
            mv = _match_option(k, val) if k in SLOTS else str(val).strip()
            if mv and k in ("filament", "recent_change", "error_message", "what_happens") and any(
                    str(val).strip() in q.get("options", []) for q in Q.values()): mv = None   # model put a button answer in a text slot
            if mv and mv.lower() not in ("none", "null", "unknown", ""): facts[k] = mv
    for k, val in keyword_facts(text).items():
        if READER == "hybrid": facts[k] = val          # clear keywords win over the model's reading; the model fills the rest
        else: facts.setdefault(k, val)
    meas = {}
    for k, val in (r.get("measurements") or {}).items():
        if k in KEYS and val not in (None, "", "null"): meas[k] = val
    for k, val in rules.items(): meas.setdefault(k, val)
    dk = [q for q in (r.get("dont_know") or []) if q in Q]
    if re.search(r"\b(don'?t know|not sure|no idea|no multimeter)\b|\b(can'?t|cannot|canont|cant|unable to|not able to)\b.{0,25}\b(check|measure|read|see|test)", text.lower()) and not dk: dk = pending[:]
    return {"intent": intent, "facts": facts, "measurements": meas, "dont_know": dk}

def validate_measurements(meas):
    """Split into (good, bad). Bad = not a number or outside the plausible range (likely a typing mistake)."""
    good, bad = {}, {}
    for k, val in meas.items():
        if k == "axis_name":
            if str(val).strip().lower() in ("x", "y", "z"): good[k] = str(val).strip().lower()
            continue
        if isinstance(val, str) and val.strip().lower() in ("open", "ol", "short"):
            good[k] = "open" if val.strip().lower() in ("open", "ol") else "short"; continue
        try: x = float(str(val).replace(",", "."))
        except ValueError: bad[k] = val; continue
        lo, hi = RANGE.get(k, (-1e12, 1e12))
        if lo <= x <= hi: good[k] = x
        else: bad[k] = val
    return good, bad
