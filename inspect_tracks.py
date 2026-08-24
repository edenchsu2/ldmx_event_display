#!/usr/bin/env python3
# Dump track_id / pdg_id for tracker hits in one event, so we can tell:
#   - a layer's multiple hits = same particle (clustering) vs different (secondary)
#   - recoil "splitting" = one track vs multiple particles (and if a positron -> pair production)
#
#   python inspect_tracks.py events.root --event 0

import argparse, uproot
from collections import Counter, defaultdict

PDG = {11: "e-", -11: "e+", 22: "photon", 13: "mu-", -13: "mu+",
       2112: "neutron", 2212: "proton", 211: "pi+", -211: "pi-"}
def name(p): return PDG.get(int(p), f"pdg{int(p)}")

p = argparse.ArgumentParser()
p.add_argument("infile")
p.add_argument("--event", type=int, default=1,
                   help="1-based event number, matching the display's 'Event N'")
p.add_argument("--tree", default="LDMX_Events")
args = p.parse_args()

f = uproot.open(args.infile)
tkey = next(k for k in f.keys() if k.split(";")[0] == args.tree)
t = f[tkey]
e = args.event - 1   # --event is 1-based (matches display); convert to 0-based index

def grab(coll, comp):
    return t[f"{coll}/{coll}.{comp}"].array(entry_start=e, entry_stop=e+1)[0]

for coll in ["TaggerSimHits_test", "RecoilSimHits_test"]:
    x = grab(coll,"x_"); y = grab(coll,"y_"); z = grab(coll,"z_")
    lay = grab(coll,"layer_id_"); tid = grab(coll,"track_id_"); pid = grab(coll,"pdg_id_")
    print(f"\n{'='*64}\n{coll}  — event {e}  ({len(x)} hits)\n{'='*64}")

    # per-hit table
    print(f"  {'layer':>5} {'track_id':>8} {'pdg':>7} {'x':>8} {'y':>8} {'z':>9}")
    for j in range(len(x)):
        print(f"  {int(lay[j]):>5} {int(tid[j]):>8} {name(pid[j]):>7} "
              f"{float(x[j]):>8.2f} {float(y[j]):>8.2f} {float(z[j]):>9.2f}")

    # summary: how many distinct particles, and hits per track
    tracks = Counter(int(v) for v in tid)
    print(f"\n  distinct track_ids: {len(tracks)}  ->  hits per track: {dict(tracks)}")
    pdgs = Counter(name(v) for v in pid)
    print(f"  particle types present: {dict(pdgs)}")
    # if >1 track, that explains 'splitting'; if a positron present, pair production
    if len(tracks) > 1:
        print(f"  -> multiple particles in this collection (explains spatial splitting)")
    if "e+" in pdgs:
        print(f"  -> positron present: consistent with photon pair-production (e+e-)")

    # layers with >1 hit: same track (cluster) or different (secondary)?
    by_layer = defaultdict(list)
    for j in range(len(x)):
        by_layer[int(lay[j])].append(int(tid[j]))
    multis = {L: tids for L, tids in by_layer.items() if len(tids) > 1}
    if multis:
        print(f"  layers with >1 hit:")
        for L, tids in sorted(multis.items()):
            same = len(set(tids)) == 1
            print(f"    layer {L}: {len(tids)} hits, track_ids={tids} "
                  f"-> {'same particle (clustering)' if same else 'different particles (secondary)'}")
