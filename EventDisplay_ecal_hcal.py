
#!/usr/bin/env python3
# LDMX 2D side-view event display.
#
# Displays:
#   - tagger tracker hits
#   - recoil tracker hits
#   - Trigger Pad 1/2/3 scintillator SimHits
#   - ECAL SimHits
#   - HCAL SimHits
#
# Input JSON is produced by root_to_events_ecal_hcal.py.
#
# Examples:
#   python EventDisplay_ecal_hcal.py --input events.json
#   python EventDisplay_ecal_hcal.py --input events.json --pdf out.pdf
#   python EventDisplay_ecal_hcal.py --input events.json --pdf out.pdf --pdf-events 1,3,7

import sys
import argparse
import random
import json
import math


# ----------------------------------------------------------------------
# Command-line options
# ----------------------------------------------------------------------

parser = argparse.ArgumentParser()

parser.add_argument(
    "--input",
    type=str,
    default=None,
    help="JSON event file to load (omit to generate fake tracker events)",
)

parser.add_argument(
    "--nevents",
    type=int,
    default=20,
    help="How many fake events to generate if no --input is given",
)

parser.add_argument(
    "--seed",
    type=int,
    default=0,
)

parser.add_argument(
    "--errscale",
    type=float,
    default=2000.0,
    help="Scale factor for tracker uncertainty error bars",
)

parser.add_argument(
    "--calo-scale",
    type=float,
    default=30.0,
    help="Marker-area scale for ECAL/HCAL/trigger energy deposition",
)

parser.add_argument(
    "--pdf",
    type=str,
    default=None,
    help=(
        "Render every event to a page of this multi-page PDF instead of "
        "launching the interactive viewer. PyQt5/display is not needed "
        "when using this option."
    ),
)

parser.add_argument(
    "--pdf-events",
    type=str,
    default=None,
    help=(
        "Comma-separated 1-based event numbers to include in --pdf output "
        "(default: all loaded events)"
    ),
)

args = parser.parse_known_args()[0]
random.seed(args.seed)


# ----------------------------------------------------------------------
# Simplified fake-event geometry
# ----------------------------------------------------------------------

TAG_LAYERS = [-60, -50, -40, -30, -20, -13, -6]
TARGET_Z = 0.0
RECOIL_LAYERS = [1.5, 3.0, 4.5, 6.0, 9.0, 18.0]


def generate_fake_event():
    """Generate a simple fake tracker-only event if no JSON is supplied."""
    hits = []

    x0 = random.uniform(-0.5, 0.5)
    slope = random.uniform(-0.01, 0.01)

    for i, z in enumerate(TAG_LAYERS):
        x = x0 + slope * z + random.gauss(0, 0.02)

        hits.append(
            {
                "z": z,
                "x": x,
                "layer": i,
                "tracker": "tag",
            }
        )

    x_target = x0 + slope * TARGET_Z
    recoil_slope = random.uniform(-0.05, 0.05)
    curvature = random.uniform(-0.02, 0.02)

    track = []

    for i, z in enumerate(RECOIL_LAYERS):
        x = (
            x_target
            + recoil_slope * z
            + curvature * z * z
            + random.gauss(0, 0.02)
        )

        hits.append(
            {
                "z": z,
                "x": x,
                "layer": i,
                "tracker": "recoil",
            }
        )

    zmin = TARGET_Z
    zmax = RECOIL_LAYERS[-1]

    track = [
        (
            z,
            x_target + recoil_slope * z + curvature * z * z,
        )
        for z in [
            zmin + (zmax - zmin) * t / 60
            for t in range(61)
        ]
    ]

    return {
        "hits": hits,
        "track": track,
    }


# ----------------------------------------------------------------------
# Shared rendering: used by both GUI and PDF export
# ----------------------------------------------------------------------

