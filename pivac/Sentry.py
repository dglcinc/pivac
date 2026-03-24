"""
pivac.Sentry — NTI Trinity Ti-200 boiler monitor via Tapo C120 / Sentry 2100 display.

Reads the 3-digit 7-segment LED display and 4 indicator LEDs on the Sentry 2100
controller by capturing frames from an RTSP camera stream.  On each poll cycle
the module opens the stream, collects one stable reading per display mode
(water_temp, air, gas_input), reads LED states from the last frame,
releases the stream, and returns the results.

The display cycles through three modes: water_temp → air → gas_input, then loops.
Water temp is only valid when the water_temp indicator is explicitly lit; when no
mode indicators are lit the display still shows the last mode's value (gas_input)
during the cycling gap.

The dhw_temp indicator is a boiler-status light, not a display-mode indicator.
It is lit when the boiler is in DHW priority and stays lit during the cycling gap,
independent of what the display is showing.  It is emitted as the boolean
hvac.boiler.sentry.dhwPriority.

Required config keys:
    rtsp_url            RTSP stream URL (include camera credentials)
    display_warp        Perspective-warp corners + dst_w/dst_h (from calibration)
    digit_positions     List of 3 digit bounding boxes (relative to rectified display)
    leds                Centre-pixel coords for burner/circ/circ_aux/thermostat_demand
    indicators          Centre-pixel coords for water_temp/air/gas_input/dhw_temp

Optional config keys:
    cycle_timeout       Seconds to poll for all three modes  (default: 30)
    mode_stable_frames  Consecutive stable frames before accepting a reading (default: 3)
    led_ratio           Spot/background brightness ratio for LED detection (default: 1.15)
    digit_threshold_factor  Threshold = mean + factor*(max-mean) per digit (default: 0.50)
    daemon_sleep        Seconds between poll cycles (framework key; recommend >= 30)

Signal K paths emitted:
    hvac.boiler.sentry.waterTemp        °F as shown on display (when water_temp indicator lit)
    hvac.boiler.sentry.outdoorTemp      °F as shown on display (when air indicator lit)
    hvac.boiler.sentry.gasInputValue    Raw 40–240 scale (when gas_input indicator lit)
    hvac.boiler.sentry.errorCode        String e.g. "ER3" (non-numeric display, no indicator)
    hvac.boiler.sentry.dhwPriority      bool (dhw_temp indicator state — DHW priority active)
    hvac.boiler.sentry.burnerOn         bool
    hvac.boiler.sentry.circOn           bool
    hvac.boiler.sentry.circAuxOn        bool
    hvac.boiler.sentry.thermostatDemand bool
"""

import logging
import time

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CV imports — deferred so the module can be imported without opencv installed;
# the ImportError surfaces only when status() is called.
# ---------------------------------------------------------------------------

def _require_cv():
    try:
        import cv2
        import numpy as np
        return cv2, np
    except ImportError:
        raise ImportError(
            "Sentry module requires opencv-python-headless. "
            "Run: pip install opencv-python-headless --break-system-packages"
        )


# ---------------------------------------------------------------------------
# RTSP helpers
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


def _to_gray(img):
    cv2, np = _require_cv()
    if len(img.shape) == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


# ---------------------------------------------------------------------------
# Display extraction (perspective warp or legacy rectangle crop)
# ---------------------------------------------------------------------------

def _get_display_crop(frame, config: dict):
    cv2, np = _require_cv()
    if "display_warp" in config:
        warp = config["display_warp"]
        src = np.float32([[c["x"], c["y"]] for c in warp["corners"]])
        dst_w, dst_h = warp["dst_w"], warp["dst_h"]
        dst = np.float32([[0, 0], [dst_w, 0], [dst_w, dst_h], [0, dst_h]])
        M = cv2.getPerspectiveTransform(src, dst)
        return cv2.warpPerspective(frame, M, (dst_w, dst_h))
    roi = config["display_roi"]
    return frame[roi["y"]:roi["y"] + roi["h"],
                 roi["x"]:roi["x"] + roi["w"]]


# ---------------------------------------------------------------------------
# 7-segment digit recognition
# ---------------------------------------------------------------------------

