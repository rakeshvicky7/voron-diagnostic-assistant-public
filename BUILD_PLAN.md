# Voron 0.2 diagnostic agent — build plan

One agent, five knowledge versions. Everything except the knowledge stays fixed.

| Arm | Knowledge behind the tools |
|---|---|
| A | none (LLM only) |
| B | Voron manual + docs as text chunks (hybrid BM25 + dense search, RRF) |
| C | structured model (data/kg) built from config, BOM and manual |
| D | generic troubleshooting guide as text chunks |
| E | C + D |

## Fixed for all arms
- same LLM (local via Ollama, qwen2.5:7b-instruct), temperature 0, seed 42
- same embedding model (nomic-embed-text), top-k 5, 6,000-character tool budget
- same prompt and the same three tools: `graph_query`, `text_search`, `ask_technician`
- answer format: ranked list of suspect components, a check for each, correct value, cited source

## Folders
- `src/extract_config.py` — builds the automatic part of the graph (done: 137 parameters, 31 pin connections, 79 components)
- `data/kg/` — schema, automatic JSON files, and two hand-filled CSVs (`manual_relations.csv`, `failure_modes.csv`)
- `data/indexes/` — chunk indexes for arms B and D (to be built)
- `eval/` — runner and scoring (to be built); test cases live in `../evaluation/Test_Set_v1.xlsx`

## Status
1. Automatic graph from config — `src/extract_config.py` (done)
2. Structured model: 28 component cards with functions, correct values, pins, links and template-derived failure modes — `src/build_kg.py` (done)
3. Text chunks for arms B (976 chunks) and D (419 chunks), same chunking rule — `src/build_chunks.py` (done)
4. Agent with hybrid search (BM25 + embeddings + RRF) and three tools — `src/agent.py`, `src/tools.py`, `src/retrieval.py` (done, tested offline)
5. Evaluation runner with top-1/top-3 accuracy and Wilson 95% CIs — `src/run_eval.py` (done, tested offline)
6. **Next: run on the laptop** — see `SETUP_WINDOWS.md`

## Design notes for the method chapter
- Every arm gets the same answer space (the 28 component ids), the same prompt, the same model and temperature 0.
- Every arm with knowledge does one mandatory retrieval with the symptom text, then may make up to 3 more tool calls.
- Tool output is capped at 6,000 characters; in arm E the cap is split between graph and text so E does not get more evidence.
- Failure modes in the graph come from a fixed template per component class (heater, sensor, motor, fan, ...), not from the test cases.
- `ask_technician` returns "no further information" in batch evaluation; it is interactive in `agent.py`.

## Useful documentation to add
- Klipper Config Reference (explains every setting): https://www.klipper3d.org/Config_Reference.html
  (source: https://github.com/Klipper3d/klipper/blob/master/docs/Config_Reference.md, GPLv3)
