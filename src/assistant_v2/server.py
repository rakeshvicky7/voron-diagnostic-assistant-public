"""Voron 0.2 diagnostic chat (assistant v2). Standard library only.

Run from the agent folder:   py -3.12 -m src.assistant_v2.server        then open http://localhost:8900
Demo without Ollama:         $env:STUB="1"; py -3.12 -m src.assistant_v2.server
Every conversation is saved to eval/assistant_v2_sessions/<id>.json (for later evaluation in the thesis).
"""
import json, os, sys, time, threading, pathlib, argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from assistant_v2 import engine as E          # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
LOGS = E.A / "eval" / "assistant_v2_sessions"
SESS, LOCK = {}, threading.Lock()
FMEA = {}
MEMORY = None
PAGES = {"/testbench": "testbench.html", "/": "home.html", "/assembly": "assembly.html", "/repair": "repair.html", "/twin": "twin.html", "/classic": "index.html"}

SHOW_LABEL = {"when": "When", "stop_type": "How it stops", "temp_behaviour": "Temperature", "which_temp": "Which temperature", "fan_state": "Hotend fan spins", "part_fan_state": "Part fan spins",
              "flow_state": "Plastic flow", "motor_behaviour": "Extruder motor", "shift_axis": "Shift direction", "noise": "Noise", "move_by_hand": "Moved by hand", "z_home": "Z homing",
              "first_layer": "First layer", "surface": "Surface", "mcu_state": "Controller board", "fuse_state": "Bed fuse", "psu_led": "Power supply LED", "runout_check": "Runout sensor"}
SHOW_SKIP = {"I can't tell", "About 0 ohm (closed)", "Yes, the LED is on", "Neither, both look normal"}
def match_scenario(part, seen, settings):
    """Pick the simulated scenario (severity / failure mode of the virtual printer) that looks most like what the technician described.
    seen = set of symptom ids recognised in the description. part = None: the printer with the user's settings and no fault."""
    from twin.virtual_printer import VirtualPrinter, PARTS as TPARTS
    from fmea.engine import link
    from assistant_v2.reasoner import NORMAL
    if part and part not in TPARTS: return None
    best = None
    for sev in ((0.3, 0.5, 0.7, 0.9) if part else (0.5,)):
        for seed in ((1, 2) if part else (1,)):
            vp = VirtualPrinter(part or None, sev, seed, settings=settings); says = vp.describe(); o, _ = vp.observations()
            shows = [SHOW_LABEL[k] + ": " + str(v).lower() for k, v in o.items() if k in SHOW_LABEL and v not in NORMAL and v not in SHOW_SKIP]
            sym = {x for x, c in link(says + ". " + ". ".join(shows)).items() if c > 0}
            visible = not says.startswith(("Everything looks normal", "Something seems slightly off"))
            score = len(sym & seen) / max(1, len(sym | seen)) + (0.2 if visible else -0.5)
            if best is None or score > best["score"]:
                best = {"part": part or "", "severity": sev, "seed": seed, "says": says, "mode": vp.mode or "", "shows": shows[:4], "visible": visible, "score": round(score, 3),
                        "klipper": o.get("error_message") if o.get("error_message") not in (None, "none") else ""}
    return best
def CB_MODES():
    from fmea.engine import MODES
    return MODES
def PART_NAME(pid):
    from assistant_v2.extra_parts import EXTRA
    return (E.KG.get(pid) or EXTRA.get(pid) or {}).get("name", pid.replace("_", " "))
_OLLAMA = {"t": 0.0, "up": False}
def ollama_up():
    """True if a language model is available: a cloud provider with a key (PROVIDER=openai), or a running local Ollama."""
    if os.environ.get("PROVIDER", "").lower() == "openai": return bool(os.environ.get("OPENAI_API_KEY"))
    return _ollama_up()
def _ollama_up():
    """Is Ollama answering? A busy Ollama (it is writing an answer) can be slow to reply, so a recent 'yes' is kept for a minute."""
    import urllib.request
    if _OLLAMA["up"] and time.time() - _OLLAMA["t"] < 60: return True
    try:
        from config import OLLAMA_URL; urllib.request.urlopen(OLLAMA_URL + "/api/tags", timeout=2.5).read(); _OLLAMA.update(t=time.time(), up=True); return True
    except Exception:
        _OLLAMA["up"] = False; return False

