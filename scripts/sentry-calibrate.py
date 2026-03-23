#!/usr/bin/env python3
"""
sentry-calibrate.py — Tapo C120 / Sentry 2100 calibration utility

Usage:
  # Capture a reference frame
  python scripts/sentry-calibrate.py --capture --rtsp-url "rtsp://user:pass@10.0.0.19:554/stream1"

  # Interactive click-to-calibrate (perspective-aware: click 4 display corners,
  # then digit/LED positions on the de-skewed rectified image)
  python scripts/sentry-calibrate.py --calibrate --image sentry-reference.jpg
  python scripts/sentry-calibrate.py --calibrate --rtsp-url "rtsp://..."

  # Annotate a saved frame with current config overlay
  python scripts/sentry-calibrate.py --annotate --image sentry-reference.jpg --config ...

  # Debug: grab one live frame, save crops + segment visualisations
  python scripts/sentry-calibrate.py --debug --rtsp-url "rtsp://..." --config ...

  # Test live reading (no Signal K)
  python scripts/sentry-calibrate.py --test --rtsp-url "rtsp://..." --config ...

Notes:
  - --calibrate requires matplotlib: pip install matplotlib --break-system-packages
  - Digit recognition: p90 per-segment brightness, threshold = mean+35%*(max-mean).
  - LED/indicator detection: spot-vs-background brightness ratio.
  - Camera can stay in Auto day/night mode.
"""

import argparse
import math
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
# Display extraction (rectangle crop OR perspective warp)
# ---------------------------------------------------------------------------

