#!/usr/bin/env python3
"""Gating and run accounting for pivac.LoopDelta.

Dependency-free (no pytest, no Signal K): run directly with

    python tests/test_loop_delta.py

The cases below use the measured behaviour of this system.  A secondary loop
holds a plausible positive delta-T while its pump is off, so the gate is what
separates a measurement from fiction, and the first minutes of a run are a
startup transient rather than data.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pivac.LoopDelta import _advance, _gate_open, _new_state  # noqa: E402

SETTLE = 180.0


def _run(gate_and_delta, settle_s=SETTLE, step=20.0):
    """Feed a sequence of (gated, delta) at `step` seconds apart. Returns every
    value the module would have published."""
    state = _new_state()
    published = []
    now = 1000.0
    for gated, delta in gate_and_delta:
        completed, _ = _advance(state, gated, delta, now, settle_s)
        if completed is not None:
            published.append(completed)
        now += step
    return published


def test_gate():
    cases = [
        ("relay off, zone calling      -> shut", False, [-1], False),
        ("relay on, no zone narrowing  -> open", True, None, True),
        ("relay on, this loop's zone   -> open", True, [-1, 0], True),
        ("relay on, other loop's zone  -> shut", True, [0, 0], False),
        ("relay on, zone heating       -> open", True, [1], True),
        ("relay unreadable             -> shut", None, [-1], False),
        ("relay on, zone unreadable    -> shut", True, [None], False),
    ]
    failures = 0
    for label, relay, zones, expected in cases:
        got = _gate_open(relay, zones)
        ok = got == expected
        failures += not ok
        print("%-4s gate: %-32s -> %s" % ("ok" if ok else "FAIL", label, got))
    return failures, len(cases)


def test_runs():
    # 20 s steps: the transient is the first 9 samples (180 s).
    transient = [(True, 6.2)] * 9
    settled = [(True, 4.0)] * 9
    cases = [
        ("idle throughout publishes nothing",
         [(False, 3.6)] * 20, []),
        ("run shorter than settle publishes nothing",
         [(True, 6.2)] * 5 + [(False, 3.6)] * 3, []),
        ("transient is excluded from the mean",
         transient + settled + [(False, 3.6)], [4.0]),
        ("value appears once, at the end of the run",
         transient + settled + [(False, 3.6)] * 5, [4.0]),
        ("two runs publish two values",
         transient + settled + [(False, 3.6)] * 3
         + transient + [(True, 5.0)] * 9 + [(False, 3.6)], [4.0, 5.0]),
        ("a stale probe mid-run drops that sample only",
         transient + [(True, None)] * 3 + settled + [(False, 3.6)], [4.0]),
    ]
    failures = 0
    for label, seq, expected in cases:
        got = _run(seq)
        ok = got == expected
        failures += not ok
        print("%-4s run:  %-45s -> %s (expected %s)"
              % ("ok" if ok else "FAIL", label, got, expected))
    return failures, len(cases)


def main():
    f1, n1 = test_gate()
    print()
    f2, n2 = test_runs()
    print("\n%d case(s), %d failure(s)" % (n1 + n2, f1 + f2))
    return 1 if (f1 + f2) else 0


if __name__ == "__main__":
    sys.exit(main())
