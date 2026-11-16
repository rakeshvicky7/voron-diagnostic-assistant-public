"""Prompt formats shared by the training-data generator and the assistant (training and use must match exactly)."""
import json

SYSTEM_LEAD = ("You lead a fault-finding conversation for a Voron 0.2 3D printer. Read the conversation, the engine's "
               "candidates, the cards and the available questions. Ask the most useful question, or name the cause only "
               "when the evidence clearly points to one part. Reply with JSON only.")
SYSTEM_READ = ("You read a technician's description of a Voron 0.2 3D printer fault and list the parts that could cause it, "
               "most likely first, using the cards given. Reply with JSON only.")

def lead_context(case, hyps, cand, KG, Q, compact_text):
    ans = "; ".join(f"{k.replace('_', ' ')}: {v}" for k, v in case["facts"].items() if k != "what_happens")
    cards = "\n".join(compact_text(KG[h["id"]]) for h in hyps[:4])
    qs = "\n".join(f"- {q['id']}: {Q[q['id']]['text']}" for q in cand) or "- none"
    return (f"CONVERSATION: {' | '.join(case['notes'])}\nANSWERS: {ans or 'none'}\nMEASUREMENTS: {json.dumps(case['measurements'])}\n"
            f"COULD NOT ANSWER: {', '.join(case['dont_know']) or 'none'}\n"
            f"CANDIDATES: " + "; ".join(f"{h['id']} {h['p']:.0%}" for h in hyps[:5]) + f"\nCARDS:\n{cards}\nQUESTIONS:\n{qs}")

def read_context(description, card_ids, KG, compact_text):
    return f"DESCRIPTION: {description}\nCARDS:\n" + "\n".join(compact_text(KG[s]) for s in card_ids)
