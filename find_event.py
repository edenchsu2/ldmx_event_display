#!/usr/bin/env python3
# Find which event index in the JSON actually contains a given track_id.
# The SIM window shows tracks 557/558 labeled "event 21" -- find where 557/558
# REALLY live, to see if the display is mis-indexing.
#   python find_event.py events_sim.json --tid 557
import json, argparse
p = argparse.ArgumentParser()
p.add_argument("jsonfile")
p.add_argument("--tid", type=int, default=557)
args = p.parse_args()

d = json.load(open(args.jsonfile))
evs = d["events"] if isinstance(d, dict) else d
print(f"{args.jsonfile}: {len(evs)} events; searching for track_id {args.tid}\n")

found = []
for i, ev in enumerate(evs):
    tids = set(h.get("track_id") for h in ev["hits"])
    if args.tid in tids:
        found.append((i, sorted(t for t in tids if t is not None)))

if found:
    for i, tids in found[:20]:
        print(f"  event index {i}: track_ids = {tids}")
    print(f"\n-> track {args.tid} appears in {len(found)} event(s). "
          f"If the display shows it under 'event 21' but it's really at another index,\n"
          f"   the display is mis-indexing (drawing event X, labeling it 21).")
else:
    print(f"  track {args.tid} appears in NO event in this file.")
    print(f"  -> then the window is not reading this file at all.")

# Also: what does index 21 actually contain here?
print(f"\n  For reference, event index 21 in this file: "
      f"{sorted(t for t in set(h.get('track_id') for h in evs[21]['hits']) if t is not None)}")
