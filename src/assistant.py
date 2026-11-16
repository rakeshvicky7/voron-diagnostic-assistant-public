"""Voron 0.2 Repair Assistant: voice + visual front end on top of the tested agent (arm G by default).

Run (from the agent folder):   py -3.12 src\\assistant.py        then open http://localhost:8800
Options: --arm G   --port 8800      Offline demo without Ollama:  $env:STUB="1"; py -3.12 src\\assistant.py

What it adds on top of the agent (none of this is used in the evaluation):
 1. Questions until the picture is clear (dialogue.clarify, at most 3 per case)
 2. Printer view: the parts where the symptom shows (orange) and the likely cause (red), with the fault
    "travelling" along the graph path from cause to symptom
 3. Cause map: the full failure graph (Cytoscape.js) with the paths highlighted
 4. Fix it: numbered steps with sources, correct values, and the assembly-manual pages opened at the right page
 5. Voice: speak instead of typing (faster-whisper, or the browser) and hear the answer (Piper, or the browser)
 6. Photo: describe what you see with a picture (optional vision model in Ollama, e.g. qwen2.5vl:3b)
Feedback goes to eval/assistant_feedback.jsonl.
"""
import json, time, argparse, threading, pathlib, base64, os, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from agent import diagnose, COMP
from tools import Toolbox
from config import LLM_MODEL, STUB, OLLAMA_URL
import dialogue, voice

A = pathlib.Path(__file__).resolve().parents[1]; ROOT = A.parent
PAGE = pathlib.Path(__file__).resolve().parent / "assistant" / "index.html"
MANUAL_PDF = ROOT / "corpus" / "02_assembly_manual" / "VORON_V0.2r1_Assembly_Manual.pdf"
FEEDBACK = A / "eval" / "assistant_feedback.jsonl"
VISION_MODEL = os.environ.get("VISION_MODEL", "qwen2.5vl:3b")
GRAPH = json.loads((A / "data/graph/graph.json").read_text(encoding="utf-8"))
_boxes, _lock = {}, threading.Lock()

def box(arm):
    if arm not in _boxes: _boxes[arm] = Toolbox(arm)
    return _boxes[arm]

def symptom_of(history):
    """First user message is the symptom; each later answer is attached to the question it answers."""
    parts, last_q = [], None
    for h in history:
        if h["role"] == "agent": last_q = h.get("question") or None
        elif h["role"] == "user":
            t = h["text"].strip()
            parts.append(f"(Asked: {last_q} Technician: {t})" if last_q else t); last_q = None
    return " ".join(parts)

def diagnose_turn(arm, history, asked):
    symptom = symptom_of(history); agent_q = []
    def technician(q): agent_q.append(q); return "The technician has not answered yet. Give your best answer now."
    with _lock:
        tb = box(arm); t = time.time()
        r = diagnose(symptom, arm, tb, technician)
        cands = [{**c, "name": COMP[c["component_id"]]["name"]} for c in r["candidates"]]
        q = None
        if agent_q and agent_q[0] not in asked and len(asked) < dialogue.MAX_QUESTIONS:
            q = {"question": agent_q[0], "options": ["Yes", "No", "Not sure"], "separates": []}
        if q is None and cands: q = dialogue.clarify(symptom, cands, asked)
    out = {"symptom": symptom, "secs": round(time.time() - t, 1), "arm": arm,
           "model": "STUB (offline demo)" if STUB else LLM_MODEL, "candidates": cands, "question": q, "graph": None}
    g = r.get("graph")
    if g and hasattr(tb, "fgraph"):
        out["graph"] = {"seeds": g["seeds"], "upstream": [{"id": u["id"], "score": u["score"], "explains": u["explains"]} for u in g["upstream"]]}
    # paths from each candidate to the parts where the symptom shows (for the "fault travels" animation)
    seeds = g["seeds"] if g else []
    fg = tb.fgraph if hasattr(tb, "fgraph") else None
    if fg is None:
        from graph_rag import FailureGraph; fg = FailureGraph()
    for c in cands:
        c["paths"] = [p for p in (fg.path(c["component_id"], s) for s in seeds[:3] if s != c["component_id"]) if p]
    return out

