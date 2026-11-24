<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
<!-- Copyright David Lewis -->

# Air-handler probe calibration, 2026-11-01

Ten new DS18B20 probes and two NTC pairs for the air-handler nodes, calibrated in one session on the rev A
air-handler shield with `AirHandlerCal` (Arduino PR #16): every probe on the shield's DS2482 bus through a
Quattro block to TB3, the NTC pairs taking turns in TB2, all tips bundled with the Thermapen in an ice bath
and a sous vide at 90 and 130 °F. Each pair logged a two-minute window at each bath once the probes' mean
had held flat for six minutes. The log is `docs/data/ah-cal-2026-11-01/ah-cal-2026-11-01.wall.log` and
`cal-fit.py` beside it prints every table here.

## Result

**The ten probes read 6.2 to 7.0 °F low, every one of them, with a slope of 0.994 to 0.995.** The error is
the same sign and nearly the same size on all ten at every bath, so it is a property of the batch, with
the chips keeping their order within the batch to 0.1 °F from ice to 130 °F. A per-probe offset in
config corrects it; the slope costs 0.1 to 0.2 K between the cooling and heating columns, the same as the
loop probes. The batch never goes into service without its offset.

**The NTCs are 10 kΩ, beta 4000 parts within 3 %**, and the sketch's 10 kΩ / 3995 reads them 0.1 to
1.4 °F high. Fitted R25 and beta per bead put every bath within 0.3 °F.

## Baths

| Window | Thermapen °F | Lines | Probe mean | Spread |
|---|---|---|---|---|
| Ice, pair 1 | 32.15 | 60 | 25.96 | 0.48 |
| Ice, pair 2 | 32.15 | 60 | 25.99 | 0.49 |
| 90, pair 1 | 89.95 | 60 | 83.53 | 0.45 |
| 90, pair 2 | 89.95 | 60 | 83.52 | 0.46 |
| 130, pair 1 | 129.8 | 60 | 123.05 | 0.45 |
| 130, pair 2 | 129.7 | 62 | 123.05 | 0.45 |

1. The Thermapen toggled 32.1 and 32.2 in the ice and 89.9 and 90.0 at the sous vide's 90 setting; the
   table carries the midpoints.
2. At the 130 setting the Thermapen read 130.0 beside the bundle and 129.6 to 129.8 among the tips, and
   the probes and both NTCs sagged 0.35 °F together over the first ten minutes while the sous vide held
   its setting. The bundle sat in slack water; the readings taken among the tips at the time of each
   window are the ones used.
3. The probes' mean held to 0.015 °F within every window.

## Probes

Reading at each bath is the mean of both windows. Error is reading minus Thermapen. The offset is the
kelvin to add to the reading at that water temperature, from a line through the three points; 55 °F is
the cooling-coil column and 115 °F the heating-coil column.

| Label | Col | w1 name | @ice | @90 | @130 | Slope | K @55 | K @115 |
|---|---|---|---|---|---|---|---|---|
| PA9A | ds0 | `28-000000D47F08` | 26.16 | 83.74 | 123.24 | 0.9948 | +3.382 | +3.556 |
| PA13A | ds1 | `28-000000D6D34A` | 25.75 | 83.29 | 122.79 | 0.9943 | +3.616 | +3.806 |
| PA12A | ds2 | `28-000000D33C3A` | 25.86 | 83.43 | 123.01 | 0.9954 | +3.547 | +3.699 |
| PA11A | ds3 | `28-000000D648F6` | 26.04 | 83.62 | 123.16 | 0.9952 | +3.446 | +3.607 |
| PA10B | ds4 | `28-000000D601E1` | 26.07 | 83.63 | 123.20 | 0.9953 | +3.434 | +3.592 |
| PA11B | ds5 | `28-000000D3A98D` | 26.04 | 83.57 | 123.03 | 0.9938 | +3.457 | +3.663 |
| PA13B | ds6 | `28-000000D5415D` | 25.70 | 83.29 | 122.79 | 0.9949 | +3.635 | +3.807 |
| PA9B | ds7 | `28-000000D48567` | 26.18 | 83.67 | 123.17 | 0.9938 | +3.387 | +3.595 |
| PA10A | ds8 | `28-000000D5FF9F` | 26.14 | 83.65 | 123.18 | 0.9943 | +3.404 | +3.595 |
| PA12B | ds9 | `28-000000D58E3F` | 25.81 | 83.37 | 122.92 | 0.9950 | +3.578 | +3.743 |

1. The error grows from 6.2 °F at the ice point to 6.7 °F at 130 °F. Stem conduction toward the
   70 °F room raises a reading in ice and lowers it at 130 °F, which widens the error in the same way,
   and the bundle's immersion was not measured, so the slope is an upper bound on the chips' own; the
   two offset columns bracket it either way.
2. A coil takes one labelled pair, so the residual after correction is common-mode; the pairs were
   formed from the sorted offsets, A and B within 0.03 K at 55 °F.
3. The w1 names reverse the six serial bytes of the printed ROM, as the sketch prints them. The labels
   were applied at the end of the session by lifting one probe at a time out of the 130 °F bath and
   naming the column that cooled, with the label fixed per column so that each PA pair has matched
   offsets: A and B of a pair are within 0.03 K at 55 °F. PA9 to PA13 follow the PA1 to PA8 roster of
   `docs/ds18b20-PA1-5-calibration.md`. Each probe carries a cable-flag label with its name and w1 name on
   one line and the two offsets on the other, printed on 12 mm laminated tape by
   `scripts/ptouch-cable-flag.py` on the Brother PT-E550W over USB.

## NTCs

Fit of ln R against 1/T through the three baths. Residuals are the fit's error at ice, 90 and 130 in °F;
the last column is what the sketch's 10 kΩ / 3995 assumption read at the same three baths.

| Pair | Channel | R25 Ω | Beta | Residuals °F | 10k/3995 error °F |
|---|---|---|---|---|---|
| 1 | ret (A0) | 9825 | 3999 | −0.08, +0.27, −0.20 | +0.47, +1.03, +0.71 |
| 1 | sup (A1) | 9928 | 4004 | −0.02, +0.09, −0.06 | +0.13, +0.42, +0.42 |
| 2 | ret (A0) | 9710 | 3982 | +0.05, −0.16, +0.12 | +1.18, +1.03, +1.35 |
| 2 | sup (A1) | 9841 | 3983 | +0.06, −0.22, +0.16 | +0.72, +0.42, +0.77 |

The beads are labelled by pair and channel, `SUP 1`, `RET 1`, `SUP 2` and `RET 2`; pair 1 is the plug that
was in TB2 for the first window of each bath and pair 2 the plug swapped in for the second.

1. Three points fit two parameters, so the residuals are the beads' departure from a single beta, 0.2 to
   0.3 °F on three of the four and under 0.1 on pair 1's supply bead. A Steinhart-Hart fit would need a
   fourth bath to be worth more than this.
2. A node sketch applies these as per-bead `R25` and `beta`, or keeps the batch beta and takes a per-bead
   offset at its operating point from the residual table, as `AirHandler_MBR` does today.
3. The ret bead of pair 1 had the widest resistance scatter in the ice window, 29 Ω against 4 to 5 for the
   rest, which is pair 1's plug contact and not the bead (below).

## What went wrong on the bench

1. **The TB3 plug's contact opened on its own**, eleven minutes into the 130 °F soak with nothing touched.
   From 16:29:40 two to six of the ten probes failed each read, a different set every line, while the
   DS2482 reported presence, no short and line high; `ds5` alone never missed. Reseating the plug cured it
   at 16:33:42, though 48 of the next 373 lines still had a miss. A random set of probes failing each line
   is a marginal bus, never a dead probe, and the header or plug is the first suspect, as it was on
   2026-10-28 when TB3's unsoldered tail read as an open bus. The leaking-probe theory was raised and
   withdrawn: the Quattro block gives each probe its own position, so a bisect by lifting one DQ lead at a
   time is available if it recurs with the plug seated.
2. **Both NTC plugs were half in at times**, RET open with SUP reading, on both pairs' plugs, so the
   TB2 RET contact is suspect on the board as well as in the plugs. Pressing the plug home cured each case.
3. **A flickering plug advanced the pair on every touch.** `CalTracker` counted the next plug as in on the
   first closed sample, so each contact flicker after a counted out advanced the pair again, and the
   pair number toggled 1, 2, 1, 2 until the plug seated. The pair was set by key for three of the five
   swaps. Fixed in Arduino `a7e5aea`: the next plug counts once both channels have held closed for 0.5 s.
4. **The R4 rebooted at 15:54:50** as the bundle went into the 90 °F bath, from a touch on the USB lead.
   The sketch restarts on pair 1 with its clock at zero and the ROM list in the same order, so nothing was
   lost but the wall-clock capture is the record to analyse, since the board's `t_s` restarts.
5. **The R4 prints its ROM list and header before a monitor can open the port**, so the capture sends
   `l` on connecting. The Mac has no pyserial; the capture is a stdlib `termios` script.

## In service

**PA11B failed at the kitchen air handler and was replaced on 2026-11-24.** The kitchen pair was
intermittent from its fitting on 2026-11-22: solid for a few hours at a time, partial around those,
absent for 15 hours overnight, and gone for good at 08:01 EST on 11-24. Both probes dropped together,
the return more often. Six supply readings on 11-23 were 38.5 °F and the return showed 38.6 °F, which
is 32 °F plus each probe's offset: an all-zero scratchpad, which passes the CRC and means the data
line was held low for the whole read. The air beads on the same unit never missed a sample.

With the plug out of the board, PA11B measured about 300 Ω from each of its three leads to the copper
pipe, and PA11A 1 to 2 MΩ. The DS2482 holds the data line up through about 1 kΩ, so a 300 Ω path to an
earthed pipe pulls the line low whenever the pipe sits near the board's ground. Two spares on the same
unit, off the pipe, listed on every poll for 13 minutes. With PA11B off the bus, PA11A answered at
once.

The return probe is now PA7B by its tag, ROM `28FF1668A316054F` (`28-0516a36816ff`), which
`docs/ds18b20-PA1-5-calibration.md` lists as the AMB spare. Its offset on the unit is +0.46 °F,
interpolated to 115 °F between PA7B's +0.451 K at 45 °F and +0.188 K at 140 °F; the AMB row's ice point
alone would give +0.89 °F. The pair is one probe from each batch, so its water ΔT carries the
difference between the two calibrations until the pair is zeroed on an idle coil. PA11A's 1 to 2 MΩ
is short of open: measure it again before trusting it through a cooling season.

A probe is checked with the plug out of the board, each lead to the pipe: open is sound.

## Rules

- A new DS18B20 batch gets a three-bath session before any of it goes into service, and the ice point
  alone would have caught this one: 26 °F in ice water.
- Read the Thermapen among the tips at the moment of each `logging` prompt, and again if the bath moves.
  In a sous vide, put the bundle in the circulator's outflow.
- Stem immersion of three inches or more; record it, since it decides how much of the slope is the chip.
- A probe set that fails at random across the bus is a contact; a probe that fails alone is a probe.
