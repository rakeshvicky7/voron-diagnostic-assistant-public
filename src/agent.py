"""Single diagnostic agent. Same prompt, model and loop for all arms; only the tools' knowledge differs.
Usage (interactive):  python src/agent.py --arm E
"""
import json, re, sys, argparse, urllib.request, urllib.error, runpy, pathlib
from config import OLLAMA_URL, LLM_MODEL, TEMPERATURE, SEED, MAX_STEPS, STUB, NUM_GPU
from tools import Toolbox
A = pathlib.Path(__file__).resolve().parents[1]
COMP = runpy.run_path(str(A / "data/kg/components.yaml.py"))["COMPONENTS"]
VOCAB = "\n".join(f"- {k}: {v['name']}" for k, v in COMP.items())

SYSTEM = f"""You are a maintenance assistant for a Voron 0.2r1 3D printer. A technician describes a symptom.
Find the most likely faulty component(s). Use the tools when available; base your answer on retrieved evidence and cite it.
Answer ONLY with JSON in this form:
{{"candidates": [{{"component_id": "<id from list>", "reason": "...", "check": "how to confirm", "correct_value": "spec or setting if known", "source": "document/line or 'none'"}}]}}
Give 1 to 3 candidates, most likely first. If the evidence is insufficient, still give your best ranked guess.
Component ids you must choose from:
{VOCAB}"""

# ---------------------------------------------------------------- prompt variants (experiment, 23 Nov 2026)
# PROMPT=plain (default): the prompt used for every thesis run (arms A-G). Unchanged.
# PROMPT=reason        : the same task, but the model must reason step by step before ranking (general method only).
# PROMPT=reason_traps  : as 'reason' plus two diagnostic traps (shared upstream cause; configuration before hardware).
#                        These two come from the error analysis, which also looked at held-out cases: report that.
import os
PROMPT = os.environ.get("PROMPT", "plain").lower()

_STEPS = """How to work, in this order:
1. Read the evidence from your tools first. Component cards give each part's failure modes, symptoms and checks.
   "POSSIBLE UPSTREAM CAUSES" (when present) lists parts whose fault can travel to the parts above.
2. SYMPTOMS: list each separate observation in the description (what happens, when, since when, what changed, error messages).
3. CANDIDATES: for each symptom, name the components whose failure modes in the evidence produce it.
4. TEST: for your 3 to 5 best candidates, say which symptoms each one explains and which it does NOT explain or contradicts.
{traps}{rank}. RANK: first = the component that explains the most symptoms, contradicts none, and is supported by the evidence.
   A part the technician already replaced or checked without any change goes down.
If the evidence does not cover the symptoms, search again with a different query before answering."""

_TRAPS = """5. Before ranking, check two common traps:
   - Several different functions fail together (for example heating AND a fan AND a motor): the cause is often the part
     they share (cable or wiring, power supply, controller board), not each part separately.
   - The fault started at build time, after a configuration/firmware/slicer change, or the symptom is a wrong direction,
     wrong distance or wrong temperature behaviour: suspect configuration or settings before mechanical parts.
"""

SYSTEM_REASON = f"""You are an expert maintenance technician for a Voron 0.2r1 3D printer. A technician describes a fault
in their own words. Find the faulty component like a careful mechanic: weigh the evidence before deciding.

{{steps}}

Answer in exactly this form:
REASONING: <at most 120 words, following the steps>
ANSWER: {{"candidates": [{{"component_id": "<id from list>", "reason": "...", "check": "how to confirm", "correct_value": "spec or setting if known", "source": "document/line or 'none'"}}]}}
Give 1 to 3 candidates, most likely first. component_id must be copied exactly from this list:
{VOCAB}"""

if PROMPT == "reason":
    SYSTEM = SYSTEM_REASON.replace("{steps}", _STEPS.format(traps="", rank="5"))
elif PROMPT == "reason_traps":
    SYSTEM = SYSTEM_REASON.replace("{steps}", _STEPS.format(traps=_TRAPS, rank="6"))

