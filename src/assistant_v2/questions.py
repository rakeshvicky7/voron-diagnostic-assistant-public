"""Question bank: the information the assistant may need, as structured questions.

kind "choice": pick one option (fills a fact slot)
kind "fields": numeric fields with units (fill measurement keys used by engineering.run)
kind "text":   free text (fills a fact slot)
helps: the components whose fault this question can confirm or rule out. It is used to choose questions
       that separate the current hypotheses (a question that helps all or none of them separates nothing).
how:   one short line on how to get the value (only to collect information, not a repair step).
"""
HOT = ["hotend_heater", "hotend_thermistor", "nozzle", "heatbreak_ptfe", "hotend_fan", "umbilical_wiring"]
EXT = ["extruder_motor", "extruder_gears_guidler", "nozzle", "heatbreak_ptfe", "filament_material", "slicer_settings"]
XY = ["xy_motors_drivers", "xy_belts", "xy_pulleys_idlers", "x_linear_rail", "y_linear_rails", "toolhead"]
ELEC = ["controller_board", "power_supply", "host_computer", "umbilical_wiring"]
Z = ["z_motor_leadscrew", "z_rails", "z_endstop", "bed_plate_carrier"]
BED = ["bed_heater", "bed_thermistor", "bed_plate_carrier"]

