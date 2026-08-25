#!/usr/bin/env python3
# LDMX 3D event display with simplified detector geometry outlines.
#
# Displays:
#   - tagger tracker hits and silicon planes
#   - recoil tracker hits and silicon planes
#   - Trigger Pad 1/2/3 scintillator hits and outlines
#   - ECAL hits and envelope
#   - HCAL hits and envelope
#   - target outline at z = 0
#   - magnet-gap wireframe
#
# This version uses dimensions extracted from the LDMX v15 8 GeV GDML
# geometry files. It intentionally draws simplified detector envelopes
# and tracker planes rather than every detailed GDML component.
#
# Examples:
#   python EventDisplay_3D.py --input events.json
#   python EventDisplay_3D.py --input events.json --no-geometry
#   python EventDisplay_3D.py --input events.json --pdf events_3d.pdf
#   python EventDisplay_3D.py --input events.json --pdf event1.pdf --pdf-events 1

import sys
import argparse
import json
import math
import random


# ----------------------------------------------------------------------
# Command-line arguments
# ----------------------------------------------------------------------

parser = argparse.ArgumentParser()

parser.add_argument(
    "--input",
    type=str,
    default=None,
    help="JSON event file to load",
)

parser.add_argument(
    "--nevents",
    type=int,
    default=20,
    help="Number of fake events if --input is omitted",
)

parser.add_argument(
    "--seed",
    type=int,
    default=0,
    help="Random seed for fake events",
)

parser.add_argument(
    "--calo-scale",
    type=float,
    default=30.0,
    help="Marker-area scale for trigger/ECAL/HCAL energy deposits",
)

parser.add_argument(
    "--view-elev",
    type=float,
    default=18.0,
    help="Initial 3D elevation angle in degrees",
)

parser.add_argument(
    "--view-azim",
    type=float,
    default=-65.0,
    help="Initial 3D azimuth angle in degrees",
)

parser.add_argument(
    "--no-geometry",
    action="store_true",
    help="Do not draw detector geometry outlines",
)

parser.add_argument(
    "--geometry-alpha",
    type=float,
    default=0.16,
    help="Transparency of detector geometry faces (default: 0.16)",
)

parser.add_argument(
    "--geometry-linewidth",
    type=float,
    default=1.35,
    help="Line width for detector geometry outlines",
)

parser.add_argument(
    "--pdf",
    type=str,
    default=None,
    help=(
        "Write a multi-page 3D PDF instead of opening the interactive "
        "viewer. One event is rendered per page."
    ),
)

parser.add_argument(
    "--pdf-events",
    type=str,
    default=None,
    help=(
        "Comma-separated 1-based event numbers for PDF output. "
        "Default: all events."
    ),
)

args = parser.parse_known_args()[0]
random.seed(args.seed)


# ----------------------------------------------------------------------
# Coordinate convention
#
# Detector coordinates:
#   x = horizontal bend direction
#   y = vertical direction
#   z = beam direction
#
# Matplotlib coordinates in this file:
#   matplotlib X axis = detector z
#   matplotlib Y axis = detector x
#   matplotlib Z axis = detector y
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# Major LDMX geometry values, in mm.
#
# Extracted from constants.gdml, detector.gdml, tagger.gdml,
# recoil.gdml, trig_scint.gdml, target.gdml, ecal.gdml, and hcal.gdml.
# ----------------------------------------------------------------------

TARGET_Z = 0.0

# Physical aluminum target.
TARGET_DX = 40.0
TARGET_DY = 100.0
TARGET_DZ = 8.89

# Magnet gap.
MAGNET_CENTER_Z = -400.0
MAGNET_DX = 430.0
MAGNET_DY = 350.0
MAGNET_DZ = 1068.0

# Tagger tracker parent envelope.
TAGGER_CENTER_Z = -312.5
TAGGER_DX = 430.0
TAGGER_DY = 350.0
TAGGER_DZ = 607.0

# Tagger silicon sensors.
TAGGER_SENSOR_DX = 40.34
TAGGER_SENSOR_DY = 100.0
TAGGER_SENSOR_DZ = 0.32

