"""Three-model comparison on all 58 cases (Test Set v2)."""
import json, csv, math, collections, pathlib
E = pathlib.Path(__file__).resolve().parent; R = E.parents[1] / "evaluation"
gt = {r["case_id"]: r["gt_primary"] for r in csv.DictReader(open(R/"ground_truth.csv", encoding="utf-8"), delimiter=";")}
files = {"Qwen": "results_raw.jsonl", "Llama": "results_raw_llama3-1-8b.jsonl", "Mistral": "results_raw_mistral-7b.jsonl"}
arms = ["A","B","C","C2","D"]
def mc(b,c):
    n=b+c;k=min(b,c); return 1.0 if n==0 else min(1,2*sum(math.comb(n,i) for i in range(k+1))/2**n)
pr=lambda j: gt[j["case"]] in j["pred"][:3]
out=[]
for m,f in files.items():
    res={}
    for l in open(E/f):
        j=json.loads(l); res[(j["arm"],j["case"])]=j
    print("==",m)
    for a in arms:
        S=[res[(a,c)] for c in gt if (a,c) in res]; n=len(S)
        row=[m,a,n,round(100*sum(s["top1"] for s in S)/n),round(100*sum(pr(s) for s in S)/n),round(100*sum(s["top3"] for s in S)/n),sum(1 for s in S if not s["pred"])]
        out.append(row); print(row)
        real=[res[(a,c)] for c in gt if c[0]=="R" and (a,c) in res]
        print("   real n",len(real),"strict",round(100*sum(pr(s) for s in real)/len(real)),"lenient",round(100*sum(s["top3"] for s in real)/len(real)))
    for x,y in [("C","D"),("C2","D"),("C","A"),("C","B"),("C2","B"),("B","A")]:
        cs=[c for c in gt if (x,c) in res and (y,c) in res]
        for nm,fn in [("top3",lambda j:j["top3"]),("strict",pr)]:
            b=sum(fn(res[(x,c)]) and not fn(res[(y,c)]) for c in cs); cc=sum(fn(res[(y,c)]) and not fn(res[(x,c)]) for c in cs)
            print(f"   {x} vs {y} {nm}: {b}/{cc} p={mc(b,cc):.4f} (n={len(cs)})")
with open(E/"summary_three_models_v2.csv","w",newline="") as fh:
    w=csv.writer(fh); w.writerow(["model","arm","n","top1","top3_primary","top3","no_valid_answer"]); w.writerows(out)
