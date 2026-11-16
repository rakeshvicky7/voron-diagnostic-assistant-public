import os
"""Sequential diagnosis: keep a probability for every part, ask the ONE question that is expected to
reduce the uncertainty the most, stop as soon as one part is clearly the most likely.

This is the "minimum entropy" probing idea of model-based diagnosis (de Kleer & Williams, 1987, GDE):
choose the next measurement by expected information gain, weighted by how hard it is to get.

posterior(c)  ∝  exp(base score of c)  x  Π over answered choice questions  P(answer | c)
P(answer | c) : if part c is listed for some answers of the question (EVIDENCE), those answers get 0.8
                of the probability and the others share 0.2; if c is listed for none, all answers are
                equally likely (the question says nothing about c).
gain(q)       = H(now) - Σ_answers P(answer) · H(after that answer)          [bits]
value(q)      = gain(q) / cost(q)     cost: click 1 (+0.1 per option above 3), short text 1.5, reading a value 1.6, multimeter test 2
"""
import math
from .questions import Q, EVIDENCE, in_area

NEUTRAL = {"I can't check", "I can't tell", "I can't reach it", "Did not try", "Not sure", "I can't see it"}
P_LISTED = 0.8
_e = lambda k, d: float(os.environ.get(k, d))   # development-set tuning (step 4) can override these
STOP_P = _e("STOP_P", 0.7)          # stop when the best part has at least this probability ...
STOP_P_RATIO = (_e("STOP_RATIO_P", 0.55), _e("STOP_RATIO", 3.0))   # ... or at least 55 % and three times the next part ...
MIN_GAIN = _e("MIN_GAIN", 0.12)     # ... or when no question is expected to give more than this (bits)
MAX_TURNS = int(_e("MAX_TURNS", 6))  # hard limit of question turns
RIVAL_P = _e("RIVAL_P", 0.08)        # before naming the leader: if the runner-up still has this much, ask one question that separates the two
RIVAL_GAIN = _e("RIVAL_GAIN", 0.05)
DK_STOP = int(_e("DK_STOP", 3))
MIN_SUPPORT = int(_e("MIN_SUPPORT", 0))
ALPHA = _e("ALPHA", 1.0)
LOO = int(_e("LOO", 0))
Q2_P, Q2_VALUE = _e("Q2_P", 0.35), _e("Q2_VALUE", 0.7)   # when to ask two one-click questions in one round   # 1: if the leader rests on a single answer (leave it out and another part leads), ask one more question   # <1 tempers each answer, so one wrong answer cannot dominate (tested on the development set)   # independent answers that must favour the leader before it is named (robust to one wrong answer)     # after this many "I can't tell" answers, name the best part found so far

def opts(qid):
    return [o for o in Q[qid]["options"] if o not in NEUTRAL]

# answers that describe a healthy part; a part that is NOT listed for a symptom answer will most likely
# give one of these (if the hotend fan is fine, it is spinning)
NORMAL = {"Looks fine", "Yes, it spins", "Neither, both look normal", "No change", "Yes, always", "Steady at target", "Turns normally", "Smooth in both", "Homes correctly", "Good everywhere",
          "No", "Normal amount but bad quality", "Not a shift problem", "Yes, but no link I can see"}
P_ABNORMAL_IF_UNLISTED = 0.1
NOT_NORMAL = {("hot_fan", "No")}     # "No" is the healthy answer to "any noise?", but a fault answer to "does the hotend fan spin?"

WIDE = {}   # filled by engine: answer -> parts one step upstream (in the failure graph) of the listed parts
W_LISTED, W_WIDE, W_NORMAL = 8.0, 2.0, 4.0
# A part listed for some answers of a question can still give the healthy answer (most parts fail in several ways and
# one question only sees some of them). Tuned on the development set only (step 4): weight of a healthy answer then.
W_NORMAL_LISTED = float(os.environ.get("W_NORMAL_LISTED", "4.0"))

def weights(qid, c):
    """Relative chance of each answer if c is the faulty part (normalised in lik)."""
    q = Q[qid]; slot = q["slot"]; O = opts(qid); sens = q.get("sens", P_LISTED)
    wl = 1 + (W_LISTED - 1) * sens / P_LISTED          # weak tests (low sens) raise the expected answers less
    w = {o: 1.0 for o in O}; hit = False
    wl *= q.get("strength", 1.0)                         # decisive checks (a measured open fuse) count more
    for o in O:
        if c in EVIDENCE.get((slot, o), []): w[o] = wl; hit = True
        elif c in WIDE.get((slot, o), []): w[o] = max(w[o], 1 + (W_WIDE - 1) * sens / P_LISTED); hit = True
    for o in O:   # healthy answers: likely if the part is not linked to the question, still possible if it is
        if o in NORMAL and (qid, o) not in NOT_NORMAL and c not in EVIDENCE.get((slot, o), []): w[o] = max(w[o], W_NORMAL if not hit else W_NORMAL_LISTED)
    return w