# Fractional coords: (x_start, y_start, width, height) relative to digit crop.
# 'a' is narrowed to the centre of the top bar to avoid brightness spillover
# from the tops of the adjacent b (upper-right) and f (upper-left) verticals.
_SEGMENT_RECTS = {
    "a": (0.25, 0.00, 0.50, 0.12),  # top horizontal (centre only)
    "b": (0.80, 0.07, 0.15, 0.38),  # upper right vertical
    "c": (0.80, 0.55, 0.15, 0.38),  # lower right vertical
    "d": (0.15, 0.88, 0.70, 0.12),  # bottom horizontal
    "e": (0.05, 0.55, 0.15, 0.38),  # lower left vertical
    "f": (0.05, 0.07, 0.15, 0.38),  # upper left vertical
    "g": (0.15, 0.44, 0.70, 0.12),  # middle horizontal
}

# Bit order: a=bit6(MSB) … g=bit0(LSB)
_SEGMENT_MAP = {
    # Standard digits
    0b1111110: "0",
    0b0110000: "1",
    0b0000110: "1",   # left-side '1' — Sentry 2100 uses left verticals
    0b1101101: "2",
    0b1111001: "3",
    0b0110011: "4",
    0b1110011: "4",   # fallback: 'a' corner spillover from b+f
    0b1011011: "5",
    0b1011111: "6",
    0b1110000: "7",
    0b1111111: "8",
    0b1111011: "9",
    # Error / status characters
    0b1001111: "E",
    0b0000101: "r",
    0b1110111: "A",
    0b1000011: "F",
    0b1001110: "C",
    0b0001110: "c",
    0b0111110: "U",
    0b0111101: "d",
    0b0000001: "-",
    0b0000000: " ",
    # Single/double-segment ghost patterns from H.264 P-frame artefacts —
    # appear on blank digit positions when compression noise pushes one
    # segment rect slightly over threshold.  Not valid characters.
    0b0010000: " ",   # c only     (lower-right ghost)
    0b0010001: " ",   # c+g        (lower-right + middle ghost)
    0b0010010: " ",   # c+f        (lower-right + upper-left ghost)
}


def _segment_brightness(digit_roi, seg_name: str) -> float:
    _, np = _require_cv()
    h, w = digit_roi.shape[:2]
    xf, yf, wf, hf = _SEGMENT_RECTS[seg_name]
    x1, y1 = int(xf * w), int(yf * h)
    x2, y2 = int((xf + wf) * w), int((yf + hf) * h)
    region = digit_roi[y1:y2, x1:x2]
    if region.size == 0:
        return 0.0
    return float(np.percentile(_to_gray(region), 90))


def _digit_threshold(gray, factor: float) -> int:
    _, np = _require_cv()
    mean_val = float(np.mean(gray))
    max_val = float(np.max(gray))
    return int(mean_val + factor * (max_val - mean_val))


def _read_digit(digit_roi, threshold: int) -> str:
    bits = 0
    for i, seg in enumerate(["a", "b", "c", "d", "e", "f", "g"]):
        if _segment_brightness(digit_roi, seg) >= threshold:
            bits |= (1 << (6 - i))
    return _SEGMENT_MAP.get(bits, "?" + format(bits, "07b"))


def _read_display(frame, config: dict) -> str:
    display_crop = _get_display_crop(frame, config)
    factor = config.get("digit_threshold_factor", 0.50)
    result = ""
    for pos in config["digit_positions"]:
        digit_crop = display_crop[pos["y"]:pos["y"] + pos["h"],
                                  pos["x"]:pos["x"] + pos["w"]]
        gray = _to_gray(digit_crop)
        threshold = _digit_threshold(gray, factor)
        result += _read_digit(digit_crop, threshold)
    return result.strip()


# ---------------------------------------------------------------------------
# LED / indicator detection
# ---------------------------------------------------------------------------

def _roi_is_lit(frame, coord: dict,
                spot_radius: int = 8, bg_radius: int = 25,
                ratio: float = 1.15) -> bool:
    _, np = _require_cv()
    x, y = coord["x"], coord["y"]
    h, w = frame.shape[:2]
    gray = _to_gray(frame)
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


def _read_leds(frame, config: dict) -> dict:
    ratio = config.get("led_ratio", 1.15)
    leds = config.get("leds", {})
    return {
        "burnerOn":         _roi_is_lit(frame, leds["burner"],            ratio=ratio),
        "circOn":           _roi_is_lit(frame, leds["circ"],              ratio=ratio),
        "circAuxOn":        _roi_is_lit(frame, leds["circ_aux"],          ratio=ratio),
        "thermostatDemand": _roi_is_lit(frame, leds["thermostat_demand"], ratio=ratio),
    }


