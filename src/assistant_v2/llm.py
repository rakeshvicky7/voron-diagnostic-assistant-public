"""One helper to ask the local model for JSON (Ollama 'format: json' keeps a 7B model to valid JSON)."""
import json, re, sys, pathlib, urllib.request
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from config import OLLAMA_URL, LLM_MODEL, NUM_GPU, STUB, SEED   # noqa: E402

def ask_json(system, user, timeout=900, max_tokens=400, ctx=4096):
    """Returns a dict, or {} if the model did not give valid JSON. Never called in STUB mode."""
    if STUB: return {}
    from provider import PROVIDER, chat_openai
    if PROVIDER == "openai":
        txt = chat_openai(LLM_MODEL, [{"role": "system", "content": system}, {"role": "user", "content": user}],
                          None, 0.0, SEED, json_mode=True, max_tokens=max_tokens, timeout=timeout)["content"]
        try: return json.loads(txt)
        except Exception:
            m = re.search(r"\{.*\}", txt or "", re.S)
            try: return json.loads(m.group(0)) if m else {}
            except Exception: return {}
    body = {"model": LLM_MODEL, "stream": False, "format": "json", "keep_alive": "60m",
            "options": {"temperature": 0, "seed": SEED, "num_ctx": ctx, "num_predict": max_tokens},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if NUM_GPU is not None: body["options"]["num_gpu"] = NUM_GPU
    req = urllib.request.Request(OLLAMA_URL + "/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        txt = json.loads(urllib.request.urlopen(req, timeout=timeout).read())["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"Could not reach the local model ({type(e).__name__}: {e}). Is Ollama running?") from None
    try: return json.loads(txt)
    except Exception:
        m = re.search(r"\{.*\}", txt or "", re.S)
        try: return json.loads(m.group(0)) if m else {}
        except Exception: return {}


def ask_local(model, system, user, max_tokens=400, timeout=600):
    """Always local Ollama (the fine-tuned model), JSON mode."""
    if STUB: return {}
    body = {"model": model, "stream": False, "format": "json", "keep_alive": "60m",
            "options": {"temperature": 0, "seed": SEED, "num_ctx": 4096, "num_predict": max_tokens},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if NUM_GPU is not None: body["options"]["num_gpu"] = NUM_GPU
    req = urllib.request.Request(OLLAMA_URL + "/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    txt = json.loads(urllib.request.urlopen(req, timeout=timeout).read())["message"]["content"]
    try: return json.loads(txt)
    except Exception:
        m = re.search(r"\{.*\}", txt or "", re.S)
        try: return json.loads(m.group(0)) if m else {}
        except Exception: return {}
