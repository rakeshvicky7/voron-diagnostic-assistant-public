"""Build the text chunks for arm BP ("B+"): the arm B documents PLUS the machine files that the
component cards (arm C) were built from, added as plain text:
  - firmware configuration (bigtreetech-skr-pico-v1.0.cfg), one chunk per [section], comments kept
  - bill of materials (voron0.2_bom.csv), in groups of rows
  - slicer profiles (*.ini), cut like the other documents
Purpose: C vs BP compares structure with the SAME information available, which B alone did not allow.
Output: data/indexes/chunks_BP.jsonl
Run: python src/build_chunks_bplus.py
"""
import json, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[2]
C = ROOT / "corpus"; IDX = ROOT / "agent/data/indexes"
MAX_WORDS, OVERLAP = 220, 40          # same rule as build_chunks.py

def windows(words):
    if len(words) <= MAX_WORDS:
        yield words; return
    step = MAX_WORDS - OVERLAP
    for i in range(0, len(words), step):
        yield words[i:i + MAX_WORDS]
        if i + MAX_WORDS >= len(words): break

def add(out, source, section, text):
    for k, w in enumerate(windows(text.split())):
        if len(w) >= 8: out.append({"source": source, "section": section, "part": k, "text": f"{section}: " + " ".join(w)})

extra = []
# 1. Firmware configuration: one chunk per [section]
cfg = C / "04_firmware_config/Firmware/bigtreetech-skr-pico-v1.0.cfg"
sec, buf = "header", []
for line in cfg.read_text(encoding="utf-8").splitlines():
    m = re.match(r"^\s*\[(.+?)\]", line)
    if m:
        if buf: add(extra, cfg.name, f"[{sec}]", " ".join(buf))
        sec, buf = m.group(1).strip(), [line.strip()]
    elif line.strip() and not re.fullmatch(r"#+", line.strip()):
        buf.append(line.strip())
if buf: add(extra, cfg.name, f"[{sec}]", " ".join(buf))
# 2. Bill of materials: groups of 15 rows
rows = [r.strip() for r in (C / "03_bom/voron0.2_bom.csv").read_text(encoding="utf-8", errors="ignore").splitlines() if r.strip(" ;")]
for i in range(0, len(rows), 15):
    add(extra, "voron0.2_bom.csv", f"BOM rows {i+1}-{min(i+15, len(rows))}", " | ".join(rows[i:i+15]))
# 3. Slicer profiles
for f in sorted((C / "04_firmware_config/Slicer_Profiles").glob("*.ini")):
    add(extra, f.name, "slicer profile", " ".join(l.strip() for l in f.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip()))

base = [json.loads(l) for l in open(IDX / "chunks_B.jsonl", encoding="utf-8")]
with open(IDX / "chunks_BP.jsonl", "w", encoding="utf-8") as f:
    for i, r in enumerate(base + extra):
        r = dict(r); r["id"] = f"BP{i:05d}"; f.write(json.dumps(r, ensure_ascii=False) + "\n")
print("BP:", len(base), "arm-B chunks +", len(extra), "machine-file chunks =", len(base) + len(extra))
