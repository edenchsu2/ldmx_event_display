#!/usr/bin/env python3
# Diagnose whether tracker hit data looks like real physics or a conversion bug.
# Prints, per event: hit counts, per-layer hit multiplicity, coordinate ranges,
# and flags anything unusual. Also checks the DIGI collections (which carry the
# position uncertainties cov_uu/cov_vv needed for real error bars).
#
#   python diagnose_events.py events.root --nevents 10

import argparse, uproot, awkward as ak
import numpy as np

p = argparse.ArgumentParser()
p.add_argument("infile")
p.add_argument("--tree", default="LDMX_Events")
p.add_argument("--nevents", type=int, default=10)
args = p.parse_args()

f = uproot.open(args.infile)
tkey = next(k for k in f.keys() if k.split(";")[0] == args.tree)
t = f[tkey]
n = min(args.nevents, t.num_entries)

def grab(coll, comp, stop):
    return t[f"{coll}/{coll}.{comp}"].array(entry_stop=stop)

print("="*70)
print("SIM HITS (truth positions) — what the current display uses")
print("="*70)
for coll in ["TaggerSimHits_test", "RecoilSimHits_test"]:
    xs = grab(coll,"x_",n); ys = grab(coll,"y_",n); zs = grab(coll,"z_",n)
    lys = grab(coll,"layer_id_",n)
    allx = ak.flatten(xs); ally = ak.flatten(ys); allz = ak.flatten(zs)
    print(f"\n{coll}:")
    print(f"  hits/event (first {n}): {[len(a) for a in xs]}")
    print(f"  x range: [{ak.min(allx):.1f}, {ak.max(allx):.1f}] mm")
    print(f"  y range: [{ak.min(ally):.1f}, {ak.max(ally):.1f}] mm")
    print(f"  z range: [{ak.min(allz):.1f}, {ak.max(allz):.1f}] mm")
    # per-layer multiplicity in event 0
    if len(lys[0]):
        u, c = np.unique(ak.to_numpy(lys[0]), return_counts=True)
        print(f"  event0 hits per layer_id: {dict(zip(u.tolist(), c.tolist()))}")
        if c.max() > 1:
            print(f"    -> NOTE: some layers have >1 hit (real: clusters/secondaries, or overlapping tracks)")

print("\n" + "="*70)
print("DIGI HITS (measured positions) — these carry uncertainties for error bars")
print("="*70)
for coll in ["DigiTaggerSimHits_test", "DigiRecoilSimHits_test"]:
    try:
        mx = grab(coll,"meas_x_",n); mz = grab(coll,"meas_z_",n)
        cuu = grab(coll,"cov_uu_",n); cvv = grab(coll,"cov_vv_",n)
        allcuu = ak.flatten(cuu)
        print(f"\n{coll}:")
        print(f"  hits/event: {[len(a) for a in mx]}")
        print(f"  cov_uu range: [{ak.min(allcuu):.4g}, {ak.max(allcuu):.4g}]  "
              f"(sigma_u ~ sqrt: [{np.sqrt(ak.min(allcuu)):.4g}, {np.sqrt(ak.max(allcuu)):.4g}] mm)")
    except Exception as e:
        print(f"\n{coll}: could not read ({e})")

print("\n" + "="*70)
print("VERDICT GUIDE:")
print("  - hits/event varying, some layers with >1 hit  -> normal real physics")
print("  - x,z ranges matching detector size (~ hundreds of mm)  -> healthy")
print("  - wildly huge coords, or all zeros, or NaNs  -> would indicate a bug")
print("="*70)
