<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
<!-- Copyright David Lewis -->

# Chiltrix CX75 in heating: how it behaves, why it trips, what to change

No setting has been changed on this analysis. Its recommendations are with Chiltrix (Matt Dail) for
review against the firmware, because the manuals list the parameters and describe none of the
control logic. Everything here is read from the 1 s register record and the CX65/CX75 IOM.

## 1. The record

All 234 registers (0–146 and 200–286) at 1 s from 2026-11-12 05:00 to 2026-11-14 09:42 EST:
188,091 sweeps, 104 compressor runs, four P1s, three P4s, one gap (the breaker cycle of 11-13,
17:26:56 to 17:30:04). Heating throughout, target 46 °C, ambient −0.8 to 13.0 °C on register 202.
The export is `Claude/cx75-2026-11-12-to-14-1s-raw.zip` in OneDrive. To rebuild it or cut another
window:

1. On the Pi: `sh scripts/chiltrix-raw-fetch.sh 2026-11-12T10 2026-11-14T15` (UTC hours).
2. On the Mac: `scripts/chiltrix-raw-build.py raw.csv.gz out.csv` forward-fills to one row per sweep.
3. `scripts/chiltrix-heating-events.py out.csv` prints the fault, low-speed and jump tables below.

## 2. Registers identified in this record

The Modbus document defines six status registers. The rest follow the panel's C-list at 200 + n
where the data agrees; these are the ones the analysis uses.

| Register | Reading | Evidence |
|---|---|---|
| 200 | Coil temperature, 0.1 °C | Tracks the saturation temperature of 211 |
| 201 | Discharge temperature, 0.1 °C | 61 to 108 °C, rises with 210 |
| 203 | Suction temperature, 0.1 °C | Equals 200 at zero superheat |
| 210 | High-side pressure, kPa | P1 at 4,188–4,311; `P84` reads 4200 |
| 211 | Low-side pressure, kPa gauge | Its saturation temperature matches 200 |
| 215 | High-side saturation temperature, 0.1 °C | Follows 210 |
| 228 | Commanded compressor frequency, Hz | 227 follows it at about 1 Hz/s |
| 239 | Second expansion valve (EVI), steps | 0 when stopped, 30 to 298 running |
| 240 | Main expansion valve, steps | 480 when stopped and in defrost |
| 245, 246 | Fan speed, rpm | 810 at full speed |
| 248 | Pump command, % | Confirmed earlier |
| 255, 258 | Line voltage, DC bus voltage | 238–247 V, 376–391 V |
| 256, 209 | Input current, compressor current, 0.1 A | 209 runs 5 % under 256 |
| 284 | Fault word | 2 is P1, 16 is P4, 32 a flow lockout |

1. Register 251 (driver status) reads 19 or 35 while running. It changed to 35 at each P4 and reads
   35 for half of all running time, so it is no clean limit flag.
