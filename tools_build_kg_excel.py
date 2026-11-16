"""Builds Voron_FMEA_Knowledge_Graph.xlsx from the knowledge files the assistant really uses.
Run from the agent folder:  py -3.12 tools_build_kg_excel.py
"""
import csv, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import ColorScaleRule
from src.fmea.kb_modes import M
from src.fmea.kb_symptoms import S
from src.fmea.kb_fixes import FIX, SAFE
from src.fmea import engine
from src.assistant_v2.extra_parts import EXTRA, EDGES

OUT = "Voron_FMEA_Knowledge_Graph.xlsx"
F = "Arial"
HEAD = PatternFill("solid", start_color="1F4E79")
BAND = PatternFill("solid", start_color="EAF1F8")
thin = Side(style="thin", color="BFBFBF")

kg = json.load(open("data/kg/kg.json", encoding="utf-8"))
parts = dict(kg); parts.update(EXTRA)
used_parts = sorted({m["part"] for m in M})

wb = Workbook()

def sheet(title, headers, rows, widths, wrap=()):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for r in rows: ws.append(list(r))
    for c in ws[1]:
        c.font = Font(name=F, bold=True, color="FFFFFF"); c.fill = HEAD
        c.alignment = Alignment(vertical="center", wrap_text=True)
    for i, row in enumerate(ws.iter_rows(min_row=2), start=2):
        for c in row:
            c.font = Font(name=F, size=10)
            c.alignment = Alignment(vertical="top", wrap_text=(c.column - 1) in wrap)
            c.border = Border(bottom=thin)
            if i % 2 == 0: c.fill = BAND
    for i, w in enumerate(widths, 1): ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = ws.dimensions
    return ws

# 1 Parts
rows = []
for pid in used_parts:
    p = parts.get(pid, {})
    nm = sum(1 for m in M if m["part"] == pid)
    rows.append((pid, p.get("name", pid), p.get("subsystem", ""), p.get("class", ""), p.get("function", ""),
                 f'=COUNTIF(\'4 Failure modes\'!B:B,A{len(rows)+2})', p.get("source", "") if isinstance(p.get("source"), str) else ""))
sheet("1 Parts", ["Part id", "Part name", "Subsystem", "Class", "What it does (function)", "No. of failure modes", "Source"],
      rows, [24, 40, 14, 12, 70, 12, 40], wrap=(1, 4, 6))

# 2 Settings per part
rows = []
for pid in used_parts:
    for prm in parts.get(pid, {}).get("parameters", []):
        rows.append((pid, prm.get("key", ""), str(prm.get("value", "")), prm.get("source", "")))
sheet("2 Part settings", ["Part id", "Setting", "Value", "Source (file:line)"], rows, [24, 36, 36, 40], wrap=(1, 2))

# 3 Pins
con = json.load(open("data/kg/connections.json", encoding="utf-8"))
sheet("3 Board pins", ["Config section", "Role", "Board pin", "Raw value", "Source (file:line)"],
      [(c["component"], c["role"], c["board_pin"], c["raw"], c["source"]) for c in con], [22, 18, 14, 22, 40])

# 4 Failure modes
sheet("4 Failure modes", ["Mode id", "Part id", "What goes wrong", "Prior (how common, 1 = normal)", "How to confirm (check)", "Source", "No. of symptoms"],
      [(m["id"], m["part"], m["name"], m.get("prior", 1.0), m["check"], m["src"], f"=COUNTIF('7 Mode-symptom links'!A:A,A{i+2})")
       for i, m in enumerate(M)], [22, 22, 46, 14, 60, 30, 11], wrap=(2, 4, 5))

# 5 Symptoms
HOWTXT = {"look": "look at it", "listen": "listen", "screen": "read the screen / console", "feel": "feel by hand",
          "test": "simple test action", "measure": "measure (multimeter, app)", "context": "when / what changed"}
sheet("5 Symptoms", ["Symptom id", "Question to the technician", "How noticed", "Meaning", "No. of wordings", "Ask cost", "Used by no. of modes"],
      [(sid, q, how, HOWTXT.get(how, ""), f"=COUNTIF('6 Symptom wordings'!A:A,A{i+2})", engine.COST.get(how, 1.0),
        f"=COUNTIF('7 Mode-symptom links'!C:C,A{i+2})") for i, (sid, (q, how, w)) in enumerate(S.items())],
      [20, 60, 11, 26, 11, 9, 12], wrap=(1,))