def _get_display_crop(frame: np.ndarray, config: dict) -> np.ndarray:
    """Return the display area, applying perspective de-skew when available."""
    if "display_warp" in config:
        warp = config["display_warp"]
        src = np.float32([[c["x"], c["y"]] for c in warp["corners"]])
        dst_w, dst_h = warp["dst_w"], warp["dst_h"]
        dst = np.float32([[0, 0], [dst_w, 0], [dst_w, dst_h], [0, dst_h]])
        M = cv2.getPerspectiveTransform(src, dst)
        return cv2.warpPerspective(frame, M, (dst_w, dst_h))
    # Legacy rectangle crop
    roi = config["display_roi"]
    return frame[roi["y"]:roi["y"] + roi["h"],
                 roi["x"]:roi["x"] + roi["w"]]


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
    otsu_val, _ = cv2.threshold(gray, 0, 255,
                                cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return int(otsu_val)


def _digit_threshold(gray: np.ndarray) -> int:
    """35% of the way from crop mean to crop max.  Robust for thin LED lines."""
    mean_val = float(np.mean(gray))
    max_val = float(np.max(gray))
    return int(mean_val + 0.35 * (max_val - mean_val))


def _segment_brightness(digit_roi: np.ndarray, seg_name: str) -> float:
    """90th-percentile brightness in a segment rectangle."""
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
    display_crop = _get_display_crop(frame, config)
    result = ""
    for pos in config["digit_positions"]:
        digit_crop = display_crop[pos["y"]:pos["y"] + pos["h"],
                                  pos["x"]:pos["x"] + pos["w"]]
        gray = to_gray(digit_crop)
        threshold = _digit_threshold(gray)
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
# Annotation helper
# ---------------------------------------------------------------------------

def draw_annotations(frame: np.ndarray, config: dict) -> np.ndarray:
    """Draw display boundary, digit boxes (back-projected if warped), LEDs."""
    annotated = frame.copy()

    if "display_warp" in config:
        warp = config["display_warp"]
        src = np.float32([[c["x"], c["y"]] for c in warp["corners"]])
        dst_w, dst_h = warp["dst_w"], warp["dst_h"]
        dst = np.float32([[0, 0], [dst_w, 0], [dst_w, dst_h], [0, dst_h]])

        # Draw warp quadrilateral
        corners_int = [(int(c["x"]), int(c["y"])) for c in warp["corners"]]
        for j in range(4):
            cv2.line(annotated, corners_int[j], corners_int[(j + 1) % 4],
                     (0, 255, 0), 3)
        cv2.putText(annotated, "display",
                    (corners_int[0][0], corners_int[0][1] - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        # Back-project digit boxes from warped to original coords
        M_inv = cv2.getPerspectiveTransform(dst, src)
        d_colors = [(255, 255, 0), (255, 200, 0), (255, 150, 0)]
        for i, pos in enumerate(config.get("digit_positions", [])):
            box = np.float32([[
                [pos["x"],              pos["y"]],
                [pos["x"] + pos["w"],  pos["y"]],
                [pos["x"] + pos["w"],  pos["y"] + pos["h"]],
                [pos["x"],             pos["y"] + pos["h"]],
            ]])
            proj = cv2.perspectiveTransform(box, M_inv)
            pts = proj.reshape(-1, 2).astype(np.int32)
            cv2.polylines(annotated, [pts], True, d_colors[i], 2)
            cv2.putText(annotated, f"d{i}", tuple(pts[0]),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, d_colors[i], 2)
    else:
        roi = config.get("display_roi", {})
        if roi:
            cv2.rectangle(annotated,
                          (roi["x"], roi["y"]),
                          (roi["x"] + roi["w"], roi["y"] + roi["h"]),
                          (0, 255, 0), 3)
            cv2.putText(annotated, "display_roi",
                        (roi["x"], roi["y"] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
            d_colors = [(255, 255, 0), (255, 200, 0), (255, 150, 0)]
            for i, pos in enumerate(config.get("digit_positions", [])):
                ax2, ay2 = roi["x"] + pos["x"], roi["y"] + pos["y"]
                cv2.rectangle(annotated, (ax2, ay2),
                              (ax2 + pos["w"], ay2 + pos["h"]),
                              d_colors[i], 2)
                cv2.putText(annotated, f"d{i}", (ax2, ay2 - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, d_colors[i], 2)

    for name, coord in config.get("leds", {}).items():
        cv2.circle(annotated, (coord["x"], coord["y"]), 14, (0, 200, 0), 2)
        cv2.putText(annotated, name, (coord["x"] + 16, coord["y"] + 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 0), 2)
    for name, coord in config.get("indicators", {}).items():
        cv2.circle(annotated, (coord["x"], coord["y"]), 14, (0, 100, 255), 2)
        cv2.putText(annotated, name, (coord["x"] + 16, coord["y"] + 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 100, 255), 2)
    return annotated


# ---------------------------------------------------------------------------
# Segment visualisation (debug helper)
# ---------------------------------------------------------------------------

def _save_segment_vis(digit_roi: np.ndarray, threshold: int,
                      prefix: str, idx: int) -> str:
    gray = to_gray(digit_roi)
    vis = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    h, w = vis.shape[:2]
    scale = 5
    vis = cv2.resize(vis, (w * scale, h * scale),
                     interpolation=cv2.INTER_NEAREST)
    for seg_name in ["a", "b", "c", "d", "e", "f", "g"]:
        xf, yf, wf, hf = SEGMENT_RECTS[seg_name]
        x1, y1 = int(xf * w * scale), int(yf * h * scale)
        x2, y2 = int((xf + wf) * w * scale), int((yf + hf) * h * scale)
        p90 = _segment_brightness(digit_roi, seg_name)
        color = (0, 220, 0) if p90 >= threshold else (0, 60, 220)
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 1)
        cv2.putText(vis, f"{seg_name}:{p90:.0f}",
                    (x1 + 2, y1 + 11),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.32, color, 1)
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


def cmd_calibrate(args):
    """Perspective-aware interactive calibration.

    Step 1 — original frame: click the 4 corners of the LED display glass
              in order TL → TR → BR → BL.  A warpPerspective de-skews it.
    Step 2 — rectified frame: click top-left + bottom-right of each digit
              (d0 hundreds, d1 tens, d2 units).  Coordinates are in the
              de-skewed space and go straight into digit_positions.
    Step 3 — original frame: click centres of the 4 LED dots, then the
              4 mode-indicator lights.
    """
    try:
        import platform
        import matplotlib
        if platform.system() == "Darwin":
            matplotlib.use("MacOSX")
        else:
            matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Polygon
    except ImportError:
        sys.exit("ERROR: matplotlib required.\n"
                 "Run: pip install matplotlib --break-system-packages")

    # --- Load frame -------------------------------------------------------
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
        logger.info(f"Frame saved: {saved}")
    else:
        sys.exit("ERROR: --image or --rtsp-url required")

    img_h, img_w = frame.shape[:2]

    def to_rgb(img):
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB) if len(img.shape) == 3 \
               else cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

    fig, ax = plt.subplots(figsize=(16, 9))
    plt.tight_layout(pad=0)

    def show_image(img, w, h):
        ax.cla()
        ax.imshow(to_rgb(img), extent=[0, w, h, 0], aspect='equal')
        ax.set_xlim(0, w)
        ax.set_ylim(h, 0)
        ax.axis('off')
        fig.canvas.draw()

    def set_title(msg):
        ax.set_title(msg, fontsize=11, loc='center',
                     color='white', backgroundcolor='#222', pad=6)
        fig.canvas.draw()

    def collect(n, msg, color, marker='+'):
        set_title(msg)
        pts = plt.ginput(n, timeout=0)
        result = []
        for x, y in pts:
            ix, iy = int(round(x)), int(round(y))
            ax.plot(ix, iy, marker, color=color,
                    markersize=16, markeredgewidth=2.5)
            result.append((ix, iy))
        fig.canvas.draw()
        return result

    print("\n" + "=" * 60)
    print("INTERACTIVE CALIBRATION  (read title bar for each step)")
    print("  Do NOT close the window until all steps complete.")
    print("=" * 60)

    # ---- Step 1: warp corners on original image --------------------------
    show_image(frame, img_w, img_h)
    corner_pts = collect(
        4,
        "STEP 1/3 — LED GLASS CORNERS (original frame): "
        "click  TOP-LEFT → TOP-RIGHT → BOTTOM-RIGHT → BOTTOM-LEFT",
        color="lime"
    )
    # Draw the quadrilateral
    from matplotlib.patches import Polygon as MPoly
    poly = MPoly(corner_pts, closed=True,
                 linewidth=2, edgecolor="lime", facecolor="none")
    ax.add_patch(poly)
    fig.canvas.draw()

    # Compute perspective transform
    src = np.float32(corner_pts)
    def _dist(a, b):
        return math.sqrt((b[0]-a[0])**2 + (b[1]-a[1])**2)
    dst_w = int(max(_dist(corner_pts[0], corner_pts[1]),
                    _dist(corner_pts[3], corner_pts[2])))
    dst_h = int(max(_dist(corner_pts[0], corner_pts[3]),
                    _dist(corner_pts[1], corner_pts[2])))
    dst = np.float32([[0,0],[dst_w,0],[dst_w,dst_h],[0,dst_h]])
    M     = cv2.getPerspectiveTransform(src, dst)
    M_inv = cv2.getPerspectiveTransform(dst, src)
    warped = cv2.warpPerspective(frame, M, (dst_w, dst_h))

    warp_path = (args.output or "sentry-calibrate") + "-rectified.jpg"
    cv2.imwrite(warp_path, warped)
    logger.info(f"Rectified display saved: {warp_path}  "
                f"(size {dst_w}x{dst_h})")
    print(f"  Warp corners: {corner_pts}")
    print(f"  Rectified size: {dst_w}x{dst_h}  (saved: {warp_path})")

    # ---- Step 2: digit positions on RECTIFIED image ---------------------
    show_image(warped, dst_w, dst_h)
    set_title("Switched to RECTIFIED view — ready for digit calibration")
    fig.canvas.draw()

    digits = []
    d_colors = ["#ffff00", "#ffcc00", "#ff9900"]
    dlabels  = [
        ("HUNDREDS (d0)", "blank when value < 100; click approx position"),
        ("TENS     (d1)", ""),
        ("UNITS    (d2)", ""),
    ]
    for i, (dlabel, hint) in enumerate(dlabels):
        hint_str = f"  ({hint})" if hint else ""
        pts = collect(
            2,
            f"STEP 2{'ABC'[i]}/3 — DIGIT {dlabel} (RECTIFIED){hint_str}: "
            f"TOP-LEFT then BOTTOM-RIGHT",
            color=d_colors[i]
        )
        (dx1, dy1), (dx2, dy2) = pts
        rel_x = min(dx1, dx2)
        rel_y = min(dy1, dy2)
        rel_w = abs(dx2 - dx1)
        rel_h = abs(dy2 - dy1)
        digits.append(dict(x=rel_x, y=rel_y, w=rel_w, h=rel_h))
        from matplotlib.patches import Rectangle
        ax.add_patch(Rectangle((rel_x, rel_y), rel_w, rel_h,
                               linewidth=2, edgecolor=d_colors[i],
                               facecolor='none'))
        ax.text(rel_x, rel_y - 6, f"d{i}",
                color=d_colors[i], fontsize=9, fontweight='bold')
        fig.canvas.draw()
        print(f"  d{i}: x={rel_x} y={rel_y} w={rel_w} h={rel_h}  (rectified coords)")

    # ---- Step 3: LEDs and indicators on ORIGINAL image ------------------
    show_image(frame, img_w, img_h)

    led_names = ["burner", "circ", "circ_aux", "thermostat_demand"]
    pts = collect(
        4,
        "STEP 3A/3 — LEDs (original frame): click CENTRE of each dot: "
        "burner → circ → circ_aux → thermostat_demand",
        color="cyan", marker="x"
    )
    leds = {}
    for name, (x, y) in zip(led_names, pts):
        leds[name] = dict(x=x, y=y)
        ax.annotate(name, (x, y), xytext=(x+12, y), color="cyan", fontsize=7)
        print(f"  led {name}: x={x} y={y}")
    fig.canvas.draw()

    ind_names = ["water_temp", "air", "gas_input", "dhw_temp"]
    pts = collect(
        4,
        "STEP 3B/3 — INDICATORS (original frame): click CENTRE of each light: "
        "water_temp → air → gas_input → dhw_temp",
        color="orange", marker="x"
    )
    indicators = {}
    for name, (x, y) in zip(ind_names, pts):
        indicators[name] = dict(x=x, y=y)
        ax.annotate(name, (x, y), xytext=(x+12, y), color="orange", fontsize=7)
        print(f"  indicator {name}: x={x} y={y}")
    fig.canvas.draw()

    set_title("Done! Close this window.")
    plt.show(block=True)

    # ---- Print YAML block -----------------------------------------------
    print("\n" + "=" * 60)
    print("  Paste this block into config/config.sentry-sample.yml")
    print("  (replaces display_roi / display_warp / digit_positions / leds / indicators)")
    print("=" * 60)
    print(f"""
  # Perspective warp: 4 corners of the LED glass in the original frame
  # Order: TL -> TR -> BR -> BL
  display_warp:
    corners:""")
    labels = ["TL", "TR", "BR", "BL"]
    for j, (x, y) in enumerate(corner_pts):
        print(f"      - {{x: {x}, y: {y}}}  # {labels[j]}")
    print(f"    dst_w: {dst_w}")
    print(f"    dst_h: {dst_h}")
    print(f"""
  digit_positions:  # relative to RECTIFIED display""")
    lbl = ["hundreds", "tens", "units"]
    for i, d in enumerate(digits):
        print(f"    - {{x: {d['x']:4d}, y: {d['y']:4d}, "
              f"w: {d['w']:4d}, h: {d['h']:4d}}}  # {lbl[i]}")
    print(f"""
  leds:""")
    for name, c in leds.items():
        print(f"    {name+':':22s} {{x: {c['x']}, y: {c['y']}}}")
    print(f"""
  indicators:""")
    for name, c in indicators.items():
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
    logger.info(f"Full frame: {prefix}-frame.jpg")

    ann_path = f"{prefix}-annotated.jpg"
    cv2.imwrite(ann_path, draw_annotations(frame, config))
    logger.info(f"Annotated overlay: {ann_path}")

    display_crop = _get_display_crop(frame, config)
    rect_path = f"{prefix}-display-rectified.jpg"
    cv2.imwrite(rect_path, display_crop)
    logger.info(f"Rectified display: {rect_path}")

    gray_display = to_gray(display_crop)
    print(f"\n=== Rectified display ({display_crop.shape[1]}x{display_crop.shape[0]}) ===")
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
        print(f"       crop: {dp}   segs: {seg_vis}")
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

    print(f"\nKey file: {rect_path}  (de-skewed display used for recognition)")


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
        sys.exit("ERROR: --rtsp-url required")

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
    parser.add_argument("--capture",   action="store_true")
    parser.add_argument("--calibrate", action="store_true",
                        help="Interactive perspective-aware calibration")
    parser.add_argument("--annotate",  action="store_true")
    parser.add_argument("--debug",     action="store_true")
    parser.add_argument("--test",      action="store_true")
    parser.add_argument("--rtsp-url",  metavar="URL")
    parser.add_argument("--config",    default="/etc/pivac/config.yml",
                        metavar="FILE")
    parser.add_argument("--image",     metavar="FILE")
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
