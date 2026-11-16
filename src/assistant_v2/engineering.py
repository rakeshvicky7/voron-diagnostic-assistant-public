"""Engineering checks: exact calculations from the user's measurements against the design values of the Voron 0.2.

Every design value carries its source (BOM, printer config line, assembly manual page, documentation site).
Values that are NOT in the project documents are marked as such ("general") so the thesis can say exactly
what is grounded and what is an engineering assumption.

Each check returns a dict:
  {"id", "title", "formula", "result", "expected", "verdict": "ok" | "warn" | "fault", "meaning", "points_to": [ids], "source"}
"""
import math

CFG = "bigtreetech-skr-pico-v1.0.cfg"
SPEC = {
    "supply_v":        (24.0,  "BOM: Meanwell LRS-150-24 (24 V supply)"),
    "psu_w":           (150.0, "BOM: Meanwell LRS-150-24 (150 W)"),
    "bed_heater_w":    (60.0,  "BOM: Silicone DC 24V Heater 100x100mm 60W"),
    "fan_v":           (24.0,  "BOM: 3010 blower / axial fans 24V"),
    "hotend_max_c":    (270.0, f"{CFG}:162 [extruder] max_temp"),
    "bed_max_c":       (120.0, f"{CFG}:196 [heater_bed] max_temp"),
    "min_extrude_c":   (170.0, f"{CFG}:163 [extruder] min_extrude_temp"),
    "hotend_fan_on_c": (50.0,  f"{CFG}:211 [heater_fan hotend_fan] heater_temp"),
    "e_rot_dist":      (22.23, f"{CFG}:147 [extruder] rotation_distance (gear_ratio 50:10, line 148)"),
    "xy_rot_dist":     (40.0,  f"{CFG}:58/85 [stepper_x/y] rotation_distance"),
    "z_rot_dist":      (8.0,   f"{CFG}:115 [stepper_z] rotation_distance (T8x8 lead screw)"),
    "nozzle_mm":       (0.4,   f"{CFG}:150 [extruder] nozzle_diameter"),
    "filament_mm":     (1.75,  f"{CFG}:151 [extruder] filament_diameter"),
    "max_cross_mm2":   (0.8,   f"{CFG}:165 [extruder] max_extrude_cross_section"),
    "max_velocity":    (200.0, f"{CFG}:43 [printer] max_velocity"),
    "max_accel":       (2000.0, f"{CFG}:44 [printer] max_accel"),
    "belt_hz":         (110.0, "Assembly manual p.141: 110 Hz at 150 mm"),
    "therm_r25":       (100000.0, f"{CFG} comment: 'Generic 3950' (NTC 100k, beta 3950); sensor_type is not set in the config"),
    "therm_beta":      (3950.0,   f"{CFG} comment: 'Generic 3950'"),
    "endstop_nc":      ("<10 ohm not pressed, >10 Mohm pressed", "Documentation site: build/electrical (endstop NC check)"),
}
GEN = "general engineering value, not in the project documents"

def v(k): return SPEC[k][0]
def src(k): return SPEC[k][1]
def _num(x):
    try: return float(x)
    except (TypeError, ValueError): return None

def ntc_temp(r_ohm, r25=None, beta=None):
    """Beta equation: 1/T = 1/T25 + ln(R/R25)/B   (T in kelvin)."""
    r25 = r25 or v("therm_r25"); beta = beta or v("therm_beta")
    return 1.0 / (1.0 / 298.15 + math.log(r_ohm / r25) / beta) - 273.15

def ntc_res(t_c, r25=None, beta=None):
    r25 = r25 or v("therm_r25"); beta = beta or v("therm_beta")
    return r25 * math.exp(beta * (1.0 / (t_c + 273.15) - 1.0 / 298.15))

def _chk(id, title, formula, result, expected, verdict, meaning, points_to, source, keys=None):
    return {"id": id, "title": title, "formula": formula, "result": result, "expected": expected,
            "verdict": verdict, "meaning": meaning, "points_to": points_to, "source": source, "keys": keys or []}