def save(case, extra=None):
    LOGS.mkdir(parents=True, exist_ok=True)
    data = {k: v for k, v in case.items() if k not in ("hyps", "calcs")}
    data["last_hypotheses"] = case.get("hyps", [])[:5]; data["last_calcs"] = case.get("calcs", [])
    if extra: data.setdefault("feedback", []).append(extra)
    (LOGS / f"{case['id']}.json").write_text(json.dumps(data, indent=1, default=str), encoding="utf-8")

# Online demo: if DEMO_PASSWORD is set, the browser asks for a user name (anything) and this password.
_DEMO_PW = os.environ.get("DEMO_PASSWORD", "")
def _authorized(handler):
    if not _DEMO_PW: return True
    import base64, hmac
    h = handler.headers.get("Authorization", "")
    try: pw = base64.b64decode(h[6:]).decode("utf-8").split(":", 1)[1] if h.startswith("Basic ") else ""
    except Exception: pw = ""
    if hmac.compare_digest(pw, _DEMO_PW): return True
    handler.send_response(401); handler.send_header("WWW-Authenticate", 'Basic realm="Voron assistant demo"')
    handler.send_header("Content-Length", "0"); handler.end_headers(); return False

_GZ = {}                     # static file path -> gzip bytes, compressed once per server run
_GZ_LOCK = threading.Lock()
def _gzip_of(f):
    """Gzip version of a static file: a ready-made .gz next to it (made in the Dockerfile) or compressed once and kept in memory."""
    key = str(f)
    if key in _GZ: return _GZ[key]
    with _GZ_LOCK:
        if key not in _GZ:
            pre = pathlib.Path(key + ".gz")
            if pre.is_file() and pre.stat().st_mtime >= f.stat().st_mtime: _GZ[key] = pre.read_bytes()
            else:
                import gzip
                _GZ[key] = gzip.compress(f.read_bytes(), 6)
    return _GZ[key]

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype, cache="no-store", gz=False):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b)))
        if gz: self.send_header("Content-Encoding", "gzip"); self.send_header("Vary", "Accept-Encoding")
        self.send_header("Cache-Control", cache); self.end_headers(); self.wfile.write(b)
    def _static(self, f, ctype, cache="no-cache"):
        """Send a static file, gzip-compressed when the browser accepts it (the 3D model shrinks from 23 MB to about 7 MB)."""
        if "gzip" in self.headers.get("Accept-Encoding", ""): return self._send(200, _gzip_of(f), ctype, cache, gz=True)
        return self._send(200, f.read_bytes(), ctype, cache)
    def _json(self, o): self._send(200, json.dumps(o, default=str), "application/json; charset=utf-8")
    def do_GET(self):
        if not _authorized(self): return
        path0 = self.path.split("?")[0]
        if path0 in PAGES: return self._static(HERE / "static" / PAGES[path0], "text/html; charset=utf-8")
        if path0.startswith("/app/"):         # shared scripts and styles of the interface
            rel = path0[5:]; f = (HERE / "static" / "app" / rel).resolve()
            if ".." in rel or not str(f).startswith(str((HERE / "static" / "app").resolve())) or not f.is_file(): return self._send(404, b"not found", "text/plain")
            return self._static(f, "text/css; charset=utf-8" if rel.endswith(".css") else "text/javascript; charset=utf-8")
        if path0 == "/api/settings":
            from twin.virtual_printer import SETTINGS, D0
            dflt = {"bed_temp": 90, "belt_a_hz": 110, "belt_b_hz": 110, "z_offset": 0, "xy_current": 1, "e_rotation_distance": 22.23}
            return self._json({k: {"min": lo, "max": hi, "unit": u, "label": lab, "design": D0.get(dk, dflt.get(k)) if dk else dflt.get(k)} for k, (dk, lo, hi, u, lab) in SETTINGS.items()})
        if path0 == "/api/assembly/steps":
            from assembly import qa as AQ
            return self._json(AQ.STEPS)
        if self.path.startswith("/vendor/"):     # three.js, bundled so the 3D view works offline
            rel = self.path.split("?")[0][8:]; f = (HERE / "static" / "vendor" / rel).resolve()
            if ".." in rel or not str(f).startswith(str((HERE / "static" / "vendor").resolve())) or not f.is_file(): return self._send(404, b"not found", "text/plain")
            return self._static(f, "text/javascript; charset=utf-8", "public, max-age=604800")   # three.js never changes: browser keeps it a week
        if path0 == "/api/tb/cases":           # testbench: all test cases + part names
            from assistant_v2 import testbench as TB
            from fmea.engine import PARTS
            from config import EMBED_STUB
            # TESTBENCH_SETS=0 (online version): only part 1 (free descriptions); the test sets are not offered
            sets = os.environ.get("TESTBENCH_SETS", "1") == "1"
            llm = (not E.STUB) and os.environ.get("FMEA_G", "1") == "1" and ollama_up()
            sem = (not EMBED_STUB) and os.environ.get("PROVIDER", "").lower() != "openai" and _ollama_up()   # embeddings need a local Ollama
            return self._json({"cases": list(TB.cases().values()) if sets else [], "names": {p: PART_NAME(p) for p in PARTS},
                               "sets": sets, "llm": llm, "sem": sem,
                               "model": (E.LLM_MODEL + (" (cloud)" if os.environ.get("PROVIDER", "").lower() == "openai" else " (Ollama)")) if llm else ""})
        if self.path == "/api/info":
            up = (not E.STUB) and ollama_up()
            return self._json({"model": "offline demo (rules only)" if E.STUB else E.LLM_MODEL + (" (cloud)" if os.environ.get("PROVIDER", "").lower() == "openai" else ""), "ollama": up, "learn": os.environ.get("FMEA_NO_LEARN") != "1",
                               "mode": "full (symptom graph + language model)" if up and os.environ.get("FMEA_G", "1") == "1" else "symptom graph only (start Ollama for the full mode)"})
        # ---- virtual printer (3D twin) -------------------------------------------------------------------------
        if self.path.startswith("/cad/"):     # the converted official CAD (tools/cad/convert_step.py)
            name = self.path.split("?")[0][5:]
            f = HERE / "static" / "cad" / name
            if "/" in name or "\\" in name or ".." in name or not f.is_file(): return self._send(404, b"not converted yet", "text/plain")
            # the CAD model rarely changes: the browser keeps it a week, so the 3D view loads fast on a second visit
            return self._static(f, "model/gltf-binary" if name.endswith(".glb") else "application/json", "public, max-age=604800")
        if self.path.split("?")[0] == "/api/twin":
            from urllib.parse import urlparse, parse_qs
            from twin.virtual_printer import VirtualPrinter
            q = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
            fault = q.get("fault") or None; sev = float(q["severity"]) if q.get("severity") else None
            settings = json.loads(q["settings"]) if q.get("settings") else None
            vp = VirtualPrinter(fault, sev, int(q.get("seed", 1)), settings=settings)
            return self._json({**vp.visual(), "settings": vp.cfg})
        if self.path == "/api/parts":
            from twin.virtual_printer import PARTS, MODES
            from assistant_v2.extra_parts import EXTRA
            out = []
            for pid in PARTS:
                k = E.KG.get(pid) or EXTRA.get(pid) or {}
                out.append({"id": pid, "name": k.get("name", pid), "subsystem": k.get("subsystem", ""), "function": k.get("function", ""),
                            "failure_modes": [fm.get("mode") if isinstance(fm, dict) else str(fm) for fm in (k.get("failure_modes") or [])][:4],
                            "checks": [fm.get("check") for fm in (k.get("failure_modes") or []) if isinstance(fm, dict) and fm.get("check")][:3],
                            "sim_modes": [m for _, m in MODES.get(pid, [])], "source": k.get("source", "")})
            return self._json(out)
        self._send(404, b"not found", "text/plain")
    def do_POST(self):
        if not _authorized(self): return
        try: d = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
        except Exception: return self._json({"error": "bad request"})
        try:
            if self.path == "/api/turn":
                sid = d.get("session")
                with LOCK:
                    case = SESS.get(sid) or E.new_case(); SESS[case["id"]] = case
                    r = E.turn(case, d.get("message"), d.get("form"))
                    save(case)
                return self._json({"session": case["id"], "reply": r["reply"], "case": r["case"]})
            if self.path == "/api/explain":   # model-written explanation, requested by the page after the instant answer
                case = SESS.get(d.get("session"))
                if not case: return self._json({})
                t = time.time()
                with LOCK: r = E.explain(case)
                r["secs"] = round(time.time() - t, 1); case["log"].append({"time": time.strftime("%H:%M:%S"), "user": None, "reply_type": "explain", "secs": r["secs"]})
                save(case); return self._json(r)
            if self.path in ("/api/tb/analyze", "/api/tb/case"):     # testbench: symptom graph with / without the language model
                from assistant_v2 import testbench as TB
                ok = (not E.STUB) and os.environ.get("FMEA_G", "1") == "1" and ollama_up()
                if self.path == "/api/tb/case" and os.environ.get("TESTBENCH_SETS", "1") != "1": return self._json({"error": "test sets are not available in this version"})
                if self.path == "/api/tb/analyze":
                    return self._json(TB.analyze(d.get("text", ""), bool(d.get("llm")), d.get("case"), True, ok, bool(d.get("sem"))))
                return self._json(TB.run_case(d["id"], d.get("llm", "none"), ok, bool(d.get("sem"))))
            if self.path == "/api/fmea":            # the final assistant: symptom graph + case memory + arm G reading
                from fmea.engine import Session, S as SYM, check_input, boost_from_ranking
                from fmea import cases as CB
                global MEMORY
                sid = d.get("session")
                llm_on = d.get("llm", True) is not False          # the page's "Language model" switch (on by default)
                llm_possible = (not E.STUB) and os.environ.get("FMEA_G", "1") == "1"
                use_g = llm_possible and llm_on
                with LOCK:
                    if MEMORY is None: MEMORY = CB.Memory(CB.load())
                    ses = FMEA.get(sid)
                    if ses is None or d.get("new"):
                        import uuid; ses = Session(); sid = uuid.uuid4().hex[:8]; FMEA[sid] = ses; ses.refined = False
                    if d.get("message") and not ses.notes:
                        msg = check_input(d["message"])
                        if msg and msg.startswith("I could not recognise"):   # vague description: ask which concrete symptom it is
                            from fmea.triage import clarify
                            return self._json({"session": sid, "type": "clarify", **clarify(d["message"])})
                        if msg: return self._json({"session": sid, "type": "notice", "text": msg})
                    if d.get("message"):
                        ses.describe(d["message"]); text = " ".join(ses.notes)
                        ses.similar = MEMORY.similar(text); ses.mem_boost = MEMORY.boost(text)
                    if d.get("answer"): ses.answer(d["answer"]["id"], {"yes": True, "no": False}.get(d["answer"]["value"]))
                    if d.get("exclude"): ses.exclude(d["exclude"])
                    # switch off: answer from the symptom graph only; switch on again: reuse the language model's earlier reading
                    if not llm_on: ses.boost = {}
                    elif getattr(ses, "g", None) and not ses.boost: ses.boost = boost_from_ranking(ses.g)
                    if d.get("confirm"):                    # the technician confirmed the faulty part: remember the case
                        pm, _ = ses.state(); modes = sorted([(p, m) for m, p in pm.items() if CB_MODES()[m]["part"] == d["confirm"]], reverse=True)
                        CB.remember(" ".join(ses.notes), d["confirm"], CB_MODES()[modes[0][1]]["name"] if modes else "")
                        MEMORY = CB.Memory(CB.load())
                        return self._json({"session": sid, "type": "saved", "cases": len(MEMORY.cases)})
                    notes0 = ses.notes[0] if ses.notes else ""
                # arm G (the language model reading the first description with the part cards and the failure graph) runs
                # outside the lock and only once per case; the page shows the instant answer first and then the refined one
                if d.get("refine") and use_g and not ses.refined and notes0:
                    try:
                        E.USE_AGENT_PRIOR = True; g = E.agent_top3(notes0)
                        with LOCK: ses.g = g; ses.boost = boost_from_ranking(g); ses.refined = True
                    except Exception as e: print("arm G not available:", e); ses.refined = True
                with LOCK:
                    # Default: name the most likely parts at once; the technician checks them in order. Questions only on request
                    # (with a simulated technician they lowered accuracy on the held-out cases).
                    ses.want_questions = getattr(ses, "want_questions", False) or bool(d.get("ask"))
                    kind, x = ses.step() if ses.want_questions else ("diagnose", None); _, pp = ses.state()
                    if x is None: x = next(iter(pp))
                    names = {k: PART_NAME(k) for k in pp}
                    top = [{"id": k, "name": names[k], "p": round(v, 3)} for k, v in list(pp.items())[:4]]
                    # for the comparison on the page: the ranking of the symptom graph alone, and what the language model said
                    llm_used = bool(ses.boost)
                    if llm_used:
                        keep = ses.boost; ses.boost = {}; _, pp0 = ses.state(); ses.boost = keep
                    else: pp0 = pp
                    out = {"session": sid, "type": kind, "top": top, "asked": len(ses.asked), "refined": ses.refined,
                           "llm_on": llm_on, "llm_possible": llm_possible, "llm_used": llm_used,
                           "graph_only": [{"id": k, "name": names.get(k) or PART_NAME(k), "p": round(v, 3)} for k, v in list(pp0.items())[:3]],
                           "llm_top3": [{"id": k, "name": PART_NAME(k)} for k in (getattr(ses, "g", None) or [])] if llm_used else [],
                           "refine": bool(use_g and not ses.refined), "seen": [SYM[s][0] for s, c in ses.ev.items() if c > 0],
                           "similar": [{"text": c["text"], "part": PART_NAME(c["part"]), "sim": round(sim, 2)} for sim, c in ses.similar[:1]]}
                    if kind == "ask": out["question"] = {"id": x, "text": SYM[x][0], "how": SYM[x][1]}
                    else:
                        from fmea.kb_fixes import FIX
                        ex = ses.explain(x); ex["name"] = names.get(x, x); ex["fix"] = FIX.get(ex["mode_id"], []); out["diagnosis"] = ex
                        out["ranked"] = []
                        for k in list(pp)[:3]:
                            e2 = ses.explain(k); e2["name"] = names.get(k, k); e2["fix"] = FIX.get(e2["mode_id"], []); out["ranked"].append(e2)
                return self._json(out)
            if self.path == "/api/assembly/ask":      # assembly guide chat
                from assembly import qa as AQ
                return self._json(AQ.answer(d.get("message", ""), d.get("step"), use_model=(not E.STUB) and ollama_up()))
            if self.path == "/api/twin/settings":     # repair assistant: settings described in words, with range checks
                from twin.twin_control import settings_command
                return self._json(settings_command(d.get("text", ""), d.get("state") or {}, use_model=(not E.STUB) and d.get("llm", True) is not False and ollama_up()))
            if self.path == "/api/twin/match":        # which simulated scenario looks like the described problem
                ses = FMEA.get(d.get("session")); seen = {x for x, c in (ses.ev.items() if ses else []) if c > 0}
                r = match_scenario(d.get("part") or None, seen, d.get("settings") or None)
                return self._json(r or {"error": "unknown part"})
            if self.path == "/api/twin/command":     # a sentence -> checked changes on the virtual printer
                from twin.twin_control import command
                return self._json(command(d.get("text", ""), d.get("state") or {}, use_model=not E.STUB))
            if self.path == "/api/feedback":
                case = SESS.get(d.get("session"))
                if case: save(case, {"time": time.strftime("%Y-%m-%d %H:%M:%S"), **{k: v for k, v in d.items() if k != "session"}})
                return self._json({})
            self._json({"error": "unknown endpoint"})
        except Exception as e:
            self._json({"error": f"{type(e).__name__}: {e}"})
    def log_message(self, *a): pass

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8900)
    ap.add_argument("--host", default="127.0.0.1", help="0.0.0.0 inside a container (cloud hosting); keep the default on a laptop")
    ap.add_argument("--open", action="store_true", help="open the assistant in the browser when it is ready"); a = ap.parse_args()
    print("Loading the component index and failure graph ..."); E._load()
    print(f"Model: {'offline demo (rules only)' if E.STUB else E.LLM_MODEL}")
    print(f"Open http://localhost:{a.port}   (Ctrl+C to stop)")
    ThreadingHTTPServer.allow_reuse_address = False   # on Windows, True lets a second server silently share the port
    try: srv = ThreadingHTTPServer((a.host, a.port), H)
    except OSError:
        raise SystemExit(f"Port {a.port} is already used by another running server. Stop it (Ctrl+C in its window) or add --port {a.port + 1}.")
    if a.open:
        import webbrowser; threading.Timer(0.8, lambda: webbrowser.open(f"http://localhost:{a.port}")).start()
    srv.serve_forever()
