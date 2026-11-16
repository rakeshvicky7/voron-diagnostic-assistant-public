"""FMEA-graph diagnosis engine: text -> observed symptoms -> failure modes -> parts, and the next best question.

Graph:  part --has--> failure mode --shows--> symptom   (kb_modes.M, kb_symptoms.S; every edge has P(symptom | mode) and a source)
1. link(text):      which symptoms the technician described (phrase matching with stems and negation; optional embeddings)
2. posterior(ev):   Bayes over failure modes (noisy evidence, leak for unexplained symptoms), summed per part
3. next_question(): the yes/no symptom question with the best expected information gain per effort
4. Session:         a whole conversation (describe -> questions -> conclusion -> 'this part is fine' -> continue)
No language model is needed. Runs in milliseconds.
"""
import math, re, os
try:
    from .kb_symptoms import S
    from .kb_modes import M
except ImportError:
    from kb_symptoms import S
    from kb_modes import M

LEAK = {"context": 0.12}          # P(symptom | a mode that does not list it); contexts are often true anyway
LEAK_DEFAULT = 0.03
COST = {"look": 1.0, "listen": 1.0, "screen": 1.0, "context": 0.8, "feel": 1.3, "test": 1.4, "measure": 2.2}
MODES = {m["id"]: m for m in M}
_PT = {}
for _m in M: _PT[_m["part"]] = _PT.get(_m["part"], 0) + _m.get("prior", 1.0)
AGG = os.environ.get("F_AGG", "sum")          # part score = sum of its failure modes ("sum", validated) or its best mode ("max", tested: better on dev, worse on held-out)
PRIOR = {m["id"]: (m.get("prior", 1.0) / _PT[m["part"]] if os.environ.get("F_PRIOR", "norm") == "norm" else m.get("prior", 1.0)) for m in M}
PARTS = sorted({m["part"] for m in M})

# ---------------------------------------------------------------- text -> symptoms
STOP = set(("a an the of to is are was were be been it its this that and or for my me i we our you your so very really just then "
             "does do did doe on in at by from when while with as has have had can could will would there here some any").split())
NEG = re.compile(r"\b(no|not|never|without|n't|dont|doesnt|didnt|isnt|wasnt|cannot|cant)\b")
OK_AFTER = re.compile(r"\b(looks?|is|seems?|stays?|are|was)\s+(normal|fine|ok|okay|stable|steady|correct|good)\b")

PRINTS_FINE = re.compile(r"\b(prints?|print quality|parts?|results?)\b[^.,;]{0,20}\b(look|looks|are|is|come out|comes out)\s+(fine|good|ok|okay|perfect|normal|great)\b|\bprint(s|ing)? (fine|perfectly|well|normally)\b")
QUALITY = ("under_extrusion", "over_extrusion", "layer_shift", "ringing", "stringing", "z_banding", "skew", "fl_high", "fl_squish", "fl_one_side", "fl_varies", "no_extrusion")

USE_PRINTS_FINE = os.environ.get("F_PRINTS_FINE", "0") == "1"

def stem(w):
    for suf in ("ings", "ing", "edly", "ed", "es", "s", "ly"):
        if len(w) > len(suf) + 2 and w.endswith(suf): return w[: -len(suf)]
    return w

def toks(t):
    t = t.lower().replace("-", " ").replace("_", " ")
    return [stem(w) for w in re.findall(r"[a-z0-9]+(?:'[a-z]+)?", t) if w not in STOP]

KLIPPER = [  # Klipper's exact messages -> symptoms (KLP common errors / config reference)
 (r"adc out of ra?n?a?ge|adc (error|out of)", ["adc_error"]), (r"lost communication|timeout with mcu|mcu .{0,20}shutdown", ["lost_comm"]),
 (r"unable to connect|serial.{0,20}not found|no such file or directory.{0,30}serial", ["unable_connect"]),
 (r"timer too close|rescheduled timer", ["timer_close"]), (r"move out of range|move exceeds", ["move_range"]),
 (r"heater[ _]heater_bed not heating|heater_bed not heating|bed not heating at expected", ["bed_not_heat"]),
 (r"heater[ _]extruder not heating|extruder not heating at expected", ["hot_not_heat"]),
 (r"extrude below minimum temp", ["cold_extrude"]), (r"endstop .{0,10}still triggered", ["z_early"]),
 (r"option .{0,40} must be specified|pin .{0,40}(reserved|used multiple|unknown)|unknown pin|unable to parse|section .{0,30} not (found|valid)|config(uration)? error|invalid .{0,20}(pin|option)|error in printer\.cfg", ["cfg_error"]),
 (r"filament runout|runout detected", ["runout_msg"]), (r"under.?voltage", ["pi_reboots"]),
]
_PH = []   # (symptom id, phrase tokens, phrase)
for sid, (q, how, says) in S.items():
    for p in says:
        tk = [w for w in toks(p)]
        if len(tk) == 1 and len(p.split()) > 1: continue          # "after a while" must not shrink to just "after"
        if tk: _PH.append((sid, tk, p))