Q = {
 # ---- context, always useful -----------------------------------------------------------------------------
 "what": {"kind": "text", "slot": "what_happens", "text": "What exactly do you see or hear when the problem happens?",
          "hint": "e.g. no plastic comes out, the head stops, a clicking sound, a number on the screen", "helps": [], "generic": True},
 # ---- triage: one click that splits the whole machine into areas ---------------------------------------
 "kind": {"kind": "choice", "slot": "problem_kind", "text": "Which of these is closest to the problem?", "helps": [],
          "options": ["The printer stops, switches off or restarts", "An error message / Klipper shutdown", "Plastic problem (none, too little, blobs, leaks)",
                      "Movement problem (layer shift, noise, crash)", "Temperature problem", "First layer / bed problem"]},
 "stop_type": {"requires": {"problem_kind": ["The printer stops, switches off or restarts", "An error message / Klipper shutdown"]}, "kind": "choice", "slot": "stop_type", "text": "When it stops, what exactly happens?", "helps": [],
               "options": ["Everything goes off: lights, fans, Raspberry Pi", "The Pi stays on, but motors and heaters stop ('Lost communication' / MCU error)",
                           "Klipper shows an error and shuts down", "The print just pauses", "The head keeps moving but no plastic comes out"]},
 "restart": {"requires": {"stop_type": ["Everything goes off: lights, fans, Raspberry Pi"]}, "sens": 0.5, "kind": "choice", "slot": "restart", "text": "After it goes off, what does it do?", "helps": [],
             "options": ["Comes back on by itself after a moment", "Stays off until I switch it on again", "Stays off even when I switch it on"]},
 "cord_wiggle": {"requires": {"stop_type": ["Everything goes off: lights, fans, Raspberry Pi"]}, "sens": 0.7, "kind": "choice", "slot": "cord_wiggle", "text": "With the printer on and idle, gently wiggle the power cord at the back where it plugs in. Does it flicker or switch off?",
                 "helps": [], "options": ["Yes, it flickers or switches off", "No change", "I can't reach it"]},
 "psu_led": {"requires": {"stop_type": ["Everything goes off: lights, fans, Raspberry Pi"]}, "kind": "choice", "slot": "psu_led",
             "text": "Look at the power supply in the electronics bay (no need to touch anything). Is its small green LED lit?", "helps": [],
             "options": ["Yes, the LED is on", "No, the LED is off", "I can't see it"]},
 "runout_check": {"requires": {"stop_type": ["The print just pauses"]}, "kind": "choice", "slot": "runout_check",
                  "text": "When it pauses, what does the web interface say, and is there filament at the sensor?", "helps": [],
                  "options": ["It says runout, but there IS filament at the sensor", "The filament really ran out, broke or tangled", "No runout message; it pauses another way"]},
 "other_load": {"requires": {"stop_type": ["Everything goes off: lights, fans, Raspberry Pi"]}, "sens": 0.3, "kind": "choice", "slot": "other_load", "text": "Is anything else plugged into the same socket or extension lead (heater, kettle, another printer)?",
                "helps": [], "options": ["No", "Yes, and the problem happens when that device switches on", "Yes, but no link I can see"]},
 "when": {"sens": 0.6, "kind": "choice", "slot": "when", "text": "When does it happen?", "generic": True, "helps": ["umbilical_wiring", "hotend_fan", "filament_material"],
          "options": ["All the time", "Only while heating", "Only when the head moves", "Right after the first layer", "After some minutes of printing", "Randomly"]},
 "onset": {"kind": "choice", "slot": "onset", "text": "How did it start?", "generic": True, "helps": [],
           "options": ["Suddenly", "Got worse slowly", "Since I built the printer", "Right after I changed something"]},
 "change": {"sens": 0.5, "kind": "text", "slot": "recent_change", "text": "Did anything change before it started? (part replaced, maintenance, config edit, new filament, printer moved)",
            "hint": "write 'nothing' if nothing changed", "helps": ["firmware_config_macros", "slicer_settings", "filament_material"], "generic": True},
 "error": {"kind": "text", "slot": "error_message", "text": "Is there an error message in Mainsail/Fluidd or the console? Please copy it exactly.",
           "hint": "write 'none' if there is no message", "helps": ELEC + ["hotend_thermistor", "bed_thermistor", "hotend_heater", "z_endstop"], "generic": True},
 # ---- hotend / temperature ---------------------------------------------------------------------------------
 "hot_temp": {"kind": "fields", "text": "Hotend temperature in the web interface:", "helps": ["hotend_heater", "hotend_thermistor", "umbilical_wiring"],
              "fields": [{"key": "hotend_target_c", "label": "Target", "unit": "°C"}, {"key": "hotend_actual_c", "label": "Actual reading", "unit": "°C"}]},
 "hot_behaviour": {"kind": "choice", "slot": "temp_behaviour", "text": "How does the hotend temperature behave?", "helps": ["hotend_thermistor", "umbilical_wiring", "hotend_heater", "part_cooling_fan"],
                   "options": ["Steady at target", "Rises slowly / never reaches target", "Swings slowly up and down", "Jumps suddenly (spikes or drops)", "Drops when the part fan turns on"]},
 "hot_swing": {"kind": "fields", "text": "While holding temperature, how far does the reading move?", "helps": ["hotend_thermistor", "umbilical_wiring", "firmware_config_macros"],
               "fields": [{"key": "hotend_swing_c", "label": "Swing (±)", "unit": "°C"}]},
 "heater_r": {"kind": "fields", "text": "Resistance of the hotend heater cartridge (unplugged, printer off):", "helps": ["hotend_heater", "umbilical_wiring"],
              "how": "multimeter on the ohm range across the two heater wires", "fields": [{"key": "hotend_heater_ohm", "label": "Resistance", "unit": "Ω", "allow": ["open"]}]},
 "therm_r": {"kind": "fields", "text": "Resistance of the hotend thermistor at room temperature (unplugged):", "helps": ["hotend_thermistor", "umbilical_wiring"],
             "how": "multimeter across the two thermistor wires; write 'open' if it shows OL", "fields": [{"key": "hotend_thermistor_ohm", "label": "Resistance", "unit": "Ω", "allow": ["open", "short"]}, {"key": "room_c", "label": "Room temperature", "unit": "°C"}]},
 "hot_fan": {"kind": "choice", "slot": "fan_state", "text": "Is the hotend (heatsink) fan spinning when the hotend is above 50 °C?", "helps": ["hotend_fan", "umbilical_wiring", "heatbreak_ptfe"],
             "options": ["Yes, always", "No", "It stutters / stops sometimes", "I can't tell"]},
 "fan_v": {"kind": "fields", "text": "Voltage at the fan connector while the fan should run:", "helps": ["hotend_fan", "part_cooling_fan", "umbilical_wiring", "controller_board"],
           "fields": [{"key": "fan_v", "label": "Voltage", "unit": "V"}]},
 # ---- extrusion ----------------------------------------------------------------------------------------------
 "flow": {"kind": "choice", "slot": "flow_state", "text": "What comes out of the nozzle?", "helps": EXT + ["hotend_heater"],
          "options": ["Nothing at all", "Less than normal / gaps in lines", "Starts fine, then stops mid-print", "Normal amount but bad quality", "Leaks around the nozzle"]},
 "motor": {"kind": "choice", "slot": "motor_behaviour", "text": "What does the extruder motor do when it should push filament?", "helps": ["extruder_motor", "extruder_gears_guidler", "nozzle", "heatbreak_ptfe"],
           "options": ["Turns normally", "Clicks / jumps back", "Does not turn at all", "Hums but does not turn", "Gears turn but filament does not move"]},
 "e_test": {"kind": "fields", "text": "Extrusion test at printing temperature (heat the hotend, mark the filament, extrude a set length):",
            "helps": ["extruder_gears_guidler", "extruder_motor", "nozzle", "heatbreak_ptfe", "firmware_config_macros"],
            "how": "mark the filament 120 mm above the extruder, command 100 mm slowly, measure what was pulled in",
            "fields": [{"key": "extrude_cmd_mm", "label": "Commanded", "unit": "mm"}, {"key": "extrude_act_mm", "label": "Actually fed", "unit": "mm"}]},
 "filament": {"kind": "text", "slot": "filament", "text": "Which filament (material, brand) and how was it stored? Any popping or steam when it extrudes?",
              "helps": ["filament_material"], "hint": "e.g. PLA, open for 3 months, some popping"},
 "print_set": {"kind": "fields", "text": "Slicer settings for this print:", "helps": ["slicer_settings", "hotend_heater"],
               "fields": [{"key": "print_temp_c", "label": "Nozzle temperature", "unit": "°C"}, {"key": "print_speed_mms", "label": "Speed", "unit": "mm/s"},
                          {"key": "layer_height_mm", "label": "Layer height", "unit": "mm"}, {"key": "line_width_mm", "label": "Line width", "unit": "mm"}]},
 # ---- XY motion ----------------------------------------------------------------------------------------------
 "shift": {"kind": "choice", "slot": "shift_axis", "text": "In which direction does the problem show?", "helps": XY,
           "options": ["X only", "Y only", "Diagonal / both", "Not a shift problem"]},
 "noise": {"kind": "choice", "slot": "noise", "text": "Any unusual sound when the head moves?", "helps": XY + ["extruder_motor"],
           "options": ["No", "Grinding / scraping", "Clicking or thumping", "Squeaking", "Motor whine / buzz"]},
 "by_hand": {"kind": "choice", "slot": "move_by_hand", "text": "With motors off, does the head move smoothly by hand in X and Y?", "helps": ["x_linear_rail", "y_linear_rails", "xy_pulleys_idlers", "xy_belts"],
             "options": ["Smooth in both", "Rough or tight in X", "Rough or tight in Y", "Rough in both"]},
 "axis_test": {"kind": "fields", "text": "Movement test (command a move, measure the real distance):", "helps": ["xy_pulleys_idlers", "xy_motors_drivers", "xy_belts", "z_motor_leadscrew"],
               "fields": [{"key": "axis_name", "label": "Axis (X/Y/Z)", "unit": "", "text": True}, {"key": "axis_cmd_mm", "label": "Commanded", "unit": "mm"}, {"key": "axis_act_mm", "label": "Measured", "unit": "mm"}]},
 "belts": {"kind": "fields", "text": "Belt frequency when plucked (head at the back, 150 mm span; a tuner app works):", "helps": ["xy_belts"],
           "fields": [{"key": "belt_a_hz", "label": "Belt A", "unit": "Hz"}, {"key": "belt_b_hz", "label": "Belt B", "unit": "Hz"}]},
 # ---- Z / bed ----------------------------------------------------------------------------------------------------
 "z_home": {"kind": "choice", "slot": "z_home", "text": "What happens when Z homes?", "helps": Z,
            "options": ["Homes correctly", "Bed crashes / does not stop", "Stops too early", "Z does not move"]},
 "first_layer": {"kind": "choice", "slot": "first_layer", "text": "How does the first layer look?", "helps": Z + ["slicer_settings", "filament_material"],
                 "options": ["Good everywhere", "Too squished everywhere", "Too high / not sticking everywhere", "Good on one side, bad on the other", "Changes from print to print"]},
 "bed_temp": {"kind": "fields", "text": "Bed temperature in the web interface:", "helps": BED,
              "fields": [{"key": "bed_target_c", "label": "Target", "unit": "°C"}, {"key": "bed_actual_c", "label": "Actual reading", "unit": "°C"}]},
 "bed_r": {"kind": "fields", "text": "Resistance of the bed heater (unplugged, printer off):", "helps": ["bed_heater"],
           "fields": [{"key": "bed_heater_ohm", "label": "Resistance", "unit": "Ω", "allow": ["open"]}]},
 # ---- electronics --------------------------------------------------------------------------------------------------
 "mcu": {"kind": "choice", "slot": "mcu_state", "text": "Does the web interface stay connected to the printer?", "helps": ELEC,
         "options": ["Yes, always", "'MCU unable to connect' at start", "Disconnects / 'Lost communication' during prints", "The web page itself does not load"]},
 "wiggle": {"sens": 0.7, "kind": "choice", "slot": "wiggle", "text": "Does the problem change when you gently move the toolhead cable by hand (printer on, idle)?", "helps": ["umbilical_wiring", "hotend_thermistor", "hotend_fan"],
            "options": ["Yes, it appears or gets worse", "No change", "Did not try"]},
 "volts": {"kind": "fields", "text": "Supply voltages (multimeter, printer idle):", "helps": ["power_supply", "host_computer"],
           "fields": [{"key": "psu_v", "label": "24 V output", "unit": "V"}, {"key": "rail_5v_v", "label": "5 V rail", "unit": "V"}]},
 # ---- added in development step 2 (gaps found by the virtual printer) ------------------------------------------
 "surface": {"kind": "choice", "slot": "surface", "text": "What does the printed part look like?", "sens": 0.6,
             "helps": ["toolhead", "xy_belts", "filament_material", "slicer_settings", "part_cooling_fan", "firmware_config_macros", "z_motor_leadscrew"],
             "options": ["Looks fine", "Ringing / ghosting (ripples after corners)", "Skewed: squares are not square", "Stringing, rough or bubbly surface",
                         "Drooping overhangs, curled corners", "Blobs, too much plastic", "Wavy or uneven layer lines (Z banding)"]},
 "fuse_r": {"strength": 6, "kind": "choice", "slot": "fuse_state", "how": "printer off and unplugged; multimeter on the ohm range across the two fuse legs",
            "text": "Measure across the bed's 150 C thermal fuse (in series with the bed heater). What does it read?",
            "helps": ["bed_thermal_fuse", "bed_heater"], "options": ["About 0 ohm (closed)", "Open (OL)", "I can't reach it"]},
 "crimp_tug": {"strength": 3, "requires": {"problem_kind": ["An error message / Klipper shutdown", "The printer stops, switches off or restarts"]}, "kind": "choice", "slot": "crimp_tug", "sens": 0.7,
               "how": "printer on and idle; gently pull each 24 V wire where it enters the controller board",
               "text": "With the printer idle, gently tug the 24 V power wires at the controller board. Does the board reset or a light flicker?",
               "helps": ["dc_power_wiring", "controller_board", "power_supply"], "options": ["Yes, it resets or flickers", "No change", "Did not try"]},
 "board_seen": {"strength": 3, "requires": {"problem_kind": ["An error message / Klipper shutdown", "The printer stops, switches off or restarts"]}, "kind": "choice", "slot": "board_seen",
                "how": "Mainsail: Machine tab, or on the Pi: ls /dev/serial/by-id",
                "text": "Does the Raspberry Pi see the controller board (it is listed under /dev/serial/by-id or in Mainsail's machine page)?",
                "helps": ["controller_board", "host_computer", "dc_power_wiring"], "options": ["Yes, it is listed", "No, it is missing", "I can't check"]},
 "part_fan": {"kind": "choice", "slot": "part_fan_state", "text": "From layer 4 on, does the part cooling fan (blower on the side of the toolhead) spin?",
              "helps": ["part_cooling_fan", "umbilical_wiring", "slicer_settings"],
              "options": ["Yes, it spins", "No, it does not spin", "I can't tell"]},
 "which_temp": {"requires": {"problem_kind": ["An error message / Klipper shutdown", "Temperature problem"]}, "kind": "choice", "slot": "which_temp",
                "text": "In the temperature graph, which reading looks wrong before the stop?",
                "helps": ["hotend_heater", "hotend_thermistor", "bed_heater", "bed_thermistor", "bed_thermal_fuse", "umbilical_wiring"],
                "options": ["The hotend", "The bed", "Both", "Neither, both look normal"]},
}

