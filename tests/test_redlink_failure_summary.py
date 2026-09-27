"""Dependency-free tests for the RedLink refresh-failure rollup.

Run with:  python tests/test_redlink_failure_summary.py

Per-device refresh failures are routine, so they log at INFO and the module
raises a WARNING only for the hourly rollup and for a device that misses
CONSEC_WARN refreshes in a row. The service runs at --loglevel WARNING, so
these two lines are all the journal sees.
"""
import importlib.util
import logging
import os
import sys
import types

# The module imports its network libraries at load; none is needed here.
for _name in ('aiohttp', 'aiosomecomfort', 'pytemperature'):
    sys.modules.setdefault(_name, types.ModuleType(_name))

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    'redlink_under_test', os.path.join(_HERE, os.pardir, 'pivac', 'RedLink.py'))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


class _Capture(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage())


capture = _Capture()
_mod.logger.addHandler(capture)
_mod.logger.setLevel(logging.WARNING)

failures = []


def check(label, ok):
    print('  %-5s %s' % ('ok' if ok else 'FAIL', label))
    if not ok:
        failures.append(label)


# A failing device is silent until it has missed CONSEC_WARN in a row.
for _ in range(_mod.CONSEC_WARN - 1):
    _mod._note_refresh('KIDS ROOM', True, 'TimeoutError')
check('no warning below the consecutive threshold', capture.lines == [])
_mod._note_refresh('KIDS ROOM', True, 'TimeoutError')
check('one warning at the consecutive threshold',
      len(capture.lines) == 1 and 'KIDS ROOM' in capture.lines[0]
      and 'in a row' in capture.lines[0])
for _ in range(5):
    _mod._note_refresh('KIDS ROOM', True, 'TimeoutError')
check('no repeat while the run continues', len(capture.lines) == 1)

# A success ends the run, so the next run warns again.
_mod._note_refresh('KIDS ROOM', False)
for _ in range(_mod.CONSEC_WARN):
    _mod._note_refresh('KIDS ROOM', True, 'TimeoutError')
check('a new run warns again', len(capture.lines) == 2)

# The rollup appears once the interval has passed, with each device's share.
capture.lines.clear()
_mod._refresh_attempts.clear()
_mod._refresh_failures.clear()
_mod._summary_start = None
_mod._summarise_refreshes(1000.0)
for i in range(10):
    _mod._note_refresh('KITCHEN', i < 3, 'TimeoutError')
    _mod._note_refresh('MASTER BR', False)
_mod._summarise_refreshes(1000.0 + _mod.SUMMARY_INTERVAL - 1)
check('no rollup inside the interval', capture.lines == [])
_mod._summarise_refreshes(1000.0 + _mod.SUMMARY_INTERVAL)
check('rollup after the interval',
      len(capture.lines) == 1 and 'KITCHEN 3/10' in capture.lines[0]
      and 'MASTER BR 0/10' in capture.lines[0])
check('rollup resets the window', _mod._refresh_attempts == {})

# A window with no failures says nothing.
capture.lines.clear()
for _ in range(10):
    _mod._note_refresh('KITCHEN', False)
_mod._summarise_refreshes(1000.0 + 2 * _mod.SUMMARY_INTERVAL)
check('a clean window is silent', capture.lines == [])

print()
if failures:
    print('%d FAILED' % len(failures))
    sys.exit(1)
print('all passed')
