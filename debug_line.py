#!/usr/bin/env python3
# Show the exact primary hits the display connects for a given track, in draw order,
# with the x-jump between consecutive ones -- so we can see why the jump guard
# did or didn't break the line.
#   python debug_line.py events_sim.json --event 21 --tid 557
import json, argparse
p = argparse.ArgumentParser()
p.add_argument("jsonfile")
p.add_argument("--event", type=int, default=21)   # 1-based, matches display
p.add_argument("--tid", type=int, default=557)
args = p.parse_args()

d = json.load(open(args.jsonfile))
evs = d["events"] if isinstance(d, dict) else d
ev = evs[args.event - 1]           # 1-based -> 0-based
hits = ev["hits"]

# replicate the display's primary flagging exactly
seen = {}
for h in hits:
    k = (h.get("track_id", -1), h["layer"], h["tracker"])
    h["_primary"] = k not in seen
    seen.setdefault(k, h)

for kind in ("tag", "recoil"):
    line = sorted([h for h in hits
                   if h.get("track_id", -1) == args.tid
                   and h["tracker"] == kind
                   and h["_primary"]],
                  key=lambda h: h["z"])
    if not line:
        continue
    print(f"\ntrack {args.tid} [{kind}] primary hits the line connects (z-order):")
    print(f"  {'layer':>5} {'x':>9} {'z':>8} {'dx from prev':>13}")
    prevx = None
    for h in line:
        dx = "" if prevx is None else f"{h['x']-prevx:+.1f}"
        flag = ""
        if prevx is not None and abs(h["x"]-prevx) > 40:
            flag = "  <-- JUMP >40mm (guard should break here)"
        print(f"  {h['layer']:>5} {h['x']:>9.2f} {h['z']:>8.2f} {dx:>13}{flag}")
        prevx = h["x"]

# also show ALL 557 hits (not just primary) to see the outlier
print(f"\nALL track {args.tid} hits (incl non-primary):")
for h in sorted([h for h in hits if h.get("track_id",-1)==args.tid], key=lambda h:(h['tracker'],h['z'])):
    print(f"  {h['tracker']:>6} layer {h['layer']:>2}  x={h['x']:>9.2f}  z={h['z']:>8.2f}  primary={h['_primary']}")
