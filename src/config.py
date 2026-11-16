"""All settings that are held constant across arms A-E."""
import os
OLLAMA_URL   = os.environ.get("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL    = os.environ.get("LLM_MODEL", "qwen2.5:7b-instruct")   # fall back to qwen2.5:3b-instruct on small GPUs
EMBED_MODEL  = os.environ.get("EMBED_MODEL", "nomic-embed-text")
TEMPERATURE  = 0.0
SEED         = 42
TOP_K        = 5            # results per search call
CHAR_BUDGET  = 6000         # max characters returned by any one tool call (same for text and graph)
MAX_STEPS    = 3            # extra tool calls the agent may make after the first mandatory retrieval
RRF_K        = 60           # reciprocal rank fusion constant
STUB         = os.environ.get("STUB") == "1"   # offline test mode: fake LLM and embeddings
EMBED_STUB   = STUB or os.environ.get("EMBED_STUB") == "1"   # cloud hosting without Ollama: hashed word vectors for search, real LLM via PROVIDER=openai
NUM_GPU      = int(os.environ["NUM_GPU"]) if os.environ.get("NUM_GPU") else None   # GPU layers; unset = Ollama decides