# Global centers of the seven tagger layers.
# These include the parent-volume global placement.
TAGGER_LAYER_Z = [
    -612.5,
    -512.5,
    -412.5,
    -312.5,
    -212.5,
    -112.5,
    -12.5,
]

# Small x offsets from the tagger GDML.
TAGGER_LAYER_X = [
    -0.003,
    -0.3405,
    -1.2405,
    -2.7035,
    -4.7305,
    -7.3215,
    -10.4775,
]

# Tagger axial/stereo sensor separation in z.
TAGGER_STEREO_OFFSET_Z = 3.0

# Recoil tracker parent envelope.
RECOIL_CENTER_Z = 98.5
RECOIL_DX = 430.0
RECOIL_DY = 350.0
RECOIL_DZ = 179.0

# Recoil silicon sensors.
RECOIL_SENSOR_DX = 50.0
RECOIL_SENSOR_DY = 80.0
RECOIL_SENSOR_DZ = 0.32

# First four layers, approximate global nominal layer positions.
RECOIL_L14_Z = [
    12.5,
    27.5,
    42.5,
    57.5,
]

# Axial/stereo separation for layers 1-4.
RECOIL_L14_STEREO_OFFSET_Z = 3.0

# Recoil layers 5 and 6.
RECOIL_L5_Z = 94.5
RECOIL_L6_Z = 184.5

# Ten sensor module centers in the transverse x/y plane for L5/L6.
RECOIL_L56_XY = [
    (96.0, 40.0),
    (48.0, 40.0),
    (0.0, 40.0),
    (-48.0, 40.0),
    (-96.0, 40.0),
    (96.0, -40.0),
    (48.0, -40.0),
    (0.0, -40.0),
    (-48.0, -40.0),
    (-96.0, -40.0),
]

# Trigger-pad dimensions.
TRIGGER_PAD_DX = 30.0
TRIGGER_PAD_DY = 78.9
TRIGGER_PAD_DZ = 4.5

# Approximate global centers extracted from geometry placement equations.
TRIGGER1_CENTER = (7.4, 0.0, -878.25)
TRIGGER2_CENTER = (8.65, 0.0, -818.25)
TRIGGER3_CENTER = (18.15, 0.0, -6.72)

# ECAL envelope.
ECAL_DX = 880.6815
ECAL_DY = 600.0
ECAL_DZ = 600.0
ECAL_CENTER_X = 0.0
ECAL_CENTER_Y = 19.05
ECAL_CENTER_Z = 540.0

# HCAL outer envelope.
HCAL_DX = 3000.0
HCAL_DY = 3000.0
HCAL_DZ = 5304.0
HCAL_CENTER_X = 0.0
HCAL_CENTER_Y = 19.05
HCAL_CENTER_Z = 2892.0


# ----------------------------------------------------------------------
# PDG particle names
# ----------------------------------------------------------------------

PDG_NAMES = {
    11: "e−",
    -11: "e+",
    13: "μ−",
    -13: "μ+",
    15: "τ−",
    -15: "τ+",
    22: "γ",
    111: "π0",
    211: "π+",
    -211: "π−",
    321: "K+",
    -321: "K−",
    130: "K0L",
    310: "K0S",
    311: "K0",
    -311: "K̄0",
    2212: "p",
    -2212: "p̄",
    2112: "n",
    -2112: "n̄",
    12: "νe",
    -12: "ν̄e",
    14: "νμ",
    -14: "ν̄μ",
    16: "ντ",
    -16: "ν̄τ",
}


def particle_name(pdg):
    """Return a readable particle label for a PDG ID."""
    if pdg is None:
        return "unknown"

    try:
        pdg = int(pdg)
    except (TypeError, ValueError):
        return "unknown"

    if pdg == 0:
        return "unknown"

    return PDG_NAMES.get(pdg, f"PDG {pdg}")


