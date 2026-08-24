# LDMX Tracker Event Display

Reads ldmx-sw ROOT output, converts tracker hits to JSON, and draws them in the
bend plane with per-particle coloring, particle-type labels, and the real physical
silicon sensors overlaid (parsed from the detector GDML).

## Install
    pip install -r requirements.txt      # uproot awkward PyQt5 matplotlib

## Full pipeline
    # 1. hits: ROOT -> JSON  (sim = truth+pdg+track_id; digi = measured+uncertainty)
    python root_to_events.py events.root --nevents 200 --source sim  --out events_sim.json
    python root_to_events.py events.root --nevents 200 --source digi --out events_digi.json

    # 2. geometry: GDML -> sensor rectangles (run once; needs the 5 gdml files)
    python gdml_to_geometry.py --gdml-dir /path/to/gdml --out geometry.json

    # 3. view: two windows (sim + digi), with sensors drawn
    python show_both.py --sim events_sim.json --digi events_digi.json --geometry geometry.json

Single window also works:
    python EventDisplay.py --input events_sim.json --geometry geometry.json

## Display encoding
- Color = track_id (sim only); legend shows particle type, e.g. "track 558 (e+)".
- Shape = subsystem (circle tagger, square recoil).
- Bands = real silicon sensors to scale (tagger 40.34mm, recoil 50mm wide) at true z.
  Tan+tick = stereo sensor (rotated about z into y; the tilt shows in y-z/x-y, not x-z).
  Gray = axial.
- Line connects one primary hit per (track, layer, subsystem); breaks on implausible
  jumps; non-primary hits (stereo partners/outliers) drawn small & faint.
- target marked at z=0. Error bars off by default (--errbars to enable, exaggerated).

## Two hit sources (pick per view)
- sim: truth hits, carry track_id + pdg -> coloring + particle labels. No uncertainty.
- digi: measured hits, carry cov_uu/cov_vv -> error bars. No per-hit track_id -> one color.
  (ldmx-sw stores truth and measured in separate collections; can't have both at once.)

## Geometry (gdml_to_geometry.py)
Parses constants.gdml + detector.gdml + tagger/recoil.gdml, resolves all variables
and expressions, applies envelope world-positions, and writes each sensor's global
(x,y,z), size, and stereo angle. VERIFIED: computed sensor z-ranges match the event
data exactly (tagger -615.5..-9.5, recoil 9.5..185.5) and hits land on sensor bands.
42 sensors: 14 tagger (7 layers x axial+stereo), 28 recoil (4x2 + two 10-sensor grids).

## Event numbering
Display and diagnostics are both 1-based: display "Event 21" == scripts --event 21.

## Diagnostics (optional)
    inspect_root.py      list ROOT branches
    inspect_tracks.py    track_id/pdg per hit for one event
    check_coords.py      raw x/y/z (coordinate mapping)
    diagnose_events.py   hit counts / ranges / health check
    check_pdg.py         verify a sim JSON carries pdg
    (others: check_indexing, check_json_vs_root, find_event, which_files, debug_line, check_signal)

## Known limitations / next steps
- x-z projection only so far. "Every projection" (reviewer request): x-y view would
  show the recoil L5/L6 sensor grid and the stereo tilt; y-z shows stereo tilt too.
  geometry.json already has full (x,y,z)+angle per sensor, ready to feed those views.
- No fitted track LINES yet (ldmx-sw memberwise track collections aren't uproot-readable;
  needs ldmx-sw/PyROOT). Current lines connect hits, not the Kalman fit.
- Stereo de-duplication for the line is a display convenience, not a true stereo->xy recon.
