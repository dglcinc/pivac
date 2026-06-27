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

from pivac.Sentry import _reading_sane, _WATER_IDLE_CEILING  # noqa: E402

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


def main():
    assert _WATER_IDLE_CEILING == 185.0, _WATER_IDLE_CEILING
    failures = []
    for label, mode, value, burner, expect_ok in CASES:
        got = _reading_sane(mode, value, burner_on=burner)
        accepted = got is not None
        ok = accepted == expect_ok
        print(f"[{'PASS' if ok else 'FAIL'}] {label}: "
              f"_reading_sane({mode!r}, {value!r}, burner_on={burner}) -> {got}")
        if not ok:
            failures.append(label)
    print()
    if failures:
        print(f"{len(failures)} FAILED: {failures}")
        sys.exit(1)
    print(f"all {len(CASES)} cases passed")


if __name__ == "__main__":
    main()
