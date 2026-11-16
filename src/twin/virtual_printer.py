"""Virtual Voron 0.2 (digital twin, stage 2): the whole printer, every part can fail.

What it is
  A behavioural simulation built from the design documents (printer config, BOM, assembly manual, slicer profile).
  It models how energy, force, heat, material and signals flow through the machine, so that a fault injected in one
  part shows its effects where a technician would see, hear or measure them. It is NOT a CAD or finite-element copy:
  shapes, vibration modes and plastic flow are reduced to the few numbers that decide what a technician observes.

Subsystems (one function each)
  power + heat ...... stage 1 (heat_power.py): wall -> PSU -> 24 V wiring -> board -> heaters/fans, Klipper PID and
                      safety checks, toolhead cable that shakes more after layer 1, heat creep when the hotend fan stops
  motion (CoreXY) ... torque needed vs. torque available per motor (A/B), belt tension, pulley grip, rail friction;
                      a lost step on ONE motor moves the head diagonally (CoreXY kinematics)
  Z + first layer ... T8x8 lead screw, microswitch endstop (NC), 3-screw bed plane; first-layer gap at 9 points
  extrusion ......... flow demand of the slicer profile vs. melt capacity of the hotend; feed force needed vs.
                      grip of the BMG gears and torque of the pancake motor; heat creep; filament state
  sensors/software .. runout switch, firmware config (PID, rotation_distance, position_endstop), slicer settings

The technician
  answer(qid) returns what a person at this printer would answer to any question of the chat assistant
  (assistant_v2/questions.py): a choice, a measured value, a short text, or None ("I can't tell").

Every design value has its source. Values not in the project documents are marked GEN (general engineering value):
they shape curves and thresholds but are not claims about the Voron.  Usage:
    from twin.virtual_printer import VirtualPrinter, run_case, PARTS
    vp = VirtualPrinter("xy_belts", severity=0.7, seed=1); vp.answer("belts")  ->  ({}, {"belt_a_hz": 61.0, ...})
"""
import math, random
try:
    from . import heat_power as HP
except ImportError:                                   # run as a script from src/twin
    import heat_power as HP

CFG, BOM, MAN, SLI = "printer config (bigtreetech-skr-pico-v1.0.cfg)", "BOM (voron0.2_bom.csv)", "assembly manual", "slicer profile Voron_V0_DD.ini"
GEN = "GEN"
D = {  # design values: (value, source)
    "xy_rot_dist": (40.0, f"{CFG}:58/85"), "z_rot_dist": (8.0, f"{CFG}:115"), "e_rot_dist": (22.23, f"{CFG}:147"),
    "e_gear_ratio": (5.0, f"{CFG}:148 gear_ratio 50:10"), "max_velocity": (200.0, f"{CFG}:43"), "max_accel": (2000.0, f"{CFG}:44"),
    "z_home_speed": (20.0, f"{CFG} [stepper_z] homing_speed"), "z_pos_endstop": (120.0, f"{CFG} [stepper_z] position_endstop"),
    "nozzle": (0.4, f"{CFG}:150"), "filament": (1.75, f"{CFG}:151"), "min_extrude_c": (170.0, f"{CFG}:163"),
    "belt_hz": (110.0, f"{MAN} p.141 (110 Hz at 150 mm)"), "xy_motor_hold_nm": (0.40, f"{BOM}:29 NEMA14 40 Ncm"),
    "layer_h": (0.2, f"{SLI}:120"), "width": (0.44, f"{SLI}:50"), "first_layer_speed": (30.0, f"{SLI}:94"),
    "perimeter_speed": (100.0, f"{SLI}:158"), "infill_speed": (125.0, f"{SLI}:112"), "infill_accel": (4000.0, f"{SLI}:103"),
    "first_layer_accel": (2000.0, f"{SLI}:90"), "print_temp": (250.0, f"{SLI}:225"), "filament_type": ("ABS", f"{SLI}:81"),
    "bed_screws": ([(60, 5), (5, 115), (115, 115)], f"{CFG} [bed_screws]"), "therm_r25": (100000.0, f"{CFG} comment 'Generic 3950'"),
    "therm_beta": (3950.0, f"{CFG} comment 'Generic 3950'"),
    # GEN: not in the documents
    "toolhead_kg": (0.30, GEN), "xy_friction_n": (1.5, GEN), "run_current_frac": (0.65, GEN + " (config comment: 60-70 % of max)"),
    "motor_corner_mms": (200.0, GEN), "melt_max_mm3s": (15.0, GEN + " (V6-class hotend at 250 C)"), "grip_n": (60.0, GEN + " (BMG dual-gear grip)"),
    "e_motor_nm": (0.032, GEN + " (36 mm pancake NEMA14 at run current)"), "feed_base_n": (3.0, GEN), "feed_k_n": (25.0, GEN),
    "squish_tol_mm": (0.06, GEN), "torque_margin": (3.0, GEN + " (design margin of motor torque over need)"),
    "z_margin": (3.0, GEN), "bed_ok_c": (8.0, GEN + " (bed more than 8 C under target: ABS stops sticking)"),
}
def v(k): return D[k][0]
D0 = {k: x[0] for k, x in D.items()}          # the documented design values (before any user setting)

# settings a user (or the language model) may change on the virtual printer: key -> (design key or None, min, max, unit, meaning)
SETTINGS = {
 "nozzle_temp":    ("print_temp", 180, 280, "C", "nozzle temperature in the slicer"),
 "bed_temp":       (None, 40, 120, "C", "bed temperature (ABS needs about 90-100 C)"),
 "print_speed":    ("infill_speed", 20, 300, "mm/s", "infill / main print speed"),
 "first_layer_speed": ("first_layer_speed", 10, 100, "mm/s", "first layer speed"),
 "layer_height":   ("layer_h", 0.05, 0.4, "mm", "layer height"),
 "line_width":     ("width", 0.3, 0.8, "mm", "extrusion line width"),
 "max_accel":      ("max_accel", 500, 6000, "mm/s2", "Klipper max_accel"),
 "belt_a_hz":      (None, 40, 160, "Hz", "belt A tension as pluck frequency (design 110 Hz)"),
 "belt_b_hz":      (None, 40, 160, "Hz", "belt B tension as pluck frequency (design 110 Hz)"),
 "z_offset":       (None, -0.5, 0.5, "mm", "first-layer gap error: + nozzle too high, - too low"),
 "xy_current":     (None, 0.2, 1.5, "x", "XY motor current, 1 = normal"),
 "e_rotation_distance": (None, 15, 30, "mm", "Klipper [extruder] rotation_distance (design 22.23)"),
}
def clean_settings(st):
    """Keep known keys and clamp them to safe ranges."""
    out = {}
    for k, val in (st or {}).items():
        if k in SETTINGS:
            try: out[k] = min(SETTINGS[k][2], max(SETTINGS[k][1], float(val)))
            except (TypeError, ValueError): pass
    return out