def track_particle_name(track_hits):
    """Find the particle name associated with one tracker track."""
    pdgs = []

    for hit in track_hits:
        if "pdg" not in hit:
            continue

        try:
            pdg = int(hit["pdg"])
        except (TypeError, ValueError):
            continue

        if pdg not in pdgs:
            pdgs.append(pdg)

    if not pdgs:
        return "unknown"

    return "/".join(particle_name(pdg) for pdg in pdgs)


# ----------------------------------------------------------------------
# Fake events
# ----------------------------------------------------------------------

def generate_fake_event():
    """Generate a simple fake electron event if no JSON is supplied."""

    hits = []

    x0 = random.uniform(-1.0, 1.0)
    y0 = random.uniform(-1.0, 1.0)

    x_slope = random.uniform(-0.015, 0.015)
    y_slope = random.uniform(-0.010, 0.010)

    for layer, z in enumerate(TAGGER_LAYER_Z):
        x = x0 + x_slope * z + random.gauss(0, 0.05)
        y = y0 + y_slope * z + random.gauss(0, 0.05)

        hits.append({
            "x": x,
            "y": y,
            "z": z,
            "layer": layer,
            "tracker": "tag",
            "track_id": 1,
            "pdg": 11,
            "primary": True,
        })

    recoil_x_slope = random.uniform(-0.08, 0.08)
    recoil_y_slope = random.uniform(-0.02, 0.02)
    curvature = random.uniform(-0.003, 0.003)

    for layer, z in enumerate(RECOIL_L14_Z):
        x = (
            x0
            + recoil_x_slope * z
            + curvature * z * z
            + random.gauss(0, 0.05)
        )

        y = y0 + recoil_y_slope * z + random.gauss(0, 0.05)

        hits.append({
            "x": x,
            "y": y,
            "z": z,
            "layer": layer,
            "tracker": "recoil",
            "track_id": 1,
            "pdg": 11,
            "primary": True,
        })

    return {"hits": hits, "track": None}


# ----------------------------------------------------------------------
# Geometry-drawing helpers
# ----------------------------------------------------------------------

def draw_box(
    ax,
    center,
    dimensions,
    color,
    label=None,
    alpha=None,
    linewidth=None,
    draw_faces=False,
):
    """
    Draw a detector-coordinate box.

    center and dimensions are in detector coordinate order:
      center = (x, y, z)
      dimensions = (dx, dy, dz)

    The display converts detector coordinates to plotting order:
      plot X = detector z
      plot Y = detector x
      plot Z = detector y
    """

    from itertools import product

    if alpha is None:
        alpha = args.geometry_alpha

    if linewidth is None:
        linewidth = args.geometry_linewidth

    cx, cy, cz = center
    dx, dy, dz = dimensions

    x0 = cx - dx / 2.0
    x1 = cx + dx / 2.0

    y0 = cy - dy / 2.0
    y1 = cy + dy / 2.0

    z0 = cz - dz / 2.0
    z1 = cz + dz / 2.0

    corners = list(product(
        [x0, x1],
        [y0, y1],
        [z0, z1],
    ))

    # Pairs of corner indices that form the 12 box edges.
    edges = [
        (0, 1), (0, 2), (0, 4),
        (1, 3), (1, 5),
        (2, 3), (2, 6),
        (3, 7),
        (4, 5), (4, 6),
        (5, 7),
        (6, 7),
    ]

    for edge_index, (a, b) in enumerate(edges):
        xa, ya, za = corners[a]
        xb, yb, zb = corners[b]

        ax.plot(
            [za, zb],
            [xa, xb],
            [ya, yb],
            color=color,
            alpha=max(alpha * 2.5, 0.35),
            lw=linewidth,
            label=label if edge_index == 0 else None,
        )

    if draw_faces:
        import numpy as np

        faces = [
            # detector z low and high faces
            [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)],
            [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
        ]

        for face in faces:
            plot_z = np.array([[point[2] for point in face[:2]],
                               [point[2] for point in face[2:]]])
            plot_x = np.array([[point[0] for point in face[:2]],
                               [point[0] for point in face[2:]]])
            plot_y = np.array([[point[1] for point in face[:2]],
                               [point[1] for point in face[2:]]])

            ax.plot_surface(
                plot_z,
                plot_x,
                plot_y,
                color=color,
                alpha=alpha,
                linewidth=0,
                shade=False,
            )


