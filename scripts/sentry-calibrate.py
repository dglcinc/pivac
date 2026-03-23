#!/usr/bin/env python3
"""
sentry-calibrate.py — Tapo C120 / Sentry 2100 calibration utility

Usage:
  # Capture a reference frame
  python scripts/sentry-calibrate.py --capture --rtsp-url "rtsp://user:pass@10.0.0.19:554/stream1"

  # Interactive click-to-calibrate (opens image window, click all corners/centres)
  python scripts/sentry-calibrate.py --calibrate --image sentry-reference.jpg
  python scripts/sentry-calibrate.py --calibrate --rtsp-url "rtsp://..."

  # Annotate a saved frame with ROI boxes from config
  python scripts/sentry-calibrate.py --annotate --image sentry-reference.jpg --config config/config.sentry-sample.yml

  # Debug: grab one live frame, save crops + annotated overlay + segment vis
  python scripts/sentry-calibrate.py --debug --rtsp-url "rtsp://..." --config config/config.sentry-sample.yml

  # Test live reading without Signal K
  python scripts/sentry-calibrate.py --test --rtsp-url "rtsp://..." --config config/config.sentry-sample.yml

Notes:
  - --calibrate requires matplotlib: pip install matplotlib --break-system-packages
  - Digit recognition uses 90th-percentile brightness per segment rectangle
    with threshold = mean + 35% * (max - mean).  This handles thin LED
    segment lines that would be diluted into near-background by a mean.
  - LED detection uses spot-vs-background brightness ratio.
  - Camera can stay in Auto day/night mode.
"""

import argparse
import sys
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np
except ImportError:
    sys.exit("ERROR: opencv-python-headless not installed.\n"
             "Run: pip install opencv-python-headless --break-system-packages")

try:
    import yaml
except ImportError:
    yaml = None


# ---------------------------------------------------------------------------
# RTSP capture helpers
# ---------------------------------------------------------------------------

def open_stream(rtsp_url: str, timeout_sec: int = 10):
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if cap.isOpened():
            return cap
        time.sleep(0.5)
    cap.release()
    raise RuntimeError(f"Could not open RTSP stream: {rtsp_url}")


def grab_frame(cap) -> np.ndarray:
    for _ in range(5):
        cap.grab()
    ret, frame = cap.retrieve()
    if not ret or frame is None:
        raise RuntimeError("Failed to retrieve frame from stream")
    return frame


def to_gray(img: np.ndarray) -> np.ndarray:
    if len(img.shape) == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


# ---------------------------------------------------------------------------
# 7-segment digit recognition
# ---------------------------------------------------------------------------

SEGMENT_RECTS = {
    "a": (0.15, 0.00, 0.70, 0.12),  # top horizontal
    "b": (0.80, 0.07, 0.15, 0.38),  # upper right vertical
    "c": (0.80, 0.55, 0.15, 0.38),  # lower right vertical
    "d": (0.15, 0.88, 0.70, 0.12),  # bottom horizontal
    "e": (0.05, 0.55, 0.15, 0.38),  # lower left vertical
    "f": (0.05, 0.07, 0.15, 0.38),  # upper left vertical
    "g": (0.15, 0.44, 0.70, 0.12),  # middle horizontal
}

SEGMENT_MAP = {
    0b1110111: "0",
    0b0010010: "1",
    0b1011101: "2",
    0b1011011: "3",
    0b0111010: "4",
    0b1101011: "5",
    0b1101111: "6",
    0b1010010: "7",
    0b1111111: "8",
    0b1111011: "9",
    0b1101101: "E",
    0b0000101: "r",
    0b1100111: "A",
    0b1100000: "F",
    0b0001101: "C",
    0b0001111: "c",
    0b1111110: "O",
    0b0111110: "U",
    0b0101111: "d",
    0b0000001: "-",
    0b0000000: " ",
}