# plausible ranges for numbers (a value outside is treated as a typing mistake and asked again)
RANGE = {"hotend_target_c": (0, 350), "hotend_actual_c": (-30, 400), "hotend_swing_c": (0, 300), "room_c": (-10, 50),
         "hotend_heater_ohm": (0, 1e7), "hotend_thermistor_ohm": (0, 1e8), "bed_target_c": (0, 150), "bed_actual_c": (-30, 200),
         "bed_heater_ohm": (0, 1e7), "bed_thermistor_ohm": (0, 1e8), "psu_v": (0, 40), "rail_5v_v": (0, 12), "fan_v": (0, 40),
         "extrude_cmd_mm": (1, 1000), "extrude_act_mm": (0, 1000), "axis_cmd_mm": (1, 300), "axis_act_mm": (0, 300),
         "belt_a_hz": (10, 500), "belt_b_hz": (10, 500), "print_speed_mms": (1, 1000), "layer_height_mm": (0.02, 1.0),
         "line_width_mm": (0.1, 2.0), "print_temp_c": (100, 350)}
KEYS = sorted(RANGE) + ["axis_name"]
SLOTS = sorted({q["slot"] for q in Q.values() if "slot" in q})

# What a choice answer points to. Derived from the failure modes on the component cards
# (each card lists "symptom" and "check"); this is the same knowledge, written as answer -> components.
EVIDENCE = {
 ("when", "Only when the head moves"): ["umbilical_wiring", "hotend_thermistor"],
 ("when", "After some minutes of printing"): ["heatbreak_ptfe", "hotend_fan", "extruder_motor"],
 ("when", "Only while heating"): ["hotend_heater", "hotend_thermistor", "bed_heater", "power_supply"],
 ("temp_behaviour", "Rises slowly / never reaches target"): ["hotend_heater", "part_cooling_fan", "power_supply"],
 ("temp_behaviour", "Swings slowly up and down"): ["firmware_config_macros"],   # PID tuning; a part-fan dip is the separate "drops when the part fan turns on"
 ("temp_behaviour", "Jumps suddenly (spikes or drops)"): ["hotend_thermistor", "umbilical_wiring"],
 ("temp_behaviour", "Drops when the part fan turns on"): ["part_cooling_fan", "hotend_heater"],
 ("fan_state", "No"): ["hotend_fan", "umbilical_wiring", "controller_board"],
 ("fan_state", "It stutters / stops sometimes"): ["hotend_fan", "umbilical_wiring"],
 ("flow_state", "Nothing at all"): ["nozzle", "heatbreak_ptfe", "extruder_gears_guidler", "hotend_heater"],
 ("flow_state", "Less than normal / gaps in lines"): ["extruder_gears_guidler", "nozzle", "slicer_settings", "filament_material"],
 ("flow_state", "Starts fine, then stops mid-print"): ["heatbreak_ptfe", "hotend_fan", "filament_material", "extruder_motor"],
 ("flow_state", "Leaks around the nozzle"): ["nozzle", "heatbreak_ptfe"],
 ("flow_state", "Normal amount but bad quality"): ["slicer_settings", "filament_material", "part_cooling_fan"],
 ("motor_behaviour", "Clicks / jumps back"): ["nozzle", "heatbreak_ptfe", "extruder_gears_guidler"],
 ("motor_behaviour", "Does not turn at all"): ["extruder_motor", "umbilical_wiring", "controller_board"],
 ("motor_behaviour", "Hums but does not turn"): ["extruder_motor", "umbilical_wiring"],
 ("motor_behaviour", "Gears turn but filament does not move"): ["extruder_gears_guidler", "filament_material"],
 ("shift_axis", "X only"): ["xy_pulleys_idlers", "x_linear_rail", "xy_belts"],
 ("shift_axis", "Y only"): ["xy_pulleys_idlers", "y_linear_rails", "xy_belts"],
 ("shift_axis", "Diagonal / both"): ["xy_motors_drivers", "xy_belts", "firmware_config_macros"],
 ("noise", "Grinding / scraping"): ["xy_pulleys_idlers", "x_linear_rail", "y_linear_rails"],
 ("noise", "Clicking or thumping"): ["xy_motors_drivers", "xy_belts"],
 ("noise", "Squeaking"): ["x_linear_rail", "y_linear_rails"],
 ("move_by_hand", "Rough or tight in X"): ["x_linear_rail", "xy_pulleys_idlers"],
 ("move_by_hand", "Rough or tight in Y"): ["y_linear_rails", "xy_pulleys_idlers"],
 ("move_by_hand", "Rough in both"): ["xy_pulleys_idlers", "xy_belts"],
 ("z_home", "Bed crashes / does not stop"): ["z_endstop"],
 ("z_home", "Stops too early"): ["z_endstop", "z_rails"],
 ("z_home", "Z does not move"): ["z_motor_leadscrew", "controller_board"],
 ("first_layer", "Good on one side, bad on the other"): ["bed_plate_carrier"],
 ("first_layer", "Changes from print to print"): ["z_endstop", "bed_plate_carrier"],
 ("first_layer", "Too squished everywhere"): ["z_endstop", "firmware_config_macros"],
 ("first_layer", "Too high / not sticking everywhere"): ["z_endstop", "filament_material", "bed_plate_carrier"],
 ("mcu_state", "'MCU unable to connect' at start"): ["controller_board", "host_computer", "firmware_config_macros"],
 ("mcu_state", "Disconnects / 'Lost communication' during prints"): ["host_computer", "power_supply", "controller_board"],
 ("mcu_state", "The web page itself does not load"): ["host_computer", "power_supply"],
 ("wiggle", "Yes, it appears or gets worse"): ["umbilical_wiring", "hotend_thermistor"],   # a fan that cuts out with cable movement is a cable fault
 # triage and power questions (failure modes of power_supply, mains_power_input, dc_power_wiring, controller_board, host_computer)
 ("problem_kind", "The printer stops, switches off or restarts"): ["mains_power_input", "power_supply", "dc_power_wiring", "host_computer", "controller_board", "filament_runout_sensor"],
 ("problem_kind", "An error message / Klipper shutdown"): ["controller_board", "hotend_thermistor", "bed_thermistor", "umbilical_wiring", "host_computer", "firmware_config_macros"],
 ("problem_kind", "Plastic problem (none, too little, blobs, leaks)"): ["nozzle", "heatbreak_ptfe", "extruder_gears_guidler", "extruder_motor", "filament_material", "slicer_settings"],
 ("problem_kind", "Movement problem (layer shift, noise, crash)"): ["xy_belts", "xy_pulleys_idlers", "xy_motors_drivers", "x_linear_rail", "y_linear_rails", "z_motor_leadscrew"],
 ("problem_kind", "Temperature problem"): ["hotend_heater", "hotend_thermistor", "bed_heater", "bed_thermistor", "bed_thermal_fuse", "part_cooling_fan"],
 ("problem_kind", "First layer / bed problem"): ["z_endstop", "bed_plate_carrier", "slicer_settings", "filament_material", "bed_heater"],
 ("stop_type", "Everything goes off: lights, fans, Raspberry Pi"): ["mains_power_input", "power_supply"],
 ("stop_type", "The Pi stays on, but motors and heaters stop ('Lost communication' / MCU error)"): ["dc_power_wiring", "controller_board", "host_computer"],
 ("stop_type", "Klipper shows an error and shuts down"): ["hotend_thermistor", "umbilical_wiring", "controller_board", "firmware_config_macros"],
 ("stop_type", "The print just pauses"): ["filament_runout_sensor", "filament_material", "firmware_config_macros"],
 ("stop_type", "The head keeps moving but no plastic comes out"): ["heatbreak_ptfe", "nozzle", "extruder_gears_guidler", "hotend_fan"],
 ("restart", "Comes back on by itself after a moment"): ["mains_power_input", "power_supply"],
 ("restart", "Stays off until I switch it on again"): ["power_supply", "mains_power_input"],
 ("restart", "Stays off even when I switch it on"): ["power_supply", "mains_power_input"],
 ("cord_wiggle", "Yes, it flickers or switches off"): ["mains_power_input"],
 ("cord_wiggle", "No change"): ["power_supply", "dc_power_wiring"],
 ("other_load", "Yes, and the problem happens when that device switches on"): ["mains_power_input", "power_supply"],
 ("psu_led", "No, the LED is off"): ["mains_power_input", "power_supply"],
 ("psu_led", "Yes, the LED is on"): ["dc_power_wiring", "power_supply", "host_computer"],
 ("runout_check", "It says runout, but there IS filament at the sensor"): ["filament_runout_sensor"],
 ("runout_check", "The filament really ran out, broke or tangled"): ["filament_material"],
 ("runout_check", "No runout message; it pauses another way"): ["firmware_config_macros", "slicer_settings"],
 ("when", "Right after the first layer"): ["umbilical_wiring", "mains_power_input", "dc_power_wiring", "xy_motors_drivers", "slicer_settings"],
}
# ---- Added in development step 2. Each link was missing from the table above; the virtual printer showed the symptom,
# and every addition is grounded in a document or a stated engineering reason (source given). Exported to
# eval/evidence_added.csv for the thesis.
EVIDENCE_ADDED = [
 (("motor_behaviour", "Clicks / jumps back"), ["hotend_fan", "extruder_motor", "slicer_settings"],
  "hotend_fan card (heat creep -> jam); Klipper: extruder skips when feed force > motor torque (weak/low-current motor, flow above melt rate)"),
 (("flow_state", "Less than normal / gaps in lines"), ["extruder_motor", "firmware_config_macros", "hotend_heater"],
  "extruder_motor card (missed steps); config [extruder] rotation_distance 22.23; melt rate falls with temperature (min_extrude_temp 170)"),
 (("flow_state", "Nothing at all"), ["slicer_settings", "extruder_motor"], "config min_extrude_temp 170 (cold extrusion blocked); open motor coil"),
 (("problem_kind", "Plastic problem (none, too little, blobs, leaks)"), ["hotend_fan", "part_cooling_fan", "firmware_config_macros"],
  "hotend_fan card (heat creep); part_cooling_fan card (overhang/bridge quality); config rotation_distance"),
 (("problem_kind", "First layer / bed problem"), ["z_rails", "z_motor_leadscrew", "bed_thermistor", "bed_heater", "toolhead"],
  "z_rails / z_motor_leadscrew cards (binding, lost Z steps); bed too cold for ABS (slicer bed 90-100 C); loose toolhead/nozzle height"),
 (("first_layer", "Changes from print to print"), ["z_rails", "z_motor_leadscrew", "toolhead"], "Z binding loses steps differently per homing; loose toolhead parts"),
 (("first_layer", "Too high / not sticking everywhere"), ["bed_heater", "bed_thermistor"], "slicer profile bed 100/90 C for ABS; a cold or mis-read bed stops adhesion"),
 (("problem_kind", "An error message / Klipper shutdown"), ["dc_power_wiring", "bed_thermal_fuse", "hotend_heater", "bed_heater", "z_endstop", "power_supply"],
  "Klipper verify_heater and MCU errors; documentation: bad crimps cause resets; thermal fuse in series with bed heater (BOM:46)"),
 (("stop_type", "Klipper shows an error and shuts down"), ["hotend_heater", "bed_heater", "bed_thermistor", "bed_thermal_fuse", "host_computer", "z_endstop"],
  "Klipper verify_heater ('not heating at expected rate'), ADC range check, homing errors ('Endstop still triggered')"),
 (("mcu_state", "Disconnects / 'Lost communication' during prints"), ["dc_power_wiring"], "dc_power_wiring card: bad crimp -> board resets, 'Lost communication'"),
 (("stop_type", "The Pi stays on, but motors and heaters stop ('Lost communication' / MCU error)"), ["power_supply"], "24 V sag resets the board while the 5 V Pi stays on"),
 (("when", "Only while heating"), ["bed_thermal_fuse", "dc_power_wiring", "bed_thermistor", "controller_board"],
  "heating draws the highest current (bed 60 W + hotend): weak crimps and an open fuse show then"),
 (("shift_axis", "Diagonal / both"), ["xy_pulleys_idlers"], "CoreXY kinematics (manual): one slipping motor pulley moves the head along a diagonal"),
 (("noise", "Clicking or thumping"), ["x_linear_rail", "y_linear_rails"], "binding carriage -> motor loses steps with a clicking sound"),
 (("when", "Right after the first layer"), ["xy_pulleys_idlers", "x_linear_rail", "y_linear_rails"], "slicer profile: 30 mm/s first layer, 100-125 mm/s after; more force needed"),
 (("restart", "Stays off until I switch it on again"), ["mains_power_input"], "mains_power_input card: tripped or unplugged supply stays off"),
 (("surface", "Ringing / ghosting (ripples after corners)"), ["toolhead", "xy_belts"], "toolhead card (loose parts); belts card (low tension -> ringing); manual p.141 110 Hz"),
 (("surface", "Skewed: squares are not square"), ["xy_belts"], "manual p.142: equal A/B belt tension, unequal tension skews CoreXY"),
 (("surface", "Stringing, rough or bubbly surface"), ["filament_material", "slicer_settings"], "filament card (wet filament pops, strings); slicer retraction"),
 (("surface", "Drooping overhangs, curled corners"), ["part_cooling_fan", "slicer_settings"], "config [fan]; slicer fan from layer 4"),
 (("surface", "Blobs, too much plastic"), ["firmware_config_macros", "slicer_settings"], "config [extruder] rotation_distance (over-extrusion)"),
 (("surface", "Wavy or uneven layer lines (Z banding)"), ["z_motor_leadscrew", "z_rails"], "Z lead screw / rails cards (binding, wobble)"),
 (("fuse_state", "Open (OL)"), ["bed_thermal_fuse"], "BOM:46 150 C thermal fuse in series with the bed heater; open = blown"),
 (("fuse_state", "About 0 ohm (closed)"), ["bed_heater", "bed_thermistor"], "fuse is fine, the heater pad or sensor is the cause"),
 (("crimp_tug", "Yes, it resets or flickers"), ["dc_power_wiring"], "dc_power_wiring card check: 'tug-test each crimp'; documentation: bad crimps"),
 (("board_seen", "No, it is missing"), ["controller_board", "dc_power_wiring", "firmware_config_macros"], "Klipper 'Unable to connect': board not powered, dead or wrong serial id"),
 (("board_seen", "Yes, it is listed"), ["host_computer", "dc_power_wiring", "power_supply"], "board enumerates: the USB link, the host or a power dip during printing"),
 (("onset", "Right after I changed something"), ["firmware_config_macros", "slicer_settings", "filament_material"], "a change of config, slicer profile or spool explains a sudden new fault"),
 (("onset", "Got worse slowly"), ["xy_belts", "x_linear_rail", "y_linear_rails", "z_rails", "nozzle", "xy_pulleys_idlers", "umbilical_wiring", "toolhead"],
  "wear parts: belts stretch, rails dry out, nozzles wear and clog, cables fatigue (maintenance page)"),
 (("mcu_state", "Disconnects / 'Lost communication' during prints"), ["umbilical_wiring"],
  "LDO V0.2r1 kit: the toolhead/umbilical board talks to the host over the umbilical cable; a bad pin there drops the link"),
 (("first_layer", "Too high / not sticking everywhere"), ["firmware_config_macros"], "config [stepper_z] position_endstop and saved Z offset decide the first-layer gap"),
 (("surface", "Wavy or uneven layer lines (Z banding)"), ["bed_plate_carrier"], "bed_plate_carrier card (not rigid): a heated bed bows as it expands and contracts"),
 (("part_fan_state", "No, it does not spin"), ["part_cooling_fan", "umbilical_wiring"], "config [fan]; part_cooling_fan card"),
 (("part_fan_state", "Yes, it spins"), ["slicer_settings", "filament_material"], "fan works: quality problem lies in settings or material"),
 (("which_temp", "The hotend"), ["hotend_heater", "hotend_thermistor", "umbilical_wiring", "part_cooling_fan", "firmware_config_macros"], "the faulty reading belongs to the hotend circuit"),
 (("which_temp", "The bed"), ["bed_heater", "bed_thermistor", "bed_thermal_fuse"], "the faulty reading belongs to the bed circuit (heater, thermistor, fuse in series)"),
 (("which_temp", "Both"), ["power_supply", "dc_power_wiring", "controller_board"], "both heaters share the 24 V supply and the board"),
 (("which_temp", "Neither, both look normal"), ["host_computer", "controller_board", "z_endstop", "dc_power_wiring"], "the stop is not a temperature fault"),
]
for _key, _ids, _src in EVIDENCE_ADDED:
    EVIDENCE.setdefault(_key, [])
    EVIDENCE[_key] += [i for i in _ids if i not in EVIDENCE[_key]]