VOCAB = sorted({w for _, tk, _ in _PH for w in tk}); _VSET = set(VOCAB)

def _fix_typos(T):
    """Map unknown words to the closest known word ('clicsk' -> 'click', 'rnage' -> 'range')."""
    import difflib
    out = []
    for w in T:
        if len(w) >= 4 and w not in _VSET:
            c = difflib.get_close_matches(w, VOCAB, n=1, cutoff=0.8)
            ok = c and not c[0].startswith(w) and not w.startswith(c[0])   # 'crack' is a word, not a typo of 'crackl(ing)'
            out.append(c[0] if ok else w)
        else: out.append(w)
    return out

_DF = {}
for _sid, _tk, _p in _PH:
    for _w in set(_tk): _DF[_w] = _DF.get(_w, 0) + 1
IDF = {w: math.log(1 + len(_PH) / n) for w, n in _DF.items()}

TOPIDF = os.environ.get("F_TOPIDF", "0") == "1"   # tested on the dev set: no gain, off

def _negated(text, start):
    left = text[max(0, start - 30):start]
    return bool(NEG.search(left.split(".")[-1].split(",")[-1]))

def link(text, min_cov=float(os.environ.get('F_COV', 0.62))):
    """Returns {symptom id: confidence (0..1, negative = described as NOT happening)}."""
    low = " " + text.lower().replace("\n", " ") + " "; out = {}
    for rx, sids in KLIPPER:
        for m in re.finditer(rx, low):
            for s in sids: out[s] = max(out.get(s, 0), 1.0)
    # sentence pieces, so a negation in one clause does not cancel another
    for piece in re.split(r"[.;!?]|\bbut\b", low):
        if OK_AFTER.search(piece):          # "the temperature looks normal" -> temperature symptoms are absent
            for s in ("hot_not_heat", "hot_spikes", "pid_osc", "temp_off_room", "bed_not_heat"):
                if any(w in piece for w in ("temp", "heat", "reading")): out.setdefault(s, -0.8)
        if USE_PRINTS_FINE and PRINTS_FINE.search(piece):       # "prints look fine": quality symptoms absent (did not validate on held-out cases: off)
            for s in QUALITY: out.setdefault(s, -0.7)
        T = _fix_typos(toks(piece)); Ts = set(T)
        if not T: continue
        neg_at = {i for i, w in enumerate(T) if NEG.fullmatch(w) or w in ("no", "not", "never", "without", "nothing")}
        for sid, tk, phrase in _PH:
            need = set(tk); matched = need & Ts
            if len(need) == 1 and not matched: continue
            if len(need) >= 2 and (len(matched) < 2 or len(matched) / len(need) < float(os.environ.get("F_CNT", 0.6))): continue   # one or two shared words are not a match
            if TOPIDF and len(need) >= 2 and max(need, key=lambda w: IDF.get(w, 1)) not in matched: continue   # the phrase's most specific word must be there
            hit = sum(IDF.get(w, 1) for w in matched) / sum(IDF.get(w, 1) for w in need)   # rare words count more
            if hit < (0.85 if S[sid][1] == "context" else min_cov): continue     # context claims need a closer match
            conf = 0.55 + 0.45 * hit if len(need) > 1 else 0.6
            first = min(i for i, w in enumerate(T) if w in matched)
            if any(first - 3 <= j < first and T[j] not in need for j in neg_at): conf = -conf   # "without any change" (but "no plastic comes out" is the symptom itself)
            if abs(conf) > abs(out.get(sid, 0)): out[sid] = round(conf, 2)
    return out

