"""Where the language model runs. Same prompts and tools everywhere; only the server changes.

PROVIDER=ollama (default)  local Ollama on this laptop (OLLAMA_URL, LLM_MODEL)
PROVIDER=openai            any OpenAI-compatible server, for example the free tiers of:
    Groq        OPENAI_BASE_URL=https://api.groq.com/openai/v1
    Gemini      OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
    OpenRouter  OPENAI_BASE_URL=https://openrouter.ai/api/v1
    Kaggle/Colab GPU running Ollama or vLLM behind a tunnel: OPENAI_BASE_URL=<tunnel url>/v1
  plus OPENAI_API_KEY=<your key> and LLM_MODEL=<model name of that provider>.
Embeddings for retrieval always stay on local Ollama (nomic-embed-text), so retrieval is identical across providers.

chat() returns an Ollama-style message: {"role", "content", "tool_calls": [{"id", "function": {"name", "arguments"}}]}
"""
import json, os, time, urllib.request, urllib.error
PROVIDER = os.environ.get("PROVIDER", "ollama").lower()
BASE = os.environ.get("OPENAI_BASE_URL", "").rstrip("/")
KEY = os.environ.get("OPENAI_API_KEY", "")
MIN_GAP = float(os.environ.get("MIN_SECONDS_BETWEEN_CALLS", "2.5"))   # stay under free-tier per-minute limits
_last = [0.0]

def _post(url, body, headers, timeout):
    # a normal client name: some providers (Cloudflare, "error code: 1010") block the default "Python-urllib" agent
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Accept": "application/json",
                                          "User-Agent": "voron-diagnostic-assistant/1.0", **headers})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())

def chat_openai(model, messages, tools=None, temperature=0.0, seed=42, json_mode=False, max_tokens=None, timeout=600):
    """OpenAI-compatible chat call with retries for free-tier rate limits (HTTP 429) and busy servers (5xx)."""
    msgs = []
    for m in messages:   # Ollama-style history -> OpenAI style
        m = dict(m)
        if m.get("tool_calls"):
            m["tool_calls"] = [{"id": c.get("id") or f"call_{i}", "type": "function",
                                "function": {"name": c["function"]["name"],
                                             "arguments": c["function"]["arguments"] if isinstance(c["function"]["arguments"], str)
                                             else json.dumps(c["function"]["arguments"])}} for i, c in enumerate(m["tool_calls"])]
            m["content"] = m.get("content") or ""
        if m["role"] == "tool": m.setdefault("tool_call_id", "call_0")
        msgs.append(m)
    body = {"model": model, "messages": msgs, "temperature": temperature, "seed": seed}
    if tools: body["tools"] = tools
    if json_mode: body["response_format"] = {"type": "json_object"}
    if max_tokens: body["max_tokens"] = max_tokens
    for attempt in range(8):
        wait = MIN_GAP - (time.time() - _last[0])
        if wait > 0: time.sleep(wait)
        _last[0] = time.time()
        try:
            r = _post(BASE + "/chat/completions", body, {"Authorization": f"Bearer {KEY}"}, timeout)
            msg = r["choices"][0]["message"]
            calls = [{"id": c.get("id"), "function": {"name": c["function"]["name"], "arguments": c["function"].get("arguments") or "{}"}}
                     for c in (msg.get("tool_calls") or [])]
            out = {"role": "assistant", "content": msg.get("content") or ""}
            if calls: out["tool_calls"] = calls
            return out
        except urllib.error.HTTPError as e:
            text = e.read().decode(errors="ignore")[:300]
            if e.code == 400 and ("response_format" in body or "seed" in body):   # some servers reject JSON mode or seed
                body.pop("response_format", None); body.pop("seed", None); continue
            if e.code == 413 or "too large" in text.lower() or "context" in text.lower() and "length" in text.lower():
                raise RuntimeError(f"Prompt too long for this model or plan: {text}") from None
            if e.code in (429, 500, 502, 503, 504):
                pause = min(120, 10 * 2 ** attempt); print(f"  model server busy or rate limit ({e.code}); waiting {pause} s"); time.sleep(pause); continue
            raise RuntimeError(f"Model server error {e.code}: {text}") from None
        except (urllib.error.URLError, TimeoutError) as e:
            pause = min(120, 10 * 2 ** attempt); print(f"  connection problem ({e}); waiting {pause} s"); time.sleep(pause)
    raise RuntimeError("Model server did not answer after several retries (daily free limit reached?)")
