"""Show, for chosen parts, what the assistant sees (all observations) and how it ranks the parts: helps find knowledge gaps."""
import os, sys
for k, v in {"STUB": "1", "AGENT_PRIOR": "0", "SELF_CHECK": "0", "LEAD": "rules", "KB_MODE": "off"}.items(): os.environ.setdefault(k, v)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dev_eval as D
from assistant_v2.reasoner import NORMAL
D.E._load()
for part in sys.argv[1:]:
    for seed in (100, 101):
        t = D.TwinTech(part, seed); f, m = t.all_observations()
        case = D.E.new_case(); D.E.turn(case, t.opener)
        D.E.turn(case, None, {"facts": {k: v for k, v in f.items() if k != "what_happens"}, "measurements": m, "dont_know": []})
        print(f"\n## {part} ({t.mode}) | {t.opener[:110]}")
        print("   abnormal:", {k: v for k, v in f.items() if v not in NORMAL and k not in ("recent_change", "filament")})
        print("   ranked:  ", [(h["id"], round(h["p"], 2)) for h in case["hyps"][:4]])
        named, hyps, asked, ended, read, c2 = D.dialogue(t); print("   dialogue:", named, asked)