def run(m):
    """m: dict of measurement key -> value (number, or the strings 'open' / 'short'). Returns the list of checks."""
    out = []; g = m.get
    # ---- hotend heater resistance -> power ------------------------------------------------------------
    r = g("hotend_heater_ohm")
    if r == "open" or (_num(r) or 0) > 1e5:
        out.append(_chk("heater_r", "Hotend heater resistance", "R measured", "open circuit", "a few to ~30 ohm",
                        "fault", "No current can flow: the heater cartridge or its wires are broken.", ["hotend_heater", "umbilical_wiring"], src("supply_v")))
    elif _num(r) is not None:
        r = _num(r); p = v("supply_v") ** 2 / r if r > 0 else float("inf")
        verdict = "fault" if r < 3 else ("warn" if not 20 <= p <= 80 else "ok")
        meaning = ("Near short circuit: risk of blowing the board's heater output." if r < 3 else
                   f"The cartridge gives about {p:.0f} W at 24 V." + ("" if 20 <= p <= 80 else " That is outside the usual 20-80 W range, so heating will be too slow or too aggressive."))
        out.append(_chk("heater_r", "Hotend heater power from resistance", "P = V^2 / R = 24^2 / R", f"{p:.1f} W (R = {r:g} ohm)",
                        "the documents do not give the cartridge wattage; 20-80 W is the usual range (" + GEN + ")", verdict, meaning,
                        ["hotend_heater"] if verdict != "ok" else [], src("supply_v")))
    # ---- bed heater resistance -------------------------------------------------------------------------
    r = g("bed_heater_ohm")
    exp_r = v("supply_v") ** 2 / v("bed_heater_w")
    if r == "open" or (_num(r) or 0) > 1e5:
        out.append(_chk("bed_r", "Bed heater resistance", "R measured", "open circuit", f"{exp_r:.1f} ohm", "fault",
                        "The bed heater pad, its wiring or the 150 C thermal fuse in series is open.", ["bed_heater", "bed_thermal_fuse"], src("bed_heater_w") + "; BOM:46 thermal fuse in series"))
    elif _num(r) is not None:
        r = _num(r); dev = (r - exp_r) / exp_r * 100
        verdict = "ok" if abs(dev) <= 15 else ("warn" if abs(dev) <= 40 else "fault")
        out.append(_chk("bed_r", "Bed heater resistance vs. design", "R_expected = V^2 / P = 24^2 / 60", f"{r:g} ohm ({dev:+.0f} %)",
                        f"{exp_r:.1f} ohm", verdict, "Matches the 60 W pad." if verdict == "ok" else
                        f"The pad would give {v('supply_v')**2/r:.0f} W instead of 60 W, so it is damaged or the wrong pad.",
                        ["bed_heater"] if verdict != "ok" else [], src("bed_heater_w")))
    # ---- thermistors -----------------------------------------------------------------------------------
    for key, cid, label in (("hotend_thermistor_ohm", "hotend_thermistor", "Hotend"), ("bed_thermistor_ohm", "bed_thermistor", "Bed")):
        r = g(key); room = _num(g("room_c")) or 22.0
        if r == "open" or (_num(r) or 0) > 2e6:
            out.append(_chk(key, f"{label} thermistor resistance", "R measured", "open circuit", f"~{ntc_res(room)/1000:.0f} kohm at {room:g} C",
                            "fault", "Open sensor: Klipper shows 'ADC out of range' and stops (documentation site: Klipper common errors).",
                            [cid, "umbilical_wiring"] if cid == "hotend_thermistor" else [cid], src("therm_r25")))
        elif r == "short" or (_num(r) is not None and _num(r) < 50):
            out.append(_chk(key, f"{label} thermistor resistance", "R measured", "short circuit", f"~{ntc_res(room)/1000:.0f} kohm at {room:g} C",
                            "fault", "Shorted sensor or wires: reads a very high temperature, Klipper stops with 'ADC out of range'.",
                            [cid, "umbilical_wiring"] if cid == "hotend_thermistor" else [cid], src("therm_r25")))
        elif _num(r) is not None:
            t = ntc_temp(_num(r)); diff = t - room
            verdict = "ok" if abs(diff) <= 5 else ("warn" if abs(diff) <= 15 else "fault")
            out.append(_chk(key, f"{label} thermistor: temperature from resistance", "1/T = 1/T25 + ln(R/R25)/B  (R25 = 100 kohm, B = 3950)",
                            f"{t:.1f} C (R = {_num(r):g} ohm)", f"room temperature {room:g} C (R ~ {ntc_res(room)/1000:.0f} kohm)", verdict,
                            "The sensor reads correctly at room temperature." if verdict == "ok" else
                            "The sensor reads wrong at rest: damaged thermistor, or a different type than the config assumes.",
                            [cid] if verdict != "ok" else [], src("therm_r25")))
    # ---- temperature reading vs target -----------------------------------------------------------------
    for pre, cid_h, cid_t, lim in (("hotend", "hotend_heater", "hotend_thermistor", "hotend_max_c"), ("bed", "bed_heater", "bed_thermistor", "bed_max_c")):
        tgt, act = _num(g(f"{pre}_target_c")), _num(g(f"{pre}_actual_c"))
        if tgt is not None and tgt > v(lim):
            out.append(_chk(f"{pre}_limit", f"{pre.capitalize()} target vs. max_temp", "target <= max_temp", f"{tgt:g} C", f"<= {v(lim):g} C",
                            "fault", "The target is above the configured limit; Klipper will refuse it.", ["firmware_config_macros", "slicer_settings"], src(lim)))
        if tgt is not None and act is not None:
            gap = tgt - act
            verdict = "ok" if abs(gap) <= 5 else ("warn" if abs(gap) <= 15 else "fault")
            meaning = ("Reaches the target." if verdict == "ok" else
                       f"{'Stays' if gap > 0 else 'Goes'} {abs(gap):.0f} C {'below' if gap > 0 else 'above'} target: "
                       + ("the heater cannot deliver enough heat, or heat is lost (fan blowing on the block, missing sock), or the sensor reads low."
                          if gap > 0 else "the sensor reads high, or the heater output is stuck on (board MOSFET)."))
            out.append(_chk(f"{pre}_gap", f"{pre.capitalize()} temperature reached", "gap = target - actual", f"{gap:+.0f} C",
                            "within +/-5 C (Klipper hysteresis default 5 C, " + GEN + ")", verdict, meaning,
                            ([cid_h, cid_t] if gap > 0 else [cid_t, "controller_board"]) if verdict != "ok" else [], "Klipper verify_heater defaults (" + GEN + ")"))
    sw = _num(g("hotend_swing_c"))
    if sw is not None:
        verdict = "ok" if sw <= 2 else ("warn" if sw <= 10 else "fault")
        out.append(_chk("swing", "Hotend temperature stability", "swing = max - min while holding", f"+/-{sw:g} C", "about +/-1-2 C with PID",
                        verdict, "Stable." if verdict == "ok" else ("Slow swing: PID values or airflow on the heater block." if verdict == "warn"
                        else "Large jumps: a loose thermistor or a broken wire in the moving cable, not a heating problem."),
                        [] if verdict == "ok" else (["firmware_config_macros", "part_cooling_fan"] if verdict == "warn" else ["hotend_thermistor", "umbilical_wiring"]),
                        f"{CFG}:158-160 PID values; " + GEN))
    tgt = _num(g("print_temp_c"))
    if tgt is not None and tgt < v("min_extrude_c"):
        out.append(_chk("cold", "Print temperature vs. min_extrude_temp", "temp >= min_extrude_temp", f"{tgt:g} C", f">= {v('min_extrude_c'):g} C",
                        "fault", "Klipper blocks extrusion below this temperature ('Extrude below minimum temp').", ["slicer_settings", "firmware_config_macros"], src("min_extrude_c")))
    # ---- extrusion: commanded vs actual ------------------------------------------------------------------
    c, a = _num(g("extrude_cmd_mm")), _num(g("extrude_act_mm"))
    RES = 1.0   # a ruler and a pen mark: about +/-1 mm reading uncertainty (general)
    if c and a is not None and (c < 20 or a > 1.5 * c):
        why = (f"{c:g} mm is too short to measure: a 1 mm reading error alone is +/-{100 * RES / c:.0f} %." if c < 20 else
               f"{a:g} mm fed for {c:g} mm commanded is physically unlikely (the extruder cannot feed 50 % more than it turns).")
        out.append(_chk("e_len", "Extruded length vs. commanded", "uncertainty = reading error / commanded length", "inconclusive",
                        "commanded length >= 50 mm (100 mm recommended)", "inconclusive",
                        why + " Please repeat the test with 100 mm.", [], "measurement practice (" + GEN + ")", keys=["extrude_cmd_mm", "extrude_act_mm"]))
        c = None
    if c and a is not None:
        err = (a - c) / c * 100; new_rd = v("e_rot_dist") * a / c
        verdict = "ok" if abs(err) <= 3 else ("warn" if abs(err) <= 15 else "fault")
        meaning = ("Extruder feeds the right length." if verdict == "ok" else
                   "Nothing is fed: motor not turning, gears slipping, or a full clog." if a <= 0.05 * c else
                   f"Feeds {abs(err):.0f} % {'too little' if err < 0 else 'too much'}. Calibration would need rotation_distance = 22.23 x {a:g}/{c:g} = {new_rd:.2f}."
                   + (" A loss this large usually means slipping gears or a partial clog rather than calibration." if err < -15 else ""))
        pts = [] if verdict == "ok" else (["extruder_gears_guidler", "extruder_motor", "nozzle", "heatbreak_ptfe"] if err < -15 else ["firmware_config_macros", "extruder_gears_guidler"])
        out.append(_chk("e_len", "Extruded length vs. commanded", "error = (actual - commanded) / commanded", f"{err:+.1f} % ({a:g} of {c:g} mm)",
                        "within +/-3 %", verdict, meaning, pts, src("e_rot_dist")))
    # ---- axis travel: commanded vs actual ----------------------------------------------------------------
    c, a = _num(g("axis_cmd_mm")), _num(g("axis_act_mm")); ax = (g("axis_name") or "").lower()
    if c and a is not None and c < 20:
        out.append(_chk("axis", "Axis travel vs. commanded", "uncertainty = reading error / commanded length", "inconclusive",
                        "commanded move >= 50 mm", "inconclusive", f"{c:g} mm is too short to measure reliably. Please repeat with 100 mm.",
                        [], "measurement practice (" + GEN + ")", keys=["axis_cmd_mm", "axis_act_mm"]))
        c = None
    if c and a is not None:
        err = (a - c) / c * 100; rd = "z_rot_dist" if ax == "z" else "xy_rot_dist"
        verdict = "ok" if abs(err) <= 1 else ("warn" if abs(err) <= 5 else "fault")
        out.append(_chk("axis", f"{ax.upper() or 'Axis'} travel vs. commanded", "error = (actual - commanded) / commanded",
                        f"{err:+.1f} % ({a:g} of {c:g} mm)", "within +/-1 %", verdict,
                        "Moves the right distance." if verdict == "ok" else
                        f"Moves {abs(err):.1f} % {'short' if err < 0 else 'long'}: with rotation_distance {v(rd):g}, a steady error is a wrong value or pulley; a random one is skipping or a slipping pulley.",
                        [] if verdict == "ok" else (["z_motor_leadscrew"] if ax == "z" else ["xy_pulleys_idlers", "xy_motors_drivers", "xy_belts"]), src(rd)))
    # ---- belts ----------------------------------------------------------------------------------------------
    fa, fb = _num(g("belt_a_hz")), _num(g("belt_b_hz"))
    for name, f in (("A", fa), ("B", fb)):
        if f is not None:
            dev = f - v("belt_hz"); t_ratio = (f / v("belt_hz")) ** 2
            verdict = "ok" if abs(dev) <= 10 else ("warn" if abs(dev) <= 25 else "fault")
            out.append(_chk(f"belt_{name}", f"Belt {name} tension", "tension ~ f^2 (string: f = (1/2L) sqrt(T/mu))", f"{f:g} Hz = {t_ratio*100:.0f} % of design tension",
                            "110 Hz at 150 mm", verdict, "Correct tension." if verdict == "ok" else
                            ("Too loose: backlash, ringing and layer shifts." if dev < 0 else "Too tight: extra load on motors and idler bearings."),
                            [] if verdict == "ok" else ["xy_belts"], src("belt_hz")))
    if fa is not None and fb is not None and abs(fa - fb) > 5:
        out.append(_chk("belt_ab", "Belt A vs. belt B", "|fA - fB|", f"{abs(fa-fb):g} Hz", "equal (within ~5 Hz)", "warn",
                        "Unequal belts skew the CoreXY motion: diagonal lines and out-of-square prints.", ["xy_belts"], "Assembly manual p.142: equal belt tension"))
    # ---- flow / cross-section ----------------------------------------------------------------------------------
    sp, lh, lw = _num(g("print_speed_mms")), _num(g("layer_height_mm")), _num(g("line_width_mm")) or v("nozzle_mm") * 1.125
    if sp and lh:
        flow = sp * lh * lw; cross = lh * lw; fil = flow / (math.pi * (v("filament_mm") / 2) ** 2)
        verdict = "ok" if flow <= 12 else ("warn" if flow <= 15 else "fault")   # 12: the official Voron profile asks 11 mm3/s
        out.append(_chk("flow", "Volumetric flow demanded", "Q = speed x layer height x line width", f"{flow:.1f} mm3/s (filament {fil:.1f} mm/s)",
                        "a small hotend melts roughly 8-15 mm3/s (" + GEN + ")", verdict,
                        "Within what a small hotend can melt." if verdict == "ok" else "More plastic is demanded than the hotend can melt: under-extrusion and extruder clicking at speed.",
                        [] if verdict == "ok" else ["slicer_settings", "hotend_heater"], GEN))
        if cross > v("max_cross_mm2"):
            out.append(_chk("cross", "Extrusion cross-section", "A = layer height x line width", f"{cross:.2f} mm2", f"<= {v('max_cross_mm2')} mm2",
                            "fault", "Klipper rejects the move ('Extrude exceeds maximum cross-section').", ["slicer_settings"], src("max_cross_mm2")))
        if sp > v("max_velocity"):
            out.append(_chk("speed", "Print speed vs. max_velocity", "speed <= max_velocity", f"{sp:g} mm/s", f"<= {v('max_velocity'):g} mm/s",
                            "warn", "Klipper limits the speed to max_velocity; the slicer value is not reached.", ["slicer_settings"], src("max_velocity")))
    # ---- voltages ------------------------------------------------------------------------------------------------
    pv = _num(g("psu_v"))
    if pv is not None:
        dev = (pv - 24) / 24 * 100; verdict = "ok" if abs(dev) <= 5 else ("warn" if abs(dev) <= 10 else "fault")
        out.append(_chk("psu", "24 V supply", "deviation = (V - 24) / 24", f"{pv:g} V ({dev:+.1f} %)", "24 V +/-5 %", verdict,
                        "Supply is fine." if verdict == "ok" else "Supply out of tolerance: heaters weaken, drivers may brown out and reset.",
                        [] if verdict == "ok" else ["power_supply"], src("supply_v") + "; tolerance " + GEN))
    r5 = _num(g("rail_5v_v"))
    if r5 is not None:
        verdict = "ok" if 4.75 <= r5 <= 5.25 else ("warn" if 4.6 <= r5 <= 5.4 else "fault")
        out.append(_chk("5v", "5 V rail (Raspberry Pi)", "4.75 V <= V <= 5.25 V", f"{r5:g} V", "5 V +/-5 %", verdict,
                        "Fine." if verdict == "ok" else "Under-voltage: the Pi throttles or reboots, which drops the MCU connection.",
                        [] if verdict == "ok" else ["power_supply", "host_computer"], GEN))
    fv = _num(g("fan_v"))
    if fv is not None:
        verdict = "ok" if fv >= 22 else ("warn" if fv >= 12 else "fault")
        out.append(_chk("fanv", "Voltage at the fan connector (fan commanded on)", "V at connector", f"{fv:g} V", ">= ~22 V (24 V fans)", verdict,
                        "The fan gets power, so a stopped fan is the fan itself." if verdict == "ok" else
                        "The fan does not get power: wiring, connector or board output.",
                        ["hotend_fan", "part_cooling_fan"] if verdict == "ok" else ["umbilical_wiring", "controller_board"], src("fan_v")))
    # ---- power budget ----------------------------------------------------------------------------------------------
    r = _num(g("hotend_heater_ohm"))
    if r and r > 3:
        total = v("bed_heater_w") + v("supply_v") ** 2 / r + 25
        out.append(_chk("budget", "Power budget", "bed 60 W + hotend 24^2/R + ~25 W motors/fans/Pi", f"{total:.0f} W", "<= 150 W",
                        "ok" if total <= 150 else "warn", "The supply has enough reserve." if total <= 150 else "Close to or over the supply rating.",
                        [] if total <= 150 else ["power_supply"], src("psu_w")))
    return out

