"""Overnight test of the chat assistant on the 58 test cases, with a simulated technician.

How it works
 - The assistant gets only the case's symptom sentence, exactly as a technician would type it.
 - Every question it asks is answered by a SIMULATED TECHNICIAN (the same local model with a different prompt).
   The simulator knows the true cause from the test set, so it can answer like someone standing at a printer
   with that fault. It is told never to name the part or the cause.
   - Button questions get one of the offered answers, or "I don't know".
   - Measurement questions are always answered "I don't know": the test cases contain no measured values,
     and invented numbers would not be evidence.
   - Any free-text answer that mentions the true part is replaced by "I don't know" (leak guard).
 - The run stops when the assistant names a cause or after 8 questions.
 - Saved per case: the named cause, its probability, the top 3, the number of questions, the time, and the full dialogue.

Run (from the agent folder; it resumes if stopped):
    py -3.12 src\\assistant_v2\\eval_dialogue.py --name run2      (a new name starts a new run)
Offline check of the script only:   $env:STUB="1"; py -3.12 src\\assistant_v2\\eval_dialogue.py --limit 3
Output: eval/dialogue_results[ _<model>].jsonl and eval/dialogue_summary[ _<model>].csv

Limits to report in the thesis: the simulator is the same model family as the assistant, and it knows the answer;
this measures how well the questioning finds the cause, not how real technicians answer.
"""
import sys, json, time, csv, re, argparse, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from run_eval import cases, wilson                      # noqa: E402  (same 58 cases and ground truth as the arms)
from assistant_v2 import engine as E                     # noqa: E402
from assistant_v2.questions import Q                     # noqa: E402
from assistant_v2.llm import ask_json, STUB, LLM_MODEL   # noqa: E402

OUT = E.A / "eval"
MAX_Q = 8
SIM_SYS = """You play a technician standing at a Voron 0.2 3D printer that has a fault. You know the hidden truth about
the fault, so you can answer what you would SEE, HEAR or READ on the screen. Rules:
- Never name the faulty part or the cause, and never hint at it beyond what you observe.
- Answer only what a technician could observe in a minute or two. If the truth does not tell you, or the question
  is about something unrelated, answer DONT_KNOW.
- For a choice question, answer with one of the options EXACTLY as written, or DONT_KNOW.
Return JSON only: {"answer": "..."}"""

def simulate_answer(case, q, words_to_hide):
    if q["kind"] == "fields": return None                              # no invented measurements
    if STUB:
        return q["options"][0] if q["kind"] == "choice" else None
    truth = f"""HIDDEN TRUTH (do not reveal): faulty part = {case['gt_component']}; cause = {case['gt_cause']}.
What the technician reported first: "{case['symptom']}"
Question from the assistant: {q['text']}"""
    if q["kind"] == "choice": truth += "\nOptions:\n" + "\n".join(f"- {o}" for o in q["options"]) + "\n- DONT_KNOW"
    else: truth += "\nAnswer in one short sentence, or DONT_KNOW."
    a = str((ask_json(SIM_SYS, truth, max_tokens=60) or {}).get("answer", "")).strip()
    if not a or a.upper().startswith("DONT"): return None
    if q["kind"] == "choice":
        m = next((o for o in q["options"] if o.lower() == a.lower()), None) or next((o for o in q["options"] if a.lower() in o.lower() or o.lower() in a.lower()), None)
        return m
    low = a.lower()
    if any(w in low for w in words_to_hide): return None                # leak guard
    return a

