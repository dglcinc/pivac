#!/usr/bin/env python3
"""pivac.offset_at: a probe's calibration offset at the temperature it is reading.

Dependency-free: python tests/test_offset_points.py

The bench records give one offset per operating point because a DS18B20's error is a
line in temperature. `offsets: {45: a, 140: b}` in config makes the module interpolate
on the reading, so the cooling and heating columns both apply without a seasonal swap.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pivac import offset_at  # noqa: E402


def f2k(f):
    return (f - 32.0) * 5.0 / 9.0 + 273.15


LOOPA_SUP = {45: 0.653, 140: 0.346}       # PA1A, docs/ds18b20-PA1-5-calibration.md
PA9A = {55: 3.382, 115: 3.556}            # docs/air-handler-probe-calibration-2026-11-01.md

CASES = [
    # (label, offsets, reading F, expected K)
    ("None means no correction", None, 70, 0.0),
    ("empty string means no correction", "", 70, 0.0),
    ("a number is a constant", 0.468, 45, 0.468),
    ("a number is a constant at any temperature", 0.468, 140, 0.468),
    ("one point is a constant", {45: 0.653}, 140, 0.653),
    ("at the cooling point, the cooling value", LOOPA_SUP, 45, 0.653),
    ("at the heating point, the heating value", LOOPA_SUP, 140, 0.346),
    ("halfway, halfway", LOOPA_SUP, 92.5, 0.4995),
    ("below the first point, the line continues", LOOPA_SUP, 32, 0.653 + (0.346 - 0.653) * (32 - 45) / 95.0),
    ("above the last point, the line continues", PA9A, 130, 3.382 + (3.556 - 3.382) * (130 - 55) / 60.0),
    ("string keys from YAML are accepted", {"55": 3.382, "115": 3.556}, 55, 3.382),
    ("order of keys does not matter", {115: 3.556, 55: 3.382}, 115, 3.556),
]


def main():
    failures = 0
    for label, offsets, f, expected in CASES:
        got = offset_at(offsets, f2k(f))
        ok = abs(got - expected) < 1e-9
        failures += not ok
        print("%-4s %-46s @%5.1f F -> %+.4f K" % ("ok" if ok else "FAIL", label, f, got))
    print("\n%d case(s), %d failure(s)" % (len(CASES), failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
