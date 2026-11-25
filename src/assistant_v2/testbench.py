"""Testbench: compare the symptom graph (FMEA) alone with the symptom graph + language model (arm G boost).

Used by the /testbench page. Nothing here changes the assistant: it calls the same functions as src/fmea/evaluate.py
(link -> posterior -> sum per part; arm G top 3 as a 5/3/2 boost), so the numbers match the evaluation.
Arm G answers come from (1) the saved evaluation run (eval/results_raw.jsonl), (2) this page's own cache
(eval/g_cache.json), or (3) a live run through Ollama when asked for.
"""
import json, threading, pathlib
from fmea.engine import link, mentions, posterior, boost_from_ranking, MODES, PRIOR, G_W, p_sym
from fmea.kb_symptoms import S
from fmea import evaluate as EV

A = pathlib.Path(__file__).resolve().parents[2]
CACHE = A / "eval" / "g_cache.json"
_lock = threading.Lock()
_cases = None
_saved = None

DEV = {"practice", "test_A"}          # used while building: shown, but marked as development cases


def _cache():
    try: return json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception: return {}


def _cache_put(key, top3):
    with _lock:
        c = _cache(); c[key] = top3
        CACHE.write_text(json.dumps(c, indent=1), encoding="utf-8")


def cases():
    """All test cases: {id: dict(set, text, ok, primary)}."""
    global _cases, _saved
    if _cases is None:
        _cases = {}
        try: loaded = EV.load()
        except Exception: loaded = {}          # online version: the test data may be absent
        for name, rows in loaded.items():
            for cid, text, ok, prim in rows:
                _cases[cid] = {"id": cid, "set": name, "text": text, "ok": sorted(ok), "primary": prim, "dev": name in DEV}
        try: _saved = EV.g_preds()
        except Exception: _saved = {}
    return _cases


def g_answer(key, text, live, ollama_ok):
    """Arm G top 3 for a case id or a free text. Returns (top3 or None, where it came from)."""
    cases()
    if key in _saved: return _saved[key], "saved evaluation run"
    c = _cache()
    if key in c: return c[key], "cached live run"
    if not live: return None, "not run"
    if not ollama_ok: return None, "Ollama not running"
    from assistant_v2 import engine as E2
    E2.USE_AGENT_PRIOR = True
    top3 = E2.agent_top3(text)
    if top3: _cache_put(key, top3)
    return (top3 or None), ("live run" if top3 else "live run failed")


def _modes_table(pm, ev, k=8):
    rows = []
    for mid, p in sorted(pm.items(), key=lambda x: -x[1])[:k]:
        m = MODES[mid]
        rows.append({"id": mid, "part": m["part"], "name": m["name"], "p": round(p, 4), "start": round(PRIOR[mid], 3),
                     "sym": [{"id": sid, "P": round(p_sym(mid, sid), 2), "listed": sid in m["s"]} for sid in ev]})
    return rows


from contextlib import contextmanager
from fmea import engine as _ENG

_sem_lock = threading.RLock()

@contextmanager
def semantic(on):
    """Switch meaning-based symptom matching on or off for one request."""
    with _sem_lock:
        old = _ENG.SEM_ON; _ENG.SEM_ON = bool(on)
        try: yield
        finally: _ENG.SEM_ON = old


def analyze(text, use_llm=False, case_id=None, live=True, ollama_ok=False, sem=False):
    with semantic(sem):
        return _analyze(text, use_llm, case_id, live, ollama_ok, sem)


def _analyze(text, use_llm, case_id, live, ollama_ok, sem):
    ev = link(text); named = sorted(mentions(text))
    pm0, pp0 = posterior(ev, named=named)
    out = {"symptoms": [{"id": s, "conf": c, "q": S[s][0], "how": S[s][1]} for s, c in sorted(ev.items(), key=lambda x: -abs(x[1]))],
           "named": named, "modes": _modes_table(pm0, ev), "parts": [[p, round(v, 4)] for p, v in list(pp0.items())[:6]]}
    if sem:
        try:
            from fmea import semantic as SM
            out["closest"] = SM.explain(text)
        except Exception as e: out["closest_error"] = str(e)
    if use_llm:
        g, src = g_answer(case_id or ("text:" + text.strip().lower()), text, live, ollama_ok)
        out["g"] = g; out["g_source"] = src; out["g_weights"] = list(G_W)
        if g:
            pm1, pp1 = posterior(ev, named=named, boost=boost_from_ranking(g))
            out["modes_llm"] = _modes_table(pm1, ev); out["parts_llm"] = [[p, round(v, 4)] for p, v in list(pp1.items())[:6]]
    return out


def _rank(lst, ok):
    for i, p in enumerate(lst):
        if p in ok: return i + 1
    return None


def run_case(cid, llm="none", ollama_ok=False, sem=False):
    with semantic(sem):
        return _run_case(cid, llm, ollama_ok)


def _run_case(cid, llm="none", ollama_ok=False):
    """One test case, scored exactly like src/fmea/evaluate.py."""
    c = cases()[cid]; ok = set(c["ok"]); text = c["text"]
    ev = link(text); named = mentions(text)
    _, pp0 = posterior(ev, named=named); r0 = list(pp0)[:5]
    res = {**c, "symptoms": [s for s, v in ev.items() if v > 0], "fmea": r0[:3], "rank0": _rank(r0, ok)}
    if llm != "none":
        g, src = g_answer(cid, text, llm == "live", ollama_ok)
        res["g"] = g; res["g_source"] = src
        if g:
            _, pp1 = posterior(ev, named=named, boost=boost_from_ranking(g)); r1 = list(pp1)[:5]
            res["final"] = r1[:3]; res["rank1"] = _rank(r1, ok); res["g_rank"] = _rank(g, ok)
    return res
