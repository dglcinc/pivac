# Chiltrix CX75 — cycling-reduction tuning plan

Goal: fewer compressor starts at part load, with the unit throttling the pump and
compressor down instead of pulling the tank to its stop point and cycling off. Every
recommendation here is grounded in measured data (InfluxDB `hvac.chiller.chiltrix.*`,
2026-08-26 → 2026-08-30) and the parameter table in `cx65-1-iom.pdf` pp. 56–60. The
register = parameter-number mapping is verified — 85 of the manual's 105 listed
parameters read exactly the documented default at the same register address, and the
15 addresses with no manual entry are exactly the P-numbers the manual skips (see
CLAUDE.md, Chiltrix Modbus notes).

## The mechanism, as measured

The cycle at part load runs: the pump trims itself down toward its ΔT target →
inlet climbs → the controller chases with the compressor → the pair overshoot the
stop point → off → idle rise → restart. Measured 2026-08-29: at a constant 26 Hz
the pump halved its own flow (41.3 → 21.8 L/min) while the evaporator ΔT widened
5.5 → 8.5 °F toward the 9 °F trim target, then the compressor chased 26 → 50 Hz
and the run ended in the low cut-out.

The parameters behind each piece, with live register values:

| Reg | Param | Meaning | Live value | Role in the cycle |
|-----|-------|---------|-----------|-------------------|
| 12  | P12 | AC temp hysteresis, 2–15 °C | **2** (minimum) | Sets the band. Observed: stop at inlet ~44.6 °F, restart at 54.0–54.2 °F against the 50 °F target. |
| 95  | P95 | ΔT the controller trims the C4 pump to hold, 2–8 °C | **5** (= 9 °F) | The pump-trim target the flow-halving chased. |
| 51  | P51 | Pump speed: 0–10 fixed (0–100 %), 11 auto | **11** | Auto is what permits the trim. |
| 53  | P53 | Pump minimum speed | **40 %** | Floor of the auto range. |
| 142 | —   | Cooling inlet target, whole °C | **10** (50 °F) | The manual's own suggested space-cooling setpoint is 53 °F (p. 55). |
| 59  | P59 | Antifreeze trip, watches **leaving** water | **3 °C** (37.4 °F) | The guardrail every change below must respect. |
| 27  | P27 | Max compressor % | **100** | Leave alone — see below. |

Two temperatures matter and they are different waters. The setpoint band is on
**inlet** (tank return): stop ~44.6 °F, restart ~54 °F. The antifreeze protection
watches **leaving** water, which rides the evaporator ΔT below inlet whenever the
compressor runs: at the stop moment, 44.6 − ~5 °F ≈ **39.6 °F against the 37.4 °F
P59 trip — a 2.2 °F margin**. That thin margin is what blocks widening the
hysteresis band at the current target, and it is where the E14 lockout of
2026-08-21 came from.

There is no cooling minimum-frequency parameter (P110 is heating-only), so the
modulation floor is fixed hardware. The achievable win is longer cycles with
gentler endings, not continuous modulation at arbitrarily low load.

## The changes, in order

Make one change at a time and read the result from data already collected (§
Verification) before the next.

### 1. P95: 5 → 3 °C

Narrows the pump-trim ΔT target. At part load the pump is then already near its
target and has little reason to slow, so the destabilizing flow cut mostly
disappears while automatic control and the idle trickle economy are kept. Range is
2–8; 3 °C ≈ 5.4 °F sits above the clean part-load ΔT of ~5 °F. Fully reversible.

### 2. Cooling target: 10 → 12 °C, then P12: 2 → 3 °C (a pair)

The target raise does not by itself reduce cycle count — the band width does — but
it moves the whole band up: stop inlet ≈ 48.2 °F, stop-moment leaving ≈ 43 °F,
antifreeze margin 5.6 °F instead of 2.2. That restored margin is what makes the
P12 widening safe; with P12 = 3 the stop drops back ~1.8 °F and still keeps more
margin than today. The wider band lengthens both the pulldown and the idle rise,
which is the direct cycling reduction. Side benefits of the warmer target: higher
COP (the manual's p. 65 argument), and 12 °C is the manual's own suggested
space-cooling setpoint.

**Set the target in whole °C on the panel and read register 142 back** — the
controller stores whole °C, and a Fahrenheit entry lands lower than typed (the
mechanism behind the E14 lockout history).

**Hot-day check before calling it done:** the only full-load day on record
(2026-08-29, runs lengthening to 232 min) ran at the 50 °F target. Watch zone
droop (`environment.inside.thermostat.*.temperature` vs `.coolset`) on the next
90 °F day at the new target.

### 3. Fallback: P51 fixed speed — only if 1–2 disappoint

Pinning the pump removes the pump/compressor coupling entirely: inlet then responds
only to compressor speed, and runs end by slow drift instead of an overshoot. It
also makes flow an independent measurement again, which retires the fouling
alarm's standing "may be measuring the controller" caveat.

Costs, from the measured numbers: auto commands 80–100 % at full load (42.5–52.9
L/min at 55 Hz against a ~53 L/min full-speed plateau), so a pin must be **8–9,
not lower** — at 70 % (~37 L/min) full output would run a ~10.5 °F ΔT with leaving
water ~2 °F colder at peak, costing COP and P59 margin exactly on the hottest
days. Compressor output itself is unaffected. And with P52 = 0 the pump never
stops, so the fixed speed applies at idle too: expect the 9–11 W idle draw to
become tens of watts around the clock. Quantify it on
`electrical.emporia.house.chiltrix` after the change.

## Not recommended

- **P12 wider at the current 50 °F target.** One more degree of band lands the
  stop-moment leaving water on the P59 trip.
- **P27 (max compressor) lower.** The 232-minute full-load runs show peak capacity
  is needed; capping it converts hot-day cycling into hot-day droop.
- **P59 lower to buy margin.** It is the antifreeze protection; buy margin with
  the target instead. The order for running colder is glycol → P59 → target
  (CLAUDE.md, E14 note).
- **Cooling AU (P43 + P112)** is the automatic version of change 2 — the target
  floats up on exactly the mild days that cause cycling — but its cooling curve is
  undocumented in this IOM. If tried, verify the effective target via register 142
  before trusting it, and keep the floor at 10 °C.

## Verification after each change

All from existing paths, no new collection needed:

- **Starts/day** — count 0 → >0 edges on `hvac.chiller.chiltrix.compressorHz`
  (drop TMO gaps before edge-counting; a timeout parsed as 0 manufactures fake
  cycles).
- **Run and idle lengths** — `hvac.chiller.chiltrix.runDuration`.
- **Evaporator ΔT** — `.evaporatorDelta`; after P95 = 3 expect part-load ΔT to
  hold nearer 5 °F instead of widening toward 9.
- **Stop/restart points** — inlet (`.inletTemp`) at the compressor edges; confirms
  where the band actually sits after a target or P12 change.
- **Fouling alarm still armed** — `.startupFlow` clean baseline is 50.5–54 L/min;
  none of these changes should move it, and a P51 pin makes it stricter (fixed
  speed → tighter plateau).
- **Pump cost of a P51 pin** — idle watts on `electrical.emporia.house.chiltrix`.

Panel changes are the only write path — the Modbus module is read-only by policy
(function 03 only). Register readback is the verification that a change stored
what was typed.