_DISPLAY_MODES = {"water_temp", "air", "gas_input"}


def _read_indicators(frame, config: dict):
    """Return the active display mode (water_temp/air/gas_input), or None.

    dhw_temp is intentionally excluded: it is a boiler-status light that stays
    lit whenever DHW priority is active, independent of what the display shows.
    Use _read_dhw_priority() to read it as a boolean.
    """
    ratio = config.get("led_ratio", 1.15)
    for mode, coord in config.get("indicators", {}).items():
        if mode not in _DISPLAY_MODES:
            continue
        if _roi_is_lit(frame, coord, ratio=ratio):
            return mode
    return None


def _read_dhw_priority(frame, config: dict) -> bool:
    """Return True if the DHW priority indicator is lit."""
    ratio = config.get("led_ratio", 1.15)
    coord = config.get("indicators", {}).get("dhw_temp")
    if coord is None:
        return False
    return _roi_is_lit(frame, coord, ratio=ratio)


# ---------------------------------------------------------------------------
# Error code classification
# ---------------------------------------------------------------------------

def _classify_error(display_str: str):
    """
    Return a normalised error code string if the 3-character display matches
    a known Sentry 2100 error pattern, else None.

    Rules (per Sentry 2100 manual):
    - d0 == 'E': error codes ER1–ER6, ER9.  d1 is always 'r' (7-seg); d2 is
      the digit.  Normalised form: 'ER' + d2  (e.g. "Er3" → "ER3").
    - d0 == 'A': status codes ASO or ASC.  d1 is always 'S'/'5' (same 7-seg
      pattern); d2 is 'O'/'0' or 'C'.  Normalised: 'AS' + ('O'|'C').
    - Any other d0: not an error code.
    """
    s = display_str.strip()
    if len(s) != 3:
        return None
    d0 = s[0].upper()
    if d0 == "E":
        return "ER" + s[2]          # d2 is always a digit; preserve as-is
    if d0 == "A":
        d2 = s[2].upper()
        d2_norm = "O" if d2 == "0" else d2   # '0' and 'O' share 7-seg pattern
        return "AS" + d2_norm
    return None


# ---------------------------------------------------------------------------
# Unit conversion
# ---------------------------------------------------------------------------

def _f_to_k(f: float) -> float:
    return round((f - 32) * 5 / 9 + 273.15, 2)


# ---------------------------------------------------------------------------
# Polling loop — shared by status() and the __main__ block
# ---------------------------------------------------------------------------

def _poll_cycle(config: dict) -> dict:
    """
    Open the RTSP stream, collect one stable reading per display mode plus LED
    states, release the stream, and return a raw dict:

        {
            "water_temp":  "179",   # raw display string, or absent if not seen
            "air":         "42",
            "gas_input":   "168",
            "error_code":  "ER3",   # present only if a non-numeric display was seen
            "dhw_priority": True,   # DHW priority indicator state
            "leds": {"burnerOn": True, ...},
        }
    """
    rtsp_url = config.get("rtsp_url")
    if not rtsp_url:
        raise ValueError("Sentry: 'rtsp_url' required in config")

    cycle_timeout    = config.get("cycle_timeout", 30)
    mode_stable_min  = config.get("mode_stable_frames", 3)

    cap = _open_stream(rtsp_url)
    logger.debug("Sentry: connected to RTSP stream, polling for up to %ds", cycle_timeout)

    # Drain initial buffer so we start on a fresh frame.
    for _ in range(5):
        cap.grab()

    collected   = {}   # mode -> raw string
    error_code  = None
    last_frame  = None
    prev_mode   = None
    stable_count = 0
    deadline    = time.time() + cycle_timeout
    expected    = _DISPLAY_MODES & set(config.get("indicators", {}).keys())

    try:
        while time.time() < deadline:
            ret, frame = cap.read()
            if not ret or frame is None:
                continue
            last_frame = frame

            mode  = _read_indicators(frame, config)
            value = _read_display(frame, config)

            # Track mode stability to skip transition-frame artefacts.
            if mode == prev_mode:
                stable_count += 1
            else:
                prev_mode    = mode
                stable_count = 0

            if "?" not in value and stable_count >= mode_stable_min:
                if mode and mode not in collected:
                    collected[mode] = value
                    logger.debug("Sentry: captured '%s' = '%s'", mode, value)
                elif mode is None:
                    code = _classify_error(value)
                    if code:
                        error_code = code
                        logger.debug("Sentry: error/status code detected: '%s'", code)

            if collected.keys() >= expected:
                logger.debug("Sentry: all display modes captured")
                break
    finally:
        cap.release()

    result = dict(collected)
    if error_code:
        result["error_code"] = error_code
    if last_frame is not None:
        result["leds"] = _read_leds(last_frame, config)
        result["dhw_priority"] = _read_dhw_priority(last_frame, config)
    else:
        result["leds"] = {}
        result["dhw_priority"] = False

    return result


