#!/usr/bin/env python3

# Convert LDMX SimHits to event-display JSON.
#
# Includes tagger/recoil tracker hits, ECAL, HCAL,
# and Trigger Pad 1/2/3 hits.

import argparse
import json
import math
import uproot


parser = argparse.ArgumentParser()

parser.add_argument("infile", help="Input ROOT file")

parser.add_argument(
    "--tree",
    default="LDMX_Events",
    help="ROOT tree/key name (default: LDMX_Events)"
)

parser.add_argument(
    "--nevents",
    type=int,
    default=100,
    help="Number of events to convert (default: 100)"
)

parser.add_argument(
    "--source",
    choices=["digi", "sim"],
    default="digi",
    help="Tracker hit source: digi or sim (default: digi)"
)

parser.add_argument(
    "--out",
    default="events.json",
    help="Output JSON file (default: events.json)"
)

# Calorimeter collection options
parser.add_argument(
    "--ecal-coll",
    default=None,
    help="ECAL SimHits collection name; auto-detected if omitted"
)

parser.add_argument(
    "--hcal-coll",
    default=None,
    help="HCAL SimHits collection name; auto-detected if omitted"
)

parser.add_argument(
    "--no-ecal",
    action="store_true",
    help="Do not include ECAL hits"
)

parser.add_argument(
    "--no-hcal",
    action="store_true",
    help="Do not include HCAL hits"
)

# Trigger scintillator collection options
parser.add_argument(
    "--trigger1-coll",
    default=None,
    help="Trigger Pad 1 SimHits collection; auto-detected if omitted"
)

parser.add_argument(
    "--trigger2-coll",
    default=None,
    help="Trigger Pad 2 SimHits collection; auto-detected if omitted"
)

parser.add_argument(
    "--trigger3-coll",
    default=None,
    help="Trigger Pad 3 SimHits collection; auto-detected if omitted"
)

parser.add_argument(
    "--no-trigger",
    action="store_true",
    help="Do not include trigger scintillator hits"
)

args = parser.parse_args()


# ------------------------------------------------------------
# Open ROOT file
# ------------------------------------------------------------

f = uproot.open(args.infile)

tkey = next(
    (k for k in f.keys() if k.split(";")[0] == args.tree),
    None
)

if tkey is None:
    raise SystemExit(f"Tree {args.tree} not found.")

t = f[tkey]

n = min(args.nevents, t.num_entries)

print(
    f"Reading {n} of {t.num_entries} events "
    f"from {tkey} (source={args.source})"
)


# ------------------------------------------------------------
# Tracker collections
# ------------------------------------------------------------

if args.source == "digi":

    COLLS = {
        "tag": "DigiTaggerSimHits_test",
        "recoil": "DigiRecoilSimHits_test"
    }

    HAS_COV = True

else:
    #COLLS = {
    #"tag": "TaggerSimHits_tm_at_ldmx_continuum",
    #"recoil": "RecoilSimHits_tm_at_ldmx_continuum"
    #}
    COLLS = {
        "tag": "TaggerSimHits_tm_at_ldmx_signal",
        "recoil": "RecoilSimHits_tm_at_ldmx_signal"
    }

    HAS_COV = False


# ------------------------------------------------------------
# Find collections automatically
# ------------------------------------------------------------

def find_collection(prefix):

    candidates = []

    for k in t.keys():

        base = k.split("/")[0]

        if base.startswith(prefix) and base not in candidates:
            candidates.append(base)

    if not candidates:
        return None

    return candidates[0]


# ECAL / HCAL

if not args.no_ecal:
    ecal_coll = (
        args.ecal_coll
        or find_collection("EcalSimHits")
    )
else:
    ecal_coll = None


if not args.no_hcal:
    hcal_coll = (
        args.hcal_coll
        or find_collection("HcalSimHits")
    )
else:
    hcal_coll = None


# Trigger scintillator pads

if not args.no_trigger:

    trigger1_coll = (
        args.trigger1_coll
        or find_collection("TriggerPad1SimHits")
    )

    trigger2_coll = (
        args.trigger2_coll
        or find_collection("TriggerPad2SimHits")
    )

    trigger3_coll = (
        args.trigger3_coll
        or find_collection("TriggerPad3SimHits")
    )

else:

    trigger1_coll = None
    trigger2_coll = None
    trigger3_coll = None


print(f"  ECAL collection:     {ecal_coll or 'none'}")
print(f"  HCAL collection:     {hcal_coll or 'none'}")
print(f"  Trigger Pad 1:       {trigger1_coll or 'none'}")
print(f"  Trigger Pad 2:       {trigger2_coll or 'none'}")
print(f"  Trigger Pad 3:       {trigger3_coll or 'none'}")


# ------------------------------------------------------------
# ROOT branch helpers
# ------------------------------------------------------------

def branch_name(coll, comp):
    return f"{coll}/{coll}.{comp}"


def arr(coll, comp):
    return t[
        branch_name(coll, comp)
    ].array(entry_stop=n)