# 6 Wordings
sheet("6 Symptom wordings", ["Symptom id", "How people describe it"],
      [(sid, w) for sid, (q, how, ws) in S.items() for w in ws], [20, 70])

# 7 Links
PTXT = {0.9: "almost always", 0.7: "usually", 0.5: "often", 0.3: "sometimes"}
links = [(m["id"], m["part"], s, p) for m in M for s, p in m["s"].items()]
sheet("7 Mode-symptom links", ["Mode id", "Part id", "Symptom id", "P(symptom seen | mode)", "In words"],
      [(a, b, c, p, PTXT.get(p, "")) for a, b, c, p in links], [22, 22, 20, 14, 16])

# 8 Matrix
sids = list(S)
ws = wb.create_sheet("8 Link matrix")
ws.append(["Mode id \\ Symptom id", "Part id"] + sids)
for m in M: ws.append([m["id"], m["part"]] + [m["s"].get(s) for s in sids])
for c in ws[1]:
    c.font = Font(name=F, bold=True, color="FFFFFF", size=9); c.fill = HEAD
    c.alignment = Alignment(text_rotation=90, horizontal="center")
ws["A1"].alignment = Alignment(); ws["B1"].alignment = Alignment()
for row in ws.iter_rows(min_row=2):
    for c in row: c.font = Font(name=F, size=9); c.alignment = Alignment(horizontal="center") if c.column > 2 else Alignment()
ws.column_dimensions["A"].width = 22; ws.column_dimensions["B"].width = 20
for i in range(3, len(sids) + 3): ws.column_dimensions[get_column_letter(i)].width = 4
ws.row_dimensions[1].height = 120; ws.freeze_panes = "C2"
rng = f"C2:{get_column_letter(len(sids)+2)}{len(M)+1}"
ws.conditional_formatting.add(rng, ColorScaleRule(start_type="num", start_value=0, start_color="FFFFFF",
                                                  end_type="num", end_value=1, end_color="2E75B6"))

# 9 Repairs
sheet("9 Repair steps", ["Mode id", "Step no.", "Repair step"],
      [(mid, i, st) for mid, steps in FIX.items() for i, st in enumerate(steps, 1)], [22, 8, 90], wrap=(2,))

# 10 Part links (arm G)
rows = []
with open("data/graph/graph_edges.csv", encoding="utf-8") as f:
    r = csv.reader(f, delimiter=";"); next(r)
    for x in r:
        if x: rows.append((x + [""] * 6)[:6])
for a, b, rel in EDGES: rows.append((a, rel, b, "manual (chat-only part)", "extra_parts.py", ""))
sheet("10 Part links", ["Cause part", "Relation", "Effect part", "How obtained", "Source", "Checked (Y/N)"], rows, [24, 18, 24, 26, 40, 10], wrap=(4,))

# 11 Klipper messages
sheet("11 Klipper messages", ["Error message pattern (regular expression)", "Symptom id(s)"],
      [(pat, ", ".join(sy)) for pat, sy in engine.KLIPPER], [90, 20], wrap=(0,))

# 12 Audit
with open("eval/fmea_source_audit.csv", encoding="utf-8") as f:
    r = csv.reader(f); hdr = next(r); rows = [x for x in r if x]
sheet("12 Source audit", hdr, rows, [22, 22, 46, 34, 14, 28], wrap=(2, 3))

# README
ws = wb["Sheet"]; ws.title = "README"
B = lambda t: Font(name=F, bold=True, size=t)
lines = [
 ("Voron 0.2 FMEA knowledge graph: all data", B(14)),
 ("This workbook holds every piece of data the symptom graph (FMEA) uses. Each sheet is one table. Exported from the project files by tools_build_kg_excel.py.", None),
 ("", None),
 ("Counts (live formulas)", B(11)),
]
for t, f in lines: ws.append([t]); ws.cell(ws.max_row, 1).font = f or Font(name=F, size=10)
counts = [("Parts", "=COUNTA('1 Parts'!A:A)-1", 31), ("Failure modes", "=COUNTA('4 Failure modes'!A:A)-1", 67),
          ("Symptoms", "=COUNTA('5 Symptoms'!A:A)-1", 106), ("Symptom wordings", "=COUNTA('6 Symptom wordings'!A:A)-1", 625),
          ("Mode-symptom links", "=COUNTA('7 Mode-symptom links'!A:A)-1", 348), ("Repair steps", "=COUNTA('9 Repair steps'!A:A)-1", None),
          ("Part links (arm G)", "=COUNTA('10 Part links'!A:A)-1", None), ("Part settings (config, BOM)", "=COUNTA('2 Part settings'!A:A)-1", None),
          ("Modes in the source audit", "=COUNTA('12 Source audit'!A:A)-1", None)]
