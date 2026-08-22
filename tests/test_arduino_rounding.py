"""Dependency-free checks on pivac.ArduinoSensor's temperature rounding.

Run with:  python tests/test_arduino_rounding.py

The module emits Kelvin, so `rounding` is a precision setting rather than a
cosmetic one. Whole Kelvin is 1.8 degF, coarser than every sensor that feeds
this module, and a difference built from two such readings moves in 1.8 degF
steps -- which is what makes an evaporator delta unusable at `rounding: 0`.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# _round_temp and DEFAULT_ROUNDING are pure; import them without pulling in
# `requests`/`pytemperature`, which are not installed on every dev machine.
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "_arduinosensor_src",
    os.path.join(os.path.dirname(__file__), "..", "pivac", "ArduinoSensor.py"),
)


def _load():
    try:
        mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(mod)
        return mod._round_temp, mod.DEFAULT_ROUNDING
    except ImportError:
        # requests/pytemperature missing -- re-exec just the helper.
        src = open(_spec.origin).read()
        ns = {}
        start = src.index("DEFAULT_ROUNDING")
        end = src.index("def status(")
        exec(src[start:end].replace("import pytemperature", ""), ns)
        return ns["_round_temp"], ns["DEFAULT_ROUNDING"]


_round_temp, DEFAULT_ROUNDING = _load()

failures = []


def check(label, got, want):
    if got != want:
        failures.append("%s: got %r, want %r" % (label, got, want))


# The default keeps enough precision that a delta survives.
check("default is 2dp", DEFAULT_ROUNDING, 2)

# 0 preserves the historical whole-Kelvin behaviour for anyone who wants it,
# and must still return an int so Signal K/InfluxDB see the same shape as before.
check("0 rounds to int", _round_temp(308.4159, 0), 308)
check("0 returns an int", isinstance(_round_temp(308.4159, 0), int), True)
check("0 rounds up", _round_temp(308.6, 0), 309)

# Positive keeps decimals.
check("2dp", _round_temp(308.4159, 2), 308.42)
check("1dp", _round_temp(308.4159, 1), 308.4)
check("3dp", _round_temp(308.4159, 3), 308.416)

# Negative leaves the reading untouched.
check("-1 is raw", _round_temp(308.4159, -1), 308.4159)

# The reason the change exists: two readings 0.5 degF apart must stay apart.
# 0.5 degF = 0.2778 K. At 0 dp they collapse to the same integer; at 2 dp they do not.
a, b = 308.0, 308.2778
check("0dp collapses a small delta", _round_temp(a, 0) == _round_temp(b, 0), True)
check("2dp preserves a small delta", _round_temp(a, 2) != _round_temp(b, 2), True)

# A 9 degF evaporator delta (5 K) must round-trip to better than 0.1 degF.
delta_k = _round_temp(283.15 + 5.0, 2) - _round_temp(283.15, 2)
check("9degF delta accurate to 0.1degF", abs(delta_k * 9 / 5 - 9.0) < 0.1, True)

if failures:
    print("FAIL")
    for f in failures:
        print("  " + f)
    sys.exit(1)
print("ok - %d checks passed" % 12)
