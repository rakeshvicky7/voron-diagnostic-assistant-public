# Results analysis notes — run of 21 October 2026

Analysis notes for you to understand and then write up in your own words. Not thesis text.

**Setup:** qwen2.5:7b-instruct via Ollama on a GTX 1650 (4 GB), temperature 0, seed 42, nomic-embed-text, 42 test cases × 5 arms = 210 runs, all completed. Files: `summary.csv`, `paired_tests.csv`, `per_case_matrix.csv`, `fig_accuracy_by_arm.png`.

## 1. Main numbers (n = 42, 95% Wilson CI)

| Arm | Correct part first | Correct part in top 3 |
|---|---|---|
| A — LLM only | 26% (15–41) | 52% (38–67) |
| B — Voron docs as text | 33% (21–48) | 60% (45–73) |
| C — structured model | 33% (21–48) | **83% (69–92)** |
| D — generic troubleshooting guide | 19% (10–33) | 43% (29–58) |
| E — C + D | 38% (25–53) | **83% (69–92)** |

## 2. Paired tests (exact McNemar, same 42 cases in every arm)

| Question | Top-3 result | p |
|---|---|---|
| C vs B — does structuring the design information beat searching it as text? | C right where B wrong in 14 cases, the reverse in 4 | **0.031** |
| C vs D — design-based structure vs generic fault guide | 19 vs 2 | **0.0002** |
| C vs A — structured model vs no knowledge | 14 vs 1 | **0.001** |
| B vs A — does plain retrieval help? | 7 vs 4 | 0.55 (no evidence) |
| E vs C — does adding the guide to C help? | 2 vs 2 | 1.0 (no difference) |

For **top-1** (first guess), no comparison except B vs D (p = 0.031) is significant.

## 3. What this means (plain words)

1. **Structure helps the agent produce the right shortlist, not the right first guess.** C puts the faulty part in its top 3 in 83% of cases, against 60% for the same documents as text. But its first guess is not more often right than B's. A useful interpretation: the structured model gives the agent the right *candidates*; choosing between them needs either a stronger model or the technician's answers (the ask-the-technician step).
2. **The generic fault guide does not help this machine.** D is not better than the model alone, and 9 of its 42 answers did not name a valid part even after a correction turn. Generic fault knowledge does not map onto a specific machine's parts.
3. **Adding generic fault knowledge to the structured model adds nothing (E = C).**
4. **On the 23 "unseen" faults** (causes the generic guide does not cover), C reaches 78% top-3 vs 48% for D (p = 0.065 — suggestive, the subset is small).
5. **On the 14 real community cases**, C reaches 79% top-3 vs 57% (B) and 29% (D); C vs D p = 0.016.

## 4. Threats to validity you must report

- **Answer-vocabulary alignment.** The structured model's text contains the same part ids the agent must answer with. This may make it easier for C to name a valid part. → Robustness check **C2** prepared (same cards, ids removed). Run it, see below.
- **Constructed cases** were written by the same person (Claude) who designed the schema — 28 of 42 cases. The real-case subset (n = 14) shows the same direction, which supports the result, but an independent review of the constructed cases is still needed.
- **One model, one run.** Temperature 0 makes it repeatable, but results may differ with another model. A second model (e.g. qwen2.5:3b or llama3.1:8b) would show whether the pattern holds.
- **Small n.** 42 cases give wide confidence intervals; top-1 differences are too small to detect.
- **Ground-truth judgement.** "Acceptable" alternative parts were defined before the run (`evaluation/ground_truth.csv`) — say so.
- **B and C do not contain the same information (found 23 Oct 2026).** Arm B indexes the manual and the documentation site only. The firmware configuration, BOM and slicer profiles were not added to B as text, but their values are inside the C/C2 cards. So C vs B (and C2 vs B) compares structure *plus* access to config values against documents without them. Report this; the cleaner test (add the config file as text to B, "B+") is future work.
- **Known display bug:** bed-screw positions shown as "correct values" in C/E cards. It did not affect scoring.

## 5. Robustness check C2 — done (22 October 2026)

C2 = the same structured model, but the component ids were removed from the card text (names only).

| | Top-1 | Top-3 |
|---|---|---|
| C (ids in text) | 33% | 83% |
| **C2 (ids removed)** | **43% (29–58)** | **69% (54–81)** |
| B (docs as text) | 33% | 60% |
| D (generic guide) | 19% | 43% |