# Klipper error messages -> components (documentation site, Klipper common errors; others marked general)
ERRORS = [
    ("adc out of range", ["hotend_thermistor", "bed_thermistor", "umbilical_wiring"], "Documentation site: Klipper common errors (ADC error)"),
    ("tmc uart", ["controller_board", "power_supply"], "Documentation site: Klipper common errors (TMC UART error)"),
    ("unable to connect", ["controller_board", "host_computer"], "Documentation site: Klipper common errors (Unable to connect)"),
    ("heater_bed not heating", ["bed_heater", "bed_thermal_fuse", "bed_thermistor", "power_supply"], "Klipper verify_heater for [heater_bed]; BOM:46 thermal fuse in series"),
    ("extruder not heating", ["hotend_heater", "hotend_thermistor", "umbilical_wiring", "part_cooling_fan"], "Klipper verify_heater for [extruder] (" + GEN + ")"),
    ("lost communication", ["host_computer", "controller_board", "power_supply", "dc_power_wiring"], "Klipper (" + GEN + "); dc_power_wiring card (bad crimp -> board resets)"),
    ("timer too close", ["host_computer"], "Klipper (" + GEN + ")"),
    ("move out of range", ["z_endstop", "xy_motors_drivers", "firmware_config_macros"], "Klipper (" + GEN + ")"),
    ("extrude below minimum temp", ["slicer_settings", "hotend_heater"], src("min_extrude_c")),
    ("exceeds maximum", ["slicer_settings"], src("max_cross_mm2")),
    ("runout", ["filament_runout_sensor", "filament_material"], f"{CFG}:232-235 [filament_switch_sensor] (commented out by default)"),
]
def error_hits(text):
    t = (text or "").lower()
    return [{"pattern": p, "points_to": ids, "source": s} for p, ids, s in ERRORS if p in t]