# ---------------------------------------------------------------------------
# Module entry point
# ---------------------------------------------------------------------------

# Sentinel used to distinguish "never emitted" from "emitted None".
# Ensures errorCode is always sent once on startup regardless of value.
_UNSET = object()
_last_error_code = _UNSET

_MODE_SK = {
    "water_temp": "hvac.boiler.sentry.waterTemp",
    "air":        "hvac.boiler.sentry.outdoorTemp",
    "gas_input":  "hvac.boiler.sentry.gasInputValue",
}

_LED_SK = {
    "burnerOn":         "hvac.boiler.sentry.burnerOn",
    "circOn":           "hvac.boiler.sentry.circOn",
    "circAuxOn":        "hvac.boiler.sentry.circAuxOn",
    "thermostatDemand": "hvac.boiler.sentry.thermostatDemand",
}


def status(config={}, output="default"):
    """
    Poll the Sentry 2100 display and return current boiler state.

    In default output mode returns a flat dict of Signal K path -> value pairs.
    In 'signalk' output mode returns a Signal K delta structure.

    errorCode is emitted only when its value changes (including a null clear
    when an error resolves), to avoid flooding InfluxDB with repeated nulls
    during normal operation.
    """
    global _last_error_code
    raw = _poll_cycle(config)

    if output == "signalk":
        from pivac import sk_init_deltas, sk_add_source, sk_add_value
        deltas = sk_init_deltas()
        sk_source = sk_add_source(deltas)

    result = {}

    for mode, sk_path in _MODE_SK.items():
        if mode not in raw:
            continue
        value_str = raw[mode]
        try:
            val = float(value_str)
        except ValueError:
            logger.warning("Sentry: could not parse '%s' value '%s' as number",
                           mode, value_str)
            continue

        if mode == "gas_input":
            sk_val = int(val)
        else:
            sk_val = val  # raw °F as shown on display — no conversion

        if output == "signalk":
            sk_add_value(sk_source, sk_path, sk_val)
        else:
            result[sk_path] = sk_val
        logger.debug("Sentry: %s = %s", sk_path, sk_val)

    current_error = raw.get("error_code")  # str like "ER3", or None
    if current_error != _last_error_code or _last_error_code is _UNSET:
        sk_path = "hvac.boiler.sentry.errorCode"
        if output == "signalk":
            sk_add_value(sk_source, sk_path, current_error)
        else:
            result[sk_path] = current_error
        if current_error:
            logger.info("Sentry: error code active: %s", current_error)
        elif _last_error_code is not _UNSET:
            logger.info("Sentry: error code cleared")
        _last_error_code = current_error

    dhw_priority = int(raw.get("dhw_priority", False))
    sk_path = "hvac.boiler.sentry.dhwPriority"
    if output == "signalk":
        sk_add_value(sk_source, sk_path, dhw_priority)
    else:
        result[sk_path] = dhw_priority
    logger.debug("Sentry: %s = %s", sk_path, dhw_priority)

    for led_key, sk_path in _LED_SK.items():
        val = int(raw["leds"].get(led_key, False))
        if output == "signalk":
            sk_add_value(sk_source, sk_path, val)
        else:
            result[sk_path] = val
        logger.debug("Sentry: %s = %s", sk_path, val)

    if output == "signalk":
        return deltas
    return result


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    import sys
    logging.basicConfig(
        format="%(name)s %(levelname)s: %(message)s",
        level=logging.DEBUG,
    )
    try:
        import yaml
    except ImportError:
        sys.exit("PyYAML required: pip install pyyaml --break-system-packages")

    cfg_path = "/etc/pivac/config.yml"
    if len(sys.argv) > 1:
        cfg_path = sys.argv[1]
    with open(cfg_path) as f:
        full_config = yaml.safe_load(f)
    config = full_config.get("pivac.Sentry", {})
    print(json.dumps(status(config), indent=2))
