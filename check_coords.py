#!/usr/bin/env python3
# Print raw x,y,z of the first several hits per collection so we can see which
# coordinate is which and map plot axes correctly (no guessing/normalizing).
#   python check_coords.py events.root

import sys, uproot

f = uproot.open(sys.argv[1] if len(sys.argv) > 1 else "events.root")
tkey = next(k for k in f.keys() if k.split(";")[0] == "LDMX_Events")
t = f[tkey]

for coll, comps in [
    ("TaggerSimHits_test",      ["x_","y_","z_","layer_id_"]),
    ("RecoilSimHits_test",      ["x_","y_","z_","layer_id_"]),
    ("DigiTaggerSimHits_test",  ["meas_x_","meas_y_","meas_z_","layer_id_"]),
    ("DigiRecoilSimHits_test",  ["meas_x_","meas_y_","meas_z_","layer_id_"]),
]:
    print(f"\n=== {coll}  (event 0, first 8 hits) ===")
    arrs = {c: t[f"{coll}/{coll}.{c}"].array(entry_stop=1)[0] for c in comps}
    ncol = comps
    print("  " + "  ".join(f"{c:>10s}" for c in ncol))
    nh = len(arrs[comps[0]])
    for j in range(min(8, nh)):
        row = "  ".join(f"{float(arrs[c][j]):>10.2f}" for c in comps)
        print("  " + row)
