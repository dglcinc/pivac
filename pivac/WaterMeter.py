"""
pivac.WaterMeter — Sensus iPerl water-meter LCD reader via RTSP camera.

Reads the iPerl's reflective-LCD totalizer (7 integer + 2 fractional gallon
digits) from a Tapo camera and publishes the cumulative reading to Signal K.

Unlike pivac.Sentry (a self-lit 7-segment *LED*), this is a reflective *LCD*:
"off" segments are a faint grey, not black, so per-segment brightness
thresholding cannot cleanly separate on from off.  Instead each digit is read
by **whole-glyph template matching** (normalized cross-correlation against a
library of glyph images), which uses the entire shape and is robust to the
LCD's low, uneven contrast — the way the display is actually read by eye.

Pipeline per cycle:
  1. Grab several frames over `capture_seconds` from the RTSP stream.
  2. Perspective-warp the (rotated/skewed) LCD flat using `display_warp`.
  3. Illumination-flatten each digit cell (divide by a large blur) to remove
     the brightness gradient/glare, then CLAHE.
  4. Classify each of the 9 digit cells against the template library.
  5. Integer digits: median of the per-frame readings (drops one-frame
     misreads).  Decimal digits: used only when stable across the frames
     (= no flow); when they change across frames (= water flowing) the reading
     is floored to whole gallons.  Flooring is conservative, so it never
     overshoots the monotonic guard; the next static read re-syncs the exact
     total.
  6. Monotonic guard: the published total only ever increases and rejects
     implausible single-cycle jumps.

Required config keys:
    rtsp_url        RTSP stream URL (include camera credentials)
    display_warp    {corners: [{x,y}x4 TL,TR,BR,BL], dst_w, dst_h}
    digit_boxes     list of 9 {x,y,w,h} in rectified coords (7 int + 2 dec)
    template_dir    directory of <glyph>.png template images (0-9, any subset)

Optional config keys:
    int_digits      number of leading integer digits   (default: 7)
    dec_digits      number of trailing fractional digits (default: 2)
    capture_seconds per-cycle frame-grab window in sec  (default: 5)
    min_corr        min cross-correlation to trust a digit (default: 0.45)
    min_valid_frames frames with a full integer read required (default: 2)
    max_reading_jump max plausible per-cycle increase, gal (default: 100)
    gal_indicator   {x,y} in rectified coords — consumption-screen confirm
                    (optional; skipped if absent)
    daemon_sleep    seconds between cycles (framework key; recommend 15)

Signal K paths emitted:
    environment.water.domestic.consumption  number, gallons (monotonic cumulative)
    environment.water.domestic.flowing      number 0/1 (decimal-digit instability)
"""

import logging
import os
import statistics
import time

# Quiet libavcodec's H.264 SEI chatter that OpenCV's FFmpeg backend floods into
# journald.  Must be set before cv2/FFmpeg initialises.  8 = AV_LOG_FATAL.
os.environ.setdefault("OPENCV_FFMPEG_LOGLEVEL", "8")

logger = logging.getLogger(__name__)

# Persisted across status() calls within a daemon process for the monotonic
# guard.  Resets on restart (the next reading re-seeds the baseline).
_state = {"last_total": None}
_templates_cache = {"dir": None, "mtime": None, "data": None}

CONSUMPTION_PATH = "environment.water.domestic.consumption"
FLOWING_PATH = "environment.water.domestic.flowing"


# ---------------------------------------------------------------------------
# CV imports — deferred so the module imports without opencv installed.
# ---------------------------------------------------------------------------

def _require_cv():
    try:
        import cv2
        import numpy as np
        return cv2, np
    except ImportError:
        raise ImportError(
            "WaterMeter module requires opencv-python-headless. "
            "Run: pip install opencv-python-headless --break-system-packages"
        )


# ---------------------------------------------------------------------------
# RTSP
# ---------------------------------------------------------------------------

def _open_stream(rtsp_url: str, timeout_sec: int = 10):
    cv2, _ = _require_cv()
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if cap.isOpened():
            return cap
        time.sleep(0.5)
    cap.release()
    raise RuntimeError("Could not open RTSP stream: %s" % rtsp_url)


# ---------------------------------------------------------------------------
# Display rectification + cell preprocessing
# (must match scripts/wm-calibrate.py template generation exactly)
# ---------------------------------------------------------------------------

