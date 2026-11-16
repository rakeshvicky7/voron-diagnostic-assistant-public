# Voron 0.2 diagnostic assistant: final model

## Start it
1. Start the **Ollama** app (for the full mode). Without Ollama the assistant still works, but it is weaker.
2. Double-click **`start_assistant.bat`** in the `agent` folder. The browser opens at http://localhost:8900.
   (Same thing by hand: `py -3.12 -m src.assistant_v2.server --open` from the `agent` folder.)
3. The **Home** page opens. Choose **Assembly** or **Repair assistant**.
   If you change the code, close the black server window and start the .bat file again.

## The pages
| Page | Address | What you do there |
|---|---|---|
| Home | `/` | Guiding page with two tiles: Assembly and Repair assistant |
| Assembly | `/assembly` | All assemblies of the official CAD model are laid out on the floor. **Assemble** builds the printer in 14 steps (order of the assembly manual). Each step shows what the part does, how it connects, a tip and the manual pages. Chat on the right: "how are the belts connected to the motors?", "show me how the bed is mounted" (replays that step). Click a part to ask about it. |
| Repair assistant | `/repair` | First only a chat: describe the problem, get the parts to check in order, **This was it** gives the repair steps. **Open simulation** puts the virtual printer in the middle, the chat on the right and the sliding **Machine settings** bar on the left. |
| Old pages | `/twin`, `/classic` | The earlier all-in-one 3D page and the first chat page (kept for comparison) |

### Simulation mode, step by step
1. The assistant asks if you want to set the virtual printer like your real machine: in the settings bar, or by writing ("nozzle 240 C, belt A 90 Hz").
   A value outside the allowed range is refused with the range ("should be between 180 and 280 C"). "I don't know" continues with the design values.
2. You describe the problem. The assistant simulates the most likely scenario and asks **"Is this the same as on your machine?"**
3. **Yes / Similar**: the suspected part glows, the rest of the printer turns faint, and the assistant asks you to check it.
   **No**: describe more, see another scenario, or answer yes/no questions. A picture you already judged is not asked again.
4. **Yes, it is faulty**: repair steps (`src/fmea/kb_fixes.py`, one list for each of the 67 failure modes), then "Show the printer after the repair".
   **No, this part is fine**: the part is ruled out and the next suspect is shown.
5. If your settings alone already cause the problem (no broken part), the assistant says so and lists the values to bring back.

## What it does
1. Reads your description: finds the symptoms and Klipper error messages in it (it corrects typos and understands "not" / "looks normal").
2. Answers at once with **the parts to check, in order** (top 3). Each part shows the likely failure, why, what to check and the source.
3. With Ollama running, the language model (Qwen, the old "arm G") also reads the description and the order is refined (up to a minute).
4. **Show** replays the fault on the 3D printer. **Checked, it is fine** removes that part and updates the list.
5. **This was it** ends the case and **saves it**. The next time a similar description comes, that part is ranked first.
6. Optional: "Answer a few yes/no questions" to narrow it down.

## How it is built
| Piece | File | Job |
|---|---|---|
| Symptom graph | `src/fmea/kb_symptoms.py`, `kb_modes.py` | 31 parts, 67 failure modes, 106 symptoms with about 600 wordings, checks and sources |
| Diagnosis engine | `src/fmea/engine.py` | description -> symptoms -> failure modes -> parts; questions |
| Case memory | `src/fmea/cases.py`, `data/case_base.json`, `data/confirmed_cases.jsonl` | 82 known cases + every case you confirm |
| Language model reading | arm G (`src/agent.py`, Ollama, qwen2.5:7b-instruct) | boosts its top 3 parts (weights 5, 3, 2) |
| Pages and server | `src/assistant_v2/static/home.html`, `assembly.html`, `repair.html`, `app/` (shared 3D module, chat, style), `server.py` | works offline (three.js is in `static/vendor`) |
| Assembly guide | `data/assembly_steps.json`, `src/assembly/qa.py` | 14 steps; answers from the part graph and the manual text, the language model only rewrites them |
| Settings check | `src/twin/twin_control.py` | reads settings from a sentence and checks the allowed ranges |

## Final accuracy, 69 held-out cases (15 Nov 2026)
Test set B (30) + first forum batch C (9) + 30 new real forum cases D-G (`data/heldout_cases_batch2-5.json`, locked with checksums before any run).

| | Right part first | Within one check | Within two checks |
|---|---|---|---|
| Full mode, all 69 cases | **65 %** (45) | **81 %** (56) | **91 %** (63) |
| 95 % range | 53-75 % | | 82-96 % |
| Full mode, 30 new forum cases only | 57 % (17) | 80 % (24) | 90 % (27) |
| Symptom graph only, 30 new forum cases | 63 % (19) | 73 % (22) | 80 % (24) |

- The language model makes the shortlist better (80 % to 90 % within two checks) but the first guess slightly worse (63 % to 57 %).
- Weak spot: configuration and firmware faults are often blamed on the mechanical part that shows the symptom.
- Supported claim: in about 9 of 10 cases the faulty part is among the first three suggestions.

## Earlier measurement (39 cases, kept for reference)
39 held-out cases: 30 from the test set (R15-R30, C15-C28) and 9 new real forum cases.

| | Right part first | Within one check | Within two checks |
|---|---|---|---|
| Full mode (symptom graph + language model) | **72 %** (28 of 39) | 82 % (32) | 92 % (36) |
| Symptom graph only (no Ollama) | 56 % (22 of 39) | 74 % (29) | 77 % (30) |
| Old conversation assistant (58 test cases) | 23 % | - | 69 % (top 3) |

- With 39 cases the true first-try rate lies between about 56 % and 83 %.
- Repeat faults: when a confirmed case comes again with the same words, the right part is first in 43 of 43 development cases
  (28 of 43 without the memory). On new faults the memory changes nothing (tested with the case left out).

## What was tested and did NOT help (so it is switched off)
- Yes/no questions answered by a simulated technician (Qwen): accuracy went down (67 % -> 50 % on 30 held-out cases). They stay optional.
- Qwen reading the description into fixed fields: worse than the keyword reader (55 % vs 63 % on the development set).
- A last tuning round (best-failure-mode scoring, extra symptoms): better on the development cases, worse on the held-out cases
  (60 % vs 67 %), so the earlier, validated version is the one shipped.

## Limits
- Tested on written cases, not yet with real people at a printer.
- The three pages were checked in Chrome on the laptop (14 November): home, the full assembly run, the chat with Ollama, and the simulation
  flow with the settings bar (wrong and right values) up to "check this part". Not checked there: the final repair screen after
  "Yes, it is faulty" (it passed the automatic page test only), and the last small Python changes (they need a restart of the server).
- The language model is slow on this laptop (a refined answer can take a minute). The simulation waits at most 8 seconds for it, then starts
  with the instant answer; the 72 % figure needs the refined answer.
- The 3D view draws about 1.2 million triangles. Chrome used the Intel graphics chip here and reached about 25 to 30 pictures per second.
- The simulated scenarios are coarse: several parts give the same picture. The picture confirms the kind of fault; the part is found by checking.
- It knows the Voron 0.2 only (31 parts). Other printers are refused.
- The symptom frequencies in the graph are estimates. 56 of 67 failure modes were checked against the documents (`eval/fmea_source_audit.csv`).

## Check the numbers yourself
```
py -3.12 src\fmea\evaluate.py --g          (saved language-model answers, seconds)
py -3.12 src\fmea\evaluate.py --live-g     (language model run live, needs Ollama, about 30 minutes)
```
