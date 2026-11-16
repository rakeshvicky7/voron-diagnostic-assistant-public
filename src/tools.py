"""The three agent tools. Which knowledge sits behind them depends on the arm."""
import json, pathlib
from retrieval import HybridIndex
from config import TOP_K, CHAR_BUDGET
A = pathlib.Path(__file__).resolve().parents[1]; IDX = A / "data/indexes"

def load_jsonl(p): return [json.loads(l) for l in open(p, encoding="utf-8")]

def card_text(c, hide_id=False):
    lines = [f"COMPONENT {c['name']} - {c['function']}" if hide_id else f"COMPONENT {c['id']} ({c['name']}) - {c['function']}"]
    if c["parameters"]: lines.append("Correct values: " + "; ".join(f"{p['key']} = {p['value']} [{p['source']}]" for p in c["parameters"]))
    if c["connections"]: lines.append("Board pins: " + "; ".join(f"{x['role']} -> {x['board_pin']}" for x in c["connections"]))
    if c["related"]:
        rel = c["related"]
        if hide_id:
            import runpy
            names = {k: v["name"] for k, v in runpy.run_path(str(A / "data/kg/components.yaml.py"))["COMPONENTS"].items()}
            rel = [" ".join(names.get(w, w.replace("_", " ")) for w in r.split()) for r in rel]
        lines.append("Links: " + "; ".join(rel))
    lines += [f"Failure mode: {f['mode']} | symptom: {f['symptom']} | check: {f['check']}" for f in c["failure_modes"]]
    lines.append(f"Source: {c['source']}")
    return "\n".join(lines)

def compact_text(c):
    """Short card used for upstream candidates in arm G: identity, function, failure modes."""
    lines = [f"COMPONENT {c['id']} ({c['name']}) - {c['function']}"]
    lines += [f"Failure mode: {f['mode']} | symptom: {f['symptom']} | check: {f['check']}" for f in c["failure_modes"]]
    return "\n".join(lines)

def clip(blocks):
    out, n = [], 0
    for b in blocks:
        if n + len(b) > CHAR_BUDGET: out.append(b[:max(0, CHAR_BUDGET - n)]); break
        out.append(b); n += len(b)
    return "\n---\n".join(out)

class Toolbox:
    def __init__(self, arm):
        self.arm = arm; self.text = self.graph = None; self.last_graph = None
        if arm in ("B",): self.text = HybridIndex("B", load_jsonl(IDX / "chunks_B.jsonl"), IDX)
        if arm == "BP": self.text = HybridIndex("BP", load_jsonl(IDX / "chunks_BP.jsonl"), IDX)   # B + config, BOM, slicer as text
        if arm in ("D", "E"): self.text = HybridIndex("D", load_jsonl(IDX / "chunks_D.jsonl"), IDX)
        if arm == "G":   # graph RAG: same cards as C for the seed search, plus the failure-propagation graph
            from graph_rag import FailureGraph
            kg = json.loads((A / "data/kg/kg.json").read_text(encoding="utf-8"))
            self.kg = kg; self.fgraph = FailureGraph()
            self.cards = [{"id": k, "text": card_text(v)} for k, v in kg.items()]
            self.graph = HybridIndex("C", self.cards, IDX)
        if arm in ("C", "E", "C2"):
            kg = json.loads((A / "data/kg/kg.json").read_text(encoding="utf-8"))
            hide = arm == "C2"   # robustness check: same cards but without the component ids in the text
            self.cards = [{"id": k, "text": card_text(v, hide)} for k, v in kg.items()]
            self.graph = HybridIndex("C2" if hide else "C", self.cards, IDX)
    def specs(self):
        s = []
        if self.arm == "G": s.append({"type": "function", "function": {"name": "graph_query", "description": "Search the failure-propagation graph of the Voron 0.2: components where a symptom appears, and upstream components whose fault can cause it, with the connecting paths.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}})
        elif self.graph: s.append({"type": "function", "function": {"name": "graph_query", "description": "Search the structured model of the Voron 0.2 (components, functions, correct values, pins, links, failure modes, checks).", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}})
        if self.text: s.append({"type": "function", "function": {"name": "text_search", "description": "Hybrid keyword + semantic search over the document collection.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}})
        if self.arm != "A": s.append({"type": "function", "function": {"name": "ask_technician", "description": "Ask the technician one short question about the machine's state.", "parameters": {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]}}})
        return s
    def call(self, name, args, technician=None):
        q = args.get("query") or args.get("question") or ""
        if name == "graph_query" and self.arm == "G":
            from graph_rag import graph_trace
            text, info = graph_trace(q, self.graph, self.kg, self.fgraph, card_text, compact_text)
            if self.last_graph is None: self.last_graph = info   # keep the first (mandatory) retrieval for the log
            return text
        if name == "graph_query" and self.graph: return clip([d["text"] for d in self.graph.search(q, TOP_K)])
        if name == "text_search" and self.text: return clip([f"[{d['source']} | {d['section']}] {d['text']}" for d in self.text.search(q, TOP_K)])
        if name == "ask_technician": return technician(q) if technician else "The technician has no further information."
        return "Tool not available."
    def first_retrieval(self, symptom):
        """Mandatory first retrieval with the symptom text, so every arm with knowledge uses it at least once."""
        parts = []
        both = bool(self.graph and self.text)      # arm E: split the same budget between the two sources
        if self.graph:
            r = self.call("graph_query", {"query": symptom}); parts.append("graph_query results:\n" + (r[:CHAR_BUDGET // 2] if both else r))
        if self.text:
            r = self.call("text_search", {"query": symptom}); parts.append("text_search results:\n" + (r[:CHAR_BUDGET // 2] if both else r))
        return "\n\n".join(parts)
