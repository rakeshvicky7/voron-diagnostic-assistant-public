"""Extra statistics for Test Set v2 (58 cases, Qwen): CIs, subsets, behaviour."""
import json, csv, math, collections, pathlib
E = pathlib.Path(__file__).resolve().parent; R = E.parents[1] / "evaluation"
gt = {r["case_id"]: r["gt_primary"] for r in csv.DictReader(open(R/"ground_truth.csv", encoding="utf-8"), delimiter=";")}
res = {}
for l in open(E/"results_raw.jsonl"):
    j = json.loads(l); res[(j["arm"], j["case"])] = j
arms = ["A","B","BP","C","C2","D","E"]; cases = sorted(gt)
def wil(k,n,z=1.96):
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; w=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d; return f"{round(100*p)}% ({round(100*max(0,c-w))}–{round(100*min(1,c+w))})"
prim=lambda j: gt[j["case"]] in j["pred"][:3]
def mc(b,c):
    n=b+c; k=min(b,c); return 1.0 if n==0 else min(1,2*sum(math.comb(n,i) for i in range(k+1))/2**n)
print("== main table")
for a in arms:
    S=[res[(a,c)] for c in cases]; n=len(S)
    print(a, wil(sum(s["top1"] for s in S),n), wil(sum(s["top3"] for s in S),n), wil(sum(prim(s) for s in S),n))
subs={"unseen":lambda c: res[("A",c)]["unseen"],"covered":lambda c: not res[("A",c)]["unseen"],"real30":lambda c:c[0]=="R","real_orig":lambda c:c[0]=="R" and int(c[1:])<15,"real_v2":lambda c:c[0]=="R" and int(c[1:])>=15,"constructed":lambda c:c[0]=="C"}
print("== subsets top3 / primary")
for s,f in subs.items():
    cs=[c for c in cases if f(c)]
    print(s,len(cs)," ".join(f"{a}:{round(100*sum(res[(a,c)]['top3'] for c in cs)/len(cs))}/{round(100*sum(prim(res[(a,c)]) for c in cs)/len(cs))}" for a in arms))
print("== subset tests (top3, raw exact McNemar)")
for s in ["unseen","covered","real30","real_v2","constructed"]:
    cs=[c for c in cases if subs[s](c)]
    for x,y in [("C","D"),("C","A"),("C","B"),("C2","D")]:
        b=sum(res[(x,c)]["top3"] and not res[(y,c)]["top3"] for c in cs); cc=sum(res[(y,c)]["top3"] and not res[(x,c)]["top3"] for c in cs)
        print(f"  {s} {x} vs {y}: {b}/{cc} p={mc(b,cc):.3f}")
print("== behaviour")
for a in arms:
    S=[res[(a,c)] for c in cases]
    extra=sum(max(0,len(s["trace"])-(1 if a!="A" else 0)) for s in S)
    tools=collections.Counter(t["tool"] for s in S for t in s["trace"])
    empty=sum(1 for s in S if not s["pred"])
    print(a,"extra calls",extra,dict(tools),"no valid answer",empty,"mean secs",round(sum(s["secs"] for s in S)/len(S)))