def describe_photo(b64):
    if STUB: return "(offline demo) a photo of the toolhead; the hotend fan is not spinning."
    body = {"model": VISION_MODEL, "stream": False, "images": [b64], "options": {"temperature": 0},
            "prompt": "This is a photo of part of a Voron 0.2 3D printer taken by a technician during a fault. "
                      "Describe in 2-3 short sentences only what is visible that could matter for finding the fault "
                      "(which part, damage, loose or burnt wires, filament problems, print defects). Do not guess the cause."}
    req = urllib.request.Request(OLLAMA_URL + "/api/generate", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=600).read())["response"].strip()

def meta():
    kg = dialogue.KG
    return {"components": {k: {"name": v["name"], "subsystem": v["subsystem"], "class": v["cls"]} for k, v in COMP.items()},
            "edges": [{"src": e["src"], "dst": e["dst"], "rel": e["rel"]} for e in GRAPH["edges"]],
            "cards": {k: {"function": c["function"], "failure_modes": c["failure_modes"],
                          "values": [f"{p['key']} = {p['value']}" for p in c["parameters"]][:6]} for k, c in kg.items()},
            "voice": voice.status(), "model": "STUB (offline demo)" if STUB else LLM_MODEL, "arm": DEFAULT_ARM,
            "manual": MANUAL_PDF.exists(), "vision_model": VISION_MODEL}

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(b)
    def _json(self, obj, code=200): self._send(code, json.dumps(obj), "application/json; charset=utf-8")
    def do_GET(self):
        path = self.path.split("?")[0].split("#")[0]
        if path == "/": return self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        if path == "/api/meta": return self._json(meta())
        if path == "/manual.pdf" and MANUAL_PDF.exists(): return self._send(200, MANUAL_PDF.read_bytes(), "application/pdf")
        self._send(404, b"not found", "text/plain")
    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0)
        try:
            if self.path == "/api/stt":
                ctype = self.headers.get("Content-Type", "audio/webm")
                return self._json({"text": voice.transcribe(raw, ".ogg" if "ogg" in ctype else ".webm")})
            d = json.loads(raw or b"{}")
            if self.path == "/api/diagnose":
                arm = d.get("arm") if d.get("arm") in ("A", "B", "BP", "C", "D", "E", "G") else DEFAULT_ARM
                return self._json(diagnose_turn(arm, d.get("history") or [], d.get("asked") or []))
            if self.path == "/api/fix":
                with _lock: plan = dialogue.fix_plan(d.get("symptom", ""), d["component_id"])
                return self._json(plan)
            if self.path == "/api/tts": return self._send(200, voice.speak(d.get("text", "")[:1500]), "audio/wav")
            if self.path == "/api/photo":
                with _lock: return self._json({"text": describe_photo(d["image"].split(",")[-1])})
            if self.path == "/api/feedback":
                FEEDBACK.parent.mkdir(exist_ok=True)
                with open(FEEDBACK, "a", encoding="utf-8") as f: f.write(json.dumps({"time": time.strftime("%Y-%m-%d %H:%M:%S"), **d}) + "\n")
                return self._json({})
            self._json({"error": "unknown endpoint"}, 404)
        except Exception as e:
            self._json({"error": f"{type(e).__name__}: {e}"})
    def log_message(self, *a): pass

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--arm", default="G"); ap.add_argument("--port", type=int, default=8800)
    a = ap.parse_args(); DEFAULT_ARM = a.arm
    print(f"Loading arm {a.arm} ..."); box(a.arm)
    s = voice.status()
    print("Voice in :", "faster-whisper (offline)" if s["stt"] else s["stt_note"])
    print("Voice out:", "Piper (offline)" if s["tts"] else s["tts_note"])
    print(f"Open http://localhost:{a.port}   (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()
