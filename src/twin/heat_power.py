"""Digital twin, stage 1: heat and power of the Voron 0.2 over one print.

A simple behavioural simulation (1-second steps) built from the design values. It is not a CAD/physics-engine copy:
it models how energy and signals flow, so a fault injected in one part shows its effects where a technician sees them.

Simulated chain:  wall -> cord/inlet contact -> PSU (24 V, 150 W, overload protection) -> 24 V wiring/crimp
                  -> controller board -> hotend heater / bed heater / fans  (+ 5 V rail -> Raspberry Pi)
                  thermistors -> Klipper (PID control, verify_heater, ADC range check, heater_fan at 50 C)
                  toolhead cable (umbilical) carries heater, thermistor and fan wires and moves with the head.
Print phases (Voron slicer profile): power-on, connect, home, heat, layer 1 (30 mm/s), layers 2-3 (100-125 mm/s,
part fan off), layer 4+ (part fan on).  Vibration = how hard the frame and cables shake (rises ~4x after layer 1).

Sources of values: config (PID, max_temp, heater_fan 50 C), BOM (24 V, 150 W PSU, 60 W bed), slicer profile (speeds,
fan from layer 4, temperatures), Klipper verify_heater / ADC behaviour. Values not in the documents (hotend
cartridge 40 W, thermal masses, contact resistances) are marked GENERAL and only shape the curves.
"""
import math, random

GENERAL = "general engineering value (not in the project documents)"
P = {
    "supply_v": 24.0, "psu_w": 150.0, "psu_ocp": 1.3,           # BOM; OCP ~130 % of rating (GENERAL)
    "hotend_r": 14.4,                                             # 40 W at 24 V (GENERAL: wattage not in docs)
    "bed_r": 9.6,                                                 # 24^2 / 60 W (BOM)
    "hotend_c": 12.0, "hotend_rth": 8.0, "hotend_rth_fan": 6.5,   # J/K, K/W (GENERAL)
    "bed_c": 250.0, "bed_rth": 1.3,                               # J/K, K/W (GENERAL)
    "pid": (28.182, 1.978, 100.397), "bed_pid": (68.453, 2.749, 426.122),   # config lines 158-160, 197-199
    "hotend_max": 270, "bed_max": 120, "fan_on_c": 50,            # config
    "target_hotend": 250, "target_bed_l1": 100, "target_bed": 90, # slicer profile
    "base_load_w": 25.0, "motor_load_w": {"idle": 5, "connect": 5, "home": 15, "heat": 5, "layer1": 15, "layers2": 30, "layers4": 30},
    "vibration": {"idle": 0.0, "connect": 0.0, "home": 0.6, "heat": 0.05, "layer1": 0.3, "layers2": 1.0, "layers4": 1.0},
    "verify_gain": 2.0, "verify_time_hotend": 20, "verify_time_bed": 60, "verify_max_error": 120,  # Klipper defaults
}
PHASES = [("idle", 20), ("connect", 10), ("home", 20), ("heat", 400), ("layer1", 180), ("layers2", 240), ("layers4", 600)]

# ---------------------------------------------------------------------------------------------------
FAULTS = {   # (part, mode index) -> parameters changed, with a severity drawn per run
 "mains_power_input":  lambda s: {"mains_contact_vib": 0.02 + 0.08 * s},             # opens under vibration
 "power_supply":       lambda s: {"psu_capacity_w": 150 - 70 * s, "rail_5v": 5.05 - 0.5 * s},
 "dc_power_wiring":    lambda s: {"crimp_r": 0.15 + 0.6 * s, "crimp_vib": 0.01 + 0.05 * s},
 "controller_board":   lambda s: {"mcu_dead": s > 0.5, "mcu_drop": 0.002 + 0.01 * s},
 "host_computer":      lambda s: {"host_dead": s > 0.6, "host_drop": 0.001 + 0.006 * s},
 "hotend_heater":      lambda s: {"hotend_r": 14.4 * (1 + 3 * s) if s < 0.8 else float("inf")},
 "hotend_thermistor":  lambda s: {"therm_mode": "open" if s > 0.66 else ("offset" if s > 0.33 else "intermittent")},
 "umbilical_wiring":   lambda s: {"umb_vib": 0.05 + 0.25 * s},                       # toolhead wires cut out with motion
 "hotend_fan":         lambda s: {"hotend_fan_dead": True},
 "part_cooling_fan":   lambda s: {"part_fan_dead": True},
 "bed_heater":         lambda s: {"bed_r": 9.6 * (1 + 2 * s) if s < 0.7 else float("inf")},
 "bed_thermistor":     lambda s: {"bed_therm_mode": "open" if s > 0.5 else "offset"},
 "bed_thermal_fuse":   lambda s: {"bed_r": float("inf")},
 "firmware_config_macros": lambda s: {"pid_scale": 3 + 4 * s},                        # badly tuned PID
}
COVERED = set(FAULTS)