def draw_tracker_plane(
    ax,
    center_x,
    center_y,
    center_z,
    dx,
    dy,
    color,
    alpha=0.18,
):
    """
    Draw a thin tracker sensor plane.

    The sensor is a thin rectangle normal to the detector z direction.
    """

    import numpy as np

    x0 = center_x - dx / 2.0
    x1 = center_x + dx / 2.0

    y0 = center_y - dy / 2.0
    y1 = center_y + dy / 2.0

    # Plot axes are (detector z, detector x, detector y).
    plot_z = np.array([
        [center_z, center_z],
        [center_z, center_z],
    ])

    plot_x = np.array([
        [x0, x1],
        [x0, x1],
    ])

    plot_y = np.array([
        [y0, y0],
        [y1, y1],
    ])

    ax.plot_surface(
        plot_z,
        plot_x,
        plot_y,
        color=color,
        alpha=alpha,
        linewidth=0,
        shade=False,
    )

    ax.plot(
        [center_z, center_z, center_z, center_z, center_z],
        [x0, x1, x1, x0, x0],
        [y0, y0, y1, y1, y0],
        color=color,
        alpha=0.55,
        lw=0.45,
    )


def draw_detector_geometry(ax):
    """Draw simplified LDMX detector outlines."""

    # Magnet gap: a large wireframe around the tracker/target region.
    draw_box(
        ax,
        center=(0.0, 0.0, MAGNET_CENTER_Z),
        dimensions=(MAGNET_DX, MAGNET_DY, MAGNET_DZ),
        color="#8e44ad",
        label="magnet gap",
        alpha=0.035,
        draw_faces=False,
    )

    # Trigger scintillator pads.
    draw_box(
        ax,
        center=TRIGGER1_CENTER,
        dimensions=(TRIGGER_PAD_DX, TRIGGER_PAD_DY, TRIGGER_PAD_DZ),
        color="#e74c3c",
        label="Trigger Pad 1",
        alpha=0.15,
        draw_faces=True,
    )

    draw_box(
        ax,
        center=TRIGGER2_CENTER,
        dimensions=(TRIGGER_PAD_DX, TRIGGER_PAD_DY, TRIGGER_PAD_DZ),
        color="#9b59b6",
        label="Trigger Pad 2",
        alpha=0.15,
        draw_faces=True,
    )

    draw_box(
        ax,
        center=TRIGGER3_CENTER,
        dimensions=(TRIGGER_PAD_DX, TRIGGER_PAD_DY, TRIGGER_PAD_DZ),
        color="#f39c12",
        label="Trigger Pad 3",
        alpha=0.15,
        draw_faces=True,
    )

    # Tagger parent envelope.
    draw_box(
        ax,
        center=(0.0, 0.0, TAGGER_CENTER_Z),
        dimensions=(TAGGER_DX, TAGGER_DY, TAGGER_DZ),
        color="#2980b9",
        label="tagger envelope",
        alpha=0.025,
        draw_faces=False,
    )

    # Tagger silicon planes: axial and stereo sensors at each layer.
    for i, (layer_x, layer_z) in enumerate(
        zip(TAGGER_LAYER_X, TAGGER_LAYER_Z),
        start=1,
    ):
        draw_tracker_plane(
            ax,
            center_x=layer_x,
            center_y=0.0,
            center_z=layer_z - TAGGER_STEREO_OFFSET_Z,
            dx=TAGGER_SENSOR_DX,
            dy=TAGGER_SENSOR_DY,
            color="#2980b9",
            alpha=0.16,
        )

        draw_tracker_plane(
            ax,
            center_x=layer_x,
            center_y=0.0,
            center_z=layer_z + TAGGER_STEREO_OFFSET_Z,
            dx=TAGGER_SENSOR_DX,
            dy=TAGGER_SENSOR_DY,
            color="#5dade2",
            alpha=0.10,
        )

    # Target slab.
    draw_box(
        ax,
        center=(0.0, 0.0, TARGET_Z),
        dimensions=(TARGET_DX, TARGET_DY, TARGET_DZ),
        color="#2c3e50",
        label="Al target",
        alpha=0.35,
        draw_faces=True,
    )

    # Recoil tracker parent envelope.
    draw_box(
        ax,
        center=(0.0, 0.0, RECOIL_CENTER_Z),
        dimensions=(RECOIL_DX, RECOIL_DY, RECOIL_DZ),
        color="#e67e22",
        label="recoil envelope",
        alpha=0.025,
        draw_faces=False,
    )

    # Recoil tracker layers 1-4: axial/stereo planes.
    for layer_z in RECOIL_L14_Z:
        draw_tracker_plane(
            ax,
            center_x=0.0,
            center_y=0.0,
            center_z=layer_z - RECOIL_L14_STEREO_OFFSET_Z,
            dx=RECOIL_SENSOR_DX,
            dy=RECOIL_SENSOR_DY,
            color="#e67e22",
            alpha=0.16,
        )

        draw_tracker_plane(
            ax,
            center_x=0.0,
            center_y=0.0,
            center_z=layer_z + RECOIL_L14_STEREO_OFFSET_Z,
            dx=RECOIL_SENSOR_DX,
            dy=RECOIL_SENSOR_DY,
            color="#f5b041",
            alpha=0.10,
        )

    # Recoil layers 5 and 6: ten separate sensor modules each.
    for module_x, module_y in RECOIL_L56_XY:
        draw_tracker_plane(
            ax,
            center_x=module_x,
            center_y=module_y,
            center_z=RECOIL_L5_Z,
            dx=RECOIL_SENSOR_DX,
            dy=RECOIL_SENSOR_DY,
            color="#e67e22",
            alpha=0.14,
        )

        draw_tracker_plane(
            ax,
            center_x=module_x,
            center_y=module_y,
            center_z=RECOIL_L6_Z,
            dx=RECOIL_SENSOR_DX,
            dy=RECOIL_SENSOR_DY,
            color="#e67e22",
            alpha=0.14,
        )

    # ECAL parent envelope.
    draw_box(
        ax,
        center=(ECAL_CENTER_X, ECAL_CENTER_Y, ECAL_CENTER_Z),
        dimensions=(ECAL_DX, ECAL_DY, ECAL_DZ),
        color="#27ae60",
        label="ECAL envelope",
        alpha=0.035,
        draw_faces=False,
    )

    # HCAL outer envelope.
    draw_box(
        ax,
        center=(HCAL_CENTER_X, HCAL_CENTER_Y, HCAL_CENTER_Z),
        dimensions=(HCAL_DX, HCAL_DY, HCAL_DZ),
        color="#1f4e79",
        label="HCAL envelope",
        alpha=0.08,
        draw_faces=False,
    )


