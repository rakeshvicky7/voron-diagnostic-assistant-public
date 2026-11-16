"""Graph RAG for arm G: find where the symptom appears, then walk the failure-propagation graph
upstream to find components that could CAUSE it - especially a shared cause behind several symptoms.

Procedure (fixed in advance, not tuned on the test set):
 1. Seed search  - the same hybrid search as arm C over the component cards gives the TOP_K components
                   whose description best matches the symptom ("where the symptom appears").
 2. Upstream walk - every component that can reach a seed along cause->effect edges within MAX_HOPS
                   is an upstream candidate.
 3. Ranking      - each upstream candidate gets: sum over the seeds it explains of (seed match 1/rank x
                   0.5 per extra hop), divided by the number of components it can affect in total (specificity).
                   Candidates that explain two or more seeds (a shared cause) are listed first.
                   "configures" / "triggers" edges are not walked further (no propagation through settings).
                   So a candidate that explains several observed components scores higher (a shared cause),
                   while very general hubs such as the configuration or the power supply, which affect
                   everything, do not win by default.
 4. Evidence     - seed cards, then the top upstream candidates with the exact propagation paths.
                   The language model reads this evidence and decides; the graph does not answer by itself.
"""
import json, math, pathlib
from collections import deque
from config import TOP_K, CHAR_BUDGET
A = pathlib.Path(__file__).resolve().parents[1]
MAX_HOPS = 2        # how far upstream to look
# Settings edges are not transitive: the configuration (or a sensor that triggers a macro) can affect a
# component directly, but a fault does not travel "through" the configuration to every other component.
TERMINAL = {"configures", "triggers"}
N_UPSTREAM = 3      # upstream candidates shown in the evidence

class FailureGraph:
    def __init__(self):
        g = json.loads((A / "data/graph/graph.json").read_text(encoding="utf-8"))
        self.nodes, self.edges = g["nodes"], g["edges"]
        self.out = {n: [] for n in self.nodes}; self.inc = {n: [] for n in self.nodes}
        for e in self.edges: self.out[e["src"]].append(e); self.inc[e["dst"]].append(e)
        self.reach = {n: self._down(n) for n in self.nodes}

    def _down(self, n):
        seen, q = {}, deque([(n, 0)])
        while q:
            v, d = q.popleft()
            if d == MAX_HOPS: continue
            for e in self.out[v]:
                if e["dst"] not in seen and e["dst"] != n:
                    seen[e["dst"]] = d + 1
                    if e["rel"] not in TERMINAL: q.append((e["dst"], d + 1))
        return seen                                   # downstream component -> hops

    def path(self, src, dst):
        """Shortest cause->effect path from src to dst as readable text."""
        q, prev = deque([src]), {src: None}
        while q:
            v = q.popleft()
            if v == dst: break
            for e in self.out[v]:
                if e["dst"] not in prev: prev[e["dst"]] = e; q.append(e["dst"])
        if dst not in prev: return ""
        steps, v = [], dst
        while prev[v]: steps.append(prev[v]); v = prev[v]["src"]
        steps.reverse()
        return steps[0]["src"] + "".join(f" --{e['rel']}--> {e['dst']}" for e in steps)

    def upstream(self, seeds):
        """seeds: list of component ids in rank order. Returns ranked upstream candidates."""
        rel = {s: 1.0 / (i + 1) for i, s in enumerate(seeds)}
        cands = []
        for n in self.nodes:
            if n in rel: continue
            explained = [s for s in seeds if s in self.reach[n]]
            if not explained: continue
            # score = how well the candidate explains the observed components, divided by how many
            # components it could affect in total (a fault that affects everything explains nothing specific)
            score = sum(rel[s] * 0.5 ** (self.reach[n][s] - 1) for s in explained) / len(self.reach[n])
            cands.append({"id": n, "explains": explained, "spread": len(self.reach[n]), "score": round(score, 4)})
        # a shared cause (explains two or more of the observed components) comes before a single neighbour
        cands.sort(key=lambda c: (-(len(c["explains"]) >= 2), -c["score"]))
        return cands

def graph_trace(symptom, card_index, cards_by_id, graph, card_text, compact_text):
    seeds = [d["id"] for d in card_index.search(symptom, TOP_K)]
    ups = graph.upstream(seeds)[:N_UPSTREAM]
    parts = ["WHERE THE SYMPTOM MAY APPEAR (best-matching components):"]
    parts += [card_text(cards_by_id[s]) for s in seeds]
    if ups:
        parts.append("POSSIBLE UPSTREAM CAUSES (components whose fault can travel to the ones above; "
                     "a component that explains several of them at once can be a shared cause):")
        for u in ups:
            paths = "; ".join(graph.path(u["id"], s) for s in u["explains"])
            parts.append(f"{compact_text(cards_by_id[u['id']])}\nExplains {len(u['explains'])} of the components above via: {paths}")
    # same total character budget as every other arm; the upstream part is reserved 2,000 characters
    # so that long seed cards cannot push the graph evidence out
    k = parts.index("POSSIBLE UPSTREAM CAUSES (components whose fault can travel to the ones above; "
                    "a component that explains several of them at once can be a shared cause):") if ups else len(parts)
    def fit(blocks, budget):
        out, n = [], 0
        for b in blocks:
            if n + len(b) > budget: out.append(b[:max(0, budget - n)]); break
            out.append(b); n += len(b) + 5
        return out
    up_budget = 2000 if ups else 0
    text = "\n---\n".join(fit(parts[:k], CHAR_BUDGET - up_budget) + fit(parts[k:], up_budget))
    return text[:CHAR_BUDGET], {"seeds": seeds, "upstream": ups}
