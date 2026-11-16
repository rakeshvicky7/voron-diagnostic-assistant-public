"""Convert the official Voron 0.2r1 STEP assembly into a web 3D file (GLB) for the virtual printer page.

    py -3.12 -m pip install cadquery-ocp          (once; free OpenCascade for Python, about 200 MB)
    py -3.12 tools\\cad\\convert_step.py tools\\cad\\V0.2R1_Master_Assembly_STEP.zip

What it does
 1. reads the STEP file with OpenCascade, keeping the assembly tree, part names and colours (XDE document)
 2. triangulates every solid (coarse enough for a browser, fine enough to see the parts)
 3. writes src/assistant_v2/static/cad/voron02r1.glb with OpenCascade's own glTF writer (names kept as node names)
 4. writes names.json next to it: every part name in the assembly, used for the mapping to the 31 parts
Takes a few minutes and about 3-6 GB of memory for the full assembly.
"""
import sys, time, json, re, zipfile, pathlib, tempfile
import importlib, pkgutil, OCP

def ocp_class(name, first=("TColStd", "NCollection", "RWGltf", "RWMesh", "TCollection", "Standard")):
    """Find a class in the installed OCP build (Windows and Linux builds put some classes in different modules)."""
    for mod in list(first) + [m.name for m in pkgutil.iter_modules(OCP.__path__)]:
        try:
            m = importlib.import_module("OCP." + mod)
            if hasattr(m, name): return getattr(m, name)
        except Exception: continue
    return None

def ocp_version():
    try:
        from importlib.metadata import version; return version("cadquery-ocp")
    except Exception: return "unknown"

TColStd_IndexedDataMapOfStringString = ocp_class("TColStd_IndexedDataMapOfStringString")
STEPCAFControl_Reader = ocp_class("STEPCAFControl_Reader", ("STEPCAFControl",))
TDocStd_Document = ocp_class("TDocStd_Document", ("TDocStd",))
TCollection_ExtendedString = ocp_class("TCollection_ExtendedString", ("TCollection",))
TCollection_AsciiString = ocp_class("TCollection_AsciiString", ("TCollection",))
BRepMesh_IncrementalMesh = ocp_class("BRepMesh_IncrementalMesh", ("BRepMesh",))
RWGltf_CafWriter = ocp_class("RWGltf_CafWriter", ("RWGltf",))
RWGltf_WriterTrsfFormat = ocp_class("RWGltf_WriterTrsfFormat", ("RWGltf",))
RWMesh_NameFormat = ocp_class("RWMesh_NameFormat", ("RWMesh",))
RWMesh_CoordinateSystem = ocp_class("RWMesh_CoordinateSystem", ("RWMesh",))
Message_ProgressRange = ocp_class("Message_ProgressRange", ("Message",))
IFSelect_RetDone = ocp_class("IFSelect_RetDone", ("IFSelect",))
_missing = [k for k, v in list(globals().items()) if v is None and k[:1].isupper() and k != "TColStd_IndexedDataMapOfStringString"]

A = pathlib.Path(__file__).resolve().parents[2]
OUT = A / "src" / "assistant_v2" / "static" / "cad"

def step_path(p):
    p = pathlib.Path(p)
    if p.suffix.lower() != ".zip": return p
    z = zipfile.ZipFile(p); name = next(n for n in z.namelist() if n.lower().endswith((".step", ".stp")))
    tmp = pathlib.Path(tempfile.gettempdir()) / "voron_step"; tmp.mkdir(exist_ok=True)
    out = tmp / pathlib.Path(name).name
    if not out.exists(): print("unzipping", name); z.extract(name, tmp); (tmp / name).rename(out) if (tmp / name) != out else None
    return out

def step_names(path):
    """All part and assembly names in the STEP file (PRODUCT entities), read as text: fast and version-proof."""
    txt = path.read_text(encoding="latin-1", errors="ignore")
    return sorted({m for m in re.findall(r"PRODUCT\('([^']*)'", txt) if m})

def main(src, deflection=0.5, angle=0.8):
    print(f"cadquery-ocp {ocp_version()}")
    if _missing:
        raise SystemExit(f"This cadquery-ocp build lacks {_missing}. Update it:  py -3.12 -m pip install --upgrade cadquery-ocp")
    t0 = time.time(); path = step_path(src); print(f"reading {path.name} ({path.stat().st_size / 1e6:.0f} MB) ...")
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    r = STEPCAFControl_Reader(); r.SetNameMode(True); r.SetColorMode(True); r.SetLayerMode(False)
    if r.ReadFile(str(path)) != IFSelect_RetDone: raise SystemExit("could not read the STEP file")
    r.Transfer(doc); print(f"  read in {time.time() - t0:.0f} s")
    # triangulate: the reader's shape holds the same solids as the document, so meshing it meshes the document
    shape = r.Reader().OneShape()
    BRepMesh_IncrementalMesh(shape, deflection, False, angle, True)     # absolute deflection in mm
    names = step_names(path)
    print(f"  meshed in {time.time() - t0:.0f} s")
    OUT.mkdir(parents=True, exist_ok=True); glb = OUT / "voron02r1.glb"
    w = RWGltf_CafWriter(TCollection_AsciiString(str(glb)), True)       # True = binary .glb
    w.SetTransformationFormat(RWGltf_WriterTrsfFormat.RWGltf_WriterTrsfFormat_TRS)
    w.SetNodeNameFormat(RWMesh_NameFormat.RWMesh_NameFormat_ProductOrInstance)    # node name = part / assembly name
    w.SetMeshNameFormat(RWMesh_NameFormat.RWMesh_NameFormat_Product)
    if hasattr(w, "SetMergeFaces"): w.SetMergeFaces(True)                         # one mesh per solid, not one per face
    if hasattr(w, "SetParallel"): w.SetParallel(True)
    cs = w.ChangeCoordinateSystemConverter()                                       # STEP is Z-up in mm -> glTF Y-up
    cs.SetInputLengthUnit(0.001); cs.SetInputCoordinateSystem(RWMesh_CoordinateSystem.RWMesh_CoordinateSystem_Zup)
    cs.SetOutputLengthUnit(0.001); cs.SetOutputCoordinateSystem(RWMesh_CoordinateSystem.RWMesh_CoordinateSystem_glTF)
    info = TColStd_IndexedDataMapOfStringString() if TColStd_IndexedDataMapOfStringString else {}   # OCP 8 may take a dict
    try: w.Perform(doc, info, Message_ProgressRange())
    except TypeError:
        raise SystemExit("This cadquery-ocp version has a different glTF writer. Install the tested one:\n"
                         "  py -3.12 -m pip install \"cadquery-ocp==7.9.3.1.1\"\nSignature here: " + str(RWGltf_CafWriter.Perform.__doc__)[:600])
    (OUT / "names.json").write_text(json.dumps(names, indent=1), encoding="utf-8")
    print(f"written {glb} ({glb.stat().st_size / 1e6:.1f} MB), {len(names)} names, {time.time() - t0:.0f} s in total")

if __name__ == "__main__":
    if len(sys.argv) < 2: raise SystemExit(__doc__)
    main(sys.argv[1], *(float(x) for x in sys.argv[2:4]))