# ----------------------------------------------------------------------
# Axis limits
# ----------------------------------------------------------------------

def event_limits(hits):
    """
    Calculate suitable plot limits.

    Geometry is always included in the limit estimate unless
    --no-geometry is specified.
    """

    if hits:
        zs = [float(hit["z"]) for hit in hits]
        xs = [float(hit["x"]) for hit in hits]
        ys = [float(hit["y"]) for hit in hits]
    else:
        zs = [0.0]
        xs = [0.0]
        ys = [0.0]

    if not args.no_geometry:
        # Use a moderate geometry range by default.
        # Full HCAL extent is included only if HCAL hits exist.
        zs.extend([
            -900.0,
            -616.0,
            -9.0,
            0.0,
            188.0,
            240.0,
            840.0,
        ])
        xs.extend([-450.0, 450.0])
        ys.extend([-350.0, 350.0])

        if any(hit.get("tracker") == "hcal" for hit in hits):
            zs.extend([240.0, 5544.0])
            xs.extend([-1500.0, 1500.0])
            ys.extend([-1500.0, 1500.0])

    zmin = min(zs)
    zmax = max(zs)

    xmin = min(xs)
    xmax = max(xs)

    ymin = min(ys)
    ymax = max(ys)

    zpad = max(40.0, 0.06 * max(zmax - zmin, 1.0))
    xpad = max(30.0, 0.15 * max(xmax - xmin, 1.0))
    ypad = max(30.0, 0.15 * max(ymax - ymin, 1.0))

    return (
        (zmin - zpad, zmax + zpad),
        (xmin - xpad, xmax + xpad),
        (ymin - ypad, ymax + ypad),
    )


