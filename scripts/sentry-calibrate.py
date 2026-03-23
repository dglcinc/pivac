#!/usr/bin/env python3
"""
sentry-calibrate.py — Tapo C120 / Sentry 2100 calibration utility

Usage:
  # Capture a reference frame and save it as a JPEG
  python scripts/sentry-calibrate.py --capture --rtsp-url "rtsp://user:pass@10.0.0.19:554/stream1"

  # Annotate a saved frame with ROI boxes from config
  python scripts/sentry-calibrate.py --annotate --image sentry-reference.jpg --config config/config.sentry-sample.yml

  # Debug: grab one live frame, save crops + annotated overlay, print brightness values
  python scripts/sentry-calibrate.py --debug --rtsp-url "rtsp://user:pass@10.0.0.19:554/stream1" --config config/config.sentry-sample.yml

  # Test live reading without Signal K (prints parsed values to stdout)
  python scripts/sentry-calibrate.py --test --rtsp-url "rtsp://user:pass@10.0.0.19:554/stream1" --config config/config.sentry-sample.yml

Notes:
  - Uses adaptive thresholds so it works in any lighting / camera mode:
      * Digit recognition uses Otsu's method per digit crop (not the full
        display ROI), giving clean bimodal separation between the black LED
        substrate and the lit segment pixels.
      * LED detection compares spot brightness against local background ratio.
  - The camera can be left in Auto day/night mode; no manual setting needed.
  - Open a captured frame in Preview (Cmd+I shows pixel coords on hover) to
    identify ROI coordinates for config.
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
    """Open an RTSP stream and return a VideoCapture object, or raise."""
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
    """Grab the most recent frame from an open VideoCapture."""
    for _ in range(5):
        cap.grab()
    ret, frame = cap.retrieve()
    if not ret or frame is None:
        raise RuntimeError("Failed to retrieve frame from stream")
    return frame


def to_gray(img: np.ndarray) -> np.ndarray:
    """Convert BGR or already-gray image to single-channel grayscale."""
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
    otsu_val, _ = cv2.threshold(gray, 0, 255,
                                cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return int(otsu_val)


def _segment_brightness(digit_roi: np.ndarray, seg_name: str) -> float:
    h, w = digit_roi.shape[:2]
    xf, yf, wf, hf = SEGMENT_RECTS[seg_name]
    x1, y1 = int(xf * w), int(yf * h)
    x2, y2 = int((xf + wf) * w), int((yf + hf) * h)
    region = digit_roi[y1:y2, x1:x2]
    if region.size == 0:
        return 0.0
    return float(np.mean(to_gray(region)))


def read_digit(digit_roi: np.ndarray, threshold: int) -> str:
    bits = 0
    for i, seg in enumerate(["a", "b", "c", "d", "e", "f", "g"]):
        if _segment_brightness(digit_roi, seg) >= threshold:
            bits |= (1 << (6 - i))
    return SEGMENT_MAP.get(bits, f"?{bits:07b}")


def read_display(frame: np.ndarray, config: dict) -> str:
    """Read the 3-digit display value from a full frame.

    Otsu thresholding is applied per digit crop rather than on the full
    display_roi.  The full ROI includes bright panel background material
    that skews the global histogram and raises the threshold well above
    actual segment pixel values.  Per-digit Otsu separates the dark LED
    substrate from the lit segments far more reliably.
    """
    roi = config["display_roi"]
    display_crop = frame[roi["y"]:roi["y"] + roi["h"],
                         roi["x"]:roi["x"] + roi["w"]]
    result = ""
    for pos in config["digit_positions"]:
        digit_crop = display_crop[pos["y"]:pos["y"] + pos["h"],
                                  pos["x"]:pos["x"] + pos["w"]]
        gray = to_gray(digit_crop)
        threshold = _otsu_threshold(gray)
        logger.debug(f"Per-digit Otsu threshold: {threshold}")
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
    """Return brightness diagnostics for a single LED/indicator position."""
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
# Annotation helper (shared by --annotate and --debug)
# ---------------------------------------------------------------------------

def draw_annotations(frame: np.ndarray, config: dict) -> np.ndarray:
    """Draw display ROI, digit boxes, LED circles, and indicator circles."""
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


def cmd_debug(args):
    """Grab one live frame, save crops + annotated overlay, print all brightness diagnostics."""
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

    # Save plain full frame
    full_path = f"{prefix}-frame.jpg"
    cv2.imwrite(full_path, frame)
    logger.info(f"Full frame saved: {full_path}")

    # Save annotated full frame — shows all ROI boxes on the live image
    ann_path = f"{prefix}-annotated.jpg"
    cv2.imwrite(ann_path, draw_annotations(frame, config))
    logger.info(f"Annotated overlay saved: {ann_path}  <-- check this first")

    # Analyse display_roi crop
    roi = config["display_roi"]
    display_crop = frame[roi["y"]:roi["y"] + roi["h"],
                         roi["x"]:roi["x"] + roi["w"]]
    crop_path = f"{prefix}-display-roi.jpg"
    cv2.imwrite(crop_path, display_crop)

    gray_display = to_gray(display_crop)
    mean_brightness = float(np.mean(gray_display))
    max_brightness = float(np.max(gray_display))
    global_otsu = _otsu_threshold(gray_display)

    print(f"\n=== display_roi (x={roi['x']} y={roi['y']} w={roi['w']} h={roi['h']}) ===")
    print(f"  Saved crop:           {crop_path}")
    print(f"  Mean brightness:      {mean_brightness:.1f}  Max: {max_brightness:.1f}")
    print(f"  Global Otsu:          {global_otsu}  (NOT used — per-digit Otsu shown below)")

    # Analyse each digit crop with its own Otsu threshold
    print("\n=== Digit crops (per-digit Otsu) ===")
    for i, pos in enumerate(config.get("digit_positions", [])):
        digit_crop = display_crop[pos["y"]:pos["y"] + pos["h"],
                                  pos["x"]:pos["x"] + pos["w"]]
        dp = f"{prefix}-digit-{i}.jpg"
        cv2.imwrite(dp, digit_crop)
        g = to_gray(digit_crop)
        dmean, dmax = float(np.mean(g)), float(np.max(g))
        digit_otsu = _otsu_threshold(g)
        char = read_digit(digit_crop, digit_otsu)
        print(f"  d{i}: mean={dmean:.1f}  max={dmax:.1f}  otsu={digit_otsu}  reads='{char}'  "
              f"saved: {dp}")
        if dmean > 80 and dmax < 180:
            print(f"       *** WARN: d{i} looks like panel background (no bright LED pixels).")
            print(f"       ***   If display shows 2 digits, this is expected for the hundreds.")
            print(f"       ***   If display shows 3 digits, increase d{i}.x in digit_positions.")
        print(f"       segments: ", end="")
        for seg in ["a", "b", "c", "d", "e", "f", "g"]:
            b = _segment_brightness(digit_crop, seg)
            lit = "*" if b >= digit_otsu else "."
            print(f"{seg}={b:.0f}{lit} ", end="")
        print()

    # LED brightness diagnostics
    print("\n=== LED brightness (spot / background / ratio) ===")
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

    print(f"\nNext step: open {ann_path} to verify all ROI boxes land on the right areas.")


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
    parser.add_argument("--capture", action="store_true",
                        help="Capture a reference frame from the RTSP stream")
    parser.add_argument("--annotate", action="store_true",
                        help="Draw ROI boxes on a saved reference frame")
    parser.add_argument("--debug", action="store_true",
                        help="Grab one live frame, save crops + annotated overlay, "
                             "print brightness diagnostics")
    parser.add_argument("--test", action="store_true",
                        help="Capture a live display cycle and print parsed values")
    parser.add_argument("--rtsp-url", metavar="URL")
    parser.add_argument("--config", default="/etc/pivac/config.yml", metavar="FILE")
    parser.add_argument("--image", metavar="FILE",
                        help="Reference image for --annotate")
    parser.add_argument("--output", "-o", metavar="FILE",
                        help="Output file / prefix (--debug uses it as a prefix)")
    args = parser.parse_args()

    if args.capture:
        if not args.rtsp_url:
            parser.error("--rtsp-url required for --capture")
        cmd_capture(args)
    elif args.annotate:
        cmd_annotate(args)
    elif args.debug:
        if not args.rtsp_url and not args.config:
            parser.error("--rtsp-url or --config with rtsp_url required for --debug")
        cmd_debug(args)
    elif args.test:
        cmd_test(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