Paired tests: C2 vs C top-3 1 vs 7, p = 0.070; C2 vs B top-3 12 vs 8, p = 0.50; C2 vs D top-3 13 vs 2, **p = 0.007**, top-1 **p = 0.021**.

**Revised conclusions (these replace section 3 where they differ):**
1. Part of C's large top-3 advantage came from the **answer-vocabulary alignment** (ids in the text). With ids removed, structured vs text is **not significantly different** (69% vs 60%). The claim "structure beats the same documents as text" is **not established** with 42 cases.
2. The claim that **design-based machine knowledge beats generic fault knowledge is robust**: C2 beats D on both top-1 and top-3.
3. C2 has the **highest first-guess accuracy** of all arms (43%) — the direction favours structure, but the sample is too small to confirm.
4. The vocabulary effect is itself a practical finding: a knowledge base that uses the **same names as the answer space** helps a small model produce usable, valid answers. Report it as a design lesson, not hidden.

## 6. Second model: Llama 3.1 8B (run finished 23 October 2026)

Same 42 cases, same prompt, tools and settings; arms A, B, C, C2, D (E left out). Part of the model ran on the CPU (`NUM_GPU=18`) because of the 4 GB GPU; this changes speed, not the method. Files: `summary_llama3-1-8b.csv`, `results_raw_llama3-1-8b.jsonl`, figure `fig_two_models.png`.

| Arm | Qwen top-1 | Llama top-1 | Qwen top-3 | Llama top-3 |
|---|---|---|---|---|
| A — none | 26% | 24% | 52% | 60% |
| B — docs as text | 33% | 21% | 60% | 50% |
| C — cards | 33% | 36% | **83%** | **74%** |
| C2 — cards, no ids | **43%** | **43%** | 69% | 64% |
| D — generic guide | 19% | 17% | 43% | 29% |

Paired tests (exact McNemar), Qwen vs Llama:

| Comparison | Qwen top-3 p | Llama top-3 p | Llama top-1 p |
|---|---|---|---|
| C2 vs D (design vs generic) | 0.007 | **0.002** | **0.007** |
| C vs D | 0.0002 | **0.0002** | 0.08 |
| C vs B (structure vs text) | 0.031 | 0.053 | 0.24 |
| C2 vs B (structure vs text, no ids) | 0.50 | 0.29 | 0.064 |
| C2 vs C (effect of ids) | 0.070 | 0.22 | 0.45 |
| B vs A (does doc retrieval help?) | 0.55 | 0.42 (B worse) | 1.0 |

Other differences: Llama gave no valid part in 15 of 42 D answers (Qwen 9); Llama used its search tools far more (one extra search in every C/C2 run, 51 extra searches in B), and was slower (B: 192 s vs 119 s per case).

**What the second model adds:**
1. **The main finding is now robust across two model families:** design-derived knowledge (C, C2) clearly beats generic troubleshooting knowledge (D) with both models, on top-3 and (for C2) on top-1.
2. **Structure vs text stays suggestive, not proven:** C beats B by 9–24 points in both models, but with ids removed (C2) the difference is not significant in either.
3. **Plain document retrieval did not help either model** (B vs A not significant; for Llama B was even lower). Documents written for building a machine do not, as text, answer diagnostic questions; this matches the RQ1 gap analysis.
4. **C2 has the best first guess in both models (43%).** Consistent, but still within the confidence intervals.
5. The id effect (C vs C2) is smaller for Llama (74% vs 64%) than for Qwen (83% vs 69%).

## 7. Third model: Mistral 7B (finished 23 October 2026)

Same setup, `NUM_GPU=18`. 209 of 210 runs: case C05 in arm D failed twice and is missing (D: n = 41). Files: `summary_mistral-7b.csv`, `results_raw_mistral-7b.jsonl`; figure with all three models: `fig_three_models.png`.

| Arm | Qwen top-1 / top-3 | Llama top-1 / top-3 | Mistral top-1 / top-3 |
|---|---|---|---|
| A — none | 26 / 52% | 24 / 60% | 24 / **71%** |
| B — docs as text | 33 / 60% | 21 / 50% | 26 / 48% |
| C — cards | 33 / **83%** | 36 / **74%** | 24 / 67% |
| C2 — cards, no ids | **43** / 69% | **43** / 64% | **43** / **74%** |
| D — generic guide | 19 / 43% | 17 / 29% | 15 / 27% |