# ----------------------------------------------------------------------
# Event renderer
# ----------------------------------------------------------------------

def render_event(ax, event, idx, total):
    """Render one LDMX event onto a Matplotlib 3D axes."""

    ax.clear()

    hits = event.get("hits", [])

    tracker_hits = [
        hit for hit in hits
        if hit.get("tracker") in ("tag", "recoil")
    ]

    zlim, xlim, ylim = event_limits(hits)

    # Draw geometry first so all particle hits appear in front.
    if not args.no_geometry:
        draw_detector_geometry(ax)

    # ------------------------------------------------------------------
    # Tracker tracks
    # ------------------------------------------------------------------

    tids = sorted(set(
        hit.get("track_id", -1)
        for hit in tracker_hits
    ))

    palette = [
        "#2980b9",
        "#e67e22",
        "#8e44ad",
        "#16a085",
        "#c0392b",
        "#2c3e50",
        "#d35400",
        "#7f8c8d",
    ]

    track_colors = {
        tid: palette[i % len(palette)]
        for i, tid in enumerate(tids)
    }

    track_particles = {}

    for tid in tids:
        this_track = [
            hit for hit in tracker_hits
            if hit.get("track_id", -1) == tid
        ]

        track_particles[tid] = track_particle_name(this_track)

    tracker_markers = {
        "tag": "o",
        "recoil": "s",
    }

    for tid in tids:

        for subsystem in ("tag", "recoil"):

            subset = [
                hit for hit in tracker_hits
                if hit.get("track_id", -1) == tid
                and hit.get("tracker") == subsystem
            ]

            if not subset:
                continue

            zs = [float(hit["z"]) for hit in subset]
            xs = [float(hit["x"]) for hit in subset]
            ys = [float(hit["y"]) for hit in subset]

            ax.scatter(
                zs,
                xs,
                ys,
                c=track_colors[tid],
                marker=tracker_markers[subsystem],
                s=35,
                edgecolors="black",
                linewidths=0.35,
                depthshade=True,
                label=f"track {tid}: {track_particles[tid]} · {subsystem}",
            )

        for subsystem in ("tag", "recoil"):

            line_hits = [
                hit for hit in tracker_hits
                if hit.get("track_id", -1) == tid
                and hit.get("tracker") == subsystem
                and hit.get("primary", True)
            ]

            line_hits.sort(key=lambda hit: float(hit["z"]))

            if len(line_hits) < 2:
                continue

            zs = [float(hit["z"]) for hit in line_hits]
            xs = [float(hit["x"]) for hit in line_hits]
            ys = [float(hit["y"]) for hit in line_hits]

            ax.plot(
                zs,
                xs,
                ys,
                color=track_colors[tid],
                lw=1.5,
                alpha=0.75,
            )

    # ------------------------------------------------------------------
    # Trigger, ECAL, and HCAL hits
    # ------------------------------------------------------------------

    detector_specs = {
        "trigger1": {
            "marker": "^",
            "label": "Trigger Pad 1 hits",
            "color": "#e74c3c",
            "alpha": 0.90,
        },
        "trigger2": {
            "marker": "v",
            "label": "Trigger Pad 2 hits",
            "color": "#9b59b6",
            "alpha": 0.90,
        },
        "trigger3": {
            "marker": "*",
            "label": "Trigger Pad 3 hits",
            "color": "#f39c12",
            "alpha": 0.95,
        },
        "ecal": {
            "marker": "D",
            "label": "ECAL hits",
            "color": "#27ae60",
            "alpha": 0.70,
        },
        "hcal": {
            "marker": "p",
            "label": "HCAL hits",
            "color": "#7f8c8d",
            "alpha": 0.70,
        },
    }

    counts = {}

    for subsystem, spec in detector_specs.items():

        subset = [
            hit for hit in hits
            if hit.get("tracker") == subsystem
        ]

        counts[subsystem] = len(subset)

        if not subset:
            continue

        zs = [float(hit["z"]) for hit in subset]
        xs = [float(hit["x"]) for hit in subset]
        ys = [float(hit["y"]) for hit in subset]

        edeps = [
            max(float(hit.get("edep", 0.0)), 0.0)
            for hit in subset
        ]

        positive_edeps = [
            energy for energy in edeps
            if energy > 0
        ]

        if positive_edeps:
            minimum_energy = min(positive_edeps)

            sizes = [
                15 + args.calo_scale *
                (1 + math.log10(
                    max(energy, minimum_energy) / minimum_energy
                ))
                for energy in edeps
            ]
        else:
            sizes = [22] * len(subset)

        ax.scatter(
            zs,
            xs,
            ys,
            c=spec["color"],
            marker=spec["marker"],
            s=sizes,
            alpha=spec["alpha"],
            edgecolors="black",
            linewidths=0.35,
            depthshade=True,
            label=spec["label"],
        )

    # Beam axis.
    ax.plot(
        [zlim[0], zlim[1]],
        [0.0, 0.0],
        [0.0, 0.0],
        "--",
        color="gray",
        alpha=0.45,
        lw=0.8,
    )

    # Axis setup.
    ax.set_xlim(zlim)
    ax.set_ylim(xlim)
    ax.set_zlim(ylim)

    ax.set_xlabel("z [mm] — beam direction", labelpad=10)
    ax.set_ylabel("x [mm] — bend plane", labelpad=10)
    ax.set_zlabel("y [mm] — vertical", labelpad=10)

    ax.view_init(
        elev=args.view_elev,
        azim=args.view_azim,
    )

    try:
        ax.set_box_aspect((
            zlim[1] - zlim[0],
            xlim[1] - xlim[0],
            ylim[1] - ylim[0],
        ))
    except AttributeError:
        pass

    title = (
        f"Event {idx + 1} / {total} · "
        "3D coordinates = (z, x, y) · "
        "tracker color = track_id · particle = PDG ID"
    )

    if not args.no_geometry:
        title += " · GDML-based simplified geometry shown"

    ax.set_title(title, fontsize=10, pad=16)

    # Remove duplicate legend entries.
    handles, labels = ax.get_legend_handles_labels()

    unique_handles = []
    unique_labels = []
    seen_labels = set()

    for handle, label in zip(handles, labels):
        if label not in seen_labels:
            unique_handles.append(handle)
            unique_labels.append(label)
            seen_labels.add(label)

    if unique_handles:
        ax.legend(
            unique_handles,
            unique_labels,
            loc="upper left",
            fontsize=7,
            ncol=2,
        )

    ntracks = len([
        tid for tid in tids
        if tid != -1
    ])

    return (
        f"Event {idx + 1} of {total} · "
        f"{len(tracker_hits)} tracker hits · "
        f"T1={counts.get('trigger1', 0)} · "
        f"T2={counts.get('trigger2', 0)} · "
        f"T3={counts.get('trigger3', 0)} · "
        f"ECAL={counts.get('ecal', 0)} · "
        f"HCAL={counts.get('hcal', 0)} · "
        f"{ntracks} track(s)"
    )


