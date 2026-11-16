"""Prompt control of the virtual printer: a sentence -> checked actions on the simulation.

Examples
  "set the nozzle to 210 C and print at 200 mm/s"      -> set nozzle_temp=210, print_speed=200
  "loosen belt A to 70 Hz"                             -> set belt_a_hz=70
  "make the hotend fan fail" / "clog the nozzle badly" -> fault hotend_fan / nozzle (severity 0.8)
  "lower the nozzle by 0.1"                            -> set z_offset=-0.1
  "back to normal" / "reset"                           -> clear everything

How: the local model (Qwen in Ollama) turns the sentence into JSON actions. A rule parser does the same for clear
sentences and is used when the model is off (STUB) or returns nothing. Every action is checked here: unknown parts or
settings are dropped and values are clamped to safe ranges (SETTINGS in virtual_printer.py), so the model can never
put the simulation into an impossible state.
"""
import re, json
try:
    from .virtual_printer import SETTINGS, PARTS, MODES, clean_settings
except ImportError:
    from virtual_printer import SETTINGS, PARTS, MODES, clean_settings

SYN = {   # words a technician uses -> part id (checked in order, first match wins)
 "thermal fuse": "bed_thermal_fuse", "fuse": "bed_thermal_fuse", "bed thermistor": "bed_thermistor", "bed heater": "bed_heater", "heat pad": "bed_heater",
 "hotend thermistor": "hotend_thermistor", "thermistor": "hotend_thermistor", "heater cartridge": "hotend_heater", "hotend heater": "hotend_heater", "heater": "hotend_heater",
 "nozzle": "nozzle", "heatbreak": "heatbreak_ptfe", "ptfe": "heatbreak_ptfe", "heat creep": "hotend_fan",
 "extruder motor": "extruder_motor", "pancake": "extruder_motor", "guidler": "extruder_gears_guidler", "extruder gear": "extruder_gears_guidler", "drive gear": "extruder_gears_guidler",
 "hotend fan": "hotend_fan", "heatsink fan": "hotend_fan", "part fan": "part_cooling_fan", "part cooling": "part_cooling_fan", "blower": "part_cooling_fan",
 "driver": "xy_motors_drivers", "xy motor": "xy_motors_drivers", "a/b motor": "xy_motors_drivers", "belt": "xy_belts", "pulley": "xy_pulleys_idlers", "idler": "xy_pulleys_idlers",
 "x rail": "x_linear_rail", "y rail": "y_linear_rails", "toolhead": "toolhead", "lead screw": "z_motor_leadscrew", "leadscrew": "z_motor_leadscrew", "z motor": "z_motor_leadscrew",
 "z rail": "z_rails", "endstop": "z_endstop", "z switch": "z_endstop", "bed level": "bed_plate_carrier", "bed screw": "bed_plate_carrier", "build plate": "bed_plate_carrier",
 "board": "controller_board", "mcu": "controller_board", "skr": "controller_board", "umbilical": "umbilical_wiring", "toolhead cable": "umbilical_wiring",
 "power supply": "power_supply", "psu": "power_supply", "raspberry": "host_computer", "pi ": "host_computer", "host": "host_computer",
 "runout": "filament_runout_sensor", "config": "firmware_config_macros", "firmware": "firmware_config_macros", "macro": "firmware_config_macros",
 "slicer": "slicer_settings", "filament": "filament_material", "spool": "filament_material", "power cord": "mains_power_input", "mains": "mains_power_input",
 "plug": "mains_power_input", "crimp": "dc_power_wiring", "24 v wire": "dc_power_wiring", "24v wire": "dc_power_wiring",
}
NUM = r"(-?\d+(?:\.\d+)?)"
RULES = [  # (regex, setting key, transform)
 (r"(?:nozzle|hotend|print(?:ing)?)\s*temp\w*\D{0,15}" + NUM, "nozzle_temp", float), (r"nozzle\D{0,12}" + NUM + r"\s*(?:°|c\b|deg)", "nozzle_temp", float),
 (r"bed\s*(?:temp\w*)?\D{0,12}" + NUM + r"\s*(?:°|c\b|deg)", "bed_temp", float), (r"bed\s*temp\w*\D{0,12}" + NUM, "bed_temp", float),
 (r"first\s*layer\s*speed\D{0,12}" + NUM, "first_layer_speed", float),
 (r"(?:print\w*\s*)?speed\D{0,12}" + NUM, "print_speed", float), (r"(?:at|to)\s*" + NUM + r"\s*mm/s\b", "print_speed", float),
 (r"layer\s*height\D{0,12}" + NUM, "layer_height", float), (r"line\s*width\D{0,12}" + NUM, "line_width", float),
 (r"accel\w*\D{0,12}" + NUM, "max_accel", float),
 (r"belt\s*a\D{0,20}" + NUM + r"\s*hz", "belt_a_hz", float), (r"belt\s*b\D{0,20}" + NUM + r"\s*hz", "belt_b_hz", float),
 (r"z[\s-]*offset\D{0,12}" + NUM, "z_offset", float), (r"rotation[_\s]*distance\D{0,12}" + NUM, "e_rotation_distance", float),
 (r"(?:motor|xy)\s*current\D{0,12}" + NUM, "xy_current", float),
]
FAULT_WORDS = re.compile(r"\b(fail|fails|failing|broken|break|dead|stop working|clog|clogged|loose|loosen|worn|bad|faulty|damaged|wet|tangled|blown|slip|binding|bind|jam|kill|disconnect|unplug|weak|simulate)\b", re.I)