Mistral paired tests: C2 vs D top-3 20 vs 1, p < 0.001, top-1 p = 0.007; C vs D top-3 16 vs 0, p < 0.001; C2 vs B top-3 p = 0.019; C vs B p = 0.096; **B vs A: B worse, p = 0.013**; C vs A and C2 vs A not significant; C2 vs C top-1 p = 0.021 (C2 better).

**Important caveat for Mistral:** it almost never followed the required answer format when tools were involved. A correction turn was needed in about 39 of 42 runs in every retrieval arm, and 9 answers in B and in C, 3 in C2 and 18 in D still had no valid part. Arm A (no tools) did not have this problem. So Mistral's retrieval arms are pulled down by **format and tool-handling failures**, not only by the knowledge given. Report this as a model-capability finding: instruction following decides whether retrieval can help at all.

**Conclusions across three model families (Qwen, Llama, Mistral):**
1. **Robust in all three:** design-derived knowledge (C2, and C) beats generic troubleshooting knowledge (D), on top-3 with p ≤ 0.007 every time; C2 also on top-1 in all three.
2. **Robust in all three:** C2 gives the best first guess (43% in every model).
3. **Robust in all three:** plain retrieval over the build documentation does not help (B never beats A; for Mistral it is significantly worse).
4. **Not robust:** whether cards beat no knowledge (C vs A) or documents as text (C vs B) depends on the model. Structure helps most for the model that follows the format best (Qwen).
5. **The generic guide (D) is the worst arm in every model**: adding general fault knowledge actively harms localisation on a specific machine.

## 8. Arm B+ (BP): documents plus machine files as text (Qwen, 24 October 2026)

BP = arm B + firmware configuration (per section), BOM and slicer profiles as plain text; 1,019 passages. Same model and settings as the main run.

| Arm | Top-1 | Top-3 |
|---|---|---|
| B — docs as text | 33% | 60% |
| **BP — docs + machine files as text** | 33% (21–48) | 62% (47–75) |
| C — cards | 33% | 83% |
| C2 — cards, no ids | 43% | 69% |

Paired tests: BP vs B top-3 3 vs 2, p = 1.0 (no difference); C vs BP top-3 14 vs 5, p = 0.064; C2 vs BP top-3 13 vs 10, p = 0.68; BP vs D top-1 6 vs 0, p = 0.031. BP gave no invalid answers.

**What this means:**
1. **Having the configuration values as text did not help** (62% vs 60%). So C's advantage over B is not explained by C having more information.
2. A likely reason: a symptom such as "the extruder pulls the filament back out" shares almost no words with the config line `dir_pin: gpio13  # Add ! if moving opposite direction`. A keyword check found a machine-file passage among the top 5 for only 2 of 42 symptoms. The cards connect the value to a failure mode and a symptom; plain text does not.
3. **Structure question, final answer:** with ids, cards vs the same information as text is borderline (83% vs 62%, p = 0.064); without ids (C2) there is no difference (69% vs 62%). Structure helps mainly by linking symptoms, failure modes and correct values, and by using the answer vocabulary. A larger test set is needed to prove it.

**How to frame RQ answers honestly:** structured design knowledge clearly outperforms generic fault knowledge for a specific machine; its advantage over well-retrieved machine documentation is suggestive but not statistically demonstrated at this sample size; vocabulary alignment between knowledge base and output space is a measurable effect.

## 9. Test Set v2: 16 new real cases (Qwen, run finished 28 October 2026)

The 16 cases (R15–R30) were collected after the first experiment. No cards, prompts or code were changed, so this is an out-of-sample test. The one BP run that failed (R24) was rerun on 28 October and was a miss, so BP now covers all 58 cases (60% top-3, 36% primary only).

**New 16 cases only**

| Arm | Top-1 | Top-3 (with accepted alternatives) | Top-3, primary part only |
|---|---|---|---|
| A — no knowledge | 13% | 75% | 31% |
| B — docs as text | 19% | 69% | 25% |
| BP — docs + machine files | 19% | 56% | 25% |
| C — cards | 31% | 75% | 31% |
| **C2 — cards, no ids** | **38%** | **88%** | **50%** |
| D — generic guide | 0% | 38% | 0% |
| E — cards + guide | 19% | 88% | 25% |

**All 58 cases pooled**

| Arm | Top-1 | Top-3 | Top-3 primary only | Real cases only (n = 30), top-3 |
|---|---|---|---|---|
| A | 22% | 59% | 34% | 63% |
| B | 29% | 62% | 40% | 63% |
| BP | 29% | 60% | 36% | 60% |
| C | 33% | 81% | 57% | 77% |
| C2 | 41% | 74% | 57% | 73% |
| D | 14% | 41% | 24% | 33% |
| E | 33% | 84% | 53% | 80% |

