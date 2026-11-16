"""Build the text chunks for arm B (Voron documentation as written) and arm D (generic troubleshooting guide).
Same chunking rule for both: split at headings (or PDF page), then cap at MAX_WORDS with overlap.
Output: data/indexes/chunks_B.jsonl, data/indexes/chunks_D.jsonl  (one JSON object per line)
Run: python src/build_chunks.py
"""
import json, re, pathlib, logging
logging.getLogger("pypdf").setLevel(logging.ERROR)
ROOT = pathlib.Path(__file__).resolve().parents[2]
C = ROOT / "corpus"
OUT = ROOT / "agent/data/indexes"
MAX_WORDS, OVERLAP = 220, 40

def windows(words):
    if len(words) <= MAX_WORDS:
        yield words; return
    step = MAX_WORDS - OVERLAP
    for i in range(0, len(words), step):
        yield words[i:i + MAX_WORDS]
        if i + MAX_WORDS >= len(words): break

def split_md(text):
    parts, title, buf = [], "", []
    for line in text.splitlines():
        if re.match(r"^#{1,4} ", line):
            if buf: parts.append((title, " ".join(buf)))
            title, buf = line.lstrip("# ").strip(), []
        elif line.strip() and not line.startswith(("---", "layout:", "title:", "parent:", "nav_order")):
            buf.append(line.strip())
    if buf: parts.append((title, " ".join(buf)))
    return parts

def chunks_from_md(path, rel):
    out = []
    for title, body in split_md(path.read_text(encoding="utf-8", errors="ignore")):
        for k, w in enumerate(windows(body.split())):
            if len(w) < 8: continue
            out.append({"source": rel, "section": title, "part": k, "text": (title + ": " if title else "") + " ".join(w)})
    return out

def chunks_from_pdf(path, rel):
    from pypdf import PdfReader
    out = []
    for n, page in enumerate(PdfReader(str(path)).pages, 1):
        txt = re.sub(r"\s+", " ", page.extract_text() or "").replace("WWW.VORONDESIGN.COM", "").strip()
        for k, w in enumerate(windows(txt.split())):
            if len(w) < 8: continue
            out.append({"source": rel, "section": f"page {n}", "part": k, "text": " ".join(w)})
    return out

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    B = chunks_from_pdf(C / "02_assembly_manual/VORON_V0.2r1_Assembly_Manual.pdf", "VORON_V0.2r1_Assembly_Manual.pdf")
    for f in sorted((C / "01_machine_docs").rglob("*.md")):
        B += chunks_from_md(f, str(f.relative_to(C)))
    D = chunks_from_md(C / "05_fault_corpus/3D-Printer-Troubleshooting-Guide-Markdown.md", "3D-Printer-Troubleshooting-Guide-Markdown.md")
    for name, rows in [("B", B), ("D", D)]:
        with open(OUT / f"chunks_{name}.jsonl", "w", encoding="utf-8") as f:
            for i, r in enumerate(rows):
                r["id"] = f"{name}{i:05d}"; f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(name, len(rows), "chunks,", sum(len(r["text"].split()) for r in rows), "words")
