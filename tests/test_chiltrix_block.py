#!/usr/bin/env python3
"""Block mode in pivac.ChiltrixModbus: coverage, line parsing, change-only send.

Dependency-free (no pytest, no pyserial): run directly with

    python tests/test_chiltrix_block.py

Chiltrix asked for registers 0-146 and 200-286 at about 1 s.  The module reads
them in five `r <lo> <n>` blocks every sweep and sends a value to Signal K only
when it changes, resending everything once `refresh_s` has passed.
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


class _Serial:
    """Plays back the sketch's reply lines to one `r` command."""
    def __init__(self, lines):
        self.lines = [l.encode() + b"\r\n" for l in lines]
        self.written = b""
        self.is_open = True

    def reset_input_buffer(self):
        pass

    def write(self, b):
        self.written += b

    def flush(self):
        pass

    def readline(self):
        return self.lines.pop(0) if self.lines else b""


def _reset():
    clock = _Clock()
    m.time = clock
    for k in list(m._state):
        m._state[k] = None
    m._state["run_duration"] = 0.0
    return clock


def test_blocks_cover_every_requested_register():
    want = set(range(0, 147)) | set(range(200, 287))
    got = set()
    for lo, hi in m.BLOCKS:
        assert hi - lo + 1 <= 50, (lo, hi)
        got |= set(range(lo, hi + 1))
    assert got == want, sorted(want ^ got)


def test_read_block_parses_signed_values_after_the_echo():
    _reset()
    s = _Serial(["> r 200 3", "R 200 3 133 -400 0"])
    assert m._read_block(s, 200, 202) == {200: 133, 201: -400, 202: 0}
    assert s.written == b"r 200 3\n"


def test_read_block_failure_and_short_line_return_empty():
    _reset()
    assert m._read_block(_Serial(["> r 0 50", "E 0 50 E2"]), 0, 49) == {}
    assert m._read_block(_Serial(["R 0 50 1 2 3"]), 0, 49) == {}


def test_silent_board_raises():
    clock = _reset()

    class _Silent(_Serial):
        def readline(self):
            clock.now += 0.2
            return b""

    try:
        m._read_block(_Silent([]), 0, 49)
    except RuntimeError:
        return
    raise AssertionError("expected RuntimeError")


def test_changed_sends_changes_always_keys_and_refresh():
    clock = _reset()
    first = m._changed({"raw.r0": 1, "raw.r1": 5, "registerCount": 234}, 60)
    assert first == {"raw.r0": 1, "raw.r1": 5, "registerCount": 234}
    clock.now += 1
    second = m._changed({"raw.r0": 1, "raw.r1": 6, "registerCount": 234}, 60)
    assert second == {"raw.r1": 6, "registerCount": 234}, second
    clock.now += 60
    third = m._changed({"raw.r0": 1, "raw.r1": 6, "registerCount": 234}, 60)
    assert third == {"raw.r0": 1, "raw.r1": 6, "registerCount": 234}, third


def test_status_block_mode_reads_every_block_each_sweep():
    _reset()
    asked = []

    def fake(s, lo, hi):
        asked.append((lo, hi))
        return {a: 0 for a in range(lo, hi + 1)}

    m._read_block = fake
    m._ser = _Serial([])
    result = m.status({})
    assert asked == m.BLOCKS, asked
    assert result["registerCount"] == 234
    assert "raw.r286" in result and "raw.r200" in result and "raw.r0" in result


if __name__ == "__main__":
    real = m._read_block
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            m._read_block = real
            fn()
            print("ok", name)