ws.append(["Item", "Count", "Expected (thesis)"])
for c in ws[ws.max_row]: c.font = Font(name=F, bold=True, color="FFFFFF"); c.fill = HEAD
for n, fml, exp in counts:
    ws.append([n, fml, exp]); [setattr(c, "font", Font(name=F, size=10)) for c in ws[ws.max_row]]
ws.append([])
text = [
 ("Sheets", True),
 ("1 Parts: the 31 parts that can cause a fault and what each one does.", False),
 ("2 Part settings: the settings linked to each part (printer.cfg values, BOM items).", False),
 ("3 Board pins: which controller pin each part uses (from printer.cfg).", False),
 ("4 Failure modes: how each part can break, how common it is (prior), how to confirm it, and the source.", False),
 ("5 Symptoms: what a technician can notice, the question the assistant asks, and how it is noticed.", False),
 ("6 Symptom wordings: the different ways people describe each symptom (used to match the user's text).", False),
 ("7 Mode-symptom links: THE GRAPH. Each row is one arrow: failure mode -> symptom, with its probability P.", False),
 ("8 Link matrix: the same links as a table (rows = modes, columns = symptoms, darker = stronger).", False),
 ("9 Repair steps: numbered repair steps for each failure mode.", False),
 ("10 Part links: how parts affect each other (used by arm G, the part graph).", False),
 ("11 Klipper messages: exact Klipper error texts mapped to symptoms.", False),
 ("12 Source audit: each failure mode checked against the documents.", False),
 ("", False),
 ("Probability scale (sheet 7)", True),
 ("0.9 = almost always seen, 0.7 = usually, 0.5 = often, 0.3 = sometimes.", False),
 ("Engine settings (src/fmea/engine.py)", True),
 (f"Leak (symptom seen although the mode does not list it): {engine.LEAK_DEFAULT}; for 'context' symptoms: {engine.LEAK['context']}", False),
 (f"Bonus when the user names a part directly (MENTION_BONUS): {engine.MENTION_BONUS}", False),
 (f"Arm G boost for its ranks 1-3 (G_W): {', '.join(str(x) for x in engine.G_W)}", False),
 (f"Part score = {engine.AGG} of its failure-mode scores. Ask cost per 'how noticed' type is in sheet 5.", False),
 ("Source codes (sheet 4)", True),
 ("BOM = parts list (voron0.2_bom.csv); CFG = printer config (bigtreetech-skr-pico-v1.0.cfg); MAN = assembly manual; DOC = docs.vorondesign.com;", False),
 ("KLP = Klipper documentation; LDO = LDO motor/kit docs; BMG = BMG extruder docs; PHY = physical reasoning (stated).", False),
 ("How it was made", True),
 ("Parts, settings and pins were extracted by script from the documents. Failure modes, symptoms, P values and repairs were drafted with AI assistance (Claude) from the documents, then checked: see sheet 12.", False),
 ("To build your own: fill sheets 1, 4, 5, 6 and 7 for a new machine. A small script then reads them into the graph.", False),
 ("Safety note used before every repair", True),
 (SAFE, False),
]
for t, bold in text:
    ws.append([t]); ws.cell(ws.max_row, 1).font = Font(name=F, bold=bold, size=11 if bold else 10)
ws.column_dimensions["A"].width = 34; ws.column_dimensions["B"].width = 12; ws.column_dimensions["C"].width = 18
wb.move_sheet("README", offset=-len(wb.sheetnames))
wb.save(OUT)
print("saved", OUT, len(M), "modes", len(S), "symptoms", sum(len(v[2]) for v in S.values()), "wordings", len(links), "links", len(used_parts), "parts")