def chat(messages, tools):
    if STUB:   # offline test: pick ids that appear in the retrieved text, in order of appearance
        ctx = " ".join(m.get("content", "") for m in messages if m["role"] != "system")
        ids = [k for k in sorted(COMP, key=lambda k: ctx.find(k) if k in ctx else 10**9) if k in ctx][:3] or ["controller_board"]
        return {"role": "assistant", "content": json.dumps({"candidates": [{"component_id": i, "reason": "stub", "check": "", "correct_value": "", "source": "stub"} for i in ids]})}
    from provider import PROVIDER, chat_openai
    if PROVIDER == "openai":   # free cloud model (Groq, Gemini, OpenRouter, Kaggle ...): same prompt, tools and settings
        return chat_openai(LLM_MODEL, messages, tools, TEMPERATURE, SEED)
    body = {"model": LLM_MODEL, "messages": messages, "stream": False, "keep_alive": "60m", "options": {"temperature": TEMPERATURE, "seed": SEED, "num_ctx": 8192}}
    if NUM_GPU is not None: body["options"]["num_gpu"] = NUM_GPU   # layers on the GPU; lower it if the GPU runs out of memory
    if tools: body["tools"] = tools
    req = urllib.request.Request(OLLAMA_URL + "/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=1800).read())["message"]
    except urllib.error.HTTPError as e:   # show Ollama's own error text (e.g. out of memory), not just "500"
        raise RuntimeError(f"Ollama error {e.code}: {e.read().decode(errors='ignore')[:300]}") from None

def parse(text):
    if PROMPT != "plain" and text and "ANSWER:" in text: text = text.split("ANSWER:")[-1]   # skip the reasoning part
    m = re.search(r"\{.*\}", text or "", re.S)
    try: c = json.loads(m.group(0))["candidates"] if m else []
    except Exception: c = []
    return [x for x in c if isinstance(x, dict) and x.get("component_id") in COMP][:3]

def diagnose(symptom, arm, toolbox=None, technician=None):
    tb = toolbox or Toolbox(arm); trace = []; tb.last_graph = None
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": f"Symptom: {symptom}"}]
    if arm != "A":
        ev = tb.first_retrieval(symptom); trace.append({"tool": "first_retrieval", "chars": len(ev)})
        msgs.append({"role": "user", "content": "Evidence from your tools:\n" + ev})
    tools = tb.specs() if arm != "A" else None
    for _ in range(MAX_STEPS + 1):
        msg = chat(msgs, tools); msgs.append(msg)
        calls = msg.get("tool_calls") or []
        if not calls: break
        for c in calls:
            fn = c["function"]["name"]; args = c["function"].get("arguments") or {}
            if isinstance(args, str): args = json.loads(args or "{}")
            res = tb.call(fn, args, technician); trace.append({"tool": fn, "args": args, "chars": len(res)})
            msgs.append({"role": "tool", "content": res, "tool_call_id": c.get("id") or "call_0"})
    else:
        msgs.append({"role": "user", "content": "Give your final JSON answer now."}); msgs.append(chat(msgs, None))
    cands = parse(msgs[-1].get("content", ""))
    if not cands:   # same rule for every arm: one correction turn if no valid component id was given
        trace.append({"tool": "format_retry"})
        msgs.append({"role": "user", "content": "Your answer did not contain valid component ids. Answer again with JSON only, using component_id values exactly from the list."})
        msgs.append(chat(msgs, None)); cands = parse(msgs[-1].get("content", ""))
    return {"candidates": cands, "raw": msgs[-1].get("content", ""), "trace": trace, "graph": tb.last_graph}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--arm", default="E"); a = ap.parse_args()
    tb = Toolbox(a.arm); ask = lambda q: input(f"\nAgent asks: {q}\nYour answer: ")
    while True:
        s = input("\nDescribe the symptom (empty to quit): ").strip()
        if not s: break
        r = diagnose(s, a.arm, tb, ask)
        for i, c in enumerate(r["candidates"], 1):
            print(f"{i}. {COMP[c['component_id']]['name']}\n   why: {c.get('reason')}\n   check: {c.get('check')}\n   correct value: {c.get('correct_value')}\n   source: {c.get('source')}")