**Paired tests, all 58 cases (exact McNemar, Holm-corrected over 9 planned comparisons; computed by `eval/analysis_v2.py`, files `paired_tests_v2.csv`, `summary_v2_primary.csv`):**

| Comparison | Top-3: only first / only second | p (Holm) | Primary-only: only first / only second | p (Holm) |
|---|---|---|---|---|
| C vs D | 27 / 4 | **0.0003** | 21 / 2 | **0.0006** |
| C2 vs D | 22 / 3 | **0.001** | 23 / 4 | **0.003** |
| C vs A | 16 / 3 | **0.031** | 16 / 3 | **0.031** |
| C vs BP | 18 / 6 | 0.136 | 15 / 3 | **0.045** |
| C vs B | 16 / 5 | 0.136 | 13 / 3 | 0.106 |
| C2 vs B | 16 / 9 | 0.92 | 16 / 6 | 0.21 |
| C2 vs C | 3 / 7 | 1.0 | 4 / 4 | 1.0 |
| B vs A | 7 / 5 | 1.0 | 8 / 5 | 1.0 |
| E vs C | 4 / 2 | 1.0 | 1 / 3 | 1.0 |

After the Holm correction, cards beat the generic guide and no knowledge on both measures. Cards beat documents-plus-files as text on the strict measure only. Cards vs documents as text (B) is still not significant.

**What changed (plain words)**
1. **Still true:** the generic guide is the worst source. On the new real cases it never named the right part as first choice and found the primary part in no case at all. It also gave no answer at all for 6 of 16 cases. This is now the strongest finding of the thesis.
2. **Stronger, but not proven:** with 58 cases, the cards lead documents as text (81% vs 62%; raw p = 0.027), but the difference does not survive the Holm correction (0.136). Against documents plus machine files (BP), the cards win on the strict primary-only measure (57% vs 36%, Holm p = 0.045).
3. **New and important:** on the new real cases alone, the cards with ids (C) were **no better than no knowledge** (75% vs 75%; primary-only 31% vs 31%). C's large lead over A comes mostly from the constructed cases, which were written from the same documents as the cards. This must be reported as a limitation, not hidden. The real-only pooled figure (C 77% vs A 63%) is the fairest headline.
4. **C2 (cards without ids) did best on the new cases** (88% top-3, 50% primary only). This weakens the "vocabulary alignment" explanation and suggests the content of the cards matters more than matching ids. With n = 16, treat this as a pointer, not a result.
5. **Error pattern (error analysis section):** four new faults were caused by the umbilical wiring or its connector (R18, R21, R24, R28). For the three electrical ones (R18, R24, R28), arm C named the part at the end of the wire (thermistor, heater, extruder motor) instead of the wiring. For R21 (the umbilical plate resonating) it blamed the X rail. The cards record the wiring as a connection but do not make "intermittent fault in several toolhead functions at once → shared cable" explicit. This is a concrete design improvement (an "upstream common cause" rule), and it fits design-science iteration.
6. **Scoring caution:** accepted alternatives raise every arm, including A (for example, `extruder_motor` was accepted for R24, R27 and R29). The primary-only column is the stricter and fairer measure. Report both, primary-only first.

## 10. Three models on all 58 cases (finished 30 October 2026)

Missing run: Llama, arm C2, case R23. It hung and timed out twice, and because the model runs at temperature 0 a retry repeats the same hang.

| Arm | Qwen (top-1 / strict top-3 / top-3) | Llama | Mistral |
|---|---|---|---|
| A | 22 / 34 / 59 | 22 / 41 / 64 | 21 / 52 / 72 |
| B | 29 / 40 / 62 | 22 / 34 / 55 | 22 / 33 / 48 |
| C | 33 / 57 / 81 | 31 / 57 / 78 | 24 / 48 / 69 |
| C2 | 41 / 57 / 74 | 37 / 47 / 67 (n = 57) | 43 / 57 / 76 |
| D | 14 / 24 / 41 | 14 / 21 / 29 | 14 / 24 / 33 |

- **C and C2 vs D:** significant in every model, on both measures and on the real cases alone (p ≤ 0.039 in all 18 tests).
- **C vs B:** lenient p = 0.027 (Qwen), 0.015 (Llama) and 0.029 (Mistral), unadjusted. The same direction in all three models, but not significant after Holm, and not on the real cases alone.
- **C vs A:** holds for Qwen only (Llama p ≈ 0.08; Mistral no difference).
- **B vs A:** never better; Mistral significantly worse.
- **C2:** best top-1 in every model.

