#!/usr/bin/env python3
"""Recalibrate pivac.Sentry's ``display_warp`` quad after the camera view drifts.

The Sentry reader decodes a 7-segment display through a perspective warp defined by
four corners in ``config.yml``. When the camera shifts, that quad slides off the
digits and the reader emits fresh-but-wrong values while every other
``hvac.boiler.sentry.*`` path keeps publishing, so the service looks healthy. This
has happened twice (2026-07-28, 2026-08-23) and recurs after physical work in the
boiler room.

**Decode logic is imported from pivac.Sentry, never reimplemented.** The older
scripts/sentry-calibrate.py duplicated it and went stale, so its decodes disagree
with the running module and cannot be trusted. Importing means this tool cannot
drift from the code it is calibrating.

Typical use, from the repo on the Pi::

    # 1. capture while the boiler cycles, then search offline
    sudo ~/pivac-venv/bin/python scripts/sentry-warp-search.py --capture 600 --save /tmp/f.npz
    sudo ~/pivac-venv/bin/python scripts/sentry-warp-search.py --load /tmp/f.npz \
         --search --truth-air 68.5 --eyecheck /tmp/eye.png
    # 2. inspect /tmp/eye.png by eye, THEN
    sudo ~/pivac-venv/bin/python scripts/sentry-warp-search.py --load /tmp/f.npz \
         --search --truth-air 68.5 --apply

``--truth-air`` is mandatory for a search and is the outdoor temperature in °F from
an independent source at capture time -- read it from
``environment.outside.thermostat.temperature`` (Kelvin, RedLink). A constant misread
scores perfectly on self-consistency, so without external ground truth a search can
converge confidently on the wrong answer. That is the trap that produced a "78 °F"
outdoor reading in July while the truth was 69.5.

The search covers ±16 px of translation and ±4 % of scale about the configured
quad. A knock moves the display further than that (2026-09-07: 58 px left, 87 px
up, and 14 % shorter). For such a move, first measure the lit-pixel bounding box of
the digits (max over the frames, threshold ~235), rebase the corners onto it by
hand, then run the search from there. Re-aim ``leds:`` and ``indicators:`` in the
same pass: locate each lens by dark-blob centroid on the per-pixel minimum of the
frames, within a window no wider than ±12 px seeded by eye.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import numpy as np
import yaml

from pivac.Sentry import (_read_display, _display_segments, _decode_display,  # noqa: E402
                          _segment_margin, _roi_is_lit, _SANE_RANGE)

# Region of the 2560x1440 frame holding digits, mode indicators and status LEDs.
# Wide enough to hold the display at both the 2026-08-23 position (digits at
# x 1143-1326, y 641-724) and the 2026-09-07 one (x 1089-1264, y 559-633).
REGION = (980, 450, 1450, 800)
VALUE_MODES = ("water_temp", "air", "gas_input")


def load_config(path=None):
    path = path or os.environ.get("PIVAC_CFG") or "/etc/pivac/config.yml"
    with open(path) as fh:
        return yaml.safe_load(fh)["pivac.Sentry"], path


def shift(cfg, ox, oy):
    """Config with every pixel coordinate rebased onto the cropped region, so the
    imported module functions work unchanged on a sub-frame."""
    out = dict(cfg)
    warp = dict(cfg["display_warp"])
    warp["corners"] = [{"x": c["x"] - ox, "y": c["y"] - oy} for c in warp["corners"]]
    out["display_warp"] = warp
    for key in ("leds", "indicators"):
        if key in cfg:
            out[key] = {k: {"x": v["x"] - ox, "y": v["y"] - oy} for k, v in cfg[key].items()}
    return out


def transform(corners, dx, dy, scale):
    """Translate and scale the quad about its centroid. dst_w/dst_h and
    digit_positions are deliberately left alone -- the hundreds position is a half
    digit whose '1' sits at the left of its cell, so deriving digit boxes from lit
    pixels breaks it."""
    cx = sum(c["x"] for c in corners) / 4.0
    cy = sum(c["y"] for c in corners) / 4.0
    return [{"x": cx + (c["x"] - cx) * scale + dx,
             "y": cy + (c["y"] - cy) * scale + dy} for c in corners]


def capture(cfg, count, timeout=240):
    import cv2
    os.environ.setdefault("OPENCV_FFMPEG_LOGLEVEL", "8")
    cap = cv2.VideoCapture(cfg["rtsp_url"])          # never logged
    if not cap.isOpened():
        sys.exit("could not open the RTSP stream")
    x0, y0, x1, y1 = REGION
    frames, colour, start = [], None, time.time()
    while len(frames) < count and time.time() - start < timeout:
        ok, frame = cap.read()
        if not ok:
            continue
        if colour is None:
            sub = frame[y0:y1, x0:x1].astype(int)
            colour = (float(np.mean(np.abs(sub[:, :, 2] - sub[:, :, 1]))),
                      float(np.mean(np.abs(sub[:, :, 1] - sub[:, :, 0]))))
        frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)[y0:y1, x0:x1])
    cap.release()
    print("captured %d frames in %.0fs" % (len(frames), time.time() - start))
    # IR/Night is true greyscale. A non-zero delta means the camera flipped to
    # day/colour, which is a different fault: relock it in the Tapo app before
    # touching the quad, because a warp fitted to a colour frame will not hold.
    print("colour deltas |R-G|=%.2f |G-B|=%.2f -> %s" % (
        colour[0], colour[1],
        "IR/Night lock OK" if max(colour) < 1.0 else "*** NOT greyscale: camera is in day mode ***"))
    return np.stack(frames)


def mode_of(frame, scfg):
    ratio = scfg.get("indicator_ratio", 1.15)
    lit = [m for m in scfg["indicators"] if _roi_is_lit(frame, scfg["indicators"][m], ratio=ratio)]
    return lit[0] if len(lit) == 1 else None


def evaluate(frames, modes, scfg, corners, indices):
    """Fraction of frames decoding to an in-range number, per-mode values, and the
    lit/unlit separation (pivac.Sentry._segment_margin) over the same frames. A
    quad is judged on the margin as much as on the clean rate: the 2026-09-09 quad
    was 100 % clean on the digits shown that night and read about 10 here, then
    read every 6 as an 8 once the outdoor temperature reached the 60s. Sound
    calibrations read 40 or more, and should do so on every +/-1 px neighbour."""
    trial = dict(scfg)
    trial["display_warp"] = dict(scfg["display_warp"], corners=corners)
    good, values, lit, unlit = 0, {}, [], []
    for i in indices:
        threshold, segments = _display_segments(frames[i], trial)
        for digit in segments:
            for b in digit.values():
                (lit if b >= threshold else unlit).append(b)
        text = _decode_display(segments, threshold)
        if not text or "?" in text:
            continue
        try:
            value = float(text)
        except ValueError:
            continue
        lo, hi = _SANE_RANGE[modes[i]]
        if not (lo <= value <= hi) and not (modes[i] == "gas_input" and value == 0):
            continue
        good += 1
        values.setdefault(modes[i], []).append(value)
    return good / max(len(indices), 1), values, _segment_margin(lit, unlit)


def report(label, clean, values, modes, indices, margin=None):
    print("\n%s  clean=%.1f%% of %d frames  margin=%s" % (
        label, clean * 100, len(indices),
        "n/a" if margin is None else "%.0f (%s)" % (margin, "sound" if margin >= 40 else "KNIFE EDGE" if margin < 20 else "thin")))
    for mode in VALUE_MODES:
        seen = sum(1 for i in indices if modes[i] == mode)
        got = values.get(mode)
        if got:
            arr = np.array(got)
            print("   %-11s %3d/%-3d  median=%6.1f  p10=%6.1f p90=%6.1f"
                  % (mode, len(arr), seen, np.median(arr), np.percentile(arr, 10), np.percentile(arr, 90)))
        else:
            print("   %-11s   0/%-3d  NOTHING DECODED" % (mode, seen))


def apply_corners(path, corners):
    import re
    with open(path) as fh:
        text = fh.read()
    block = re.search(r"(display_warp:\s*\n\s*corners:\s*\n)((?:\s*-\s*\{[^}]*\}.*\n){4})", text)
    if not block:
        sys.exit("could not locate the display_warp corners block; edit by hand")
    lines, out = block.group(2).splitlines(), []
    for line, corner in zip(lines, corners):
        out.append(re.sub(r"\{[^}]*\}", "{x: %d, y: %d}" % (round(corner["x"]), round(corner["y"])), line, count=1))
    backup = "%s.bak-%s" % (path, time.strftime("%Y%m%d-%H%M%S"))
    with open(backup, "w") as fh:
        fh.write(text)
    with open(path, "w") as fh:
        fh.write(text.replace(block.group(2), "\n".join(out) + "\n"))
    print("\nbacked up to %s" % backup)
    print("written. now: sudo systemctl restart pivac-sentry")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config")
    ap.add_argument("--capture", type=int, metavar="N", help="grab N frames from the camera")
    ap.add_argument("--save", metavar="PATH")
    ap.add_argument("--load", metavar="PATH")
    ap.add_argument("--search", action="store_true")
    ap.add_argument("--truth-air", type=float, metavar="DEGF",
                    help="independent outdoor temperature in F at capture time; required for --search")
    ap.add_argument("--eyecheck", metavar="PATH",
                    help="write a gamma-compressed PNG of the quad(s): the current one alone "
                         "without --search, current (red) and winner (green) with it")
    ap.add_argument("--apply", action="store_true", help="write the winning corners to config.yml")
    args = ap.parse_args()

    cfg, cfg_path = load_config(args.config)
    ox, oy = REGION[0], REGION[1]
    scfg = shift(cfg, ox, oy)

    if args.capture:
        frames = capture(cfg, args.capture)
        if args.save:
            np.savez_compressed(args.save, frames=frames)
            print("saved %s" % args.save)
    elif args.load:
        frames = np.load(args.load)["frames"]
        print("loaded %d frames from %s" % (len(frames), args.load))
    else:
        ap.error("one of --capture or --load is required")

    modes = [mode_of(f, scfg) for f in frames]
    indices = [i for i, m in enumerate(modes) if m in _SANE_RANGE]
    print("frames with exactly one indicator lit: %d of %d" % (len(indices), len(frames)))
    if not indices:
        sys.exit("no mode-bearing frames; is the display cycling?")

    base = scfg["display_warp"]["corners"]
    clean, values, margin = evaluate(frames, modes, scfg, base, indices)
    report("CURRENT quad", clean, values, modes, indices, margin)

    if not args.search:
        if args.eyecheck:
            write_eyecheck(frames, modes, scfg, base, None, args.eyecheck)
        return
    if args.truth_air is None:
        ap.error("--search needs --truth-air: a constant misread scores perfectly on "
                 "self-consistency, so an external reference is what separates right from stable")

    coarse = [(dx, dy, s) for dx in range(-16, 17, 4) for dy in range(-16, 17, 4) for s in (0.96, 1.0, 1.04)]
    sample = indices[::max(1, len(indices) // 120)]
    scored = []
    for dx, dy, s in coarse:
        f, v, m = evaluate(frames, modes, scfg, transform(base, dx, dy, s), sample)
        air = float(np.median(v["air"])) if v.get("air") else None
        penalty = abs(air - args.truth_air) if air is not None else 99.0
        scored.append((round(f, 4), -min(penalty, 20.0), m if m is not None else -99.0, dx, dy, s))
    scored.sort(reverse=True)
    best = scored[0][0]
    plateau = [c for c in scored if c[0] >= best - 1e-9]
    dx = int(round(np.mean([c[3] for c in plateau])))
    dy = int(round(np.mean([c[4] for c in plateau])))
    print("\nbest clean=%.1f%% across a %d-candidate plateau; centre dx=%+d dy=%+d"
          % (best * 100, len(plateau), dx, dy))
    if len(plateau) < 3:
        print("*** narrow optimum -- treat with suspicion, a robust fit has a broad plateau ***")

    fine = []
    for fdx in range(dx - 3, dx + 4):
        for fdy in range(dy - 3, dy + 4):
            f, v, m = evaluate(frames, modes, scfg, transform(base, fdx, fdy, 1.0), sample)
            air = float(np.median(v["air"])) if v.get("air") else None
            penalty = abs(air - args.truth_air) if air is not None else 99.0
            fine.append((round(f, 4), -min(penalty, 20.0), m if m is not None else -99.0, fdx, fdy))
    fine.sort(reverse=True)
    plateau = [c for c in fine if c[0] >= fine[0][0] - 1e-9]
    dx = int(round(np.mean([c[3] for c in plateau])))
    dy = int(round(np.mean([c[4] for c in plateau])))
    print("fine pass: clean=%.1f%% across a %d-candidate plateau; centre dx=%+d dy=%+d"
          % (fine[0][0] * 100, len(plateau), dx, dy))

    winner = transform(base, dx, dy, 1.0)
    wclean, wvalues, wmargin = evaluate(frames, modes, scfg, winner, indices)
    report("WINNER quad", wclean, wvalues, modes, indices, wmargin)

    air = float(np.median(wvalues["air"])) if wvalues.get("air") else None
    if air is not None:
        gap = abs(air - args.truth_air)
        print("\nground truth: air median %.1f F vs reference %.1f F -> %.1f F apart (%s)"
              % (air, args.truth_air, gap, "within the 1-4 F baseline" if gap <= 5 else "*** TOO FAR, do not apply ***"))
    if wclean < clean or (wclean == clean and (wmargin or -99) <= (margin or -99)):
        print("\nno improvement over the current quad in clean rate or margin; not recommending a change")
        return

    absolute = [{"x": c["x"] + ox, "y": c["y"] + oy} for c in winner]
    print("\ncorners: " + "  ".join("{x: %d, y: %d}" % (round(c["x"]), round(c["y"])) for c in absolute))

    if args.eyecheck:
        write_eyecheck(frames, modes, scfg, base, winner, args.eyecheck)
    if args.apply:
        apply_corners(cfg_path, absolute)
    else:
        print("re-run with --apply to write these to %s" % cfg_path)


def write_eyecheck(frames, modes, scfg, base, winner, path):
    """Gamma-compress the blown IR highlights so unlit segments show as grey ghosts.
    Without this the saturated digits are unreadable and a 0 cannot be told from an 8."""
    import cv2
    panels = []
    for mode in VALUE_MODES:
        idx = next((i for i, m in enumerate(modes) if m == mode), None)
        if idx is None:
            continue
        frame = frames[idx]
        vis = cv2.cvtColor((np.clip((frame.astype(float) - 120) / 130.0, 0, 1) ** 0.45 * 255).astype(np.uint8),
                           cv2.COLOR_GRAY2BGR)
        quads = [(base, (0, 0, 255))] + ([(winner, (0, 255, 0))] if winner else [])
        for corners, colour in quads:
            pts = np.array([[int(round(c["x"])), int(round(c["y"]))] for c in corners], np.int32)
            cv2.polylines(vis, [pts], True, colour, 1)
        xs = [c["x"] for q, _ in quads for c in q]
        ys = [c["y"] for q, _ in quads for c in q]
        x0, x1 = max(0, int(min(xs)) - 30), int(max(xs)) + 30
        y0, y1 = max(0, int(min(ys)) - 30), int(max(ys)) + 30
        crop = cv2.resize(vis[y0:y1, x0:x1], None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
        old = _read_display(frame, dict(scfg, display_warp=dict(scfg["display_warp"], corners=base)))
        if winner:
            new = _read_display(frame, dict(scfg, display_warp=dict(scfg["display_warp"], corners=winner)))
            label = "%s  red/old=%s  green/new=%s" % (mode, old or "-", new or "-")
        else:
            label = "%s  live quad reads %s" % (mode, old or "-")
        cv2.putText(crop, label, (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)
        panels.append(crop)
    cv2.imwrite(path, np.vstack(panels))
    print("wrote %s -- the display's real digits are the final check" % path)


if __name__ == "__main__":
    main()