# parts the technician names (a hint, not proof: "after I replaced the belts" makes belts more likely)
MENTION = {
 "xy_belts": r"\bbelts?\b", "xy_pulleys_idlers": r"\bpulleys?\b|\bidlers?\b|grub ?screw", "x_linear_rail": r"\bx (rail|carriage)\b",
 "y_linear_rails": r"\by rails?\b", "umbilical_wiring": r"umbilical|toolhead (board|mcu|cable|pcb)|cable chain|drag chain|\bcan ?bus\b|\bebb\b|nitehawk|picobilical",
 "hotend_fan": r"hotend fan|heatsink fan", "part_cooling_fan": r"part (cooling )?fans?|blowers?", "z_endstop": r"z endstop|z switch|endstop",
 "z_motor_leadscrew": r"lead ?screw|z motor|\bnut\b", "z_rails": r"z rails?", "bed_plate_carrier": r"build plate|\bpei\b|bed screws?|\bbed\b(?! ?(heater|temp|thermistor))",
 "bed_heater": r"bed heater|heat ?pad|silicone heater", "bed_thermistor": r"bed (thermistor|temperature (reading|reads|sensor))", "bed_thermal_fuse": r"thermal fuse",
 "hotend_thermistor": r"thermistor|pt1000", "hotend_heater": r"heater cartridge|cartridge", "nozzle": r"\bnozzle\b", "heatbreak_ptfe": r"heat ?break|ptfe",
 "extruder_gears_guidler": r"guidler|drive gears?|bmg", "extruder_motor": r"extruder motor|pancake", "controller_board": r"skr|pico board|mainboard|controller board",
 "host_computer": r"raspberry|\bpi\b|sd card|\bos\b", "power_supply": r"power supply|\bpsu\b", "mains_power_input": r"power cord|\bplug\b|outlet|socket|inlet",
 "dc_power_wiring": r"crimps?|24 ?v wires?|screw terminal", "filament_material": r"spool|filament (roll|brand|quality)|\bwet\b", "slicer_settings": r"slicer|orca|prusaslicer|superslicer|cura",
 "firmware_config_macros": r"printer\.cfg|\bconfig\b|macro|klipper update|rotation.?distance", "filament_runout_sensor": r"runout",
 "xy_motors_drivers": r"stepper drivers?|tmc|a/b motors?|\b(a|b) motor|run.?current", "toolhead": r"toolhead|stealthburner|carriage",
}
MENTION_BONUS = float(os.environ.get("F_MENTION", 3.0))
def mentions(text):
    low = text.lower(); return [p for p, rx in MENTION.items() if re.search(rx, low)]

# ---------------------------------------------------------------- Bayes over failure modes
def leak(sid): return LEAK.get(S[sid][1], LEAK_DEFAULT)

def p_sym(m, sid): return MODES[m]["s"].get(sid, leak(sid))

G_W = tuple(float(x) for x in os.environ.get("F_GW", "5,3,2").split(","))   # weight of the graph agent's (arm G) ranks 1-3; chosen on test_A

def boost_from_ranking(ranked):
    """Arm G (Qwen reading the description with cards + failure graph) proposes a top 3; it becomes a prior boost."""
    return {p: G_W[i] for i, p in enumerate(ranked[:3])}

def posterior(ev, excluded=(), named=(), boost=None):
    """ev: {symptom: +conf (seen) / -conf (not seen)}; named: parts the technician mentioned. Returns ({mode: p}, {part: p})."""
    logp = {}
    for mid, m in MODES.items():
        if m["part"] in excluded: continue
        lp = math.log(PRIOR[mid]) + (math.log(MENTION_BONUS) if m["part"] in named else 0.0) + math.log((boost or {}).get(m["part"], 1.0))
        for sid, c in ev.items():
            if sid not in S or c == 0: continue
            p = p_sym(mid, sid); a = abs(c)
            like = p if c > 0 else 1 - p
            lp += math.log(a * like + (1 - a) * 0.5 + 1e-9)        # soft evidence: confidence a mixes with 'no information'
        logp[mid] = lp
    mx = max(logp.values()); e = {k: math.exp(v - mx) for k, v in logp.items()}; z = sum(e.values())
    pm = {k: v / z for k, v in e.items()}; pp = {}
    for k, v in pm.items():
        part = MODES[k]["part"]
        pp[part] = max(pp.get(part, 0), v) if AGG == "max" else pp.get(part, 0) + v     # best explanation per part
    zp = sum(pp.values()) or 1.0; pp = {k: v / zp for k, v in pp.items()}
    return pm, dict(sorted(pp.items(), key=lambda x: -x[1]))

def _H(ps): return -sum(p * math.log2(p) for p in ps if p > 0)

def question_gain(sid, pm):
    """Expected information gain (bits) about the faulty PART from a yes/no answer to symptom sid."""
    py = sum(p * p_sym(m, sid) for m, p in pm.items())
    def part_dist(yes):
        d = {}
        for m, p in pm.items():
            w = p * (p_sym(m, sid) if yes else 1 - p_sym(m, sid)); d[MODES[m]["part"]] = d.get(MODES[m]["part"], 0) + w
        z = sum(d.values()) or 1; return [v / z for v in d.values()]
    base = {}
    for m, p in pm.items(): base[MODES[m]["part"]] = base.get(MODES[m]["part"], 0) + p
    return _H(base.values()) - (py * _H(part_dist(True)) + (1 - py) * _H(part_dist(False)))