2. Register 253 (driver's highest allowed frequency) reads 120 throughout and never fell.
3. Register 216 stayed 0 through every defrost. A defrost shows as 240 at 480 with 245 at 0.

## 3. How the unit controls itself

| Function | Behaviour in the record | Setting read |
|---|---|---|
| Stop and restart | Stops at 49.2 °C inlet, restarts at 44 °C | Target 46 °C, `P12` 2 |
| Frequency ceiling | 66 Hz at 10 °C ambient, 79 Hz at 0 °C | `P27` 100 |
| Pressure limit | Frequency cut from 3,900 kPa | `P28` 3900 |
| P1 trip | 4,188–4,311 kPa | `P84` 4200, `P86` 400 |
| Main valve | Closes 10 steps per 40 s at zero superheat, floor 66–76 | `P78` 1, `P79` 4, `P96` 54 |
| Pump | Slows as outlet minus inlet falls, to 65 % | `P95` 3, `P53` 50 |
| Fan | 810 rpm in cold weather, 500–800 rpm in mild at low speed | `P32` 4 |
| Defrost | Seven of 4–5 min on the night of 11-13 at −0.8 to 4 °C | `P38` 15, `P39` 12 |

The stop comes 3 °C above the target, so the tank runs 44 to 49.2 °C at the inlet and 52 °C
(126 °F) leaving. No listed parameter sets that 3 °C.

## 4. P1: refrigerant backs up at low speed in mild weather

All four P1s followed one sequence at 6 to 10 °C ambient:

1. The compressor held 36–38 Hz for 8 to 10 minutes with the inlet creeping from 47 to 47.8 °C,
   short of the 49.2 °C stop.
2. Suction equalled coil temperature, so superheat read zero, and the main valve stepped down to
   66–76.
3. The pump slowed to 65–73 %, 38 to 41 L/min.
4. High-side pressure rose about 900 kPa in two minutes with inlet and outlet water unchanged, and
   its saturation temperature reached 64 °C against 51 °C leaving water.

Step 4 reads as liquid filling the plate exchanger: the condensing surface shrinks, so the pressure
rises without the water moving. At minimum speed the `P28` limiter has no frequency left to cut.

Of 37 low-speed periods of 100 s or more, five had the valve at 76 or below and flow at 41 L/min
or below: the four P1s and a near miss at 4,163 kPa (11-12 23:57). No period with the valve at 83
or above passed 3,470 kPa.

| Start (EST) | Length | Valve min | Flow min | Pressure max | Result |
|---|---|---|---|---|---|
| 11-12 05:41 | 492 s | 71 | 37.9 | 4,192 | P1 |
| 11-12 14:18 | 631 s | 66 | 41.3 | 4,311 | P1 |
| 11-12 17:18 | 458 s | 73 | 40.2 | 4,225 | P1 |
| 11-13 00:53 | 501 s | 74 | 37.9 | 4,200 | P1 |
| 11-12 23:57 | 700 s | 74 | 37.9 | 4,163 | none |
| 11-13 01:19 | 677 s | 75 | 44.8 | 3,589 | none |
| 11-12 06:06 | 602 s | 83 | 42.5 | 3,470 | none |
| 11-12 10:43 | 1,223 s | 95 | 42.5 | 3,911 | none |

Three earlier findings follow from this. The P1 rate did not fall when the target went from 50 to
46 °C, because the water does not move during the rise. Every lockout came at 46 to 54 °F, because
cold nights have no long low-speed periods: on 11-13 and 11-14 they lasted 14 to 19 s. And the
fan is cleared: it ran at 800 rpm through the 11-13 00:53 P1 and the near miss.

## 5. P4: current overshoots on a mid-run jump to full speed

All three P4s of 11-13 came when the commanded frequency jumped mid-run from 44–47 Hz to 73–77 Hz
with the inlet at 44 °C or above. The compressor followed at about 1 Hz/s and input current passed
28.0 A while still accelerating.

The record holds 26 such jumps in heating. Fifteen peaked at 26.0 to 27.2 A without a trip, so the
drive's limit normally holds the current near 27 A; the three that reached 28.0, 28.4 and 28.5 A
tripped. A steady 28.2 A at 73 Hz on 11-14 07:51 did not trip, so the trip is not a plain threshold
on register 256. No P4 came in the 14 hours after the breaker cycle, at the same ambient.

| Frequency | Median current | Highest |
|---|---|---|
| 64–65 Hz | 21.7 A | 26.0 A |
| 66–67 Hz | 23.4 A | 26.9 A |
| 68–69 Hz | 24.8 A | 27.3 A |
| 70–71 Hz | 25.2 A | 28.0 A |
| 72–75 Hz | 26.1 A | 28.5 A |

## 6. Recommended changes, one at a time

| Parameter | Now | Proposed | Purpose |
|---|---|---|---|
| `P53` pump minimum | 50 % | 80 % | Flow of 46 L/min or more in low-speed periods |
| `P96` valve minimum | 54 | 90 | Keep the valve above the range where pressure ran away |
| `P27` maximum speed | 100 % | 90 % | Keep the mid-run jump under the current trip |

1. `P53` is the safe one: Chiltrix raised it from 40 to 50 on 2026-10-20 and 80 tops its range.
   Proof: register 248 never under 80 with the compressor running. It applies in cooling too, so
   revisit it in spring.
2. `P96` needs Chiltrix's agreement. The observed floor of 66–76 does not match the live 54, so
   `P96` may not be the floor in use. Superheat already reads zero with the valve at 110 to 180, so
   a higher floor should add no liquid return. Proof: register 240 at 90 or above and low-speed
   pressure under 3,600 kPa.
3. `P27` costs capacity where the unit runs flat out: at 34 to 37 °F it ran 93 to 100 % duty at
   75–77 Hz. The manual does not say what the percentage scales, so read register 228's ceiling
   after the change. If a room slips, raise the balance point to 40 °F
   (`docs/chiltrix-shoulder-season-heating-plan.md` §8.1).
4. Judge 1 and 2 at 43 to 50 °F, where the long low-speed periods occur, against 8 % of heating
   stops ending in P1.

For energy, water temperature is the largest gain, 2 to 3 % of COP per °C, and the chiller runs
under 40 % duty above 50 °F. Heating AU mode (`P24`–`P26`, `P48`, `P49`) lowers the target with
outdoor temperature, and the manuals do not give its curve. `P12` 2 → 3 lengthens the cycles and
lowers the mean tank temperature about 0.5 °C; it waits on the P1 changes. Defrost, fan and pump
mode stay as they are.

Leave alone: `P28` and `P84`–`P87` (pressure protection), `P78` and `P79` (valve control), `P88`
and `P99` (model codes), `P98` (wipes the factory settings).

## 7. Questions with Chiltrix

- Is register 240 the main valve and 239 the EVI valve, what sets the valve's floor, and what does
  it control to at low speed?
- Is the 3 °C above target at which the compressor stops a setting?
- What does Method 2 of `P04` and `P07` do?
- Register 65 reads 14 against the manual's 20 for the CX75. Which is right?
- What is the heating AU curve?
- What does the P4 trip act on, and is the acceleration rate a setting?
