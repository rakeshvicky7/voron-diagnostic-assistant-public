"""Conversation test of the FMEA-graph assistant, with a language model playing the technician.

For every case: the assistant reads the first sentence, asks yes/no symptom questions, names a part.
The technician (local Qwen via Ollama) knows the hidden true part and cause and answers yes / no / don't know,
only from what someone at the printer could observe. If the named part is wrong, the technician says
"this part is fine" once and the assistant continues (reported separately).

Run from the agent folder (Ollama running):   py -3.12 src\\fmea\\eval_dialogue.py --sets practice test_A test_B
Offline smoke test (graph-based technician, NOT a real test):   $env:STUB="1"; py -3.12 src\\fmea\\eval_dialogue.py --limit 3
Output: eval/fmea_dialogue_<set>.jsonl and a summary table.
"""
import os, sys, json, time, random, argparse, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from fmea.engine import Session, S, MODES
from fmea.evaluate import load
from run_eval import wilson
A = pathlib.Path(__file__).resolve().parents[2]
STUB = os.environ.get("STUB") == "1"

SIM_SYS = """You are a technician standing at a Voron 0.2 3D printer that has a fault. You know the hidden truth about the fault.
Answer the assistant's yes/no question about what you can OBSERVE at the printer (see, hear, feel, read on the screen, or a simple
test). Rules: never name the faulty part or cause; answer "yes" or "no" only when the hidden truth clearly implies it;
if the question needs a measurement you could not plausibly make, or the truth does not tell you, answer "dont_know".
Return JSON only: {"answer": "yes" | "no" | "dont_know"}"""

def llm_answer(case, sid):
    from assistant_v2.llm import ask_json
    q = S[sid][0]
    user = (f"HIDDEN TRUTH (do not reveal): faulty part = {case['part']}; cause = {case.get('cause', '')}.\n"
            f"What you reported first: \"{case['text']}\"\nQuestion: {q}")
    a = str((ask_json(SIM_SYS, user, max_tokens=20) or {}).get("answer", "")).lower()
    return True if a.startswith("y") else False if a.startswith("n") else None

def stub_answer(case, sid, rnd):
    """Offline proxy only (circular, NOT a measurement): a sloppy technician like the language model one -
    35 % 'don't know', misses a true symptom 25 % of the time, imagines a false one 5 % of the time."""
    modes = [m for m in MODES.values() if m["part"] == case["part"]]; m = max(modes, key=lambda x: x.get("prior", 1))
    if rnd.random() < 0.35: return None
    true = rnd.random() < m["s"].get(sid, 0.03)
    if true and rnd.random() < 0.25: return False
    if not true and rnd.random() < 0.05: return True
    return true

_G = None
def g_top3(case):
    """Arm G's top 3 for this description: cached from the arms evaluation when available, else run live (needs Ollama)."""
    global _G
    if _G is None:
        _G = {}
        f = A / "eval" / "results_raw.jsonl"
        if f.exists():
            for l in open(f, encoding="utf-8"):
                r = json.loads(l)
                if r.get("arm") == "G" and r.get("model", "").startswith("qwen"): _G[r["case"]] = r["pred"]
    if case["id"] in _G: return _G[case["id"]]
    if STUB: return []
    from assistant_v2 import engine as E2
    E2.USE_AGENT_PRIOR = True; return E2.agent_top3(case["text"])

def run_case(case, max_q=8, checks=1, use_g=False):
    from fmea.engine import boost_from_ranking
    rnd = random.Random(case["id"]); ses = Session(case["text"], boost_from_ranking(g_top3(case)) if use_g else None); log = []; t0 = time.time()
    def ask_loop():
        while True:
            kind, x = ses.step()
            if kind == "diagnose": return x
            a = stub_answer(case, x, rnd) if STUB else llm_answer(case, x)
            ses.answer(x, a); log.append((x, a))
            if len(ses.asked) >= max_q + 4: return ses.step()[1]
    named = ask_loop(); first = named; _, pp = ses.state(); top3 = list(pp)[:3]
    used = 0
    while named not in case["ok"] and used < checks:
        used += 1; ses.exclude(named); named = ask_loop()
    return {"id": case["id"], "truth": case["part"], "named": first, "top1": first in case["ok"], "top3": any(p in case["ok"] for p in top3),
            "within1check": named in case["ok"], "questions": len(log), "secs": round(time.time() - t0, 1),
            "dialogue": [(S[s][0], a) for s, a in log]}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--sets", nargs="*", default=["practice", "test_A", "test_B"]); ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--arm-g", action="store_true", help="start from arm G's top 3 (cards + failure graph read by Qwen)")
    a = ap.parse_args(); sets = load(); P = {p["id"]: p for p in json.loads((A / "data" / "practice_cases.json").read_text(encoding="utf-8"))}
    from openpyxl import load_workbook
    ws = load_workbook((A / "evaluation" if (A / "evaluation").exists() else A.parent / "evaluation") / "Test_Set_v2.xlsx", read_only=True)["Test_Cases"]
    cause = {r[0]: r[6] or "" for r in list(ws.iter_rows(values_only=True))[1:]}
    rows_all = []
    for name in a.sets:
        out = A / "eval" / f"fmea_dialogue_{name}{'_g' if a.arm_g else ''}{'_stub' if STUB else ''}.jsonl"; rows = []
        C = sets[name][: a.limit or None]
        for cid, text, ok, prim in C:
            case = {"id": cid, "text": text, "ok": ok, "part": prim, "cause": P[cid]["cause"] if cid in P else cause.get(cid, "")}
            r = run_case(case, use_g=a.arm_g); rows.append(r)
            print(f"{name} {cid}: named {r['named']} (truth {prim}) {'TOP1' if r['top1'] else 'top3' if r['top3'] else 'miss'}"
                  f"{' / right after one check' if not r['top1'] and r['within1check'] else ''}, {r['questions']} questions, {r['secs']} s", flush=True)
        out.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8"); rows_all += [(name, r) for r in rows]
    print("\n| Set | Cases | Top-1 (95% CI) | Top-3 | Right after one 'this part is fine' | Mean questions |\n|---|---|---|---|---|---|")
    for name in a.sets + ["all"]:
        R = [r for n, r in rows_all if n == name or name == "all"]
        if not R: continue
        t1 = wilson(sum(r["top1"] for r in R), len(R)); t3 = wilson(sum(r["top3"] for r in R), len(R)); w = wilson(sum(r["within1check"] for r in R), len(R))
        print(f"| {name} | {len(R)} | {t1[0]:.0%} ({t1[1]:.0%}-{t1[2]:.0%}) | {t3[0]:.0%} | {w[0]:.0%} | {sum(r['questions'] for r in R) / len(R):.1f} |")
