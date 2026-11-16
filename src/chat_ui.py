"""Chat interface for trying the diagnostic agent by hand.

Run (Windows, from the agent folder):   py -3.12 src\\chat_ui.py          then open http://localhost:8765
Options:  --arm G (default)   --port 8765
Only the Python standard library is used (no extra installs). Ollama must be running, as for run_eval.py.

What it does
 - You type a symptom. The agent runs exactly as in the evaluation (same prompt, model, tools, budget).
 - It shows the top-3 components with reason, check, correct value and source.
 - For arm G it also shows the graph evidence: where the symptom may appear (seeds) and the upstream
   causes with their propagation paths.
 - If the agent wants to ask the technician a question, the question is shown; your next message is
   added to the symptom (the conversation is combined into one description) and the agent runs again.
 - You can mark each answer as correct or wrong (and name the right part). Feedback is saved to
   eval/chat_feedback.jsonl. This is for your own checking; it is NOT part of the test-set results.
"""
import json, time, argparse, threading, pathlib, runpy, html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from agent import diagnose
from tools import Toolbox
from config import LLM_MODEL, STUB

A = pathlib.Path(__file__).resolve().parents[1]
COMP = runpy.run_path(str(A / "data/kg/components.yaml.py"))["COMPONENTS"]
FEEDBACK = A / "eval" / "chat_feedback.jsonl"
ARMS = {"G": "G - graph RAG (cards + failure graph)", "E": "E - cards + generic guide", "C": "C - component cards",
        "BP": "BP - documents + machine files as text", "B": "B - documents as text", "D": "D - generic guide", "A": "A - no knowledge"}
_boxes, _lock = {}, threading.Lock()   # one toolbox per arm; one model call at a time (one GPU)

def box(arm):
    if arm not in _boxes: _boxes[arm] = Toolbox(arm)
    return _boxes[arm]

