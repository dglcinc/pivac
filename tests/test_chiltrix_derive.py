#!/usr/bin/env python3
"""startupFlow derivation in pivac.ChiltrixModbus: the stop-edge settle guard.

Dependency-free (no pytest, no pyserial): run directly with

    python tests/test_chiltrix_derive.py

Replays the 2026-09-02 trace that false-fired chiltrix-pump-only-flow-low.
The 08:07 run stopped between samples; the 08:28:17 sample caught the pump
spinning down (0 Hz, 36.8 L/min), that value became the published plateau,
and the 6.9 L/min idle trickle could not displace it for the 36 minutes until
the next start.  The alert window is 30 minutes.  The strainer read 52.9 on
the start before cleaning and 52.9 on the start after.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pivac.ChiltrixModbus as m  # noqa: E402

PERIOD = 71.0   # observed sample cadence, seconds


class _Clock:
    def __init__(self):
        self.now = 1_000_000.0

    def time(self):
        return self.now


def _reset():
    clock = _Clock()
    m.time = clock
    for k in list(m._state):
        m._state[k] = None
    m._state["run_duration"] = 0.0
    return clock


def _feed(clock, samples, **kw):
    """samples: (hz, flow L/min[, pump %]).  Returns startupFlow per sample."""
    out = []
    for hz, lpm, *pump in samples:
        clock.now += PERIOD
        result = {}
        regs = {227: hz, 213: int(round(lpm * 10))}
        if pump:
            regs[248] = pump[0]
        m._derive(regs, result, **kw)
        out.append(result.get("startupFlow"))
    return out


# The 08:07 run as logged, then the stop sample and the idle that followed.
RUN_0807 = [
    (0, 6.9), (0, 6.9),            # deep idle (first sample seeds prev_hz)
    (0, 51.7),                     # pump-only pre-start window
    (44, 52.9), (51, 50.5), (55, 50.5), (41, 50.5), (41, 45.9), (41, 43.6),
    (37, 42.5), (25, 36.8), (25, 36.8), (25, 43.6), (25, 43.6), (25, 47.1),
    (25, 51.7), (25, 51.7), (25, 50.5), (25, 51.7), (21, 51.7),
]
STOP_SAMPLE = [(0, 36.8)]          # 08:28:17 — pump spinning down
IDLE_36MIN = [(0, 6.9)] * 30


def test_ramp_down_sample_is_not_the_plateau():
    clock = _reset()
    seen = _feed(clock, RUN_0807 + STOP_SAMPLE + IDLE_36MIN)
    assert seen[-1] == 52.9, seen[-1]
    assert min(v for v in seen if v is not None) >= 50.5, seen
    assert 36.8 not in seen, "the spin-down sample leaked into the plateau"


def test_old_behaviour_reproduced_with_settle_disabled():
    """Proves the guard is what fixed it: settle 0 = the pre-fix code path."""
    clock = _reset()
    seen = _feed(clock, RUN_0807 + STOP_SAMPLE + IDLE_36MIN, stop_settle_s=0)
    assert seen[-1] == 36.8, seen[-1]


def test_restriction_before_a_start_still_lowers_the_plateau():
    """The guard must not blind the alarm: a 22.9 pump-only reading (the
    2026-08-28 restriction) after a long idle is still captured."""
    clock = _reset()
    seen = _feed(clock, RUN_0807 + STOP_SAMPLE + IDLE_36MIN
                 + [(0, 22.9), (41, 22.9), (55, 20.6)])
    assert seen[-1] == 22.9, seen[-1]


def test_restart_inside_settle_uses_the_run_side():
    """A restart 142 s after the stop is inside the settle period; the first
    150 s of the run still capture the plateau."""
    clock = _reset()
    seen = _feed(clock, RUN_0807 + STOP_SAMPLE + [(0, 6.9), (43, 52.9), (50, 51.7)])
    assert seen[-1] == 52.9, seen[-1]


def test_first_cycle_mid_run_publishes_nothing():
    clock = _reset()
    seen = _feed(clock, [(55, 50.5), (55, 50.5)])
    assert seen == [None, None], seen


def test_run_duration_holds_last_run_while_stopped():
    clock = _reset()
    _feed(clock, RUN_0807 + STOP_SAMPLE + [(0, 6.9)])
    result = {}
    clock.now += PERIOD
    m._derive({227: 0, 213: 69}, result)
    # run_started is the first >0 Hz sample; the stop sample is 17 periods on
    assert abs(result["runDuration"] - 17 * PERIOD) < 1e-6, result


# 2026-10-20: the 08:11 start, the run trimmed to 34 Hz, the P1 stop at 08:30,
# then the latched lockout with the pump held at its 40 % minimum.
P1_LOCKOUT = [
    (0, 8.0, 10), (0, 8.0, 10),
    (0, 54.0, 100),                               # pump-only pre-start
    (50, 55.2, 100), (55, 54.0, 100), (67, 54.0, 100), (64, 55.2, 100),
    (34, 50.5, 88), (34, 40.2, 69), (34, 39.0, 69), (34, 36.8, 63),
    (0, 35.6, 62),                                # stop sample
] + [(0, 8.0, 10)] * 9 + [(0, 24.1, 40)] * 50     # lockout, 40 % pump


def test_lockout_minimum_pump_is_not_the_plateau():
    clock = _reset()
    out = _feed(clock, P1_LOCKOUT)
    assert out[-1] == 55.2, out[-1]


def test_lockout_old_behaviour_reproduced_without_the_pump_gate():
    clock = _reset()
    out = _feed(clock, P1_LOCKOUT, full_pump_pct=0)
    assert out[-1] == 24.1, out[-1]


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print("PASS", name)
        except AssertionError as exc:
            failed += 1
            print("FAIL", name, "--", exc)
    print("%d/%d passed" % (len(tests) - failed, len(tests)))
    sys.exit(1 if failed else 0)
