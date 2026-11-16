"""Dialogue test on the virtual printer: the chat assistant questions a SIMULATED PRINTER instead of a simulated person.

For every part (31) and several random faults per part:
  1. The virtual printer gets the fault (random fault mode and severity).
  2. The assistant receives the technician's first sentence (virtual_printer.describe(); it never names the part).
  3. Every question the assistant asks is answered from the simulation (choices, measured values, short texts).
     With --dont-know 0.15 the technician answers "I can't tell" to 15 % of the questions.
  4. The run ends when the assistant names a cause, or after 8 questions.

Unlike eval_dialogue.py (a language model plays the technician and invents nothing measurable), the answers here come
from physics and the design values, so measurement questions get real numbers. It needs no model and runs in minutes.
It is a test of the questioning on simulated faults, NOT a replacement for the 58 real/constructed test cases.

Run from the agent folder:   py -3.12 src\\twin\\eval_twin.py --runs 5
Output: eval/twin_dialogue.csv (one row per run) and eval/twin_dialogue_summary.md
"""
import os, sys, csv, time, random, argparse, pathlib, collections
for _k, _v in {"STUB": "1", "AGENT_PRIOR": "0", "SELF_CHECK": "0", "LEAD": "rules", "KB_MODE": "off", "FT_MODEL": ""}.items():
    os.environ[_k] = _v                                          # rules only: no model, no network
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from twin.virtual_printer import VirtualPrinter, PARTS            # noqa: E402
from assistant_v2 import engine as E                              # noqa: E402
from assistant_v2.questions import Q                              # noqa: E402

MAX_Q = 8
EVAL28 = set(PARTS[:28])                                          # the 28 parts of the one-shot evaluation (arms A-G)

def dialogue(part, seed, dont_know):
    vp = VirtualPrinter(part, seed=seed, dont_know=dont_know); case = E.new_case(); t0 = time.time()
    r = E.turn(case, vp.describe())["reply"]; asked = 0; log = [vp.describe()]
    while r["type"] == "questions" and asked < MAX_Q:
        form = {"facts": {}, "measurements": {}, "dont_know": []}
        for q in r["questions"]:
            asked += 1; qid = q["id"]
            a = vp.answer(qid) if qid in Q else None
            if a is None: form["dont_know"].append(qid); log.append(f"{qid}=?"); continue
            form["facts"].update(a[0]); form["measurements"].update(a[1]); log.append(f"{qid}={list(a[0].values()) or a[1]}")
        r = E.turn(case, None, form)["reply"]
    hyps = [h["id"] for h in case.get("hyps", [])]
    named = r.get("diagnosis", {}).get("cause") if r["type"] == "diagnosis" else (hyps[0] if hyps else None)
    return {"part": part, "mode": vp.mode or "-", "severity": round(vp.s, 2), "seed": seed, "named": named,
            "top1": named == part, "top3": part in hyps[:3], "questions": asked, "ended": r["type"],
            "secs": round(time.time() - t0, 2), "dialogue": " | ".join(log)}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--runs", type=int, default=5); ap.add_argument("--dont-know", type=float, default=0.0)
    ap.add_argument("--parts", nargs="*", default=None); a = ap.parse_args()
    E._load(); rows = []
    for part in a.parts or PARTS:
        for i in range(a.runs):
            try: rows.append(dialogue(part, 500 + i, a.dont_know))
            except Exception as e: print(f"{part} run {i} failed: {type(e).__name__}: {e}"); continue
            x = rows[-1]; print(f"{part:24s} {x['mode'][:26]:26s} -> {str(x['named']):24s} {'TOP1' if x['top1'] else 'top3' if x['top3'] else 'miss'}  {x['questions']} q")
    out = E.A / "eval"; out.mkdir(exist_ok=True); tag = f"_dk{int(a.dont_know * 100)}" if a.dont_know else ""
    with open(out / f"twin_dialogue{tag}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    def summ(S): return (len(S), 100 * sum(r["top1"] for r in S) / len(S), 100 * sum(r["top3"] for r in S) / len(S), sum(r["questions"] for r in S) / len(S))
    L = [f"# Dialogue test on the virtual printer ({a.runs} faults per part, 'I can't tell' rate {a.dont_know:.0%})", "",
         "| Subset | Runs | Top-1 | Top-3 | Mean questions |", "|---|---|---|---|---|"]
    for name, S in [("all 31 parts", rows), ("28 evaluation parts", [r for r in rows if r["part"] in EVAL28]),
                    ("3 extra power/bed parts", [r for r in rows if r["part"] not in EVAL28])]:
        if S: n, t1, t3, q = summ(S); L.append(f"| {name} | {n} | {t1:.0f} % | {t3:.0f} % | {q:.1f} |")
    L += ["", "| Part | Top-1 | Top-3 | Mean questions | Most frequent wrong answer |", "|---|---|---|---|---|"]
    for part in a.parts or PARTS:
        S = [r for r in rows if r["part"] == part]
        if not S: continue
        n, t1, t3, q = summ(S); wrong = collections.Counter(r["named"] for r in S if not r["top1"]).most_common(1)
        L.append(f"| {part} | {t1:.0f} % | {t3:.0f} % | {q:.1f} | {wrong[0][0] if wrong else ''} |")
    (out / f"twin_dialogue_summary{tag}.md").write_text("\n".join(L), encoding="utf-8"); print("\n".join(L[:7]))