def has_branch(coll, comp):
    return branch_name(coll, comp) in t


# ------------------------------------------------------------
# Convert tracker hits
# ------------------------------------------------------------

def convert_tracker(kind, coll):

    lys = arr(coll, "layer_id_")

    if HAS_COV:

        gx = arr(coll, "meas_y_")
        gy = arr(coll, "meas_z_")
        gz = arr(coll, "meas_x_")

        cuu = arr(coll, "cov_uu_")
        cvv = arr(coll, "cov_vv_")

    else:

        gx = arr(coll, "x_")
        gy = arr(coll, "y_")
        gz = arr(coll, "z_")

    tid = (
        arr(coll, "track_id_")
        if has_branch(coll, "track_id_")
        else None
    )

    pid = (
        arr(coll, "pdg_id_")
        if has_branch(coll, "pdg_id_")
        else None
    )

    per_event = []

    for i in range(n):

        ev = []

        for j in range(len(gx[i])):

            h = {
                "z": float(gz[i][j]),
                "x": float(gx[i][j]),
                "y": float(gy[i][j]),
                "layer": int(lys[i][j]),
                "tracker": kind,
            }

            if tid is not None:
                h["track_id"] = int(tid[i][j])

            if pid is not None:
                h["pdg"] = int(pid[i][j])

            if HAS_COV:

                h["sx"] = math.sqrt(
                    abs(float(cuu[i][j]))
                )

                h["sy"] = math.sqrt(
                    abs(float(cvv[i][j]))
                )

            ev.append(h)

        # Mark one hit per track/layer/subsystem as primary
        seen = {}

        for h in ev:

            key = (
                h.get("track_id", -1),
                h["layer"],
                h["tracker"]
            )

            h["primary"] = key not in seen

            if h["primary"]:
                seen[key] = h

        per_event.append(ev)

    return per_event


# ------------------------------------------------------------
# Convert ECAL / HCAL / Trigger SimHits
# ------------------------------------------------------------

def convert_detector(kind, coll):

    if coll is None:
        return [[] for _ in range(n)]

    required = [
        "x_",
        "y_",
        "z_",
        "edep_"
    ]

    missing = [
        c for c in required
        if not has_branch(coll, c)
    ]

    if missing:
        raise SystemExit(
            f"{coll} is missing required branches: {missing}"
        )

    xs = arr(coll, "x_")
    ys = arr(coll, "y_")
    zs = arr(coll, "z_")
    edeps = arr(coll, "edep_")

    per_event = []

    for i in range(n):

        ev = []

        for j in range(len(xs[i])):

            h = {
                "z": float(zs[i][j]),
                "x": float(xs[i][j]),
                "y": float(ys[i][j]),
                "tracker": kind,
                "edep": float(edeps[i][j]),
            }

            ev.append(h)

        per_event.append(ev)

    return per_event


# ------------------------------------------------------------
# Convert everything
# ------------------------------------------------------------

data = {

    "tag":
        convert_tracker(
            "tag",
            COLLS["tag"]
        ),

    "recoil":
        convert_tracker(
            "recoil",
            COLLS["recoil"]
        ),

    "ecal":
        convert_detector(
            "ecal",
            ecal_coll
        ),

    "hcal":
        convert_detector(
            "hcal",
            hcal_coll
        ),

    "trigger1":
        convert_detector(
            "trigger1",
            trigger1_coll
        ),

    "trigger2":
        convert_detector(
            "trigger2",
            trigger2_coll
        ),

    "trigger3":
        convert_detector(
            "trigger3",
            trigger3_coll
        ),
}


# ------------------------------------------------------------
# Build JSON events
# ------------------------------------------------------------

events = []

for i in range(n):

    hits = (
        data["tag"][i]
        + data["recoil"][i]
        + data["ecal"][i]
        + data["hcal"][i]
        + data["trigger1"][i]
        + data["trigger2"][i]
        + data["trigger3"][i]
    )

    events.append({
        "hits": hits,
        "track": None
    })


# ------------------------------------------------------------
# Write output
# ------------------------------------------------------------

with open(args.out, "w") as fout:

    json.dump(
        {
            "events": events,

            "has_uncertainty": HAS_COV,

            "collections": {

                "tag": COLLS["tag"],
                "recoil": COLLS["recoil"],

                "ecal": ecal_coll,
                "hcal": hcal_coll,

                "trigger1": trigger1_coll,
                "trigger2": trigger2_coll,
                "trigger3": trigger3_coll,
            },
        },
        fout
    )


# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

counts = {
    k: sum(
        len(data[k][i])
        for i in range(n)
    )
    for k in data
}

print(f"Wrote {len(events)} events to {args.out}")

print(
    "  hits: "
    + ", ".join(
        f"{k}={v}"
        for k, v in counts.items()
    )
)

print(
    "  track_id present: "
    f"{any(
        'track_id' in h
        for ev in events
        for h in ev['hits']
    )}"
)
