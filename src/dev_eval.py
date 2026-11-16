"""Development yardstick for the chat assistant: how often does it end on the right part, and WHY does it fail?

Development set (tune on this as much as needed; the 58 test cases are NOT used here)
  twin      31 parts x N simulated faults; the virtual printer answers every question from physics
  practice  real cases (not in the 58) in data/practice_cases.json; each case has the technician's first sentence and
            the answers the forum poster could give ("scripted technician"); anything not written = "I can't tell"

For each case
  dialogue  first sentence -> questions answered -> the assistant names one part (or 8 questions are used up)
  oracle    first sentence + ALL observations at once -> which part does the engine rank first?
Failure types (for wrong top-1)
  reading    the first sentence was read into a fact that contradicts what the technician later says
  knowledge  even with all observations the engine ranks another part first (cards/evidence cannot explain it)
  question   with all observations it would be right, but no question separates the truth from the part it named
  stop       it would be right with all observations and a separating question exists, but it stopped or chose badly

Run from the agent folder (no model needed):   py -3.12 src\\dev_eval.py --runs 10
Options: --dont-know 0.15 (technician can't answer 15 %), --wrong 0.1 (10 % wrong answers), --set twin|practice|all
Output: eval/dev_report.md and eval/dev_cases.csv
"""
import os, sys, csv, json, random, argparse, pathlib, collections
for _k, _v in {"STUB": "1", "AGENT_PRIOR": "0", "SELF_CHECK": "0", "LEAD": "rules", "KB_MODE": "off", "FT_MODEL": ""}.items():
    os.environ.setdefault(_k, _v)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from assistant_v2 import engine as E                    # noqa: E402
from assistant_v2 import reasoner as R                  # noqa: E402
from assistant_v2.questions import Q, EVIDENCE           # noqa: E402
from assistant_v2.understand import keyword_facts        # noqa: E402
from twin.virtual_printer import VirtualPrinter, PARTS   # noqa: E402

MAX_Q = 8
A = E.A

# ---------------------------------------------------------------- technicians
class TwinTech:
    """The virtual printer answers; optional 'I can't tell' and wrong answers."""
    def __init__(self, part, seed, dont_know=0.0, wrong=0.0):
        self.vp = VirtualPrinter(part, seed=seed); self.rnd = random.Random(seed * 7 + 1); self.dk, self.wr = dont_know, wrong
        self.truth = part; self.opener = self.vp.describe(); self.kind = "twin"; self.id = f"{part}#{seed}"; self.mode = self.vp.mode or "-"
    def answer(self, qid):
        if qid not in Q or self.rnd.random() < self.dk: return None
        if os.environ.get("NO_MEASURE") == "1" and Q[qid]["kind"] == "fields": return None   # like the 58-case protocol
        a = self.vp._answer(qid)
        if a and self.rnd.random() < self.wr and Q[qid]["kind"] == "choice" and qid not in os.environ.get("NO_WRONG", "").split(","):
            slot = Q[qid]["slot"]; others = [o for o in Q[qid]["options"] if o != a[0].get(slot)]
            if others: a = ({slot: self.rnd.choice(others)}, {})
        return a
    def all_observations(self): return self.vp.observations()

class ScriptTech:
    """A real practice case: answers written from the forum thread."""
    def __init__(self, case):
        self.c = case; self.truth = case["part"]; self.opener = case["opener"]; self.kind = "practice"; self.id = case["id"]; self.mode = case.get("cause", "")
        self.ok = set(case.get("ok", [case["part"]]))
    def answer(self, qid):
        if qid not in Q: return None
        q = Q[qid]; f, m = self.c.get("facts", {}), self.c.get("measurements", {})
        if os.environ.get("NO_MEASURE") == "1" and q["kind"] == "fields": return None
        if q["kind"] == "fields":
            vals = {fl["key"]: m[fl["key"]] for fl in q["fields"] if fl["key"] in m}
            return ({}, vals) if vals else None
        return ({q["slot"]: f[q["slot"]]}, {}) if q.get("slot") in f else None
    def all_observations(self): return dict(self.c.get("facts", {})), dict(self.c.get("measurements", {}))