def _otsu_threshold(gray: np.ndarray) -> int:
    """Otsu threshold (kept for reference / display in --debug output)."""
    otsu_val, _ = cv2.threshold(gray, 0, 255,
                                cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return int(otsu_val)


def _digit_threshold(gray: np.ndarray) -> int:
    """Threshold for segment-lit detection within a digit crop.

    Placed 35% of the way from the crop mean to the crop maximum.  More
    reliable than Otsu when lit segments occupy only a small fraction of
    the crop (Otsu then splits on dark-substrate vs mid-gray background
    instead of background vs lit-segment).
    """
    mean_val = float(np.mean(gray))
    max_val = float(np.max(gray))
    return int(mean_val + 0.35 * (max_val - mean_val))


def _segment_brightness(digit_roi: np.ndarray, seg_name: str) -> float:
    """90th-percentile brightness within a segment's measurement rectangle.

    Using p90 rather than mean handles thin LED segment lines: even when a
    segment is only a few pixels wide, p90 reliably captures those bright
    pixels rather than averaging them into the surrounding background.
    """
    h, w = digit_roi.shape[:2]
    xf, yf, wf, hf = SEGMENT_RECTS[seg_name]
    x1, y1 = int(xf * w), int(yf * h)
    x2, y2 = int((xf + wf) * w), int((yf + hf) * h)
    region = digit_roi[y1:y2, x1:x2]
    if region.size == 0:
        return 0.0
    return float(np.percentile(to_gray(region), 90))


def read_digit(digit_roi: np.ndarray, threshold: int) -> str:
    bits = 0
    for i, seg in enumerate(["a", "b", "c", "d", "e", "f", "g"]):
        if _segment_brightness(digit_roi, seg) >= threshold:
            bits |= (1 << (6 - i))
    return SEGMENT_MAP.get(bits, f"?{bits:07b}")


def read_display(frame: np.ndarray, config: dict) -> str:
    """Read the 3-digit display value from a full frame."""
    roi = config["display_roi"]
    display_crop = frame[roi["y"]:roi["y"] + roi["h"],
                         roi["x"]:roi["x"] + roi["w"]]
    result = ""
    for pos in config["digit_positions"]:
        digit_crop = display_crop[pos["y"]:pos["y"] + pos["h"],
                                  pos["x"]:pos["x"] + pos["w"]]
        gray = to_gray(digit_crop)
        threshold = _digit_threshold(gray)
        logger.debug(f"digit threshold: {threshold}")
        result += read_digit(digit_crop, threshold)
    return result.strip()


# ---------------------------------------------------------------------------
# LED / indicator detection
# ---------------------------------------------------------------------------

def _roi_is_lit(frame: np.ndarray, coord: dict,
                spot_radius: int = 8, bg_radius: int = 25,
                ratio: float = 1.4) -> bool:
    x, y = coord["x"], coord["y"]
    h, w = frame.shape[:2]
    gray = to_gray(frame)
    sx1, sy1 = max(0, x - spot_radius), max(0, y - spot_radius)
    sx2, sy2 = min(w, x + spot_radius), min(h, y + spot_radius)
    spot = gray[sy1:sy2, sx1:sx2]
    if spot.size == 0:
        return False
    spot_brightness = float(np.mean(spot))
    bx1, by1 = max(0, x - bg_radius), max(0, y - bg_radius)
    bx2, by2 = min(w, x + bg_radius), min(h, y + bg_radius)
    bg_brightness = float(np.mean(gray[by1:by2, bx1:bx2]))
    if bg_brightness < 1.0:
        bg_brightness = 1.0
    return spot_brightness >= bg_brightness * ratio


def _roi_brightness_info(frame: np.ndarray, coord: dict,
                         spot_radius: int = 8, bg_radius: int = 25) -> dict:
    x, y = coord["x"], coord["y"]
    h, w = frame.shape[:2]
    gray = to_gray(frame)
    sx1, sy1 = max(0, x - spot_radius), max(0, y - spot_radius)
    sx2, sy2 = min(w, x + spot_radius), min(h, y + spot_radius)
    spot_brightness = float(np.mean(gray[sy1:sy2, sx1:sx2]))
    bx1, by1 = max(0, x - bg_radius), max(0, y - bg_radius)
    bx2, by2 = min(w, x + bg_radius), min(h, y + bg_radius)
    bg_brightness = float(np.mean(gray[by1:by2, bx1:bx2]))
    ratio = spot_brightness / max(bg_brightness, 1.0)
    return {"spot": round(spot_brightness, 1), "bg": round(bg_brightness, 1),
            "ratio": round(ratio, 2)}


def read_leds(frame: np.ndarray, config: dict) -> dict:
    ratio = config.get("led_ratio", 1.4)
    leds = config.get("leds", {})
    return {
        "burnerOn":         _roi_is_lit(frame, leds["burner"],            ratio=ratio),
        "circOn":           _roi_is_lit(frame, leds["circ"],              ratio=ratio),
        "circAuxOn":        _roi_is_lit(frame, leds["circ_aux"],          ratio=ratio),
        "thermostatDemand": _roi_is_lit(frame, leds["thermostat_demand"], ratio=ratio),
    }


def read_indicators(frame: np.ndarray, config: dict) -> str | None:
    ratio = config.get("led_ratio", 1.4)
    for mode, coord in config.get("indicators", {}).items():
        if _roi_is_lit(frame, coord, ratio=ratio):
            return mode
    return None


# ---------------------------------------------------------------------------
# Temperature conversion
# ---------------------------------------------------------------------------

def f_to_k(f: float) -> float:
    return (f - 32) * 5 / 9 + 273.15


# ---------------------------------------------------------------------------
# Annotation helpers
# ---------------------------------------------------------------------------

def draw_annotations(frame: np.ndarray, config: dict) -> np.ndarray:
    annotated = frame.copy()
    roi = config.get("display_roi", {})
    if roi:
        cv2.rectangle(annotated,
                      (roi["x"], roi["y"]),
                      (roi["x"] + roi["w"], roi["y"] + roi["h"]),
                      (0, 255, 0), 3)
        cv2.putText(annotated, "display_roi", (roi["x"], roi["y"] - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        for i, pos in enumerate(config.get("digit_positions", [])):
            ax, ay = roi["x"] + pos["x"], roi["y"] + pos["y"]
            cv2.rectangle(annotated, (ax, ay),
                          (ax + pos["w"], ay + pos["h"]),
                          (255, 255, 0), 2)
            cv2.putText(annotated, f"d{i}", (ax, ay - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
    for name, coord in config.get("leds", {}).items():
        cv2.circle(annotated, (coord["x"], coord["y"]), 14, (0, 200, 0), 2)
        cv2.putText(annotated, name, (coord["x"] + 16, coord["y"] + 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 0), 2)
    for name, coord in config.get("indicators", {}).items():
        cv2.circle(annotated, (coord["x"], coord["y"]), 14, (0, 100, 255), 2)
        cv2.putText(annotated, name, (coord["x"] + 16, coord["y"] + 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 100, 255), 2)
    return annotated


def _save_segment_vis(digit_roi: np.ndarray, threshold: int,
                      prefix: str, idx: int) -> str:
    """Save a 4x upscaled digit crop with segment rectangles colour-coded.

    Green rectangle = segment detected as lit (p90 >= threshold).
    Red rectangle   = segment detected as off.
    Brightness value shown is the p90 used for the decision.
    """
    gray = to_gray(digit_roi)
    vis = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    h, w = vis.shape[:2]
    scale = 5
    vis = cv2.resize(vis, (w * scale, h * scale),
                     interpolation=cv2.INTER_NEAREST)
    for seg_name in ["a", "b", "c", "d", "e", "f", "g"]:
        xf, yf, wf, hf = SEGMENT_RECTS[seg_name]
        x1 = int(xf * w * scale)
        y1 = int(yf * h * scale)
        x2 = int((xf + wf) * w * scale)
        y2 = int((yf + hf) * h * scale)
        p90 = _segment_brightness(digit_roi, seg_name)
        lit = p90 >= threshold
        color = (0, 220, 0) if lit else (0, 60, 220)
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 1)
        cv2.putText(vis, f"{seg_name}:{p90:.0f}",
                    (x1 + 2, y1 + 11),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.32, color, 1)
    # Mark the threshold
    cv2.putText(vis, f"thr={threshold}",
                (2, vis.shape[0] - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
    path = f"{prefix}-digit-{idx}-segs.jpg"
    cv2.imwrite(path, vis)
    return path


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

def cmd_capture(args):
    logger.info(f"Connecting to {args.rtsp_url} ...")
    cap = open_stream(args.rtsp_url)
    logger.info("Connected. Grabbing frame ...")
    frame = grab_frame(cap)
    cap.release()
    out = args.output or "sentry-reference.jpg"
    cv2.imwrite(out, frame)
    h, w = frame.shape[:2]
    logger.info(f"Saved {w}x{h} frame to: {out}")
    logger.info("Open in Preview — hover to get pixel coords (Cmd+I for inspector).")


def cmd_calibrate(args):
    """Interactive: open frame in a window, click all corners/centres, print YAML."""
    try:
        import platform
        import matplotlib
        if platform.system() == "Darwin":
            matplotlib.use("MacOSX")
        else:
            matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
    except ImportError:
        sys.exit(
            "ERROR: matplotlib is required for --calibrate.\n"
            "Run: pip install matplotlib --break-system-packages"
        )

    if args.image:
        frame = cv2.imread(args.image)
        if frame is None:
            sys.exit(f"ERROR: Could not read image: {args.image}")
        logger.info(f"Using image: {args.image}")
    elif args.rtsp_url:
        logger.info(f"Capturing frame from {args.rtsp_url} ...")
        cap = open_stream(args.rtsp_url)
        frame = grab_frame(cap)
        cap.release()
        saved = (args.output or "sentry-calibrate") + "-frame.jpg"
        cv2.imwrite(saved, frame)
        logger.info(f"Frame saved to {saved} (use --image {saved} to recalibrate)")
    else:
        sys.exit("ERROR: --image or --rtsp-url required for --calibrate")

    img_h, img_w = frame.shape[:2]
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) if len(frame.shape) == 3 \
          else cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)

    fig, ax = plt.subplots(figsize=(16, 9))
    ax.imshow(rgb, extent=[0, img_w, img_h, 0], aspect='equal')
    ax.set_xlim(0, img_w)
    ax.set_ylim(img_h, 0)
    ax.axis('off')
    plt.tight_layout(pad=0)

    def _set_title(msg):
        ax.set_title(msg, fontsize=11, loc='center',
                     color='white', backgroundcolor='#222', pad=6)
        fig.canvas.draw()

    def collect(n, msg, color, marker='+'):
        _set_title(msg)
        pts = plt.ginput(n, timeout=0)
        out = []
        for x, y in pts:
            ix, iy = int(round(x)), int(round(y))
            ax.plot(ix, iy, marker, color=color,
                    markersize=16, markeredgewidth=2.5)
            out.append((ix, iy))
        fig.canvas.draw()
        return out

    def draw_box(p1, p2, color, label=''):
        x1, y1 = p1
        x2, y2 = p2
        ax.add_patch(Rectangle(
            (min(x1, x2), min(y1, y2)),
            abs(x2 - x1), abs(y2 - y1),
            linewidth=2, edgecolor=color, facecolor='none'
        ))
        if label:
            ax.text(min(x1, x2), min(y1, y2) - 8, label,
                    color=color, fontsize=9, fontweight='bold')
        fig.canvas.draw()

    print("\n" + "=" * 60)
    print("INTERACTIVE CALIBRATION")
    print("  Read each prompt in the WINDOW TITLE BAR, then click.")
    print("  DO NOT close the window until all steps are done.")
    print("=" * 60)

    results = {}

    pts = collect(2,
        "STEP 1/3 — LED GLASS:  click TOP-LEFT corner  then  BOTTOM-RIGHT corner",
        color="lime")
    (x1, y1), (x2, y2) = pts
    roi_x, roi_y = min(x1, x2), min(y1, y2)
    roi_w, roi_h = abs(x2 - x1), abs(y2 - y1)
    results["display_roi"] = dict(x=roi_x, y=roi_y, w=roi_w, h=roi_h)
    draw_box(pts[0], pts[1], "lime", "display_roi")
    print(f"  display_roi: x={roi_x} y={roi_y} w={roi_w} h={roi_h}")

    digits = []
    digit_labels = [
        ("HUNDREDS (d0)", "blank when value < 100; click approximate position"),
        ("TENS     (d1)", ""),
        ("UNITS    (d2)", ""),
    ]
    colors_d = ["#ffff00", "#ffcc00", "#ff9900"]
    for i, (dlabel, hint) in enumerate(digit_labels):
        hint_str = f"  ({hint})" if hint else ""
        pts = collect(2,
            f"STEP 2{'ABC'[i]}/3 — DIGIT {dlabel}{hint_str}:"
            f"  TOP-LEFT  then  BOTTOM-RIGHT",
            color=colors_d[i])
        (dx1, dy1), (dx2, dy2) = pts
        rel_x = min(dx1, dx2) - roi_x
        rel_y = min(dy1, dy2) - roi_y
        rel_w = abs(dx2 - dx1)
        rel_h = abs(dy2 - dy1)
        digits.append(dict(x=rel_x, y=rel_y, w=rel_w, h=rel_h))
        draw_box(pts[0], pts[1], colors_d[i], f"d{i}")
        print(f"  d{i}: x={rel_x} y={rel_y} w={rel_w} h={rel_h}  (relative to display_roi)")
    results["digit_positions"] = digits

    led_names = ["burner", "circ", "circ_aux", "thermostat_demand"]
    pts = collect(4,
        "STEP 3A/3 — LEDs: click centre of each dot in order: "
        "burner → circ → circ_aux → thermostat_demand",
        color="cyan", marker="x")
    results["leds"] = {}
    for name, (x, y) in zip(led_names, pts):
        results["leds"][name] = dict(x=x, y=y)
        ax.annotate(name, (x, y), xytext=(x + 12, y), color="cyan", fontsize=7)
        print(f"  led {name}: x={x} y={y}")
    fig.canvas.draw()

    ind_names = ["water_temp", "air", "gas_input", "dhw_temp"]
    pts = collect(4,
        "STEP 3B/3 — MODE INDICATORS: click centre of each bottom light: "
        "water_temp → air → gas_input → dhw_temp",
        color="orange", marker="x")
    results["indicators"] = {}
    for name, (x, y) in zip(ind_names, pts):
        results["indicators"][name] = dict(x=x, y=y)
        ax.annotate(name, (x, y), xytext=(x + 12, y), color="orange", fontsize=7)
        print(f"  indicator {name}: x={x} y={y}")
    fig.canvas.draw()

    _set_title("Done! Close this window.")
    plt.show(block=True)

    r = results["display_roi"]
    print("\n" + "=" * 60)
    print("  Paste this block into config/config.sentry-sample.yml")
    print("  (replace display_roi / digit_positions / leds / indicators)")
    print("=" * 60)
    print(f"""
  display_roi:
    x: {r['x']}
    y: {r['y']}
    w: {r['w']}
    h: {r['h']}

  digit_positions:""")
    lbl = ["hundreds", "tens", "units"]
    for i, d in enumerate(results["digit_positions"]):
        print(f"    - {{x: {d['x']:4d}, y: {d['y']:4d}, "
              f"w: {d['w']:4d}, h: {d['h']:4d}}}  # {lbl[i]}")
    print(f"""
  leds:""")
    for name, c in results["leds"].items():
        print(f"    {name+':':22s} {{x: {c['x']}, y: {c['y']}}}")
    print(f"""
  indicators:""")
    for name, c in results["indicators"].items():
        print(f"    {name+':':12s} {{x: {c['x']}, y: {c['y']}}}")
    print()


def cmd_debug(args):
    if not yaml:
        sys.exit("ERROR: PyYAML required. pip install pyyaml")
    with open(args.config) as f:
        full_config = yaml.safe_load(f)
    config = full_config.get("pivac.Sentry", {})
    rtsp_url = args.rtsp_url or config.get("rtsp_url")
    if not rtsp_url:
        sys.exit("ERROR: --rtsp-url required")

    prefix = args.output or "sentry-debug"

    logger.info(f"Connecting to {rtsp_url} ...")
    cap = open_stream(rtsp_url)
    frame = grab_frame(cap)
    cap.release()

    cv2.imwrite(f"{prefix}-frame.jpg", frame)
    logger.info(f"Full frame saved: {prefix}-frame.jpg")

    ann_path = f"{prefix}-annotated.jpg"
    cv2.imwrite(ann_path, draw_annotations(frame, config))
    logger.info(f"Annotated overlay: {ann_path}")

    roi = config["display_roi"]
    display_crop = frame[roi["y"]:roi["y"] + roi["h"],
                         roi["x"]:roi["x"] + roi["w"]]
    cv2.imwrite(f"{prefix}-display-roi.jpg", display_crop)

    gray_display = to_gray(display_crop)
    print(f"\n=== display_roi (x={roi['x']} y={roi['y']} "
          f"w={roi['w']} h={roi['h']}) ===")
    print(f"  Mean: {np.mean(gray_display):.1f}  "
          f"Max: {np.max(gray_display):.1f}  "
          f"Otsu: {_otsu_threshold(gray_display)}")

    print("\n=== Digit crops ===")
    for i, pos in enumerate(config.get("digit_positions", [])):
        digit_crop = display_crop[pos["y"]:pos["y"] + pos["h"],
                                  pos["x"]:pos["x"] + pos["w"]]
        dp = f"{prefix}-digit-{i}.jpg"
        cv2.imwrite(dp, digit_crop)
        g = to_gray(digit_crop)
        dmean, dmax = float(np.mean(g)), float(np.max(g))
        thr = _digit_threshold(g)
        char = read_digit(digit_crop, thr)
        seg_vis = _save_segment_vis(digit_crop, thr, prefix, i)
        print(f"  d{i}: mean={dmean:.1f}  max={dmax:.1f}  "
              f"threshold={thr}  reads='{char}'")
        print(f"       crop: {dp}   segments: {seg_vis}")
        print(f"       ", end="")
        for seg in ["a", "b", "c", "d", "e", "f", "g"]:
            p90 = _segment_brightness(digit_crop, seg)
            lit = "*" if p90 >= thr else "."
            print(f"{seg}={p90:.0f}{lit} ", end="")
        print()

    print("\n=== LED brightness ===")
    print(f"  (need ratio >= {config.get('led_ratio', 1.4)} to register as lit)")
    for name, coord in config.get("leds", {}).items():
        info = _roi_brightness_info(frame, coord)
        lit = "LIT" if info["ratio"] >= config.get("led_ratio", 1.4) else "off"
        print(f"  {name:20s}: spot={info['spot']:5.1f}  bg={info['bg']:5.1f}  "
              f"ratio={info['ratio']:.2f}  -> {lit}")

    print("\n=== Indicator brightness ===")
    for name, coord in config.get("indicators", {}).items():
        info = _roi_brightness_info(frame, coord)
        lit = "LIT" if info["ratio"] >= config.get("led_ratio", 1.4) else "off"
        print(f"  {name:20s}: spot={info['spot']:5.1f}  bg={info['bg']:5.1f}  "
              f"ratio={info['ratio']:.2f}  -> {lit}")

    print(f"\nOpen {ann_path} and the *-segs.jpg files to diagnose alignment.")


def cmd_annotate(args):
    if not yaml:
        sys.exit("ERROR: PyYAML required. pip install pyyaml")
    if not args.image:
        sys.exit("ERROR: --image required for --annotate")
    with open(args.config) as f:
        full_config = yaml.safe_load(f)
    config = full_config.get("pivac.Sentry", {})
    frame = cv2.imread(args.image)
    if frame is None:
        sys.exit(f"ERROR: Could not read image: {args.image}")
    out = args.output or "sentry-annotated.jpg"
    cv2.imwrite(out, draw_annotations(frame, config))
    logger.info(f"Annotated image saved to: {out}")


def cmd_test(args):
    if not yaml:
        sys.exit("ERROR: PyYAML required. pip install pyyaml")
    with open(args.config) as f:
        full_config = yaml.safe_load(f)
    config = full_config.get("pivac.Sentry", {})
    rtsp_url = args.rtsp_url or config.get("rtsp_url")
    if not rtsp_url:
        sys.exit("ERROR: --rtsp-url required (or set rtsp_url in config)")

    cycle_timeout = config.get("cycle_timeout", 15)
    frame_interval = config.get("frame_interval", 2.5)

    logger.info(f"Connecting to {rtsp_url} ...")
    cap = open_stream(rtsp_url)
    logger.info(f"Capturing frames for up to {cycle_timeout}s ...")

    collected = {}
    last_frame = None
    deadline = time.time() + cycle_timeout

    while time.time() < deadline:
        try:
            frame = grab_frame(cap)
            last_frame = frame
        except RuntimeError as e:
            logger.warning(f"Frame grab failed: {e}")
            time.sleep(frame_interval)
            continue

        mode = read_indicators(frame, config)
        value = read_display(frame, config)
        logger.info(f"  frame: display='{value}'  mode={mode}")

        if mode and mode not in collected:
            collected[mode] = value
            logger.info(f"  -> captured '{mode}' = '{value}'")

        if len(collected) >= len(config.get("indicators", {})):
            logger.info("All display modes captured.")
            break

        time.sleep(frame_interval)

    cap.release()

    print("\n=== Parsed display values ===")
    for mode, raw in collected.items():
        print(f"  {mode}: raw='{raw}'", end="")
        try:
            val = float(raw)
            if mode in ("water_temp", "dhw_temp", "air"):
                print(f"  ->  {val}F  =  {f_to_k(val):.2f} K")
            elif mode == "gas_input":
                print(f"  ->  gas input scale {int(val)}")
            else:
                print()
        except ValueError:
            print(f"  (non-numeric)")

    if last_frame is not None:
        leds = read_leds(last_frame, config)
        print("\n=== LED states ===")
        for k, v in leds.items():
            print(f"  {k}: {'ON' if v else 'off'}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sentry 2100 / Tapo C120 calibration utility")
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--calibrate", action="store_true",
                        help="Interactive: click corners/centres in a window")
    parser.add_argument("--annotate", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--rtsp-url", metavar="URL")
    parser.add_argument("--config", default="/etc/pivac/config.yml", metavar="FILE")
    parser.add_argument("--image", metavar="FILE")
    parser.add_argument("--output", "-o", metavar="FILE")
    args = parser.parse_args()

    if args.capture:
        if not args.rtsp_url:
            parser.error("--rtsp-url required for --capture")
        cmd_capture(args)
    elif args.calibrate:
        cmd_calibrate(args)
    elif args.annotate:
        cmd_annotate(args)
    elif args.debug:
        cmd_debug(args)
    elif args.test:
        cmd_test(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
