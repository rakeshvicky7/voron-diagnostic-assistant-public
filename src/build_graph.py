"""Build the failure-propagation graph for arm G (graph RAG).

Nodes  = the 28 components of the structured model (same ids as the cards, so the answer space is unchanged).
Edges  = directed CAUSE -> EFFECT links: "a fault in <src> can show its symptom at <dst>".
         Each edge has a relation type (how the fault travels) and a source.
         - Board-pin edges are derived automatically from the firmware configuration (connections.json).
         - Configuration edges are derived automatically: every component with values in the config
           depends on the firmware configuration.
         - Physical, wiring, thermal and power edges are typed by hand from the assembly manual and
           the documentation site, as the relations of the cards were.
Nothing from the test set is used.

Run: python src/build_graph.py   (after extract_config.py and build_kg.py)
Output: data/graph/graph.json and data/graph/graph_edges.csv (for checking each edge against its source)
"""
import json, csv, pathlib, runpy
A = pathlib.Path(__file__).resolve().parents[1]
COMP = runpy.run_path(str(A / "data/kg/components.yaml.py"))["COMPONENTS"]
kg = json.loads((A / "data/kg/kg.json").read_text(encoding="utf-8"))
conns = json.loads((A / "data/kg/connections.json").read_text())
OUT = A / "data/graph"; OUT.mkdir(parents=True, exist_ok=True)

edges = []
def add(src, dst, rel, source, how):
    assert src in COMP and dst in COMP, (src, dst)
    if not any(e["src"] == src and e["dst"] == dst and e["rel"] == rel for e in edges):
        edges.append({"src": src, "dst": dst, "rel": rel, "source": source, "how": how})

# 1) Automatic: every pin in the config gives "controller_board -> component" (the board drives / reads it).
for x in conns:
    for cid, c in COMP.items():
        if x["component"] in c["cfg"] and (not c["keys"] or x["role"] in c["keys"]):
            rel = "reads_signal_of" if c["cls"] == "sensor" else "drives"
            add("controller_board", cid, rel, x["source"], "automatic (config pin)")

# 2) Automatic: every component with configured values depends on the firmware configuration.
for cid, card in kg.items():
    if card["parameters"] and cid != "firmware_config_macros":
        src = card["parameters"][0]["source"]
        add("firmware_config_macros", cid, "configures", src, "automatic (config values)")

# 3) By hand, from the assembly manual and the documentation site.
M = "VORON_V0.2r1_Assembly_Manual.pdf"
HAND = [
 # power and communication
 ("power_supply", "controller_board", "powers", "Documentation site: build/electrical (24 V supply to controller)"),
 ("power_supply", "host_computer", "powers", "Documentation site: build/electrical (5 V supply to Raspberry Pi)"),
 ("host_computer", "controller_board", "commands", "Documentation site: build/software (Klipper host talks to the MCU over USB)"),
 ("controller_board", "umbilical_wiring", "feeds", f"{M} p.188 (toolhead wiring routed from the motor plate)"),
 # toolhead cable: every toolhead function runs through it
 ("umbilical_wiring", "hotend_heater", "carries_power_to", f"{M} p.188 (heater wires routed in the umbilical)"),
 ("umbilical_wiring", "hotend_thermistor", "carries_signal_of", f"{M} p.188 (thermistor wires routed in the umbilical)"),
 ("umbilical_wiring", "hotend_fan", "carries_power_to", f"{M} p.188 (hotend fan wires routed in the umbilical)"),
 ("umbilical_wiring", "part_cooling_fan", "carries_power_to", f"{M} pp.187-188 (toolhead wire routing)"),
 ("umbilical_wiring", "extruder_motor", "carries_power_to", f"{M} pp.187-188 (toolhead wire routing)"),
 # XY motion chain
 ("xy_motors_drivers", "xy_pulleys_idlers", "turns", "Assembly manual: motion (CoreXY A/B motors with pulleys)"),
 ("xy_pulleys_idlers", "xy_belts", "drives", "Assembly manual: motion (belt path over pulleys and idlers)"),
 ("xy_belts", "toolhead", "moves", "Assembly manual: motion (belts clamp to the toolhead)"),
 ("x_linear_rail", "toolhead", "guides", "Assembly manual: gantry (toolhead on the X rail)"),
 ("y_linear_rails", "x_linear_rail", "carries", "Assembly manual: gantry (X rail carried by the Y rails)"),
 # Z axis and bed
 ("z_motor_leadscrew", "bed_plate_carrier", "moves", "Assembly manual: Z axis (lead screw lifts the bed carrier)"),
 ("z_rails", "bed_plate_carrier", "guides", "Assembly manual: Z axis (bed carrier on the Z rails)"),
 ("z_endstop", "z_motor_leadscrew", "references_homing_of", "Documentation site: build/startup (Z homes to the endstop)"),
 ("bed_thermistor", "bed_heater", "controls", "Config [heater_bed]: heater controlled from the bed sensor"),
 ("bed_heater", "bed_plate_carrier", "heats", "Assembly manual: bed (heater mounted on the bed plate)"),
 # extrusion chain
 ("extruder_motor", "extruder_gears_guidler", "drives", "Assembly manual: print head (motor drives the drive gears)"),
 ("extruder_gears_guidler", "heatbreak_ptfe", "feeds_filament_to", "Assembly manual: print head (filament path)"),
 ("heatbreak_ptfe", "nozzle", "feeds_filament_to", "Assembly manual: print head (filament path)"),
 ("filament_material", "extruder_gears_guidler", "feeds", "Slicer profiles / documentation site: filament path"),
 ("filament_material", "nozzle", "flows_through", "Slicer profiles / documentation site: filament path"),
 # thermal
 ("hotend_thermistor", "hotend_heater", "controls", "Config [extruder]: heater controlled from the hotend sensor"),
 ("hotend_heater", "nozzle", "heats", "Assembly manual: print head (heater block holds the nozzle)"),
 ("hotend_fan", "heatbreak_ptfe", "cools", "Documentation site: build/startup (heatsink fan prevents clogging)"),
 ("part_cooling_fan", "nozzle", "cools_output_of", "Documentation site: slicer/first print (part cooling)"),
 # sensors and settings
 ("filament_runout_sensor", "firmware_config_macros", "triggers", "Config [filament_switch_sensor] (pause on runout)"),
 ("slicer_settings", "nozzle", "commands_flow_and_temperature_of", "Slicer profiles (temperatures, flow, retraction)"),
 ("slicer_settings", "part_cooling_fan", "commands", "Slicer profiles (fan speeds)"),
 ("slicer_settings", "toolhead", "commands_motion_of", "Slicer profiles (speeds, accelerations)"),
 ("toolhead", "nozzle", "carries", "Assembly manual: print head (hotend mounted in the toolhead)"),
]
for s, d, r, src in HAND: add(s, d, r, src, "by hand")

nodes = {cid: {"id": cid, "name": c["name"], "class": c["cls"], "subsystem": c["subsystem"]} for cid, c in COMP.items()}
(OUT / "graph.json").write_text(json.dumps({"nodes": nodes, "edges": edges}, indent=1), encoding="utf-8")
with open(OUT / "graph_edges.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, delimiter=";"); w.writerow(["cause (src)", "relation", "effect (dst)", "how obtained", "source", "checked (Y/N)"])
    for e in edges: w.writerow([e["src"], e["rel"], e["dst"], e["how"], e["source"], ""])
auto = sum(e["how"].startswith("automatic") for e in edges)
print(f"{len(nodes)} nodes, {len(edges)} edges ({auto} automatic, {len(edges) - auto} by hand)")
