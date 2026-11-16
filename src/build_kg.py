"""Build data/kg/kg.json: one card per component combining the hand-written component list,
the automatic parameters/connections from the config, and template-derived failure modes.
Run: python src/build_kg.py  (after extract_config.py)
"""
import json, pathlib, runpy
A = pathlib.Path(__file__).resolve().parents[1]
COMP = runpy.run_path(str(A / "data/kg/components.yaml.py"))["COMPONENTS"]
params = json.loads((A / "data/kg/parameters.json").read_text())
conns = json.loads((A / "data/kg/connections.json").read_text())

# Fixed FMEA-style template per component class (design knowledge, applied uniformly)
FAILURE_TEMPLATES = {
 "heater": [("no or weak heating (open circuit, loose cartridge, failed output)", "slow or no heat-up, 'not heating at expected rate' error, cold prints", "watch temperature graph during heat-up; measure resistance; check cartridge clamped"),
            ("control or limit setting wrong (PID, max_temp)", "temperature oscillates or printer shuts down at high temperature", "compare PID/max_temp with stock config; re-run PID_CALIBRATE")],
 "sensor": [("open or shorted sensor / wiring", "'ADC out of range' or absurd reading, shutdown", "check connector and wiring; measure resistance at room temperature"),
            ("wrong sensor configuration (type, pullup, trigger threshold)", "reading offset from real value or false/no trigger", "compare sensor_type/pullup/threshold with hardware and docs"),
            ("intermittent contact or loose mount", "spikes, drops or drifting reference between runs", "wiggle test while watching readings; check mount rigidity")],
 "motor":  [("wrong setting (direction, rotation_distance, current, stall threshold)", "moves wrong way, wrong distance, skipped steps or bad homing", "compare config values with stock and calibrate"),
            ("insufficient torque or driver fault", "skipping/clicking under load or at high acceleration", "raise current within limits; check driver temperature and wiring")],
 "fan":    [("fan not spinning (failed fan, wiring/polarity, wrong pin)", "fan stops or stutters; overheating of what it cools", "command fan to 100%; swap with known good fan/port; check polarity")],
 "mechanical_drive": [("loose, slipping or worn transmission", "layer shifts, dimensional error, slipping or under-feeding", "check tension/grub screws/wear; mark and observe slip"),
            ("misalignment or binding", "periodic artefacts, noise, uneven motion", "move by hand with motors off; check alignment")],
 "guide":  [("play or low preload", "toolhead/bed rocks; height or position varies across the plate", "push gently and look for play; replace with preloaded rail"),
            ("binding or misalignment", "periodic lines, extra load on motor", "move by hand; re-align and lubricate")],
 "passive_flow": [("partial or full blockage", "thin, gappy lines; extruder clicks", "cold pull; extrude in air and watch flow"),
            ("gap or mismatch in filament path", "leaks, stringing, intermittent jams", "re-seat tube/nozzle; check fittings")],
 "structure": [("not rigid, loose or not level", "uneven first layer, ringing, height varies by position", "check fasteners and tramming; press test")],
 "electronics": [("power or connection fault", "board does not start, disconnects mid-print", "check supply voltages, connectors, jumpers, USB link"),
            ("configuration/jumper mismatch", "Klipper config error or a function never triggers", "compare jumpers and pins with wiring docs")],
 "wiring": [("intermittent or swapped conductors in connectors", "several toolhead functions cut out together; fans/thermistor erratic", "re-seat connectors; continuity and wiggle test; check pinout")],
 "software": [("setting or macro inconsistent with this machine", "errors such as move out of range, refusing to extrude, unexpected pauses or artefacts", "read the error; compare macro/limits with machine size and stock config")],
 "material": [("material condition out of spec (moisture, diameter)", "popping, stringing, rough surfaces", "dry filament; measure diameter")],
}
# Mechanical / electrical links between components (from the assembly manual and wiring docs)
RELATIONS = [
 ("hotend_heater","controlled_by","hotend_thermistor"), ("hotend_heater","wired_through","umbilical_wiring"),
 ("hotend_thermistor","wired_through","umbilical_wiring"), ("hotend_fan","wired_through","umbilical_wiring"),
 ("part_cooling_fan","wired_through","umbilical_wiring"), ("extruder_motor","wired_through","umbilical_wiring"),
 ("extruder_motor","drives","extruder_gears_guidler"), ("extruder_gears_guidler","feeds","heatbreak_ptfe"),
 ("heatbreak_ptfe","feeds","nozzle"), ("hotend_fan","cools","heatbreak_ptfe"), ("part_cooling_fan","cools","nozzle"),
 ("xy_motors_drivers","drives","xy_belts"), ("xy_belts","runs_over","xy_pulleys_idlers"), ("xy_belts","moves","toolhead"),
 ("toolhead","guided_by","x_linear_rail"), ("x_linear_rail","carried_by","y_linear_rails"),
 ("z_motor_leadscrew","moves","bed_plate_carrier"), ("bed_plate_carrier","guided_by","z_rails"), ("z_endstop","references","z_motor_leadscrew"),
 ("bed_heater","controlled_by","bed_thermistor"), ("bed_heater","mounted_on","bed_plate_carrier"),
 ("controller_board","drives","xy_motors_drivers"), ("controller_board","drives","z_motor_leadscrew"), ("controller_board","powers","bed_heater"),
 ("umbilical_wiring","connects_to","controller_board"), ("power_supply","powers","controller_board"), ("power_supply","powers","host_computer"),
 ("host_computer","talks_to","controller_board"), ("filament_runout_sensor","triggers","firmware_config_macros"),
 ("firmware_config_macros","configures","controller_board"),
]
cards = {}
for cid, c in COMP.items():
    P = [p for p in params if p["section"] in c["cfg"] and (not c["keys"] or p["key"] in c["keys"])]
    K = [x for x in conns if x["component"] in c["cfg"] and (not c["keys"] or x["role"] in c["keys"])]
    cards[cid] = {"id": cid, "name": c["name"], "subsystem": c["subsystem"], "class": c["cls"], "function": c["function"],
                  "parameters": [{"key": f'[{p["section"]}] {p["key"]}', "value": p["value"], "source": p["source"]} for p in P],
                  "connections": [{"role": x["role"], "board_pin": x["board_pin"], "source": x["source"]} for x in K],
                  "failure_modes": [{"mode": m, "symptom": s, "check": ch} for m, s, ch in FAILURE_TEMPLATES[c["cls"]]],
                  "related": [f"{a} {r} {b}" for a,r,b in RELATIONS if cid in (a,b)], "source": c["src"]}
(A / "data/kg/kg.json").write_text(json.dumps(cards, indent=1), encoding="utf-8")
print(len(cards), "component cards;", sum(len(v["parameters"]) for v in cards.values()), "parameters linked;",
      sum(len(v["connections"]) for v in cards.values()), "pin connections;", sum(len(v["failure_modes"]) for v in cards.values()), "failure modes")
