#!/usr/bin/env python3
# Figure out how signal vs background is encoded in this file, before labeling.
# Checks: A'/dark-brem truth branches (signal by construction) and veto/trigger
# decisions (reconstructed). Prints what's filled for the first several events.
#
#   python check_signal.py events.root --nevents 10

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
keys = set(t.keys())

def try_read(name):
    # find a branch whose name contains `name`
    hit = next((k for k in keys if name in k), None)
    if hit is None: return None, None
    try:
        return hit, t[hit].array(entry_stop=n)
    except Exception as e:
        return hit, f"<unreadable: {e}>"

print(f"Events checked: {n}\n")

print("=== SIGNAL TRUTH candidates (A' / dark brem) ===")
for nm in ["APrimeEnergy", "APrimePz", "DarkBremZ", "DarkBremVertexMaterial"]:
    br, arr = try_read(nm)
    if br is None:
        print(f"  {nm}: (branch not found)")
        continue
    if isinstance(arr, str):
        print(f"  {br}: {arr}")
        continue
    # per-event: is it filled / nonzero?
    def summ(a):
        try:
            v = ak.to_numpy(ak.fill_none(a, 0))
            return [float(x) for x in v[:n]]
        except Exception:
            return [len(x) if hasattr(x,'__len__') else x for x in a[:n]]
    print(f"  {br}: {summ(arr)}")

print("\n=== RECONSTRUCTED DECISIONS (veto / trigger) ===")
for nm in ["TrackerVeto_test/passes_veto_", "EcalVeto_test/passes_veto_",
           "HcalVeto_test/passes_veto_", "Trigger_test/pass_"]:
    br, arr = try_read(nm)
    if br is None:
        print(f"  {nm}: (not found)")
        continue
    if isinstance(arr, str):
        print(f"  {br}: {arr}")
        continue
    try:
        vals = [bool(x) for x in ak.to_numpy(ak.flatten(arr, axis=None))[:n]]
    except Exception:
        vals = list(arr[:n])
    print(f"  {br}: {vals}")

print("\nGuide:")
print("  - A'/darkbrem branches filled/nonzero -> this is a SIGNAL sample (dark photon events)")
print("  - all zero/empty -> likely a BACKGROUND sample")
print("  - veto 'passes_veto' = the analysis' decision (reconstructed), not truth")
