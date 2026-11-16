# Diagnostic chat v2: how it works

Goal of this version: find the **cause** of a fault through a conversation. It does not give repair steps; that comes in a later version.

## The idea

A single sentence like "my nozzle is not working" is not enough to name a cause. A good engineer would first ask what exactly happens, then ask for the observations and measurements that separate the possible causes, and check the numbers against the design values. The assistant does the same.

## One turn, step by step

| Step | What happens | File |
|---|---|---|
| 1. Check the input | Empty, gibberish, too long, another printer (Ender, Prusa, Bambu, Voron 2.4 …) → a polite message asking for valid Voron 0.2 input | `understand.py` |
| 2. Understand | The model labels the message (fault report / answer / info question / greeting / off-topic / other machine) and pulls out facts and numbers. A rule-based extractor for numbers with units (°C, Ω, V, Hz, mm, mm/s) fills any gaps | `understand.py` |
| 3. Case file | Everything known so far: the technician's words, facts (when, how it started, error message, what comes out …) and measurements | `engine.py` |
| 4. Possible causes | Scored from: the part the technician names plus the parts upstream of it in the failure graph; the card search; Klipper error messages; the chosen answers; and the calculations. A passing calculation lowers the score of the parts it tests | `engine.py` |
| 5. Calculations | Exact checks against design values, each with its source (see below) | `engineering.py` |
| 6. Probabilities | Every part has a probability: base score × the likelihood of each answer given (Bayes). If an answer is expected when part d is faulty, it is also expected (more weakly) for the parts that power, feed or carry d in the failure graph | `reasoner.py` |
| 7. Next question | ONE question at a time (two only if both are one-click and equally useful), chosen by expected information gain ÷ effort (minimum-entropy probing, de Kleer & Williams 1987). It follows a diagnosis tree: the kind of problem → the area → the part. For example, no extruder questions for a power cut, and the cord test only after "everything goes off". Once one part leads, the question is chosen to confirm or refute that part | `reasoner.py`, `questions.py` |
| 8. Stop | Name the cause when it is ≥ 70 % (or ≥ 55 % and 3× the next part), after at least one confirming answer; or when no question would change much; or after 6 questions. Never from the first sentence alone | `reasoner.py` |
| 9. Name the cause | The cause as a physical chain (what failed → what that does → what you see), with the evidence, calculations, probability, other possibilities, what was ruled out, and what would make it certain | `engine.py` |

Impossible numbers (for example 5000 mm fed when 100 mm were commanded) are not used. The assistant asks for them again.

Button answers do not go through the language model, so they are instant. The model is only used to read free text and to write the final explanation.

## Parts added for the assistant only

The evaluation keeps its 28 parts. The assistant adds three power parts from the BOM and the electrical documentation (`extra_parts.py`):

- the mains power input (C13 cord, IEC C14 inlet, AC wiring);
- the 24 V DC wiring and crimps;
- the 150 °C bed thermal fuse.

## Timing physics: "what changes at that moment"

`engineering.context` explains why a fault shows at a certain moment. Example: "after the first layer". In the Voron slicer profile, the head then goes from 30 to 100–125 mm/s (about 4× faster, about 17× the kinetic energy), the part fan stays off until layer 4, and the bed drops from 100 to 90 °C. So a stop exactly there points to a connection that opens under vibration, not to heat or the fan. This check explains the timing but adds no weight: the same fact is already counted through the answer.

## Calculations and their sources

| Check | Formula | Design value and source |
|---|---|---|
| Hotend heater power | P = V²/R | 24 V (BOM: Meanwell LRS-150-24). The cartridge wattage is not in the documents, so the usual 20–80 W range is marked as general |
| Bed heater | R_expected = 24²/60 = 9.6 Ω | BOM: 60 W silicone heater |
| Thermistor temperature | 1/T = 1/T25 + ln(R/R25)/B | NTC 100 k, B 3950 (config comment "Generic 3950") |
| Temperature reached | gap = target − actual | max_temp 270 / 120 (config) |
| Extruded length | (actual − commanded)/commanded | rotation_distance 22.23, gear ratio 50:10 (config lines 147–148) |
| Axis travel | same | rotation_distance 40 (XY), 8 (Z) (config) |
| Belt tension | tension ∝ f² | 110 Hz at 150 mm (assembly manual p.141) |
| Flow demanded | Q = speed × layer height × line width | max_extrude_cross_section 0.8 (config). The hotend melt limit is marked as general |
| Supply voltages | deviation from 24 V / 5 V | BOM (24 V). The ±5 % tolerance is marked as general |
| Fan voltage | V at connector | 24 V fans (BOM) |
| Power budget | 60 W + 24²/R + ~25 W | 150 W supply (BOM) |

## Not in this version

- Repair steps.
- Voice.
- Pictures.

## How to evaluate it (for the thesis)

1. Run `test_scenarios.py`. It checks the required behaviours (asks on vague input, rejects invalid input, handles off-topic and other printers, catches impossible values, lets calculations decide).
2. Run simulated conversations for the 58 test cases: a script answers the assistant's questions from the case description. Then measure:
   - whether the right part was named;
   - how many questions were needed;
   - how often it asked for information the case already contained.
3. A small user check with real people.