def run_case(c):
    case = E.new_case(); t0 = time.time(); dialogue = [{"user": c["symptom"]}]
    hide = {w for w in re.findall(r"[a-z]{4,}", (c["gt_component"] + " " + c["primary"].replace("_", " ")).lower())} - {"with", "and", "settings", "incl"}
    r = E.turn(case, c["symptom"])["reply"]; asked = 0
    while r["type"] == "questions" and asked < MAX_Q:
        form = {"facts": {}, "measurements": {}, "dont_know": []}
        for q in r["questions"]:
            asked += 1
            if q["id"] == "recheck": form["dont_know"].append(q["id"]); continue
            a = simulate_answer(c, {**Q.get(q["id"], {}), **q}, hide)
            if a is None: form["dont_know"].append(q["id"])
            else: form["facts"][(Q.get(q["id"]) or q).get("slot", q["id"])] = a   # engine questions (machine, which_part) are not in Q
            dialogue.append({"q": q["id"], "a": a or "DONT_KNOW"})
        r = E.turn(case, None, form)["reply"]
    hyps = [h["id"] for h in case.get("hyps", [])]
    named = r.get("diagnosis", {}).get("cause") if r["type"] == "diagnosis" else (hyps[0] if hyps else None)
    # the assistant's confirm loop: the technician checks the named part; if it is not the faulty one he answers
    # "this part is fine" (exclude) and the assistant continues (reported separately from strict top-1)
    named_check, asked_check = named, asked
    if r["type"] == "diagnosis" and named not in c["ok"]:
        r2 = E.turn(case, None, {"facts": {}, "measurements": {}, "dont_know": [], "exclude": [named]})["reply"]
        while r2["type"] == "questions" and asked_check < MAX_Q + 4:
            form = {"facts": {}, "measurements": {}, "dont_know": []}
            for q in r2["questions"]:
                asked_check += 1
                a = simulate_answer(c, {**Q.get(q["id"], {}), **q}, hide) if q["id"] in Q else None
                if a is None: form["dont_know"].append(q["id"])
                else: form["facts"][(Q.get(q["id"]) or q).get("slot", q["id"])] = a   # engine questions (machine, which_part) are not in Q
            r2 = E.turn(case, None, form)["reply"]
        h2 = [h["id"] for h in case.get("hyps", [])]
        named_check = r2.get("diagnosis", {}).get("cause") if r2["type"] == "diagnosis" else (h2[0] if h2 else None)
    return {"within1check": named_check in c["ok"], "questions_with_check": asked_check, "case": c["id"], "type": c["type"], "unseen": c["unseen"], "model": LLM_MODEL, "named": named,
            "p": r.get("diagnosis", {}).get("p"), "top3": hyps[:3], "primary": c["primary"], "ok": sorted(c["ok"]),
            "top1": named == c["primary"], "top3_hit": any(h in c["ok"] for h in hyps[:3]),
            "questions": asked, "ended": r["type"], "secs": round(time.time() - t0, 1), "dialogue": dialogue}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--name", default="", help="run name, so a new run does not resume an old one (e.g. run2)")
    ap.add_argument("--cases", default="test", choices=["test", "practice"], help="practice = the 15 development cases (data/practice_cases.json)"); a = ap.parse_args()
    tag = "_stub" if STUB else ("" if LLM_MODEL == "qwen2.5:7b-instruct" else "_" + re.sub(r"[^a-z0-9]+", "-", LLM_MODEL.lower()).strip("-"))
    if a.name: tag += "_" + a.name
    raw = OUT / f"dialogue_results{tag}.jsonl"; done = {json.loads(l)["case"] for l in open(raw)} if raw.exists() else set()
    # the test set gives the symptom; the ground-truth text is read for the simulator only
    from openpyxl import load_workbook
    ws = load_workbook((E.A / "evaluation" if (E.A / "evaluation").exists() else E.A.parent / "evaluation") / "Test_Set_v2.xlsx", read_only=True)["Test_Cases"]; rows = list(ws.iter_rows(values_only=True))
    extra = {r[0]: {"gt_component": r[5] or "", "gt_cause": r[6] or ""} for r in rows[1:]}
    C = cases()
    if a.cases == "practice":   # development cases, same protocol (the language model plays the technician)
        P = json.loads((E.A / "data" / "practice_cases.json").read_text(encoding="utf-8"))
        C = [{"id": p["id"], "type": "Practice (real)", "symptom": p["opener"], "unseen": False, "primary": p["part"], "ok": set(p.get("ok", [p["part"]]))} for p in P]
        extra = {p["id"]: {"gt_component": p["part"], "gt_cause": p.get("cause", "")} for p in P}
    if a.limit: C = C[:a.limit]
    E._load()
    for c in C:
        if c["id"] in done: continue
        c.update(extra.get(c["id"], {"gt_component": "", "gt_cause": ""}))
        for attempt in (1, 2):
            try: rec = run_case(c); break
            except Exception as e: print(f"{c['id']} attempt {attempt} failed: {e}"); rec = None; time.sleep(20)
        if rec is None: continue
        open(raw, "a", encoding="utf-8").write(json.dumps(rec) + "\n")
        print(f"{c['id']}: named {rec['named']} (truth {c['primary']}) {'TOP1' if rec['top1'] else ('top3' if rec['top3_hit'] else 'miss')} "
              f"after {rec['questions']} questions, {rec['secs']} s")
    res = [json.loads(l) for l in open(raw, encoding="utf-8")]
    rows = []
    for name, f in [("all", lambda r: True), ("practice (development)", lambda r: r["type"].startswith("Practice")), ("real community cases", lambda r: r["type"].startswith("Real")), ("constructed", lambda r: r["type"] == "Constructed"),
                    ("unseen (not in guide)", lambda r: r["unseen"])]:
        S = [r for r in res if f(r)]
        if not S: continue
        q = sum(r["questions"] for r in S) / len(S); t = sum(r["secs"] for r in S) / len(S)
        rows.append([name, len(S), *wilson(sum(r["top1"] for r in S), len(S)), *wilson(sum(r["top3_hit"] for r in S), len(S)), round(q, 2), round(t, 1),
                     *wilson(sum(r.get("within1check", False) for r in S), len(S))])
    with open(OUT / f"dialogue_summary{tag}.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["subset", "n", "top1", "top1_lo95", "top1_hi95", "top3", "top3_lo95", "top3_hi95", "mean_questions", "mean_secs", "within1check", "w1c_lo95", "w1c_hi95"]); w.writerows(rows)
    for r in rows: print(r)
