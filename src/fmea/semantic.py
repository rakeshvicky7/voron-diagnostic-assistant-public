"""Meaning-based symptom matching (optional experiment).

The word matcher in engine.link() only finds a symptom when the technician uses words close to a stored wording.
This module adds a second reader: every wording is turned into an embedding (768 numbers) once with the small
embedding model nomic-embed-text (run by Ollama, NO language model), and each clause of the technician's text is
compared with all wordings by cosine similarity. A symptom whose best wording is close enough in meaning is added,
but only if the word matcher did not already decide about it.

Switched OFF by default, so the thesis results stay unchanged. Switch on with:
    $env:F_SEM="1"           (threshold: $env:F_SEM_T="0.72", prefixes: $env:F_SEM_PREFIX="1")
Needs Ollama running with nomic-embed-text, but works with STUB=1 (the language model stays off).
"""
import os, re, json, hashlib, pathlib, urllib.request
import numpy as np

A = pathlib.Path(__file__).resolve().parents[2]
CACHE_DIR = A / "data" / "indexes"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
FAKE = os.environ.get("F_SEM_FAKE") == "1"      # offline plumbing test only (hashed words, no meaning)

THRESHOLD = float(os.environ.get("F_SEM_T", 0.72))   # minimum cosine similarity
PREFIX = os.environ.get("F_SEM_PREFIX", "1") == "1"  # nomic task prefixes: search_query / search_document
TOP_PER_CLAUSE = int(os.environ.get("F_SEM_K", 2))   # at most this many symptoms from one clause
NEG = re.compile(r"\b(no|not|never|without|n't|dont|doesnt|didnt|isnt|wasnt|cannot|cant)\b")

_index = None   # (matrix of wording vectors, list of symptom ids, list of wordings)


def _embed(texts):
    if FAKE:
        V = np.zeros((len(texts), 512))
        for i, t in enumerate(texts):
            for w in re.findall(r"[a-z0-9]+", t.lower()): V[i, int(hashlib.md5(w.encode()).hexdigest(), 16) % 512] += 1
        return V / (np.linalg.norm(V, axis=1, keepdims=True) + 1e-9)
    out = []
    for i in range(0, len(texts), 32):
        body = json.dumps({"model": MODEL, "input": texts[i:i + 32]}).encode()
        req = urllib.request.Request(OLLAMA_URL + "/api/embed", data=body, headers={"Content-Type": "application/json"})
        out += json.loads(urllib.request.urlopen(req, timeout=600).read())["embeddings"]
    V = np.array(out, dtype=float)
    return V / (np.linalg.norm(V, axis=1, keepdims=True) + 1e-9)


def _build():
    """Embed all wordings once and cache them on disk (rebuilt automatically if the wordings change)."""
    global _index
    from .kb_symptoms import S
    sids, words = [], []
    for sid, (q, how, says) in S.items():
        for w in says: sids.append(sid); words.append(w)
    docs = [("search_document: " if PREFIX else "") + w for w in words]
    tag = hashlib.md5(("|".join(docs) + MODEL + str(FAKE)).encode()).hexdigest()[:10]
    f = CACHE_DIR / f"emb_SYM_{'fake' if FAKE else MODEL.replace(':', '_')}_{tag}.npy"
    if f.exists(): E = np.load(f)
    else:
        print(f"  embedding {len(docs)} symptom wordings (one-time)...")
        E = _embed(docs); CACHE_DIR.mkdir(parents=True, exist_ok=True); np.save(f, E)
    _index = (E, sids, words)
    return _index


def match(text, threshold=None):
    """{symptom id: confidence} found by meaning. Clauses with a negation are skipped (the word matcher handles 'not')."""
    t = THRESHOLD if threshold is None else threshold
    E, sids, words = _index or _build()
    clauses = [c.strip() for c in re.split(r"[.;!?]|\bbut\b", text.lower()) if len(c.strip().split()) >= 2]
    clauses = [c for c in clauses if not NEG.search(c)]
    if not clauses: return {}
    Q = _embed([("search_query: " if PREFIX else "") + c for c in clauses])
    out = {}
    for qv in Q:
        sim = E @ qv
        best = {}
        for i in np.argsort(-sim)[:40]:                       # best wording per symptom
            if sim[i] < t: break
            best.setdefault(sids[i], float(sim[i]))
        for sid, s in sorted(best.items(), key=lambda x: -x[1])[:TOP_PER_CLAUSE]:
            conf = round(min(0.9, 0.55 + 0.4 * (s - t) / max(1e-6, 1 - t)), 2)
            out[sid] = max(out.get(sid, 0), conf)
    return out


def explain(text, k=5):
    """For the testbench: the closest wordings per clause, with their similarity."""
    E, sids, words = _index or _build()
    clauses = [c.strip() for c in re.split(r"[.;!?]|\bbut\b", text.lower()) if len(c.strip().split()) >= 2] or [text.lower()]
    Q = _embed([("search_query: " if PREFIX else "") + c for c in clauses])
    res = []
    for c, qv in zip(clauses, Q):
        sim = E @ qv
        res.append({"clause": c, "negated": bool(NEG.search(c)), "closest": [{"symptom": sids[i], "wording": words[i], "sim": round(float(sim[i]), 3)} for i in np.argsort(-sim)[:k]]})
    return res
