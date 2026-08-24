#!/usr/bin/env python3
# Convert LDMX ldmx-sw tracker hits -> event-display JSON, carrying track_id and
# flagging stereo duplicates so the bend-plane view doesn't falsely "fork".
#
#   pip install uproot awkward
#   python root_to_events.py events.root --nevents 200 --out events.json
#   python root_to_events.py events.root --source sim --out events_sim.json
#
# digi (default): measured hits + uncertainties (cov_uu/cov_vv). Coords are stored
#   rotated vs global frame (verified vs SimHits): meas_x_=z, meas_y_=x, meas_z_=y.
# sim: truth hits, global frame, includes track_id/pdg for particle-level coloring.

import argparse, json, math
import uproot

parser = argparse.ArgumentParser()
parser.add_argument("infile", help="Input ROOT file")
parser.add_argument("--tree", default="LDMX_Events",
                    help="ROOT tree/key name (default: LDMX_Events)")
parser.add_argument("--nevents", type=int, default=100,
                    help="Number of events to convert (default: 100)")
parser.add_argument("--source", choices=["digi", "sim"], default="digi",
                    help="Hit source: digi or sim (default: digi)")
parser.add_argument("--out", default="events.json",
                    help="Output JSON file (default: events.json)")
args = parser.parse_args()

f = uproot.open(args.infile)
tkey = next((k for k in f.keys() if k.split(";")[0] == args.tree), None)
if tkey is None:
    raise SystemExit(f"Tree {args.tree} not found.")
t = f[tkey]
n = min(args.nevents, t.num_entries)
print(f"Reading {n} of {t.num_entries} events from {tkey}  (source={args.source})")

if args.source == "digi":
    COLLS = {"tag": "DigiTaggerSimHits_test", "recoil": "DigiRecoilSimHits_test"}
    HAS_COV = True
else:
    #COLLS = {
    #"tag": "TaggerSimHits_tm_at_ldmx_signal",
    #"recoil": "RecoilSimHits_tm_at_ldmx_signal"
    #}
    COLLS = {
    "tag": "TaggerSimHits_tm_at_ldmx_continuum",
    "recoil": "RecoilSimHits_tm_at_ldmx_continuum"
    }
    HAS_COV = False

def arr(coll, comp):
    return t[f"{coll}/{coll}.{comp}"].array(entry_stop=n)

def has_branch(coll, comp):
    return f"{coll}/{coll}.{comp}" in t

data = {}
for kind, coll in COLLS.items():
    lys = arr(coll, "layer_id_")
    if HAS_COV:
        gz = arr(coll, "meas_x_"); gx = arr(coll, "meas_y_"); gy = arr(coll, "meas_z_")
        cuu = arr(coll, "cov_uu_"); cvv = arr(coll, "cov_vv_")
    else:
        gx = arr(coll, "x_"); gy = arr(coll, "y_"); gz = arr(coll, "z_")
    # track_id present on sim hits; digi has track_ids_ (a list per hit)
    tid = arr(coll, "track_id_") if has_branch(coll, "track_id_") else None
    pid = arr(coll, "pdg_id_")   if has_branch(coll, "pdg_id_")   else None

    per_event = []
    for i in range(n):
        ev = []
        for j in range(len(gx[i])):
            h = {"z": float(gz[i][j]), "x": float(gx[i][j]), "y": float(gy[i][j]),
                 "layer": int(lys[i][j]), "tracker": kind}
            if tid is not None:
                h["track_id"] = int(tid[i][j])
            if pid is not None:
                h["pdg"] = int(pid[i][j])
            if HAS_COV:
                h["sx"] = math.sqrt(abs(float(cuu[i][j])))
                h["sy"] = math.sqrt(abs(float(cvv[i][j])))
            ev.append(h)

        # Flag stereo duplicates: for each (track_id, layer) keep ONE primary hit
        # for the bend-plane line; mark the rest as stereo partners (still drawn faint).
        seen = {}
        for h in ev:
            key = (h.get("track_id", -1), h["layer"], h["tracker"])
            if key not in seen:
                h["primary"] = True
                seen[key] = h
            else:
                h["primary"] = False   # stereo partner / duplicate measurement
        per_event.append(ev)
    data[kind] = per_event

events = []
for i in range(n):
    hits = data["tag"][i] + data["recoil"][i]
    events.append({"hits": hits, "track": None})

with open(args.out, "w") as fout:
    json.dump({"events": events, "has_uncertainty": HAS_COV}, fout)

ntag = sum(len(data["tag"][i]) for i in range(n))
nrec = sum(len(data["recoil"][i]) for i in range(n))
has_tid = any("track_id" in h for h in events[0]["hits"]) if events else False
print(f"Wrote {len(events)} events to {args.out} ({ntag} tagger + {nrec} recoil hits)")
print(f"  track_id present: {has_tid}   uncertainties: {HAS_COV}")
if not has_tid:
    print("  NOTE: this source has no per-hit track_id, so the display can't color by")
    print("        particle (all hits one color). Use '--source sim' for track-colored views.")
