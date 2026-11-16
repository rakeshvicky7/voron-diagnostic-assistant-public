"""Development score (practice + test_A only). Never prints the held-out sets."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1])); sys.argv = sys.argv[:1]
from fmea.evaluate import load, g_preds
from fmea.engine import rank_text
from fmea.cases import Memory, load as load_cases
import os
S = load(); G = g_preds(); MEM = Memory(load_cases(["dev"])) if os.environ.get("F_CASES", "1") == "1" else None
def sc(name, use_g):
    n = len(S[name]); t = [0, 0, 0]
    for cid, text, ok, prim in S[name]:
        r = [p for p, _ in rank_text(text, 5, G.get(cid) if use_g else None, MEM.boost(text, skip_id=cid) if MEM else None)]
        for i in range(3): t[i] += any(x in ok for x in r[:i + 1])
    return "/".join(f"{100*x//n}" for x in t), t[0]
a = sc("practice", False); b = sc("test_A", False); c = sc("test_A", True)
print(f"practice {a[0]} | A {b[0]} | A+G {c[0]} | total top1 {a[1]+b[1]+c[1]}")
if MEM:   # repeat faults: the same description again after the case was confirmed and remembered
    n = w0 = w1 = 0
    for name in ("practice", "test_A"):
        for cid, text, ok, prim in S[name]:
            n += 1; w0 += rank_text(text, 1)[0][0] in ok; w1 += rank_text(text, 1, None, MEM.boost(text))[0][0] in ok
    print(f"repeat faults (case remembered): right part first without memory {w0}/{n}, with memory {w1}/{n}")
