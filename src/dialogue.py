"""Extra steps for the interactive assistant (NOT used in the evaluation, so the test results stay comparable).

 clarify()      - after a diagnosis, decide if one more question would separate the top causes; if yes, give it.
 manual_pages() - find the assembly-manual pages for a component (BM25 over the manual pages; no model call).
 fix_plan()     - short, numbered repair steps for the chosen component, grounded in its card and manual pages.
All three use the same local model as the agent (or the offline stub).
"""
import json, re, pathlib
from agent import chat, COMP
from retrieval import BM25
from tools import compact_text, load_jsonl, IDX
from config import STUB

A = pathlib.Path(__file__).resolve().parents[1]
KG = json.loads((A / "data/kg/kg.json").read_text(encoding="utf-8"))
MANUAL = "VORON_V0.2r1_Assembly_Manual.pdf"
_pages = [d for d in load_jsonl(IDX / "chunks_B.jsonl") if d["source"] == MANUAL]
_bm25 = BM25([d["text"] for d in _pages])
MAX_QUESTIONS = 3

def _json(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    try: return json.loads(m.group(0)) if m else {}
    except Exception: return {}

def clarify(symptom, candidates, asked):
    """candidates: agent answer list. asked: questions already asked in this case.
    Returns {"question": str, "options": [...], "separates": [id, id]} or None when the picture is clear."""
    ids = [c["component_id"] for c in candidates][:3]
    if len(ids) < 2 or len(asked) >= MAX_QUESTIONS: return None
    if STUB:   # offline: ask the check of the second candidate once
        if asked: return None
        f = KG[ids[1]]["failure_modes"][0]
        return {"question": f"Do you also see this: {f['symptom']}?", "options": ["Yes", "No", "Not sure"], "separates": ids[:2]}
    cards = "\n---\n".join(compact_text(KG[i]) for i in ids)
    prev = "\n".join(f"- {q}" for q in asked) or "- none"
    prompt = f"""A technician reported this about a Voron 0.2 3D printer: "{symptom}"
The current most likely faulty components are (best first):
{cards}
Questions already asked:
{prev}
Decide if ONE more short question to the technician would clearly separate the first component from the others.
Only ask about things a technician can observe or test in under two minutes (sounds, temperatures in the web interface,
whether it happens only when the head moves, a fan spinning, a connector feeling loose). Do not repeat a question.
Answer ONLY with JSON: {{"enough": true or false, "question": "...", "options": ["Yes","No","Not sure"], "separates": ["<id>","<id>"]}}"""
    r = _json(chat([{"role": "user", "content": prompt}], None).get("content", ""))
    if r.get("enough") or not r.get("question"): return None
    q = r["question"].strip()
    if any(q.lower() == a.lower() for a in asked): return None
    return {"question": q, "options": r.get("options") or ["Yes", "No", "Not sure"], "separates": r.get("separates") or ids[:2]}

def manual_pages(cid, k=3):
    """The k manual pages that best match the component name, its function and its failure checks."""
    c = KG[cid]
    q = " ".join([c["name"], c["name"], c["function"]] + [f["check"] for f in c["failure_modes"]])
    s = _bm25.scores(q)
    best = sorted(range(len(_pages)), key=lambda i: -s[i])[:k]
    out = []
    for i in best:
        p = int(re.sub(r"\D", "", _pages[i]["section"]) or 1)
        if not any(o["page"] == p for o in out): out.append({"page": p, "text": _pages[i]["text"][:900]})
    return out

def fix_plan(symptom, cid):
    """Numbered steps to confirm and fix the fault in component cid. Every step names its source."""
    c = KG[cid]; pages = manual_pages(cid)
    values = [f"{p['key']} = {p['value']} ({p['source']})" for p in c["parameters"]]
    base = {"component": cid, "name": c["name"], "values": values, "pages": [p["page"] for p in pages]}
    if STUB:
        steps = [{"step": f["check"], "source": c["source"]} for f in c["failure_modes"]]
        steps += [{"step": f"Compare with the correct value: {v}", "source": "config"} for v in values[:2]]
        steps.append({"step": "See the assembly manual pages shown on the right for how it is mounted.", "source": f"{MANUAL} p.{pages[0]['page']}" if pages else "manual"})
        return {**base, "steps": steps}
    ctx = "\n".join(f"[{MANUAL} p.{p['page']}] {p['text']}" for p in pages)
    prompt = f"""A technician reported: "{symptom}". The most likely faulty component is {c['name']} ({cid}).
Component card:
{compact_text(c)}
Correct values: {'; '.join(values) or 'none'}
Assembly manual pages:
{ctx}
Write 3 to 6 short numbered steps: first how to confirm this is the fault, then how to fix it, then how to test the fix.
Use only the information above; if the documents do not say something, write a safe general step and mark its source "general".
Answer ONLY with JSON: {{"steps": [{{"step": "...", "source": "card / config file:line / {MANUAL} p.N / general"}}]}}"""
    r = _json(chat([{"role": "user", "content": prompt}], None).get("content", ""))
    steps = [s for s in r.get("steps", []) if isinstance(s, dict) and s.get("step")]
    if not steps: steps = [{"step": f["check"], "source": "card"} for f in c["failure_modes"]]
    return {**base, "steps": steps}
