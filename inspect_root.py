#!/usr/bin/env python3
# Inspect an LDMX events.root file: list branches and show the shape of the
# tagger/recoil track and hit collections. Run this on your machine (needs uproot).
#   pip install uproot awkward
#   python inspect_root.py events.root

import sys
import uproot

fname = sys.argv[1] if len(sys.argv) > 1 else "events.root"
f = uproot.open(fname)

print("=== top-level keys ===")
for k in f.keys():
    print("  ", k)

# find the events tree
tree_name = None
for k in f.keys():
    if "LDMX_Events" in k:
        tree_name = k
        break
if tree_name is None:
    print("\nCouldn't find LDMX_Events; keys above show what's here.")
    sys.exit(0)

t = f[tree_name]
print(f"\n=== tree: {tree_name}  ({t.num_entries} entries) ===")

print("\n=== all branches ===")
for b in t.keys():
    print("  ", b)

# Show branches most relevant to a tracker display
print("\n=== track / hit / sim branches ===")
for b in t.keys():
    if any(w in b for w in ("Track","Tagger","Recoil","Hit","Sim","Sp","Scoring","Measurement")):
        print("  ", b)

# Peek at the structure of the track collections for one event
print("\n=== structure of first event's track collections ===")
for coll in ("TaggerTracks_test", "RecoilTracks_test"):
    match = [b for b in t.keys() if coll in b]
    if not match:
        print(f"  {coll}: not found as a branch (may be a sub-object)")
        continue
    try:
        arr = t[match[0]].array(entry_stop=1)
        print(f"  {match[0]}: {arr.type}")
    except Exception as e:
        print(f"  {match[0]}: couldn't read ({e})")
