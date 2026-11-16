"""Scripted conversations to check the assistant's behaviour. Run from the agent folder:
    py -3.12 -m src.assistant_v2.test_scenarios          (real model; Ollama must be running)
    $env:STUB="1"; py -3.12 -m src.assistant_v2.test_scenarios   (rules only, no model)
Each scenario prints what the assistant did, so you can check it against the expected behaviour."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from assistant_v2 import engine as E

SCENARIOS = [
 ("vague single statement -> must ask, not guess", ["my nozzle is not working"], {}),
 ("gibberish -> ask for valid input", ["asdkjh qwrtz xcvbnm"], {}),
 ("empty", [""], {}),
 ("off topic", ["what is the capital of France?"], {}),
 ("other printer", ["my ender 3 bed is not heating"], {}),
 ("greeting", ["hello"], {}),
 ("info question", ["what is the rotation distance of the extruder?"], {}),
 ("detailed description", ["The hotend heats to 215 C but during printing the temperature suddenly drops to 150 C and comes back, "
                           "only when the head moves. No error message. I re-routed the toolhead cable last week."], {}),
 ("vague, then structured answers", ["no plastic comes out of the nozzle", None],
  {1: {"facts": {"flow_state": "Nothing at all", "motor_behaviour": "Clicks / jumps back"}, "measurements": {"hotend_target_c": "210", "hotend_actual_c": "209"}}}),
 ("measurements in free text", ["bed does not heat", "the bed heater measures 9.8 ohm and the bed thermistor is open"], {}),
 ("impossible number -> re-check", ["extruder under extrudes", None], {1: {"measurements": {"extrude_cmd_mm": "100", "extrude_act_mm": "5000"}}}),
 ("calculation decides", ["under extrusion on every print", None], {1: {"measurements": {"extrude_cmd_mm": "100", "extrude_act_mm": "62"},
                                                                       "facts": {"motor_behaviour": "Gears turn but filament does not move"}}}),
]

def show(rep):
    t = rep["type"]
    print(f"   -> {t}", rep.get("kind", ""), "|", (rep.get("text") or rep.get("intro") or "")[:220].replace("\n", " "))
    if t == "questions": print("      asks:", [q["id"] for q in rep["questions"]])
    if t == "diagnosis":
        d = rep["diagnosis"]; print("      CAUSE:", d["cause"], f"({d['confidence']})", "| alternatives:", [a["id"] for a in d["alternatives"]])
    if rep.get("calcs"): print("      calcs:", [(k["id"], k["result"], k["verdict"]) for k in rep["calcs"]])
    if rep.get("hyps"): print("      hypotheses:", [(h["id"], h["score"]) for h in rep["hyps"][:4]])

# simulated technician: answers each question from a hidden "truth" (the faulty part's observations)
SIMULATED = [
 ("loose mains plug", "loose", "My printer stops after printing the first layer", "mains_power_input",
  {"stop_type": "Everything goes off: lights, fans, Raspberry Pi", "cord_wiggle": "Yes, it flickers or switches off", "restart": "Comes back on by itself after a moment"}, {}),
 ("bad 24 V crimp", "", "My printer stops after printing the first layer", "dc_power_wiring",
  {"stop_type": "The Pi stays on, but motors and heaters stop ('Lost communication' / MCU error)", "mcu_state": "Disconnects / 'Lost communication' during prints"}, {}),
 ("runout sensor false trigger", "", "My printer stops after printing the first layer", "filament_runout_sensor",
  {"stop_type": "The print just pauses", "runout_check": "It says runout, but there IS filament at the sensor"}, {}),
 ("weak power supply", "", "my printer switches off while the bed is heating up", "power_supply",
  {"cord_wiggle": "No change", "restart": "Stays off until I switch it on again", "other_load": "No"}, {"psu_v": "21.2", "rail_5v_v": "5.0"}),
 ("nozzle clog", "", "my nozzle is not working", "nozzle",
  {"problem_kind": "Plastic problem (none, too little, blobs, leaks)", "flow_state": "Nothing at all", "motor_behaviour": "Clicks / jumps back", "temp_behaviour": "Steady at target", "fan_state": "Yes, always"}, {}),
]

def simulate(first, truth_facts, truth_meas, limit=10):
    from assistant_v2.questions import Q
    c = E.new_case(); r = E.turn(c, first)["reply"]; asked = []
    while r["type"] == "questions" and len(asked) < limit:
        form = {"facts": {}, "measurements": {}, "dont_know": []}
        for q in r["questions"]:
            asked.append(q["id"]); qq = Q.get(q["id"], {})
            if qq.get("slot") in truth_facts: form["facts"][qq["slot"]] = truth_facts[qq["slot"]]
            elif qq.get("kind") == "fields" and any(f["key"] in truth_meas for f in qq["fields"]):
                form["measurements"] = {f["key"]: truth_meas[f["key"]] for f in qq["fields"] if f["key"] in truth_meas}
            else: form["dont_know"].append(q["id"])
        r = E.turn(c, None, form)["reply"]
    return r, asked

if __name__ == "__main__":
    print("\n##### Simulated technician (counts the questions needed)")
    ok = 0
    for name, _, first, truth, facts, meas in SIMULATED:
        r, asked = simulate(first, facts, meas)
        got = r.get("diagnosis", {}).get("cause"); ok += got == truth
        print(f"   {name:28s} truth={truth:24s} named={got} ({r.get('diagnosis', {}).get('p')})  questions={len(asked)} {asked}  {'OK' if got == truth else 'WRONG'}")
    print(f"   correct: {ok}/{len(SIMULATED)}")
    for name, msgs, forms in SCENARIOS:
        print(f"\n=== {name}"); c = E.new_case()
        for i, m in enumerate(msgs):
            print("   user:", m if m is not None else f"[form] {forms.get(i)}")
            show(E.turn(c, m, forms.get(i))["reply"])
