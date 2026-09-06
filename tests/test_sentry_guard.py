#!/usr/bin/env python3
"""Phantom-hundreds-digit guard for pivac.Sentry water-temp reads.

Dependency-free (no pytest/cv2 needed): run directly with

    python tests/test_sentry_guard.py

Exercises _reading_sane against the exact patterns seen in InfluxDB on
2026-06-25 (the 98<->198 idle spike) and the last clean DHW call (smooth
105->182 ramp, burner firing; ~165 cooldown with burner off).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pivac.Sentry import (  # noqa: E402
    _reading_sane,
    _WATER_IDLE_CEILING,
    _display_threshold,
    _decode_segments,
    _low_margin,
    _MARGIN_BAND,
    _MIN_SEPARATION,
)

CASES = [
    # (label, mode, value, burner_on, expected_accepted)
    # --- the phantom-hundreds misread we are killing ---
    ("idle 98 phantom -> 198, burner off", "water_temp", "198", False, False),
    ("idle 88 phantom -> 188, burner off", "water_temp", "188", False, False),
    ("idle ceiling boundary 185, burner off", "water_temp", "185", False, False),

    # --- legitimate reads that MUST still pass ---
    ("real firing peak 198, burner ON", "water_temp", "198", True, True),
    ("real firing peak 200, burner ON", "water_temp", "200", True, True),
    ("early cooldown 165, burner off", "water_temp", "165", False, True),
    ("early cooldown 180, burner off", "water_temp", "180", False, True),
    ("idle standby 116, burner off", "water_temp", "116", False, True),
    ("cold standby 98, burner off", "water_temp", "98", False, True),
    ("ramp midpoint 153, burner ON", "water_temp", "153", True, True),

    # --- absolute range still enforced (tightened 220 -> 205) ---
    ("above abs ceiling 210, burner ON", "water_temp", "210", True, False),
    ("below abs floor 30, burner off", "water_temp", "30", False, False),

    # --- burner unknown (None): idle check skipped, abs range only ---
    ("198 burner unknown -> abs range passes", "water_temp", "198", None, True),

    # --- other modes unaffected by the water-temp idle gate ---
    ("gas_input 0 is valid off", "gas_input", "0", None, True),
    ("gas_input 110 in range", "gas_input", "110", None, True),
    ("gas_input 30 below floor", "gas_input", "30", None, False),
    ("air 73 in range", "air", "73", None, True),

    # --- garbage strings -> None (rejected) ---
    ("non-numeric display", "water_temp", "ER3", False, False),
]


# Display-wide digit threshold — the root-cause fix for the phantom hundreds digit.
# The old per-digit-crop threshold let a BLANK digit's own glare set the bar, so a
# stray bright pixel manufactured a phantom "1" (~84 read as 184). The bar is now
# derived once from the whole display (background -> a genuinely-lit segment) and
# applied to every digit, so a blank position stays blank.
#
# Brightness fixtures below are the REAL per-segment values measured off the live
# RTSP stream on 2026-06-28 (display reading "165"/"163", bg~116, lit segs ~255).
# threshold = _display_threshold(bg=116, hi=255, factor=0.65) = 206.
THR = _display_threshold(116.0, 255.0, 0.65)   # -> 206

# (label, brightness dict, expected char)
DECODE_CASES = [
    # real hundreds "1" (Sentry uses the left verticals e+f): lit 255, off <=179
    ("real '1' hundreds (e+f lit)",
     {"a": 133, "b": 159, "c": 179, "d": 148, "e": 255, "f": 255, "g": 161}, "1"),
    # real tens "6": all lit except b (b sits at 192, just under the 206 bar)
    ("real '6' tens (b off at 192)",
     {"a": 255, "b": 192, "c": 255, "d": 255, "e": 255, "f": 255, "g": 255}, "6"),
    # real units "5"
    ("real '5' units",
     {"a": 255, "b": 185, "c": 255, "d": 255, "e": 175, "f": 255, "g": 255}, "5"),
    # BLANK digit at off-level brightness -> must stay blank (no phantom)
    ("blank digit (all off ~130-180) -> ' '",
     {"a": 133, "b": 159, "c": 179, "d": 148, "e": 150, "f": 160, "g": 161}, " "),
    # BLANK digit with mild IR glare (b,c pushed to ~190) -> still blank, NOT "1".
    # Under the old per-crop bar these two would have read lit -> phantom "1".
    ("blank digit + glare (b,c~190) -> ' ' not '1'",
     {"a": 150, "b": 190, "c": 193, "d": 150, "e": 160, "f": 165, "g": 160}, " "),
]


# Aim check. Ratios are real measurements taken 2026-09-06 with the boiler idle:
# the four LED spots at their then-configured coords (burner hugging the 1.05 bar
# after two camera drifts), and the same spots re-centred on the lens.
MARGIN_CASES = [
    ("burner drifted onto the bezel -> flagged",
     {"burner": [1.040, 1.045, 1.047, 1.051, 1.043]}, 1.05, ["burner"]),
    ("all four at the lens centres -> clean",
     {"burner":            [0.812, 0.815, 0.822],
      "circ":              [0.790, 0.804, 0.809],
      "circ_aux":          [0.810, 0.814, 0.828],
      "thermostat_demand": [0.804, 0.811, 0.814]}, 1.05, []),
    ("a genuinely lit LED is not flagged",
     {"burner": [1.31, 1.35, 1.39]}, 1.05, []),
    ("a minority of on-bar frames is not flagged",
     {"circ": [0.80, 0.81, 1.045, 0.79, 0.82]}, 1.05, []),
    ("indicator hugging its 1.15 bar -> flagged",
     {"water_temp": [1.14, 1.152, 1.147, 1.16]}, 1.15, ["water_temp"]),
    ("empty samples are ignored", {"burner": []}, 1.05, []),
    # Cycling indicators: real ratios, 160 frames each, 2026-09-06. The drifted
    # water_temp switched states correctly but on a 0.090 separation, which the
    # majority test cannot see -- it is dark for three quarters of every cycle.
    ("drifted water_temp, thin gap -> flagged",
     {"water_temp": [1.049, 1.045, 1.053, 1.056, 1.179, 1.183, 1.177]},
     1.15, ["water_temp"]),
    ("lens-centred water_temp, wide gap -> clean",
     {"water_temp": [0.871, 0.868, 0.874, 0.880, 1.392, 1.401, 1.388]},
     1.15, []),
    ("lens-centred air and gas_input -> clean",
     {"air":        [0.893, 0.890, 1.501, 1.495],
      "gas_input":  [0.895, 0.891, 1.450, 1.444]}, 1.15, []),
]


def main():
    assert _WATER_IDLE_CEILING == 185.0, _WATER_IDLE_CEILING
    assert _MARGIN_BAND == 0.03, _MARGIN_BAND
    assert _MIN_SEPARATION == 0.15, _MIN_SEPARATION
    assert THR == 206, THR
    failures = []
    for label, mode, value, burner, expect_ok in CASES:
        got = _reading_sane(mode, value, burner_on=burner)
        accepted = got is not None
        ok = accepted == expect_ok
        print(f"[{'PASS' if ok else 'FAIL'}] {label}: "
              f"_reading_sane({mode!r}, {value!r}, burner_on={burner}) -> {got}")
        if not ok:
            failures.append(label)

    for label, brightness, expect_char in DECODE_CASES:
        got = _decode_segments(brightness, THR)
        ok = got == expect_char
        print(f"[{'PASS' if ok else 'FAIL'}] {label}: "
              f"_decode_segments(..., {THR}) -> {got!r} (want {expect_char!r})")
        if not ok:
            failures.append(label)

    for label, ratios, thr, expect_names in MARGIN_CASES:
        got = [n for n, _ in _low_margin(ratios, thr)]
        ok = got == expect_names
        print(f"[{'PASS' if ok else 'FAIL'}] {label}: "
              f"_low_margin(..., {thr}) -> {got} (want {expect_names})")
        if not ok:
            failures.append(label)

    print()
    total = len(CASES) + len(DECODE_CASES) + len(MARGIN_CASES)
    if failures:
        print(f"{len(failures)} FAILED: {failures}")
        sys.exit(1)
    print(f"all {total} cases passed")


if __name__ == "__main__":
    main()
