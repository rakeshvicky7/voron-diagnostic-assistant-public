# Running the agent on your laptop (Windows)

Everything runs locally with free models through **Ollama**. No internet is needed after the models are downloaded.

## Step 1 — Check your graphics card (2 min)

1. Press **Ctrl + Shift + Esc** to open Task Manager.
2. Click **Performance** on the left, then click **GPU** (choose the NVIDIA one if there are two).
3. Note two things: the **GPU name** (top right, e.g. "NVIDIA GeForce RTX 4060 Laptop GPU") and **Dedicated GPU memory** (e.g. 8.0 GB).

| Dedicated GPU memory | Model to use |
|---|---|
| 8 GB or more | `qwen2.5:7b-instruct` (default) |
| 4–6 GB | `qwen2.5:3b-instruct` |

## Step 2 — Install Ollama (5 min)

1. Download the Windows installer from https://ollama.com/download/windows and run it.
2. Open **PowerShell** (Start menu → type PowerShell → Enter) and type:

```
ollama pull qwen2.5:7b-instruct
ollama pull nomic-embed-text
```

(Use `qwen2.5:3b-instruct` instead of the 7b model if your GPU has less than 8 GB.) The downloads are about 5 GB and 0.3 GB.

3. Test it: `ollama run qwen2.5:7b-instruct "Say hello"` — you should get an answer. Type `/bye` to exit.

## Step 3 — Install the Python packages (2 min)

Python 3.12 is already installed on your laptop. In PowerShell:

```
cd "C:\Users\rakes\Downloads\rag dataset\agent"
py -3.12 -m pip install -r requirements.txt
```

## Step 4 — Try the agent yourself (5 min)

```
py -3.12 src\agent.py --arm E
```

The first start takes a few minutes because it builds the search indexes once (they are saved for next time). Then type a symptom, for example:
`The first layer does not stick anywhere on the bed`

If you use the 3b model, first type this in the same PowerShell window: `$env:LLM_MODEL="qwen2.5:3b-instruct"`

## Step 5 — Run the full experiment (1–3 hours, runs by itself)

```
py -3.12 src\run_eval.py --arms A B C D E
```

- It runs all 42 test cases on all 5 versions (210 runs) and prints `top1`, `top3` or `miss` for each.
- You can stop it any time (Ctrl + C) and start the same command again — it continues where it stopped.
- Keep the laptop plugged in.

## Step 6 — Send me the results