TEXT_EVIDENCE = [  # words in free text -> components (from the card failure modes)
 (("popping", "crackl", "steam", "wet", "moist", "humid", "brittle"), ["filament_material"]),
 (("runout", "pause", "paused by itself"), ["filament_runout_sensor", "filament_material"]),
 (("burn", "smoke", "melted wire", "smell"), ["umbilical_wiring", "hotend_heater", "controller_board"]),
 (("stringing", "strings", "oozing"), ["slicer_settings", "filament_material"]),
 (("warp", "lifting corners"), ["bed_heater", "filament_material", "slicer_settings"]),
 (("printer.cfg", "edited the config", "changed the config", "config edit", "firmware update"), ["firmware_config_macros"]),
 (("slicer profile", "print faster", "changed my slicer", "new profile", "lower temperature"), ["slicer_settings"]),
 (("new spool", "different filament", "new filament", "spool", "tangle", "jerk", "snag"), ["filament_material"]),
 (("belt does not run straight", "belt rubs", "belt moves up", "belt climbs", "belt rides", "rubs at the", "belt runs off"), ["xy_pulleys_idlers", "xy_belts"]),
]

# Which area each question belongs to, and which areas fit each kind of problem (system -> subsystem -> part).
AREA = {"kind": "general", "when": "general", "onset": "general", "change": "general", "error": "general", "what": "general",
        "stop_type": "power error", "restart": "power", "cord_wiggle": "power", "other_load": "power", "volts": "power", "mcu": "power error",
        "runout_check": "power", "psu_led": "power", "hot_temp": "temperature", "hot_behaviour": "temperature", "hot_swing": "temperature", "heater_r": "temperature",
        "therm_r": "temperature error", "wiggle": "temperature error", "hot_fan": "temperature plastic", "fan_v": "temperature plastic",
        "flow": "plastic", "motor": "plastic", "e_test": "plastic", "filament": "plastic firstlayer", "print_set": "plastic",
        "shift": "motion", "noise": "motion", "by_hand": "motion", "axis_test": "motion", "belts": "motion",
        "z_home": "firstlayer", "first_layer": "firstlayer", "bed_temp": "firstlayer temperature", "bed_r": "firstlayer temperature",
        "part_fan": "plastic", "which_temp": "temperature error", "surface": "plastic motion firstlayer",
        "fuse_r": "temperature error", "crimp_tug": "power error", "board_seen": "power error"}
