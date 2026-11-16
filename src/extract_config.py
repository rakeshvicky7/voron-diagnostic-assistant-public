"""Extract the machine-readable part of the structured model (arm C) from the Klipper config and BOM.

Outputs (in data/kg/):
  parameters.json  - every active setting: section, key, value, inline comment, source file and line
  connections.json - every pin assignment: which component uses which controller-board pin
  components.json  - candidate component list from config sections and the BOM (non-fastener rows)

Mechanical relations (which belt runs over which idler, which fan cools what) are NOT in these files;
they are added by hand from the assembly manual (see data/kg/manual_relations.csv).
Run:  python src/extract_config.py
"""
import csv, json, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]          # .../rag dataset
CFG = ROOT / "corpus/04_firmware_config/Firmware/bigtreetech-skr-pico-v1.0.cfg"
BOM = ROOT / "corpus/03_bom/voron0.2_bom.csv"
OUT = ROOT / "agent/data/kg"

PIN_RE = re.compile(r"[!^~]*(gpio\d+)")

def parse_cfg(path):
    params, section = [], None
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^\[(.+?)\]", line)
        if m:
            section = m.group(1).strip()
            continue
        if section is None or ":" not in line or line.startswith(("gcode", "{%", " ")):
            continue
        body, _, comment = raw.partition("#")
        if ":" not in body:
            continue
        key, _, value = body.partition(":")
        key, value = key.strip(), value.strip()
        if not key or " " in key:          # skips gcode-macro body lines
            continue
        params.append({"section": section, "key": key, "value": value,
                       "comment": comment.strip(), "source": f"{path.name}:{n}"})
    return params

def connections(params):
    out = []
    for p in params:
        if p["key"].endswith("pin") or p["key"] == "pin":
            for pin in PIN_RE.findall(p["value"]):
                out.append({"component": p["section"], "role": p["key"], "board_pin": pin,
                            "raw": p["value"], "source": p["source"]})
    return out

def components(params):
    comps = {p["section"]: {"name": p["section"], "origin": "config", "source": p["source"]} for p in params}
    with BOM.open(encoding="utf-8") as f:
        cat = ""
        for i, row in enumerate(csv.DictReader(f, delimiter=";"), 2):
            cat = row["Category"] or cat
            if cat.lower() == "fasteners":
                continue
            name = row["Description"].strip()
            comps[name] = {"name": name, "origin": "bom", "category": cat, "qty": row["Qty"],
                           "source": f"{BOM.name}:{i}"}
    return list(comps.values())

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    ps = parse_cfg(CFG)
    cs = connections(ps)
    comps = components(ps)
    for name, data in [("parameters", ps), ("connections", cs), ("components", comps)]:
        (OUT / f"{name}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"parameters: {len(ps)}  connections: {len(cs)}  components: {len(comps)}")