LIK_EPS = _e("LIK_EPS", 0.0)   # people sometimes answer wrongly: no single answer may rule a part out completely

def lik(qid, ans, c):
    """P(answer | c is the faulty part), mixed with a small chance that the answer is a mistake."""
    w = weights(qid, c); p = w.get(ans, 0) / sum(w.values())
    return (1 - LIK_EPS) * p + LIK_EPS / len(w)

def cost(qid):
    q = Q[qid]
    if q["kind"] == "choice": return 1.0 + 0.1 * max(0, len(q["options"]) - 3)   # more options = more to read
    if q["kind"] == "text": return 1.5
    return 2.0 if q.get("how") else 1.6

def entropy(P): return -sum(p * math.log2(p) for p in P.values() if p > 0)

def normalise(logs):
    m = max(logs.values()); e = {c: math.exp(v - m) for c, v in logs.items()}; z = sum(e.values())
    return {c: v / z for c, v in e.items()}

def posterior(base, facts, parts):
    """base: {part: score} from text, graph, errors and calculations. facts: answered choice slots."""
    logs = {c: base.get(c, 0.0) for c in parts}
    for qid, q in Q.items():
        if q["kind"] != "choice": continue
        a = facts.get(q["slot"])
        if not a or a in NEUTRAL or a not in q["options"]: continue
        for c in parts: logs[c] += ALPHA * math.log(lik(qid, a, c) * len(opts(qid)))   # ratio to an uninformative answer (tempered)
    return normalise(logs)

def gain(qid, P, top=None):
    """Expected information gain. With top given: gain about 'is it the leading part or not'."""
    if top is not None:
        # differential diagnosis: the leader against its closest rival (the one that is easiest to confuse with it)
        rest = {c: p for c, p in P.items() if c != top}; zr = sum(rest.values()) or 1.0
        def L(a, k): return lik(qid, a, top) if k == "__top" else sum(p * lik(qid, a, c) for c, p in rest.items()) / zr
        def B(abn, k):
            H = set(Q[qid]["helps"]); f = lambda c: ((0.8 if abn else 0.2) if c in H else (0.15 if abn else 0.85))
            return f(top) if k == "__top" else sum(p * f(c) for c, p in rest.items()) / zr
        P2 = {"__top": P[top], "__rest": 1 - P[top]}; H0 = entropy(P2); exp_h = 0.0
        outs = opts(qid) if Q[qid]["kind"] == "choice" else [True, False]
        for a in outs:
            j = {k: p * (L(a, k) if Q[qid]["kind"] == "choice" else B(a, k)) for k, p in P2.items()}; pa = sum(j.values())
            if pa > 0: exp_h += pa * entropy({k: v / pa for k, v in j.items()})
        return H0 - exp_h
    q = Q[qid]; H0 = entropy(P)
    if q["kind"] == "choice":
        exp_h = 0.0
        for a in opts(qid):
            joint = {c: p * lik(qid, a, c) for c, p in P.items()}; pa = sum(joint.values())
            if pa > 0: exp_h += pa * entropy({c: v / pa for c, v in joint.items()})
        return H0 - exp_h
    # measurement / text: two outcomes, "abnormal" (points to the parts it tests) or "normal"
    H = set(q["helps"]); exp_h = 0.0
    for abn in (True, False):
        joint = {c: p * ((0.8 if abn else 0.2) if c in H else (0.15 if abn else 0.85)) for c, p in P.items()}; pa = sum(joint.values())
        if pa > 0: exp_h += pa * entropy({c: v / pa for c, v in joint.items()})
    return H0 - exp_h

def answered(qid, case):
    q = Q[qid]
    if "slot" in q:
        v = case["facts"].get(q["slot"])
        if q["slot"] == "what_happens": return bool(v) and len(v) >= 40
        return bool(v)
    return all(f["key"] in case["measurements"] for f in q["fields"] if not f.get("text"))

def involves(qid):
    q = Q[qid]
    if q["kind"] == "choice": return {c for o in q["options"] for c in EVIDENCE.get((q["slot"], o), [])}
    return set(q["helps"])

def rank_questions(case, P, top=None):
    out = []
    lead2 = set(sorted(P, key=P.get, reverse=True)[:2])
    for qid in Q:
        if qid in case["asked_ids"] or answered(qid, case) or qid in ("what", "onset"): continue
        if not in_area(qid, case): continue            # stay inside the area of the problem (e.g. no extruder questions for a power cut)
        req = Q[qid].get("requires")   # follow-up questions only make sense after a certain answer (diagnosis tree)
        if req and not all(case["facts"].get(k) in v for k, v in req.items()): continue
        # when confirming, only ask about the leader or its closest rival (keeps questions on topic)
        if top is not None and not (involves(qid) & lead2): continue
        g = gain(qid, P, top)
        if g > 0.01: out.append({"id": qid, "gain": round(g, 3), "value": round(g / cost(qid), 3)})
    out.sort(key=lambda x: -x["value"])
    return out