KIND_AREAS = {"The printer stops, switches off or restarts": {"power", "error"},
              "An error message / Klipper shutdown": {"error", "temperature", "power"},
              "Plastic problem (none, too little, blobs, leaks)": {"plastic", "temperature"},
              "Movement problem (layer shift, noise, crash)": {"motion"},
              "Temperature problem": {"temperature"},
              "First layer / bed problem": {"firstlayer", "plastic"}}

def in_area(qid, case):
    kind = case["facts"].get("problem_kind")
    if not kind or kind not in KIND_AREAS: return True
    tags = set(AREA.get(qid, "general").split())
    return "general" in tags or bool(tags & KIND_AREAS[kind])

def answered(qid, case):
    q = Q[qid]
    if "slot" in q:
        v = case["facts"].get(q["slot"])
        if q["slot"] == "what_happens": return bool(v) and len(v) >= 40   # one short sentence is not yet a description
        return bool(v)
    return all(f["key"] in case["measurements"] for f in q["fields"] if not f.get("text"))

def candidates(case, hyps, n=8):
    """Questions not answered or asked yet, ranked by how well they split the current hypotheses.
    hyps: list of (component id, score). p = share of the hypothesis score a question can test.
    value = 4 p (1 - p): highest when the question tests about half of the probable causes (it splits them),
    near 0 when it tests none of them (irrelevant) or all of them (separates nothing)."""
    total = sum(max(s, 0) for _, s in hyps) or 1.0; out = []
    for qid, q in Q.items():
        if qid in case["asked_ids"] or answered(qid, case): continue
        if q.get("generic"): score = {"what": 6, "error": 0.8, "when": 0.8, "change": 0.5, "onset": 0.4}[qid]
        else:
            p = sum(max(s, 0) for c, s in hyps if c in q["helps"]) / total
            if p == 0: continue
            score = 4 * p * (1 - p) + 0.3 * p
        if q["kind"] == "fields" and case["rounds"] < 2: score /= 2   # cheap observations first, measurements later
        out.append((score, qid))
    out.sort(key=lambda x: -x[0])
    return [qid for s, qid in out[:n] if s > 0.05]
