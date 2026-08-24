#!/usr/bin/env python3
"""Per-sensor calibration offsets for pivac.OneWireTherm.

Dependency-free (no pytest, no w1thermsensor): run directly with

    python tests/test_onewire_offset.py

The offset is stated in Kelvin because Signal K output is always read in Kelvin. The
cases below use the real bench values from docs/ds18b20-PA1-5-calibration.md, and check
the property the calibration exists for: a *pair* offset must move the loop delta-T by
the pair's ice-point difference, which is what a supply/return measurement depends on.
"""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# w1thermsensor is a Pi-only dependency (it reads /sys/bus/w1). Stub it so the pure
# offset arithmetic can be tested on any machine.
if "w1thermsensor" not in sys.modules:
    stub = types.ModuleType("w1thermsensor")

    class W1ThermSensor:  # noqa: D101
        @staticmethod
        def get_available_sensors():
            return []

    class Unit:  # noqa: D101
        KELVIN = "kelvin"
        DEGREES_C = "celsius"
        DEGREES_F = "fahrenheit"

    stub.W1ThermSensor = W1ThermSensor
    stub.Unit = Unit
    sys.modules["w1thermsensor"] = stub

from pivac.OneWireTherm import _apply_offset  # noqa: E402

# Bench ice-point offsets in Kelvin, docs/ds18b20-PA1-5-calibration.md
PA1A, PA1B = 0.588, 0.423
PA2A, PA2B = -0.184, 0.083
PA3A, PA3B = 0.348, 0.466
PA4A, PA4B = 0.468, 0.143

CASES = [
    # (label, temp, offset_k, read_fahrenheit, expected)
    ("no offset configured leaves the reading alone", 281.90, 0, False, 281.90),
    ("absent offset defaults to zero", 281.90, 0.0, False, 281.90),
    ("kelvin read adds the offset directly", 281.90, PA3A, False, 282.248),
    ("negative offset subtracts", 285.00, PA2A, False, 284.816),
    ("fahrenheit read scales the same offset by 1.8", 47.80, PA3A, True, 48.4264),
    ("negative offset in fahrenheit", 53.00, PA2A, True, 52.6688),
    # A raw value at the ice point must land on the bench anchor of 32.05 F = 273.1722 K.
    ("PA1A raw ice point corrects to the anchor", 272.5842, PA1A, False, 273.1722),
]

# Pair delta-T corrections: correcting both ends must shift the delta by exactly
# (offset_A - offset_B), the "pair delta-T-zero correction" column of the record.
PAIRS = [
    ("PA1 (loop B)", PA1A, PA1B, 0.166),
    ("PA2 (loop A)", PA2A, PA2B, -0.267),
    ("PA3 (buffer tank)", PA3A, PA3B, -0.118),
    # The record's pair column reads +0.324: that is 0.583 F / 1.8 rounded on its own.
    # The two per-probe K offsets as configured differ by 0.325, which is what the
    # module computes. Do not "correct" the config to close the 0.001 K gap.
    ("PA4 (primary loop, IN/OUT)", PA4A, PA4B, 0.325),
]

TOL = 1e-3


def main():
    failures = 0

    for label, temp, offset_k, read_f, expected in CASES:
        got = _apply_offset(temp, offset_k, read_f)
        ok = abs(got - expected) < TOL
        if not ok:
            failures += 1
        print("%-4s %-52s %.4f -> %.4f (expected %.4f)"
              % ("ok" if ok else "FAIL", label, temp, got, expected))

    # Same raw reading on both probes: the corrected delta is the pair correction.
    raw = 283.15
    for label, off_a, off_b, expected_delta in PAIRS:
        delta = _apply_offset(raw, off_a) - _apply_offset(raw, off_b)
        ok = abs(delta - expected_delta) < TOL
        if not ok:
            failures += 1
        print("%-4s %-52s delta %+.3f K (expected %+.3f)"
              % ("ok" if ok else "FAIL", label + " delta-T zero", delta, expected_delta))

    print("\n%d case(s), %d failure(s)" % (len(CASES) + len(PAIRS), failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
