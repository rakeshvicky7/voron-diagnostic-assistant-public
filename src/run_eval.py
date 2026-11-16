"""Run all test cases on the chosen arms and score them.
Usage:  python src/run_eval.py --arms A B C D E   (graph RAG: --arms G)      (resumes if interrupted)
Output: eval/results_raw.jsonl, eval/summary.csv
"""
import json, csv, math, time, argparse, pathlib
from openpyxl import load_workbook
from agent import diagnose
from tools import Toolbox
from config import LLM_MODEL, STUB
A = pathlib.Path(__file__).resolve().parents[1]; R = A / "evaluation" if (A / "evaluation" / "ground_truth.csv").exists() else A.parent / "evaluation"; OUT = A / "eval"

def cases():
    gt = {r["case_id"]: r for r in csv.DictReader(open(R / "ground_truth.csv", encoding="utf-8"), delimiter=";")}
    ts = R / "Test_Set_v2.xlsx" if (R / "Test_Set_v2.xlsx").exists() else R / "Test_Set_v1.xlsx"
    ws = load_workbook(ts, read_only=True)["Test_Cases"]; rows = list(ws.iter_rows(values_only=True))
    h = rows[0]; out = []
    for r in rows[1:]:
        d = dict(zip(h, r)); g = gt[d["Case ID"]]
        out.append({"id": d["Case ID"], "type": d["Type"], "symptom": d["Symptom (technician wording, paraphrased)"],
                    "unseen": d["Cause covered by generic guide (arm D)?"] == "No",
                    "primary": g["gt_primary"], "ok": {g["gt_primary"], *[x for x in g["gt_acceptable"].split("|") if x]}})
    return out

def wilson(k, n, z=1.96):
    if n == 0: return (0, 0, 0)
    p = k / n; d = 1 + z*z/n; c = (p + z*z/(2*n)) / d; w = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return (round(p, 3), round(max(0, c - w), 3), round(min(1, c + w), 3))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--arms", nargs="+", default=list("ABCDE")); a = ap.parse_args()
    # The main model writes to results_raw.jsonl; any other model gets its own files, so results never mix.
    import re
    tag = "" if LLM_MODEL == "qwen2.5:7b-instruct" else "_" + re.sub(r"[^a-z0-9]+", "-", LLM_MODEL.lower()).strip("-")
    OUT.mkdir(exist_ok=True); raw = OUT / ("results_raw_stub.jsonl" if STUB else f"results_raw{tag}.jsonl")
    done = {(j["arm"], j["case"]) for j in map(json.loads, open(raw))} if raw.exists() else set()
    C = cases()
    for arm in a.arms:
        tb = Toolbox(arm)
        for c in C:
            if (arm, c["id"]) in done: continue
            t = time.time(); r = None
            for attempt in (1, 2):          # a stuck model call is retried once; if it fails twice the case is skipped and rerun next time
                try: r = diagnose(c["symptom"], arm, tb); break
                except Exception as e: print(f"{arm} {c['id']} attempt {attempt} failed: {type(e).__name__}: {e}"); time.sleep(30)
            if r is None: continue
            ids = [x["component_id"] for x in r["candidates"]]
            rec = {"arm": arm, "case": c["id"], "model": LLM_MODEL, "pred": ids, "top1": bool(ids) and ids[0] == c["primary"],
                   "top3": any(i in c["ok"] for i in ids[:3]), "unseen": c["unseen"], "type": c["type"], "secs": round(time.time() - t, 1),
                   "answer": r["candidates"], "raw": r["raw"][:3000], "trace": r["trace"]}
            if r.get("graph"): rec["graph"] = {"seeds": r["graph"]["seeds"], "upstream": [[u["id"], u["score"], u["explains"]] for u in r["graph"]["upstream"]]}
            open(raw, "a").write(json.dumps(rec) + "\n"); print(arm, c["id"], ids, "top1" if rec["top1"] else ("top3" if rec["top3"] else "miss"))
    res = [json.loads(l) for l in open(raw)]
    rows = []
    for arm in sorted({r["arm"] for r in res}):
        for subset, f in [("all", lambda r: True), ("unseen (not in guide)", lambda r: r["unseen"]), ("seen/partly in guide", lambda r: not r["unseen"]), ("real community cases", lambda r: r["type"].startswith("Real")), ("real, original 14", lambda r: r["type"] == "Real (community)"), ("real, added v2", lambda r: "added v2" in r["type"]), ("constructed", lambda r: r["type"] == "Constructed")]:
            S = [r for r in res if r["arm"] == arm and f(r)]
            t1 = wilson(sum(r["top1"] for r in S), len(S)); t3 = wilson(sum(r["top3"] for r in S), len(S))
            rows.append([arm, subset, len(S), *t1, *t3])
    with open(OUT / ("summary_stub.csv" if STUB else f"summary{tag}.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["arm", "subset", "n", "top1", "top1_lo95", "top1_hi95", "top3", "top3_lo95", "top3_hi95"]); w.writerows(rows)
    for r in rows: print(r)