def simulate(fault=None, severity=0.5, seed=0, idle_wiggle=False):
    """Run one print. Returns observations a technician could make (see observe())."""
    rnd = random.Random(seed); q = dict(P); f = FAULTS[fault](severity) if fault in FAULTS else {}
    q.update({k: v for k, v in f.items() if k in q})
    Th = Tb = Ths = 22.0; ih = ib = 0.0; eh_prev = eb_prev = 0.0
    log = {"events": [], "off_phase": None, "restarted": None, "errors": [], "hot": [], "bed": [], "fan_v": [], "psu_v": [],
           "pi_reboot": False, "mcu_lost": False, "heat_creep_phase": None, "stuck_off": False}
    t = 0; power_on = True; mcu_ok = not f.get("mcu_dead"); host_ok = not f.get("host_dead"); off_since = None
    if not host_ok: log["errors"].append("web interface does not load"); log["off_phase"] = "idle"
    if not mcu_ok: log["errors"].append("mcu 'mcu': Unable to connect"); log["mcu_lost"] = True; log["off_phase"] = "connect"
    phases = [("idle", 60)] if idle_wiggle else PHASES        # the cord test is done with the printer idle
    for phase, dur in phases:
        if log["errors"] and any(e.startswith(("ADC", "Heater", "mcu", "web", "Lost")) for e in log["errors"]): break
        for _ in range(dur):
            t += 1; vib = q["vibration"][phase] + (0.5 if idle_wiggle else 0)
            # --- mains contact and PSU ---------------------------------------------------------------
            if power_on and rnd.random() < f.get("mains_contact_vib", 0) * vib:
                power_on = False; off_since = t; log["off_phase"] = log["off_phase"] or phase; log["events"].append(f"power lost ({phase})")
            elif not power_on and off_since and t - off_since > 3:
                power_on = True; log["restarted"] = "Comes back on by itself after a moment"; log["pi_reboot"] = True
                break                                                    # the Pi rebooted: the print is lost
            heating = phase in ("heat", "layer1", "layers2", "layers4")
            tgt_h = q["target_hotend"] if heating else 0; tgt_b = (q["target_bed_l1"] if phase in ("heat", "layer1") else q["target_bed"]) if heating else 0
            # PID (positional form, clipped duty 0..1)
            kp, ki, kd = q["pid"]; sc = f.get("pid_scale", 1.0)
            meas_h = read_therm(Th, f.get("therm_mode"), vib, f.get("umb_vib", 0), rnd)
            if f.get("pid_scale") and heating and phase != "heat" and meas_h is not None:   # badly tuned PID: steady oscillation
                meas_h += (4 + 2 * f["pid_scale"]) * math.sin(2 * math.pi * t / 40)
            eh = tgt_h - (meas_h if meas_h is not None else 999); ih = max(-50, min(50, ih + eh)) if tgt_h else 0
            duty_h = max(0.0, min(1.0, (sc * kp * eh + ki * ih + kd * (eh - eh_prev) / sc) / 255)) if tgt_h else 0; eh_prev = eh
            kb, kib, kdb = q["bed_pid"]; meas_b = read_bed(Tb, f.get("bed_therm_mode"))
            eb = tgt_b - (meas_b if meas_b is not None else 999); ib = max(-50, min(50, ib + eb)) if tgt_b else 0
            duty_b = max(0.0, min(1.0, (kb * eb + kib * ib + kdb * (eb - eb_prev)) / 255)) if tgt_b else 0; eb_prev = eb
            # electrical load and supply
            v = q["supply_v"]
            umb_open = rnd.random() < f.get("umb_vib", 0) * vib
            ph = 0 if (umb_open or not power_on) else duty_h * v * v / q["hotend_r"] if q["hotend_r"] != float("inf") else 0
            pb = 0 if not power_on else duty_b * v * v / q["bed_r"] if q["bed_r"] != float("inf") else 0
            load = ph + pb + q["base_load_w"] + q["motor_load_w"][phase]
            cap = f.get("psu_capacity_w", q["psu_w"])
            droop = 0.02 if fault != "power_supply" else 0.04 + 0.5 * severity      # V per 10 W of load (weak supply sags)
            if power_on: log["psu_v"].append(round(v - droop * load / 10, 2))
            if power_on and load > cap * q["psu_ocp"] * 0.8 + (0 if fault == "power_supply" else 999):
                power_on = False; off_since = t; log["off_phase"] = log["off_phase"] or phase
                log["events"].append(f"PSU overload protection ({phase}, {load:.0f} W)"); log["restarted"] = "Comes back on by itself after a moment"; break
            v_board = v - (load / v) * f.get("crimp_r", 0.0)
            if power_on and (rnd.random() < f.get("crimp_vib", 0) * vib or v_board < 20.5):
                log["mcu_lost"] = True; log["errors"].append("Lost communication with MCU 'mcu'"); log["off_phase"] = log["off_phase"] or phase; break
            if power_on and rnd.random() < f.get("mcu_drop", 0) * (1 + vib):
                log["mcu_lost"] = True; log["errors"].append("Lost communication with MCU 'mcu'"); log["off_phase"] = log["off_phase"] or phase; break
            if power_on and rnd.random() < f.get("host_drop", 0):
                log["errors"].append("Timer too close" if rnd.random() < .5 else "Lost communication with MCU 'mcu'"); log["off_phase"] = log["off_phase"] or phase; break
            if f.get("rail_5v", 5.05) < 4.75 and heating and rnd.random() < 0.01:
                log["pi_reboot"] = True; log["errors"].append("Lost communication with MCU 'mcu'"); log["off_phase"] = log["off_phase"] or phase; break
            # --- thermal ------------------------------------------------------------------------------------
            fan_h = power_on and not f.get("hotend_fan_dead") and not umb_open and Th > q["fan_on_c"]
            fan_p = power_on and not f.get("part_fan_dead") and phase == "layers4" and not umb_open
            rth = q["hotend_rth_fan"] if fan_p else q["hotend_rth"]
            Th += (ph - (Th - 22) / rth) / q["hotend_c"]
            Tb += (pb - (Tb - 22) / q["bed_rth"]) / q["bed_c"]
            Ths += ((Th - Ths) * 0.004 - (Ths - 22) * (0.03 if fan_h else 0.002))      # heatsink above the heatbreak
            if Ths > 70 and heating and not log["heat_creep_phase"]: log["heat_creep_phase"] = phase
            log["fan_v"].append(24.0 if (fan_h or (f.get("hotend_fan_dead") and power_on and Th > q["fan_on_c"])) and not umb_open else 0.0)
            log["hot"].append(round(meas_h if meas_h is not None else -1, 1)); log["bed"].append(round(meas_b if meas_b is not None else -1, 1))
            # --- Klipper safety checks ------------------------------------------------------------------------
            if meas_h is None or (meas_h is not None and meas_h > q["hotend_max"]):
                log["errors"].append("ADC out of range"); log["off_phase"] = log["off_phase"] or phase; break
            if meas_b is None: log["errors"].append("ADC out of range"); log["off_phase"] = log["off_phase"] or phase; break
            if phase == "heat" and t % q["verify_time_hotend"] == 0 and tgt_h and meas_h < tgt_h - 10 and len(log["hot"]) > q["verify_time_hotend"]:
                if meas_h - log["hot"][-q["verify_time_hotend"]] < q["verify_gain"] and power_on:
                    log["errors"].append("Heater extruder not heating at expected rate"); log["off_phase"] = phase; break
            if phase == "heat" and t % q["verify_time_bed"] == 0 and tgt_b and meas_b < tgt_b - 10 and len(log["bed"]) > q["verify_time_bed"]:
                if meas_b - log["bed"][-q["verify_time_bed"]] < q["verify_gain"] and power_on:
                    log["errors"].append("Heater heater_bed not heating at expected rate"); log["off_phase"] = phase; break
            if heating and phase != "heat" and tgt_h and abs(tgt_h - meas_h) > q["verify_max_error"] / 4 and rnd.random() < 0.02:
                log["errors"].append("Heater extruder not heating at expected rate"); log["off_phase"] = phase; break
            if phase == "heat" and (Th >= tgt_h - 2 or not tgt_h) and (Tb >= tgt_b - 2 or not tgt_b) and t > 60: break
        else:
            continue
        if log["errors"]: break
    if log["off_phase"] and log["restarted"] is None and fault in ("mains_power_input", "power_supply"): log["stuck_off"] = True
    return log