PARTS = ["hotend_heater", "hotend_thermistor", "nozzle", "heatbreak_ptfe", "extruder_motor", "extruder_gears_guidler", "hotend_fan",
         "part_cooling_fan", "xy_motors_drivers", "xy_belts", "xy_pulleys_idlers", "x_linear_rail", "y_linear_rails", "toolhead",
         "z_motor_leadscrew", "z_rails", "z_endstop", "bed_heater", "bed_thermistor", "bed_plate_carrier", "controller_board",
         "umbilical_wiring", "power_supply", "host_computer", "filament_runout_sensor", "firmware_config_macros", "slicer_settings",
         "filament_material", "mains_power_input", "dc_power_wiring", "bed_thermal_fuse"]

# fault modes per part: the severity s (0..1) picks the mode and its strength. Each mode is one failure mode of the part card.
MODES = {
 "nozzle": [(0.45, "partial clog"), (0.85, "heavy clog"), (1.01, "full clog")],
 "heatbreak_ptfe": [(0.4, "gap between PTFE and nozzle: leak"), (1.01, "gap between PTFE and nozzle: plug forms")],
 "extruder_motor": [(0.7, "weak motor / low current"), (1.01, "open coil")],
 "extruder_gears_guidler": [(0.6, "guidler too loose"), (1.01, "worn or slipping drive gear")],
 "xy_motors_drivers": [(1.01, "driver overheats, current drops")],
 "xy_belts": [(0.5, "belts unequal"), (1.01, "belts loose")],
 "xy_pulleys_idlers": [(0.55, "loose pulley grub screw"), (1.01, "worn idler bearing")],
 "x_linear_rail": [(1.01, "dry or damaged X rail")], "y_linear_rails": [(1.01, "dry or damaged Y rails")],
 "toolhead": [(1.01, "loose toolhead parts")],
 "z_motor_leadscrew": [(0.7, "binding lead screw / nut"), (1.01, "motor or coupler failed")],
 "z_rails": [(1.01, "binding Z rails")],
 "z_endstop": [(0.5, "switch mount loose"), (0.8, "broken wire (NC reads triggered)"), (1.01, "switch does not actuate")],
 "bed_plate_carrier": [(0.6, "bed not level (screws)"), (1.01, "plate loose / warped")],
 "filament_runout_sensor": [(1.01, "false runout triggers")],
 "firmware_config_macros": [(0.35, "badly tuned PID"), (0.7, "wrong extruder rotation_distance"), (1.01, "wrong Z position_endstop")],
 "slicer_settings": [(0.6, "speed / flow too high"), (1.01, "nozzle temperature too low")],
 "filament_material": [(0.5, "wet filament"), (0.8, "tangled spool"), (1.01, "thin / out-of-tolerance filament")],
 "umbilical_wiring": [(1.01, "broken strands in the toolhead cable")],
}
HEAT_POWER = set(HP.FAULTS) - {"firmware_config_macros"}
HOT_SET = {"hotend_heater", "hotend_thermistor", "umbilical_wiring", "firmware_config_macros", "part_cooling_fan", "power_supply"}

def ntc_res(t_c):
    return v("therm_r25") * math.exp(v("therm_beta") * (1 / (t_c + 273.15) - 1 / 298.15))

