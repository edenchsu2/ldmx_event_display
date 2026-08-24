#!/usr/bin/env python3
# Show which JSON files exist and what event 21 looks like in EACH, so we can see
# which file the SIM window is actually drawing (its track_ids should identify it).
#   python which_files.py --event 21
import glob, json, argparse
p = argparse.ArgumentParser()
p.add_argument("--event", type=int, default=21)
args = p.parse_args()
e = args.event

files = sorted(glob.glob("*.json"))
print(f"JSON files in this folder: {files}\n")
for fn in files:
    try:
        d = json.load(open(fn))
        evs = d["events"] if isinstance(d, dict) else d
        has_unc = d.get("has_uncertainty", "?") if isinstance(d, dict) else "?"
        if e < len(evs):
            hits = evs[e]["hits"]
            tids = sorted(set(h.get("track_id", "MISSING") for h in hits))
            print(f"  {fn:28s} n={len(evs):4d}  has_uncertainty={has_unc}  "
                  f"event {e}: {len(hits)} hits, track_ids={tids}")
        else:
            print(f"  {fn:28s} n={len(evs)}  (event {e} out of range)")
    except Exception as ex:
        print(f"  {fn:28s} ERROR: {ex}")

print("\nThe file whose event-21 track_ids = [1,12,557,558] is what the SIM window is drawing.")
print("If that's NOT events_sim.json, the launcher is loading the wrong file.")
