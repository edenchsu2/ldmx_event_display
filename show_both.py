#!/usr/bin/env python3
# Open TWO independent event-display windows at once: sim and digi.
# Each steps through events on its own (separate Prev/Next).
#
#   # make both JSONs first:
#   python root_to_events.py events.root --nevents 200 --source sim  --out events_sim.json
#   python root_to_events.py events.root --nevents 200 --source digi --out events_digi.json
#   # then:
#   python show_both.py --sim events_sim.json --digi events_digi.json

import sys, argparse
from PyQt5.QtWidgets import QApplication
import EventDisplay as ED   # reuse the display window + loader

p = argparse.ArgumentParser()
p.add_argument("--sim",  default="events_sim.json",  help="sim JSON (truth hits, colored by particle)")
p.add_argument("--digi", default="events_digi.json", help="digi JSON (measured hits, with error bars)")
p.add_argument("--geometry", default=None, help="geometry.json (sensor rectangles)")
opts = p.parse_args()

# if a geometry file was given, load it into the display module so both windows draw sensors
if opts.geometry:
    import json as _json
    try:
        with open(opts.geometry) as _gf:
            ED.GEOMETRY = _json.load(_gf)
        print(f"Loaded {len(ED.GEOMETRY.get('sensors', []))} sensors from {opts.geometry}")
    except Exception as _e:
        print(f"Could not load geometry {opts.geometry}: {_e}")

app = QApplication(sys.argv)
windows = []

for path, label, dx in [(opts.sim, "SIM — truth hits (colored by particle)", 60),
                        (opts.digi, "DIGI — measured hits (error bars)", 700)]:
    try:
        events = ED.load_events(path)
    except FileNotFoundError:
        print(f"Skipping {label}: file not found ({path})")
        continue
    if not events:
        print(f"Skipping {label}: no events")
        continue
    w = ED.EventDisplay(events, title=f"LDMX Tracker — {label}")
    w.move(dx, 80)          # offset so the two windows don't stack exactly
    w.show()
    windows.append(w)

if not windows:
    print("No windows to show — check that the JSON files exist.")
    sys.exit(1)

sys.exit(app.exec_())