# ---- context: what physically changes at the moment the fault appears -----------------------------------
SLICER = "Slicer profile Voron_V0_DD.ini"
LAYER = {"first_layer_speed": (30, f"{SLICER}:94"), "infill_speed": (125, f"{SLICER}:112"), "perimeter_speed": (100, f"{SLICER}:158"),
         "first_layer_accel": (2000, f"{SLICER}:90"), "infill_accel": (4000, f"{SLICER}:103"),
         "disable_fan_first_layers": (3, f"{SLICER}:31"), "first_layer_bed": (100, f"{SLICER}:91"), "bed": (90, f"{SLICER}:7")}

def context(facts, notes):
    """Checks that explain WHY a fault shows at a certain moment (no measurements needed)."""
    out = []; low = " ".join(notes).lower() + " " + str(facts.get("when", "")).lower()
    if "first layer" in low and ("after" in low or facts.get("when") == "Right after the first layer"):
        L = {k: v[0] for k, v in LAYER.items()}
        sp = L["infill_speed"] / L["first_layer_speed"]
        acc = min(L["infill_accel"], v("max_accel")) / L["first_layer_accel"]
        out.append(_chk("layer2", "What changes after the first layer (Voron slicer profile)",
                        "speed 30 -> 100-125 mm/s; acceleration capped by max_accel 2000; part fan off until layer 4; bed 100 -> 90 C",
                        f"head moves {sp:.1f}x faster; kinetic energy of the head ~{sp**2:.0f}x (E = m v^2 / 2); acceleration x{acc:.1f}; heater load slightly lower",
                        "a fault that starts exactly here is triggered by motion/vibration, not by heating or the part fan", "info",
                        "At layer 2 the head moves about 4x faster, so the frame and cables shake much more; the part fan is still off "
                        "and the bed needs less power. A stop at this moment points to a connection that opens under vibration "
                        "(power plug, crimps, toolhead cable) or to motion overload, not to overheating.",
                        ["mains_power_input", "dc_power_wiring", "umbilical_wiring", "xy_motors_drivers"],
                        f"{LAYER['first_layer_speed'][1]}; {LAYER['infill_speed'][1]}; {LAYER['disable_fan_first_layers'][1]}; {CFG}:44 max_accel"))
    return out
