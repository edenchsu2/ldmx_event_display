#!/usr/bin/env python3
# Compare event 21 as stored in the JSON the display reads vs. the ROOT file,
# to locate where the track_id mismatch enters.
#
#   python check_json_vs_root.py events_sim.json events.root --event 21

import argparse, json, uproot

p = argparse.ArgumentParser()
p.add_argument("jsonfile")
p.add_argument("rootfile")
p.add_argument("--event", type=int, default=21)
args = p.parse_args()

e = args.event - 1   # --event is 1-based (matches display); convert to 0-based index

# ---- JSON side (what the display actually drew) ----
d = json.load(open(args.jsonfile))
evs = d["events"] if isinstance(d, dict) else d
print(f"JSON: {args.jsonfile}")
print(f"  total events in file: {len(evs)}")
if e < len(evs):
    hits = evs[e]["hits"]
    tids = sorted(set(h.get("track_id", "MISSING") for h in hits))
    print(f"  event {e}: {len(hits)} hits, track_ids = {tids}")
else:
    print(f"  event {e} out of range!")

# ---- ROOT side (ground truth) ----
f = uproot.open(args.rootfile)
t = f["LDMX_Events"]
print(f"\nROOT: {args.rootfile}  (LDMX_Events, n={t.num_entries})")
for coll in ["TaggerSimHits_test", "RecoilSimHits_test"]:
    br = f"{coll}/{coll}.track_id_"
    if br in t.keys():
        arr = t[br].array(entry_start=e, entry_stop=e+1)[0]
        print(f"  event {e} {coll}: track_ids = {sorted(set(int(v) for v in arr))}")

print("\nIf JSON track_ids != ROOT track_ids for the same event index,")
print("the JSON was built from a DIFFERENT root file (stale/mismatched).")
print("Fix = regenerate the JSON from THIS events.root.")
