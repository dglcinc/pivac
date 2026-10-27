#!/usr/bin/env python3
"""Fast fault poll in pivac.ChiltrixModbus: scan scheduling and faultCode hold.

Dependency-free (no pytest, no pyserial): run directly with

    python tests/test_chiltrix_fault.py

Register 284 shows a fault only while it is active, and the full scan every
~70 s missed 6 of 18 self-clearing P1s.  The module now reads 227 and 284 on
every short cycle and the full set once `scan_s` has passed; faultCode holds a
non-zero 284 for `fault_hold_s` so one fast read covers a minute bucket.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pivac.ChiltrixModbus as m  # noqa: E402


class _Clock:
    def __init__(self):
        self.now = 1_000_000.0

    def time(self):
        return self.now

    def sleep(self, s):
        self.now += s


class _Port:
    is_open = True


class _Chiller:
    """Answers _read_range from a dict, and records every range asked for."""
    def __init__(self, clock):
        self.clock = clock
        self.regs = {227: 40, 284: 0, 213: 300}
        self.asked = []

    def read(self, s, lo, hi):
        self.asked.append((lo, hi))
        self.clock.now += 0.5
        return {a: self.regs.get(a, 0) for a in range(lo, hi + 1)}


def _setup():
    clock = _Clock()
    m.time = clock
    for k in list(m._state):
        m._state[k] = None
    m._state["run_duration"] = 0.0
    chiller = _Chiller(clock)
    m._read_range = chiller.read
    m._ser = _Port()
    return clock, chiller


def _cycle(clock, chiller, sleep, config):
    chiller.asked.clear()
    result = m.status(config)
    clock.now += sleep
    return result, list(chiller.asked)


def test_fast_cycles_between_full_scans():
    clock, chiller = _setup()
    cfg = {"scan_s": 60}
    result, asked = _cycle(clock, chiller, 5, cfg)
    assert asked == m.RAW_RANGES, asked
    assert "registerCount" in result
    fulls = 1
    for _ in range(30):                          # ~2.5 minutes at 5 s
        result, asked = _cycle(clock, chiller, 5, cfg)
        if asked == m.RAW_RANGES:
            fulls += 1
            assert "registerCount" in result
        else:
            assert asked == [(227, 227), (284, 284)], asked
            assert "registerCount" not in result
            assert set(result) >= {"compressorHz", "raw.r284", "faultCode"}, result
    assert fulls == 3, fulls                     # t=0, ~60 s, ~120 s


def test_daemon_sleep_60_is_always_a_full_scan():
    clock, chiller = _setup()
    for _ in range(5):
        _, asked = _cycle(clock, chiller, 60, {"scan_s": 60})
        assert asked == m.RAW_RANGES


def test_fault_code_holds_one_fast_read_for_a_minute():
    clock, chiller = _setup()
    cfg = {"scan_s": 60, "fault_hold_s": 60}
    _cycle(clock, chiller, 5, cfg)
    chiller.regs[284] = 2                        # a P1 seen by one fast read
    result, _ = _cycle(clock, chiller, 5, cfg)
    assert result["faultCode"] == 2 and result["raw.r284"] == 2
    chiller.regs[284] = 0
    held = []
    for _ in range(14):
        result, _ = _cycle(clock, chiller, 5, cfg)
        held.append(result["faultCode"])
    assert result["raw.r284"] == 0
    assert held[:8] == [2] * 8, held             # cycles are ~6 s with the reads
    assert held[-1] == 0, held


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