# =====================================================================================================================
class VirtualPrinter:
    def __init__(self, fault=None, severity=None, seed=0, dont_know=0.0, room_c=22.0, settings=None):
        assert fault is None or fault in PARTS, f"unknown part {fault}"
        self.cfg = clean_settings(settings); saved = dict(D)
        for k, val in self.cfg.items():
            if SETTINGS[k][0]: D[SETTINGS[k][0]] = (val, "user setting")
        try: self._build(fault, severity, seed, dont_know, room_c)
        finally: D.clear(); D.update(saved)

    def _build(self, fault, severity, seed, dont_know, room_c):
        self.rnd = random.Random(seed); self.seed = seed
        self.fault = fault; self.s = severity if severity is not None else self.rnd.uniform(0.2, 0.95)
        self.mode = next((m for lim, m in MODES.get(fault, []) if self.s < lim), None) if fault else None
        self.dont_know = dont_know; self.room = room_c
        hp_fault = fault if fault in HEAT_POWER or (fault == "firmware_config_macros" and self.mode == "badly tuned PID") else None
        self.hp_log = HP.simulate(hp_fault, self.s, seed)
        self.hp_obs, self.hp_meas = HP.observe(self.hp_log, HP.simulate(hp_fault, self.s, seed + 1, idle_wiggle=True)
                                               if fault in ("mains_power_input", "power_supply", "dc_power_wiring") else None)
        # did a print actually run? (a stop while connecting, homing or heating means nothing was printed)
        self.printed = self.hp_log.get("off_phase") not in ("idle", "connect", "home", "heat")
        self.homed = self.hp_log.get("off_phase") not in ("idle", "connect")
        self.motion = self._motion(); self.z = self._z(); self.ext = self._extrusion()

    def is_(self, part, mode=None): return self.fault == part and (mode is None or self.mode == mode)

    # ---- motion: CoreXY ------------------------------------------------------------------------------------------
    def _motion(self):
        s = self.s; r = v("xy_rot_dist") / (2 * math.pi) / 1000            # pulley radius, m
        fr = {"x": v("xy_friction_n"), "y": v("xy_friction_n")}           # friction along each axis, N
        if self.is_("x_linear_rail"): fr["x"] += 12 * s
        if self.is_("y_linear_rails"): fr["y"] += 12 * s
        bearing = self.is_("xy_pulleys_idlers", "worn idler bearing")
        if bearing: fr["x"] += 6 * s; fr["y"] += 6 * s
        hz = {"a": self.cfg.get("belt_a_hz", v("belt_hz")), "b": self.cfg.get("belt_b_hz", v("belt_hz"))}
        if self.is_("xy_belts", "belts loose"): hz = {"a": v("belt_hz") * math.sqrt(1 - 0.95 * s), "b": v("belt_hz") * math.sqrt(1 - 0.85 * s)}
        if self.is_("xy_belts", "belts unequal"): hz["b"] = v("belt_hz") * (0.9 - 0.25 * s)
        tension = {k: (f / v("belt_hz")) ** 2 for k, f in hz.items()}      # tension ~ f^2 (string law)
        acc_ref = min(v("infill_accel"), v("max_accel"))                   # Klipper clamps the slicer's 4000 to max_accel 2000
        f_ref = (v("toolhead_kg") * acc_ref / 1000 + v("xy_friction_n")) / 2 * math.sqrt(2)
        t_ref = f_ref * r                                                   # torque a healthy printer needs per motor
        # effective torque at speed, scaled so a healthy printer has the design margin of 3 at infill speed (GEN)
        f_ref0 = (v("toolhead_kg") * min(D0["infill_accel"], D0["max_accel"]) / 1000 + v("xy_friction_n")) / 2 * math.sqrt(2) * r
        t0 = v("torque_margin") * f_ref0 * (1 + D0["infill_speed"] / v("motor_corner_mms")) * self.cfg.get("xy_current", 1.0)
        cur = {"a": 1.0, "b": 1.0}
        if self.is_("xy_motors_drivers"): cur["a"] = 0.30 * (1 - s) + 0.05   # one driver overheats: thermal current cut-back
        grip = {"a": 9.9, "b": 9.9}                                         # pulley set-screw grip, Nm (tight = never slips)
        if self.is_("xy_pulleys_idlers", "loose pulley grub screw"): grip["a"] = t_ref * max(0.05, 1.25 - 1.5 * s)
        # motion phases of a print (slicer profile; both use 2000 mm/s^2 after the clamp, layers 2+ run 4x faster)
        phases = {"layer1": (v("first_layer_speed"), min(v("first_layer_accel"), v("max_accel"))), "layers2": (v("infill_speed"), acc_ref)}
        skips = {}; noise = None
        for ph, (spd, acc) in phases.items():
            for ax in ("x", "y"):
                f_need = (v("toolhead_kg") * acc / 1000 + fr[ax]) / 2 * math.sqrt(2)     # per motor: a CoreXY move needs both
                t_need = f_need * r
                for m in ("a", "b"):
                    hot = cur[m] if ph == "layers2" else min(1.0, cur[m] * 3)  # the driver heats up over the first minutes
                    t_av = t0 / (1 + spd / v("motor_corner_mms")) * hot
                    if t_need > t_av: skips.setdefault(ph, set()).add(("motor", m, ax))
                    if t_need > grip[m]: skips.setdefault(ph, set()).add(("pulley", m, ax))
                    if tension[m] < 0.4: skips.setdefault(ph, set()).add(("belt", m, ax))   # teeth jump on a slack belt
        # which way does the head shift?  one motor slipping = diagonal (CoreXY); both motors on one axis = that axis
        kinds = set().union(*skips.values()) if skips else set()
        motors = {m for _, m, _ in kinds}
        axes_load = {ax for _, _, ax in kinds}
        if not kinds: shift = "Not a shift problem"
        elif len(motors) == 1: shift = "Diagonal / both"
        elif axes_load == {"x"}: shift = "X only"
        elif axes_load == {"y"}: shift = "Y only"
        else: shift = "Diagonal / both"
        when = "Right after the first layer" if "layers2" in skips and "layer1" not in skips else ("All the time" if skips else None)
        if any(k == "motor" or k == "belt" for k, _, _ in kinds): noise = "Clicking or thumping"
        if bearing: noise = "Grinding / scraping"
        if self.is_("x_linear_rail") or self.is_("y_linear_rails"): noise = noise or "Squeaking"
        if self.is_("toolhead"): noise = "Clicking or thumping" if s > 0.5 else "No"
        by_hand = "Smooth in both"; rough = 2.3 * v("xy_friction_n")       # a technician feels about 2x the normal drag
        if fr["x"] > rough and fr["y"] > rough: by_hand = "Rough in both"
        elif fr["x"] > rough: by_hand = "Rough or tight in X"
        elif fr["y"] > rough: by_hand = "Rough or tight in Y"
        # 100 mm test move at 50 mm/s, slow: only slipping grip, slack belts and heavy binding show
        axis = "Y" if shift == "Y only" or self.is_("y_linear_rails") else "X"
        act = 100.0
        if ("layer1" in skips) or self.is_("xy_pulleys_idlers", "loose pulley grub screw") and kinds: act -= self.rnd.uniform(1, 4) * s
        if self.is_("xy_belts", "belts loose"): act -= 0.6 * s                     # backlash of a slack belt
        skew = self.is_("xy_belts", "belts unequal")                                # unequal tension: out-of-square parts
        return {"skips": skips, "shift": shift, "when": when, "noise": noise or "No", "by_hand": by_hand, "belt_hz": hz, "skew": skew,
                "axis": axis, "axis_act": round(act + self.rnd.gauss(0, 0.05), 2),
                "ringing": self.is_("toolhead") or min(tension.values()) < 0.6 or skew}

    # ---- Z axis and first layer ------------------------------------------------------------------------------------
    def _z(self):
        s = self.s; home = "Homes correctly"; err = None; sigma = 0.01; offset = 0.0; tilt = (0.0, 0.0)
        if self.is_("z_endstop", "switch mount loose"): sigma = 0.04 + 0.12 * s
        if self.is_("z_endstop", "broken wire (NC reads triggered)"): home = "Stops too early"; err = "Endstop z still triggered after retract"
        if self.is_("z_endstop", "switch does not actuate"): home = "Bed crashes / does not stop"; err = "Move out of range"
        load = 1 + (6 * s if self.is_("z_motor_leadscrew", "binding lead screw / nut") else 0) + (4 * s if self.is_("z_rails") else 0)
        margin = v("z_margin") / load                                               # torque available / torque needed
        lost = max(0.0, 1 - margin)                                                 # share of steps lost while the bed moves
        if self.is_("z_motor_leadscrew", "motor or coupler failed"): home = "Z does not move"; lost = 1.0
        elif lost > 0.6: home = "Z does not move"
        elif lost > 0: sigma += 0.15 * lost; offset += 0.3 * lost; home = "Stops too early" if lost > 0.3 else home
        if self.is_("z_rails"): sigma += 0.03 + 0.05 * s
        if self.is_("bed_plate_carrier", "bed not level (screws)"): tilt = (0.1 + 0.35 * s, self.rnd.uniform(-0.1, 0.1) * s)
        if self.is_("bed_plate_carrier", "plate loose / warped"): sigma += 0.05 + 0.08 * s; tilt = (0.1 * s, 0.1 * s)
        if self.is_("firmware_config_macros", "wrong Z position_endstop"): offset -= 0.12 + 0.3 * (self.s - 0.7) / 0.3
        if self.is_("toolhead"): sigma += 0.02 + 0.04 * s
        offset += self.cfg.get("z_offset", 0.0)
        # the bed must be hot enough for ABS to stick (real bed temperature, not the reading)
        bed_real = self.hp_meas.get("bed_actual_c", 89) - (12 if self.fault == "bed_thermistor" and HP.FAULTS["bed_thermistor"](s)["bed_therm_mode"] == "offset" else 0)
        if self.fault not in ("bed_heater", "bed_thermistor", "bed_thermal_fuse", "power_supply"): bed_real = 89   # a stop for another reason, not a cold bed
        if "bed_temp" in self.cfg: bed_real = min(bed_real, self.cfg["bed_temp"])
        cold_bed = 90 - bed_real > v("bed_ok_c")
        tol = v("squish_tol_mm"); prints = []                                       # gap error (mm) on a 3x3 grid, two prints
        for _ in range(2):
            o = offset + self.rnd.gauss(0, sigma)
            prints.append([o + tilt[0] * (x - 60) / 120 + tilt[1] * (y - 60) / 120 for x in (10, 60, 110) for y in (10, 60, 110)])
        def look(g):
            lo, hi = sum(e < -tol for e in g), sum(e > tol for e in g)
            if lo == 0 and hi == 0: return "Good everywhere"
            if lo == 9: return "Too squished everywhere"
            if hi == 9: return "Too high / not sticking everywhere"
            return "Good on one side, bad on the other"
        looks = [look(g) for g in prints]
        if home in ("Z does not move", "Bed crashes / does not stop") or err: first = None
        elif looks[0] != looks[1] and "Good on one side, bad on the other" not in looks or abs(sum(prints[0]) - sum(prints[1])) / 9 > tol:
            first = "Changes from print to print"
        else: first = looks[0] if looks[0] == looks[1] else "Good on one side, bad on the other"
        if cold_bed and first == "Good everywhere": first = "Too high / not sticking everywhere"
        z_act = round(100 * (1 - min(lost, 1) * 0.5) + self.rnd.gauss(0, 0.03), 2)
        return {"home": home, "error": err, "first": first, "z_act": z_act, "lost": lost, "cold_bed": cold_bed,
                "grid": [round(x, 3) for x in prints[0]], "tilt": tilt, "offset": round(offset, 3)}

    # ---- extrusion -------------------------------------------------------------------------------------------------
    def _extrusion(self):
        s = self.s; temp = v("print_temp"); spd, w, h = v("infill_speed"), v("width"), v("layer_h")
        if self.is_("slicer_settings", "speed / flow too high"): spd, w, h = 160 + 90 * s, 0.5, 0.28
        if self.is_("slicer_settings", "nozzle temperature too low"): temp = 225 - 40 * (s - 0.6) / 0.4
        spd = min(spd, v("max_velocity"))                                          # Klipper clamps to max_velocity
        q = spd * w * h                                                            # mm^3/s asked by the slicer
        cond = 1.0                                                                 # nozzle conductance (1 = clean)
        if self.is_("nozzle"): cond = {"partial clog": 0.75 - 0.6 * s, "heavy clog": 0.25 - 0.2 * s, "full clog": 0.0}[self.mode]
        hp_t = self.hp_meas.get("hotend_actual_c", 245)
        if self.fault == "hotend_thermistor" and HP.FAULTS["hotend_thermistor"](s)["therm_mode"] == "offset": hp_t -= 15   # real temperature is lower
        t_eff = min(temp, hp_t + 5) if hp_t < 240 or self.fault == "hotend_thermistor" else temp
        qmax = v("melt_max_mm3s") * max(0.0, (t_eff - 190) / (250 - 190)) * cond   # melt capacity of the hotend
        rot_err = v("e_rot_dist") / self.cfg.get("e_rotation_distance", v("e_rot_dist"))   # commanded vs. real feed (firmware)
        if self.is_("firmware_config_macros", "wrong extruder rotation_distance"):
            rot_err = 1 + (0.15 + 0.3 * (s - 0.35) / 0.35) * (1 if self.seed % 2 else -1)
        friction = 0.0
        creep = bool(self.hp_log.get("heat_creep_phase")) or self.is_("hotend_fan")
        if creep: friction += 60 + 40 * s                                          # softened filament jams in the heatbreak
        if self.is_("heatbreak_ptfe", "gap between PTFE and nozzle: plug forms"): friction += 40 + 40 * s
        if self.is_("filament_material", "tangled spool"): friction += 80
        grip = v("grip_n")
        if self.is_("extruder_gears_guidler", "guidler too loose"): grip *= (1 - s) ** 2.5
        if self.is_("extruder_gears_guidler", "worn or slipping drive gear"): grip *= 0.45 - 0.3 * s
        if self.is_("filament_material", "wet filament"): grip *= 0.95
        r_drive = v("e_rot_dist") / (2 * math.pi) / 1000
        torque = v("e_motor_nm") * (max(0.03, 0.4 - 0.35 * s) if self.is_("extruder_motor", "weak motor / low current") else 1)
        dead_motor = self.is_("extruder_motor", "open coil")
        f_motor = 0.0 if dead_motor else torque * v("e_gear_ratio") / r_drive
        def need(qq):                                                              # feed force for flow qq
            if qmax <= 0: return 1e9
            L = qq / qmax
            return v("feed_base_n") + v("feed_k_n") * L * L * (1 + 2 * (L - 1) if L > 1 else 1)   # pressure rises steeply past the melt limit
        def run(qq, extra):
            f = need(qq) + extra; lim = min(grip, f_motor)
            ratio = min(1.0, qmax / qq if qq else 1) * (1.0 if f <= lim else max(0.0, (lim / f) ** 1.5))
            if f <= lim: mot = "Turns normally"
            elif dead_motor: mot = "Hums but does not turn" if s < 0.9 else "Does not turn at all"
            elif grip < f_motor: mot = "Gears turn but filament does not move"
            else: mot = "Clicks / jumps back"
            return ratio * rot_err, mot
        q1 = v("first_layer_speed") * w * h
        r_start, m_start = run(q1, 0)                                              # first layer: slow, no creep yet
        r_late, m_late = run(q, friction)                                          # layers 2+: fast, after some minutes
        if self.is_("filament_material", "thin / out-of-tolerance filament"): r_start *= 1 - 0.3 * s; r_late *= 1 - 0.3 * s
        leak = self.is_("heatbreak_ptfe", "gap between PTFE and nozzle: leak")
        if r_start < 0.05 and r_late < 0.05: flow = "Nothing at all"
        elif leak: flow = "Leaks around the nozzle"
        elif r_start > 0.9 and r_late < 0.5 and friction > 0: flow = "Starts fine, then stops mid-print"   # time-dependent jam (creep, plug, tangle)
        elif r_late < 0.92 or r_start < 0.92: flow = "Less than normal / gaps in lines"
        elif r_late > 1.08: flow = "Normal amount but bad quality"                # over-extrusion: blobs, rough top
        elif self.is_("part_cooling_fan") or self.is_("filament_material", "wet filament") or self.motion["ringing"]: flow = "Normal amount but bad quality"
        else: flow = None
        motor = m_late if m_late != "Turns normally" else m_start
        if self.is_("umbilical_wiring") and s > 0.6 and self.rnd.random() < 0.3: motor = "Does not turn at all"
        # extrusion test: 100 mm slowly at the measured temperature (2 mm/s feed = 4.8 mm^3/s), short, so no creep
        f_test = need(4.8) + (40 if self.is_("filament_material", "tangled spool") else 0) + (30 * s if self.is_("heatbreak_ptfe", "gap between PTFE and nozzle: plug forms") else 0)
        lim = min(grip, f_motor); fed = 100 * rot_err * (1.0 if f_test <= lim else max(0.0, (lim / f_test) ** 1.5))
        return {"flow": flow, "motor": motor, "q": round(q, 1), "qmax": round(qmax, 1), "temp": temp, "fed": round(fed + self.rnd.gauss(0, 0.5), 1),
                "spd": spd, "w": w, "h": h, "creep": creep, "r_late": round(r_late, 2), "r_start": round(r_start, 2)}

    # ---- what the technician sees --------------------------------------------------------------------------------------
    def _kind(self):
        o = self.hp_obs
        if self.is_("filament_runout_sensor") or self.is_("filament_material", "tangled spool") and self.s > 0.7:
            return "The printer stops, switches off or restarts"
        if o.get("problem_kind"): return o["problem_kind"]
        if self.z["error"]: return "An error message / Klipper shutdown"
        if self.ext["flow"] in ("Nothing at all", "Less than normal / gaps in lines", "Starts fine, then stops mid-print", "Leaks around the nozzle"):
            return "Plastic problem (none, too little, blobs, leaks)"
        if self.motion["shift"] != "Not a shift problem" or self.motion["noise"] != "No" or self.motion["skew"]: return "Movement problem (layer shift, noise, crash)"
        if self.z["first"] not in (None, "Good everywhere") or self.z["home"] != "Homes correctly": return "First layer / bed problem"
        if o.get("temp_behaviour", "Steady at target") != "Steady at target" or abs(self.hp_meas.get("bed_actual_c", 90) - 90) > 5:
            return "Temperature problem"
        if self.ext["flow"]: return "Plastic problem (none, too little, blobs, leaks)"
        return None

    def observations(self):
        """All observations at once (slot -> option, key -> value); healthy printer gives the normal answers."""
        o = {}; m = {}
        for qid in ("kind", "stop_type", "restart", "cord_wiggle", "psu_led", "runout_check", "other_load", "when", "onset", "change", "error",
                    "hot_temp", "hot_behaviour", "hot_swing", "heater_r", "therm_r", "hot_fan", "fan_v", "flow", "motor", "e_test", "filament",
                    "print_set", "shift", "noise", "by_hand", "axis_test", "belts", "z_home", "first_layer", "bed_temp", "bed_r", "mcu", "wiggle", "volts",
                    "part_fan", "which_temp", "surface", "fuse_r", "crimp_tug", "board_seen"):
            a = self._answer(qid)
            if a: o.update(a[0]); m.update(a[1])
        try:                                   # follow-up questions only apply after a matching answer (e.g. PSU LED only if all power went off)
            from assistant_v2.questions import Q
            for qid, q in Q.items():
                req = q.get("requires")
                if req and q.get("slot") in o and not all(o.get(k) in v for k, v in req.items()): o.pop(q["slot"], None)
        except ImportError: pass
        return o, m

    def answer(self, qid):
        """Answer one question of the assistant like a technician: (facts, measurements) or None = 'I can't tell'."""
        if self.dont_know and self.rnd.random() < self.dont_know: return None
        return self._answer(qid)

    def _answer(self, qid):
        o, mm, s, f = self.hp_obs, self.hp_meas, self.s, self.fault
        kind = self._kind(); C = lambda slot, val: ({slot: val}, {}) if val else None
        if qid in ("flow", "motor", "shift", "first_layer") and not self.printed: return None     # nothing was printed: can't tell
        if qid == "z_home" and not self.homed: return None
        if qid == "what": return C("what_happens", self.describe())
        if qid == "kind": return C("problem_kind", kind)
        if qid == "stop_type":
            if f == "filament_runout_sensor" or self.is_("filament_material", "tangled spool"): return C("stop_type", "The print just pauses")
            if self.ext["flow"] == "Starts fine, then stops mid-print": return C("stop_type", "The head keeps moving but no plastic comes out")
            return C("stop_type", o.get("stop_type") or ("Klipper shows an error and shuts down" if self.z["error"] else None))
        if qid == "restart": return C("restart", o.get("restart"))
        if qid == "cord_wiggle": return C("cord_wiggle", o.get("cord_wiggle") or "No change")
        if qid == "psu_led":
            off = f in ("power_supply",) and s > 0.8 or (f == "mains_power_input" and o.get("restart") is None and o.get("stop_type"))
            return C("psu_led", "No, the LED is off" if off else "Yes, the LED is on")
        if qid == "runout_check":
            if f == "filament_runout_sensor": return C("runout_check", "It says runout, but there IS filament at the sensor")
            if self.is_("filament_material", "tangled spool"): return C("runout_check", "The filament really ran out, broke or tangled")
            return C("runout_check", "No runout message; it pauses another way") if kind else None
        if qid == "other_load": return C("other_load", "No")
        if qid == "when":
            w = o.get("when") or self.motion["when"]
            if not w and self.ext["flow"] == "Starts fine, then stops mid-print": w = "After some minutes of printing"
            if not w and f == "filament_runout_sensor": w = "Randomly"
            if not w and f in ("umbilical_wiring", "hotend_thermistor") and o.get("temp_behaviour") == "Jumps suddenly (spikes or drops)": w = "Only when the head moves"
            if not w and kind: w = "All the time"
            return C("when", w)
        if qid == "onset":
            if not kind: return None
            slow = {"x_linear_rail", "y_linear_rails", "xy_belts", "nozzle", "filament_material", "z_rails", "toolhead", "umbilical_wiring", "xy_pulleys_idlers"}
            changed = {"firmware_config_macros", "slicer_settings"}
            return C("onset", "Right after I changed something" if f in changed else "Got worse slowly" if f in slow else "Suddenly")
        if qid == "change":
            txt = {"firmware_config_macros": "I edited printer.cfg last week", "slicer_settings": "I changed my slicer profile to print faster" if (self.mode or "").startswith("speed") else "I tried a lower temperature",
                   "filament_material": "new spool, it was stored open"}.get(f, "nothing")
            return C("recent_change", txt)
        if qid == "error":
            err = o.get("error_message") or self.z["error"] or ("Filament runout detected" if f == "filament_runout_sensor" else None)
            if self.is_("slicer_settings", "nozzle temperature too low") and self.ext["temp"] < v("min_extrude_c"): err = "Extrude below minimum temp"
            return C("error_message", err or "none")
        if qid == "hot_temp": return ({}, {"hotend_target_c": mm.get("hotend_target_c", 250) if not f == "slicer_settings" else round(self.ext["temp"]),
                                         "hotend_actual_c": mm.get("hotend_actual_c", 245)})
        if qid == "hot_behaviour":
            tb = o.get("temp_behaviour", "Steady at target")
            if tb != "Steady at target" and f not in HOT_SET:           # the print stopped for another reason: the hotend
                tb = None if self.hp_log.get("off_phase") in ("heat", "idle", "connect", "home") else "Steady at target"   # was still warming up
            return C("temp_behaviour", tb)
        if qid == "hot_swing": return ({}, {"hotend_swing_c": mm.get("hotend_swing_c", 0)})
        if qid == "heater_r":
            r = HP.P["hotend_r"] if f != "hotend_heater" else HP.FAULTS["hotend_heater"](s)["hotend_r"]
            if f == "umbilical_wiring" and s > 0.85: r = float("inf")
            return ({}, {"hotend_heater_ohm": "open" if r == float("inf") else round(r * (1 + self.rnd.gauss(0, 0.01)), 1)})
        if qid == "therm_r":
            mode = HP.FAULTS["hotend_thermistor"](s)["therm_mode"] if f == "hotend_thermistor" else None
            if mode == "open": val = "open"
            elif mode == "offset": val = round(ntc_res(self.room + 15))
            elif f == "umbilical_wiring" and s > 0.85: val = "open"
            else: val = round(ntc_res(self.room) * (1 + self.rnd.gauss(0, 0.01)))
            return ({}, {"hotend_thermistor_ohm": val, "room_c": self.room})
        if qid == "hot_fan":
            if f == "hotend_fan": return C("fan_state", "No")
            if f == "umbilical_wiring": return C("fan_state", "It stutters / stops sometimes")
            if f == "controller_board" and o.get("mcu_state", "").startswith("Disconnects"): return C("fan_state", "I can't tell")
            return C("fan_state", "Yes, always")
        if qid == "fan_v":
            if not self.homed or self.hp_log.get("mcu_lost") or self.hp_log.get("power_lost") or o.get("stop_type", "").startswith("Everything"):
                return ({}, {"fan_v": 0.0}) if not self.homed else None   # board not running: the fan output is off / nothing to measure
            val = mm.get("fan_v", 24.0)
            if f == "umbilical_wiring": val = round(self.rnd.choice([0.0, 24.0, 11.0]), 1)
            return ({}, {"fan_v": val})
        if qid == "flow": return C("flow_state", self.ext["flow"] or ("Normal amount but bad quality" if kind else None))
        if qid == "motor": return C("motor_behaviour", self.ext["motor"])
        if qid == "e_test": return ({}, {"extrude_cmd_mm": 100, "extrude_act_mm": max(0.0, self.ext["fed"])})
        if qid == "filament":
            txt = {"wet filament": "ABS, spool open for months, it pops and crackles when extruding",
                   "tangled spool": "ABS, the spool looks tangled and the filament is pulled tight",
                   "thin / out-of-tolerance filament": "cheap ABS, the diameter varies along the spool"}.get(self.mode if f == "filament_material" else "", "ABS, normal spool, nothing unusual")
            return C("filament", txt)
        if qid == "print_set": return ({}, {"print_temp_c": round(self.ext["temp"]), "print_speed_mms": round(self.ext["spd"]),
                                           "layer_height_mm": self.ext["h"], "line_width_mm": self.ext["w"]})
        if qid == "shift": return C("shift_axis", self.motion["shift"])
        if qid == "noise": return C("noise", self.motion["noise"])
        if qid == "by_hand": return C("move_by_hand", self.motion["by_hand"])
        if qid == "axis_test":
            z = f in ("z_motor_leadscrew", "z_rails")
            return ({}, {"axis_name": "Z" if z else self.motion["axis"], "axis_cmd_mm": 100, "axis_act_mm": self.z["z_act"] if z else self.motion["axis_act"]})
        if qid == "belts":
            hz = self.motion["belt_hz"]; n = lambda x: round(x + self.rnd.gauss(0, 1.5))
            return ({}, {"belt_a_hz": n(hz["a"]), "belt_b_hz": n(hz["b"])})
        if qid == "z_home": return C("z_home", self.z["home"])
        if qid == "first_layer": return C("first_layer", self.z["first"])
        if qid == "bed_temp": return ({}, {"bed_target_c": mm.get("bed_target_c", 90), "bed_actual_c": mm.get("bed_actual_c", 89)})
        if qid == "bed_r":
            r = HP.P["bed_r"] if f not in ("bed_heater", "bed_thermal_fuse") else HP.FAULTS[f](s)["bed_r"]
            return ({}, {"bed_heater_ohm": "open" if r == float("inf") else round(r * (1 + self.rnd.gauss(0, 0.01)), 1)})
        if qid == "mcu": return C("mcu_state", o.get("mcu_state", "Yes, always"))
        if qid == "fuse_r": return C("fuse_state", "Open (OL)" if f == "bed_thermal_fuse" else "About 0 ohm (closed)")
        if qid == "crimp_tug": return C("crimp_tug", "Yes, it resets or flickers" if f == "dc_power_wiring" and s > 0.3 else "No change")
        if qid == "board_seen":
            dead = (f == "controller_board" and HP.FAULTS["controller_board"](s)["mcu_dead"]) or not self.homed and f in ("dc_power_wiring", "power_supply")
            return C("board_seen", "No, it is missing" if dead else "Yes, it is listed")
        if qid == "surface":
            if not self.printed: return None
            mo, e = self.motion, self.ext
            if f == "part_cooling_fan": v_ = "Drooping overhangs, curled corners"
            elif mo["skew"]: v_ = "Skewed: squares are not square"
            elif f == "toolhead" or mo["ringing"]: v_ = "Ringing / ghosting (ripples after corners)"
            elif self.is_("filament_material", "wet filament"): v_ = "Stringing, rough or bubbly surface"
            elif e.get("r_late", 1) > 1.08: v_ = "Blobs, too much plastic"
            elif f in ("z_motor_leadscrew", "z_rails") and self.z["lost"] > 0: v_ = "Wavy or uneven layer lines (Z banding)"
            elif e["flow"] in ("Less than normal / gaps in lines", "Nothing at all", "Starts fine, then stops mid-print"): return None   # answered by the flow question
            else: v_ = "Looks fine"
            return C("surface", v_)
        if qid == "part_fan":
            if not self.printed or self.hp_log.get("off_phase") in ("layer1", "layers2"): return None   # never reached layer 4
            spins = f != "part_cooling_fan" and not (f == "umbilical_wiring" and self.rnd.random() < .4)
            return C("part_fan_state", "Yes, it spins" if spins else "No, it does not spin")
        if qid == "which_temp":
            hot_bad = (o.get("temp_behaviour", "Steady at target") != "Steady at target" and f in HOT_SET) or f in ("hotend_heater", "hotend_thermistor")
            bed_bad = f in ("bed_heater", "bed_thermistor", "bed_thermal_fuse") or abs(mm.get("bed_actual_c", 89) - 90) > 6 and f in ("power_supply",)
            if f in ("umbilical_wiring",): hot_bad = True
            return C("which_temp", "Both" if hot_bad and bed_bad else "The hotend" if hot_bad else "The bed" if bed_bad else "Neither, both look normal")
        if qid == "wiggle":
            yes = f in ("umbilical_wiring",) or (f == "hotend_thermistor" and HP.FAULTS[f](s)["therm_mode"] == "intermittent")
            return C("wiggle", "Yes, it appears or gets worse" if yes else "No change")
        if qid == "volts":
            rail = 5.05 - (0.5 * s if f == "power_supply" else 0) - (0.3 * s if f == "host_computer" else 0)
            psu = mm.get("psu_v", 23.9) if f not in ("mains_power_input",) else 23.9
            return ({}, {"psu_v": psu, "rail_5v_v": round(rail, 2)})
        return None

    def describe(self):
        """One short sentence a technician might type first (never names the part)."""
        o = self.hp_obs; e = self.ext; mo = self.motion; z = self.z; f = self.fault
        if f == "filament_runout_sensor": return "The print keeps pausing by itself in the middle of the job, I resume and it pauses again later"
        if o.get("stop_type", "").startswith("Everything goes off"): return "The whole printer switches off during the print, the Pi and fans go off too" + (" and it comes back on" if o.get("restart") else "")
        if o.get("error_message", "").startswith("web"): return "The web interface does not load at all, I cannot reach the printer"
        if "Unable to connect" in o.get("error_message", ""): return f"Klipper does not start, it says '{o['error_message']}'"
        if o.get("error_message"): return f"Klipper stops the print with the error '{o['error_message']}' {('while heating' if o.get('when') == 'Only while heating' else 'during the print')}"
        if z["error"]: return f"Homing fails with '{z['error']}'"
        if e["flow"] == "Nothing at all": return "No plastic comes out of the nozzle at all, the extruder " + ("clicks" if e["motor"].startswith("Clicks") else "does not push")
        if e["flow"] == "Starts fine, then stops mid-print": return "The print starts fine but after some minutes the extrusion stops and the head keeps moving in the air"
        if e["flow"] == "Leaks around the nozzle": return "Plastic leaks out around the top of the nozzle and makes blobs on the print"
        if e["flow"] == "Less than normal / gaps in lines": return "The walls are thin with gaps between the lines, it looks under-extruded" + (", the extruder clicks" if e["motor"].startswith("Clicks") else "")
        if mo["shift"] != "Not a shift problem": return "My prints have layer shifts, the layers move sideways partway up" + (" with a loud clicking sound" if mo["noise"].startswith("Click") else "")
        if mo["noise"] != "No": return f"There is a {mo['noise'].split(' /')[0].lower()} noise when the head moves"
        if mo["skew"]: return "My prints come out skewed, squares are not square and diagonal lines look off"
        if z["home"] != "Homes correctly": return "Something is wrong when Z homes: " + z["home"].lower()
        if z["first"] not in (None, "Good everywhere"): return "The first layer is not right: " + z["first"].lower()
        if o.get("temp_behaviour", "Steady at target") != "Steady at target": return "The hotend temperature " + o["temp_behaviour"].lower()
        if abs(self.hp_meas.get("bed_actual_c", 89) - 90) > 5: return f"The bed only reaches about {self.hp_meas['bed_actual_c']} C instead of 90"
        if e["flow"]: return "The prints look bad, " + ("overhangs droop and corners curl" if f == "part_cooling_fan" else "stringy and rough surfaces" if f == "filament_material" else "ringing and ghosting on the walls")
        return "Everything looks normal" if f is None else "Something seems slightly off but I cannot say what"

    # ---- what the 3D view needs ------------------------------------------------------------------------------------
    def visual(self):
        """Everything the 3D viewer shows: the print as it comes out, moving parts, temperatures over time."""
        lg, mo, z, e, f, s = self.hp_log, self.motion, self.z, self.ext, self.fault, self.s
        ph_layer = {"idle": 0, "connect": 0, "home": 0, "heat": 0, "layer1": 1, "layers2": 2, "layers4": 5}
        stop_layer = ph_layer.get(lg.get("off_phase"), None) if lg.get("off_phase") else None
        if f in ("filament_runout_sensor",): stop_layer = None
        rnd = random.Random(self.seed + 7)
        shift = None
        if mo["shift"] != "Not a shift problem":
            kinds = set().union(*mo["skips"].values())
            motors = {m for _, m, _ in kinds}
            if len(motors) == 1:   # CoreXY: one motor slipping moves the head along a diagonal
                d = (1, 1) if "a" in motors else (1, -1)
            elif mo["shift"] == "X only": d = (1, 0)
            elif mo["shift"] == "Y only": d = (0, 1)
            else: d = (1, 1)
            mag = 0.8 + 2.5 * s
            shift = {"from_layer": 2 if mo["when"] == "Right after the first layer" else 1 + rnd.randint(1, 3),
                     "dx": round(d[0] * mag / math.hypot(*d), 2), "dy": round(d[1] * mag / math.hypot(*d), 2), "every": rnd.randint(4, 8)}
        flow_stop = 6 if e["flow"] == "Starts fine, then stops mid-print" else None
        n = len(lg["hot"]); step = max(1, n // 120)
        off_all = bool(lg.get("events")) and not lg.get("mcu_lost")
        return {
            "fault": f, "mode": self.mode, "severity": round(s, 2), "says": self.describe(), "printed": self.printed, "homed": self.homed,
            "stop_layer": stop_layer, "power_lost": off_all, "restarted": bool(lg.get("restarted")), "errors": lg.get("errors", []) + ([z["error"]] if z["error"] else []),
            "shift": shift, "skew_deg": round(1.5 * (1 - mo["belt_hz"]["b"] / mo["belt_hz"]["a"]) * 10, 2) if mo["skew"] else 0,
            "ringing": mo["ringing"], "noise": mo["noise"], "belt_hz": {k: round(x) for k, x in mo["belt_hz"].items()},
            "flow_start": round(min(1.3, max(0.0, e.get("r_start", 1.0))), 2),
            "flow_late": round(min(1.3, max(0.0, e.get("r_late", 1.0))), 2), "flow_stop_layer": flow_stop, "leak": e["flow"] == "Leaks around the nozzle",
            "flow": e["flow"], "e_motor": e["motor"], "creep": e["creep"],
            "first_layer": z["first"], "z_home": z["home"], "bed_tilt": z["tilt"], "z_offset": z["offset"], "z_grid": z["grid"],
            "hotend_fan": not (f == "hotend_fan") and self.homed, "part_fan": f != "part_cooling_fan" and self.printed,
            "umbilical_flicker": f == "umbilical_wiring", "runout_pause": f == "filament_runout_sensor",
            "hot": lg["hot"][::step], "bed": lg["bed"][::step], "psu_v": lg["psu_v"][::step], "dt": step,
            "off_phase": lg.get("off_phase"), "measurements": self.observations()[1], "answers": self.observations()[0],
        }

COVERED = set(PARTS)

def run_case(fault, severity=None, seed=0):
    """Same interface as heat_power.run_case: all observations of a printer with this fault."""
    return VirtualPrinter(fault if fault in COVERED else None, severity, seed).observations()

if __name__ == "__main__":
    import sys
    parts = sys.argv[1:] or [None] + PARTS
    for p in parts:
        vp = VirtualPrinter(p if p != "healthy" else None, seed=3)
        o, m = vp.observations()
        print(f"\n== {p or 'healthy'} ({vp.mode or '-'}, severity {vp.s:.2f})\n  says: {vp.describe()}\n  answers: {o}\n  measured: {m}")