# ---------------------------------------------------------------- one case
def dialogue(tech, ok=None, checks=0):
    """checks: how many times the technician may check a named part and report 'this part is fine' (the assistant's
    confirm loop); the dialogue then continues with the remaining suspects."""
    case = E.new_case(); r = E.turn(case, tech.opener)["reply"]; asked = []
    read = dict(case["facts"]); used = 0
    while True:
        r = _ask_loop(tech, case, r, asked)
        named = r.get("diagnosis", {}).get("cause") if r["type"] == "diagnosis" else None
        if named is None or ok is None or named in ok or used >= checks: break
        used += 1; r = E.turn(case, None, {"facts": {}, "measurements": {}, "dont_know": [], "exclude": [named]})["reply"]
    hyps = [h["id"] for h in case.get("hyps", [])]
    named = r.get("diagnosis", {}).get("cause") if r["type"] == "diagnosis" else (hyps[0] if hyps else None)
    return named, hyps, asked, r["type"], read, case

def _ask_loop(tech, case, r, asked):
    while r["type"] == "questions" and len(asked) < MAX_Q:
        form = {"facts": {}, "measurements": {}, "dont_know": []}
        for q in r["questions"]:
            asked.append(q["id"]); a = which_part(tech, q) if q["id"] == "which_part" else tech.answer(q["id"])
            if a is None: form["dont_know"].append(q["id"])
            else: form["facts"].update(a[0]); form["measurements"].update(a[1])
        r = E.turn(case, None, form)["reply"]
    return r

def which_part(tech, q):
    """The engine asks which part the technician meant by a vague word ('fan', 'heater'). The technician knows what they saw."""
    opts = q.get("options", []); low = tech.opener.lower(); name = E.NAME.get(tech.truth, tech.truth).lower()
    if any(w in low for w in ("whole printer", "everything", "all fans")):
        o = next((x for x in opts if x.lower().startswith("all")), None)
        if o: return ({q.get("slot", "which_part"): o}, {})
    words = {w for w in name.replace("(", " ").replace(")", " ").split() if len(w) > 3}
    best = max(opts, key=lambda o: len(words & set(o.lower().replace("(", " ").replace(")", " ").replace(",", " ").split())), default=None)
    if best and words & set(best.lower().replace("(", " ").replace(")", " ").replace(",", " ").split()): return ({q.get("slot", "which_part"): best}, {})
    o = next((x for x in opts if x.lower().startswith("something else")), None)
    return ({q.get("slot", "which_part"): o}, {}) if o else None

def oracle(tech):
    """First sentence plus every observation at once: the best the knowledge can do."""
    case = E.new_case(); E.turn(case, tech.opener)
    f, m = tech.all_observations()
    E.turn(case, None, {"facts": {k: v for k, v in f.items() if k != "what_happens"}, "measurements": m, "dont_know": []})
    return [h["id"] for h in case.get("hyps", [])]

def separating_question(truth, other):
    """Is there any question whose answers point differently at the two parts (in the evidence table or the 'helps' lists)?"""
    for qid, q in Q.items():
        if truth in q.get("helps", []) and other not in q.get("helps", []): return qid
        if q["kind"] == "choice":
            for o in q["options"]:
                ev = EVIDENCE.get((q["slot"], o), [])
                if (truth in ev) != (other in ev): return qid
    return None

def classify(tech, named, hyps, asked, read, ok):
    if named in ok: return "correct"
    f, _ = tech.all_observations()
    choice_slots = {q["slot"] for q in Q.values() if q["kind"] == "choice"}
    if any(k in f and f[k] != v for k, v in read.items() if k in choice_slots): return "reading"
    orc = oracle(tech)
    if not orc or orc[0] not in ok: return "knowledge"
    if named and not separating_question(tech.truth, named): return "question"
    return "stop"

