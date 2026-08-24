#!/usr/bin/env python3
# Diagnose the event-indexing / tree-cycle mismatch between the converter and
# inspect_tracks. Prints, for a given event index, the sim track_ids as read
# under EACH tree cycle, so we can see if 'event 21' means different things.
#
#   python check_indexing.py events.root --event 21

import argparse, uproot
import awkward as ak

p = argparse.ArgumentParser()
p.add_argument("infile")
p.add_argument("--event", type=int, default=21)
args = p.parse_args()

f = uproot.open(args.infile)
e = args.event - 1   # --event is 1-based (matches display); convert to 0-based index

# List every LDMX_Events cycle present
cycles = [k for k in f.keys() if k.split(";")[0] == "LDMX_Events"]
print("LDMX_Events cycles present:", cycles)
print(f"(uproot's default 'LDMX_Events' resolves to: {f['LDMX_Events'].name};{f['LDMX_Events'].cycle if hasattr(f['LDMX_Events'],'cycle') else '?'})")
print()

def tids_for(treekey, coll):
    t = f[treekey]
    br = f"{coll}/{coll}.track_id_"
    if br not in t.keys():
        return f"(no {coll})"
    arr = t[br].array(entry_start=e, entry_stop=e+1)
    if len(arr) == 0:
        return "(event out of range)"
    return sorted(set(int(v) for v in arr[0]))

for treekey in cycles + ["LDMX_Events"]:  # each explicit cycle, then the default
    tag = tids_for(treekey, "TaggerSimHits_test")
    rec = tids_for(treekey, "RecoilSimHits_test")
    n = f[treekey].num_entries
    print(f"{treekey:>16}  (n={n})  event {e}:  tagger track_ids={tag}   recoil track_ids={rec}")

print()
print("If different cycles give different track_ids for the same event index,")
print("that's the bug: converter and inspect_tracks are reading different cycles.")
print("Fix = both scripts pin the SAME cycle (usually the highest, ;4).")