# ----------------------------------------------------------------------
# PDF export
# ----------------------------------------------------------------------

def export_pdf(events, output_path, event_indices=None):
    """Write selected events to a multi-page PDF."""

    import matplotlib
    matplotlib.use("Agg")

    from matplotlib.figure import Figure
    from matplotlib.backends.backend_pdf import PdfPages

    total = len(events)

    if event_indices is None:
        event_indices = list(range(total))

    with PdfPages(output_path) as pdf:

        for idx in event_indices:

            figure = Figure(figsize=(13, 8))
            axes = figure.add_subplot(111, projection="3d")

            status = render_event(
                axes,
                events[idx],
                idx,
                total,
            )

            figure.tight_layout()
            pdf.savefig(figure)

            print(f"  wrote page for {status}")

    print(f"Saved {len(event_indices)} event(s) to {output_path}")


# ----------------------------------------------------------------------
# Interactive PyQt5 viewer
# ----------------------------------------------------------------------

def run_gui(events):
    """Launch the interactive Qt/Matplotlib 3D viewer."""

    from PyQt5.QtWidgets import (
        QApplication,
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QPushButton,
        QLabel,
        QLineEdit,
    )

    from matplotlib.backends.backend_qt5agg import (
        FigureCanvasQTAgg as FigureCanvas,
        NavigationToolbar2QT as NavigationToolbar,
    )

    from matplotlib.figure import Figure

    class EventDisplay3D(QWidget):

        def __init__(self, loaded_events):
            super().__init__()

            self.events = loaded_events
            self.idx = 0

            self.setWindowTitle(
                "LDMX 3D Event Display — "
                "GDML Geometry + Tracker + Trigger + ECAL + HCAL"
            )

            self.resize(1280, 820)

            outer = QVBoxLayout(self)

            self.figure = Figure(figsize=(13, 8))
            self.canvas = FigureCanvas(self.figure)

            self.ax = self.figure.add_subplot(
                111,
                projection="3d",
            )

            toolbar = NavigationToolbar(self.canvas, self)

            outer.addWidget(toolbar)
            outer.addWidget(self.canvas)

            navigation = QHBoxLayout()

            previous_button = QPushButton("< Prev")
            previous_button.clicked.connect(self.previous_event)

            next_button = QPushButton("Next >")
            next_button.clicked.connect(self.next_event)

            self.jump = QLineEdit()
            self.jump.setPlaceholderText("go to #")
            self.jump.setFixedWidth(75)
            self.jump.returnPressed.connect(self.jump_to_event)

            self.status_label = QLabel()

            navigation.addWidget(previous_button)
            navigation.addWidget(next_button)
            navigation.addWidget(self.jump)
            navigation.addWidget(self.status_label)
            navigation.addStretch()

            outer.addLayout(navigation)

            self.draw_event()

        def draw_event(self):
            status = render_event(
                self.ax,
                self.events[self.idx],
                self.idx,
                len(self.events),
            )

            self.status_label.setText(status)
            self.canvas.draw()

        def next_event(self):
            self.idx = (self.idx + 1) % len(self.events)
            self.draw_event()

        def previous_event(self):
            self.idx = (self.idx - 1) % len(self.events)
            self.draw_event()

        def jump_to_event(self):
            try:
                event_number = int(self.jump.text()) - 1
            except ValueError:
                self.jump.clear()
                return

            if 0 <= event_number < len(self.events):
                self.idx = event_number
                self.draw_event()

            self.jump.clear()

    app = QApplication(sys.argv)

    window = EventDisplay3D(events)
    window.show()

    sys.exit(app.exec_())


# ----------------------------------------------------------------------
# Input loading
# ----------------------------------------------------------------------

def load_events():
    """Load JSON events or create fake events."""

    if args.input:

        with open(args.input) as input_file:
            data = json.load(input_file)

        events = data["events"] if isinstance(data, dict) else data

        print(f"Loaded {len(events)} events from {args.input}")

        return events

    events = [
        generate_fake_event()
        for _ in range(args.nevents)
    ]

    print(f"Generated {len(events)} fake events")

    return events


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

if __name__ == "__main__":

    events = load_events()

    if not events:
        print("No events to display.")
        sys.exit(1)

    if args.pdf:

        selected_events = None

        if args.pdf_events:

            selected_events = [
                int(value.strip()) - 1
                for value in args.pdf_events.split(",")
                if value.strip()
            ]

            for event_index in selected_events:
                if not (0 <= event_index < len(events)):
                    raise SystemExit(
                        f"--pdf-events: event number {event_index + 1} "
                        f"is out of range (1..{len(events)})"
                    )

        export_pdf(
            events,
            args.pdf,
            selected_events,
        )

    else:
        run_gui(events)