def run(arm, history):
    """history: list of {"role": "user"|"agent", "text": ...}. All user messages form one symptom description;
    earlier agent questions are kept so the model knows what the technician is answering."""
    lines = []
    for h in history:
        if h["role"] == "user": lines.append(h["text"].strip())
        elif h.get("question"): lines.append(f"(Agent asked: {h['question']})")
    symptom = " ".join(lines)
    asked = []
    def technician(q):            # a web page cannot answer in the middle of a run: record the question
        asked.append(q); return "The technician has not answered yet. Give your best answer now."
    with _lock:
        tb = box(arm); t = time.time()
        r = diagnose(symptom, arm, tb, technician)
    out = {"symptom": symptom, "secs": round(time.time() - t, 1), "model": "STUB (offline test)" if STUB else LLM_MODEL,
           "arm": arm, "questions": asked, "candidates": [], "graph": None}
    for c in r["candidates"]:
        out["candidates"].append({**c, "name": COMP[c["component_id"]]["name"]})
    g = r.get("graph")
    if g:
        out["graph"] = {"seeds": [{"id": s, "name": COMP[s]["name"]} for s in g["seeds"]],
                        "upstream": [{"id": u["id"], "name": COMP[u["id"]]["name"], "score": u["score"],
                                      "paths": [tb.fgraph.path(u["id"], s) for s in u["explains"]]} for u in g["upstream"]]}
    return out

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>Voron 0.2 diagnostic agent</title>
<style>
body{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f4f5f7;color:#222}
header{background:#1f3a5f;color:#fff;padding:12px 20px;display:flex;gap:16px;align-items:center}
header h1{font-size:18px;margin:0;flex:1} select,button,input,textarea{font:inherit}
#chat{max-width:900px;margin:16px auto;padding:0 12px 140px}
.msg{margin:10px 0;padding:10px 14px;border-radius:8px;background:#fff;box-shadow:0 1px 2px #0002}
.user{background:#dbe8f7;margin-left:80px}.meta{color:#666;font-size:12px}
.cand{border-left:4px solid #1f3a5f;padding:6px 10px;margin:8px 0;background:#fafbfc}
.cand b{font-size:15px}.k{color:#555;font-weight:600}
details{margin-top:8px}summary{cursor:pointer;color:#1f3a5f;font-weight:600}
.path{font-family:Consolas,monospace;font-size:12px;color:#333}
.q{background:#fff4d6;padding:6px 10px;border-radius:6px;margin-top:8px}
.fb{margin-top:10px;font-size:13px}.fb button{margin-right:6px}
#bar{position:fixed;bottom:0;left:0;right:0;background:#fff;border-top:1px solid #ccc;padding:10px}
#bar div{max-width:900px;margin:auto;display:flex;gap:8px}
textarea{flex:1;height:54px;padding:6px}#send{background:#1f3a5f;color:#fff;border:0;padding:0 20px;border-radius:6px}
</style></head><body>
<header><h1>Voron 0.2 diagnostic agent</h1>
<label>Arm <select id="arm">__ARMS__</select></label><button onclick="newCase()">New case</button></header>
<div id="chat"><div class="msg meta">Describe a symptom in your own words. If the agent asks a question,
answer it in the next message; it is added to the same case. Press <b>New case</b> to start over.</div></div>
<div id="bar"><div><textarea id="box" placeholder="e.g. the hotend fan stops and the temperature jumps when the head moves"></textarea>
<button id="send" onclick="send()">Send</button></div></div>
<script>
let hist=[];const chat=document.getElementById('chat');
const esc=s=>(s||'').toString().replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function add(h){const d=document.createElement('div');d.innerHTML=h;chat.appendChild(d.firstChild);window.scrollTo(0,document.body.scrollHeight);return chat.lastChild}
function newCase(){hist=[];add('<div class="msg meta">--- new case ---</div>')}
document.getElementById('box').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}});
async function send(){const b=document.getElementById('box');const t=b.value.trim();if(!t)return;b.value='';
 hist.push({role:'user',text:t});add('<div class="msg user">'+esc(t)+'</div>');
 const wait=add('<div class="msg meta">Thinking... (a local model can take a minute)</div>');
 try{const r=await (await fetch('/api/diagnose',{method:'POST',body:JSON.stringify({arm:document.getElementById('arm').value,history:hist})})).json();
  wait.remove();if(r.error){add('<div class="msg">Error: '+esc(r.error)+'</div>');return}
  hist.push({role:'agent',question:(r.questions||[])[0]||''});show(r)}catch(e){wait.remove();add('<div class="msg">Error: '+esc(e)+'</div>')}}
function show(r){let h='<div class="msg"><div class="meta">arm '+r.arm+' | '+esc(r.model)+' | '+r.secs+' s</div>';
 if(!r.candidates.length)h+='<p>No valid component given.</p>';
 r.candidates.forEach((c,i)=>{h+='<div class="cand"><b>'+(i+1)+'. '+esc(c.name)+'</b> <span class="meta">('+esc(c.component_id)+')</span><br>'+
  '<span class="k">Why:</span> '+esc(c.reason)+'<br><span class="k">Check:</span> '+esc(c.check)+'<br>'+
  '<span class="k">Correct value:</span> '+esc(c.correct_value)+'<br><span class="k">Source:</span> '+esc(c.source)+'</div>'});
 (r.questions||[]).forEach(q=>h+='<div class="q"><b>Agent asks:</b> '+esc(q)+' <span class="meta">(answer in your next message)</span></div>');
 if(r.graph){h+='<details><summary>Graph evidence</summary><p class="k">Where the symptom may appear:</p><p>'+
  r.graph.seeds.map(s=>esc(s.name)).join(' &middot; ')+'</p><p class="k">Possible upstream causes:</p>';
  r.graph.upstream.forEach(u=>{h+='<div><b>'+esc(u.name)+'</b> <span class="meta">score '+u.score+'</span>'+u.paths.map(p=>'<div class="path">'+esc(p)+'</div>').join('')+'</div>'});h+='</details>'}
 const id='f'+Date.now();h+='<div class="fb" id="'+id+'">Was this right? <button>Correct (1st)</button><button>In top 3</button><button>Wrong</button>'+
  ' right part: <select>'+'__PARTS__'+'</select> <input placeholder="note" size="22"></div></div>';
 const el=add(h);const fb=el.querySelector('.fb');fb.querySelectorAll('button').forEach(btn=>btn.onclick=async()=>{
  await fetch('/api/feedback',{method:'POST',body:JSON.stringify({verdict:btn.textContent,right_part:fb.querySelector('select').value,note:fb.querySelector('input').value,result:r})});
  fb.innerHTML='Saved: '+esc(btn.textContent)})}
</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        b = body.encode("utf-8"); self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8"); self.send_header("Content-Length", str(len(b)))
        self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path != "/": return self._send(404, "{}")
        arms = "".join(f'<option value="{k}"{" selected" if k == DEFAULT_ARM else ""}>{html.escape(v)}</option>' for k, v in ARMS.items())
        parts = '<option value="">-</option>' + "".join(f'<option value="{k}">{html.escape(v["name"])}</option>' for k, v in COMP.items())
        self._send(200, PAGE.replace("__ARMS__", arms).replace("__PARTS__", parts.replace("'", "&#39;")), "text/html")
    def do_POST(self):
        try: d = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        except Exception: return self._send(400, json.dumps({"error": "bad request"}))
        if self.path == "/api/diagnose":
            arm = d.get("arm") if d.get("arm") in ARMS else DEFAULT_ARM
            try: self._send(200, json.dumps(run(arm, d.get("history") or [])))
            except Exception as e: self._send(200, json.dumps({"error": f"{type(e).__name__}: {e}"}))
        elif self.path == "/api/feedback":
            FEEDBACK.parent.mkdir(exist_ok=True)
            with open(FEEDBACK, "a", encoding="utf-8") as f:
                f.write(json.dumps({"time": time.strftime("%Y-%m-%d %H:%M:%S"), **d}) + "\n")
            self._send(200, "{}")
        else: self._send(404, "{}")
    def log_message(self, *a): pass

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--arm", default="G", choices=list(ARMS)); ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args(); DEFAULT_ARM = a.arm
    print(f"Loading arm {a.arm} ..."); box(a.arm)
    print(f"Open http://localhost:{a.port}   (Ctrl+C to stop)")
    ThreadingHTTPServer.allow_reuse_address = False   # on Windows, True lets a second server silently share the port
    try: srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    except OSError:
        raise SystemExit(f"Port {a.port} is already used by another running server. Stop it (Ctrl+C in its window) or add --port {a.port + 1}.")
    srv.serve_forever()
