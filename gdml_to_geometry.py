#!/usr/bin/env python3
"""
Parse LDMX tracker GDML into a geometry.json of real sensor rectangles (global mm).

Reads constants.gdml (numbers), detector.gdml (envelope world positions), and
tagger.gdml / recoil.gdml (per-sensor placement), resolves all variables and
expressions, and writes each silicon sensor's global center (x,y,z), size, and
stereo angle.

    python gdml_to_geometry.py --gdml-dir /path/to/gdml --out geometry.json

Verified against constants.gdml values (stereo_angle=5.7296 deg, etc.).
"""
import argparse, json, re, os, math
import xml.etree.ElementTree as ET

ap = argparse.ArgumentParser()
ap.add_argument("--gdml-dir", default=".", help="folder with the .gdml files")
ap.add_argument("--out", default="geometry.json")
args = ap.parse_args()

D = args.gdml_dir

# ---------------------------------------------------------------------------
# 1. Build a symbol table from constants.gdml (and the <define> in detector.gdml)
#    Handles <constant>, <variable> (scalars) and <matrix> (arrays).
#    Values are expressions in terms of other symbols; we evaluate them safely.
# ---------------------------------------------------------------------------

# unit words that appear in GDML expressions -> multiplicative factors (mm base)
UNITS = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "deg": 1.0, "rad": 180.0/math.pi}

scalars = {}      # name -> float
matrices = {}     # name -> list[float]  (flat) with coldim stored separately
matrix_cols = {}  # name -> coldim

def strip_comments(text):
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

def read_defines(path):
    """Yield (kind, name, attrib) for constant/variable/matrix definitions.
    Handles both files with a <define>...</define> wrapper (detector.gdml) and
    entity-include files that are bare lists of <constant>/<variable>/<matrix>
    with no wrapper (constants.gdml)."""
    raw = strip_comments(open(path).read())
    blocks = re.findall(r"<define>(.*?)</define>", raw, flags=re.DOTALL)
    if not blocks:
        blocks = [raw]   # constants.gdml: no wrapper, scan whole file
    for block in blocks:
        for tag in ("constant", "variable", "matrix"):
            # match <tag ...> ... </tag>  OR self-closing <tag ... />
            for em in re.finditer(rf"<{tag}\b([^>]*?)/?>", block):
                attrs = dict(re.findall(r'(\w+)\s*=\s*"([^"]*)"', em.group(1)))
                if attrs.get("name"):
                    yield tag, attrs.get("name"), attrs

def expr_eval(expr, symbols):
    """Evaluate a GDML numeric expression using known symbols and unit words."""
    if expr is None:
        return None
    e = " ".join(expr.split())   # collapse newlines/indentation to single spaces
    # replace unit tokens (mm, cm, m, deg) used multiplicatively: '4.0*cm', '15*mm'
    # turn standalone unit words into their factor
    def repl_unit(tok):
        return str(UNITS[tok])
    # tokenize-ish: replace whole-word units
    e = re.sub(r"\b(mm|cm|m|deg|rad)\b", lambda mo: repl_unit(mo.group(1)), e)
    # matrix element access name[i] or name[i, j] -> value
    def repl_index(mo):
        nm, idx = mo.group(1), mo.group(2)
        parts = [int(p) for p in idx.split(",")]
        if nm in matrices:
            cols = matrix_cols.get(nm, 1)
            if len(parts) == 1:
                return repr(matrices[nm][parts[0]-1])           # 1-based
            else:
                r, c = parts
                return repr(matrices[nm][(r-1)*cols + (c-1)])   # 1-based row,col
        raise KeyError(nm)
    e = re.sub(r"(\w+)\s*\[\s*([\d,\s]+)\]", repl_index, e)
    # now substitute scalar symbol names with their values (longest first)
    for nm in sorted(symbols, key=len, reverse=True):
        e = re.sub(rf"\b{re.escape(nm)}\b", repr(symbols[nm]), e)
    # what remains should be pure arithmetic
    return eval(e, {"__builtins__": {}}, {})

# read constants.gdml then detector.gdml defines (order matters; resolve iteratively)
pending = []
for f in ["constants.gdml", "detector.gdml", "tagger.gdml", "recoil.gdml"]:
    p = os.path.join(D, f)
    if not os.path.exists(p):
        continue
    for kind, name, attrs in read_defines(p):
        if name is None:
            continue
        pending.append((kind, name, attrs))

# iteratively resolve (some depend on later-defined names)
for _ in range(20):
    progress = False
    still = []
    for kind, name, attrs in pending:
        try:
            if kind in ("constant", "variable"):
                if name in scalars:
                    continue
                val = expr_eval(attrs.get("value"), scalars)
                scalars[name] = float(val); progress = True
            elif kind == "matrix":
                if name in matrices:
                    continue
                cols = int(attrs.get("coldim", "1"))
                vals = [expr_eval(tok, scalars)
                        for tok in attrs.get("values", "").split()]
                matrices[name] = [float(v) for v in vals]
                matrix_cols[name] = cols; progress = True
        except (KeyError, NameError, TypeError):
            still.append((kind, name, attrs))
    pending = still
    if not pending or not progress:
        break