def rule_parse(text):
    t = " " + text.lower().replace("°", " c ") + " "; acts = []
    if re.search(r"\b(reset|back to normal|healthy|fix (it|everything)|undo all|clear)\b", t): return [{"type": "reset"}]
    for rx, key, fn in RULES:
        m = re.search(rx, t)
        if m and not any(a.get("key") == key for a in acts): acts.append({"type": "set", "key": key, "value": fn(m.group(1))})
    # relative wording without numbers
    if "lower the nozzle" in t or "nozzle closer" in t or "more squish" in t:
        m = re.search(NUM, t); acts.append({"type": "set", "key": "z_offset", "value": -abs(float(m.group(1))) if m else -0.1})
    if "raise the nozzle" in t or "nozzle higher" in t or "less squish" in t:
        m = re.search(NUM, t); acts.append({"type": "set", "key": "z_offset", "value": abs(float(m.group(1))) if m else 0.1})
    if re.search(r"loose\w*\s+(both\s+)?belts?|belts?\s+(are\s+)?loose", t) and not any(a.get("key", "").startswith("belt") for a in acts):
        acts.append({"type": "fault", "part": "xy_belts", "severity": 0.75})
    if FAULT_WORDS.search(t) and not acts:
        part = next((pid for w, pid in SYN.items() if w in t), None)
        if part:
            sev = 0.85 if re.search(r"\b(badly|completely|totally|fully|very|severe)\b", t) else 0.3 if re.search(r"\b(slightly|a bit|little|mild)\b", t) else 0.6
            acts.append({"type": "fault", "part": part, "severity": sev})
    if re.search(r"\b(run|print|start|show me)\b", t): acts.append({"type": "run"})
    return acts

SYSTEM = """You control a SIMULATED Voron 0.2 3D printer. Turn the user's sentence into JSON actions. Allowed actions:
{"type":"set","key":<setting>,"value":<number>}    settings: %s
{"type":"fault","part":<part id>,"severity":<0.2-0.95>}   part ids: %s
{"type":"clear_fault"}  {"type":"reset"}  {"type":"run"}
Rules: use only these keys and part ids; numbers in the units given; if the sentence asks for nothing you can do, return no actions.
Return JSON only: {"actions":[...], "reply":"one short sentence saying what you changed"}"""

def model_parse(text):
    from assistant_v2.llm import ask_json
    keys = "; ".join(f"{k} ({u}, {lo}-{hi}: {d})" for k, (_, lo, hi, u, d) in SETTINGS.items())
    r = ask_json(SYSTEM % (keys, ", ".join(PARTS)), text, max_tokens=250) or {}
    return r.get("actions") or [], r.get("reply") or ""

