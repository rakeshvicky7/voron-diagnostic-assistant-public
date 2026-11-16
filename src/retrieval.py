"""Hybrid retrieval used by every arm: BM25 + dense embeddings, merged with reciprocal rank fusion.
Works on any list of documents {id, text, ...}. Embeddings come from Ollama and are cached on disk."""
import json, math, re, hashlib, pathlib, urllib.request
from collections import Counter
import numpy as np
from config import OLLAMA_URL, EMBED_MODEL, STUB, EMBED_STUB, RRF_K

TOK = re.compile(r"[a-z0-9_]+")
def tokens(t): return TOK.findall(t.lower())

class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.toks = [tokens(d) for d in docs]; self.k1, self.b = k1, b
        self.avg = sum(map(len, self.toks)) / max(1, len(self.toks))
        df = Counter(w for t in self.toks for w in set(t)); N = len(self.toks)
        self.idf = {w: math.log(1 + (N - n + 0.5) / (n + 0.5)) for w, n in df.items()}
        self.tf = [Counter(t) for t in self.toks]
    def scores(self, q):
        qs = tokens(q); out = []
        for tf, t in zip(self.tf, self.toks):
            s = 0.0
            for w in qs:
                if w in tf:
                    f = tf[w]; s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * len(t) / self.avg))
            out.append(s)
        return np.array(out)

def embed(texts):
    if EMBED_STUB:   # deterministic hashed bag-of-words, only for offline testing
        V = np.zeros((len(texts), 512))
        for i, t in enumerate(texts):
            for w in tokens(t): V[i, int(hashlib.md5(w.encode()).hexdigest(), 16) % 512] += 1
        return V / (np.linalg.norm(V, axis=1, keepdims=True) + 1e-9)
    out = []
    for i in range(0, len(texts), 32):
        req = urllib.request.Request(OLLAMA_URL + "/api/embed", data=json.dumps({"model": EMBED_MODEL, "input": texts[i:i+32]}).encode(),
                                     headers={"Content-Type": "application/json"})
        out += json.loads(urllib.request.urlopen(req, timeout=600).read())["embeddings"]
    V = np.array(out); return V / (np.linalg.norm(V, axis=1, keepdims=True) + 1e-9)

class HybridIndex:
    def __init__(self, name, docs, cache_dir):
        self.docs = docs; texts = [d["text"] for d in docs]
        self.bm25 = BM25(texts)
        tag = "stub" if EMBED_STUB else EMBED_MODEL.replace(":", "_").replace("/", "_")
        f = pathlib.Path(cache_dir) / f"emb_{name}_{tag}.npy"
        if f.exists() and np.load(f).shape[0] == len(docs): self.E = np.load(f)
        else:
            print(f"  embedding {len(docs)} items for index {name} (one-time)..."); self.E = embed(texts); np.save(f, self.E)
    def search(self, q, k, mode="hybrid"):
        b = self.bm25.scores(q)
        if mode == "bm25": return [self.docs[i] for i in np.argsort(-b)[:k]]   # words only: identical on every machine
        d = self.E @ embed([q])[0]
        rb = {i: r for r, i in enumerate(np.argsort(-b))}; rd = {i: r for r, i in enumerate(np.argsort(-d))}
        fused = sorted(range(len(self.docs)), key=lambda i: -(1 / (RRF_K + rb[i]) + 1 / (RRF_K + rd[i])))
        return [self.docs[i] for i in fused[:k]]