def S(name):  # scalar accessor
    return scalars[name]

print(f"Resolved {len(scalars)} scalars, {len(matrices)} matrices")
for k in ["stereo_angle","si_sensor_dx","si_sensor_dy","si_large_sensor_dx",
          "si_large_sensor_dy","tagger_envelope_dz","recoil_envelope_dz",
          "tagger_layer_delta","tagger_layer_offset","recoil_l14_sensor_sep",
          "recoil_delta_l14","recoil_delta_l45","recoil_delta_l56",
          "tracker_envelope_clearance"]:
    if k in scalars:
        print(f"   {k} = {scalars[k]:.4f}")

# envelope world positions (from detector.gdml)
tagger_pos_z = S("tagger_pos_z")
recoil_pos_z = S("recoil_pos_z")
print(f"   tagger_pos_z = {tagger_pos_z:.3f}   recoil_pos_z = {recoil_pos_z:.3f}")

# ---------------------------------------------------------------------------
# 2. Compute sensor placements (local), then add envelope offset -> global z.
# ---------------------------------------------------------------------------
sensors = []

# ---- TAGGER: 7 layers, axial + stereo, from tagger.gdml formulas ----
tagger_layer_x = matrices["tagger_layer_x"]
tenv_down = S("tagger_envelope_dz")/2
tl7_mid = tenv_down - S("tracker_envelope_clearance")
tagger_layer_z_local = [tl7_mid - k*S("tagger_layer_delta") for k in range(7)]
tagger_rot = matrices["tagger_rot"]
off = S("tagger_layer_offset")
for i in range(7):
    xz = tagger_layer_x[i]
    zc = tagger_layer_z_local[i]
    for kind, zoff, rot in [("axial", -off, 0.0), ("stereo", +off, tagger_rot[i])]:
        sensors.append({
            "subsystem": "tagger", "layer": i+1, "kind": kind,
            "x": xz, "y": 0.0,
            "z": tagger_pos_z + (zc + zoff),   # global z
            "dx": S("si_sensor_dx"), "dy": S("si_sensor_dy"),
            "stereo_deg": rot,
        })

# ---- RECOIL L1-4: axial + stereo pairs ----
renv_up = -S("recoil_envelope_dz")/2
recoil_l1_z = renv_up + S("tracker_envelope_clearance")
recoil_l14_z_local = [recoil_l1_z + k*S("recoil_delta_l14") for k in range(4)]
recoil_l14_rot = matrices["recoil_l14_rot"]
sep14 = S("recoil_l14_sensor_sep")
for i in range(4):
    zc = recoil_l14_z_local[i]
    for kind, zoff, rot in [("axial", -sep14, 0.0), ("stereo", +sep14, recoil_l14_rot[i])]:
        sensors.append({
            "subsystem": "recoil", "layer": i+1, "kind": kind,
            "x": 0.0, "y": 0.0,
            "z": recoil_pos_z + (zc + zoff),
            "dx": S("si_large_sensor_dx"), "dy": S("si_large_sensor_dy"),
            "stereo_deg": rot,
        })

# ---- RECOIL L5-6: axial-only 10-sensor xy grid each ----
recoil_l56_xy = matrices["recoil_l56_xy"]  # flat, coldim 2
l5_mid = recoil_l1_z + 3*S("recoil_delta_l14") + S("recoil_delta_l45")
l6_mid = l5_mid + S("recoil_delta_l56")
sep56 = S("recoil_l56_sensor_sep")
# per-sensor z alternation pattern from recoil.gdml (+,-,+,-,+,+,-,+,-,+)
patt = [+1,-1,+1,-1,+1,+1,-1,+1,-1,+1]
for layer_name, mid in [("L5", l5_mid), ("L6", l6_mid)]:
    for k in range(10):
        xk = recoil_l56_xy[k*2 + 0]
        yk = recoil_l56_xy[k*2 + 1]
        zk = mid + patt[k]*sep56
        sensors.append({
            "subsystem": "recoil", "layer": 5 if layer_name=="L5" else 6,
            "kind": "axial",
            "x": xk, "y": yk,
            "z": recoil_pos_z + zk,
            "dx": S("si_large_sensor_dx"), "dy": S("si_large_sensor_dy"),
            "stereo_deg": 0.0,
        })

# target
sensors_meta = {
    "target_z": S("target_z") if "target_z" in scalars else 0.0,
    "stereo_angle_deg": S("stereo_angle"),
}

out = {"sensors": sensors, "meta": sensors_meta}
json.dump(out, open(args.out, "w"), indent=1)

# report global z-ranges to compare against event data
tz = [s["z"] for s in sensors if s["subsystem"]=="tagger"]
rz = [s["z"] for s in sensors if s["subsystem"]=="recoil"]
print(f"\nWrote {len(sensors)} sensors to {args.out}")
print(f"  tagger global z range: [{min(tz):.1f}, {max(tz):.1f}] mm")
print(f"  recoil global z range: [{min(rz):.1f}, {max(rz):.1f}] mm")
print(f"  (compare to event data: tagger -615..-9, recoil +9..+186)")
