"""Validation of the virtual printer (stage 2): does it behave like the documents say?

Checks
 1. Healthy printer: every answer is a normal answer and every engineering check (engineering.py) passes.
 2. Detectability: with each fault (40 runs, severity 0.2-0.95), how often does the technician see something abnormal?
 3. Agreement with the part cards: for every abnormal answer the twin gives, do the cards (EVIDENCE table in
    questions.py) list the faulty part for that answer?  Disagreements are listed: they are either a gap in the cards
    or a limit of the twin, and each one is worth a look.
 4. Engineering checks: do the calculations on the twin's measurements point to the faulty part?

Run from the agent folder:   py -3.12 src\\twin\\validate_twin.py      (about 10 seconds, no model needed)
Output: eval/twin_validation.md and eval/twin_validation.csv
"""
import sys, csv, pathlib, random, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from twin.virtual_printer import VirtualPrinter, PARTS, MODES, D, GEN     # noqa: E402
from assistant_v2.questions import EVIDENCE                                 # noqa: E402
from assistant_v2 import engineering as eng                                 # noqa: E402
from assistant_v2.reasoner import NORMAL                                    # noqa: E402

A = pathlib.Path(__file__).resolve().parents[2]
N_RUNS = 40
SKIP_SLOTS = {"recent_change", "filament", "what_happens", "error_message", "onset", "when", "problem_kind", "runout_check", "psu_led", "other_load"}

def abnormal(o):
    """Choice answers that differ from a healthy printer (context slots such as 'when' are not symptoms by themselves)."""
    return {(k, x) for k, x in o.items() if k not in SKIP_SLOTS and x not in NORMAL and x != "I can't tell"}

def run():
    rows, gaps, report = [], collections.Counter(), []
    # 1. healthy printer
    bad_h, eng_h = collections.Counter(), collections.Counter()
    for seed in range(30):
        o, m = VirtualPrinter(None, seed=seed).observations()
        for a in abnormal(o): bad_h[a] += 1
        if o.get("error_message", "none") != "none": bad_h[("error_message", o["error_message"])] += 1
        for c in eng.run(m):
            if c["verdict"] != "ok": eng_h[c["title"]] += 1
    # 2-4. every part
    for part in PARTS:
        rnd = random.Random(part); det = agree = total_ab = eng_hit = 0; modes = collections.Counter(); seen = collections.Counter()
        for i in range(N_RUNS):
            vp = VirtualPrinter(part, severity=rnd.uniform(0.2, 0.95), seed=1000 + i); o, m = vp.observations()
            modes[vp.mode or "-"] += 1
            ab = abnormal(o); err = o.get("error_message", "none") != "none"
            checks = [c for c in eng.run(m) + eng.context(o, [vp.describe()]) if c["verdict"] != "ok"]
            told = not vp.describe().startswith(("Everything looks normal", "Something seems slightly off"))
            if ab or err or checks or told: det += 1
            if any(part in c.get("points_to", []) for c in checks): eng_hit += 1
            for a in ab:
                total_ab += 1; seen[a] += 1
                if part in EVIDENCE.get(a, []): agree += 1
                else: gaps[(part, a)] += 1
        rows.append({"part": part, "modes": "; ".join(f"{k} ({n})" for k, n in modes.items()), "detectable_%": round(100 * det / N_RUNS),
                     "abnormal_answers": total_ab, "cards_agree_%": round(100 * agree / total_ab) if total_ab else "",
                     "engineering_points_to_part_%": round(100 * eng_hit / N_RUNS),
                     "typical_answers": "; ".join(f"{k}={x}" for (k, x), _ in seen.most_common(3))})
    # write
    out = A / "eval"; out.mkdir(exist_ok=True)
    with open(out / "twin_validation.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    n_gen = sum(1 for _, (val, src) in D.items() if str(src).startswith(GEN))
    L = ["# Virtual printer: validation", "",
         f"Design values used: {len(D)}, of which {len(D) - n_gen} come from the documents and {n_gen} are general engineering values (GEN).", "",
         "## 1. Healthy printer (30 runs)", "",
         ("All answers normal and all engineering checks pass." if not bad_h and not eng_h else
          "Abnormal answers: " + ", ".join(f"{k}={x} ({n})" for (k, x), n in bad_h.items()) + "; engineering flags: " + ", ".join(f"{k} ({n})" for k, n in eng_h.items())), "",
         f"## 2-4. Each part with a fault ({N_RUNS} runs, random severity 0.2-0.95)", "",
         "| Part | Fault modes (runs) | Technician notices a problem | Cards agree | Engineering check names it | Most frequent abnormal answers |", "|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['part']} | {r['modes']} | {r['detectable_%']} % | {r['cards_agree_%']}{' %' if r['cards_agree_%'] != '' else ''} | "
                 f"{r['engineering_points_to_part_%']} % | {r['typical_answers']} |")
    det_all = sum(r["detectable_%"] for r in rows) / len(rows)
    ag = [r["cards_agree_%"] for r in rows if r["cards_agree_%"] != ""]
    L += ["", f"Mean detectability: {det_all:.0f} %. Mean agreement with the cards: {sum(ag) / len(ag):.0f} % (over parts with abnormal answers).", "",
          "## Disagreements between the twin and the cards (most frequent)", "",
          "The twin gives this answer for this faulty part, but the cards do not list the part for the answer.", "",
          "| Faulty part | Answer | Runs |", "|---|---|---|"]
    for (part, (k, x)), n in gaps.most_common(25):
        L.append(f"| {part} | {k} = {x} | {n} |")
    (out / "twin_validation.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))

if __name__ == "__main__":
    run()