def render_event(ax, ev, idx, total):
    """
    Draw one event onto a matplotlib Axes.

    Returns a short status string for the GUI label or terminal output.
    """

    ax.clear()

    hits = ev.get("hits", [])

    # Only tracker hits define tracker detector-plane lines.
    tracker_hits = [
        h for h in hits
        if h.get("tracker") in ("tag", "recoil")
    ]

    for z in sorted(set(round(h["z"], 1) for h in tracker_hits)):
        ax.axvline(
            z,
            color="#ededed",
            lw=0.7,
            zorder=0,
        )

    # ------------------------------------------------------------------
    # Tracker hits: colored by scalar tracker track_id
    # ------------------------------------------------------------------

    tids = sorted(set(h.get("track_id", -1) for h in tracker_hits))

    palette = [
        "#2980b9",
        "#e67e22",
        "#8e44ad",
        "#16a085",
        "#c0392b",
        "#2c3e50",
    ]

    tcolor = {
        tid: palette[k % len(palette)]
        for k, tid in enumerate(tids)
    }

    tracker_markers = {
        "tag": "o",
        "recoil": "s",
    }

    has_err = False

    for tid in tids:

        # Draw tracker hit markers.
        for kind in ("tag", "recoil"):

            sub = [
                h for h in tracker_hits
                if h.get("track_id", -1) == tid
                and h["tracker"] == kind
            ]

            if not sub:
                continue

            zs = [h["z"] for h in sub]
            xs = [h["x"] for h in sub]

            # Optional uncertainty bars from digitized tracker hits.
            if any("sx" in h for h in sub):

                has_err = True

                xerr = [
                    h.get("sx", 0.0) * args.errscale
                    for h in sub
                ]

                ax.errorbar(
                    zs,
                    xs,
                    yerr=xerr,
                    fmt="none",
                    ecolor=tcolor[tid],
                    elinewidth=1,
                    capsize=2,
                    alpha=0.5,
                    zorder=2,
                )

            ax.scatter(
                zs,
                xs,
                c=tcolor[tid],
                marker=tracker_markers[kind],
                s=28,
                zorder=4,
                edgecolors="black",
                linewidths=0.3,
                label=f"track {tid} · {kind}",
            )

        # Connect primary tracker hits with a line.
        # Stereo partners are still visible but not used for the line.
        for kind in ("tag", "recoil"):

            line = sorted(
                [
                    h for h in tracker_hits
                    if h.get("track_id", -1) == tid
                    and h["tracker"] == kind
                    and h.get("primary", True)
                ],
                key=lambda h: h["z"],
            )

            if len(line) > 1:

                ax.plot(
                    [h["z"] for h in line],
                    [h["x"] for h in line],
                    "-",
                    color=tcolor[tid],
                    lw=1,
                    alpha=0.6,
                    zorder=3,
                )

    # ------------------------------------------------------------------
    # Trigger scintillator, ECAL, and HCAL hits
    #
    # These do not have a single unambiguous scalar track_id, so they are
    # shown as subsystem-specific energy-deposition markers rather than
    # track-colored or connected by lines.
    # ------------------------------------------------------------------

    detector_specs = {
        "trigger1": {
            "marker": "^",
            "label": "Trigger Pad 1",
            "color": "#e74c3c",
            "alpha": 0.80,
            "zorder": 6,
        },
        "trigger2": {
            "marker": "v",
            "label": "Trigger Pad 2",
            "color": "#9b59b6",
            "alpha": 0.80,
            "zorder": 6,
        },
        "trigger3": {
            "marker": "*",
            "label": "Trigger Pad 3",
            "color": "#f39c12",
            "alpha": 0.90,
            "zorder": 7,
        },
        "ecal": {
            "marker": "D",
            "label": "ECAL",
            "color": "#27ae60",
            "alpha": 0.65,
            "zorder": 5,
        },
        "hcal": {
            "marker": "p",
            "label": "HCAL",
            "color": "#7f8c8d",
            "alpha": 0.65,
            "zorder": 5,
        },
    }

    detector_counts = {}

    for kind, spec in detector_specs.items():

        sub = [
            h for h in hits
            if h.get("tracker") == kind
        ]

        detector_counts[kind] = len(sub)

        if not sub:
            continue

        zs = [h["z"] for h in sub]
        xs = [h["x"] for h in sub]

        edep = [
            max(float(h.get("edep", 0.0)), 0.0)
            for h in sub
        ]

        # Logarithmic size scaling prevents one high-energy cell from
        # obscuring every smaller energy deposit.
        positive = [e for e in edep if e > 0]

        if positive:

            emin = min(positive)

            sizes = [
                12 + args.calo_scale *
                (1 + math.log10(max(e, emin) / emin))
                for e in edep
            ]

        else:
            sizes = [16] * len(edep)

        ax.scatter(
            zs,
            xs,
            marker=spec["marker"],
            s=sizes,
            c=spec["color"],
            alpha=spec["alpha"],
            edgecolors="black",
            linewidths=0.3,
            label=spec["label"],
            zorder=spec["zorder"],
        )

    # ------------------------------------------------------------------
    # Target position
    # ------------------------------------------------------------------

    ax.axvline(
        TARGET_Z,
        color="black",
        linestyle="--",
        lw=1.0,
        alpha=0.7,
        label="target (z=0)",
    )

    ax.set_xlabel("z  [mm]  (beam direction)")
    ax.set_ylabel("x  [mm]  (bend plane)")

    ax.legend(
        loc="upper left",
        fontsize=7,
        ncol=3,
    )

    title = (
        f"Event {idx + 1} / {total} · "
        "color = tracker track_id · "
        "○ tagger · □ recoil · "
        "▲ trigger 1 · ▼ trigger 2 · ★ trigger 3 · "
        "◆ ECAL · ⬟ HCAL"
    )

    if has_err:
        title += f" · err bars ×{args.errscale:g}"

    ax.set_title(title, fontsize=9)

    ntracks = len([tid for tid in tids if tid != -1])

    return (
        f"Event {idx + 1} of {total} · "
        f"{len(tracker_hits)} tracker hits · "
        f"T1={detector_counts.get('trigger1', 0)} · "
        f"T2={detector_counts.get('trigger2', 0)} · "
        f"T3={detector_counts.get('trigger3', 0)} · "
        f"ECAL={detector_counts.get('ecal', 0)} · "
        f"HCAL={detector_counts.get('hcal', 0)} · "
        f"{ntracks} track(s)"
    )


