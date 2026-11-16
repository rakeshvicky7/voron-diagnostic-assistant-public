"""The whole knowledge base as one text, for strong models with a long context ("full-knowledge mode").

The evaluation arms read only the top search results within 6,000 characters (a fair, fixed budget).
A prototype chat with a strong cloud model does not need that limit: it can read every part card, every
failure-graph link and the key design facts at once, so it never misses a part because retrieval did.

KB_MODE = full     every card with all values and failure modes (~24k characters, ~6k tokens): best with Gemini
          compact  every card with function and failure modes only (~15k characters): fits Groq's free per-minute limit
          off      no knowledge text (local 7B model: too slow for long prompts)
          auto     (default) full for Gemini, compact for other cloud providers, off for local Ollama
"""
import os
from tools import card_text, compact_text
from . import engineering as eng

def mode():
    m = os.environ.get("KB_MODE", "auto").lower()
    if m != "auto": return m
    if os.environ.get("PROVIDER", "ollama") != "openai": return "off"
    return "full" if "googleapis" in os.environ.get("OPENAI_BASE_URL", "") else "compact"

_cache = {}
def knowledge(KG, graph):
    """The knowledge text for the current mode ('' when off). Built once per mode."""
    level = mode()
    if level == "off": return ""
    if level not in _cache:
        cards = "\n\n".join((card_text if level == "full" else compact_text)(v) for v in KG.values())
        edges = "\n".join(f"- {e['src']} --{e['rel']}--> {e['dst']}" for e in graph.edges)
        facts = "\n".join(f"- {k}: {v[0]} [{v[1]}]" for k, v in eng.SPEC.items())
        layer = "\n".join(f"- {k}: {v[0]} [{v[1]}]" for k, v in eng.LAYER.items())
        _cache[level] = f"""VORON 0.2 KNOWLEDGE BASE (from the design documents: assembly manual, BOM, printer config, slicer profile, documentation site)

KEY DESIGN VALUES
{facts}

SLICER PROFILE (what changes during a print)
{layer}

FAILURE GRAPH: cause --relation--> effect ("a fault in the left part can show up at the right part")
{edges}

PART CARDS (component id, name, function, design values, failure modes with symptom and check)
{cards}"""
    return _cache[level]
