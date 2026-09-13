#!/usr/bin/env python3
"""Camera-creep registration in pivac.Sentry.

Run directly: python tests/test_sentry_registration.py (needs numpy + OpenCV,
skips cleanly without them). Builds a synthetic panel -- bezel edges, printed
labels, lens holes, digits that change between "cycles" -- shifts it by known
amounts and checks that the tracker measures the shift, moves the quad and lens
spots by it, refuses a knock beyond max_shift, and resets on a calibration edit.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import numpy as np
    import cv2
except ImportError:
    print("numpy/OpenCV not installed; registration tests skipped")
    sys.exit(0)

import pivac.Sentry as S  # noqa: E402

W, H = 640, 400
CORNERS = [{"x": 300, "y": 150}, {"x": 460, "y": 145}, {"x": 452, "y": 215}, {"x": 294, "y": 222}]
LEDS = {"burner": {"x": 500, "y": 150}, "circ": {"x": 500, "y": 176}}
INDS = {"water_temp": {"x": 300, "y": 250}, "air": {"x": 354, "y": 248}}


def panel(digits_seed, dx=0.0, dy=0.0):
    """One frame: fixed structure plus random lit bars inside the quad."""
    rng = np.random.default_rng(digits_seed)
    img = np.full((H, W), 110, np.uint8)
    cv2.rectangle(img, (270, 120), (540, 280), 60, 6)          # bezel
    for i in range(6):                                           # printed labels
        cv2.putText(img, "GAS%d" % i, (280 + 40 * i, 275), cv2.FONT_HERSHEY_SIMPLEX, 0.4, 30, 1)
    for v in list(LEDS.values()) + list(INDS.values()):          # lens holes
        cv2.circle(img, (v["x"], v["y"]), 7, 40, -1)
    for _ in range(6):                                           # digit content
        x = int(rng.integers(305, 440)); y = int(rng.integers(150, 210))
        cv2.rectangle(img, (x, y), (x + 20, y + 4), 250, -1)
    noise = rng.normal(0, 3, img.shape)
    img = np.clip(img.astype(float) + noise, 0, 255).astype(np.uint8)
    if dx or dy:
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        img = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REPLICATE)
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


def cycle_min(config, reg, seeds, dx=0.0, dy=0.0):
    """What _poll_cycle accumulates: the per-pixel minimum over the region."""
    if S._REG["region"] is None:
        S._REG["region"] = S._registration_region(config, (H, W), reg["pad"])
    x0, y0, x1, y1 = S._REG["region"]
    acc = None
    for sd in seeds:
        sub = S._to_gray(panel(sd, dx, dy))[y0:y1, x0:x1]
        acc = sub.copy() if acc is None else np.minimum(acc, sub)
    return acc


def main():
    failures = 0

    def check(label, ok, detail=""):
        nonlocal failures
        print("%s %s %s" % ("PASS" if ok else "FAIL", label, detail))
        if not ok:
            failures += 1

    with tempfile.TemporaryDirectory() as td:
        config = {"display_warp": {"corners": CORNERS, "dst_w": 168, "dst_h": 75},
                  "leds": LEDS, "indicators": INDS,
                  "registration": {"state_dir": td, "history": 3}}
        reg = S._reg_cfg(config)

        # Cycle 1: no reference yet, calibration sound -> reference captured.
        S._reg_prepare(config, reg)
        acc = cycle_min(config, reg, range(0, 40))
        dx, dy, score = S._reg_update(config, reg, acc, margin=55, misses=0)
        check("reference captured", S._REG["ref"] is not None and (dx, dy) == (0.0, 0.0))
        check("state file written", os.path.exists(os.path.join(td, S._REG_FILE)))

        # An unsound cycle must not capture a reference.
        S._REG.update(ref=None, mask=None)
        S._reg_update(config, reg, acc, margin=12, misses=1)
        check("no reference on a thin margin", S._REG["ref"] is None)
        S._reg_update(config, reg, acc, margin=55, misses=0)

        # Same view, different digits: no shift.
        dx, dy, score = S._reg_update(config, reg, cycle_min(config, reg, range(40, 80)), 55, 0)
        check("still view reads ~0", abs(dx) < 0.3 and abs(dy) < 0.3 and score > 0.7,
              "(%.2f, %.2f) score %.2f" % (dx, dy, score))

        # A 3 px right, 4 px up creep over three cycles becomes the median.
        for k in range(3):
            dx, dy, score = S._reg_update(config, reg, cycle_min(config, reg, range(80 + 40 * k, 120 + 40 * k), 3, -4), 55, 0)
        check("creep measured", abs(dx - 3) < 0.4 and abs(dy + 4) < 0.4,
              "(%.2f, %.2f) score %.2f" % (dx, dy, score))
        eff = S._effective_config(config, S._REG["shift"])
        check("quad follows", abs(eff["display_warp"]["corners"][0]["x"] - (CORNERS[0]["x"] + dx)) < 1e-6)
        check("lens spots follow, rounded",
              eff["leds"]["burner"] == {"x": LEDS["burner"]["x"] + round(dx), "y": LEDS["burner"]["y"] + round(dy)})
        check("saved shift readable by tools",
              tuple(round(v) for v in S.registration_shift(config)) == (3, -4))

        # A knock beyond max_shift is refused and the last shift held.
        held = S._REG["shift"]
        ndx, ndy, score = S._reg_update(config, reg, cycle_min(config, reg, range(300, 340), 22, 0), 55, 0)
        check("knock held, not applied", (ndx, ndy) == held, "score %.2f" % score)

        # Editing the calibration resets the reference.
        edited = dict(config, display_warp={"corners": [dict(c, x=c["x"] + 3) for c in CORNERS],
                                            "dst_w": 168, "dst_h": 75})
        S._reg_prepare(edited, reg)
        check("calibration edit resets", S._REG["ref"] is None and S._REG["shift"] == (0.0, 0.0))

    print("\n%s" % ("all registration checks passed" if not failures else "%d FAILED" % failures))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
