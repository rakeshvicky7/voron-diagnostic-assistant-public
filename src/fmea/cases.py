"""Case memory: confirmed past cases (description -> faulty part). Similar new descriptions get a boost for that part.

Sources: data/case_base.json (the collected real and constructed cases) and data/confirmed_cases.jsonl (every case a
technician confirms with 'This was it' in the assistant). So the assistant learns from use.
For honest testing, evaluation scripts pass only the development cases and leave the tested case out.
"""
import json, math, os, pathlib, time
try:
    from .engine import toks, _fix_typos
except ImportError:
    from engine import toks, _fix_typos
A = pathlib.Path(__file__).resolve().parents[2]
BASE, LEARNED = A / "data" / "case_base.json", A / "data" / "confirmed_cases.jsonl"
# boost = exp(K * (similarity - MIN_SIM)): a near-identical past case counts a lot, a loosely similar one hardly at all
K = float(os.environ.get("F_CASE_K", 12.0)); MIN_SIM = float(os.environ.get("F_CASE_SIM", 0.5))

def load(splits=None):
    cases = []
    if BASE.exists():
        cases = [c for c in json.loads(BASE.read_text(encoding="utf-8")) if splits is None or c.get("split") in splits]
    if LEARNED.exists() and splits is None:
        for l in LEARNED.read_text(encoding="utf-8").splitlines():
            try: cases.append(json.loads(l))
            except Exception: pass
    return cases

def remember(text, part, mode=""):
    """Called when a technician confirms the faulty part."""
    rec = {"id": "U" + time.strftime("%Y%m%d%H%M%S"), "text": text, "part": part, "mode": mode, "split": "learned"}
    if os.environ.get("FMEA_NO_LEARN") == "1": return rec        # automatic tests must not teach the assistant
    with open(LEARNED, "a", encoding="utf-8") as fh: fh.write(json.dumps(rec) + "\n")
    return rec

class Memory:
    def __init__(self, cases):
        self.cases = cases; self.docs = [set(_fix_typos(toks(c["text"]))) for c in cases]
        df = {}
        for d in self.docs:
            for w in d: df[w] = df.get(w, 0) + 1
        n = max(1, len(self.docs)); self.idf = {w: math.log(1 + n / k) for w, k in df.items()}; self.default = math.log(1 + n)
    def _w(self, w): return self.idf.get(w, self.default)
    def similar(self, text, skip_id=None, k=3):
        q = set(_fix_typos(toks(text))); out = []
        nq = math.sqrt(sum(self._w(w) ** 2 for w in q)) or 1.0
        for c, d in zip(self.cases, self.docs):
            if skip_id is not None and c.get("id") == skip_id: continue
            nd = math.sqrt(sum(self._w(w) ** 2 for w in d)) or 1.0
            sim = sum(self._w(w) ** 2 for w in q & d) / (nq * nd)
            if sim >= MIN_SIM: out.append((sim, c))
        out.sort(key=lambda x: -x[0]); return out[:k]
    def boost(self, text, skip_id=None):
        """{part: factor >= 1} from the most similar remembered cases."""
        b = {}
        for sim, c in self.similar(text, skip_id):
            b[c["part"]] = max(b.get(c["part"], 1.0), math.exp(K * (sim - MIN_SIM)))
        return b