def support(case, P, leader):
    """How many answered choice questions favour the leader clearly over the other suspects (likelihood ratio > 1.5)."""
    n = 0; rest = {c: p for c, p in P.items() if c != leader}; z = sum(rest.values()) or 1.0
    for qid, q in Q.items():
        if q["kind"] != "choice": continue
        a = case["facts"].get(q["slot"])
        if not a or a in NEUTRAL or a not in q["options"]: continue
        other = sum(p * lik(qid, a, c) for c, p in rest.items()) / z
        if other > 0 and lik(qid, a, leader) / other > 1.5: n += 1
    return n

def fragile(case, P, leader):
    """True if leaving out any single answer would put another part first (the conclusion rests on one answer)."""
    base = case.get("_base")
    if base is None: return False
    for qid, q in Q.items():
        if q["kind"] != "choice" or q["slot"] not in case["facts"] or case["facts"][q["slot"]] in NEUTRAL: continue
        f2 = {k: v for k, v in case["facts"].items() if k != q["slot"]}
        P2 = posterior(base, f2, list(P))
        if max(P2, key=P2.get) != leader: return True
    return False

def next_step(case, P, has_evidence):
    """Returns ("ask", [question ids]) or ("diagnose", reason)."""
    ps = sorted(P.values(), reverse=True); best_p, second = ps[0], ps[1]
    leader = max(P, key=P.get)
    # when one part already leads, ask what best confirms or refutes THAT part; otherwise what best splits all parts
    ranked = rank_questions(case, P, leader if best_p >= 0.5 else None)
    if not ranked and best_p >= 0.5: ranked = rank_questions(case, P)
    turns = case["rounds"]
    # a description alone is never enough: confirm with at least one answer or measurement before naming the cause
    confirmed = turns > 0 or bool(case["measurements"]) or bool(case["facts"].get("error_message"))
    clear = best_p >= STOP_P or (best_p >= STOP_P_RATIO[0] and best_p >= STOP_P_RATIO[1] * second)
    if has_evidence and confirmed and clear and LOO and turns < MAX_TURNS and fragile(case, P, leader):
        more = [r for r in rank_questions(case, P, leader) if r["gain"] >= RIVAL_GAIN]
        if more: return "ask", [more[0]["id"]]
    if has_evidence and confirmed and clear and MIN_SUPPORT and turns < MAX_TURNS and support(case, P, leader) < MIN_SUPPORT:
        more = [r for r in rank_questions(case, P, leader) if r["gain"] >= RIVAL_GAIN]
        if more: return "ask", [more[0]["id"]]             # one more independent check before trusting a single answer
    if has_evidence and confirmed and clear and second >= RIVAL_P and turns < MAX_TURNS:
        rival = sorted(P, key=P.get, reverse=True)[1]; pair = {leader, rival}
        sep = [r for r in rank_questions(case, {c: (P[c] if c in pair else 0.0) for c in P}) if involves(r["id"]) & pair and r["gain"] >= RIVAL_GAIN]
        if sep: return "ask", [sep[0]["id"]]               # tell the two closest suspects apart before concluding
    if has_evidence and confirmed and clear:
        # one more click is worth it if a single quick question can still confirm or refute the leader well
        quick = [r for r in rank_questions(case, P, leader) if Q[r["id"]]["kind"] == "choice" and r["gain"] >= 0.15]
        if best_p < 0.85 and turns < 3 and quick: return "ask", [quick[0]["id"]]
        return "diagnose", f"one part is clearly most likely ({best_p:.0%})"
    if len(case["dont_know"]) >= DK_STOP and has_evidence and best_p >= 0.4:
        return "diagnose", "best answer with the information you could give"
    if turns >= MAX_TURNS: return "diagnose", "question limit reached"
    min_gain = MIN_GAIN / 3 if best_p >= 0.5 else MIN_GAIN    # two-class gains are smaller by nature
    if not confirmed and ranked: return "ask", [ranked[0]["id"]]    # always confirm once before naming a cause
    if not ranked or ranked[0]["gain"] < min_gain:
        return ("diagnose", "no remaining question would change the answer much") if has_evidence else ("ask", ["what"])
    ask = [ranked[0]["id"]]
    # a second quick question only if it is almost as useful and both are one-click answers
    if len(ranked) > 1 and Q[ranked[0]["id"]]["kind"] == "choice" and Q[ranked[1]["id"]]["kind"] == "choice" \
            and ranked[1]["value"] >= Q2_VALUE * ranked[0]["value"] and best_p < Q2_P:
        ask.append(ranked[1]["id"])
    return "ask", ask
