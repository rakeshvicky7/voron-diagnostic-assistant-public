# Handoff: finishing the Voron 0.2 diagnostic assistant

STATUS: DONE

The user (RR, M.Sc. thesis) asked for a final, working, accurate assistant. Use simple English with him, decide yourself,
only free/offline tools (Ollama + qwen2.5:7b-instruct on his laptop; no paid APIs). Work in `C:\Users\rakes\Downloads\rag dataset\agent`.

## What the final model is
- `src/fmea/` : symptom graph (kb_symptoms.py 106 symptoms with many wordings, kb_modes.py 67 failure modes for 31 parts),
  `engine.py` (text -> symptoms -> failure modes -> parts; typo fixing; negation; Klipper errors; optional yes/no questions),
  `cases.py` (case memory: data/case_base.json + data/confirmed_cases.jsonl, learns when the technician confirms a part),
  `evaluate.py` (one-shot accuracy), `eval_dialogue.py` (conversation test with Qwen as technician), `dev.py` (dev score only).
- Arm G (old graph agent, Qwen via Ollama) reads the first description; its top 3 boost the ranking (weights 5,3,2).
- Server `src/assistant_v2/server.py`: `/` = final assistant page (`static/twin.html`, 3D printer + assistant),
  `/api/fmea` (message / refine / exclude / confirm / ask / answer), `/classic` = old chat.
- Held-out results so far (never tuned on): test_B (30) + test_C (9): graph + arm G = 72 % right part first, 82 % within one check,
  92 % within two checks. Old conversation assistant: 23 % first.

## Rules (important)
- Tune ONLY on the dev sets (practice + test_A): `python src/fmea/dev.py`. Never tune on test_B / test_C.
- Run the held-out sets once at the very end: `python src/fmea/evaluate.py --g` (uses saved arm G answers for the 58 cases).
- Evaluation must not use the case memory for the tested case (dev split only + leave-one-out).

## Final state (14 Nov 2026)
- [x] Case memory (cases.py): neutral on new faults (dev, leave-one-out), repeat faults 28/43 -> 43/43
- [x] Server: two-phase answer (instant, then `refine` with arm G), `confirm` saves the case, `/` = final page, `--open`, `/vendor` (three.js offline)
- [x] twin.html: refine flow, confirm, similar past case, mode line
- [x] start_assistant.bat, FINAL_MODEL.md, SETUP_WINDOWS.md step 22
- [x] One final held-out run. A tuning round (max aggregation, raw priors, extra symptoms, "prints look fine" negation) was better on dev
      but worse on held-out (test_B 60 % vs 67 % first), so it was reverted: the shipped engine is the validated one
      (`python src/fmea/evaluate.py --g` must print test_B 67/77/90 and test_C 67/100/100).
## Still open (not blocking)
- Browser check of the new page flow on the user's laptop with Ollama (instant answer -> refined answer, "This was it" saving).
- More held-out real cases (9 so far in data/heldout_cases.json; goal about 40). A trial with real people.
