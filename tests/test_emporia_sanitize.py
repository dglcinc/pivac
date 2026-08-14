"""Dependency-free tests for pivac.Emporia._sanitize.

Run with:  python tests/test_emporia_sanitize.py

_sanitize output becomes both a Signal K path component and an InfluxDB
measurement name, and renaming one orphans its history -- so the important
property is not just "cleans punctuation" but "does not change any name that is
already in service".
"""
import importlib.util
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    'emporia_under_test', os.path.join(_HERE, os.pardir, 'pivac', 'Emporia.py'))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
sanitize = _mod._sanitize

failures = []


def check(label, raw, expected):
    got = sanitize(raw)
    ok = got == expected
    print('  %-5s %-34r -> %-30r %s' % ('ok' if ok else 'FAIL', raw, got,
                                        '' if ok else '(expected %r)' % expected))
    if not ok:
        failures.append(label)


print('punctuation that would need InfluxQL quoting is removed:')
check('apostrophe', "Don't know", 'dont_know')
check('plus', 'Microwave + Refrigerator', 'microwave_refrigerator')
check('ampersand', 'Downstairs Bath & Floor', 'downstairs_bath_floor')
check('parens', 'Bova (Kitchen)', 'bova_kitchen')
check('slash', 'Washer/Dryer', 'washer_dryer')
check('hyphen', 'Sub-Panel', 'sub_panel')

print('\na period must not survive -- it would nest the Signal K path:')
check('dot', 'Circ. Pump', 'circ_pump')
check('dots', 'A.B.C', 'abc')

print('\nno collapsing to empty, no leading/trailing or doubled underscores:')
check('empty', '', 'unnamed')
check('punct only', '!!!', 'unnamed')
check('edges', '  Wall Oven  ', 'wall_oven')
check('doubled', 'Kids  --  Room', 'kids_room')

print('\nnames already in service must be unchanged (renaming orphans history):')
for name in ['main', 'balance', 'chiltrix', 'wall_oven', 'bova_kitchen',
             'bova_great_room', 'hall_sub_panel', 'utility_sub_panel',
             'downstairs_bath_and_floor', 'air_conditioner', 'furnace',
             'clothes_washer']:
    check('stable:' + name, name, name)

print('\nsanitize is idempotent (re-running never renames):')
for raw in ["Don't know", 'Microwave + Refrigerator', 'Bova (Kitchen)', 'Circ. Pump']:
    once = sanitize(raw)
    check('idempotent:' + once, once, once)

print('\noutput is always a safe path component:')
for raw in ["Don't know", 'Microwave + Refrigerator', 'A.B.C', '!!!', 'Kids  --  Room']:
    out = sanitize(raw)
    if not re.fullmatch(r'[a-z0-9_]+', out):
        print('  FAIL %r -> %r contains an unsafe character' % (raw, out))
        failures.append('charset:' + raw)
print('  ok    all outputs match [a-z0-9_]+')

print()
if failures:
    print('FAILED: %d' % len(failures))
    sys.exit(1)
print('all passed')
