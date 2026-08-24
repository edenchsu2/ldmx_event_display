#!/usr/bin/env python3
# Check whether the sim JSON actually carries pdg on its hits.
#   python check_pdg.py events_sim.json --event 21
import json, argparse
p = argparse.ArgumentParser()
p.add_argument("jsonfile")
p.add_argument("--event", type=int, default=21)   # 1-based
args = p.parse_args()
d = json.load(open(args.jsonfile))
evs = d["events"] if isinstance(d, dict) else d
ev = evs[args.event - 1]
hits = ev["hits"]
has_pdg = any("pdg" in h for h in hits)
has_tid = any("track_id" in h for h in hits)
print(f"{args.jsonfile}  event {args.event}: {len(hits)} hits")
print(f"  has track_id: {has_tid}")
print(f"  has pdg:      {has_pdg}")
if has_pdg:
    # show pdg per track
    from collections import defaultdict
    d2 = defaultdict(set)
    for h in hits:
        if "track_id" in h and "pdg" in h:
            d2[h["track_id"]].add(h["pdg"])
    for tid in sorted(d2):
        print(f"    track {tid}: pdg codes {sorted(d2[tid])}")
    print("\n  -> JSON HAS pdg. If the legend still lacks (e-/e+), the DISPLAY code is stale.")
else:
    print("\n  -> JSON has NO pdg. Regenerate it: the converter that wrote this file")
    print("     predates the pdg change, OR the running converter lacks the pdg edit.")