# ---------------------------------------------------------------- run
def load_practice():
    p = A / "data" / "practice_cases.json"
    return [ScriptTech(c) for c in json.loads(p.read_text(encoding="utf-8"))] if p.exists() else []

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--runs", type=int, default=10); ap.add_argument("--set", default="all")
    ap.add_argument("--dont-know", type=float, default=0.0); ap.add_argument("--wrong", type=float, default=0.0); ap.add_argument("--tag", default="")
    a = ap.parse_args(); E._load()
    techs = []
    if a.set in ("all", "twin"):      # only faults a technician would notice and report (a silent fault is not a case)
        for p in PARTS:
            got, seed = 0, 100
            while got < a.runs and seed < 100 + 20 * a.runs:
                t = TwinTech(p, seed, a.dont_know, a.wrong); seed += 1
                if t.opener.startswith(("Everything looks normal", "Something seems slightly off")): continue
                techs.append(t); got += 1
    if a.set in ("all", "practice"): techs += load_practice()
    rows = []
    print(f"{len(techs)} cases; model mode: {'offline rules (STUB)' if os.environ.get('STUB') == '1' else 'real search + Ollama'}", flush=True)
    for n, t in enumerate(techs, 1):
        print(f"  case {n}/{len(techs)}: {t.id}", flush=True)
        ok0 = getattr(t, "ok", {t.truth})
        try:
            named, hyps, asked, ended, read, _ = dialogue(t)
            named1, _, asked1, _, _, _ = dialogue(t, ok0, checks=1)     # with one "I checked it, this part is fine"
        except Exception as e: print("failed", t.id, type(e).__name__, e); continue
        ok = getattr(t, "ok", {t.truth})
        kind = classify(t, named, hyps, asked, read, ok)
        rows.append({"set": t.kind, "id": t.id, "truth": t.truth, "mode": t.mode, "named": named, "top1": named in ok, "within1check": named1 in ok, "q_with_check": len(asked1),
                     "top3": any(h in ok for h in hyps[:3]), "questions": len(asked), "ended": ended, "failure": kind,
                     "asked": " ".join(asked), "opener": t.opener})
    out = A / "eval"; out.mkdir(exist_ok=True); tag = a.tag or (f"_dk{int(a.dont_know*100)}" if a.dont_know else "") + (f"_w{int(a.wrong*100)}" if a.wrong else "")
    with open(out / f"dev_cases{tag}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    pc = lambda S, k: 100 * sum(r[k] for r in S) / len(S) if S else 0
    L = [f"# Development yardstick ({a.runs} twin faults per part; 'can't tell' {a.dont_know:.0%}; wrong answers {a.wrong:.0%})", "",
         "| Set | Cases | Top-1 | Top-3 | Mean questions | Right after at most one 'this part is fine' | Questions then |", "|---|---|---|---|---|---|---|"]
    for name, S in [("twin (31 parts)", [r for r in rows if r["set"] == "twin"]), ("practice (real)", [r for r in rows if r["set"] == "practice"]), ("all", rows)]:
        if S: L.append(f"| {name} | {len(S)} | {pc(S, 'top1'):.0f} % | {pc(S, 'top3'):.0f} % | {sum(r['questions'] for r in S) / len(S):.1f} | "
                       f"{pc(S, 'within1check'):.0f} % | {sum(r['q_with_check'] for r in S) / len(S):.1f} |")
    wrong = [r for r in rows if not r["top1"]]; fc = collections.Counter(r["failure"] for r in wrong)
    L += ["", "## Why the wrong ones failed", "", "| Failure type | Cases | Share of failures |", "|---|---|---|"]
    for k in ("knowledge", "question", "stop", "reading"):
        L.append(f"| {k} | {fc.get(k, 0)} | {100 * fc.get(k, 0) / max(1, len(wrong)):.0f} % |")
    L += ["", "## Per part (twin)", "", "| Part | Top-1 | Top-3 | Questions | Main failure | Most often named instead |", "|---|---|---|---|---|---|"]
    for p in PARTS:
        S = [r for r in rows if r["set"] == "twin" and r["truth"] == p]
        if not S: continue
        fw = collections.Counter(r["failure"] for r in S if not r["top1"]).most_common(1); nw = collections.Counter(r["named"] for r in S if not r["top1"]).most_common(1)
        L.append(f"| {p} | {pc(S, 'top1'):.0f} % | {pc(S, 'top3'):.0f} % | {sum(r['questions'] for r in S) / len(S):.1f} | {fw[0][0] if fw else ''} | {nw[0][0] if nw else ''} |")
    P_ = [r for r in rows if r["set"] == "practice"]
    if P_:
        L += ["", "## Practice cases", "", "| Case | Truth | Named | Result | Failure |", "|---|---|---|---|---|"]
        L += [f"| {r['id']} | {r['truth']} | {r['named']} | {'TOP1' if r['top1'] else 'top3' if r['top3'] else 'miss'} | {r['failure']} |" for r in P_]
    (out / f"dev_report{tag}.md").write_text("\n".join(L), encoding="utf-8"); print("\n".join(L))

if __name__ == "__main__":
    main()