FOCUS_MODES = int(os.environ.get("F_FOCUS", 6))      # only ask about symptoms of the most likely failure modes (stay on topic)
YES_CONF, NO_CONF = float(os.environ.get("F_YES", 0.9)), float(os.environ.get("F_NO", 0.7))   # people miss things more often than they imagine them

def next_question(ev, pm, asked, top_k_modes=10):
    ranked = sorted(pm.items(), key=lambda x: -x[1])
    top = dict(ranked[:top_k_modes]); z = sum(top.values()); top = {k: v / z for k, v in top.items()}
    focus = {sid for m, _ in ranked[:FOCUS_MODES] for sid, p in MODES[m]["s"].items() if p >= 0.3}
    best = []
    for sid, (q, how, _) in S.items():
        if sid in ev or sid in asked or sid not in focus: continue
        g = question_gain(sid, top)
        if g > 0.02: best.append((g / COST.get(how, 1.0), g, sid))
    best.sort(reverse=True)
    return best

# ---------------------------------------------------------------- a whole conversation
STOP_P, RATIO, MAX_Q, MIN_GAIN = float(os.environ.get("F_STOP_P", 0.75)), float(os.environ.get("F_RATIO", 3.0)), int(os.environ.get("F_MAX_Q", 8)), 0.04

class Session:
    def __init__(self, text="", boost=None):
        self.ev = {}; self.asked = []; self.excluded = []; self.notes = []; self.boost = boost or {}
        self.mem_boost = {}; self.similar = []        # from the case memory (confirmed past cases)
        if text: self.describe(text)
    def describe(self, text):
        self.notes.append(text)
        for s, c in link(text).items():
            if abs(c) > abs(self.ev.get(s, 0)): self.ev[s] = c
    def answer(self, sid, ans):          # ans: True / False / None (don't know)
        if sid not in self.asked: self.asked.append(sid)
        if ans is True: self.ev[sid] = YES_CONF
        elif ans is False: self.ev[sid] = -NO_CONF
    def exclude(self, part): self.excluded.append(part)
    def state(self):
        pm, pp = posterior(self.ev, self.excluded, mentions(" ".join(self.notes)), combine(self.boost, self.mem_boost)); return pm, pp
    def step(self):
        """('ask', symptom id) or ('diagnose', part)."""
        pm, pp = self.state(); ranked = list(pp.items()); best, second = ranked[0][1], ranked[1][1] if len(ranked) > 1 else 0
        cand = next_question(self.ev, pm, self.asked)
        clear = best >= STOP_P or (best >= 0.55 and best >= RATIO * second)
        if (clear and len(self.asked) >= 1) or not cand or cand[0][1] < MIN_GAIN or len(self.asked) >= MAX_Q:
            return "diagnose", ranked[0][0]
        return "ask", cand[0][2]
    def explain(self, part):
        pm, pp = self.state(); modes = sorted([(p, m) for m, p in pm.items() if MODES[m]["part"] == part], reverse=True)
        m = MODES[modes[0][1]]; seen = [s for s, c in self.ev.items() if c > 0 and s in m["s"]]
        return {"part": part, "p": round(pp.get(part, 0), 3), "mode": m["name"], "mode_id": m["id"], "because": [S[s][0] for s in seen], "matched": [S[s][2][0] for s in seen if S[s][2]], "check": m["check"], "source": m["src"]}

OTHER_PRINTER = re.compile(r"\b(ender|prusa|bambu|anycubic|artillery|creality|cr-?10|sovol|elegoo|flashforge|voron (2\.4|trident|switchwire)|trident|v2\.4)\b", re.I)

def check_input(text):
    """None if the text can be diagnosed, else a short reply asking for more (or warning about another machine)."""
    if OTHER_PRINTER.search(text):
        return "I know the design of the Voron 0.2 only. If this is about a Voron 0.2, please describe what it does."
    if not link(text) and not mentions(text):
        return ("I could not recognise a symptom yet. Please describe what you see, hear or read on the screen, e.g. "
                "'layers shift sideways', 'the extruder clicks', 'Klipper says ADC out of range', 'the bed does not heat'.")
    return None

def combine(*boosts):
    out = {}
    for b in boosts:
        for p, f in (b or {}).items(): out[p] = out.get(p, 1.0) * f
    return out

def rank_text(text, k=5, g_top3=None, case_boost=None):
    """One-shot: description -> top-k parts (optionally combined with arm G's top 3 and the case memory)."""
    _, pp = posterior(link(text), named=mentions(text), boost=combine(boost_from_ranking(g_top3) if g_top3 else None, case_boost)); return list(pp.items())[:k]

if __name__ == "__main__":
    import sys
    t = " ".join(sys.argv[1:]) or "The print starts fine but after some minutes the extrusion stops and the extruder clicks"
    print(link(t)); print(rank_text(t))
