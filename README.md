# Voron 0.2 diagnostic assistant

A document-grounded assistant that helps a technician find the faulty part of a Voron 0.2r1 3D printer from a description in plain words, and guides the repair. Built for an M.Sc. thesis. Runs fully offline on a Windows laptop.

## What it does

- **Repair assistant:** the user describes the problem; the assistant ranks the parts to check, says what to check and why, and gives repair steps. A simulation mode replays the fault on a virtual printer (official Voron CAD in 3D) so the user can compare it with the real machine.
- **Assembly guide:** all assemblies of the CAD model are laid out and assembled step by step (order of the official manual), with a chat that explains how parts work and connect.
- **Learns from use:** a part confirmed as faulty is saved and recognised faster next time.

## How it works

| Piece | Folder | Job |
|---|---|---|
| Symptom graph (FMEA) | `src/fmea/` | 31 parts, 67 failure modes, 106 symptoms with about 600 wordings, checks, repair steps and sources |
| Diagnosis engine | `src/fmea/engine.py` | description -> symptoms -> failure modes -> ranked parts; optional yes/no questions |
| Language model reading | `src/agent.py` (Ollama, qwen2.5:7b-instruct) | re-ranks the suspects ("arm G", graph RAG) |
| Virtual printer | `src/twin/` | simulates the effect of each fault and of machine settings |
| Assembly guide | `src/assembly/`, `data/assembly_steps.json` | 14 assembly steps and part questions |
| Pages and server | `src/assistant_v2/` | Home, Assembly, Repair pages; three.js is bundled in `static/vendor` |

## Run it (Windows)

1. Install Python 3.12 and the packages: `py -3.12 -m pip install -r requirements.txt`
2. Optional, for full mode: install [Ollama](https://ollama.com), then `ollama pull qwen2.5:7b-instruct` and `ollama pull nomic-embed-text`
3. Double-click `start_assistant.bat`. The browser opens at http://localhost:8900

Without Ollama the assistant still works (symptom graph only). Details: `SETUP_WINDOWS.md`.

## Results (69 held-out cases, never used for building or tuning)

| | Right part first | Within one check | Within two checks |
|---|---|---|---|
| Full mode | 65 % (45) | 81 % (56) | 91 % (63) |

30 of these are real, solved forum cases collected after the model was finished (`data/heldout_cases_batch2-5.json`, each with its source link and a checksum `.lock` file). Full breakdown and limits: `FINAL_MODEL.md`.

Check the numbers: `py -3.12 src\fmea\evaluate.py --g` (saved language-model answers) or `--live-g` (live, needs Ollama).

## Third-party material

- Voron 0.2r1 CAD model, assembly manual and documentation: [VoronDesign](https://github.com/VoronDesign), GPLv3. The STEP file is not stored here; `tools/cad/convert_step.py` converts it to `static/cad/voron02r1.glb`.
- three.js 0.160.0 (MIT) in `src/assistant_v2/static/vendor/`.
- Experiment arms D and E also used a third-party 3D-printing troubleshooting guide (`data/indexes/chunks_D.jsonl`). It is not included in the public version, and the saved D/E answers that quoted it are blanked (their scores are kept). The final model does not use it; only re-running arms D and E needs it.
- The held-out cases in `data/heldout_cases*.json` are short summaries of public forum threads, each with its source link.

## Knowledge graph as a spreadsheet

`Voron_FMEA_Knowledge_Graph.xlsx` contains all data of the symptom graph (parts, settings, failure modes, symptoms, wordings, links with probabilities, repair steps, part links, source audit). It is rebuilt from the code with `py -3.12 tools_build_kg_excel.py`.

## Other documents

`FINAL_MODEL.md` (final model and results), `SETUP_WINDOWS.md` (step-by-step setup), `BUILD_PLAN.md` (original experiment plan, arms A to E), `GRAPH_VERSION_CHECKLIST.md`.
