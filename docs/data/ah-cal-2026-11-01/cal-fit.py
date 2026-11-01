#!/usr/bin/env python3
"""Fit the 2026-11-01 bath session: ten DS18B20s and two NTC pairs on the rev A air-handler shield.

Reads ah-cal-2026-11-01.wall.log (AirHandlerCal's CSV with a wall-clock prefix) and prints, for each
of the six logged windows, the bath summary; for each probe, its reading per bath, its error against
the Thermapen, the slope of reading against true, and the offset in kelvin to add at 55 F (cooling
water) and 115 F (heating water); and for each NTC, R25 and beta fitted from the three baths with the
residuals, beside what the sketch's 10 k / 3995 assumption would have read.

The Thermapen was held among the probe tips and read at each window; the values below are its readings.
"""
import csv, math, statistics as st

LOG = 'ah-cal-2026-11-01.wall.log'
# window: (pair, start, end, thermapen F). Start/end are wall clock; the sketch's log/done lines inside.
WINDOWS = {
    'ice p1': ('1', '15:40:42', '15:42:39', 32.15),
    'ice p2': ('2', '15:44:13', '15:46:11', 32.15),
    '90 p1':  ('1', '16:01:49', '16:03:47', 89.95),
    '90 p2':  ('2', '16:06:59', '16:08:57', 89.95),
    '130 p1': ('1', '16:38:30', '16:40:36', 129.8),
    '130 p2': ('2', '16:45:11', '16:47:13', 129.7),
}
ROMS = ['28-000000D47F08', '28-000000D6D34A', '28-000000D33C3A', '28-000000D648F6', '28-000000D601E1',
        '28-000000D3A98D', '28-000000D5415D', '28-000000D48567', '28-000000D5FF9F', '28-000000D58E3F']


def f(x):
    return float(x) if x else None


def fit_line(xs, ys):
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return my - b * mx, b


rows = [r for r in csv.reader(open(LOG)) if len(r) >= 21 and r[0].split()[-1].isdigit()]
win = {}
for name, (pair, t0, t1, tp) in WINDOWS.items():
    win[name] = ([r for r in rows if t0 <= r[0][:8] <= t1 and r[2] in ('log', 'done') and r[1] == pair], tp)

print('window   n  Thermapen  ret ohm  sup ohm   ds mean  spread  ds sd')
ntc = {}
for name, (sel, tp) in win.items():
    ret = [f(r[4]) for r in sel]; sup = [f(r[7]) for r in sel]
    per = [[f(r[11 + i]) for r in sel if f(r[11 + i]) is not None] for i in range(10)]
    m = [st.mean(p) for p in per]
    bath, pair = name.split()
    pair = pair[1:]                      # 'p1' -> '1'
    ntc[(pair, 'ret', bath)] = (st.mean(ret), tp)
    ntc[(pair, 'sup', bath)] = (st.mean(sup), tp)
    print('%-7s %3d  %7.2f  %8.1f %8.1f  %8.3f  %.2f   %.3f' % (
        name, len(sel), tp, st.mean(ret), st.mean(sup), st.mean(m), max(m) - min(m),
        st.pstdev([f(r[9]) for r in sel])))

print('\nProbes: reading per bath (both windows), error against the Thermapen, slope, offset K at 55 and 115 F')
print('col  w1 name           @ice    @90    @130   err ice  err 90  err 130  slope   K@55    K@115')
for i in range(10):
    pts = []
    for bath in ('ice', '90', '130'):
        vals, tps = [], []
        for name, (sel, tp) in win.items():
            if name.startswith(bath):
                vals += [f(r[11 + i]) for r in sel if f(r[11 + i]) is not None]; tps.append(tp)
        pts.append((st.mean(tps), st.mean(vals)))
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    a, b = fit_line(xs, ys)
    off = lambda T: (T - (a + b * T)) * 5 / 9
    print('ds%d  %s  %6.2f %6.2f %6.2f   %+6.2f  %+6.2f  %+6.2f  %.4f  %+.3f  %+.3f' % (
        i, ROMS[i], ys[0], ys[1], ys[2], ys[0] - xs[0], ys[1] - xs[1], ys[2] - xs[2], b, off(55), off(115)))

print('\nNTCs: ln R = ln R25 + beta (1/T - 1/298.15) fitted to the three baths; residuals in F; '
      'and the error of the sketch\'s 10 k / 3995 at each bath')
for pair in ('1', '2'):
    for ch in ('ret', 'sup'):
        pts = [ntc[(pair, ch, b)] for b in ('ice', '90', '130')]
        X = [1 / ((tp - 32) * 5 / 9 + 273.15) - 1 / 298.15 for _, tp in pts]
        Y = [math.log(R) for R, _ in pts]
        lnR25, B = fit_line(X, Y)
        res = []
        for (R, tp), x in zip(pts, X):
            Tk = 1 / ((math.log(R) - lnR25) / B + 1 / 298.15)
            res.append((Tk - 273.15) * 9 / 5 + 32 - tp)
        sk = []
        for R, tp in pts:
            Tk = 1 / (1 / 298.15 + math.log(R / 10000) / 3995)
            sk.append((Tk - 273.15) * 9 / 5 + 32 - tp)
        print('pair %s %s:  R %s ohm   R25 %.0f  beta %.0f   residuals %s   10k/3995 errors %s' % (
            pair, ch, ' '.join('%.0f' % R for R, _ in pts), math.exp(lnR25), B,
            ' '.join('%+.2f' % r for r in res), ' '.join('%+.2f' % r for r in sk)))
