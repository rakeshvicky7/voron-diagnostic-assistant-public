"""Test Set v2 analysis: primary-only scores, paired exact McNemar with Holm correction (58 cases, Qwen)."""
import json, csv, math, pathlib
E = pathlib.Path(__file__).resolve().parent; R = E.parents[1] / "evaluation"
gt = {r["case_id"]: r["gt_primary"] for r in csv.DictReader(open(R / "ground_truth.csv", encoding="utf-8"), delimiter=";")}
res = {}
for l in open(E / "results_raw.jsonl"):
    j = json.loads(l); res[(j["arm"], j["case"])] = j
arms = ["A", "B", "BP", "C", "C2", "D", "E"]; cases = sorted(gt)
def grp(c): return "constructed" if c[0] == "C" else ("real_v2" if int(c[1:]) >= 15 else "real_orig")
def prim(j): return gt[j["case"]] in j["pred"][:3]
rows = []
for a in arms:
    for g, f in [("all", lambda c: True), ("real (30)", lambda c: c[0] == "R"), ("real_v2 (16)", lambda c: grp(c) == "real_v2"), ("constructed (28)", lambda c: c[0] == "C")]:
        S = [res[(a, c)] for c in cases if f(c) and (a, c) in res]
        n = len(S); rows.append([a, g, n, round(sum(s["top1"] for s in S)/n, 3), round(sum(s["top3"] for s in S)/n, 3), round(sum(prim(s) for s in S)/n, 3)])
def mcnemar(b, c):
    n = b + c
    if n == 0: return 1.0
    k = min(b, c); return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n)
fam = [("C", "D"), ("C", "A"), ("C", "B"), ("C", "BP"), ("C2", "D"), ("C2", "C"), ("B", "A"), ("E", "C"), ("C2", "B")]
tests = []
for metric, fn in [("top3", lambda j: j["top3"]), ("primary_top3", prim)]:
    out = []
    for x, y in fam:
        b = sum(fn(res[(x, c)]) and not fn(res[(y, c)]) for c in cases); c_ = sum(fn(res[(y, c)]) and not fn(res[(x, c)]) for c in cases)
        out.append([metric, f"{x} vs {y}", b, c_, mcnemar(b, c_)])
    order = sorted(range(len(out)), key=lambda i: out[i][4]); m = len(out); prev = 0
    for r_, i in enumerate(order):
        adj = min(1.0, max(prev, (m - r_) * out[i][4])); prev = adj; out[i].append(adj)
    tests += out
with open(E / "summary_v2_primary.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["arm", "subset", "n", "top1", "top3", "top3_primary_only"]); w.writerows(rows)
with open(E / "paired_tests_v2.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["metric", "comparison", "b_first_only", "c_second_only", "p_exact", "p_holm"]); w.writerows([[*t[:4], round(t[4], 4), round(t[5], 4)] for t in tests])
for r in rows: print(r)
for t in tests: print(t[0], t[1], t[2], t[3], round(t[4], 4), round(t[5], 4))
