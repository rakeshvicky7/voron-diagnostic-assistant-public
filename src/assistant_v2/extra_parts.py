"""Parts the 28-component evaluation model does not have, added for the chat assistant only.

The evaluation (arms A-G) keeps the original 28 components so its results stay comparable.
These three parts are in the BOM and the electrical documentation, and a technician can meet their faults:
the mains cord and inlet, the 24 V DC wiring and crimps, and the bed thermal fuse.
"""
BOM = "BOM voron0.2_bom.csv"
ELEC = "Documentation site: build/electrical"
EXTRA = {
 "mains_power_input": {
   "id": "mains_power_input", "name": "Mains power input (C13 power cord, IEC C14 inlet, AC wiring to the PSU)",
   "subsystem": "Electronics", "class": "wiring",
   "function": "Brings mains AC from the wall socket through the power cord and the IEC inlet to the 24 V power supply.",
   "parameters": [{"key": "power cord", "value": "C13 power cord", "source": f"{BOM}:34"},
                  {"key": "inlet", "value": "IEC320 C14 inlet", "source": f"{BOM}:35"},
                  {"key": "AC wire size", "value": ">= 18 AWG (0.75 mm2)", "source": f"{ELEC} (AC wiring should be properly dimensioned)"}],
   "connections": [],
   "failure_modes": [
     {"mode": "loose plug in the inlet or wall socket, worn cord, loose AC screw terminal",
      "symptom": "whole printer switches off or restarts, often with vibration or when the cord is touched; Pi and fans go off together",
      "check": "wiggle the cord and plug at the inlet with the printer idle; check the AC terminals on the PSU are tight"},
     {"mode": "undersized or damaged AC wire heating at the terminal",
      "symptom": "power drops after some minutes of heating; smell or discoloured terminal",
      "check": "look for discoloration at the inlet and PSU terminals; wire size >= 18 AWG"}],
   "related": ["mains_power_input powers power_supply"], "source": f"{BOM}:34-35; {ELEC}"},
 "dc_power_wiring": {
   "id": "dc_power_wiring", "name": "24 V DC power wiring and crimps (PSU to controller board)",
   "subsystem": "Electronics", "class": "wiring",
   "function": "Carries 24 V from the power supply to the controller board, which powers motors, heaters and fans.",
   "parameters": [{"key": "wire", "value": "18 gauge wire", "source": f"{BOM}:45"}],
   "connections": [],
   "failure_modes": [
     {"mode": "bad crimp or loose screw terminal on the 24 V input",
      "symptom": "board resets or drivers drop out (TMC errors, 'Lost communication') under load or vibration; Pi may stay on",
      "check": "tug-test each crimp; measure 24 V at the board input while heaters and motors run"}],
   "related": ["power_supply powers dc_power_wiring", "dc_power_wiring powers controller_board"],
   "source": f"{BOM}:45; {ELEC} ('Bad crimps are a major source of problems later on and sometimes hard to identify')"},
 "bed_thermal_fuse": {
   "id": "bed_thermal_fuse", "name": "Bed thermal fuse (150 °C)",
   "subsystem": "Bed", "class": "wiring",
   "function": "Safety fuse in series with the bed heater; it opens for good if the bed overheats.",
   "parameters": [{"key": "rating", "value": "150 C", "source": f"{BOM}:46"}],
   "connections": [],
   "failure_modes": [
     {"mode": "fuse opened (after an overheat or a weak fuse near its rating)",
      "symptom": "bed stops heating completely; bed heater resistance reads open although the pad looks fine",
      "check": "measure across the fuse: open = blown"}],
   "related": ["bed_thermal_fuse in_series_with bed_heater"], "source": f"{BOM}:46; {ELEC} (thermal fuse on the bed heater)"},
}
EDGES = [  # cause -> effect, same meaning as data/graph/graph.json
 ("mains_power_input", "power_supply", "powers"),
 ("power_supply", "dc_power_wiring", "powers"),
 ("dc_power_wiring", "controller_board", "powers"),
 ("bed_thermal_fuse", "bed_heater", "in_series_with"),
]
