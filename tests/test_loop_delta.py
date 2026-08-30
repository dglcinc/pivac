#!/usr/bin/env python3
"""Gating and run accounting for pivac.LoopDelta.

Dependency-free (no pytest, no Signal K): run directly with

    python tests/test_loop_delta.py

The cases below use the measured behaviour of this system.  A secondary loop
holds a plausible positive delta-T while its pump is off, so the gate is what
separates a measurement from fiction, and the first minutes of a run are a
startup transient rather than data.  The three publishable values mean three
different things and the cases below pin all of them: a number is a live
measurement, 0 is "not measuring right now", and None is a gap meaning a source
is unreadable.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pivac.LoopDelta import _advance, _gate_open, _new_state  # noqa: E402

SETTLE = 180.0


def _run(gate_and_delta, settle_s=60.0, step=20.0):
    """Feed a sequence of (gated, delta) at `step` seconds apart, returning every
    value the module would publish — including the 0s and the Nones, which carry
    distinct meanings."""
    state = _new_state()
    out = []
    now = 1000.0
    for gated, delta in gate_and_delta:
        value, _ = _advance(state, gated, delta, now, settle_s)
        out.append(value)
        now += step
    return out


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


def test_values():
    # 20 s steps, so settle_s=60 makes the first 3 samples of a run the charge-up.
    cases = [
        ("idle publishes 0, never a gap",
         [(False, 3.6)] * 4, [0.0, 0.0, 0.0, 0.0]),
        ("the stagnant value is never plotted as live",
         [(True, 3.6)] * 3 + [(True, 4.0)] * 2, [0.0, 0.0, 0.0, 4.0, 4.0]),
        ("live delta-T is instantaneous, not averaged",
         [(True, 0.0)] * 3 + [(True, 6.2)] + [(True, 5.0)] + [(True, 4.0)],
         [0.0, 0.0, 0.0, 6.2, 5.0, 4.0]),
        ("a run shorter than settle contributes only 0s",
         [(True, 6.2)] * 2 + [(False, 3.6)], [0.0, 0.0, 0.0]),
        ("returning to idle returns to 0",
         [(True, 0.0)] * 3 + [(True, 4.0)] + [(False, 3.6)] * 2,
         [0.0, 0.0, 0.0, 4.0, 0.0, 0.0]),
        ("a stale probe is a gap, distinct from idle's 0",
         [(True, 0.0)] * 3 + [(True, None)] + [(True, 4.0)],
         [0.0, 0.0, 0.0, None, 4.0]),
        ("settle restarts with each run, not once per process",
         [(True, 0.0)] * 3 + [(True, 4.0)] + [(False, 0.0)]
         + [(True, 9.9)] * 3 + [(True, 5.0)],
         [0.0, 0.0, 0.0, 4.0, 0.0, 0.0, 0.0, 0.0, 5.0]),
    ]
    failures = 0
    for label, seq, expected in cases:
        got = _run(seq)
        ok = got == expected
        failures += not ok
        print("%-4s val:  %-52s -> %s" % ("ok" if ok else "FAIL", label, got))
        if not ok:
            print("%-4s %-58s expected %s" % ("", "", expected))
    return failures, len(cases)


def main():
    f1, n1 = test_gate()
    print()
    f2, n2 = test_values()
    print("\n%d case(s), %d failure(s)" % (n1 + n2, f1 + f2))
    return 1 if (f1 + f2) else 0


if __name__ == "__main__":
    sys.exit(main())