def read_therm(T, mode, vib, umb, rnd):
    if mode == "open": return None
    if mode == "offset": return T + 15
    if (mode == "intermittent" and rnd.random() < 0.08 * (vib + 0.2)) or (umb and rnd.random() < umb * vib):
        return T - rnd.choice([40, 60, 90]) if rnd.random() < 0.8 else None
    return T

def read_bed(T, mode):
    if mode == "open": return None
    if mode == "offset": return T + 12
    return T

# ---------------------------------------------------------------------------------------------------------
def observe(log, wiggle_log=None):
    """Turn a simulation log into the answers of the assistant's questions (slot -> option, measurement -> value)."""
    o, m = {}, {}
    ph = log["off_phase"]
    if log["errors"]: o["error_message"] = log["errors"][0]
    if ph:
        o["problem_kind"] = ("An error message / Klipper shutdown" if log["errors"] and not log["events"]
                             else "The printer stops, switches off or restarts")
        if log["events"] and not log["mcu_lost"]: o["stop_type"] = "Everything goes off: lights, fans, Raspberry Pi"
        elif log["mcu_lost"]: o["stop_type"] = "The Pi stays on, but motors and heaters stop ('Lost communication' / MCU error)"
        elif log["errors"]: o["stop_type"] = "Klipper shows an error and shuts down"
        o["when"] = {"idle": "All the time", "connect": "All the time", "home": "All the time", "heat": "Only while heating",
                     "layer1": "Only while heating", "layers2": "Right after the first layer", "layers4": "After some minutes of printing"}[ph]
        if log["restarted"]: o["restart"] = log["restarted"]
        elif log["stuck_off"]: o["restart"] = "Stays off until I switch it on again"
    hot = [x for x in log["hot"] if x >= 0]
    if hot:
        tail = hot[-60:]; sw = (max(tail) - min(tail)) / 2
        m["hotend_target_c"] = 250; m["hotend_actual_c"] = round(sum(tail) / len(tail))
        jumps = any(abs(a - b) > 20 for a, b in zip(hot, hot[1:]))
        o["temp_behaviour"] = ("Jumps suddenly (spikes or drops)" if jumps else "Swings slowly up and down" if sw > 4
                               else "Rises slowly / never reaches target" if m["hotend_actual_c"] < 235 else "Steady at target")
        m["hotend_swing_c"] = round(min(sw, 120))
    bed = [x for x in log["bed"] if x >= 0]
    if bed:
        m["bed_target_c"] = 90; m["bed_actual_c"] = round(sum(bed[-60:]) / len(bed[-60:]))
    if log["heat_creep_phase"]:
        o["flow_state"] = "Starts fine, then stops mid-print"; o.setdefault("when", "After some minutes of printing")
    fv = log["fan_v"]
    if fv: m["fan_v"] = max(fv)
    if log["psu_v"]: m["psu_v"] = min(v for v in log["psu_v"] if v > 0) if any(v > 0 for v in log["psu_v"]) else 24.0
    o["mcu_state"] = ("Disconnects / 'Lost communication' during prints" if log["mcu_lost"] and ph not in ("idle", "connect")
                      else "'MCU unable to connect' at start" if log["mcu_lost"] else
                      "The web page itself does not load" if "web interface does not load" in log["errors"] else "Yes, always")
    if wiggle_log is not None:
        o["cord_wiggle"] = "Yes, it flickers or switches off" if wiggle_log["events"] else "No change"
    return o, m

def run_case(fault, severity=None, seed=0):
    """Simulate a print with the fault plus an idle 'wiggle the cord' test; return (facts, measurements)."""
    rnd = random.Random(seed); s = severity if severity is not None else rnd.uniform(0.2, 0.95)
    log = simulate(fault, s, seed)
    wig = simulate(fault, s, seed + 1, idle_wiggle=True) if fault in ("mains_power_input", "power_supply", "dc_power_wiring") else None
    return observe(log, wig)

if __name__ == "__main__":
    for fault in [None] + sorted(FAULTS):
        o, m = run_case(fault, seed=3)
        print(f"\n{fault or 'healthy'}:\n  answers: {o}\n  measurements: {m}")
