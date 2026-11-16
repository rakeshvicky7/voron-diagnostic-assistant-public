# Graph version (arm G): what it is and what was checked

## The idea (from the supervisor)

All parts of the machine are connected in a graph. Each edge says "a fault in this part can show up at that part". When a symptom appears at one part, the agent walks back along the edges to find the part that is really at fault, and in particular a part that explains several symptoms at once.

## How it works

1. **Graph** (`src/build_graph.py` → `data/graph/graph.json`, `graph_edges.csv`)
   - 28 nodes. These are the same 28 components as the cards, so the answer list does not change.
   - 56 directed cause → effect edges:
     - 10 come automatically from the board pins in the printer config (the board drives or reads a part);
     - 13 come automatically from the config values (the config sets values for a part);
     - 33 were typed by hand from the assembly manual and the documentation site. Each one has its source.
   - Nothing in the graph comes from the test cases.
2. **Seed search.** The same hybrid search as arm C finds the 5 cards that best match the symptom. These are the parts where the symptom may appear.
3. **Upstream walk.** Every part that can reach a seed within 2 steps is a possible cause. Edges of the types "configures" and "triggers" are not walked any further, because a fault does not travel through the configuration to every other part.
4. **Ranking.** Score = sum over the seeds the candidate explains of (seed match × 0.5 for each extra step), divided by the number of parts the candidate can affect in total.
   - Candidates that explain 2 or more seeds (a shared cause) come first.
   - Dividing by the number of parts a candidate can affect stops very general parts, such as the power supply or the config, from winning every time.
   - The top 3 are shown.
5. **Evidence.** The model receives the seed cards plus the 3 upstream candidates with their paths. The budget is the same 6,000 characters as for every other arm, and 2,000 of them are kept for the graph part. The model, prompt, settings and answer format are the same as in arms A–E. The graph does not answer on its own; the model decides.

## Requirements checklist

| # | Requirement | Status |
|---|---|---|
| 1 | Parts are connected by cause → effect edges taken from the design documents only | Done (56 edges, each with a source) |
| 2 | From one part's symptom, the agent can find an upstream part at fault | Done (upstream walk + paths in the evidence) |
| 3 | A shared cause behind several symptoms is ranked first | Done (rule fixed before testing) |
| 4 | General parts (config, power supply) do not win by default | Done (score divided by spread; no walking through settings) |
| 5 | Same model, prompt, budget and answer list as the other arms (fair comparison) | Done |
| 6 | Runs on all 58 test cases without errors | Done in offline test mode (58/58). The real run is tonight |
| 7 | The graph evidence used for each case is saved in the results | Done (`graph` field in `results_raw.jsonl`) |
| 8 | A chat window to try the agent by hand, with top 3, check, value, source, graph paths and feedback | Done (`src/chat_ui.py`) |
| 9 | Design rules fixed by principle, not tuned on the test cases | Done. The checks used invented symptoms (fan + thermistor on head move, layer shift, under-extrusion, bed temperature), not the test cases |
| 10 | You check every hand-made edge against its source | **To do**: open `data/graph/graph_edges.csv` and put Y or N in the last column |

## What I saw in the offline check (fake model, fake embeddings; only shows the pipeline works)

- "Hotend fan stops and the temperature jumps when the head moves": the toolhead cable (umbilical_wiring) is the first upstream cause, explaining 3 of the seeds.
- "Layer shift": XY pulleys/idlers come first (they explain toolhead + belts).
- Before the fix, the power supply, the host computer and the filament runout sensor came first because they connect to everything through the config. The two rules in step 3 and step 4 removed this.

## Known limits (to write in the thesis)

- If the seed search misses the part where the symptom appears, the walk starts in the wrong place.
- There are no "can be caused by" edges for material or slicer problems beyond the few typed by hand.
- 2 steps upstream is a fixed choice. Longer chains, such as power supply → board → cable → fan, are cut off. This is on purpose, so that hubs do not take over.
