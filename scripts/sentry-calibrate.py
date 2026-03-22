#!/usr/bin/env python3
"""
sentry-calibrate.py — Tapo C120 / Sentry 2100 calibration utility

Usage:
  # Capture a reference frame and save it as a JPEG
  python scripts/sentry-calibrate.py --capture --rtsp-url "rtsp://user:pass@10.0.0.19:554/stream1"

  # Capture and annotate: draw ROI boxes from a config file onto the saved frame
  python scripts/sentry-calibrate.py --annotate --config /etc/pivac/config.yml

  # Test live reading without Signal K (prints parsed values to stdout)
  python scripts/sentry-calibrate.py --test --rtsp-url "rtsp://user:pass@10.0.0.19:554/stream1" --config /etc/pivac/config.yml

The --capture output is saved to ./sentry-reference.jpg in the current directory.
Transfer it to your Mac to identify pixel coordinates for config.yml.
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
    # Drain the buffer so we get the freshest frame
    for _ in range(5):
        cap.grab()
    ret, frame = cap.retrieve()
    if not ret or frame is None:
        raise RuntimeError("Failed to retrieve frame from stream")
    return frame


# ---------------------------------------------------------------------------
# 7-segment digit recognition
# ---------------------------------------------------------------------------

# Segment layout within a digit bounding box (relative fractions):
#
#   aaa
#  f   b
#  f   b
#   ggg
#  e   c
#  e   c
#   ddd
#
# Each entry is (x_frac, y_frac, w_frac, h_frac) — fraction of digit bbox.
SEGMENT_RECTS = {
    "a": (0.15, 0.00, 0.70, 0.12),  # top horizontal
    "b": (0.80, 0.07, 0.15, 0.38),  # upper right vertical
    "c": (0.80, 0.55, 0.15, 0.38),  # lower right vertical
    "d": (0.15, 0.88, 0.70, 0.12),  # bottom horizontal
    "e": (0.05, 0.55, 0.15, 0.38),  # lower left vertical
    "f": (0.05, 0.07, 0.15, 0.38),  # upper left vertical
    "g": (0.15, 0.44, 0.70, 0.12),  # middle horizontal
}

# Map 7-bit segment state (a,b,c,d,e,f,g) → character
# Bit order: a=64, b=32, c=16, d=8, e=4, f=2, g=1
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
    # Special characters for Sentry error/menu codes
    0b1101101: "E",  # used in ER codes
    0b0000101: "r",
    0b1100111: "A",  # used in ASO/ASC
    0b1100000: "F",
    0b0001101: "C",  # lower C (used in ASC)
    0b0001111: "c",
    0b1111110: "O",  # used in ASO
    0b0111110: "U",
    0b0101111: "d",  # used in dIF
    0b0000001: "-",
    0b0000000: " ",
}


def _segment_brightness(digit_roi: np.ndarray, seg_name: str) -> float:
    """Return mean brightness (0–255) of a segment within a digit ROI."""
    h, w = digit_roi.shape[:2]
    xf, yf, wf, hf = SEGMENT_RECTS[seg_name]
    x1 = int(xf * w)
    y1 = int(yf * h)
    x2 = int((xf + wf) * w)
    y2 = int((yf + hf) * h)
    region = digit_roi[y1:y2, x1:x2]
    if region.size == 0:
        return 0.0
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY) if len(region.shape) == 3 else region
    return float(np.mean(gray))


def read_digit(digit_roi: np.ndarray, threshold: int = 150) -> str:
    """Recognise a single 7-segment digit from its ROI crop."""
    bits = 0
    for i, seg in enumerate(["a", "b", "c", "d", "e", "f", "g"]):
        brightness = _segment_brightness(digit_roi, seg)
        if brightness >= threshold:
            bits |= (1 << (6 - i))

    return SEGMENT_MAP.get(bits, f"?{bits:07b}")


def read_display(frame: np.ndarray, config: dict) -> str:
    """Read the 3-digit display value from a full frame."""
    roi = config["display_roi"]
    display_crop = frame[roi["y"]:roi["y"] + roi["h"],
                         roi["x"]:roi["x"] + roi["w"]]

    result = ""
    threshold = config.get("brightness_threshold", 150)
    for pos in config["digit_positions"]:
        digit_crop = display_crop[pos["y"]:pos["y"] + pos["h"],
                                  pos["x"]:pos["x"] + pos["w"]]
        result += read_digit(digit_crop, threshold)

    return result.strip()


# ---------------------------------------------------------------------------
# LED / indicator detection
# ---------------------------------------------------------------------------

def _roi_is_lit(frame: np.ndarray, coord: dict, threshold: int = 80,
                radius: int = 6) -> bool:
    """Return True if the LED/indicator at (x, y) is illuminated."""
    x, y = coord["x"], coord["y"]
    h, w = frame.shape[:2]
    x1 = max(0, x - radius)
    y1 = max(0, y - radius)
    x2 = min(w, x + radius)
    y2 = min(h, y + radius)
    region = frame[y1:y2, x1:x2]
    if region.size == 0:
        return False
    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    # Green hue range: 40–80 in OpenCV (0–180 scale)
    green_mask = cv2.inRange(hsv, np.array([40, 40, threshold]),
                             np.array([80, 255, 255]))
    return float(np.mean(green_mask)) > 10.0


def read_leds(frame: np.ndarray, config: dict) -> dict:
    """Read the 4 green LED indicator states."""
    threshold = config.get("brightness_threshold", 150)
    leds = config.get("leds", {})
    return {
        "burnerOn":         _roi_is_lit(frame, leds["burner"], threshold),
        "circOn":           _roi_is_lit(frame, leds["circ"], threshold),
        "circAuxOn":        _roi_is_lit(frame, leds["circ_aux"], threshold),
        "thermostatDemand": _roi_is_lit(frame, leds["thermostat_demand"], threshold),
    }


def read_indicators(frame: np.ndarray, config: dict) -> str | None:
    """Return the active display mode based on which indicator light is lit."""
    threshold = config.get("brightness_threshold", 150)
    indicators = config.get("indicators", {})
    for mode, coord in indicators.items():
        if _roi_is_lit(frame, coord, threshold):
            return mode
    return None


# ---------------------------------------------------------------------------
# Temperature conversion
# ---------------------------------------------------------------------------

def f_to_k(f: float) -> float:
    return (f - 32) * 5 / 9 + 273.15


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

def cmd_capture(args):
    """Capture a single reference frame and save to JPEG."""
    logger.info(f"Connecting to {args.rtsp_url} …")
    cap = open_stream(args.rtsp_url)
    logger.info("Connected. Grabbing frame …")
    frame = grab_frame(cap)
    cap.release()

    out = args.output or "sentry-reference.jpg"
    cv2.imwrite(out, frame)
    h, w = frame.shape[:2]
    logger.info(f"Saved {w}×{h} frame to: {out}")
    logger.info("")
    logger.info("Open the image and note the pixel coordinates of:")
    logger.info("  display_roi   — bounding box around all 3 digits (x, y, w, h)")
    logger.info("  digit_positions[0,1,2] — each digit within that box (x, y, w, h)")
    logger.info("  leds.burner / circ / circ_aux / thermostat_demand — centre pixel (x, y)")
    logger.info("  indicators.water_temp / air / gas_input / dhw_temp — centre pixel (x, y)")
    logger.info("")
    logger.info("Then update pivac.Sentry config in /etc/pivac/config.yml")


def cmd_annotate(args):
    """Draw ROI boxes on a saved reference frame using config coords."""
    if not yaml:
        sys.exit("ERROR: PyYAML required for --annotate. pip install pyyaml")
    if not args.image:
        sys.exit("ERROR: --image required for --annotate")

    with open(args.config) as f:
        full_config = yaml.safe_load(f)
    config = full_config.get("pivac.Sentry", {})

    frame = cv2.imread(args.image)
    if frame is None:
        sys.exit(f"ERROR: Could not read image: {args.image}")

    # Draw display ROI
    roi = config.get("display_roi", {})
    if roi:
        cv2.rectangle(frame,
                      (roi["x"], roi["y"]),
                      (roi["x"] + roi["w"], roi["y"] + roi["h"]),
                      (0, 255, 0), 2)
        cv2.putText(frame, "display_roi", (roi["x"], roi["y"] - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # Draw digit positions (relative to display_roi)
        for i, pos in enumerate(config.get("digit_positions", [])):
            ax = roi["x"] + pos["x"]
            ay = roi["y"] + pos["y"]
            cv2.rectangle(frame, (ax, ay),
                          (ax + pos["w"], ay + pos["h"]),
                          (255, 255, 0), 1)
            cv2.putText(frame, f"d{i}", (ax, ay - 3),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

    # Draw LEDs
    for name, coord in config.get("leds", {}).items():
        cv2.circle(frame, (coord["x"], coord["y"]), 8, (0, 200, 0), 2)
        cv2.putText(frame, name, (coord["x"] + 10, coord["y"] + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 0), 1)

    # Draw indicators
    for name, coord in config.get("indicators", {}).items():
        cv2.circle(frame, (coord["x"], coord["y"]), 8, (200, 100, 0), 2)
        cv2.putText(frame, name, (coord["x"] + 10, coord["y"] + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 100, 0), 1)

    out = args.output or "sentry-annotated.jpg"
    cv2.imwrite(out, frame)
    logger.info(f"Annotated image saved to: {out}")


def cmd_test(args):
    """Capture a full display cycle and print parsed values."""
    if not yaml:
        sys.exit("ERROR: PyYAML required for --test. pip install pyyaml")

    with open(args.config) as f:
        full_config = yaml.safe_load(f)
    config = full_config.get("pivac.Sentry", {})

    rtsp_url = args.rtsp_url or config.get("rtsp_url")
    if not rtsp_url:
        sys.exit("ERROR: --rtsp-url required (or set rtsp_url in config)")

    cycle_timeout = config.get("cycle_timeout", 15)
    frame_interval = config.get("frame_interval", 2.5)

    logger.info(f"Connecting to {rtsp_url} …")
    cap = open_stream(rtsp_url)
    logger.info(f"Capturing frames for up to {cycle_timeout}s …")

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
            logger.info(f"  → captured mode '{mode}' = '{value}'")

        if len(collected) >= len(config.get("indicators", {})):
            logger.info("All display modes captured — stopping early.")
            break

        time.sleep(frame_interval)

    cap.release()

    print("\n=== Parsed display values ===")
    for mode, raw in collected.items():
        print(f"  {mode}: raw='{raw}'", end="")
        try:
            val = float(raw)
            if mode in ("water_temp", "dhw_temp", "air"):
                print(f"  →  {val}°F  =  {f_to_k(val):.2f} K")
            elif mode == "gas_input":
                print(f"  →  gas input scale {int(val)}")
            else:
                print()
        except ValueError:
            print(f"  (non-numeric — error/menu code?)")

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
        description="Sentry 2100 / Tapo C120 calibration and test utility")
    parser.add_argument("--capture", action="store_true",
                        help="Capture a reference frame and save as JPEG")
    parser.add_argument("--annotate", action="store_true",
                        help="Draw ROI boxes on a saved reference frame")
    parser.add_argument("--test", action="store_true",
                        help="Capture a live display cycle and print parsed values")
    parser.add_argument("--rtsp-url", metavar="URL",
                        help="RTSP stream URL (overrides config)")
    parser.add_argument("--config", default="/etc/pivac/config.yml",
                        metavar="FILE", help="Path to pivac config.yml")
    parser.add_argument("--image", metavar="FILE",
                        help="Reference image for --annotate")
    parser.add_argument("--output", "-o", metavar="FILE",
                        help="Output filename (default: sentry-reference.jpg / sentry-annotated.jpg)")
    args = parser.parse_args()

    if args.capture:
        if not args.rtsp_url:
            parser.error("--rtsp-url required for --capture")
        cmd_capture(args)
    elif args.annotate:
        cmd_annotate(args)
    elif args.test:
        cmd_test(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