Send these two files from `agent\eval\`:
- `summary.csv` — accuracy per version with 95% confidence intervals
- `results_raw.jsonl` — every answer, for analysis

Note: `results_raw_stub.jsonl` and `summary_stub.csv` are from my offline test with a fake model. They test the code only and are **not results**.

## Step 7 — Second and third model (comparison of open-source models)

Each extra model saves to its own files (`results_raw_<model>.jsonl`, `summary_<model>.csv`), so the Qwen results are never touched. Run one model at a time, laptop plugged in.

```
cd "C:\Users\rakes\Downloads\rag dataset\agent"
ollama pull llama3.1:8b
$env:LLM_MODEL="llama3.1:8b"
py -3.12 src\run_eval.py --arms A B C C2 D
```

When it has finished (several hours), do the same for Mistral in a **new** PowerShell window:

```
ollama pull mistral:7b
$env:LLM_MODEL="mistral:7b"
py -3.12 src\run_eval.py --arms A B C C2 D
```

If you get `CUDA error: out of memory`, put fewer layers on the GPU before running: `$env:NUM_GPU="18"` (try `"12"` if it still fails). The rest runs on the CPU; slower, same results.

Arm E is left out: it added nothing for Qwen, and leaving it out saves about an hour per model. If a run stops, type the same three lines again; it continues where it stopped.

## Step 8 — Arm B+ (fairness check: documents plus machine files as text)

Arm BP = arm B plus the firmware configuration, BOM and slicer profiles as plain text (1,019 passages). It is run with the main model (Qwen), so open a **new** PowerShell window (no model setting) and make sure Ollama is running:

```
cd "C:\Users\rakes\Downloads\rag dataset\agent"
py -3.12 src\run_eval.py --arms BP
```

The first start embeds the 1,019 passages once (a few minutes). Results are added to `results_raw.jsonl` and `summary.csv`.

## Step 9 — The 16 new real cases (Test Set v2)

The test set now has 58 cases (16 new real owner reports, R15–R30). The runner reads `Test_Set_v2.xlsx` automatically and skips every case it has already done, so only the new cases run. Open a **new** PowerShell window (no model setting), make sure Ollama is running, then:

```
cd "C:\Users\rakes\Downloads\rag dataset\agent"
py -3.12 src\run_eval.py --arms A B BP C C2 D E
```

That is 16 cases × 7 arms = 112 runs (about 2–4 hours). If it stops, type the same line again.

Optional, afterwards (same new cases for the other two models):

```
$env:NUM_GPU="18"
$env:LLM_MODEL="llama3.1:8b"
py -3.12 src\run_eval.py --arms A B C C2 D
$env:LLM_MODEL="mistral:7b"
py -3.12 src\run_eval.py --arms A B C C2 D
```

## Step 10 — The graph version (arm G) and the chat window

**10a. Try it yourself in the chat window (10 min).** Open a **new** PowerShell window, make sure Ollama is running, then:

```
cd "C:\Users\rakes\Downloads\rag dataset\agent"
py -3.12 src\build_graph.py
py -3.12 src\chat_ui.py
```

The first line rebuilds the graph (it should print `28 nodes, 56 edges`). The second line starts the chat; open **http://localhost:8765** in your browser.

- Type a symptom in your own words and press Enter. One answer takes about 30 s to 2 min.
- Under the answer, click **Graph evidence** to see where the symptom may appear and which upstream parts could cause it, with the path (for example `umbilical_wiring --carries_power_to--> hotend_fan`).
- Click **Correct (1st)**, **In top 3** or **Wrong** and pick the right part. This is saved in `eval\chat_feedback.jsonl`.
- The arm list at the top lets you compare the same symptom with arm C or E.
- Please do **not** type the test cases from the Excel file here, so the overnight test stays clean. Use your own new symptoms.
- Stop the chat with Ctrl+C before you start 10b (both need the GPU).

**10b. Overnight run (58 cases, about 2–4 hours).** In the same window:

```
py -3.12 src\run_eval.py --arms G
```

If it stops, type the same line again; it continues where it stopped. In the morning, send me `eval\results_raw.jsonl` and `eval\summary.csv`.

Optional on the next night (graph version on the other two models):

```
$env:NUM_GPU="18"
$env:LLM_MODEL="llama3.1:8b"
py -3.12 src\run_eval.py --arms G
$env:LLM_MODEL="mistral:7b"
py -3.12 src\run_eval.py --arms G
```

## Step 12 — Diagnostic chat v2 (the main feature, built step by step)

This is a clean chat that asks for the information it needs, checks your numbers with exact calculations, and names the faulty part. It does not give repair steps yet. With Ollama running:

```
cd "C:\Users\rakes\Downloads\rag dataset\agent"
py -3.12 src\assistant_v2\server.py
```

Open **http://localhost:8900**. In VS Code you can instead pick **"A. Diagnostic chat v2"** and press F5.

To check its behaviour on fixed test conversations (vague, detailed, invalid, off-topic, other printer, impossible numbers):

```
py -3.12 src\assistant_v2\test_scenarios.py > eval\v2_scenarios.txt
```

Send me `eval\v2_scenarios.txt` and a few of your own chats from `eval\assistant_v2_sessions\`.

## Step 13 — Overnight test (graph arm G + chat assistant on all 58 cases)

Before you start: plug in the laptop, set sleep to "Never" (Settings → System → Power), close other programs, and start the Ollama app. Then, in one PowerShell window:

```
cd "C:\Users\rakes\Downloads\rag dataset\agent"
py -3.12 src\run_eval.py --arms G ; py -3.12 src\assistant_v2\eval_dialogue.py
```

The first command tests the graph version (arm G) on the 58 cases, about 2–4 hours. The second tests the chat assistant on the same 58 cases with a simulated technician, about 2–3 hours. If either one stops, type the same line again; both continue where they stopped.

In the morning, send me:
- `eval\results_raw.jsonl` and `eval\summary.csv` (arm G)
- `eval\dialogue_results.jsonl` and `eval\dialogue_summary.csv` (chat assistant)

## Step 14 — A much bigger model for free (Groq free tier)

The code can now send the same prompts to a free cloud model instead of the local 7B. Retrieval stays on your laptop, so keep Ollama running.

1. Go to console.groq.com, sign up (free) and create an API key. Copy it.
2. Open a **new** PowerShell window and run:

```
cd "C:\Users\rakes\Downloads\rag dataset\agent"
$env:PROVIDER="openai"
$env:OPENAI_BASE_URL="https://api.groq.com/openai/v1"
$env:OPENAI_API_KEY="paste-your-key-here"
$env:LLM_MODEL="openai/gpt-oss-120b"
py -3.12 src\run_eval.py --arms A C G
```

If Groq says the model name is unknown, look up the current model list in the Groq console and change `LLM_MODEL`. Results are saved in their own files (`results_raw_openai-gpt-oss-120b.jsonl`), so they never mix with the 7B results. The free tier has a daily limit; if it stops with "limit reached", run the same line again the next day and it continues where it stopped.

The chat assistant uses the same settings: set the four lines above, then start `py -3.12 src\assistant_v2\server.py`.

## Step 15 — Full-knowledge mode with Gemini (free)

With a cloud model, the chat now reads ALL part cards, the whole failure graph and the key design values in every step (not only the top search results). Gemini's free tier allows much longer prompts than Groq, so it can read the full cards.

1. Go to aistudio.google.com, sign in with Google, click **Get API key** → **Create API key**, copy it.
2. In AI Studio, look at the model list and note a **Flash** model name (for example `gemini-2.5-flash`).
3. New PowerShell window (Ollama running):

```
cd "C:\Users\rakes\Downloads\rag dataset\agent"
$env:PROVIDER="openai"
$env:OPENAI_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
$env:OPENAI_API_KEY="your-gemini-key"
$env:LLM_MODEL="gemini-2.5-flash"
py -3.12 src\assistant_v2\server.py
```

Note: Google uses free-tier prompts to improve its products; the Voron documents are public, so this is fine for the prototype. With Groq the chat uses a shorter version of the cards (Groq's free per-minute limit). `$env:KB_MODE="full"` / `"compact"` / `"off"` overrides this.

## Step 16 — Fine-tune your own model (free GPU), then use it offline

**A. Training data** (laptop, Ollama running, ~20 min): `py -3.12 src\finetune\gen_training.py` → `data\finetune\train.jsonl`, `val.jsonl`.

**B. Train on Kaggle (free, ~1–3 h):**
1. kaggle.com → sign up → verify your phone (Settings → Phone verification; needed for GPU and internet).
2. *Datasets* → *New Dataset* → upload `train.jsonl` and `val.jsonl` → name it `voron-finetune` → Create.
3. *Code* → *New Notebook* → *File* → *Import Notebook* → choose `agent\finetune\voron_finetune.ipynb`.
4. Right panel: *Accelerator* = **GPU T4 x2** (or P100), *Internet* = **On**; *Add Input* → your `voron-finetune` dataset.
5. *Run All*. Keep the tab open. The check cell prints how often the model gets held-out faults right.
6. When done: right panel → *Output* → download the `.gguf` file (~4.7 GB) into `agent\finetune\`.

**C. Load it into Ollama** (laptop):
```
cd "C:\Users\rakes\Downloads\rag dataset\agent\finetune"
ollama create voron-qwen -f Modelfile
```
(If the downloaded file has another name, change the `FROM` line in `Modelfile` first.)

**D. Use it in the chat** (offline, no limits):
```
cd "C:\Users\rakes\Downloads\rag dataset\agent"
$env:FT_MODEL="voron-qwen"
py -3.12 src\assistant_v2\server.py
```
Overnight test of the fine-tuned version: same `$env:FT_MODEL` line, then `py -3.12 src\assistant_v2\eval_dialogue.py --name ft1`.

## Step 17 — The virtual printer (simulation of the whole Voron 0.2)

No model and no internet needed. From the `agent` folder:

1. See every fault once: `py -3.12 src\twin\virtual_printer.py` (or one part: `py -3.12 src\twin\virtual_printer.py xy_belts`)
2. Check the simulation against the documents: `py -3.12 src\twin\validate_twin.py` → `eval\twin_validation.md`
3. Let the assistant question the virtual printer (31 parts × 5 faults, about 10 seconds):
   `py -3.12 src\twin\eval_twin.py --runs 5` → `eval\twin_dialogue_summary.md`
   With a technician who can't answer 15 % of the questions: add `--dont-know 0.15`
4. Training data v3 (simulated answers for all 31 parts; Ollama must run): `py -3.12 src\finetune\gen_training.py`
   (`--twin heat` makes the old v2 data again)

## Step 18 — The 3D virtual printer with the assistant

1. Start the assistant as usual (Ollama running): `py -3.12 -m src.assistant_v2.server`
   (demo without Ollama: `$env:STUB="1"; py -3.12 -m src.assistant_v2.server`)
2. Open **http://localhost:8900/twin** in Chrome or Edge (the 3D library loads from the internet the first time).
3. Rotate with the left mouse button, zoom with the wheel, pan with the right button. Click a part to see its card.
4. Left panel: pick a faulty part and severity, press **Run the print** and watch the result.
   Or type into **Tell the virtual printer**, e.g. `belt A 70 Hz`, `nozzle 210 C`, `make the hotend fan fail`, `reset`.
5. Right panel, **Assistant** tab: describe your problem. Answer the questions; press **Show** next to a suspect to see it on
   the virtual printer and tick what matches your printer. At the end the faulty part glows yellow: check it, then press
   **It was this part** or **This part is fine** (the assistant then continues with the next suspect).

## Step 19 — The official Voron CAD in the 3D page (once)

1. The file `tools\cad\V0.2R1_Master_Assembly_STEP.zip` (official Voron 0.2r1 assembly from the Voron GitHub) must be there.
2. From the `agent` folder:
   ```
   py -3.12 -m pip install cadquery-ocp
   py -3.12 tools\cad\convert_step.py tools\cad\V0.2R1_Master_Assembly_STEP.zip
   ```
   It takes a few minutes and writes `src\assistant_v2\static\cad\voron02r1.glb` and `names.json`.
   If it runs out of memory, make the mesh coarser: add `1.0 1.0` at the end of the second command.
3. Restart the assistant, open http://localhost:8900/twin and tick **Official Voron CAD model**.

## Step 11 — The Repair Assistant (voice + pictures) — on hold; we come back to it after v2

This is the advanced front end. It uses the same tested agent (arm G), and adds:

- questions until the picture is clear;
- a printer drawing that shows where the symptom is (orange) and the likely cause (red);
- a cause map;
- repair steps with the manual page opened at the right page;
- voice and photos.

**11a. Start it (works right away, no new installs).** With Ollama running:

```
cd "C:\Users\rakes\Downloads\rag dataset\agent"
py -3.12 src\assistant.py
```

Open **http://localhost:8800** in **Chrome or Edge**. Without the extras below, voice uses the browser's own speech functions. The browser's voice input sends the audio to Google's speech service, so it needs internet.

**11b. Offline voice (recommended, about 10 min).**

```
py -3.12 -m pip install -r requirements_assistant.txt
cd data\voices
py -3.12 -m piper.download_voices en_US-lessac-medium
cd ..\..
py -3.12 src\assistant.py
```

The first time you speak, faster-whisper downloads its speech model (about 500 MB, only once). The top bar should then say `voice in: Whisper · voice out: Piper`. For faster but less accurate speech recognition, run `$env:WHISPER_MODEL="base.en"` before starting.

**11c. Photos (optional, about 3 GB download).**

```
ollama pull qwen2.5vl:3b
```

Then click the camera button and choose a photo. The model describes what it sees, and that description is added to the case.

**11d. Try without Ollama (demo mode with a fake model, just to see the screens):** `$env:STUB="1"; py -3.12 src\assistant.py`

**How to use it**

1. Speak (click the microphone, then click again to stop) or type the problem.
2. Answer its questions with the buttons, or by voice. It asks at most 3.
3. **Printer view:** press ▶ to see how the fault travels from the cause to where you see it.
4. **Fix it:** tick the steps as you do them. Press **Read next step**, or type or say "next".
5. Press **Yes, fixed** or **No** at the end. This is saved in `eval\assistant_feedback.jsonl`.

The assistant is a demonstration tool. It is not part of the test results, so please don't type the 58 test cases into it.

## If something goes wrong

- *"Connection refused"* → Ollama is not running. Open the Ollama app from the Start menu.
- *"model not found"* → run the `ollama pull` command from Step 2 again.
- Very slow (more than 2 minutes per case) → use the 3b model.
- Anything else → send me a screenshot of the error.

## Step 20 — Accuracy check with the real models (development set, step 5)

From the `agent` folder, Ollama running. Run the three blocks one after another. Each prints `case 1/77 ...` while it works
and a table at the end. The 58 test cases are NOT used here.

A. Keyword reader only, no language model (should match my offline numbers; a few minutes):
```
$env:STUB="0"; $env:AGENT_PRIOR="0"; $env:LEAD="rules"; $env:FT_MODEL=""; $env:READER="rules"
py -3.12 src\dev_eval.py --runs 2 --tag _A2_rules
```
B. Keywords first, Qwen fills what the keywords miss (about 20-40 minutes):
```
$env:READER="hybrid"
py -3.12 src\dev_eval.py --runs 2 --tag _B2_hybrid
```
C. Qwen reads everything (the setting of your first run; about 20-40 minutes):
```
$env:READER="model"
py -3.12 src\dev_eval.py --runs 2 --tag _C2_model
```
Paste me the first table of each run.

## Step 21 — The new FMEA-graph assistant

The assistant now works on a symptom graph (31 parts, failure modes, about 100 observable symptoms with many wordings,
Klipper error messages, checks and sources): `src\fmea\kb_symptoms.py`, `src\fmea\kb_modes.py`, `src\fmea\engine.py`.
It asks simple yes / no questions and needs no language model.

1. Try it: start the assistant (`py -3.12 -m src.assistant_v2.server`), open http://localhost:8900/twin, Assistant tab.
2. Quick check without questions (seconds): `py -3.12 src\fmea\evaluate.py`
3. Conversation test with Qwen playing the technician (Ollama running, about 30-60 minutes):
   ```
   $env:STUB="0"
   py -3.12 src\fmea\eval_dialogue.py --sets practice test_A test_B
   ```
   test_B (R15-R30, C15-C28) was never used to build or tune the graph: it is the honest score.
4. Best setting (FMEA graph + arm G's reading of the first sentence):
   ```
   $env:STUB="0"
   py -3.12 src\fmea\eval_dialogue.py --sets practice test_A test_B --arm-g
   ```
   In the assistant page arm G is used automatically on the first message when Ollama runs (turn off: `$env:FMEA_G="0"`).
5. Held-out check with arm G run live (also covers the new held-out cases in data\heldout_cases.json):
   ```
   $env:STUB="0"
   py -3.12 src\fmea\evaluate.py --live-g
   ```

## Step 22 — The final assistant (start here)

Double-click `start_assistant.bat` in the `agent` folder (start the Ollama app first for the full mode).
The browser opens http://localhost:8900 with the 3D printer and the assistant. Everything about the final model,
its measured accuracy and its limits is in `FINAL_MODEL.md`. The old chat page is still at http://localhost:8900/classic.