# ----------------------------------------------------------------------
# PDF export: works without PyQt5 or a visible display
# ----------------------------------------------------------------------

def export_pdf(events, path, which=None):
    """
    Render selected events to a multi-page PDF, one event per page.

    which is either None (all events) or a list of zero-based event indices.
    """

    import matplotlib
    matplotlib.use("Agg")

    from matplotlib.figure import Figure
    from matplotlib.backends.backend_pdf import PdfPages

    total = len(events)

    indices = (
        list(which)
        if which is not None
        else list(range(total))
    )

    with PdfPages(path) as pdf:

        for idx in indices:

            ev = events[idx]

            fig = Figure(figsize=(12, 6.5))
            ax = fig.subplots()

            status = render_event(ax, ev, idx, total)

            fig.tight_layout()
            pdf.savefig(fig)

            print(f"  wrote page for {status}")

    print(f"Saved {len(indices)} event(s) to {path}")


# ----------------------------------------------------------------------
# Interactive PyQt5 GUI
# ----------------------------------------------------------------------

def run_gui(events):

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
    )

    from matplotlib.figure import Figure

    class EventDisplay(QWidget):

        def __init__(self, events):
            super().__init__()

            self.events = events
            self.idx = 0

            self.setWindowTitle(
                "LDMX Event Display — "
                "Tracker + Trigger Scintillators + ECAL + HCAL"
            )

            self.resize(1200, 650)

            outer = QVBoxLayout(self)

            self.canvas = FigureCanvas(
                Figure(figsize=(12, 6.5))
            )

            self.ax = self.canvas.figure.subplots()

            outer.addWidget(self.canvas)

            nav = QHBoxLayout()

            prev = QPushButton("< Prev")
            prev.clicked.connect(self.prev_event)

            nxt = QPushButton("Next >")
            nxt.clicked.connect(self.next_event)

            self.jump = QLineEdit()
            self.jump.setPlaceholderText("go to #")
            self.jump.setFixedWidth(70)
            self.jump.returnPressed.connect(self.jump_to_event)

            self.label = QLabel()

            nav.addWidget(prev)
            nav.addWidget(nxt)
            nav.addWidget(self.jump)
            nav.addWidget(self.label)
            nav.addStretch()

            outer.addLayout(nav)

            self.draw_event()

        def draw_event(self):

            ev = self.events[self.idx]

            status = render_event(
                self.ax,
                ev,
                self.idx,
                len(self.events),
            )

            self.label.setText(status)
            self.canvas.draw()

        def next_event(self):

            self.idx = (
                self.idx + 1
            ) % len(self.events)

            self.draw_event()

        def prev_event(self):

            self.idx = (
                self.idx - 1
            ) % len(self.events)

            self.draw_event()

        def jump_to_event(self):

            try:
                n = int(self.jump.text()) - 1
            except ValueError:
                return

            if 0 <= n < len(self.events):
                self.idx = n
                self.draw_event()

            self.jump.clear()

    app = QApplication(sys.argv)

    win = EventDisplay(events)
    win.show()

    sys.exit(app.exec_())


# ----------------------------------------------------------------------
# Input loading
# ----------------------------------------------------------------------

def load_events():

    if args.input:

        with open(args.input) as f:
            data = json.load(f)

        events = (
            data["events"]
            if isinstance(data, dict)
            else data
        )

        # Convert optional precomputed track lists from JSON lists to tuples.
        for ev in events:
            if ev.get("track"):
                ev["track"] = [
                    tuple(p)
                    for p in ev["track"]
                ]

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

        which = None

        if args.pdf_events:

            which = [
                int(s.strip()) - 1
                for s in args.pdf_events.split(",")
                if s.strip()
            ]

            for i in which:

                if not (0 <= i < len(events)):
                    raise SystemExit(
                        f"--pdf-events: event number {i + 1} out of range "
                        f"(1..{len(events)})"
                    )

        export_pdf(
            events,
            args.pdf,
            which=which,
        )

    else:
        run_gui(events)