def _rectify(frame, config: dict):
    cv2, np = _require_cv()
    warp = config["display_warp"]
    src = np.float32([[c["x"], c["y"]] for c in warp["corners"]])
    dw, dh = warp["dst_w"], warp["dst_h"]
    dst = np.float32([[0, 0], [dw, 0], [dw, dh], [0, dh]])
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(gray, M, (dw, dh))


def _prep_cell(cell):
    """Resize to 40x64, illumination-flatten, CLAHE.  Returns float32."""
    cv2, np = _require_cv()
    c = cv2.resize(cell, (40, 64))
    bg = cv2.GaussianBlur(c.astype(np.float32), (0, 0), 12)
    flat = np.clip(c.astype(np.float32) / (bg + 1e-3) * 128, 0, 255).astype(np.uint8)
    return cv2.createCLAHE(2.0, (4, 4)).apply(flat).astype(np.float32)


def _digit_cell(rect, box):
    return _prep_cell(rect[box["y"]:box["y"] + box["h"],
                           box["x"]:box["x"] + box["w"]])


# ---------------------------------------------------------------------------
# Template library + classification
# ---------------------------------------------------------------------------

def _load_templates(template_dir: str):
    cv2, np = _require_cv()
    try:
        mtime = max((os.path.getmtime(os.path.join(template_dir, f))
                     for f in os.listdir(template_dir) if f.endswith(".png")),
                    default=None)
    except FileNotFoundError:
        raise RuntimeError("WaterMeter: template_dir not found: %s" % template_dir)
    if (_templates_cache["dir"] == template_dir
            and _templates_cache["mtime"] == mtime):
        return _templates_cache["data"]
    # Multiple exemplars per glyph: filename "<glyph>.png" or "<glyph>_<tag>.png"
    # (e.g. 4_a.png, 4_b.png) — grouped by the leading glyph char.  Capturing a
    # glyph from several positions/lighting makes matching robust to the LCD's
    # uneven illumination across the display.
    data = {}
    for f in os.listdir(template_dir):
        if not f.endswith(".png"):
            continue
        glyph = os.path.splitext(f)[0].split("_")[0]
        img = cv2.imread(os.path.join(template_dir, f), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        if img.shape != (64, 40):
            img = cv2.resize(img, (40, 64))
        data.setdefault(glyph, []).append(img.astype(np.float32))
    if not data:
        raise RuntimeError("WaterMeter: no templates in %s" % template_dir)
    _templates_cache.update(dir=template_dir, mtime=mtime, data=data)
    logger.info("WaterMeter: loaded templates for %d glyphs (%s)",
                len(data), " ".join("%s:%d" % (g, len(v)) for g, v in sorted(data.items())))
    return data


def _ncc(a, b):
    _, np = _require_cv()
    a = a - a.mean()
    b = b - b.mean()
    d = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float((a * b).sum() / d) if d else 0.0


def _classify(cell, templates, min_corr):
    """Return (glyph, score) for the best-matching glyph (max correlation over
    that glyph's exemplars), or (None, score) if below min_corr."""
    best_g, best_s = None, -1.0
    for g, exemplars in templates.items():
        s = max(_ncc(cell, t) for t in exemplars)
        if s > best_s:
            best_g, best_s = g, s
    return (best_g if best_s >= min_corr else None), best_s


def _read_frame(rect, config, templates, min_corr):
    """Classify all digit boxes in one rectified frame.
    Returns a list of glyph chars (None where unreadable)."""
    return [_classify(_digit_cell(rect, box), templates, min_corr)[0]
            for box in config["digit_boxes"]]


# ---------------------------------------------------------------------------
# Poll cycle
# ---------------------------------------------------------------------------

def _gal_screen_ok(rect, config):
    """Best-effort consumption-screen check via the Gal indicator ROI.
    Returns True if no indicator is configured (assume consumption screen)."""
    ind = config.get("gal_indicator")
    if not ind:
        return True
    cv2, np = _require_cv()
    x, y = ind["x"], ind["y"]
    r = 6
    spot = rect[max(0, y - r):y + r, max(0, x - r):x + r]
    bg = rect[max(0, y - 25):y + 25, max(0, x - 25):x + 25]
    if spot.size == 0 or bg.size == 0:
        return True
    # LCD indicator is darker than its background when lit
    return float(np.mean(spot)) <= float(np.mean(bg)) * config.get("gal_ratio", 0.9)


def _poll_cycle(config: dict) -> dict:
    """Open the stream, read for `capture_seconds`, and return:
        {"total": float|None, "flowing": int, "valid_frames": int}
    total is None when no confident integer reading was obtained."""
    rtsp_url = config.get("rtsp_url")
    if not rtsp_url:
        raise ValueError("WaterMeter: 'rtsp_url' required in config")

    int_n = config.get("int_digits", 7)
    dec_n = config.get("dec_digits", 2)
    capture_seconds = config.get("capture_seconds", 5)
    min_corr = config.get("min_corr", 0.45)
    min_valid = config.get("min_valid_frames", 2)
    templates = _load_templates(config["template_dir"])

    cap = _open_stream(rtsp_url)
    for _ in range(5):                      # drain stale buffer
        cap.grab()

    int_readings = []                       # per-frame integer value (all int digits confident)
    dec_readings = []                       # per-frame decimal string (all dec digits confident)
    deadline = time.time() + capture_seconds
    try:
        while time.time() < deadline:
            ret, frame = cap.read()
            if not ret or frame is None:
                continue
            rect = _rectify(frame, config)
            if not _gal_screen_ok(rect, config):
                continue
            digits = _read_frame(rect, config, templates, min_corr)
            int_part, dec_part = digits[:int_n], digits[int_n:int_n + dec_n]
            if all(d is not None for d in int_part):
                int_readings.append(int("".join(int_part)))
            if dec_n and all(d is not None for d in dec_part):
                dec_readings.append("".join(dec_part))
    finally:
        cap.release()

    if len(int_readings) < min_valid:
        logger.warning("WaterMeter: only %d/%d valid integer frames this cycle; skipping",
                       len(int_readings), min_valid)
        return {"total": None, "flowing": 0, "valid_frames": len(int_readings)}

    int_val = int(statistics.median(int_readings))

    # Decimals are trustworthy only if stable across the cycle (no flow).
    # If they can't be read at all (not yet calibrated), flow is undetermined:
    # floor to whole gallons and leave flowing=0 rather than false-flagging it.
    flowing = 0
    total = float(int_val)
    if dec_n and dec_readings:
        if len(set(dec_readings)) == 1 and len(dec_readings) >= min_valid:
            total = int_val + int(dec_readings[0]) / (10 ** dec_n)
        else:
            flowing = 1            # decimals read but changing -> water moving; floor
    logger.debug("WaterMeter: int_frames=%s dec_frames=%s -> total=%.2f flowing=%d",
                 int_readings, dec_readings, total, flowing)
    return {"total": total, "flowing": flowing, "valid_frames": len(int_readings)}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def status(config={}, output="default"):
    raw = _poll_cycle(config)
    result = {}
    total = raw["total"]

    if total is not None:
        last = _state["last_total"]
        max_jump = config.get("max_reading_jump", 100)
        if last is not None and not (last <= total <= last + max_jump):
            logger.warning("WaterMeter: rejecting total %.2f (last %.2f, jump limit %s)",
                           total, last, max_jump)
            total = None
        else:
            _state["last_total"] = total

    if output == "signalk":
        from pivac import sk_init_deltas, sk_add_source, sk_add_value
        deltas = sk_init_deltas()
        src = sk_add_source(deltas)
        if total is not None:
            sk_add_value(src, CONSUMPTION_PATH, round(total, 2))
            sk_add_value(src, FLOWING_PATH, raw["flowing"])
        return deltas

    if total is not None:
        result[CONSUMPTION_PATH] = round(total, 2)
        result[FLOWING_PATH] = raw["flowing"]
    return result


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    import sys
    logging.basicConfig(format="%(name)s %(levelname)s: %(message)s", level=logging.DEBUG)
    try:
        import yaml
    except ImportError:
        sys.exit("PyYAML required: pip install pyyaml --break-system-packages")
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "/etc/pivac/config.yml"
    with open(cfg_path) as f:
        config = yaml.safe_load(f).get("pivac.WaterMeter", {})
    print(json.dumps(status(config), indent=2))