## 10. Three models on all 58 cases (finished 1 November 2026)

Script: `eval/multi_v2.py`; summary: `summary_three_models_v2.csv`. One run is missing: Llama, C2, R23. The model stalled and timed out twice, and the result is deterministic, so a retry would stall again.

| Arm | Qwen (top-1 / strict / lenient) | Llama | Mistral |
|---|---|---|---|
| A | 22 / 34 / 59 | 22 / 41 / 64 | 21 / 52 / 72 |
| B | 29 / 40 / 62 | 22 / 34 / 55 | 22 / 33 / 48 |
| C | 33 / 57 / 81 | 31 / 57 / 78 | 24 / 48 / 69 |
| C2 | 41 / 57 / 74 | 37 / 47 / 67 | 43 / 57 / 76 |
| D | 14 / 24 / 41 | 14 / 21 / 29 | 14 / 24 / 33 |

**What changed:**
- **Cards vs documents (C vs B):** now significant (unadjusted) on the lenient measure in all three models (p = 0.027 / 0.015 / 0.029), and on the strict measure in two. It is still not significant after the Holm correction in the main model. But the same direction in three models is stronger evidence than any one test, so the thesis now calls this "consistent across models" rather than "not shown".
- **Cards vs no knowledge (C vs A):** significant only with Qwen. Llama is borderline (p = 0.077) and Mistral loses (6 / 8). This claim is weaker than before.
- **Cards vs generic guide (C and C2 vs D):** p ≤ 0.003 in all models on both measures. This is still the strongest result.

## 11. Graph RAG (arm G) and the chat assistant, overnight run of 6-7 Nov 2026 (Qwen 2.5 7B, 58 cases)

### Arm G (single answer, same prompt, model and budget as A-E)

| Arm | Top-1 (strict) | Top-3 |
|---|---|---|
| A no knowledge | 13/58 (22 %) | 34/58 (59 %) |
| B documents | 17/58 (29 %) | 36/58 (62 %) |
| C cards | 19/58 (33 %) | 47/58 (81 %) |
| E cards + guide | 19/58 (33 %) | 49/58 (84 %) |
| **G graph RAG** | **19/58 (33 %)** | **50/58 (86 %)** |

Exact McNemar tests on top-3, G against each arm (G wins / the other arm wins):

| Comparison | G wins / other wins | p |
|---|---|---|
| G vs A | 19 / 3 | 0.0009 |
| G vs B | 17 / 3 | 0.003 |
| G vs B+ | 19 / 4 | 0.003 |
| G vs D | 28 / 2 | < 0.001 |
| G vs C | 6 / 3 | 0.51 |
| G vs E | 3 / 2 | 1.0 |

G has the highest top-3 of all arms. It is clearly better than having no knowledge and better than the documents as text. It is not significantly better than the component cards alone (C) or cards plus guide (E). Top-1 is the same as C and E.

Reading: the graph adds reach (the shared upstream cause comes into the top 3), but not ranking at position 1. These p-values are not yet Holm-corrected together with the earlier family of tests.

### Chat assistant v2, simulated technician (first run)

| Measure | Result |
|---|---|
| Top-1 | 13/58 (22 %) |
| Top-3 | 34/58 (59 %) |
| Mean questions per case | 3.6 |
| Mean time per case | 42 s |

The assistant was significantly worse than arm G on top-3 (G wins 18, dialogue wins 2, p = 0.0004). Causes found:

1. **Input handling (12 of 58 cases lost).** In 12 cases the model labelled a plain fault statement as an "info question" or a "greeting", so no diagnosis was made. Examples: "Overhangs droop and bridges sag", "Ghost echoes next to sharp corners". Fixed: a message counts as a question or a greeting only if it reads like one. Print-quality words (overhang, ghosting, banding, ringing …) were added to the printer vocabulary.
2. **Weak starting belief.** The assistant's own start (card search plus rules) is weaker than the arm G agent. Fixed: the arm G agent now reads the description once, and its top 3 become the starting belief that the questions confirm or change.
3. **Many unanswerable questions.** 143 of 208 simulated answers were "don't know", because the test cases describe only the symptom, so many questions cannot be answered from the case. This limits what questioning can add in this test.

Second run: `eval_dialogue.py --name run2`.
