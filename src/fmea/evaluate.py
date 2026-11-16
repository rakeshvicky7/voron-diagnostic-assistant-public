"""One-shot accuracy of the FMEA engine from the description alone (no questions).
Sets: practice (15 dev), test-A (R01-R14 + C01-C14, used for development), test-B (R15-R30 + C15-C28, held out)."""
import sys, json, csv, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from fmea.engine import rank_text, link
from run_eval import cases
A = pathlib.Path(__file__).resolve().parents[2]
def load():
    P = json.loads((A / "data" / "practice_cases.json").read_text(encoding="utf-8"))
    sets = {"practice": [(p["id"], p["opener"], set(p.get("ok", [p["part"]])), p["part"]) for p in P]}
    C = cases()
    def num(cid): return int(cid[1:])
    sets["test_A"] = [(c["id"], c["symptom"], c["ok"], c["primary"]) for c in C if num(c["id"]) <= 14]
    sets["test_B"] = [(c["id"], c["symptom"], c["ok"], c["primary"]) for c in C if num(c["id"]) > 14]
    h = A / "data" / "heldout_cases.json"      # new held-out real cases (collected after the graph was built; never used for tuning)
    if h.exists():
        H = json.loads(h.read_text(encoding="utf-8")); sets["test_C"] = [(p["id"], p["opener"], set(p.get("ok", [p["part"]])), p["part"]) for p in H]
    h2 = A / "data" / "heldout_cases_batch2.json"   # second batch of real forum cases (locked 14 Nov, checksum in heldout_cases_batch2.lock)
    if h2.exists():
        H = json.loads(h2.read_text(encoding="utf-8")); sets["test_D"] = [(p["id"], p["opener"], set(p.get("ok", [p["part"]])), p["part"]) for p in H]
    h3 = A / "data" / "heldout_cases_batch3.json"   # third batch (locked 15 Nov)
    if h3.exists():
        H = json.loads(h3.read_text(encoding="utf-8")); sets["test_E"] = [(p["id"], p["opener"], set(p.get("ok", [p["part"]])), p["part"]) for p in H]
    h4 = A / "data" / "heldout_cases_batch4.json"   # fourth batch (locked 15 Nov)
    if h4.exists():
        H = json.loads(h4.read_text(encoding="utf-8")); sets["test_F"] = [(p["id"], p["opener"], set(p.get("ok", [p["part"]])), p["part"]) for p in H]
    h5 = A / "data" / "heldout_cases_batch5.json"   # fifth batch (locked 15 Nov)
    if h5.exists():
        H = json.loads(h5.read_text(encoding="utf-8")); sets["test_G"] = [(p["id"], p["opener"], set(p.get("ok", [p["part"]])), p["part"]) for p in H]
    return sets
def g_preds():
    G = {}; f = A / "eval" / "results_raw.jsonl"
    if f.exists():
        for l in open(f, encoding="utf-8"):
            r = json.loads(l)
            if r.get("arm") == "G" and r.get("model", "").startswith("qwen"): G[r["case"]] = r["pred"]
    return G

def run(show=(), quiet=False, use_g="--g" in sys.argv or "--live-g" in sys.argv):
    sets = load(); res = {}; G = g_preds() if use_g else {}
    for name, S in sets.items():
        if use_g and name == "practice" and "--live-g" not in sys.argv: continue      # arm G was not run on the practice cases
        t1 = t2 = t3 = 0
        for cid, text, ok, prim in S:
            g = G.get(cid)
            if g is None and "--live-g" in sys.argv:          # run arm G now (needs Ollama), e.g. for the new held-out cases
                from assistant_v2 import engine as E2
                E2.USE_AGENT_PRIOR = True; g = E2.agent_top3(text)
            r = [p for p, _ in rank_text(text, 5, g)]
            t1 += r[0] in ok; t2 += any(x in ok for x in r[:2]); t3 += any(x in ok for x in r[:3])
            if name in show: print(f"  {cid:4s} {'TOP1' if r[0] in ok else 'top3' if any(x in ok for x in r[:3]) else 'miss':4s} truth={prim:24s} got={r[:3]}  | {text[:80]}  {link(text)}")
        res[name] = (len(S), round(100 * t1 / len(S)), round(100 * t3 / len(S)))
        if not quiet: print(f"{name:9s} n={len(S):2d}  top1={100*t1/len(S):.0f}%  within 1 check (top2)={100*t2/len(S):.0f}%  top3={100*t3/len(S):.0f}%")
    return res
if __name__ == "__main__": run(show=tuple(a for a in sys.argv[1:] if not a.startswith("--")))