def check(actions):
    """Drop anything unknown and clamp values: the model can only do what the simulation allows."""
    ok = []
    for a in actions if isinstance(actions, list) else []:
        if not isinstance(a, dict): continue
        t = a.get("type")
        if t == "set" and a.get("key") in SETTINGS:
            v = clean_settings({a["key"]: a.get("value")})
            if v: ok.append({"type": "set", "key": a["key"], "value": v[a["key"]]})
        elif t == "fault" and a.get("part") in PARTS:
            try: sev = min(0.95, max(0.2, float(a.get("severity", 0.6))))
            except (TypeError, ValueError): sev = 0.6
            ok.append({"type": "fault", "part": a["part"], "severity": sev})
        elif t in ("clear_fault", "reset", "run"): ok.append({"type": t})
    return ok

def validate(actions):
    """Like check(), but a setting outside its range is NOT clamped: it is rejected with the allowed range, so the user can correct it."""
    ok, rejected = [], []
    for a in actions if isinstance(actions, list) else []:
        if isinstance(a, dict) and a.get("type") == "set" and a.get("key") in SETTINGS:
            _, lo, hi, unit, label = SETTINGS[a["key"]]
            try: val = float(a.get("value"))
            except (TypeError, ValueError): continue
            if val < lo or val > hi: rejected.append({"key": a["key"], "value": val, "min": lo, "max": hi, "unit": unit, "label": label}); continue
            ok.append({"type": "set", "key": a["key"], "value": val})
        else: ok += check([a])
    return ok, rejected

def range_message(r):
    return f"{r['label'].capitalize()}: {r['value']:g} {r['unit']} is outside the allowed range. It should be between {r['min']:g} and {r['max']:g} {r['unit']}. Please check the value."

def settings_command(text, state, use_model=False):
    """For the repair assistant: only settings (no fault injection), with range checks. Returns {"actions", "rejected", "state", "reply"}."""
    acts = rule_parse(text)
    if not [a for a in acts if a.get("type") in ("set", "reset")] and use_model and re.search(r"\d", text):
        try: acts, _ = model_parse(text)
        except Exception: acts = []
    acts = [a for a in acts if isinstance(a, dict) and a.get("type") in ("set", "reset")]
    ok, rejected = validate(acts); st = apply(state, ok) if ok else state
    parts = []
    if ok: parts.append("Done: " + describe(ok) + ".")
    parts += [range_message(r) for r in rejected]
    return {"actions": ok, "rejected": rejected, "state": st, "reply": " ".join(parts)}

def apply(state, actions):
    st = {"fault": state.get("fault"), "severity": state.get("severity", 0.6), "settings": dict(state.get("settings") or {})}
    for a in actions:
        if a["type"] == "reset": st = {"fault": None, "severity": 0.6, "settings": {}}
        elif a["type"] == "clear_fault": st["fault"] = None
        elif a["type"] == "fault": st["fault"], st["severity"] = a["part"], a["severity"]
        elif a["type"] == "set": st["settings"][a["key"]] = a["value"]
    return st

def describe(actions):
    out = []
    for a in actions:
        if a["type"] == "set": k = SETTINGS[a["key"]]; out.append(f"{k[4]} = {a['value']:g} {k[3]}")
        elif a["type"] == "fault": out.append(f"fault in {a['part'].replace('_', ' ')} (severity {a['severity']:.2f})")
        elif a["type"] == "reset": out.append("everything back to the design values")
        elif a["type"] == "clear_fault": out.append("fault removed")
    return "; ".join(out)

def command(text, state, use_model=True):
    """Returns {"actions", "state", "reply", "by"}."""
    acts, reply, by = [], "", "rules"
    rules = check(rule_parse(text))
    if use_model:
        try: acts, reply = model_parse(text); acts = check(acts); by = "model"
        except Exception: acts = []
    if not acts: acts, by, reply = rules, "rules", ""
    if not acts: return {"actions": [], "state": state, "by": by,
                         "reply": "I could not turn that into a change. Try e.g. 'nozzle temperature 210', 'belt A 70 Hz', 'make the hotend fan fail', 'reset'."}
    return {"actions": acts, "state": apply(state, acts), "by": by, "reply": reply or ("Done: " + describe(acts) + ".")}

if __name__ == "__main__":
    for s in ["set the nozzle to 210 C and print at 200 mm/s", "loosen belt A to 70 Hz", "make the hotend fan fail", "clog the nozzle badly",
              "lower the nozzle by 0.1", "layer height 0.3, line width 0.6", "reset", "what is the weather"]:
        print(f"{s!r:55} -> {command(s, {}, use_model=False)['reply']}")
