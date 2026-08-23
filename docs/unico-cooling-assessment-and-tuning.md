# Unico Hydronic Cooling — Assessment and Tuning

**Date:** 2026-08-19.
**Status:** Assessment complete against existing instrumentation, including a logged comparison
against the plant this one replaced. Loop A is on MEDIUM and the Taco is confirmed on HIGH.
Remedies proposed, none built.
**System:** Chiltrix CX75 air-to-water heat pump feeding Unico M2430 air handlers through a
primary/secondary glycol loop, plus two Bosch BOVA direct-expansion zones on their own Unico air
handlers.

**Objective:** summer comfort and capacity. Efficiency and running cost are secondary. Heating is
rarely a problem, so it is monitored and left alone.

This document works in one direction. Section 3 establishes what the existing sensors already
prove, section 5 explains the hydraulics behind it, section 6 gives a verdict, and section 7
lists what to change in order of cost. Reference material that supports the argument without
advancing it lives in the appendices.

---

## Contents

**Assessment**

- [1. Purpose and how to read this](#1-purpose-and-how-to-read-this)
- [2. The system in brief](#2-the-system-in-brief)
  - [2.1 Plant, distribution and zones](#21-plant-distribution-and-zones)
  - [2.2 Elevation and pipe runs](#22-elevation-and-pipe-runs)
  - [2.3 Circulators and their settings](#23-circulators-and-their-settings)
- [3. What the existing instrumentation proves](#3-what-the-existing-instrumentation-proves)
  - [3.1 Measured state, 18 August 2026](#31-measured-state-18-august-2026)
  - [3.2 Every zone holds setpoint with the plant half idle](#32-every-zone-holds-setpoint-with-the-plant-half-idle)
  - [3.3 Humidity is the marginal axis](#33-humidity-is-the-marginal-axis)
  - [3.4 The buffer tank is fully mixed](#34-the-buffer-tank-is-fully-mixed)
  - [3.5 Loop pressure is adequate at the attic coil](#35-loop-pressure-is-adequate-at-the-attic-coil)
  - [3.6 What the existing sensors cannot settle](#36-what-the-existing-sensors-cannot-settle)
  - [3.7 Two limits on the data itself](#37-two-limits-on-the-data-itself)
  - [3.8 The previous plant is a controlled comparison](#38-the-previous-plant-is-a-controlled-comparison)
  - [3.9 One day at a colder target, cut short](#39-one-day-at-a-colder-target-cut-short)
- [4. Measurements that would close the gaps](#4-measurements-that-would-close-the-gaps)
  - [4.1 Free: read the pipe and the pump](#41-free-read-the-pipe-and-the-pump)
  - [4.2 The sensor package](#42-the-sensor-package)
  - [4.3 Flow without a flow meter](#43-flow-without-a-flow-meter)
  - [4.4 Air-side sensors on one air handler](#44-air-side-sensors-on-one-air-handler)
  - [4.5 A flow meter on the primary](#45-a-flow-meter-on-the-primary)
  - [4.6 Reading the master bedroom's fan stage](#46-reading-the-master-bedrooms-fan-stage)
- [5. Hydraulic analysis](#5-hydraulic-analysis)
  - [5.1 Primary flow is fixed, so primary delta-T reads house load](#51-primary-flow-is-fixed-so-primary-delta-t-reads-house-load)
  - [5.2 What that means for the 8 to 12 degree target](#52-what-that-means-for-the-8-to-12-degree-target)
  - [5.3 Elevation adds no pump head in a closed loop](#53-elevation-adds-no-pump-head-in-a-closed-loop)
  - [5.4 What elevation does affect](#54-what-elevation-does-affect)
  - [5.5 Friction head on the index circuits](#55-friction-head-on-the-index-circuits)
  - [5.6 What the calculation says about each coil](#56-what-the-calculation-says-about-each-coil)
  - [5.7 Choosing the pump speed, and whether balancing helps](#57-choosing-the-pump-speed-and-whether-balancing-helps)
  - [5.8 Can the primary supply both loops at maximum call?](#58-can-the-primary-supply-both-loops-at-maximum-call)
  - [5.9 What is still unresolved](#59-what-is-still-unresolved)
  - [5.10 Why the master bedroom calls its high fan stage](#510-why-the-master-bedroom-calls-its-high-fan-stage)
  - [5.11 Water temperature is the larger term, and distribution is the smaller one](#511-water-temperature-is-the-larger-term-and-distribution-is-the-smaller-one)
- [6. Verdict](#6-verdict)
  - [6.1 What optimal means here](#61-what-optimal-means-here)
  - [6.2 Scorecard](#62-scorecard)
  - [6.3 Conclusion](#63-conclusion)
  - [6.4 A clogged strainer sat underneath the comparison](#64-a-clogged-strainer-sat-underneath-the-comparison)
- [7. Remedy ladder, cheapest first](#7-remedy-ladder-cheapest-first)
  - [7.1 Costs nothing](#71-costs-nothing)
  - [7.2 Under $100](#72-under-100)
  - [7.3 $100 to $500](#73-100-to-500)
  - [7.4 $500 to $2,000](#74-500-to-2000)
  - [7.5 Ideal pump sizing, ignoring what is installed](#75-ideal-pump-sizing-ignoring-what-is-installed)
  - [7.6 Above $2,000, and the last resort](#76-above-2000-and-the-last-resort)
  - [7.7 What not to do](#77-what-not-to-do)
- [8. Sequence](#8-sequence)
- [9. Open questions](#9-open-questions)

**Appendices**

- [Appendix A — System reference](#appendix-a--system-reference)
- [Appendix B — Measurement physics](#appendix-b--measurement-physics)
- [Appendix C — Primary/secondary hydraulics](#appendix-c--primarysecondary-hydraulics)
- [Appendix D — The BOVA direct-expansion zones](#appendix-d--the-bova-direct-expansion-zones)
- [Appendix E — Air-handler node build specification](#appendix-e--air-handler-node-build-specification)
- [Appendix F — pivac integration](#appendix-f--pivac-integration)
- [Appendix G — Calibration and analysis methods](#appendix-g--calibration-and-analysis-methods)
- [Appendix H — Utility-room instrumentation](#appendix-h--utility-room-instrumentation)
- [Appendix I — Operational integration](#appendix-i--operational-integration)
- [Appendix J — The master bedroom thermostat](#appendix-j--the-master-bedroom-thermostat)
- [Appendix K — The previous plant and the Chiltrix controls](#appendix-k--the-previous-plant-and-the-chiltrix-controls)

---

## 1. Purpose and how to read this

The question is whether the hydronic cooling system is delivering what it can, and if not, what
to change. The system holds every setpoint today, so this is an optimisation exercise rather
than a fault hunt.

Four observations started it. Secondary-loop water rarely shows the 8 to 12 °F ΔT that a hydronic
coil is designed around. One circulator serves several air handlers on each secondary loop, which
raises the question of whether any single coil gets its share. Three of the five zones sit a storey
above the mechanical room, with one coil in the attic, which raises the question of pump head. And
the master bedroom runs its high fan stage more often than a zone with capacity in hand should.

Section 5 answers all four, and the last two land in the same place. The low ΔT is what a
fixed-flow primary reads at part load, and the design band arrives at design load. Elevation costs
no pump head at all in a closed loop. The shared-circulator concern is real: the two zones sharing
Loop A's 105 ft index circuit read humid, and the one zone with a circulator to itself over 15 ft
reads dry. The master bedroom sits at the far end of that index circuit, and its high fan stage is
the symptom that circuit predicts.

Sections 1 to 3 are assessment, section 5 is analysis, sections 6 to 8 are decisions. The
appendices carry the supporting physics, the build specifications, and the reference tables. A
reader who wants only the answer can read section 6.

---

## 2. The system in brief

Full detail is in [Appendix A](#appendix-a--system-reference).

### 2.1 Plant, distribution and zones

A Chiltrix CX75 air-to-water heat pump makes chilled water at 4.3 tons nominal cooling, 51,600
BTU/hr, through a buffer tank. An NTI Trinity Ti-200 boiler makes hot water for the same
distribution in winter. Each source carries its own primary pump into a header. Two secondary
loops tap that header through closely spaced tees, and a Honeywell HZ-432 drives one zone valve
per zone with no dampers.

Five zones have thermostats. Three cool on chilled water and two cool on their own Bosch BOVA
direct-expansion condensers.

| Zone | Air handler | Level | Loop | Order | Cooling source | Water side |
|---|---|---|---|---|---|---|
| Kids room | Unico M1218 | Ground | A | first | Chiltrix | Chilled and hot |
| Master bedroom | Unico M2430 | Second, coil in attic | A | second | Chiltrix | Chilled and hot |
| Downstairs family and utility | Unico M2430 | Ground | B | first | Chiltrix | Chilled and hot |
| Kitchen | Unico M3036 | Second | B | second | Bosch BOVA (`BOS1`) | Hot only, hydronic module |
| Great room | Unico M3036 | Second | B | third | Bosch BOVA (`BOS2`) | Hot only, hydronic module |

The two M3036 units carry 6-row refrigerant coils for cooling and a hot-water hydronic module
for heat. They leave the water side entirely in summer and rejoin it as the largest coils on the
system in winter.

Chilled water therefore splits two coils onto Loop A and one onto Loop B in summer, because the
kitchen and great room cool on their own condensers. In winter every zone runs on boiler hot
water, so Loop A carries two coils and Loop B carries three.

| | Loop A | Loop B |
|---|---|---|
| Summer, chilled | kids room and master bedroom | downstairs family room only |
| Winter, hot | kids room and master bedroom | family room, kitchen, great room |

### 2.2 Elevation and pipe runs

Two of the six air handlers sit a storey above the mechanical room and one of those is in the
attic. Pipe lengths are David's estimates, taken as one-way distance from the secondary tees to
the coil.

| Loop | Zone | Rise | Run | Notes |
|---|---|---|---|---|
| A | Kids room | 0 ft | ~75 ft | Longest ground-level run |
| A | Master bedroom | ~10 ft above the kids branch | ~20 ft past the rise | Coil in the attic, the system high point |
| B | Downstairs family room | 0 ft | ~15 ft | Includes the start of the secondary loop and a short branch |
| B | Kitchen | ~10 ft | ~15 ft past the rise | |
| B | Great room | ~10 ft | ~20 ft past the kitchen branch | |

The master bedroom is the index circuit for Loop A at roughly 105 ft one way, or 210 ft of pipe
out and back. The great room is the index circuit for Loop B at roughly 60 ft one way, or 120 ft
out and back. David's figures mix conventions, some quoted one way and some as "to and from", so
treat every developed length here as ±30 %. The conclusion in [5.5](#55-friction-head-on-the-index-circuits) rests on pipe size, which the
spread does not change.

### 2.3 Circulators and their settings

| Position | Pump | Speed | Rating |
|---|---|---|---|
| Boiler primary | Grundfos UP26-99F | HIGH | 1/6 HP |
| Primary distribution, tank to header | Taco 0015-MSF3-IFC | HIGH, read at the switch | 1/20 HP, 18 GPM and 17 ft maximum |
| Chiller to tank | CX75 internal circulator | n/a | On the far side of the buffer tank |
| Loop A secondary | Grundfos UP26-99F | MEDIUM | 2 zones year-round |
| Loop B secondary | Grundfos UP26-99F | LOW | 1 zone in summer, 3 in winter |

Both secondary loops are **insulated PEX, part 1¼" and part 1"**, with the long main runs believed
to be 1¼" and the smaller size appearing nearer the air handlers. The split is not measured. PEX
matters to the arithmetic: 1¼" PEX has an inside diameter near 1.07" against 1.265" for 1¼" type L
copper, so it carries roughly the friction of 1" copper rather than of its own nominal size, and
1" PEX is near 0.87". [5.5](#55-friction-head-on-the-index-circuits) brackets the uncertainty.

The chiller primary is materially the smallest pump in the system. A Taco 0015-MSF3-IFC is a
1/20 HP circulator against the UP26-99F's 1/6 HP, and its 17 ft maximum head is roughly half the
Grundfos figure. Section 5 tests whether that matters.

> The primary covers the secondaries with little to spare. Loop A on MEDIUM and Loop B on LOW draw
> 15.8 GPM combined, against a Taco on HIGH delivering 14.5 to 16.4 GPM depending on the fitting
> allowance ([5.8](#58-can-the-primary-supply-both-loops-at-maximum-call)). Raising either secondary
> again crosses the primary, and the closely spaced tees then mix backwards
> ([Appendix C](#appendix-c--primarysecondary-hydraulics)).

> Loop B's tap is a seasonal setting. It drives one coil in summer and three in winter, so no
> single tap suits the whole year. Raise it before heating season, alongside the 25 % to 30 %
> glycol top-up. Nothing automates either.

---

## 3. What the existing instrumentation proves

The house already carries enough sensors to answer most of the question. Four DS18B20s on the
1-wire bus give primary supply and return either side of the tees plus two buffer-tank probes.
An Emporia CT gives Chiltrix electrical power. RedLink gives per-zone temperature, setpoint and
humidity, and an Arduino gives hydronic loop pressure.

### 3.1 Measured state, 18 August 2026

Eight hours ending 19:57 EDT. Outdoor air averaged 80.0 °F and peaked at 85.0 °F, so this is a
warm evening rather than a design day. Values are conditioned on the chiller drawing more than
1500 W, which excludes its 8.8 W idle floor.

| Quantity | Value |
|---|---|
| Chiller duty above 1500 W | 46 % of the window, 221 of 476 minutes |
| Chiller power while running, mean | 1,903 W |
| Chiller power, peak | 3,537 W |
| Primary supply `IN`, mean while running | 47.8 °F |
| Primary return `OUT`, mean while running | 53.1 °F |
| **Primary ΔT, mean while running** | **5.3 °F** |
| **Primary ΔT, peak** | **10.7 °F** |
| Buffer tank `UBT`, mean while running | 47.4 °F |
| Tank stratification, `UBT − LBT` | 0.03 °F |
| `IN − UBT` | 0.35 °F |
| Hydronic loop pressure, 24 h mean | 21.1 psi, range 19.4 to 22.7 |

Primary ΔT binned against chiller power over 24 hours appears in [5.1](#51-primary-flow-is-fixed-so-primary-delta-t-reads-house-load), and it carries this
document's central finding.

Zone state over the same window:

| Zone | Cooling source | Temperature | Setpoint | Droop | RH mean | RH peak, 24 h |
|---|---|---|---|---|---|---|
| Master bedroom | Chiltrix | 76.0 °F | 76 | 0.0 | 50.9 % | 60 % |
| Downstairs family room | Chiltrix | 76.0 °F | 76 | 0.0 | 45.9 % | not sampled |
| Kids room | Chiltrix | 74.0 °F | 74 | 0.0 | 53.7 % | 59 % |
| Kitchen | BOVA `BOS1` | 76.0 °F | 76 | 0.0 | 48.6 % | not sampled |
| Great room | BOVA `BOS2` | 75.0 °F | 75 | 0.0 | 53.4 % | not sampled |

### 3.2 Every zone holds setpoint with the plant half idle

All five zones sat on setpoint for the whole window, and the chiller was idle 54 % of the time.
On an 80 °F evening the system has better than half its capacity in reserve, and no zone is
capacity-limited or control-limited at these conditions.

That result also removes the most common reason to instrument a coil. Per-coil BTU measurement
earns its keep when a zone cannot hold setpoint and the cause is unclear. No zone qualifies.

The exposure is a design day rather than an average one. Three Chiltrix zones carry roughly 6
tons of coil against a 4.3-ton chiller, so a simultaneous full call on a 95 °F afternoon
saturates the plant before it saturates the distribution. That case is detectable from existing
data alone and has not yet been observed.

### 3.3 Humidity is the marginal axis

The master bedroom reached 60 % RH and the kids room 59 % over 24 hours, against a comfort
target nearer 50 %. Both are Chiltrix zones. The kitchen, on a direct-expansion BOVA, averaged
48.6 % over the same period.

Part of the gap follows from coil surface temperature. A direct-expansion evaporator runs near
40 °F, while a chilled-water coil fed at 47.8 °F runs a surface temperature closer to 52 °F.
Warmer surfaces condense less moisture, so a chilled-water zone holding setpoint dead-on can read
humid while the direct-expansion zone beside it reads dry.

That explains the kitchen and leaves a sharper pattern unexplained. All three Chiltrix zones share
one plant, one water temperature and one coil type, and they do not read alike.

| Zone | Loop | Coils sharing the circulator | Calculated flow | Mean RH |
|---|---|---|---|---|
| Downstairs family room | B | 1 in summer | 6.5 GPM | **45.9 %** |
| Kids room | A | 2 | 4.3 GPM | 53.7 % |
| Master bedroom | A | 2 | 3.9 GPM | 50.9 % |

**The split between loops matches. The split within Loop A does not.** The family-room coil has a
circulator to itself over a 15 ft run and receives roughly half again what either Loop A coil does,
and it is markedly the driest zone. More water flow removes more moisture
([B.6](#b6-water-flow-and-dehumidification-move-together)), so the loop-level difference reads as
hydraulic. Within Loop A the kids room carries more flow than the master bedroom and still reads
2.8 points wetter, so something other than flow dominates there.

**Latent load is the difference, and the kids zone has an unusual amount of it.** That zone is a
small space carrying the laundry room and two full baths, and the showers are frequent. Laundry and
showers are close to pure latent gain, so the zone presents a large moisture load on a small
sensible one.

That combination produces exactly what is measured. The M1218 satisfies 74 °F quickly against a
small sensible load and cycles off, and a coil that cycles dehumidifies poorly: its surface warms
between calls, and blower run-on re-evaporates condensate off the fins back into the airstream.
The room holds its setpoint to the degree and stays wet.

It also means **more sensible capacity would make that zone worse**, so a larger air handler is the
wrong direction ([7.1](#71-costs-nothing)). The master bedroom's coil sits in an attic, where duct
leakage draws hot humid air into the return, which is a separate mechanism for a separate zone.

This is the one measured shortfall against the stated objective.

### 3.4 The buffer tank is fully mixed

Upper and lower tank probes differ by 0.03 °F. Both are fully seated in the tank's two ½" sensor
wells at different heights, and the chiller does not read them; they serve pivac alone. The pair is
therefore a genuine top-to-bottom measurement, and it says the tank holds thermal mass with no
stratification. Its state is one temperature rather than a charge profile.

The unit is a Chiltrix **VCT37C**: 37 gallons, stainless inner tank and jacket, **2" polyurethane
insulation**, 18.5" diameter by 58.5" tall, 74 lb empty. It carries six 1" NPT ports on one side,
three in and three out, four 1½" NPT ports on the other, two in and two out, and **two ½" sensor
wells**. The 1½" ports match the header, so the four-pipe arrangement uses both sets. At 8.6
gallons per ton against the CX75 it is generous by the usual rule, and on 25 % propylene glycol it
stores **304 BTU/°F** including the shell. The 2" of polyurethane also means standby loss is small,
which keeps the energy-balance bias in [4.2](#42-the-sensor-package) to well under a percent.

That storage is enough to stop an inverter chiller short-cycling at part load and not enough to
mask a capacity shortfall:

| House load | Ride-through on a 6 °F tank swing |
|---|---|
| 51,600 BTU/hr, design | 2.1 minutes |
| 33,000, the measured mean | 3.3 minutes |
| 20,000 | 5.5 minutes |
| 12,000, one zone | 9.1 minutes |

The chiller's own band sets which row applies. It cuts out at its 50 °F target and restarts 2 °C
above it, so the working swing is **3.6 °F rather than 6**, and every figure in the table shortens to
about six-tenths of what it shows: roughly 2 minutes at the measured mean load.

**So the tank is an anti-cycling device rather than a reserve.** On a design-day afternoon it buys
two minutes, which means [6.2](#62-scorecard)'s untested design-day question is about plant
capacity and cannot be answered by tank size. Its full mixing is also what makes the lumped
thermal-capacity correction in [4.2](#42-the-sensor-package) valid.

Two consequences follow. Tank depletion shows as the whole tank warming rather than as a
descending thermocline, so watch `UBT` absolute rather than `UBT − LBT`. And the lower probe reads
nothing the upper one does not, though it is properly mounted and the Modbus feed supplies chiller
leaving water without disturbing it ([4.2](#42-the-sensor-package)).

### 3.5 Loop pressure is adequate at the attic coil

The hydronic loop runs 19.4 to 22.7 psi, averaging 21.1. The attic coil sits roughly 25 ft above
the gauge, which costs 25 ÷ 2.31 ≈ 10.8 psi of static head, leaving about 10 psi at the coil.

Ten psi clears the 5 psi minimum that keeps air vents working and keeps dissolved air in
solution. The 3.3 psi swing across the day is normal thermal expansion, which also shows the
expansion tank is charged and doing its job.

Air-binding at the attic coil is therefore ruled out as a standing condition on pressure grounds.
An air vent that has failed shut would still bind that coil, which is a visual check rather than
a measurement.

### 3.6 What the existing sensors cannot settle

Four questions remain open, and each needs a sensor the house does not have.

Secondary-loop ΔT is unmeasured. `IN` and `OUT` bracket the primary side of the closely spaced
tees, so they measure what the whole house extracts and say nothing about either loop
individually. David's observation of low secondary ΔT comes from spot readings rather than from
logged data.

Coil entering water temperature is unmeasured, so reverse mixing at the tees cannot be confirmed
or ruled out. If combined secondary flow exceeds primary flow, the loops pull return water
backwards through the return tee and feed the coils water warmer than the tank
([Appendix C](#appendix-c--primarysecondary-hydraulics)). That costs capacity in a way nothing
downstream can distinguish from an undersized chiller.

Flow is unmeasured anywhere. Every capacity figure in this document is derived from electrical
power and an assumed efficiency, so it carries that assumption's error.

Fan stage is unmeasured, and Honeywell does not supply it. The master bedroom runs its high fan
stage often enough to be noticeable, and a two-stage thermostat calls stage 2 when stage 1 fails to
hold setpoint, so this is a capacity statement about that coil. Nothing logs it. The Total Connect
payload behind `pivac.RedLink` was read directly to check: it carries `EquipmentOutputStatus`, which
resolves to off, heat or cool and nothing finer, and a `fanData` block giving the user's fan mode
rather than the speed the equipment runs. Reading Y2 needs a wire
([4.6](#46-reading-the-master-bedrooms-fan-stage)).

### 3.7 Two limits on the data itself

Quantitative ΔT starts 18 August 2026. Both `pivac.OneWireTherm` and `pivac.RedLink` emitted
whole-Kelvin temperatures until that date, and RedLink truncated rather than rounded, so every
zone read up to 1.8 °F cold. A ΔT built from two such readings moves in 1.8 °F steps, which is
±45 % on a 4 °F primary delta. Both are fixed and now emit two decimals. Earlier history cannot
be recovered.

Droop resolution is limited by Honeywell rather than by pivac. The thermostats report whole
degrees Fahrenheit, so post-fix each zone has held one constant value. Droop is therefore a 1 °F
signal that reads 0 or ±1, which is adequate to detect a zone losing setpoint and inadequate to
rank zones against each other. Humidity, reported to 1 %, is the finer signal of the two and the
one that moves.

### 3.8 The previous plant is a controlled comparison

Two Unico UniChillers ran this house until they failed on 4 July 2026, and the same sensors logged
them. They were 5-ton on/off machines controlling on **leaving** water, set to a 38 °F setpoint with
a 10 °F differential, so they cut out at 38 °F and back in at 48 °F. Unico's own guide puts the floor
at exactly that: "no lower than 38 °F for cooling". One ran at a time this season. The Chiltrix
modulates and controls on **return** water, which is a different control philosophy on the same
distribution, the same coils and the same zones.

David reports the master bedroom held on its low fan stage under the old plant except on the hottest
days. The logged data says why. Both eras below are binned by outdoor air, with `IN` taken only while
the master bedroom was calling and the loop was carrying chilled water:

| Outdoor | Old `IN` | New `IN` | Old duty | New duty | Old RH | New RH |
|---|---|---|---|---|---|---|
| 65–70 °F | 41.5 °F | 49.4 °F | 7.1 % | 11.3 % | 54.1 % | 59.0 % |
| 70–75 | 41.3 | 49.1 | 23.2 | 26.1 | 46.0 | 56.5 |
| 75–80 | 41.3 | 48.2 | 31.9 | 47.6 | 44.9 | 53.3 |
| 80–85 | 41.4 | 47.4 | 46.0 | 68.5 | 42.7 | 49.0 |
| 85–95 | 41.8 | 47.4 | 85.6 | 68.1 | 42.9 | 48.5 |

Duty and RH are the master bedroom's. Old era 1 June to 4 July, new era 30 July to 19 August,
5-minute samples throughout.

**The loop runs 6 to 8 °F warmer at every outdoor condition, the master bedroom runs longer, and it
sits 5 to 10 points more humid.** At 80 to 85 °F outdoor the zone went from 46 % of the time to
68 %. Weather does not flatter the comparison: the new era is the milder of the two, peaking at
90.1 °F against the old era's 98.3 °F, and its top bin holds only 235 samples, so read that last row
lightly.

**Neither plant is capacity-limited at these conditions.** `IN` barely moves across the outdoor range
in either era, which is what a held target looks like; a plant running out would show `IN` climbing
with load. The 6 to 8 °F is a setting rather than a shortfall, which is what makes it recoverable.

**The setting is 50 °F of return water, and the new plant cycles too.** The Chiltrix cuts out at its
50 °F target and does not restart until the return rises 2 °C above it, about 53.4 °F, so the loop
runs a **50 to 53.4 °F band** rather than a steady figure. Set against the UniChillers' 38 to 48 °F,
the new band sits entirely above the old one's midpoint and its cold end is warmer than the old
plant's warm end.

> **The era comparison survives an uncalibrated sensor.** `IN` measures 47.4 to 49.4 °F against a
> band the controller puts at 50 to 53.4, so the DS18B20 and the Chiltrix's own return sensor
> disagree by two or three degrees, and neither has had matched-pair calibration
> ([G.1](#g1-matched-pair-calibration-before-install)). It does not matter to the finding. Both eras
> are measured by the same probe in the same place, so any offset cancels in the difference, and the
> difference is what this section reports. It does matter when comparing `IN` against a controller
> reading, which is why the target steps in [7.1](#71-costs-nothing) are scored on the change in
> `IN` rather than on its absolute value.

**A 42 °F target would put `IN` near 42 °F**, close to the old plant's measured 41.3 to 41.8. The two
settings are not comparable, though, and the difference is the reason to step carefully rather than
jump. **The UniChillers sensed leaving water and the Chiltrix senses return**, so the same loop
temperature sits on opposite sides of each machine's own evaporator ΔT. Matching the old loop asks
the Chiltrix for leaving water near 33 °F, colder than the UniChillers ever made, whose floor was
38 °F. That is inside what Chiltrix permits and it is not free
([7.1](#71-costs-nothing), [Appendix K](#appendix-k--the-previous-plant-and-the-chiltrix-controls)).

> **Quantisation cuts the right way here.** `pivac.OneWireTherm` rounded to whole Kelvin before 18
> August, so individual `IN` readings move in 1.8 °F steps across both eras
> ([3.7](#37-two-limits-on-the-data-itself)). Rounding is unbiased in the mean, and this difference
> is 6 to 8 °F against a 1.8 °F step, so it survives its own precision by a wide margin. `RedLink`
> truncated rather than rounded, which biases droop low in both eras alike, so era-to-era droop
> comparisons hold while absolute droop is understated. The old chillers' call relays are not used
> here: the comparison rests on water temperature and on the zone's own `statenum`.

### 3.9 One day at a colder target, cut short

The target went to 46 °F at about 21:30 on 20 August and the chiller locked out on E14 at 19:01 the
next evening ([7.1](#71-costs-nothing)). That leaves one usable afternoon, and it is the only direct
test of this document's central claim.

Afternoons only, 12:00 to 19:00 local, hourly means:

| Afternoon | `IN` | Outdoor | Outdoor dew point | Master RH | Master temp | **Master dew point** |
|---|---|---|---|---|---|---|
| 19 Aug | 47.8 °F | 82.4 °F | 72.4 °F | 50.7 % | 76.0 °F | 56.4 °F |
| 20 Aug | 50.2 | 73.0 | 73.0 | 50.9 | 76.0 | 56.5 |
| **21 Aug, colder target** | **46.6** | 76.7 | **73.3** | **47.7** | 76.0 | **54.7** |

**Indoor dew point fell 1.7 °F while outdoor dew point rose**, which is the result that matters. The
weather was working against the trial rather than for it: 21 August carried the wettest outdoor air
of the three days. Room temperature held at exactly 76.0 °F throughout, so RH and dew point tell the
same story and neither is confounded by the other.

**The trial delivered only part of the change that was asked for.** A 46 °F entry stores as 7 °C,
44.6 °F, yet `IN` averaged 46.6 °F through the afternoon, because the antifreeze protection was
clipping the bottom off every cycle ([7.1](#71-costs-nothing)). So **1.2 to 3.6 °F of actual water
temperature bought 1.7 °F of indoor dew point**, and the full change is worth more than that.

**Zone duty improved and cycle length did not.** The kids room ran **48.8 % of the 20th at 73.0 °F
outdoor and 40.5 % of the 21st at 76.7 °F** — less running on a warmer day, which is the capacity
gain arriving. Its cycles also became shorter and more numerous, 16 starts at 13 minutes against 21
starts at 8 minutes. Those two move together arithmetically at lower duty and the second is not an
improvement, so read the duty figure and not the cycle count. The 19 August column cannot be compared
at all: at 85.7 % duty that zone was close to running continuously, which produces few long cycles
because it never got to stop.

> **One afternoon, seven hourly means per day.** The direction is consistent across every metric and
> the outdoor dew point rules out the obvious confounder, but this is a single day and it is not a
> substitute for the staged trial in [8](#8-sequence) once the protection has been moved.

---

## 4. Measurements that would close the gaps

Ordered by cost. Each entry states what it settles.

### 4.1 Free: read the pipe and the pump

Three unknowns need no purchase and change the analysis materially.

**The master bedroom's cooling-stage settings.** Whether that thermostat upstages on a differential,
on a timer, or under a rule that holds the high stage to the end of every call decides whether its
high fan stage reports a capacity shortfall or a configuration choice
([Appendix J](#appendix-j--the-master-bedroom-thermostat)). Read these before instrumenting
anything.

**Whether balancing valves exist on the branches.** The calculation in
[5.7](#57-choosing-the-pump-speed-and-whether-balancing-helps) puts the master bedroom at 68 to 82 % of design flow at every pump speed while the kids room
passes 100 %, so redistribution is worth more than another speed. Whether the hardware to do it
already exists decides the cost.

**Confirm the copper sections near the air handlers.** The mains are 1¼" PEX, which governs the
friction, and the copper runs are the easier pipe. Their length matters only if they are shorter
or smaller than assumed.

### 4.2 The sensor package

Four DS18B20s and a Modbus feed are all that need adding. Zone call state is already collected,
and a flow meter is optional.

| # | Sensor | Where | Answers |
|---|---|---|---|
| 1–2 | Modbus from the CX75 | Chiller entering and leaving water, plus pump speed | Chiller output and COP with the existing CT. Pump speed also settles whether the internal circulator modulates |
| 3 | `LOOPA_SUP` DS18B20 | Loop A supply, on the copper just past its tee | Against `IN` and `UBT`, the mixing check |
| 4 | `LOOPA_RET` DS18B20 | Loop A return, on the copper just before its tee | Loop A ΔT and capacity |
| 5 | `LOOPB_SUP` DS18B20 | Loop B supply, same | Same for Loop B |
| 6 | `LOOPB_RET` DS18B20 | Loop B return, same | Same for Loop B |
| 7–9 | Already collected | `pivac.RedLink` `statenum`, charted on the Grafana stats panel | Per-zone call state and runtime. See below |
| 10 | Flow meter, pulse output | Distribution header near `IN` | Absolute BTU/hr and system COP. Optional |

#### The Modbus feed

The wired controller in the utility room displays everything and stores nothing, so a separate
Modbus master is needed to get a time series into pivac.

**Bus first, before anything else.** Modbus RTU allows one master on a segment. If the existing
controller polls the chiller, adding a second master onto the same pair produces collisions and
can disturb the controller. Two safe routes:

- **Find the dedicated BMS port.** Chiltrix documents a Modbus connection for building-management
  integration that is separate from the wired controller's terminals. That is the clean answer if
  this unit has one.
- **Listen only.** Wire the adapter's receive pair and never transmit, decoding the controller's
  polls and the chiller's replies as they pass. No collisions, and it works on any bus, at the cost
  of writing a decoder rather than issuing reads.

**Adapter.** Either a USB RS-485 adapter directly on the Pi, which sits in the same room and needs
no new network node, or an RS-485 to Ethernet gateway presenting Modbus TCP, which matches the
pattern the Arduino nodes already use. RS-485 carries far further than this house needs, so cable
length does not decide it. The USB route is fewer moving parts; the gateway route keeps the Pi's
USB free and survives a Pi swap.

**Registers worth having**, in rough order of value:

| Value | Use |
|---|---|
| Leaving water temperature | Chiller output with the flow below, and the reference for every mixing check |
| Entering water temperature | Chiller ΔT |
| **Water flow** | See below. Several CX models report it, and it removes the need for a flow meter |
| Pump speed | Confirms the internal circulator's modulation, and proxies flow if flow is absent |
| Compressor frequency | Load state, and it separates a modulating unit from a cycling one |
| Fault and status codes | Freshness and diagnostics |

**The register map is not published, and the parameters are.** Chiltrix states plainly that it
"does not support Modbus programming or training, it's available for experienced Modbus users
only", and no register map appears on the site. What the CX-series IOM does publish is the
controller's C-parameter list, and those are the same values the bus carries:

| Parameter | Meaning | Range | Use here |
|---|---|---|---|
| `C05` | AC outlet water temp | −30 to 97 °C | **Chiller leaving water** |
| `C04` | Plate heat exchanger inlet temperature | −30 to 97 °C | **Chiller entering water** |
| `C13` | Usage side water flow volume | 0 to 100 L/min | **Flow.** 1 L/min = 0.264 GPM |
| `C27` | Compressor frequency | actual Hz | Load state, and modulating against cycling |
| `C09` | Compressor current, from the main IPM | 0 to 30 A | Cross-check against the Emporia CT |
| `C02` | Ambient temp | −30 to 97 °C | Load normalisation |
| `C10`, `C11` | High and low pressure | bar | Refrigerant-side diagnostics |
| `C34`–`C36` | Water pump states | 1 run, 0 stop | Run state, though not speed |

**`C13` is the register that matters**, and its presence means the flow substitution in this
section is available rather than hypothetical. Pump *speed* has no obvious C parameter, so if the
controller displays it, it sits elsewhere in the map.

**Two community register maps exist, and they contradict each other.**
[jasipsw/homeassistant-chiltrix-modbus](https://github.com/jasipsw/homeassistant-chiltrix-modbus)
publishes a Home Assistant configuration for the CX50-2, over Modbus TCP through a Waveshare
RS-485 gateway on port 502, slave 1, holding registers.
[gonzojive/heatpump](https://github.com/gonzojive/heatpump) publishes a Go implementation for the
CX34. **The two assign different meanings to nearly every address**, so at most one of them
describes the CX75 and neither may be assumed to:

| Register | jasipsw, CX50-2 | gonzojive, CX34 |
|---|---|---|
| 202 | Water inlet temperature | Ambient temperature |
| 203 | Water outlet temperature | Suction temperature |
| 204 | Ambient temperature | Plate heat exchanger temperature |
| 205 | Coil temperature | AC outlet water temperature |
| 213 | DHW setpoint | **Water flow rate** |
| 257 | **Flow rate** | Compressor phase current |
| 258 | Compressor speed | Bus line voltage |
| 261 | System pressure | Compressor total running time |
| 281 | Compressor starts | Water inlet sensor 1 |

Only the unit itself can settle which applies, which is why the scan comes before the module.

**The CX50-2 map**, the closer match on model generation:

| Register | Value | Type | Scale | Use |
|---|---|---|---|---|
| 203 | Water outlet temperature | int16 | 0.1 °C | **Chiller leaving water** |
| 202 | Water inlet temperature | int16 | 0.1 °C | **Chiller entering water** |
| 257 | Flow rate | uint16 | 0.1 L/min | **The flow term.** 1 L/min = 0.264 GPM |
| 260 | Pump speed | uint16 | % | Confirms the internal circulator's modulation |
| 258, 259 | Compressor and fan speed | uint16 | % | Load state |
| 256 | Current power | uint16 | 1 W | **Cross-check against `electrical.emporia.house.chiltrix`** |
| 281 | Compressor starts | uint32, word swap | | Cycling rate, which is what the buffer tank exists to limit |
| 264 | Total run hours | uint32, word swap | | Duty accounting |
| 243, 244 | Operating state, error code | uint16 | | Status and freshness |
| 209 | Setpoint temperature | int16 | 0.1 °C | **Reads the target back** |
| 214 | Antifreeze temperature | int16 | 0.1 °C | **`P59` at runtime** |
| 261 | System pressure | uint16 | 0.1 bar | Refrigerant side |
| 204 | Ambient temperature | int16 | 0.1 °C | Load normalisation |
| 205, 206, 207 | Coil, discharge, suction temperature | int16 | 0.1 °C | Refrigerant-side diagnostics |
| 213 | DHW setpoint | int16 | 0.1 °C | |
| 285 | Defrost count | uint16 | | Heating season |

Four of those carry more than they look. **Register 256 reports the unit's own power**, which
validates the Emporia CT and is validated by it, so a disagreement points at one or the other
rather than leaving both suspect. **Register 281 counts compressor starts**, measuring short
cycling directly against the 37-gallon tank's 2 to 9 minute ride-through
([3.4](#34-the-buffer-tank-is-fully-mixed)). **Register 209 reads the target back**, which shows
whether a Fahrenheit entry landed on the whole-°C value intended
([K.3](#k3-the-parameters-that-matter)). And **register 214 exposes `P59`**, the limit that latched
E14, without walking the parameter menu.

**Parameter numbers may be register addresses.** In the CX34 map, register 53 is the EC water pump
minimum speed, which is `P53` exactly. If that holds on the CX75 then `P59`, `P65` and `P109` sit
at registers 59, 65 and 109. **One read settles it: fetch register 53 and see whether it returns
40**, the value `P53` holds on this unit. A known-exact answer makes it a better first probe than
any temperature. That map also carries register 225, the inner water flow switch behind a P5 alarm,
and register 284, the live fault code.

**Chiltrix documents the connection parameters.** The ProtoAir gateway guide, shipped alongside the
CX50-2 IOM in the same repository, specifies what any device on the chiller's RS-485 port must use:

| Setting | Value |
|---|---|
| Protocol | Modbus RTU |
| Baud, parity, data, stop | 9600, none, 8, 1 |
| Node-ID | 1 for a single chiller, 1 to 255 where there are more |
| Terminals | `A` = "+", `B` = "−", plus RS-485 GND |

Bias resistors are 510 Ω and belong at one point on the bus only. Both PDFs, and COP calculation
templates covering the same arithmetic as [4.3](#43-flow-without-a-flow-meter), are in that
repository; the PDFs are also filed in `~/OneDrive - DGLC/Claude/HVAC Manuals/`.

> **Verify every address against the panel.** The two maps disagree, neither covers the CX75, and
> firmware moves addresses within a family. **The CX75's P and C codes match its own controller
> display for every value of interest here**, so the display is the reference: `C04`, `C05`, `C13`
> and `C27` against 202, 203, 257 and 258, and `P53` against 53. Where a value reads as nonsense,
> try the address ±1 for the 0-based and 1-based ambiguity. Use function code 3 only until the map
> is confirmed.

**If a register disagrees, the controller settles it.** Poll the block, watch which value tracks
`C05` on the display as the chiller runs, and correct the map against the parameter list above.

> **Read only.** Writing to a misidentified register can move a setpoint or a protection limit.
> Use function codes 3 and 4 and never 6 or 16 until the map is confirmed.

For reference on what a CX-series pump can drive: the CX65 publishes a maximum flow of 12.5 GPM, a
design flow of 10.6 GPM, and 16 ft of head at 10 GPM, "leaving about 24 ft of head net of the
unit". The chiller-to-tank run here is 12 ft of pipe, so the internal pump has far more head
available than that circuit consumes.

**If flow is in the register map, it substitutes for the flow meter.** The chiller's flow is only
the chiller-to-tank circuit and never reaches the loops, which is the objection to raise first. It
is used here as an energy measurement rather than a flow one. **The tank decouples flow and
conserves energy**, so what crosses it is BTU/hr:

```
Q_chiller = K × GPM_chiller × ΔT_chiller          both from Modbus
```

When the tank is thermally steady, whatever the chiller makes is what the house takes, so
`Q_house = Q_chiller` and the distribution flow follows from a delta already logged:

```
GPM_distribution  =  GPM_chiller × ΔT_chiller / (IN − OUT)
```

**That measures the Taco's flow with no meter and settles the 13 to 16 GPM question in
[5.8](#58-can-the-primary-supply-both-loops-at-maximum-call) for the price of a register read.**
Item 10 is then unnecessary rather than merely deferred.

**Better still, the tank's volume is known, so no steady state is needed at all.** A Chiltrix 37
gallon buffer on 25 % propylene glycol holds 317 lb of fluid at Cp 0.935, which is 296 BTU/°F, and
about 8 BTU/°F more in the shell. Call it **304 BTU/°F**. The imbalance is then a correction rather
than a disqualification:

```
Q_house = Q_chiller − 304 × d(UBT)/dt          [BTU/hr, with dUBT/dt in °F per hour]
```

The measured 0.03 °F of stratification is what makes that valid. A single lumped temperature
describes a fully mixed tank, and a stratified one would need a layered model
([3.4](#34-the-buffer-tank-is-fully-mixed)).

If you would rather select steady windows than differentiate a noisy series, 304 BTU/°F sets the
bar:

| `UBT` drift | Over | Implied imbalance | As a share of a 33,000 BTU/hr flow |
|---|---|---|---|
| 0.2 °F | 30 min | 122 BTU/hr | 0.4 % |
| 0.5 °F | 15 min | 608 BTU/hr | 1.8 % |
| 1.0 °F | 15 min | 1,217 BTU/hr | 3.7 % |
| 2.0 °F | 15 min | 2,434 BTU/hr | 7.4 % |

**One degree over fifteen minutes costs under 4 %**, comparable to every other error term here, and
it will find far more usable windows than a stricter bar. The chiller also has to be running, which
its power series shows and which holds 46 % of the time, and both ΔTs need calibrated pairs, which
for `IN` and `OUT` means the bench procedure in
[G.1](#g1-matched-pair-calibration-before-install).

Accuracy is better than the alternatives. The result is a ratio of two similar deltas, each near
5 °F, so ±0.2 °F on each gives about ±6 % on the ratio and perhaps ±10 % overall with the chiller's
own flow reading. The pump-curve estimate in
[5.8](#58-can-the-primary-supply-both-loops-at-maximum-call) carries ±20 %, so this is the better
number and it arrives without opening a pipe.

Standby loss is the one bias worth naming. An insulated tank in a warm mechanical room gains a
little heat, so `Q_house` computed this way runs slightly low. On a well-lagged tank it is a
percent or two, which does not change any conclusion here.

The same three quantities also close the tank's energy balance. Chiller output minus house
extraction is the rate the buffer is charging, which is the signal that tells you on a design day
whether the plant is keeping ahead of the load.

**Module.** Follow the house pattern: `pivac.Chiltrix` implementing `status(config, output)`,
`pymodbus` or `minimalmodbus` in the venv, the register map and scaling in `config.yml` rather than
in code, a `pivac-chiltrix.service` unit, and a freshness alert in `sensor-freshness.yaml`. Emit
temperatures in Kelvin at `rounding: 2`, since whole-Kelvin output is what made two years of
1-wire and RedLink history unusable for ΔT work.

#### Mounting the four loop probes

**Mount on copper, not on PEX.** Copper conducts about a thousand times better than PEX, so a
strap-on probe on copper equilibrates with the water quickly and one on PEX reads the outside of a
tube that is thermally distant from the fluid. The header is 1½" copper and the loops transition to
PEX further out, so **put the probes on the copper at the tees**, which is also where they measure
the loop rather than the run.

1. Clean the copper to bright metal at the probe position, on straight pipe at least 5 diameters
   downstream of any fitting, tee or valve.
2. Thermal compound between the probe body and the pipe, then clamp firmly with a worm-drive clamp
   or stainless tie. Contact pressure matters more than the amount of compound.
3. Bury it under **at least 25 mm of insulation, extending at least 100 mm either side of the
   probe**. The 100 mm matters because copper conducts along its length, so insulating only at the
   probe leaves the pipe acting as a fin into the room.
4. **Seal the insulation, including the seam and both ends.** This is a chilled loop below the room
   dew point, so an open seam admits moist air, condenses on the pipe at the probe, and both
   corrodes the joint and biases the reading.
5. Route the leads **downward** away from the probe so condensate cannot wick along the cable into
   the probe body.

Where the pipe already carries insulation, slit it, fit the probe, and reseal rather than leaving a
gap. Skimping here is the main failure mode: an uninsulated probe reads somewhere between the water
and the room, and the error differs between the supply and return pipes, which is the worst case
for a ΔT.

#### Zone call state is already collected

`pivac.RedLink` publishes `environment.inside.thermostat.<ZONE>.statenum` for every zone, and it is
already charted on the Grafana stats panel. No GPIO inputs are needed.

| `statenum` | Meaning |
|---|---|
| −1 | Call for cooling |
| 0 | Off |
| +0.5 | Circulating fan |
| +1 | Call for heating |

**Filter for cooling on `statenum < −0.5`.** An earlier pass through this data tested `> 0.5` and
found zero duty everywhere, which is what a sign error looks like rather than an idle system.

Over 24 hours to 18 August 2026, at an 80 °F mean outdoor and 85 °F peak:

| Zone | Loop | Cooling duty |
|---|---|---|
| Kids room | A | **51.4 %** |
| Master bedroom | A | 45.5 % |
| Great room | BOVA | 44.3 % |
| Downstairs family room | B | 42.8 % |
| Kitchen | BOVA | 41.3 % |

**Two questions close on those numbers.**

The kids-room air handler is not undersized. It runs the highest duty in the house and still holds
74 °F with zero droop, so it has roughly half its running time in reserve at these conditions. A
unit short of sensible capacity would run near-continuously and drift anyway. That leaves the
latent load as the explanation for its humidity, which is what
[3.3](#33-humidity-is-the-marginal-axis) concluded from the laundry and two baths. Extrapolating to
a 95 °F design day puts it near 90 % duty, so it is adequate now and marginal at design.

Loop concurrency is high enough to matter. Loop A calls 74.4 % of the time, Loop B 42.7 %, and
**both loops together 33.9 %**. Loop A runs both its coils 22.4 % of the time, which bounds the
full 15.8 GPM demand case at no more than that. So the mixing question in
[5.8](#58-can-the-primary-supply-both-loops-at-maximum-call) applies during roughly a fifth of the
cooling day, and the master bedroom's 74 % share applies over the same window rather than
continuously.

#### The flow meter is not critical

Defer it. The ΔT ratio between primary and each secondary gives relative flows from thermometers
alone ([C.2](#c2-the-flow-ratio-falls-out-of-temperatures-alone)), and the pump-curve calculation
brackets the absolute value to roughly ±20 %. Every live question here is answered by temperatures
plus zone state.

What a meter adds is absolute BTU/hr and system COP, which is an efficiency and accounting question
the objective ranks second. Buy it if the ΔT-ratio results come out ambiguous, or when you want to
compare a coil against its Unico rating table rather than against last month.

#### Calibration

Calibrate each pair before installing. Bundle both probes of a pair in a stirred bath, log 15
minutes at the production sample rate, and write the mean difference into `offsets:`
([G.1](#g1-matched-pair-calibration-before-install)). Without it a 5 °F loop ΔT carries ±36 % of
error, and the flow-ratio method is a ratio of two such differences. `IN` and `OUT` need the same
treatment and have almost certainly never had it.

> Fix these names once. The Signal K path becomes the InfluxDB measurement name, and four prior
> renames each orphaned their history.

### 4.3 Flow without a flow meter

Chiller output is recoverable from the Emporia CT and an efficiency assumption, and flow follows
from output and ΔT:

```
Q       [BTU/hr]  =  EER × P_electrical [W]
GPM     [gal/min] =  Q / (K × ΔT)                    K = 481 for 25 % propylene glycol
```

Applied across the power bands in [5.1](#51-primary-flow-is-fixed-so-primary-delta-t-reads-house-load), this returns a flow that climbs with load rather than a
constant:

| Chiller power | Primary ΔT | Assumed EER | Q, BTU/hr | Implied primary GPM |
|---|---|---|---|---|
| 1,102 W | 5.00 °F | 18 | 19,800 | 8.2 |
| 1,482 W | 5.04 °F | 16 | 23,700 | 9.8 |
| 2,040 W | 5.13 °F | 15 | 30,600 | 12.4 |
| 2,699 W | 5.18 °F | 14 | 37,800 | 15.2 |
| 3,283 W | 5.87 °F | 13 | 42,700 | 15.1 |

The EER column falls with load because a modulating heat pump is most efficient at part load, and
the published EER 19.6 is an IPLV figure weighted toward exactly that. The spread carries into the
flow estimate, so read this as 8 to 15 GPM rising with output, with roughly ±30 % on any single
row.

Two things follow. Primary flow at high load sits above the roughly 10.6 GPM design figure
published for the neighbouring CX65, which supports the regulated-ΔT reading rather than a
starved primary. And the Taco cannot be doing that work alone. It is rated 18 GPM at zero head
and 17 ft at zero flow, against a chiller evaporator the CX65 datasheet puts at 16 ft of drop at
10 GPM. Something else is moving that water, which is the strongest available evidence that the
CX75 carries its own circulator.

The same arithmetic run against a secondary ΔT gives per-loop flow, which is why the four loop
sensors return more than their cost.

### 4.4 Air-side sensors on one air handler

Two Honeywell 10K NTC duct sensors in the supply and return plenums, plus the commanded ECM
airflow, give measured sensible capacity:

```
Q_sensible [BTU/hr] = 1.08 × CFM_commanded × ΔT_air
```

Against water-side total capacity this splits sensible from latent, which is the axis section
3.3 identified as marginal. On a BOVA zone there is no water side, so these two sensors plus the
existing CT are most of the job.

Build detail is in [Appendix E](#appendix-e--air-handler-node-build-specification), calibration
in [Appendix G](#appendix-g--calibration-and-analysis-methods), and the direct-expansion control
findings in [Appendix D](#appendix-d--the-bova-direct-expansion-zones).

### 4.5 A flow meter on the primary

$200 to $400 for a hydronic paddlewheel or turbine with pulse output. Because `IN` and `OUT`
bracket the tees, one meter on the primary converts every ratio in this document into an absolute
number for every loop at once:

```
Q_all_zones = K × GPM_primary × (IN − OUT)
COP         = Q_all_zones / (W_chiltrix × 3.412)
```

That is whole-house delivered capacity and system efficiency from one purchase. A per-coil meter
answers a smaller question for the same money, which is why the primary comes first.

### 4.6 Reading the master bedroom's fan stage

One bit of state settles the fourth observation, and the metric it produces is better than anything
the thermostats report:

```
Y2 fraction = time(Y2 asserted) / time(the zone is calling for cool)
```

The denominator already exists. `environment.inside.thermostat.MASTER_BR.statenum` reads −1 through
a cooling call, so the zone's cooling runtime is logged back to the date the precision fix landed.
Adding the numerator turns a yes-or-no impression into a continuous measure of how much of that
runtime stage 1 could not cover.

Droop cannot do this job. Honeywell reports whole degrees, every zone reads zero droop today, and a
1 °F signal separates a zone that is losing setpoint from one that is not while ranking nothing in
between ([3.7](#37-two-limits-on-the-data-itself)). Y2 fraction moves continuously between 0 and 1
and responds to every change in section 7, which makes it the scoring metric for the tuning work
rather than one more series.

**Ring out the spare pair first.** The run back from the master's air handler once carried a dry
contact for this signal. If that pair is still good, the measurement is a 24 VAC coil relay across
Y2 and C at the air handler with its contacts on the pair, landing on a free Pi input under
`pivac.GPIO` beside the seven already there. About $15, no firmware, no new service, and it is the
sensing pattern the CDP relays already use. Free inputs are BCM 13, 16 and 24. Avoid BCM 26, a dead
pad.

If the pair is open, the same signal becomes one more input on the air-handler node
([E.9](#e9-sensing-the-y2-call)). That is the stronger reason to build the node at the master
bedroom rather than at the family room: the zone that raises the question is the zone whose coil,
air and water the node would read together.

---

## 5. Hydraulic analysis

### 5.1 Primary flow is fixed, so primary delta-T reads house load

The primary loop runs tank → Taco 0015-MSF3-IFC → header with closely spaced tees → tank. No
evaporator sits in it, so the Taco faces only the header and the tank connections, perhaps 9 ft
at 16 GPM. Against that it delivers **14 to 15 GPM**, and the head barely changes with load, so
primary flow is effectively constant ([5.8](#58-can-the-primary-supply-both-loops-at-maximum-call)).

That makes `IN − OUT` a direct readout of what the house is extracting:

```
Q_house = K × GPM_primary × (IN − OUT) = 481 × ~14.5 × ΔT
```

| House load | Primary ΔT at 14.5 GPM |
|---|---|
| 51,600 BTU/hr, the CX75's full rating | 7.4 °F |
| 40,000 | 5.7 °F |
| 30,000, about 2.5 tons | 4.3 °F |
| 20,000 | 2.9 °F |

The measured 5.3 °F mean therefore corresponds to roughly **3.1 tons of extraction** on an 80 °F
evening, against a plant rated at 4.3. **The 8 to 12 °F band arrives at design load and not
before**, which is the whole answer to the question that opened this document. Nothing is wrong,
and nothing on the water side needs adjusting to produce it.

> **Two pumps, two circuits, one tank between them.** The CX75's internal circulator modulates,
> confirmed at the controller, but it drives the chiller-to-tank circuit. The Taco drives the
> distribution circuit at a fixed speed. The tank separates them, so a modulating pump on one side
> does not make `IN − OUT` a regulated quantity on the other.
>
> Binning ΔT against chiller power does not test that, and an earlier reading of this data
> over-claimed. Primary ΔT reflects what the coils extract; chiller power reflects what the plant
> puts into the tank. **The four-pipe buffer sits between them and breaks the instantaneous link**,
> which is its purpose, so the two series are not expected to track at two-minute resolution. Back
> -calculating an EER from them gives 17.5 at the mean and an impossible 28.4 in the lowest power
> band, which is the tank discharging while the coils keep drawing. Treat chiller power as a
> plant-side signal and `IN − OUT` as a load-side one, and compare them only over hours.

### 5.2 What that means for the 8 to 12 degree target

The band is a design-load figure, and this system reaches it at design load. Primary flow is fixed,
so ΔT rises and falls with what the coils extract: 7.4 °F at the CX75's full rating and 4.3 °F at
2.5 tons ([5.1](#51-primary-flow-is-fixed-so-primary-delta-t-reads-house-load)). The 5.3 °F measured
on an 80 °F evening is the correct number for that evening. Balancing valves, pump taps and coil
cleaning all move flow between zones or change it a little; none of them changes what the house is
extracting.

**Reaching the band on a mild day means slowing the primary, and that is the wrong move here for two
reasons.** Lower water flow warms the average coil surface, so more of the coil rises toward the
entering-air dewpoint and stops condensing
([B.6](#b6-water-flow-and-dehumidification-move-together)); humidity is already the marginal axis in
the two Loop A bedrooms ([3.3](#33-humidity-is-the-marginal-axis)). And the primary has 0.6 GPM of
margin over the combined secondary call, so slowing it puts the secondaries above it and mixes the
tees backwards ([5.8](#58-can-the-primary-supply-both-loops-at-maximum-call)).

The high flow the system runs today works in its favour. It holds the coils close to entering water
temperature, which is what keeps their surfaces below the air dewpoint. What it costs is pump
energy, which the objective ranks last.

One case would justify slowing it. If a design-day test ever shows the plant saturating while the
loops still run a 5 °F ΔT, the loops are moving more water than the chiller can charge, and the
primary can come down to recover pump energy at no comfort cost. Until that test happens, leave it
alone.

### 5.3 Elevation adds no pump head in a closed loop

The pump does not lift the water. In a closed, full loop every foot of rise on the supply side is
matched by a foot of fall on the return, and the two cancel exactly. The circulator overcomes
friction alone, so the master bedroom's 10 ft rise and the attic coil's position cost nothing in
pump head.

This holds regardless of how tall the building is. A twenty-storey closed system uses a
circulator sized for its friction losses, and only an open system, one that discharges to
atmosphere, pays for static lift.

The shared-circulator concern is real and the elevation concern is not. Section 5.4 quantifies
the part that matters.

### 5.4 What elevation does affect

Height changes the static pressure at the high point, and it changes where air collects.

Fill pressure has to keep the highest point comfortably above atmospheric. The working rule is
`P_fill ≥ height ÷ 2.31 + 5 psi`. At 25 ft of rise that is about 16 psi, and the loop runs 21 psi,
so section 3.5 already confirmed this passes with roughly 10 psi at the attic coil.

Air collects at high points, and the attic coil is the system high point. An automatic air vent
there is not optional. A coil that has air-bound presents as one zone underperforming while every
other zone is fine, which is a distinct signature from anything discussed elsewhere in this
document. All zones currently hold setpoint, so nothing is air-bound today.

Pump and expansion-tank positions matter for the same reason. The expansion tank connection is the
point of no pressure change, and a circulator pumping toward it subtracts from system pressure
rather than adding to it. On a tall system that can pull the top below atmospheric even when the
gauge reads healthy. Worth confirming once, visually, that both secondary circulators pump away
from the expansion tank connection.

### 5.5 Friction head on the index circuits

Design flow comes from the Unico coil tables. At 45 °F entering water the M2430 delivers 26.9 MBH
at 6 GPM and 600 CFM, and the M1218 delivers 17.5 MBH at 6 GPM and 400 CFM, so 6 GPM and 4 GPM are
the working design points.

Coil pressure drop is published rather than assumed. From Unico bulletin 20-020.3.020 at 45 °F
entering water, pure water, in feet of water gauge:

| Coil | 2 GPM | 4 GPM | 6 GPM | 8 GPM |
|---|---|---|---|---|
| M1218CL1-C | 0.9 | 3.4 | 7.4 | — |
| M2430CL1-C | 0.9 | 3.4 | 7.4 | 12.6 |
| M3036CL1-C | 0.6 | 1.8 | 4.2 | 7.2 |

Two things follow. **The M1218 and M2430 coils have identical pressure drops**, so the smaller
handler is no easier to feed at a given flow. And a coil at design flow is a large fraction of the
whole circuit, since 7.4 ft is more than a quarter of Loop A's index-circuit head.

> Water temperature and glycol both move these numbers. Across 40 to 55 °F entering water the
> published drop moves about 4 %, from 7.5 to 7.2 ft on the M2430 at 6 GPM, so temperature is a
> minor term. **Glycol is the larger correction**, and Unico publishes a multiplier table for it in
> the same bulletin. The figures here use 1.25 for 25 % propylene glycol at 45 °F and 1.10 at
> heating temperatures, which are standard engineering values. Substitute Unico's own multiplier
> when you read the bulletin, and note that the planned 25 % to 30 % top-up moves it again.

Head is friction alone, since a closed loop cancels static lift
([5.3](#53-elevation-adds-no-pump-head-in-a-closed-loop)). Each element is computed at the flow it
carries, with 40 % added to pipe for fittings. Pipe size is the remaining uncertainty, so results
are bracketed between all 1¼" and all 1".

| Loop and season | Design flow | Index circuit |
|---|---|---|
| Loop A, both coils calling | 10.0 GPM: kids 4.0, master 6.0 | master bedroom, ~105 ft one way |
| Loop B, summer | 6.0 GPM: family room alone | family room, ~15 ft one way |
| Loop B, winter | 16.5 GPM: family 4.1, kitchen 6.2, great room 6.2 | great room, ~60 ft one way |

> Velocity flags Loop B rather than Loop A. In 1¼" PEX, 10 GPM runs 3.6 ft/s and 16.5 GPM runs
> 5.9 ft/s, against the 4 ft/s limit that governs erosion and noise. **Loop B in winter is above
> that limit at design flow**, and it would be far above it in 1" pipe.

The kitchen and great room carry hot-water hydronic modules rather than CL chilled-water coils,
and their pressure drops are not in this bulletin. The winter figures below use the M3036
chilled-water coil as a stand-in, which is the largest single assumption left in the calculation.

### 5.6 What the calculation says about each coil

The Grundfos UPS26-99FC, the three-speed pump these loops use, carries these curve endpoints on
the SuperBrute data sheet:

| Speed | Shutoff head | Maximum flow | Input power |
|---|---|---|---|
| 3, high | ~29 ft | ~33 GPM | 197 W |
| 2, medium | ~26.5 ft | ~29 GPM | 179 W |
| 1, low | ~21.5 ft | ~24 GPM | 150 W |

The three curves sit closer together than a three-speed circulator usually does, which the 150 to
197 W spread confirms. Low is not a weak setting on this pump.

Intersecting each curve with the system curve gives total loop flow, and splitting at equal branch
head gives each coil. With 1¼" mains and 1" branch runs:

**Loop A, cooling.** Design 10.0 GPM.

| Speed | Loop total | Kids room, design 4.0 | Master bedroom, design 6.0 |
|---|---|---|---|
| 1, low | 8.2 GPM, 82 % | 4.3 GPM, 108 % | 3.9 GPM, 66 % |
| 2, medium | 9.3 GPM, 93 % | 4.9 GPM, 122 % | 4.5 GPM, 74 % |
| 3, high | 9.9 GPM, 99 % | 5.2 GPM, 130 % | 4.7 GPM, 79 % |

**Loop B, summer, the family room alone.** Design 6.0 GPM. LOW gives 6.5 GPM, 109 %; MEDIUM
7.4 GPM, 123 %; HIGH 7.8 GPM, 130 %.

**Loop B, winter, all three coils.** Design 16.5 GPM.

| Speed | Loop total | Family room, design 4.1 | Kitchen, design 6.2 | Great room, design 6.2 |
|---|---|---|---|---|
| 1, low | 13.4 GPM, 81 % | 4.8 GPM, 117 % | 4.4 GPM, 71 % | 4.1 GPM, 67 % |
| 2, medium | 15.3 GPM, 93 % | 5.5 GPM, 134 % | 5.1 GPM, 82 % | 4.8 GPM, 77 % |
| 3, high | 16.5 GPM, 100 % | 5.9 GPM, 145 % | 5.5 GPM, 88 % | 5.1 GPM, 83 % |

**Both loops lose their far coil, and the pattern is the same.** The first coil on each loop takes
110 to 145 % of its design flow while the last takes 66 to 83 %. On Loop A that is the master
bedroom in the attic; on Loop B in winter it is the great room, the largest coil in the house,
sitting behind two main segments and a 10 ft rise.

Pipe size changes the magnitude and not the shape. If a substantial length of main is 1" rather
than 1¼", Loop A falls to 61 to 72 % of design flow overall with the master bedroom at 46 to 55 %,
and Loop B in winter falls to 66 to 80 % with the great room at 47 to 57 %. **The main runs being
1¼" is what keeps this system in workable territory**, so confirming that matters more than any
other measurement in this section.

### 5.7 Choosing the pump speed, and whether balancing helps

The method needs five steps and no new hardware.

1. Take design flow per coil from the Unico coil table at your entering water temperature.
2. Sum along the index circuit, the longest path from the tees to a coil and back.
3. Build the head at design flow: main friction leg by leg, fittings, branch run, coil, zone valve.
4. Draw the system curve through that point. Friction scales as `H = H_design × (Q/Q_design)^1.85`.
5. Intersect it with each pump-speed curve. Choose the lowest speed that meets design flow.

**The settings that fall out are MEDIUM for Loop A, which is where it now sits, LOW for Loop B in
summer, and HIGH for Loop B in winter.** Loop A on MEDIUM reaches 93 % of design for 29 W more than LOW, and HIGH buys 6 % more
for another 18 W while pushing combined secondary flow further past the primary. Loop B already
over-pumps its single summer coil on LOW. Loop B in winter wants HIGH rather than merely "higher",
since LOW leaves the great room at 67 % of design.

Balancing answers a different question. Throttling the near branch redistributes, at a cost, with
Loop A on MEDIUM:

| Kids branch | Loop total | Kids room | Master bedroom |
|---|---|---|---|
| As installed | 9.3 GPM | 4.9 GPM, 122 % | 4.5 GPM, 74 % |
| Throttled to design flow | 8.9 GPM | 4.1 GPM, 102 % | 4.8 GPM, 80 % |
| Throttled to equal share | 8.5 GPM | 3.4 GPM, 84 % | 5.1 GPM, 85 % |
| Shut | 6.4 GPM | 0 | 6.4 GPM, 106 % |

**The exchange rate is about half.** Every gallon per minute taken off the kids room delivers about
0.46 GPM to the master bedroom, because throttling steepens the system curve and the pump falls
back to a lower total flow. Balancing to equal share brings both coils to about 85 % of design
against 122 % and 74 % as installed, and that is the best a valve can do without starving the kids
room outright.

> Balancing serves fair share, and it will not help humidity. It moves flow between two zones
> rather than adding any, and the kids room is the more humid of the two at 53.7 % against the
> master's 50.9 %. More total flow helps both, which is what the tap change does, and colder water
> helps both ([7.1](#71-costs-nothing)).

> ⚠️ One ceiling bounds any further increase, and Loop A on MEDIUM now sits against it. Secondary
> flow must stay under primary flow or the tees mix backwards
> ([Appendix C](#appendix-c--primarysecondary-hydraulics)). Loop A on MEDIUM plus Loop B on LOW
> draws **15.8 GPM**, against the 14.5 to 16.4 GPM the Taco delivers on HIGH
> ([5.8](#58-can-the-primary-supply-both-loops-at-maximum-call)). Loop A on HIGH would add 0.6 GPM
> and cross it. **The tap change is made and now wants checking**, which is why the four loop
> sensors in [4.2](#42-the-sensor-package) matter more than any further speed change.

> What is measured and what is assumed. Coil pressure drops and coil capacities are Unico's
> published figures. The pump curve is read off the printed SuperBrute chart and interpolated with
> a fitted curve shape. Pipe lengths are rough, the pipe-size split is unknown and bracketed, the
> zone-valve drop is assumed at 3 ft, and the hot-water hydronic modules use the M3036
> chilled-water coil as a stand-in. Confirm against the loop sensors rather than against the
> arithmetic.

### 5.8 Can the primary supply both loops at maximum call?

The mechanical room is compact, which decides this. The header is 6 ft of 1½" copper, the tank and
boiler sit beside it with at most 10 ft of pipe each, the boiler run is 7 ft total, and the chiller
run is 6 ft each way. Friction across any of these circuits is under a foot at working flow, so
head comes from fittings, tank nozzles, check valves and heat exchangers rather than from pipe.

**Cooling.** The primary is roughly 20 ft of 1½" copper with no heat exchanger in it, so its head
lands between 2 and 6 ft at 16 GPM. Against that the Taco's speed switch is worth about 3 GPM:

| Circuit head at 16 GPM | Speed 1 | Speed 2 | Speed 3 |
|---|---|---|---|
| 2.2 ft, 2× fitting allowance | 13.3 GPM | 15.1 GPM | 16.4 GPM |
| 3.9 ft, 3× fittings | 12.6 GPM | 14.3 GPM | 15.5 GPM |
| 5.9 ft, deliberately pessimistic | 11.8 GPM | 13.4 GPM | 14.5 GPM |

Combined secondary call is 15.8 GPM. **The Taco is confirmed on HIGH**, which puts the primary at
14.5 to 16.4 GPM depending on the fitting allowance, so it covers the secondaries in the two
likelier cases and falls a little short only in the pessimistic one. **Reverse mixing in cooling is
therefore unlikely rather than merely unproven**, and the loop probes remain the way to confirm
it.

The thermal evidence brackets the same range from the other side. A primary ΔT of 5.34 °F at
1,903 W implies an EER of 17.5 at 13 GPM, 19.6 at 14.5 and 21.3 at 15.8. The CX75's published 19.6
is an IPLV figure, and instantaneous part-load EER at a 47.8 °F leaving-water temperature and 80 °F
ambient can exceed it, so none of these is excluded. **Primary flow is 13 to 16 GPM, and where it
sits inside that band is set by the speed switch.**

**Heating.** The boiler circuit is 13 ft of pipe including the header, so the Ti-200's exchanger is
the whole question:

| Ti-200 exchanger drop | Circuit head at 26 GPM | UP26-99F on HIGH delivers |
|---|---|---|
| 3 ft at 20 GPM | 7.5 ft | 27.0 GPM |
| 5 ft at 20 GPM | 10.8 ft | 25.2 GPM |
| 8 ft at 20 GPM | 15.6 ft | 23.1 GPM |
| 12 ft at 20 GPM | 22.1 ft | 21.0 GPM |

Against a 25.8 GPM winter call, the answer swings from comfortable to 5 GPM short across a range
of exchanger drops that a datasheet would settle in a minute
([9](#9-open-questions)).

**The chiller-to-tank circuit is not in question.** Twelve feet of pipe contributes about half a
foot at 11 GPM, negligible beside an evaporator near 19 ft, so the CX75's internal pump sees
essentially only the load it was sized for.

> **The 4 ft of rise from the tank costs nothing.** A closed loop cancels static lift
> ([5.3](#53-elevation-adds-no-pump-head-in-a-closed-loop)), the same point that disposed of the
> attic coil.

**No pump needs buying.** A 1/20 HP circulator on a 2 to 6 ft circuit is a sensible pairing rather
than an undersized one; an earlier reading in this document put the chiller evaporator in this loop
and concluded otherwise, when the tank decouples that circuit entirely. What the primary needs is a
switch checked and two probes fitted.

### 5.9 What is still unresolved

Regulated primary flow explains the primary ΔT and says nothing about either secondary loop. Three
possibilities remain for the loops themselves, and one measurement separates them.

| Condition | Loop supply against `IN` | Loop ΔT against primary ΔT | Consequence |
|---|---|---|---|
| Decoupled and healthy | equal | at or above | None. The coils see tank temperature |
| Secondary overpumped | equal | below | Pump energy wasted. Coil capacity and dehumidification are unharmed |
| Reverse mixing at the tees | warmer in cooling | below | Real capacity loss, presenting as an undersized chiller |

Loop supply temperature against `IN` is the discriminator, and it needs two of the four sensors in
[4.2](#42-the-sensor-package).

The evidence leans toward the first row, by a narrower margin than it did before Loop A went to
MEDIUM. The Taco on HIGH delivers 14.5 to 16.4 GPM and the two secondaries now draw 15.8 combined
([5.8](#58-can-the-primary-supply-both-loops-at-maximum-call)), so the ordering holds in the
optimistic fitting case and comes within a few per cent of reversing in the others. It is
comfortable rather than proven, and it inverts on a design day when both Loop A zone valves and
Loop B open together.

### 5.10 Why the master bedroom calls its high fan stage

A two-stage thermostat calls stage 2 when stage 1 fails to hold setpoint, so the observation is a
statement about that coil's capacity. Four things could produce it, and they separate cleanly.

**The thermostat may be manufacturing it.** ISU 3020, Finish With High Cool Stage, holds the high
stage on until the setpoint is reached once anything has upstaged, and ISU 3030 sets how far above
setpoint stage 2 engages at all ([Appendix J](#appendix-j--the-master-bedroom-thermostat)). Either
produces long stage-2 runtime on a zone with capacity in hand. Read both before fitting a sensor,
because a finish-on-high rule makes Y2 fraction a record of the setting.

**The coil is the least-fed on the system.** It sits at the far end of Loop A's 105 ft index circuit
and takes 74 % of its design flow on MEDIUM, against the kids room's 122 %
([5.6](#56-what-the-calculation-says-about-each-coil)). Capacity saturates with water flow rather
than tracking it, so 74 % of flow costs well under 26 % of capacity
([B.5](#b5-coil-capacity-against-water-flow-saturates)). On its own that is a few per cent, and a few
per cent is the distance between holding on stage 1 and upstaging on the hottest afternoon.

**The tees may be adding to it.** The primary clears the combined secondary call by 0.6 GPM in the
optimistic fitting case and falls short in the pessimistic one
([5.8](#58-can-the-primary-supply-both-loops-at-maximum-call)). Where it falls short the coils
receive water warmer than the tank, and coil capacity scales with the gap between entering air and
entering water, so 2 °F of warm supply against a 30 °F gap costs about 7 %. The coil with the least
flow margin feels that first, and it is this one.

**Some of it is load.** The coil is in the attic and the zone is on the top storey, so its sensible
load peaks with the roof. Load and shortfall separate on the clock. A zone that upstages through the
afternoon and not at four in the morning is loaded; one that upstages at both is short of capacity.

The two hydronic causes share a test. Both act through the water the coil receives, so lowering the
chiller's return-water target ([7.1](#71-costs-nothing)) should show as Y2 fraction
falling at a given outdoor temperature. No flow is left to add: Loop A is on MEDIUM and HIGH would
cross the primary ([5.7](#57-choosing-the-pump-speed-and-whether-balancing-helps)), which leaves
colder water and branch balancing as the two routes to more capacity at this coil. If Y2 fraction
does not move, the cause is the thermostat or the load, and the air-side sensors separate those two
([4.4](#44-air-side-sensors-on-one-air-handler)).

> **Stage 2 works against the humidity finding.** More airflow over the same coil gives a warmer
> average surface and a higher sensible heat ratio, so the zone dries the air less on stage 2 than
> on stage 1 ([B.4](#b4-the-two-deltas-move-in-opposite-directions)). The master bedroom peaks at
> 60 % RH, the highest in the house ([3.3](#33-humidity-is-the-marginal-axis)). If that thermostat
> is set to dehumidify with the low-speed fan, the effect is explicit: Honeywell states the
> thermostat will not lower the fan speed while the second stage of cooling is on, so every minute
> on Y2 is a minute the zone cannot dehumidify by that route. The high fan stage and the humidity
> reading may be one problem seen twice.

### 5.11 Water temperature is the larger term, and distribution is the smaller one

Section 5.6 puts the master bedroom's coil at 74 % of design water flow, and 5.8 puts the mixing loss
at about 7 % when both loops call. Both are real and both are small. The temperature difference
measured in [3.8](#38-the-previous-plant-is-a-controlled-comparison) is neither.

Sensible capacity at a chilled-water coil scales with the gap between entering air and entering
water. Taking a 76 °F room and the 80 to 85 °F outdoor bin:

| Era | Entering water | Air-to-water gap | Capacity against the old plant |
|---|---|---|---|
| Old UniChiller | 41.4 °F | 34.6 °F | 100 % |
| Chiltrix today | 47.4 °F | 28.6 °F | **83 %** |

**A 17 % capacity loss at the same airflow is several times every distribution effect in this
document put together**, and it applies to every coil in the house rather than to one branch. It is
the direct reason a zone that held on its low fan stage now reaches for its high one, and the
measured duty increase in the same bin, 46 % to 68 %, is the same story counted a second way.

Latent capacity moves further, because condensation is a threshold rather than a slope. Air gives up
moisture only where the coil surface sits below its dew point:

| Era, 75–80 °F outdoor | Room RH | Room dew point | `IN` | Primary return `OUT` |
|---|---|---|---|---|
| Old | 44.9 % | 53.1 °F | 41.3 °F | 47.8 °F |
| New | 53.3 % | 57.8 °F | 48.2 °F | 53.4 °F |

The old coil sat below the room's dew point along its whole length. The new one starts below it and
finishes at it, so the last stretch of coil cools air without drying it. That is the mechanism behind
[3.3](#33-humidity-is-the-marginal-axis). It is self-limiting rather than self-reinforcing: the room
settles wherever humidity has risen enough that a warmer coil can still carry the latent load, which
is a stable operating point and a worse one.

**The buffer tank is not the obstacle.** A fully mixed tank holds one temperature
([3.4](#34-the-buffer-tank-is-fully-mixed)), and the chiller's target sets that temperature, not the
tank. Hydraulic separation governs flow, not temperature.

Both plants cycle, and the bands are what separate them. The UniChillers ran 38 to 48 °F on a 10 °F
differential; the Chiltrix runs 50 to 53.4 °F on a 2 °C one. The old band spent much of every cycle
far below the room dew point, and its warm end only reached where the new band begins. The new band
never gets there at all, which is why the narrower, better-regulated plant is the one that dries the
house less. **Narrow is the right shape and the level is wrong**, and the level is a number in a
menu.

**So the answer to whether the old operating point is reachable is yes, by setting it.** The route
and its prerequisite are in [7.1](#71-costs-nothing), and the parameters are in
[Appendix K](#appendix-k--the-previous-plant-and-the-chiltrix-controls).

## 6. Verdict

### 6.1 What optimal means here

Six criteria, in the order the objective ranks them.

1. Every zone holds setpoint on a design day, and does it on stage 1.
2. Humidity stays near 50 % RH in occupied zones.
3. Coil entering water temperature matches the tank, so no capacity is lost at the tees.
4. Each zone gets its share of flow when all zones on its loop call together.
5. The plant retains reserve capacity at design conditions.
6. Pump and plant energy are no higher than the above requires.

### 6.2 Scorecard

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Zones hold setpoint, on stage 1 | **Pass on temperature, unmeasured on stage** | Zero droop on all five zones over 8 h; the master bedroom's high fan stage is unlogged ([4.6](#46-reading-the-master-bedrooms-fan-stage)) |
| 2 | Humidity near 50 % | **Fails against the plant it replaced, partly from restricted flow** | 5 to 10 points wetter than the UniChillers at every matched outdoor band ([3.8](#38-the-previous-plant-is-a-controlled-comparison)); 60 % peak in the master bedroom. A clogged strainer held the chiller above its own target through that period ([6.4](#64-a-clogged-strainer-sat-underneath-the-comparison)) |
| 3 | No loss at the tees | **Likely fine** | Needs loop supply against `IN` ([4.2](#42-the-sensor-package)) |
| 4 | Fair share between zones | **Suspect on Loop A** | The far coil takes 74 % of design flow against the near coil's 122 %, and it is the zone calling its high fan stage ([5.6](#56-what-the-calculation-says-about-each-coil), [5.10](#510-why-the-master-bedroom-calls-its-high-fan-stage)) |
| 5 | Reserve at design | **Untested, on a smaller plant than before** | 4.3 tons nominal against the 5-ton UniChiller it replaced, and the Chiltrix era has not exceeded 90.1 °F outdoor |
| 6 | Energy proportionate | **Suspect** | Primary flow reaches ~15 GPM against a ~10.6 GPM design figure ([4.3](#43-flow-without-a-flow-meter)) |

### 6.3 Conclusion

**The system holds setpoint, and it runs measurably behind the plant it replaced.** Every zone was at
setpoint through eight hours of an 80 °F evening with the chiller idle more than half the time, so
nothing here needs fixing to restore comfort. Measured against the UniChillers at matched outdoor
conditions, though, the master bedroom runs about half again as long, sits 5 to 10 points wetter, and
reaches for a fan stage it used to leave alone
([3.8](#38-the-previous-plant-is-a-controlled-comparison)).

**The cause is the chilled-water target, and it is a setting rather than a limitation.** The loop
runs 6 to 8 °F warmer than it did, which costs about 17 % of sensible capacity at every coil and
lifts much of the coil surface to the room's dew point
([5.11](#511-water-temperature-is-the-larger-term-and-distribution-is-the-smaller-one)). That is
several times every distribution effect in this document put together. The target sits at 50 °F,
P109 is now set to `1` so it can go as low as 41, and the glycol top-up is the prerequisite for using
that range. How far down to go is bounded by capacity rather than by the controller
([7.1](#71-costs-nothing)).

The low ΔT is what a fixed-flow primary reads at part load, and it is better left alone. At roughly
14.5 GPM the measured 5.3 °F is about 3.1 tons of extraction against a plant rated at 4.3, so the
design band arrives at design load
([5.1](#51-primary-flow-is-fixed-so-primary-delta-t-reads-house-load)). Reaching it on a mild day
means slowing the primary, which costs capacity and dehumidification and would put the secondaries
above it ([5.2](#52-what-that-means-for-the-8-to-12-degree-target)). The 5 °F the system runs today
is part of why the coils keep their surfaces below the air dewpoint. It costs pump energy, which the
objective ranks last.

**Humidity also falls along the loop split, and that is the second-order term.** The one
chilled-water coil with a circulator to itself over a 15 ft run reads 45.9 % RH; the two sharing a
circulator across a 105 ft index circuit read 50.9 % and 53.7 %, peaking at 60 % and 59 %. Loop A has
gone to MEDIUM, which is as far as it can go without crossing the primary
([5.7](#57-choosing-the-pump-speed-and-whether-balancing-helps)), so what remains on the distribution
side is branch balancing. Fix the water temperature first: it is larger, it is free once the glycol
is up, and it lands on every zone.

**The master bedroom's high fan stage is the sharpest unmeasured signal in the house.** It sits at
the far end of Loop A on 74 % of its design flow, it reads the highest humidity of the five zones,
and stage 2 makes that humidity worse for as long as it runs
([5.10](#510-why-the-master-bedroom-calls-its-high-fan-stage)). One 24 VAC relay turns it into a
continuous capacity measure where droop gives a flat zero
([4.6](#46-reading-the-master-bedrooms-fan-stage)).

Three things remain unverified. Distribution between the two Loop A coils is unbalanced by
construction and unmeasured, which matters most on the design day nobody has yet observed. Whether
the tees mix backwards is unknown, which section 7 resolves for about $20. And whether that
thermostat's own staging settings produce the high fan stage is a menu read away
([Appendix J](#appendix-j--the-master-bedroom-thermostat)).

---

### 6.4 A clogged strainer sat underneath the comparison

**The Y-strainer in the shared four-pipe loop was found heavily clogged on 22 August 2026**, with
calcium-looking scale migrating from the boiler side, after repeated **`P5` "indoor unit water flow
error"** alarms. `P65` sets that low-flow trip at 20 L/min on a CX65/CX75 and `C13` is the live
readout; after cleaning, `C13` reads over 54 L/min. The restriction developed over weeks, which
places it underneath the data this document compares.

**The failure is visible to the hour.** Between 10:00 and 14:00 EDT on 22 August the chiller ran
5, 10, 0 and 6 minutes in those four hours while `IN` climbed 58.6 → 65.3 → 73.3 → 76.0 °F and the
tank tracked it. Recovery begins at 14:00 and by 15:00 the unit is drawing 2650 W for the full hour
with `IN` back to 48.1 °F.

**Before cleaning, the chiller ran above its own return-water target every afternoon.** Over matched
09:00–17:45 windows on 12–20 August, all at the 50 °F target, return water held 52.4–54.4 °F, mean
53.3. A chiller meeting its load sits at target. Sitting 2.4 to 4.4 °F above it through every
afternoon is what restricted evaporator flow produces.

**After cleaning it holds closer, on less power.** On 23 August, at a 75.4 °F outdoor average and an
81.0 °F peak, return water averaged 51.9 °F and running power 1423 W. That is the lowest running
power and the lowest return water of any day in the window, on an above-median outdoor day, against
a pre-clean running-power mean of 1593 W. Runtime does not explain it: 19 August ran the longest of
any day at 513 minutes and still returned warmer water, 53.9 °F, than 23 August did at 446 minutes.

**So part of the 6 to 8 °F gap in [3.8](#38-the-previous-plant-is-a-controlled-comparison) is the
chiller failing to hold the setpoint it already had.** That is a different finding from the setpoint
being too warm, and it points at a different remedy. Restricted flow costs capacity and
dehumidification at every coil, through the tank, and it would present exactly as this document
recorded: a loop running warmer than the plant it replaced, at every outdoor band.

**The E14 lockout reads differently too.** Low flow widens the evaporator ΔT, which drives leaving
water down onto the `P59` trip, so the restriction likely contributed to the 21 August lockout at a
46 °F target rather than the target alone accounting for it. A retry at a colder target against
clean flow is a different experiment from the one that failed.

**Zone comfort shows no change yet.** All three chiller-served zones sat on setpoint on 23 August,
droop −0.01 °F, as they also did on 19 and 20 August before the cleaning; there was no droop to
remove. On humidity, with the DX kitchen and great room as a control group the chiller has no part
in, the chiller zones ran 0.5 points above the DX zones on 23 August, inside the −1.5 to +2.4 spread
of the pre-clean days. Absolute humidity was low that day and the DX zones were low with it, so that
reads as drier outdoor air.

**Three limits on all of the above.** One post-clean day is thin. The tank probes were physically
replaced on 22 August, so `UBT` and `LBT` cannot be compared across that date. And zone temperatures
before 18 August are truncated to whole Kelvin and read up to 1.8 °F cold, so any zone comparison
spanning that date is invalid, which is why only days from the 18th on appear here.

**Add the strainer to the maintenance list.** The scale arrives from the boiler side of a shared
loop, so it will foul again. Reading `C13` during the one to two minute pump-only window at the
start of a call costs nothing and catches the next restriction long before `P5` does.

## 7. Remedy ladder, cheapest first

### 7.1 Costs nothing

**Read the master bedroom's thermostat settings before touching that zone.** Finish With High Cool
Stage and the cool-stage differential decide whether its high fan stage is a capacity signal at all,
and the dehumidification block decides whether the 55 % setpoint every zone carries does anything
([Appendix J](#appendix-j--the-master-bedroom-thermostat)). Free, and it is the difference between
measuring a coil and measuring a menu.

**Set the master bedroom's fan from circulate to auto.** That zone runs fan circulate, so its blower
moves air across a wet coil between calls and re-evaporates condensate back into the room. The kids
room runs auto and reads just as humid, so this is not the whole of the humidity finding. It is free
and reversible, and RH is already logged.

**Check the result of the Loop A tap change rather than assuming it worked.** Loop A is on MEDIUM,
which the calculation puts at 93 % of design flow against 82 % on LOW, and the master bedroom at
74 % of its own against 66 % ([5.6](#56-what-the-calculation-says-about-each-coil)). More secondary
flow than the primary supplies would feed the coils water warmer than the tank and cancel part of
the gain ([5.7](#57-choosing-the-pump-speed-and-whether-balancing-helps)). The four loop sensors in
[4.2](#42-the-sensor-package) show it directly as Loop A's supply drifting above `IN`.

**Lower the commanded CFM on the kids-room air handler.** That zone carries the laundry room and
two full baths in a small space, so it runs a large latent load on a small sensible one
([3.3](#33-humidity-is-the-marginal-axis)). Less airflow gives a colder coil and a lower sensible
heat ratio, trading capacity this zone has to spare for the moisture removal it needs. The Unico
Smart Controller sets it in software, so the change is free and reversible, and it is the opposite
of the direction the great room was tuned
([Appendix D](#appendix-d--the-bova-direct-expansion-zones)).

**Check the bath and laundry exhaust in that zone.** Fans that run long enough and duct to outside
remove moisture at its source, before it reaches a coil at all. A dryer venting into the space,
or a ventless one, would put the whole load on the air handler. This sits outside the hydronic
system and is likely the highest-value fix available for that room.

> **⚠️ Gated on a clean-flow baseline.** The strainer was clogged through the period this remedy was
> sized against ([6.4](#64-a-clogged-strainer-sat-underneath-the-comparison)), and clean flow has
> already recovered part of the gap on its own. **Collect two weeks at the 50 °F target with the
> strainer clean before moving it**, and re-measure the gap against
> [3.8](#38-the-previous-plant-is-a-controlled-comparison) on that baseline. The target may need
> less movement than the 6 to 8 °F figure implies, or none.

**Walk the Chiltrix return-water target down.** This is the largest single remedy in the document,
and the measured gap to the plant it replaced is 6 to 8 °F
([3.8](#38-the-previous-plant-is-a-controlled-comparison)). **P109 is set to `1`**, so the range now
opens to 41 °F against the 50 °F the target sits at today.

**Read `C04` and `C05` before moving it.** The target governs return water and the unit makes water
about 9 °F colder than that, so every degree off the target is a degree off the leaving temperature
too: at today's 50 °F the leaving water is near 41 °F, and a 42 °F target would put it near 33 °F.
**Check that figure rather than assume it.** Chiltrix's 9 °F is the design ΔT from its own sizing
formula, `BTU = WF × ΔT × GPM`, at design flow and full load, and this plant runs at part load most
of the time, where the real ΔT is smaller. `C04` and `C05` on the controller give the actual inlet
and outlet and cost nothing to read. Read `IN` and `OUT` on the Pi at the same moment while you are
there, and the same reading also calibrates the two sensor sets against each other.

**Step to 46 °F first, and stop when the coil clears the dew point rather than aiming at a number.**
This is gated on P59 and the glycol, per the warning below; 46 °F with P59 at its default locks the
unit out.
The threshold that matters is a coil surface below the room's dew point along its whole length, not
the coldest water the machine will make
([5.11](#511-water-temperature-is-the-larger-term-and-distribution-is-the-smaller-one)). At 46 °F
loop water the coil runs roughly 48 to 53 °F against a room dew point near 56 °F, so it condenses
everywhere; today's 48 °F leaves the outlet end sitting at the dew point, which is why it does not.
**Most of the gain therefore arrives in the first two to four degrees**, and the last few toward 41
buy the least latent capacity for the most lost sensible capacity. Hold each step a few comparable
days and score it on Y2 fraction and master-bedroom RH. Because the tank settles at the target, `IN`
should follow each step within a degree, which is the check that the change took.

**One prerequisite gates it: the glycol.** The manual attaches a condition to P109 = 1, glycol not
frozen at −10 °C. **25 % propylene glycol freezes at about −10 °C and 30 % at about −13 °C**, so the
loop currently sits on the limit rather than inside it. The 25 % to 30 % top-up already planned for
heating season therefore moves onto the critical path for this change instead of waiting for autumn.
Set `fluid_k` to 476 on the day and annotate Grafana.

**Two costs come with it, and one of them binds.** Efficiency falls as the target falls, which the
objective ranks second and which the Emporia CT already measures. **Capacity falls too, and that is
the constraint that decides how far this can go**: roughly 2 to 3 % per °F of leaving-water
reduction, so a 42 °F target costs on the order of 20 % against today. The CX75 is 4.3 tons nominal
against the single 5-ton UniChiller it replaced, and the measured house peak was about 3.1 tons on an
80 °F evening, against a design day nobody has yet observed. Watch for `IN` rising above its target on
hot afternoons, which is the plant running out, and stop stepping down when that appears.

> **⚠️ The antifreeze protection binds long before capacity does. Proven on 21 August 2026.** A 46 °F
> target set the night before produced **E14, "System anti freeze level one twice"**, at 19:01 on a
> mild evening, and the chiller locked out. Freezing is not the failure mode and capacity was never
> reached; **P59 is**.
>
> **P59, "AC anti-freezing temperature", defaults to 3 °C, which is 37.4 °F**, and it watches leaving
> water. Range is −15 to 5 °C. Against a 9 °F evaporator ΔT that default puts the lowest safe return
> target at about 49 °F, which is why 50 °F ran all season without complaint and 46 °F failed in one
> night.
>
> **The controller stores the target in whole °C, so a Fahrenheit entry lands lower than typed.**
> This is the rounding David observed, and it is worth 1.8 °F a step:
>
> | Typed | Stored | Actual target | Leaving at 9 °F ΔT | Against P59 = 37.4 °F |
> |---|---|---|---|---|
> | 50 °F | 10 °C | 50.0 °F | 41.0 °F | 3.6 °F of margin |
> | 48 °F | 8 °C | 46.4 °F | 37.4 °F | **exactly on the trip** |
> | 46 °F | 7 °C | 44.6 °F | 35.6 °F | **1.8 °F below the trip** |
> | 44 °F | 6 °C | 42.8 °F | 33.8 °F | 3.6 °F below |
>
> 50 °F is exactly 10 °C, which is why it alone loses nothing to rounding. **Think in whole °C**, and
> read the stored value back after entering one.
>
> **So the order of operations matters, and it is not the one this document first gave.** P109 opens
> the setpoint range; P59 decides when the machine protects itself; the glycol decides how far P59
> may safely move. Top up the glycol first, then lower P59 with margin above the fluid's freeze
> point, then lower the target. Lowering the target alone buys a lockout.
>
> **Recovery: the controller's "Error reset" button did not clear this one.** A latched
> level-one-twice antifreeze fault needed a power cycle at the breaker. Leave it off about a minute,
> restore the target to a whole °C with margin, and expect a few minutes' delay before the compressor
> starts on its own minimum-off timer. Use "Clear" only to wipe the error log, which is worth
> keeping. **If E14 returns at a 50 °F target, the setpoint is no longer the explanation** — look at
> water flow, at the charge, and at the leaving-water sensor itself.

**Read the secondary main pipe size.** It swings the Loop A head estimate from about 13 ft to
about 30 ft ([5.5](#55-friction-head-on-the-index-circuits)) and decides whether balancing or a
bigger pump is the answer if the tap change falls short.

**Add a design-day saturation alert.** Chiller power pinned near 3,537 W for an extended period
with droop above zero on more than one zone is the signature of the plant running out, and it is
the condition none of the sampled days contained. Grafana already has the two series.

**Confirm the attic coil's automatic air vent and the expansion-tank position** relative to both
secondary circulators ([5.4](#54-what-elevation-does-affect)). Visual checks.

**Set Loop B to HIGH before heating season**, with the 25 % to 30 % glycol top-up. Loop B drives
one coil in summer and three in winter, including both M3036 hydronic modules, and the
calculation puts LOW at 74 % of design across them against 91 % on HIGH ([5.7](#57-choosing-the-pump-speed-and-whether-balancing-helps)). Return it to LOW
in spring. Set `fluid_k` to 476 on the day of the top-up and add a Grafana annotation.

### 7.2 Under $100

**Four DS18B20s on the secondary loops, about $20.** This is the highest-value purchase in the
document. It resolves criteria 3 and 4, gives per-loop flow through the ratio method with no
meter, and detects reverse mixing ([4.2](#42-the-sensor-package)).

**A Y2 sense relay on the master bedroom, about $15.** A 24 VAC coil relay across Y2 and C, its dry
contacts on the spare pair back to a free Pi input, and one more entry under `pivac.GPIO`. That
makes the zone's stage-2 runtime a logged series and answers the fourth question this document
opened with ([4.6](#46-reading-the-master-bedrooms-fan-stage)). Contingent on the pair ringing out;
if it is open, the signal goes on the air-handler node instead.

**Restore leak detection, about $20.** The booster-pump leak pan lost its GPIO input when BCM 25
was renamed from `SCALA` to `CHIL` on 11 August 2026. A room holding the boiler, buffer tank, DHW
and the domestic water main now has no water detection. Free inputs with existing wire runs are
BCM 13/33, 16/36 and 24/18. Avoid BCM 26, a dead pad. This has nothing to do with cooling and is
the cheapest insurance available.

**A mechanical-room temperature and humidity sensor, about $15.** Explains the Pi's thermal
ceiling, which sits at 76 °C with 83 °C peaks against an 80 °C soft limit, and flags chilled-pipe
sweating.

**Two 10K NTC duct sensors, already on hand.** In whichever zone the humidity comparison
identifies, these give measured sensible capacity and separate an airflow-starved coil from a
capacity-limited one ([4.4](#44-air-side-sensors-on-one-air-handler)).

### 7.3 $100 to $500

**Close the loop from the master bedroom back to the chiller with Dynamic Humidity Control.** The
CX-series controller already does what a home-built feedback loop would do: it takes an indoor
temperature and humidity sensor on its own RS-485 pair and lowers the water target when room humidity
passes P114 or room temperature passes P115. Humidity feedback and "this zone cannot hold" feedback
both arrive from one sensor, so the Y2 wire stays a measurement rather than becoming a control input
([K.4](#k4-dynamic-humidity-control-is-the-feedback-loop-you-would-have-built)). Site the sensor in
the master bedroom, which is the binding zone. Cost is the sensor plus a wiring run to the outdoor
unit and a parameter session; the sensor price is not established here. This is the version of
[7.1](#71-costs-nothing)'s target reduction that pays the efficiency cost only while humidity asks
for it.

**A flow meter on the primary, $200 to $400.** Converts every ratio in this document into
absolute BTU/hr and yields system COP against the existing Chiltrix CT
([4.5](#45-a-flow-meter-on-the-primary)). Buy this before any per-coil meter.

**A static balancing valve on the kids-room branch, roughly $60 to $120 installed. Defer this
one.** It is the direct answer to criterion 4: as installed the kids room takes 122 % of design
flow on MEDIUM while the master bedroom takes 74 %, and throttling the near branch brings both to
about 85 % ([5.7](#57-choosing-the-pump-speed-and-whether-balancing-helps)). Three things argue
against doing it now. The exchange rate is about half a gallon per minute gained for every one
removed. The master bedroom holds setpoint today, so this reads as design-day insurance rather than
a fix. And the kids zone carries the house's largest latent load
([3.3](#33-humidity-is-the-marginal-axis)), so cutting its flow works against the one measured
shortfall.

**Y2 fraction is what would promote it.** The middle argument rests on the master bedroom holding
setpoint, and a zone that holds setpoint by running stage 2 half the time is not the same as a zone
holding it comfortably ([5.10](#510-why-the-master-bedroom-calls-its-high-fan-stage)). Revisit this
if the loop sensors confirm the split and Y2 fraction stays high after the return-water target
comes down, or if the zone starts drooping on hot afternoons.

**Pressure-independent control valves, $150 to $300 per branch, are the better version of the same
idea.** They combine the zone valve and the balancing function in one body and hold branch flow at
a set rate regardless of what other zones do, which is what "ideal share" means in hardware. They
cost more than static balancing and they are correct under every combination of calls rather than
at one design point. The same deferral applies.

**The air-handler node, roughly $300 with a flow meter.** Full specification in
[Appendix E](#appendix-e--air-handler-node-build-specification). It is the only route to per-coil attribution within a loop and to the sensible and latent
split. It sits behind the loop sensors and the primary meter, which cost less and answer larger
questions.

### 7.4 $500 to $2,000

**Replace the Taco with an ECM circulator on the primary, $400 to $700.** Justified only if the
loop sensors show reverse mixing, which would mean combined secondary flow exceeds what a 1/20 HP
pump supplies. A Grundfos ALPHA2 or equivalent in constant-pressure mode also removes the
speed-tap guesswork.

**Pressure-independent balancing valves on the Loop A branches, $150 to $300 each.** These hold
branch flow at a set GPM regardless of how many other zones are open, which is the exact failure
mode section 5.5 predicts. More expensive than static balancing and correct under every
combination of calls rather than at one design point.

**ΔP-controlled ECM secondary circulators, $500 to $900 each.** A constant-pressure ECM holds
per-branch flow steady as zone valves open and close, which is the clean version of stepping a pump
up when more zones call, and it removes Loop B's seasonal tap ritual entirely. **Buy them when a
circulator fails rather than before.** They redistribute and economise; they add no capacity, and
they cannot exceed the primary-flow ceiling in
[5.8](#58-can-the-primary-supply-both-loops-at-maximum-call). A ΔT-controlled model is the wrong
choice here, since holding a higher loop ΔT means less flow and less dehumidification
([B.6](#b6-water-flow-and-dehumidification-move-together)).

**Do not build the speed control in pivac.** An ECM circulator does this autonomously and
continuously, without adding a software failure mode to the heating and cooling paths. pivac's job
is measuring whether it worked.

### 7.5 Ideal pump sizing, ignoring what is installed

Each circuit's duty point is its design flow at the head that circuit presents.

| Circuit | Design flow | Head | What it pushes |
|---|---|---|---|
| Chiller to tank | ~10.7 GPM at 10 °F ΔT | ~19 ft | CX-series evaporator plus tank piping. The CX75's internal pump |
| Primary distribution, tank to header | must exceed 15.8 GPM in summer | **~3 to 5 ft** | A 6 ft header in 1½" copper, tank runs, fittings and the pump's check valve |
| Boiler circuit, heating | must exceed 25.8 GPM | ~9 to 19 ft | Ti-200 exchanger plus the same short header. No tank in this path |
| Loop A secondary | 10.0 GPM | ~26 ft | 150 ft of 1¼" main, M2430 coil at 7.4 ft, zone valve |
| Loop B secondary | 16.5 GPM, the winter case | ~23 ft | 120 ft of main across three coils |

**Nothing here needs replacing on capacity grounds.** The primary duty is 16 GPM against 3 to 5 ft,
which wants flow rather than head, and the Taco 0015-MSF3-IFC delivers 14 to 16 GPM there. It is a
sensible pairing rather than an undersized one
([5.8](#58-can-the-primary-supply-both-loops-at-maximum-call)). The boiler circuit lands at 22 to
26 GPM against a 25.8 GPM winter demand, equally marginal.

If a primary pump were ever replaced, the duty is easy to beat: a UP26-99 class circulator on speed
1 reaches well past 16 GPM against 5 ft, and an ECM in the 0014e or ALPHA2 25-70 class does the
same while trimming itself. Neither is worth buying against a gap this uncertain.

| Recovering the mixing penalty | Total capacity | Latent capacity |
|---|---|---|
| 0.95 °F, today's load, if the gap is real at all | +3.7 % | +6.3 % |
| 1.46 °F, design load | +5.6 % | +9.7 % |

And it only applies while both loops call together. Loop A alone draws 9.3 GPM and Loop B alone
6.5, both well under the primary, so each is already decoupled and carries no penalty at any pump
size. How often the two overlap is unmeasured, which the zone call state already in InfluxDB
([4.2](#42-the-sensor-package)) answer.

The secondaries are a different story. Loop A wants 10 GPM at 26 ft, slightly beyond a UP26-99 on
HIGH. Loop B wants 16.5 GPM at 23 ft in winter against 6 GPM at 12 ft in summer, a three-to-one
turndown no fixed three-speed pump serves well.

> **Loop B is the strongest case for an ECM in the house**, precisely because of that turndown. A
> constant-pressure ECM covers both duties with no seasonal tap change. Loop A gains less, since
> its duty barely moves between seasons. Buy either when a circulator fails rather than before.

> Upsizing pipe competes with upsizing pumps on the secondaries. Loop A's 26 ft is roughly half
> main friction and half coil and valve, so a larger main would cut the duty point rather than
> raise the pump to meet it. Worth pricing only if a run is already open.

### 7.6 Above $2,000, and the last resort

**Upsize the Loop A mains.** Only if the pipe proves to be 1" and balancing cannot deliver design
flow to the master bedroom. Opening walls to reach a 105 ft run is the most expensive item here
and the least likely to be needed, since the plant saturates before the distribution does.

**Split the master bedroom onto its own circulator.** Cheaper than repiping and it removes the
index circuit from the shared loop. Consider it only if criterion 4 fails specifically on that
zone.

**Modulating zone valves under pivac control.** Belimo characterised control valves, an actuator
driver, and flow measurement to close the loop. This inserts a software failure mode into both
the heating and cooling paths for a gain bounded by coil capacity saturating above design flow.
Everything above captures most of the benefit with no software and nothing to maintain.

### 7.7 What not to do

**Do not chase an 8 to 12 °F ΔT.** It would mean raising the chiller's target and cutting flow,
and lower water flow costs capacity and dehumidification in a house whose measured shortfall is
humidity ([5.2](#52-what-that-means-for-the-8-to-12-degree-target)). The number is a design
convention, and this system is better off without it.

**Do not throttle a valve to move the ΔT either.** The ΔT is held by a control loop, so throttling
makes the pump work harder against the restriction and arrive at the same target
([5.1](#51-primary-flow-is-fixed-so-primary-delta-t-reads-house-load)).

**Do not raise both secondary taps at once.** Combined secondary flow above primary flow causes
reverse mixing, which loses more than it gains
([Appendix C](#appendix-c--primarysecondary-hydraulics)). Loop A is the one that needs it; Loop B
in summer drives a single coil over 15 ft and is already generous.

**Do not reset `rounding` to 0 in the 1-wire config.** Every ΔT analysis here depends on the
two-decimal Kelvin fix. If a WilhelmSK gauge shows noisy decimals, set the precision in the app.

**Do not add capacity before testing a design day.** The 46 % duty at 80 °F suggests reserve, and
the 6-tons-of-coil against 4.3-tons-of-chiller ratio suggests a limit. One hot afternoon of data
settles which, and it costs nothing.

---

## 8. Sequence

| Step | Action | Cost | Resolves |
|---|---|---|---|
| 1 | Read the master bedroom's thermostat settings; read the secondary main pipe size; check for branch balancing valves | — | [4.1](#41-free-read-the-pipe-and-the-pump) |
| 2 | Ring out the spare pair from the master bedroom's air handler | — | Decides step 4 |
| 3 | Set the master bedroom's fan from circulate to auto; watch its RH for a few comparable hot days | — | Criterion 2 |
| 4 | Y2 sense relay on the master bedroom, on that pair to a free Pi input | ~$15 | Criterion 1, and it scores every step below |
| 5 | Measure the loop's glycol percentage, then top up 25 % to 30 % | ~$60 | Prerequisite for steps 6 and 7 |
| 6 | Lower **P59** from 3 °C with margin above the glycol's freeze point; consider raising **P53** | — | Without this, step 7 locks the chiller out on E14 |
| 7 | **Build the Modbus feed, then step the return target down one whole °C and hold** | — | **The largest single remedy.** Criteria 1 and 2 |
| 8 | Add the design-day saturation alert; wait for one 95 °F afternoon | — | Criterion 5, and it bounds how far step 7 can go |
| 9 | Four DS18B20s on the secondary loops | ~$20 | Criteria 3 and 4, and whether the Loop A tap change delivered |
| 10 | Restore leak detection; add mechanical-room T/RH | ~$35 | Regression, and the Pi's thermal ceiling |
| 11 | Two 10K NTCs in the master bedroom's plenums | on hand | Sensible against latent, and load against shortfall |
| 12 | Dynamic Humidity Control sensor, sited in the master bedroom | sensor + wiring | Makes step 7 automatic and seasonal rather than fixed |
| 13 | Flow meter on the primary | $200–400 | Absolute capacity and system COP |
| 14 | Branch balancing on Loop A, if step 9 shows maldistribution | $200–400 | Criterion 4 |
| 15 | The air-handler node at the master bedroom | ~$300 | Per-coil attribution, and Y2 if the pair is open |

Steps 1 to 4 are instrumentation and about $15 between them. Step 1 leads because a finish-on-high
staging rule would make step 4 a record of the thermostat rather than of the coil
([5.10](#510-why-the-master-bedroom-calls-its-high-fan-stage)), and step 4 leads the rest because Y2
fraction is what scores every change after it.

**Step 7 is the one that matters, and steps 5 and 6 are not optional preparation for it.** Lowering
the target without lowering P59 locks the chiller out on E14, which is not a hypothetical: it
happened on 21 August 2026 at a 46 °F target ([7.1](#71-costs-nothing)). **The target now stays at
50 °F until the Modbus feed can watch the leaving water while it moves** — registers 202 and 203 give
the actual part-load evaporator ΔT, which is the number that decides whether a colder target needs
P59 touched at all, and 257 and 260 show whether the pump is falling to its P53 minimum at low
demand, which is the mechanism behind the lockout ([4.2](#42-the-sensor-package)). Step 8 then says when to
stop stepping down, since capacity falls with the target and this plant is smaller than the one it
replaced. Change one step at a time so effects stay separable. Step 9 settles the distribution
questions: it either confirms the healthy-decoupling reading in
[5.9](#59-what-is-still-unresolved) and shows whether the Loop A tap
change delivered, or it finds mixing or maldistribution and sends the work to step 14.

---

## 9. Open questions

- Is the spare pair from the master bedroom's air handler still continuous, and does that handler
  take Y2 as a blower-speed tap rather than as a second call to something else? Together they decide
  whether stage-2 runtime costs $15 or waits for the node
  ([4.6](#46-reading-the-master-bedrooms-fan-stage)).
- What are ISU 3010, 3020, 3030, 3140, 9000 and 9070 set to on the master bedroom thermostat? The
  first decides whether the rest are displayed at all
  ([Appendix J](#appendix-j--the-master-bedroom-thermostat)).
- How much of each loop is 1¼" PEX and how much is 1"? It is the largest remaining uncertainty in
  the hydraulic calculation. At 1¼" mains Loop A reaches 82 to 99 % of design flow; at 1" it falls
  to 61 to 72 % ([5.6](#56-what-the-calculation-says-about-each-coil)).
- What is the pressure drop of the hot-water hydronic modules in the two M3036 units? The winter
  figures use the M3036 chilled-water coil as a stand-in.
- What is Unico's own glycol multiplier for pressure drop at 25 % and at 30 % propylene glycol? The
  calculation uses 1.25 and 1.10, which are standard values rather than Unico's
  ([5.5](#55-friction-head-on-the-index-circuits)).
- What is the zone-valve Cv? Assumed at 3 ft of drop at 6 GPM.
- What is the Ti-200's water-side pressure drop at design flow? It swings the boiler circuit from
  27 GPM to 21 against a 25.8 GPM winter call, which is the difference between adequate and short
  ([5.8](#58-can-the-primary-supply-both-loops-at-maximum-call)).
- What is the loop's glycol percentage, measured with a refractometer rather than assumed? P109 = 1
  is conditioned on the fluid not freezing at −10 °C, and 25 % propylene glycol sits on that line
  rather than inside it ([7.1](#71-costs-nothing)).
- What is the CX75's actual evaporator ΔT at part load? Chiltrix's 9 °F is the design figure from its
  sizing formula, and it sets how much leaving-water headroom each target step costs. `C04` and `C05`
  on the controller answer it in one reading ([7.1](#71-costs-nothing)).
- Where does the CX75's capacity land at a 42 °F return target, and does Chiltrix publish the derate?
  It decides how far step 6 of the sequence can go before the plant becomes the limit.
- Which indoor sensor does Dynamic Humidity Control take, and what does it cost
  ([K.4](#k4-dynamic-humidity-control-is-the-feedback-loop-you-would-have-built))?
- Are there balancing valves on any branch today?
- What is the CX75's published design flow and evaporator pressure drop? The sell sheet omits
  both. The neighbouring CX65 publishes 10.6 GPM design and 16 ft of head at 10 GPM, which is the
  figure section 4.3 leans on.
- Does the Taco run continuously through a cooling call or only with the compressor, and is it
  powered from the Chiltrix circuit and therefore already inside
  `electrical.emporia.house.chiltrix`?
- Does the CX75 expose Modbus RTU? It would supply entering and leaving water temperature and
  compressor state with no plumbing work, replacing several sensors in section 4.
- How many hydronic zone valves are there, and does one HZ-432 drive all five? Five zones take hot
  water in winter, which is more than a single four-zone panel provides. The kitchen and great
  room may be switched separately, since their cooling comes from their own condensers.
- In heating, does hot water come from the boiler alone, or does the Chiltrix also run as a heat
  pump? It decides whether a heating efficiency figure is a COP against the Chiltrix CT or a
  combustion efficiency against gas input.
- Which glycol is in the loop, propylene or ethylene? It moves `K` by 3 %
  ([Appendix B](#appendix-b--measurement-physics)).

---

# Appendix A — System reference

## A.1 Topology

```
  boiler ──[Grundfos UP26-99F, HIGH]──┐                  ┌── Loop A [UP26-99F, LOW]
                                      ├─ PRIMARY HEADER ─┤    └─ kids (75 ft) → master BR (attic)
 chiller ──[Taco 0015-MSF3-IFC]───────┘  (closely spaced └── Loop B [UP26-99F, LOW]
            18 GPM / 17 ft max               tees)            └─ lower fam. room (15 ft)
                                                                 → kitchen (+10 ft rise)
                                                                 → great room (+20 ft)
```

Each source carries its own primary pump; no separate always-on primary circulator exists.
Primary flow is whatever the active source pump delivers, the Taco in cooling and the boiler's
UP26-99F in heating. One three-speed circulator serves each secondary loop, with HZ-432 zone
valves per zone.

The primary return routes to the active source: to the boiler loop when heating, to the chiller
buffer tank when cooling. The buffer tank therefore serves the chilled side only, and heating
runs unbuffered (see [C.4](#c4-cooling-is-buffered-heating-runs-direct)).

## A.2 Seasonal asymmetry

| | Loop A | Loop B |
|---|---|---|
| Summer, chilled | kids room and master bedroom | lower family room only; kitchen and great room cool on their BOVAs |
| Winter, hot | kids room and master bedroom | family room, kitchen, great room |

Loop A carries two coils year-round, and its index circuit is the master bedroom at roughly 105 ft
one way with the coil in the attic. It is the harder duty of the two in summer and the loop the
humidity measurement points at ([3.3](#33-humidity-is-the-marginal-axis)).

Loop B in cooling is a single-zone loop, hydraulically isolated. One zone valve open and one pump
running leaves nothing to share flow with, so its cooling-season flow is constant. The family-room
coil is therefore the cheapest to instrument and the easiest to interpret, and it doubles as the
high-flow reference against which the two Loop A coils are compared.

Loop B's speed tap is consequently a seasonal setting. It is sized for three zones in winter and
drives one in summer, so no single tap suits the whole year.

| Season | Zones on Loop B | Right tap |
|---|---|---|
| Summer, chilled | 1, the lower family room | LOW, and it still over-pumps that coil by about 19 % |
| Winter, hot | 3: family room, kitchen, great room | HIGH. LOW delivers 74 % of design across the three ([5.7](#57-choosing-the-pump-speed-and-whether-balancing-helps)) |

## A.3 The plant

| | Value | Source |
|---|---|---|
| Chiltrix CX75 cooling | 4.3 tons, 51,600 BTU/hr | Unico sell sheet |
| Chiltrix CX75 heating | 6 tons, 72,000 BTU/hr | Unico sell sheet |
| Cooling efficiency | EER 19.6 IPLV | Unico sell sheet |
| Heating efficiency | COP 4.57 at W95/A47 | Unico sell sheet |
| Refrigerant | R32 | Unico sell sheet |
| Design flow | not published for CX75; CX65 publishes 10.6 GPM | inferred |
| Evaporator head | not published for CX75; CX65 publishes 16 ft at 10 GPM | inferred |
| NTI Trinity Ti-200 | gas condensing boiler, heating only | existing |

Coil capacity connected to the chiller totals roughly 6 tons across three M2430 air handlers,
against 4.3 tons of plant. Diversity covers that on an average day and not necessarily on a
design day.

## A.4 Air handlers and their coils

| Zone | Model | Nominal | Cooling | Heating | Loop |
|---|---|---|---|---|---|
| Kids room | Unico M1218 | 1 to 1.5 ton | chilled water | hot water | A |
| Master bedroom | Unico M2430 | 2 to 2.5 ton | chilled water | hot water | A, coil in attic |
| Downstairs family and utility | Unico M2430 | 2 to 2.5 ton | chilled water | hot water | B |
| Kitchen | Unico M3036 | 2.5 to 3 ton | 6-row refrigerant coil, BOVA `BOS1` | hot-water hydronic module | B, heating only |
| Great room | Unico M3036 | 2.5 to 3 ton | 6-row refrigerant coil, BOVA `BOS2` | hot-water hydronic module | B, heating only |

The two M3036 units are the largest boxes in the house and they cool on refrigerant, so the water
side never sees them in summer. In winter their hydronic modules make Loop B the heavier of the
two loops, and its 1¼" PEX mains run 5.9 ft/s at design flow
([5.5](#55-friction-head-on-the-index-circuits)).

Published coil pressure drop, Unico bulletin 20-020.3.020, at 45 °F entering water and pure water,
in feet of water gauge:

| Coil | 2 GPM | 4 GPM | 6 GPM | 8 GPM |
|---|---|---|---|---|
| M1218CL1-C | 0.9 | 3.4 | 7.4 | — |
| M2430CL1-C | 0.9 | 3.4 | 7.4 | 12.6 |
| M3036CL1-C | 0.6 | 1.8 | 4.2 | 7.2 |

The M1218 and M2430 coils are hydraulically identical. Across 40 to 55 °F entering water the drop
moves about 4 %, so temperature is a minor correction; glycol is the larger one and Unico publishes
a multiplier table for it in the same bulletin.

The kitchen and great room carry hot-water hydronic modules rather than CL chilled-water coils, and
their pressure drops are in a different bulletin. Branch runs to the handlers are 1" PEX stepping
to ¾" sweat connections at the cabinet.

## A.5 Existing instrumentation

| Signal K path | What it measures |
|---|---|
| `environment.inside.hvac.IN.temperature` | Primary supply, just before the closely spaced tees |
| `environment.inside.hvac.OUT.temperature` | Primary return, just after the tees |
| `environment.inside.hvac.UBT.temperature` | Buffer tank, upper |
| `environment.inside.hvac.LBT.temperature` | Buffer tank, lower |
| `electrical.emporia.house.chiltrix` | Chiller electrical power, W |
| `electrical.emporia.house.bova_kitchen` | Kitchen BOVA condenser power, W |
| `electrical.emporia.house.bova_great_room` | Great-room BOVA condenser power, W |
| `electrical.ac.arduinoThermPSI.psi` | Hydronic loop pressure |
| `environment.inside.thermostat.<ZONE>.temperature` | Zone temperature, 1 °F resolution |
| `environment.inside.thermostat.<ZONE>.coolset` | Zone cooling setpoint |
| `environment.inside.thermostat.<ZONE>.humidity` | Zone RH, 1 % resolution |
| `environment.outside.thermostat.temperature` | Outdoor air |
| `electrical.ac.switch.utility.CHIL` | Any water-cooled zone calling |
| `electrical.ac.switch.utility.BLR` | Boiler call, used for changeover mode |
| `hvac.boiler.sentry.*` | Boiler supply temperature, gas input, burner state |

> `CHIL` is a system-wide call rather than any one zone's. It asserts when any water-cooled zone
> calls through the HZ-432, so it reads true while a given coil's valve is shut. Never gate a
> per-coil calculation on it. Use it for changeover mode, telling you whether arriving water is
> chilled or hot, and prefer determining that from supply water temperature so the logic survives
> another relay-roster change.

---

# Appendix B — Measurement physics

## B.1 Water measures total capacity; air dry bulb measures sensible only

```
Q_total    [BTU/hr] = K × GPM × ΔT_water [°F]
Q_sensible [BTU/hr] = 1.08 × CFM × ΔT_air [°F]
```

In cooling these disagree by design. Everything the coil spends condensing water vapour appears
in the water ΔT and not in the air dry-bulb ΔT. On a high-velocity Unico coil the latent fraction
is large, with SHR typically 0.70 to 0.75, so the air-side figure lands 25 to 30 % below the
water-side figure. That gap is the dehumidification.

Heating has no latent load, so the two sides must agree. That makes heating season the calibration
window ([G.2](#g2-cfm-is-commanded-which-turns-the-energy-balance-into-a-diagnostic)).

## B.2 K is 481 for a 25 % glycol loop

The textbook constant 500 assumes pure water: 8.337 lb/gal × 60 × Cp 1.0. With glycol,
`K = 500.2 × SG × Cp`.

| Fluid | SG | Cp, BTU/lb·°F | K | Error if you use 500 |
|---|---|---|---|---|
| Water | 1.000 | 1.000 | 500 | — |
| 25 % propylene glycol at 45 °F, the loop today | ~1.028 | ~0.935 | ~481 | 4 % high |
| 25 % propylene glycol at 140 °F | ~1.010 | ~0.955 | ~483 | 3.5 % high |
| 30 % propylene glycol at 45 °F, planned before winter | ~1.035 | ~0.920 | ~476 | 5 % high |
| 25 % ethylene glycol at 45 °F | ~1.035 | ~0.900 | ~466 | 7 % high |

Confirm the glycol type and verify the concentration with a refractometer rather than trusting
the fill record. Keep `K` in config rather than firmware. This one number carries a 4 to 7 %
systematic bias into every capacity figure the system will ever produce.

> The planned 25 % to 30 % change creates a discontinuity. Three things happen at once, and
> unanticipated they read as a fault.
>
> 1. `K` drops from about 481 to about 476. Update `fluid_k` in `config.yml` on the day. Left
>    stale, every subsequent figure runs about 1 % high.
> 2. Real capacity drops slightly. Higher glycol lowers specific heat and raises viscosity, which
>    reduces flow at the same pump head and slightly worsens heat transfer. Expect a step down of
>    a few percent in capacity and UA.
> 3. Re-measure GPM afterwards if you are running on a fixed-flow constant. The viscosity change
>    moves the operating point on the pump curve.
>
> Add a Grafana annotation on the changeover date. A year later an unexplained step in the UA
> trend invites a fouling diagnosis.

## B.3 Delta-T precision sets the accuracy of every capacity figure

Capacity error is directly proportional to ΔT error. At a design ΔT_water of 10 °F:

| Per-sensor error | Worst-case ΔT error | Capacity error |
|---|---|---|
| DS18B20 datasheet absolute, ±0.9 °F | ±1.8 °F | ±18 % |
| After matched-pair calibration, ±0.05 °F | ±0.1 °F | ±1 % |

A ±18 % measurement cannot answer whether a coil is delivering its maximum, so matched-pair
calibration is required ([G.1](#g1-matched-pair-calibration-before-install)). The DS18B20's
0.0625 °C resolution and its repeatability are both excellent. Only absolute accuracy is poor,
and absolute accuracy cancels out of a difference once the offset is characterised.

The same argument covers the 10K NTCs and disposes of a second problem with them. Honeywell 10K
sensors come in more than one resistance curve, Type II at about 32.6 kΩ at 32 °F and Type III at
about 29.5 kΩ. Guessing wrong costs several degrees absolute, and two duct sensors of the same
part calibrated as a pair make that error common-mode. Verify the curve anyway with an ice bath:
the two types differ by about 10 % at 32 °F, which any multimeter resolves.

## B.4 The two deltas move in opposite directions

The water and air deltas are linked by the energy balance, so when capacity falls, the delta that
moved identifies the constrained side.

| Signature | ΔT_water | ΔT_air | Capacity | Diagnosis |
|---|---|---|---|---|
| Water-starved | up | down | down | Closed balancing valve, plugged strainer, air-bound coil, failing circulator, zone valve not fully opening |
| Air-starved | down | up | down | Dirty filter, collapsed or undersized duct, blower speed tap, iced coil |
| Plant-limited | normal | normal | down | Entering water temperature wrong: tank off setpoint, chiller undersized, changeover fault |
| Overpumped | low | normal | at spec | Capacity fine, pump energy wasted. Throttle the balancing valve |

A single delta is ambiguous. Both together isolate the fault.

> A constant-airflow ECM suppresses the air-starved signature until it is severe. The table above
> describes a fixed-speed blower. A constant-airflow ECM holds CFM against rising static pressure
> by drawing more torque, so a moderately dirty filter changes neither ΔT_air nor capacity and
> shows up only as increased blower watts, which nothing here meters. The signature then appears
> abruptly and late, once the motor runs out of authority. The early warning is the CFM ratio in
> [G.2](#g2-cfm-is-commanded-which-turns-the-energy-balance-into-a-diagnostic). A stable ΔT_air is
> not evidence of a healthy air side.

## B.5 Coil capacity against water flow saturates

Capacity against flow is a saturating curve. Below design flow, capacity climbs steeply, and
recovering from 50 % to 100 % of design is worth 20 to 25 %. Above design flow the curve
flattens: 100 % to 150 % buys perhaps 3 to 5 % while pumping power rises roughly with the cube of
flow.

Flow below design leaves real capacity available, usually through the cheapest fix on the list.
Flow at or above design offers almost nothing, because the ceiling comes from entering water
temperature and coil UA.

Balancing redistributes capacity between zones rather than creating it. Total loop capacity comes
from the plant and the pump.

| Symptom | Meaning | Right intervention |
|---|---|---|
| One room short while another overshoots | Maldistribution | Balance the branches |
| All rooms on a loop short together | Loop-wide shortfall | Speed tap, or the plant and its entering water temperature |
| Water ΔT very low, 3 to 5 °F, at high plant output | Overpumped | Lower the tap, and check for reverse mixing |
| Water ΔT above 15 °F with low capacity | Starved | More flow, or find the restriction |

> Read that last table only against known plant output. At part load a low ΔT means nothing at
> all ([5.1](#51-primary-flow-is-fixed-so-primary-delta-t-reads-house-load)).

## B.6 Water flow and dehumidification move together

In cooling, water flow sets the average coil surface temperature, which sets the sensible and
latent split. Water leaves the coil at `T_in + Q / (K × GPM)`, so the average water temperature is
`T_in + Q / (2 × K × GPM)`. Lower flow raises that average, which raises the surface temperature
along the leaving-water end of the coil.

Dehumidification depends on how much of the coil surface sits below the entering-air dewpoint. At
76 °F and 55 % RH the dewpoint is about 58.6 °F. Water entering at 47.8 °F gives a surface near
51 °F at high flow, condensing across the whole coil. Drop the flow until the water leaves 8 °F
warmer and the last part of the coil reaches 57 to 58 °F, at the dewpoint, where it stops
condensing.

**More water flow therefore removes more moisture, and less flow removes less.** A zone that holds
setpoint yet feels clammy wants more water flow, a lower entering water temperature, or less
airflow.

> This runs opposite to the air side, which is the common source of confusion. Lower *airflow*
> gives a colder coil and more dehumidification, and that is the direction
> [Appendix D](#appendix-d--the-bova-direct-expansion-zones) uses for the direct-expansion zones.
> Lower *water* flow gives a warmer coil and less dehumidification. The two adjustments move
> latent capacity in opposite directions.

Heating carries no latent load and offers nothing to modulate. Take flow up to saturation and
stop.

---

# Appendix C — Primary/secondary hydraulics

## C.1 Closely spaced tees and how they fail

Closely spaced tees deliver full primary supply temperature to a secondary loop only while
secondary flow stays at or below primary flow. A secondary pump drawing more than the primary
supplies makes up the deficit by pulling water backwards from the return tee, blending return
water into the supply. Cooling then sends warmer water to the coil and heating sends cooler.
Capacity drops, and the usual misdiagnosis is an undersized chiller.

Verification costs one comparison. Against `environment.inside.hvac.IN.temperature`, the primary
supply already in InfluxDB:

- In cooling, a loop supply warmer than `IN` by more than pipe gain means reverse mixing, with
  the secondary overdrawing relative to primary flow.
- In heating, a loop supply cooler than `IN` means the same fault with the opposite sign.

Combined secondary flow has to stay under primary flow when both secondary pumps run. This
constraint bounds how far the secondaries can be raised if a loop proves starved: raising a
secondary tap trades a starvation problem for a mixing problem.

## C.2 The flow ratio falls out of temperatures alone

Mixing is arithmetic. With one secondary loop active, primary supply `T_ps` equal to `IN`,
primary return `T_pr` equal to `OUT`, and secondary return `T_sr`:

```
T_pr = [ (GPM_pri − GPM_sec)·T_ps  +  GPM_sec·T_sr ] / GPM_pri
```

which rearranges to

```
GPM_sec / GPM_pri  =  (T_ps − T_pr) / (T_ps − T_sr)  =  ΔT_primary / ΔT_secondary
```

The ratio of the two ΔTs is the flow ratio, and it holds in both regimes.

| ΔT_pri / ΔT_sec | Meaning |
|---|---|
| < 1 | Primary flow exceeds secondary. Healthy decoupling; the coil gets full primary temperature |
| ≈ 1 | Flows matched, on the edge |
| > 1 | Secondary overdraws. Reverse mixing, coil entering temperature degraded |

A supply sensor on each loop gives the same answer a second way. Loop supply equal to `IN` means
no mixing, and divergence from it means mixing.

One accuracy caveat. This is a ratio of two differences, so when primary flow greatly exceeds
secondary, ΔT_primary is small and its relative error dominates. At a 0.4 flow ratio and a 10 °F
secondary ΔT, primary ΔT is 4 °F, which works after the two-decimal fix and pair calibration and
fails before. `IN` and `OUT` need the same matched-pair treatment as
[G.1](#g1-matched-pair-calibration-before-install), and have almost certainly never had it.

## C.3 An idle loop identifies itself

In summer Loop B serves only the lower family room, so whenever that zone is not calling,
`IN − OUT` reflects Loop A alone, which is the two-coil case the algebra above assumes.

The family room has a RedLink thermostat, `DSTRS_FAM_ROOM`, so its call state is already in
pivac and the isolation windows can be selected from data on hand. The loop sensors confirm it
independently. A loop with its pump off and its zone valve shut shows supply and return
converging, both drifting toward ambient, so a loop ΔT under about 1 °F is a reliable idle flag.
Free GPIO inputs with existing wire runs are BCM 13/33, 16/36 and 24/18 if a hard signal is ever
wanted.

## C.4 Cooling is buffered; heating runs direct

The primary pump belongs to its source and generally runs only when that source runs. If a source
stops while a secondary pump keeps circulating, primary flow reaches zero, the secondary
recirculates its own return water, and the coil receives return temperature while the zone still
calls.

In cooling the buffer tank prevents this. The primary return routes through the tank, leaving a
reservoir of chilled water between compressor cycles.

In heating the primary return goes to the boiler loop and bypasses the tank, so no thermal
reservoir exists. A single small Unico zone calling against a Trinity Ti-200 is a very large
turndown, and an unbuffered condensing boiler at far-below-minimum load short-cycles.

> This is visible today with no new hardware. Plot `hvac.boiler.sentry.gasInputValue` against the
> number of zones calling. Many short cycles on a one-zone call is the unbuffered-heating
> signature, and the remedy is a buffer or hydraulic separator on the heating side. Use
> `gasInputValue` rather than `burnerOn`, which under-reports during calls before the 2026-07-20
> LED recalibration.

## C.5 Pump curves

| Pump | HP | Maximum flow | Maximum head | Position |
|---|---|---|---|---|
| Taco 0015-MSF3-IFC | 1/20 | 18 GPM | 17 ft | Chiller primary |
| Grundfos UP26-99F / UPS26-99FC | 1/6 | ~33 GPM | ~29 ft on speed 3 | Boiler primary, both secondaries |

Maximum head is the shutoff figure at zero flow. Useful head at working flow is far lower, and a
three-speed circulator's LOW runs roughly 50 to 60 % of its HIGH flow at a given head. Pull the
manufacturer curve before sizing anything from these two numbers.

---

# Appendix D — The BOVA direct-expansion zones

The kitchen (`BOS1`) and great room (`BOS2`) are Unico air handlers on Bosch BOVA inverter
condensers. They have no water side, so nothing in [Appendix C](#appendix-c--primarysecondary-hydraulics) applies to them. The air-side
instrumentation does, and for these zones it is most of the job.

All findings below are checked against the BOVA-36HDN1-M18M Installation Instructions, Bosch
Thermotechnology 06.2016, the model installed here.

## D.1 Measuring these zones

Two 10K NTCs in the supply and return plenums plus the commanded ECM airflow give measured
sensible capacity, `Q_sensible = 1.08 × CFM_commanded × ΔT_air`. Latent comes from the zone's
RedLink humidity, and the condenser's power is already metered, which supplies an EER
cross-check. No water plumbing and no flow meter.

Airflow drives capacity on these units because the compressor modulates on suction pressure. Low
airflow is self-reinforcing: less air over the coil lowers suction pressure, the compressor
modulates down, capacity falls, and the room drifts further. A zone can therefore read as
control-limited, with the compressor below maximum, and be airflow-limited at the same time.

| Air ΔT | Condenser power | Meaning |
|---|---|---|
| High | low | Airflow-starved, self-limiting through suction pressure |
| Normal | at max | Capacity-limited at these conditions |
| Low | low | Not calling, or short-cycling |

A thermistor clamped to the suction line is a cheap addition. A persistently cold suction line
with low airflow indicates starvation or freezing.

## D.2 `Y2` has no terminal on the condenser

`Y2` appears nowhere in the manual. The low-voltage hook-up, Figure 26, gives the terminal blocks
as:

| Block | Terminals |
|---|---|
| Outdoor unit | `C` `Y` `B` `D/W`, with B and D/W on heat-pump models only |
| Indoor unit | `G` `R` `C` `W1` |
| Thermostat | `W2` `B` `C` `R` `Y` `G` |

The condenser accepts one `Y`, a single 24 V cooling call. §15.1 states the unit "adopts the same
24VAC control as any conventional Heat Pump" and stages internally. It has no second-stage input.

> `Y2` belongs to the air handler. The thermostat's `Y2` drives the Unico blower's second-stage
> fan speed, which is how a second-stage call reaches the compressor: through air. More airflow
> puts more heat into the coil, raising evaporator pressure and ramping the compressor. A
> disabled `Y2` fan wire starves the coil on the hot days the second stage exists for, and the
> compressor answers by slowing down. Confirm `Y2` is connected and working at the air handler
> before diagnosing anything else on a BOVA zone.

## D.3 Suction pressure has one adjustment, and it is already set

Suction pressure is a dependent variable, set by load, airflow and charge, so it cannot be
managed directly to make the compressor work harder. The manual exposes the target it modulates
toward, §15.1, verbatim:

> "The compressor's speed is controlled based on coil pressures monitored by pressure
> transducer… the compressor speed will modulate relative to **evaporator pressure during cooling
> operation**… The target pressure can automatically adjust based on compressor operation so
> optimal capacity can be achieved. **Target pressure can manually be adjusted (SW4)** to achieve
> improved dehumidification and capacity demands."

`SW4` on the outdoor control board, Table 8:

| Switch | ON | OFF |
|---|---|---|
| SW4-1 | *Not used* | |
| SW4-2 | *Not used* | |
| SW4-3 | Adaptive capacity output disable | Adaptive capacity output enable |
| SW4-4 | Accelerated cooling/heating | Normally cooling/heating |

Both are already set on the great-room unit: SW4-4 accelerated on both units, and SW4-3 switched
on in July, after which its board display read 75 to 77 Hz. No third capacity switch exists, so
the compressor already runs as hard as the controls allow.

That relocates the problem. A unit at maximum commanded speed with a zone still drifting is
constrained downstream of the compressor, in refrigerant mass flow from charge or in evaporator
heat transfer from airflow. The subcooling check covers the first: the manual makes subcooling
the only recommended charging method above 55 °F outdoor ambient, with weigh-in below that, and
the target is 10 ± 2 °F.

## D.4 SW4-3 may be trading away the comfort you want

The manual ties SW4 to improved dehumidification and capacity demands, and those trade against
each other. Disabling adaptive capacity holds the target evaporator pressure higher, giving a
warmer coil and less moisture removal. The objective is comfort rather than raw sensible output,
so a great room sitting at 75 °F and humid could be worse off with SW4-3 on even as sensible
capacity rises.

The great room measured 53.4 % RH against the kitchen's 48.6 % over the same window, which is
consistent with that trade and short of proof.

This is testable. Both BOVAs have their own CT and RedLink logs per-zone humidity, so run SW4-3
off for a few comparable hot days and compare droop and humidity against the SW4-3 on period. If
droop holds steady while humidity falls, adaptive capacity was the better setting.

> The great room carries three sensible-biased settings at once: `Y2` fan connected, base CFM
> raised, and `SW4-3` on. All three trade latent for sensible in the same direction, so watch
> humidity there rather than temperature. If that zone holds setpoint while reading humid against
> the others, give `SW4-3` back first, since it costs the least capacity now that airflow is
> unconstrained.

## D.5 Airflow is the adjustment

Suction pressure is the load signal. Evaporator pressure settles where heat arriving at the coil
balances heat the compressor removes, so a hotter, wetter return raises evaporator pressure and
the control ramps the compressor up. That is a closed loop on actual thermal load, and it beats a
`Y2` contact, which only proxies load from room temperature.

The catch is that the loop sees load as delivered to the coil, `airflow × enthalpy difference`.
It cannot separate low load from ample load with too little air to carry it, since both present as
low suction pressure.

```
more CFM → more heat into the coil → higher suction pressure → compressor ramps up
```

Two paths deliver it and they stack. The thermostat's `Y2` selects the blower's second-stage speed
on a second-stage call, raising airflow only when the zone asks for more. The base CFM setting on
the Unico Smart Controller sets the floor both stages work from, in software, free and reversible.

> Do not raise suction pressure artificially. Overcharging or interfering with the pressure
> transducer raises the number without raising capacity, and the board runs low-pressure
> protection in cooling and compression-ratio protection off that same transducer, so a falsified
> signal defeats the protections. Feed the coil more heat rather than misreporting it.

## D.6 Static CFM sets where the compressor operates

The Unico blower and the BOVA compressor do not communicate. `Y2` couples the thermostat to the
blower, so airflow follows the thermostat's two-stage demand rather than the compressor's state.
The Smart Controller's only interface is USB, and the air handler pauses while fan speed changes,
which puts dynamic load-following airflow out of reach. Reverse-engineering the USB protocol would
not help, because the pause is the blocker.

The compressor is the only dynamic element in the pair, so the static CFM setting decides where in
its modulation range the compressor lives. Higher CFM raises suction pressure, so the compressor
runs faster and makes more sensible capacity at a warmer coil with less dehumidification. Lower
CFM does the reverse.

That converts an open-ended control problem into a finite tuning exercise over two static
settings, both free to change, with measurable outcomes.

| Setting | Options | Effect |
|---|---|---|
| Unico CFM | a few settings via USB | Sets the compressor's operating point |
| SW4-3 | ON / OFF | Adaptive capacity disabled or enabled |

Evaluate each combination on droop and humidity over comparable hot days, both already logged per
zone.

> CFM is therefore a seasonal setting, like Loop B's pump tap. Peak summer wants more airflow for
> maximum sensible with the compressor pushed high, and shoulder season wants less for better
> dehumidification at part load. A USB change twice a year is practical even though a dynamic one
> is not, and it belongs on the seasonal list that already holds the pump tap and the glycol
> top-up.

**Source:** [BOVA-36HDN1-M18M Installation Instructions, Bosch, 06.2016](https://blobanarus.blob.core.windows.net/boschthermotechnology-boschproducts/BOVA-36HDN1-M18M_Installation_instructions.pdf)

---

# Appendix E — Air-handler node build specification

Build this only after the loop sensors and the primary flow meter, which cost less and answer
larger questions ([8](#8-sequence)). It remains the only route to attribution within a loop and to
the sensible and latent split at a single coil.

## E.1 Everything hangs off one Arduino at the air handler

All sensors go on the node rather than split between the node and the Pi's 1-wire bus, for three
reasons.

Simultaneity comes first. `Q = K × GPM × ΔT` holds only if flow and both temperatures are sampled
at the same instant, and two collectors polling on different schedules cannot deliver that.

Cable length comes second. 1-Wire is finicky over long runs, and the Pi's bus has a documented
history of the OUT sensor dropping off for hours. A 30 cm run inside the air-handler cabinet
carries none of that risk.

Precedent comes third. The DHW board at 10.0.0.114 already runs a DS18B20 on an UNO R4 alongside
its analog sensor, so the pattern is proven on this system.

One board per air handler, DHCP-reserved by MAC in UniFi like the others. **Build the first one at
the master bedroom.** That is the coil the fourth question is about, it is the least-fed on the
system ([5.6](#56-what-the-calculation-says-about-each-coil)), and it is the only place where the
water, the air and the fan stage can be read against each other at the same instant.

## E.2 Bill of materials

| Qty | Item | Notes |
|---|---|---|
| 1 | Arduino UNO R4 WiFi | Same as every other pivac node; the 14-bit ADC suffices |
| 2 | DS18B20, stainless probe | Water supply and return, waterproof probe version |
| 2 | Brass thermowell or pipe clamp with insulation | See [E.3](#e3-water-temperature-thermowell-against-strap-on) |
| 1 | 4.7 kΩ resistor | 1-Wire pull-up, DQ to 5 V. External, not the internal pull-up |
| 2 | Honeywell 10K NTC duct sensors | Already on hand. Supply and return air |
| 2 | 10.0 kΩ 0.1 % metal-film resistor | Divider reference. Tolerance becomes temperature error |
| 2 | 0.1 µF ceramic | ADC anti-alias, across the NTC leg |
| 1 | Water flow sensor, pulse output | [E.5](#e5-water-flow-sensor-selection) |
| 1 | 24 VAC opto-isolator module, or a 24 VAC coil relay | Y2 sense. See [E.9](#e9-sensing-the-y2-call) |
| 1 | 5 V PSU or USB supply | Consider the Arduinos Shelly |
| — | Pipe insulation, cable glands, enclosure | |

Optional: one SHT41 or SHT31 I²C temperature and humidity sensor for return-air humidity. Probably
unnecessary, since the IAQ thermostat supplies it through RedLink
([G.3](#g3-humidity-is-probably-already-available)). Measure before buying.

## E.3 Water temperature: thermowell against strap-on

A thermowell is the correct method and a strap-on is acceptable with proper insulation.

A brass thermowell, ½" NPT into a tee, puts the probe in the stream and reads fast and
unambiguously. It requires cutting the pipe and draining that section of a glycol loop.

A strap-on clamps the DS18B20 to bare, cleaned copper with thermal compound, then buries it under
at least 25 mm of insulation extending 100 mm either side. On copper at these flow rates it reads
within a few tenths of a °F of the fluid. Skimping on insulation ruins strap-on installs: an
uninsulated probe reads somewhere between the water and the room, and the error differs on the hot
and cold pipes, which is the worst case for a ΔT.

Draining a glycol loop is a chore, so strap-on with thorough insulation is the pragmatic choice,
provided you run the in-situ pair calibration in
[G.1](#g1-matched-pair-calibration-before-install), which measures and removes this class of
installation error.

Mount both probes on straight pipe, at least 5 diameters downstream of any fitting, as close to the
coil connections as possible, so the measurement covers the coil rather than the piping run.

## E.4 Air temperature: reading the 10K NTCs

Standard ratiometric divider, one per sensor:

```
 5V ──[ 10.0 kΩ 0.1% ]──┬── A0  (and A1 for the second)
                        │
                     [ 10K NTC ]
                        │
                       GND         0.1 µF from A0 to GND
```

The ratiometric arrangement is the point. The divider is fed from the same 5 V the ADC uses as its
reference, so supply variation cancels. Do not add a separate precision reference.

Set `analogReadResolution(14)` on the RA4M1. Near room temperature the divider gives about 31
mV/°F against a 0.305 mV LSB, roughly 0.01 °F per count, so noise dominates rather than
resolution. Average 100 to 256 samples per reported reading. Convert with Steinhart-Hart or a
beta fit using the curve confirmed by the ice-bath test in [B.3](#b3-delta-t-precision-sets-the-accuracy-of-every-capacity-figure), keeping the coefficients in
firmware as sensor-physics constants and the per-sensor offset in config. Self-heating is
negligible in a moving airstream, about 0.6 mW in a 10 kΩ leg.

Probe placement matters more than probe accuracy. Put the return sensor in the return plenum
upstream of the coil, out of line of sight of the coil face. Put the supply sensor in the supply
plenum downstream of the blower and before the first takeoff. On a Unico the blower does the
mixing, and a sensor at the coil face reads a stratified, unrepresentative slice. Shield both
from radiation, since a sensor that can see a 45 °F coil reads low regardless of air
temperature. In cooling the supply sensor sits in roughly 95 % RH air, so seal the probe body
and route the leads downward to stop condensate wicking into the cable.

## E.5 Water flow sensor selection

Sizing, for an M2430 at a nominal 2 tons:

```
24,000 BTU/hr ÷ (481 × 10 °F ΔT) ≈ 5 GPM
```

Specify for 3 to 8 GPM in ¾" to 1" pipe, with 25 % glycol, over a service range spanning chilled
duty near 45 °F and heating duty up to about 140 °F. That temperature span rules out most domestic
water meters.

| Option | Cost | Verdict |
|---|---|---|
| Hydronic paddlewheel or turbine with pulse output: Seametrics SPX, Omega FTB, Onicon F-1100, brass or stainless, rated 200 °F or above | $200–400 | Recommended. Rated for the fluid, the temperature and continuous duty |
| Brass-body hall turbine, Digiten or Gredia class, 212 °F rated | ~$25 | Workable budget path. Plastic rotor and bearing wear plus calibration drift in continuous hot glycol are the risks. Re-verify annually against the energy balance |
| Clamp-on ultrasonic | high | No plumbing cut and glycol-agnostic. Best if you would rather not open the loop |
| DAE MJ-75a class, as on the domestic meter | ~$60 | Unsuitable. Nutating-disc domestic meters are rated to about 120 °F and are not intended for closed-loop glycol |

> A cheap hall turbine failed on the irrigation line, and the root cause was a mismatch with
> OpenSprinkler's pulse-rate handling above 50 Hz rather than a defect in the sensor class. On a
> dedicated Arduino ISR a high pulse rate is an advantage, since it supplies instantaneous flow
> resolution. Rule out plastic turbines on temperature and duty cycle, and keep metal ones in
> consideration.

## E.6 Whether a per-coil meter is needed depends on the loop

| If the instrumented coil is… | Cooling season | Winter | Verdict |
|---|---|---|---|
| Lower family room, Loop B | Single-zone loop, flow constant | Shares Loop B with kitchen and great room | Start without a meter. Measure GPM once, run all cooling season on a constant, add the meter before winter if the data warrants |
| Kids room or master bedroom, Loop A | Shares with the other, and both call together on hot days | Same | Buy the meter. Per-zone flow varies exactly when it matters |

Sharing matters on Loop A because two zone valves on one fixed-speed circulator are hydraulically
coupled. Opening the second valve lowers loop head, so flow through the first coil drops. Per-zone
GPM becomes a function of whether the other zone is calling, and it reaches its minimum on design
days when both run together.

One cheap test settles it either way. At a steady outdoor condition, log a coil's ΔT_water with one
zone calling, then with both. A material rise in ΔT at the same entering water temperature means
the zones share flow. An afternoon decides a $200 to $400 purchase.

The three-speed tap acts per loop rather than per zone. It changes total loop flow, raising or
lowering every zone together, and cannot redistribute between them.

## E.7 Pin map

| Signal | Pin | Notes |
|---|---|---|
| DS18B20 ×2, water supply and return | D2 | One shared 1-Wire bus, addressed by ROM. 4.7 kΩ to 5 V |
| Flow sensor pulse | D3 | Interrupt-capable. Debounce in the ISR |
| Return-air NTC | A0 | Divider per [E.4](#e4-air-temperature-reading-the-10k-ntcs) |
| Supply-air NTC | A1 | Divider per [E.4](#e4-air-temperature-reading-the-10k-ntcs) |
| Y2 call sense | D6 | 24 VAC through an opto or a relay contact, never to the pin directly. See [E.9](#e9-sensing-the-y2-call) |
| SHT41 temperature and humidity, optional | A4/A5 | I²C |

Avoid D0/D1 (Serial1), D4/D5 (CAN) and D10 to D13 (SPI). The free general-purpose pins on the R4
are D2, D3, D6, D7, D8 and D9, and this design uses three.

**Record both DS18B20 ROM addresses in this document during the build.** The printed tags on these
probes are unreliable as physical identifiers, one probe having been found carrying two tags, and
the .114 board's DS18B20 ROM exists in neither repo.

## E.8 Firmware contract

The Arduino emits raw measurements and computes no BTUs. The DHW board's recirc-temperature sketch
was never committed and exists only on the M2 MacBook, so reflashing that board would silently
drop a sensor. Calibration offsets, the glycol constant `K`, and the capacity arithmetic all belong
in `config.yml` and Python, where they are version-controlled and deploy with a `git pull`.

The response dict matches the single-quoted pseudo-JSON convention `ArduinoSensor` parses with
`ast.literal_eval`:

```
{'wsup' : 118.42, 'wret' : 108.31, 'asup' : 96.10, 'aret' : 70.44,
 'flow' : 4.92, 'volume' : 10432.5, 'y2' : 1, 'uptime_ms' : 84213}
```

| Field | Unit | Meaning |
|---|---|---|
| `wsup` | °F | Water entering the coil |
| `wret` | °F | Water leaving the coil |
| `asup` | °F | Supply, or leaving, air |
| `aret` | °F | Return, or entering, air |
| `flow` | gal/min | Rolling-window instantaneous flow |
| `volume` | gal | Lifetime totalizer, EEPROM-persisted |
| `y2` | 0 or 1 | Second-stage call present at the air handler. See [E.9](#e9-sensing-the-y2-call) |
| `uptime_ms` | ms | A low value means a recent reboot, the same power-event diagnostic the pressure boards use |

Emit two decimal places on every temperature. The precision has to survive as far as the delta.

Reuse the scaffolding proven in `DomesticWater.ino`: a D-pin pulse interrupt with debounce, an
EEPROM totalizer with a magic marker, a 10 s rolling flow window, the RA4M1 watchdog, and bounded
WiFi and HTTP handling. Add the 12-bit DS18B20 read and the two averaged ADC reads.

Handle disconnected sensors explicitly. A DS18B20 that fails to read returns −127, and an open NTC
divider rails to full scale. Emit a −999 sentinel rather than a plausible number, so the Pi can
drop the sample instead of computing a confident and wrong figure.

## E.9 Sensing the Y2 call

Y2 is 24 VAC, so it never reaches a digital pin directly. Two ways to land it, and the choice is
about what else is in the cabinet.

An **AC opto-isolator module** is the smaller of the two: a bridge, a current-limiting resistor and
an optocoupler, its output pulled to a digital input. It gives galvanic isolation between the 24 VAC
control transformer and the Arduino, which matters because the node's ground reaches mains through
its own supply.

A **24 VAC coil relay** with dry contacts is the alternative, and it is the same part the Pi route
uses ([4.6](#46-reading-the-master-bedrooms-fan-stage)). It is bulkier and it clicks, and it is
legible to anyone who opens the panel in five years, which counts on a control nobody will remember
adding.

**Debounce in time rather than in hardware.** A bare opto follows the waveform and drops out twice a
cycle, so the input reads a 120 Hz square wave instead of a level. Sample it across a window and
report the call present when any sample in the last 100 ms was high, or fit an RC filter with a time
constant well above 8.3 ms and read a level. Either works. The failure is reading the pin once per
loop and reporting whichever phase the waveform happened to be in.

Report `y2` as 0 or 1 rather than as a duty figure. The Pi polls every few seconds and the
integration belongs in Grafana, where the denominator already exists.

> **Sense Y2 only.** `pivac.RedLink` already publishes a cooling call for every zone as `statenum`
> at −1, which is the denominator of the Y2 fraction
> ([4.6](#46-reading-the-master-bedrooms-fan-stage)). One new wire yields both terms.

---

# Appendix F — pivac integration

## F.1 `pivac.ArduinoSensor` needs a `rounding:` key

`ArduinoSensor` hardcodes `int(round(...))` on every `type: temperature` field
(`pivac/ArduinoSensor.py:65`), so it quantises to whole Kelvin, 1.8 °F. This project rests on ΔT
values of 10 to 20 °F, so that destroys the measurement before it reaches Signal K.

Add an optional per-input `rounding:` key defaulting to `0`, which leaves every existing input
byte-for-byte unchanged:

```python
digits = scfg.get("rounding", 0)
k = _to_kelvin(raw, scfg.get("scale", "fahrenheit"))
kelvin = int(round(k)) if digits == 0 else round(k, digits)
```

This mirrors `pivac.OneWireTherm` (`pivac/OneWireTherm.py:113`), which has carried the same
per-sensor `rounding` key all along. The DHW recirc input keeps `rounding: 0` and its InfluxDB
series stays undisturbed. New inputs use `rounding: 2`.

## F.2 `pivac.UnicoAH` wraps `ArduinoSensor`

The pattern follows `pivac.DomesticWater`: call through for the raw fields, then append derived
values. All physics stays in Python and all constants stay in config.

```
ΔT_water  = wsup - wret                       (°F, sign follows mode)
ΔT_air    = asup - aret
Q_total   = K × GPM × |ΔT_water|              (BTU/hr)
Q_sens    = 1.08 × CFM × |ΔT_air|             (BTU/hr)
SHR       = Q_sens / Q_total                  (cooling only)
UA        = Q_total / |aret - wsup|           (BTU/hr·°F, the fouling metric)
running   = flow > flow_threshold             (0/1)
```

Gate everything on `running`. A ΔT computed on a dead coil is noise, and a UA computed on a
near-zero denominator is a divide-by-zero waiting to happen. Emit zero or null for the derived
values while the coil is off. Suppress the first 5 minutes after a start, because the coil, the
water in it and the duct mass all need to reach steady state.

## F.3 Signal K paths

> Name these carefully. The Signal K path becomes the InfluxDB measurement name, and four prior
> renames each orphaned their history. Adding a second air handler later must not force a rename
> of the first, which is why the path carries a `<unit>` level.

| Path | Unit | Source |
|---|---|---|
| `environment.inside.hvac.ah.mbr.water.supply.temperature` | K | node |
| `environment.inside.hvac.ah.mbr.water.return.temperature` | K | node |
| `environment.inside.hvac.ah.mbr.air.supply.temperature` | K | node |
| `environment.inside.hvac.ah.mbr.air.return.temperature` | K | node |
| `environment.inside.hvac.ah.mbr.water.flowRate` | gal/min | node |
| `environment.inside.hvac.ah.mbr.water.consumption` | gal | node, totalizer for drift checks |
| `environment.inside.hvac.ah.mbr.water.deltaT` | °F | derived |
| `environment.inside.hvac.ah.mbr.air.deltaT` | °F | derived |
| `environment.inside.hvac.ah.mbr.capacity.total` | BTU/hr | derived |
| `environment.inside.hvac.ah.mbr.capacity.sensible` | BTU/hr | derived |
| `environment.inside.hvac.ah.mbr.capacity.ua` | BTU/hr·°F | derived |
| `environment.inside.hvac.ah.mbr.shr` | ratio | derived |
| `environment.inside.hvac.ah.mbr.running` | 0/1 | derived |
| `environment.inside.hvac.ah.mbr.y2` | 0/1 | node, only if the spare pair is open |

> If the spare pair rings out, Y2 arrives through `pivac.GPIO` instead, as
> `electrical.ac.switch.utility.MBY2.statenum` beside the seven relays already there
> ([4.6](#46-reading-the-master-bedrooms-fan-stage)). Choose one and keep it. Publishing the same
> signal on both paths would split its history the day the other is retired.

The four secondary-loop sensors in [4.2](#42-the-sensor-package) go on the Pi's
1-wire bus instead, under `environment.inside.hvac.{LOOPA_SUP,LOOPA_RET,LOOPB_SUP,LOOPB_RET}`.

> A ΔT must never pass through `type: temperature`. That branch adds 273.15, which is correct for
> an absolute temperature and destroys a difference. Emit the deltas as plain untyped numbers from
> the wrapper module. A `deltaT` of 10 °F arriving in InfluxDB as 283.15 looks like a plausible
> temperature and survives review.

## F.4 Config sketch

```yaml
pivac.UnicoAH_MBR:
    description: Unico M2430 hydronic air handler capacity monitoring
    module: pivac.UnicoAH
    enabled: true
    ipaddr: 10.0.0.xxx
    daemon_sleep: 15
    sk_path: environment.inside.hvac.ah.mbr

    # --- physics constants (Appendix B.2) ---
    fluid_k: 481.0          # 25% PG; ~476.0 after the 30% top-up
    nominal_cfm:            # commanded airflow from the Unico Smart Controller
        cooling: 900
        heating: 800
    flow_gpm_fixed: null    # set a number for the constant-flow shortcut
    flow_threshold: 0.5     # gal/min below which the coil counts as off
    settle_seconds: 300     # ignore the first 5 min of a call

    # --- per-sensor calibration offsets, °F (Appendix G.1) ---
    offsets:
        wsup:  0.00
        wret: +0.14         # measured, not guessed
        asup:  0.00
        aret: -0.09

    inputs:
        wsup:
            sk_path: environment.inside.hvac.ah.mbr.water.supply
            outname: ""
            type: temperature
            scale: fahrenheit
            rounding: 2     # required, see F.1
        # ... wret / asup / aret identically
        flow:
            sk_path: environment.inside.hvac.ah.mbr.water
            outname: flowRate
```

---

# Appendix G — Calibration and analysis methods

## G.1 Matched-pair calibration, before install

This turns a ±18 % measurement into a ±1 % one
([B.3](#b3-delta-t-precision-sets-the-accuracy-of-every-capacity-figure)), so it is required.

1. Wire all sensors to the board on the bench, running the final firmware.
2. Bundle the two water probes together in a stirred bath. An insulated jug of water serves;
   stability matters far more than knowing the true temperature.
3. Log for at least 15 minutes at the production sample rate, and take the mean difference rather
   than a spot reading.
4. Repeat at a second temperature spanning the working range, ice water and hand-hot, to learn
   whether the offset holds constant or drifts. Fit a slope instead of a constant if it drifts
   materially.
5. Repeat steps 2 to 4 for the two air NTCs.
6. Write the offsets into `offsets:` in config. Keep them out of firmware, because they need
   annual re-verification.

Acceptance: with offsets applied, two water probes in a common bath should agree within 0.1 °F.

The four secondary-loop DS18B20s and the existing `IN` and `OUT` pair need the same treatment. The
flow-ratio method in [C.2](#c2-the-flow-ratio-falls-out-of-temperatures-alone) is a ratio of two
small differences, and it is the analysis most sensitive to an uncalibrated pair.

## G.2 CFM is commanded, which turns the energy balance into a diagnostic

The Unico Smart Controller's ECM is configured in software, so read the commanded airflow per mode
off the controller and put it in `nominal_cfm`. Sensible capacity then needs no derivation.

The energy balance serves a different purpose. Heating carries no latent load, so the two sides
must agree and the balance solves for airflow:

```
CFM_derived = (K × GPM × ΔT_water) / (1.08 × ΔT_air)      [heating only]
```

Track `CFM_derived / CFM_commanded` as a first-class series.

| Ratio | Meaning |
|---|---|
| ≈ 1.0 | The measurement chain is validated end to end: flow-meter calibration, all four temperature offsets, and the blower agree. This doubles as the acceptance test for the build |
| Drifting down over weeks | The ECM is losing its fight with static pressure, from a dirty filter or a developing duct restriction. This is the early warning the ECM otherwise hides |
| Sudden step | Something changed physically: a filter swap, a damper position, a sensor knocked loose, or the controller reconfigured |
| Persistently off 1.0 from day one | A calibration error rather than a fault. Suspect the flow meter's K-factor first, then the temperature offsets |

Capture the commanded CFM per mode. A Smart Controller is typically configured with different
airflow for heating and cooling, and possibly per stage, so `nominal_cfm` should be a small map
keyed by mode rather than one number.

Two minor caveats: air density differs by about 5 % between 110 °F and 55 °F supply air, and the
balance assumes steady state, which [G.5](#g5-sampling-discipline) enforces.

## G.3 Humidity is probably already available

Entering-air wet bulb drives a chilled-water coil's capacity and splits total capacity into
sensible and latent. It needs entering dry bulb, available at full precision from the `aret` NTC,
plus entering RH.

The IAQ thermostat supplies the RH. `pivac.RedLink` publishes
`environment.inside.thermostat.<ZONE>.humidity` for every zone today (`pivac/RedLink.py:331`, as a
0 to 1 fraction). Return air is room air, so the zone thermostat's RH proxies entering-air RH
well; the error comes from duct leakage and infiltration into the return rather than from the
model.

Combining the `aret` dry bulb with the RedLink humidity for the same zone gives entering
enthalpy. That supplies three things:

- a true SHR and latent split, independent of the stored CFM;
- a CFM derivation that works in cooling through `Q_total = 4.5 × CFM × Δh`, where
  [G.2](#g2-cfm-is-commanded-which-turns-the-energy-balance-into-a-diagnostic) works only in
  winter;
- the physically correct denominator for coil performance in
  [G.4](#g4-what-maximum-capacity-means).

Two caveats. Take temperature from the node's own NTC and only humidity from the thermostat, since
RedLink temperatures now carry two decimals and still lag the node, and the thermostat itself
reports whole degrees. RedLink also polls on its own schedule with a documented 15 to 25 %
per-device timeout rate, so the humidity series is coarser and gappier than the node's own data.
Interpolate and tolerate gaps rather than dropping the sample.

Add an SHT41 in the return plenum only if that proves inadequate, and measure first. Supply
humidity is not proposed either way: off a wet coil that air sits at 90 to 98 % RH, which is hard
to measure accurately and hard on the sensor.

## G.4 What maximum capacity means

Capacity depends on five things: entering water temperature, water flow, air flow, entering air wet
bulb, and coil cleanliness. Raw BTU/hr is therefore not a target, since it varies with weather. Two
normalised metrics work better.

UA is the fouling and health metric:

```
UA = Q_total / |T_return_air − T_water_supply|
```

This divides out both the weather and the plant, leaving coil effectiveness. At a given GPM and
CFM, UA should hold constant. Plotted over months, a steady decline means fouling, either air-side
dirt or water-side scale, and it is the clearest available signal that the coil is degrading.

Capacity against the manufacturer's rating is the second. Pull the Unico coil rating table at your
entering water temperature, GPM and CFM and compare. That answers whether you fall short of design,
a separate question from whether you fall short of last year.

Then apply the [B.4](#b4-the-two-deltas-move-in-opposite-directions) table. Sort the steady-state
samples by capacity, take the worst decile, and find which delta is anomalous.

## G.5 Sampling discipline

Gate on `running` and discard the first 5 minutes of every call, or startup transients will
dominate the dataset while representing nothing.

Aggregate to 1 to 5 minute means before analysis. Instantaneous BTU/hr is noisy and nothing in this
problem changes quickly.

Collect at least one full heating and one full cooling season before drawing conclusions about
fouling. UA drift is a slow signal, and a month of data cannot separate it from seasonal variation.

Condition every water-side conclusion on plant output. A ΔT figure taken without knowing whether
the chiller was at 30 % or 100 % is uninterpretable
([5.1](#51-primary-flow-is-fixed-so-primary-delta-t-reads-house-load)).

---

# Appendix H — Utility-room instrumentation

The air handler measures whether one coil is delivering. The mechanical room measures whether the
plant is healthy, and several of those sensors cost less and return more than the coil node.

## H.1 Tier 1

| Sensor | Where | Why |
|---|---|---|
| 4× DS18B20, supply and return on each secondary loop | Loop A and Loop B, at the tees | Starvation, flow ratios, mixing, loop-idle detection. The highest-value addition in this document ([4.2](#42-the-sensor-package)) |
| 1× DS18B20, chiller leaving water | Chiller outlet | The reference that makes distribution loss absolute. The redundant `LBT` probe can be relocated here at no cost ([7.1](#71-costs-nothing)) |
| 1× DS18B20, boiler return | Boiler return, before the primary tee | Condensing verification. Monitor-only |
| 1× temperature and humidity sensor | Mechanical room, away from the boiler | Standby losses, and the Pi's thermal ceiling |
| Leak and flood detection | Pan under boiler, buffer tank, booster pump | Closes a regression |

Boiler return temperature is worth recording and not worth chasing. A Trinity Ti-200 condenses only
when return water sits below the flue-gas dew point, roughly 130 °F. Above that it loses most of
the condensing gain, on the order of 10 % efficiency. Hydronic air-handler coils are commonly
designed around 140 to 180 °F supply, which puts return water above the threshold, so this boiler
may never condense in this application. Confirming that would point to outdoor reset, which trades
coil capacity for efficiency. Capacity is the priority and heating is rarely the problem, so record
the number and leave it alone.

Room ambient explains a documented problem. The Pi is a fanless Pi 4 running at about 76 °C with
83 °C peaks during Sentry capture bursts, grazing the 80 °C soft-temp limit. Ambient boiler-room
heat is the suspected contributor, and nothing measures it. A room temperature series turns that
from hypothesis into correlation. Humidity comes free with the same sensor: a mechanical room
that runs humid in summer carries mould and corrosion risk, and flags chilled-pipe sweating from
insulation gaps.

> Leak detection was lost rather than retired. BCM 25 carried the booster-pump leak pan as `SCALA`
> until 11 August 2026, when the input was renamed in place to `CHIL` to sense the chiller call.
> A room holding the boiler, buffer tank, DHW, booster pump and the domestic water main now has no
> water detection. Free GPIO inputs with existing wire runs are BCM 13/33, 16/36 and 24/18. Avoid
> BCM 26, a permanently dead pad.

## H.2 Tier 2

| Sensor | Why |
|---|---|
| Flow meter on the primary loop | Whole-house delivered capacity, system COP, boiler delivered-against-fired efficiency. Converts every ratio in [C.2](#c2-the-flow-ratio-falls-out-of-temperatures-alone) into an absolute number |
| 1× DS18B20, Chiltrix entering water | With the leaving-water probe above, chiller-side ΔT and therefore chiller COP directly, separate from distribution losses. Skip if the CX75 exposes them over Modbus |
| CTs on the circulators | Definitive pump-running state, better than inference, plus pump energy accounting. A failing circulator shows as changed draw. Needs spare Emporia channels, and four CTs were borrowed from the apartment panel for the Chiltrix |

## H.3 Tier 3

| Sensor | Why |
|---|---|
| Differential-pressure transducer across a secondary loop | An alternative to a flow meter: read ΔP and look up flow on the pump curve. Often taps existing ports, so no pipe cutting |
| Boiler flue temperature | Direct efficiency indicator, complementing the condensing check |
| Condensate trap float switch | A blocked trap shuts a condensing boiler down, and it fails at the worst time of year |
| CO detector with a monitored contact | Safety rather than optimisation, and the GPIO inputs already exist |

## H.4 Wiring

Tier 1's DS18B20s go on the Pi's existing 1-wire bus, taking it from 4 sensors to 10, well within
1-Wire's addressing limits. Watch total cable length and topology: prefer a daisy chain over a
star, and consider dropping the pull-up to 2.2 to 3.3 kΩ as the bus grows, which §5 of
`docs/circ-loop-temp-monitoring-plan.md` covers. `pivac.OneWireTherm` re-scans every cycle since
2026-07-06, so sensors added live appear within one daemon cycle and need no restart.

The temperature and humidity sensor and the leak detector are not 1-Wire. RH wants I²C, so it
belongs on an Arduino or a small dedicated node, and a leak pan is a dry contact into a spare GPIO.

> While editing the 1-wire config block, note the `0316a015e7ff: Unassigned` entry. It is the ROM
> of the DS18B20 on the .114 DHW Arduino, which is not on the Pi's bus. `OneWireTherm` iterates
> found sensors and looks names up, so it is harmless, and it misleads beside ten real entries.

---

# Appendix I — Operational integration

**Freshness alerts.** Add rules to `grafana/provisioning/alerting/sensor-freshness.yaml`
following the existing pattern: 30 min staleness, `noDataState: Alerting`, and a never-true
sentinel for the threshold. Temperatures publish in Kelvin, so reuse the `value < 100` sentinel.
`flowRate` is never negative, so use `value < -1`, the shape `domestic-water-stale` already uses.

**Removing a rule needs an explicit `deleteRules:` block.** Provisioning is additive, so deleting a
rule from the YAML leaves it evaluating with `provenance=file` indefinitely. Verify the
`alert_rule` table after any removal rather than trusting the restart.

**Design-day saturation alert.** Chiller power sustained near 3,537 W with droop above zero on more
than one zone is the plant running out of capacity ([7.1](#71-costs-nothing)). Both series already
exist.

**Watchdog.** `scripts/arduino-watchdog.sh` pings only `.114` and `.219` and power-cycles the
shared Arduinos Shelly at `10.0.0.61`. An air-handler board will sit on a different circuit,
leaving it without auto-recovery. Either extend the watchdog with a second plug or accept
alert-only coverage and record that choice.

**Grafana.** Follow the house conventions: `custom.axisWidth: 50` on every timeseries, no
per-panel `axisLabel`, and stepped-line timeseries rather than state-timeline for boolean series,
since state-timeline cannot set row-label width and will not align. A loop panel wants both loop
ΔTs and the primary ΔT on one axis, which makes the flow ratio readable by eye.

**Restart order.** Config edit, then restart the pivac service, then restart `signalk`. Signal K
freezes retired paths at their last value until the server restarts, which is documented three
times over for relays, 1-wire and Emporia. Adding paths needs no Signal K restart; only removing
them does.

---

# Appendix J — The master bedroom thermostat

The zone runs a Honeywell **THX9421R5021WW**, the Prestige IAQ 2.0 with an Equipment Interface
Module, rated for up to 3 heat and 2 cool stages on a conventional system. Installer options are
reached with MENU > INSTALLER OPTIONS and the date code printed on the back of the thermostat, which
MENU > EQUIPMENT STATUS also shows. VIEW/EDIT CURRENT SETUP reads one setting without walking the
whole CREATE SETUP sequence.

## J.1 What the cloud already reports

`pivac.RedLink` reads Honeywell's Total Connect payload, and these values came from it on 19 August
2026. They cost nothing and they frame everything below.

| Zone | Temp | Cool setpoint | RH | Auto deadband | Fan mode | System mode |
|---|---|---|---|---|---|---|
| Master bedroom | 76 °F | 76 °F | 50 % | 5 °F | **circulate** | auto |
| Kids room | 74 | 74 | 52 | 5 | auto | auto |
| Downstairs family | 76 | 76 | 48 | 3 | circulate | auto |
| Kitchen | 76 | 76 | 48 | 3 | circulate | cool |
| Great room | 75 | 75 | 51 | 5 | on | cool |

Every zone carries a dehumidification setpoint of **55 % RH** against a 40 to 80 % range. The master
bedroom peaks at 60 % ([3.3](#33-humidity-is-the-marginal-axis)), so either that setpoint is not
acting or the equipment behind it is not configured. ISU 9000 decides which.

**The payload carries no stage information.** `EquipmentOutputStatus` resolves to off, heat or cool
and nothing finer, and `fanData` reports the user's fan mode rather than the speed the blower runs.
That is why Y2 needs a wire ([4.6](#46-reading-the-master-bedrooms-fan-stage)).

**Fan circulate runs the blower between calls**, moving room air across a coil still wet from the
last call and returning that moisture to the room. Three of the five zones are set this way,
including this one. Changing it is free and reversible.

## J.2 Settings to read, and what each would mean

| ISU | Setting | Why it matters here |
|---|---|---|
| **3010** | Temperature Control Options, Basic or Advanced | Read this first. On Basic, 3020, 3030 and 3140 are not displayed at all |
| **3020** | Finish With High Cool Stage | If yes, stage 2 holds to setpoint once anything upstages, which inflates Y2 fraction on a zone with capacity in hand |
| **3030** | Staging Control, Cool Differentials | How far above setpoint stage 2 engages. A small differential upstages a zone that would have held |
| 3140 | Cool Cycles Per Hour | A high rate shortens cycles, and short cycles upstage sooner |
| 2070–2090 | Cool/Compressor Stages | Confirms the zone is configured for two-stage cool at all |
| 3240 | Minimum Compressor Off Time | |
| 3260 | Extended Fan Run Time in Cool | Run-on after a call re-evaporates condensate, the same effect as fan circulate |
| **9000** | Dehumidification Equipment | A/C with Low Speed Fan, A/C with High Speed Fan, or Whole House Dehumidifier. Decides whether the 55 % setpoint does anything |
| 9050 | A/C with Low Speed Fan Setup | Which U terminal, normally open or normally closed |
| **9070** | Dehumidification, Overcooling Limit | 0 to 3 °F. At 0 the thermostat never overcools to dry the room |
| 9120 | System Modes Allowing Dehumidification | |
| 9140 | Dehumidifier Lockout | |

> **Honeywell ties the two questions together.** On the low-speed-fan option the manual states that
> the thermostat will not lower the fan speed while the second stage of cooling is on. If 9000 is
> set that way, every minute this zone spends on Y2 is a minute it cannot dehumidify by that route,
> and it is the zone with the highest humidity in the house
> ([5.10](#510-why-the-master-bedroom-calls-its-high-fan-stage)).

## J.3 Air-side sensing the thermostat can do, and why it is not enough

The Prestige IAQ accepts a **return air sensor** (ISU 5070, 5080) and a **discharge air sensor**
(ISU 5090, 5100), and computes Delta T diagnostics from them (ISU 13010), alerting when the system
drifts outside limits learned during an installer test. Two things stop that from replacing the
sensors in [4.4](#44-air-side-sensors-on-one-air-handler). The manual restricts Delta T diagnostics
to non-zoned forced-air systems. And the result lands in the thermostat's own alert log rather than
in Total Connect, so pivac cannot read it and nothing reaches InfluxDB. It is a cross-check during a
service visit and not a data feed.

---

# Appendix K — The previous plant and the Chiltrix controls

## K.1 The Unico UniChillers

Two 5-ton Unico UniChillers served the house until 4 July 2026, one running at a time this season.
They pumped chilled water into the primary loop from a pump at the chiller, with no buffer tank
between plant and distribution.

They were on/off machines under a Digital Temperature Controller:

| Setting | Meaning | Set here | Guide's start-up recommendation |
|---|---|---|---|
| `S2` | Cooling setpoint, on **leaving** water | 38 °F | 44 °F |
| `DIF 2` | Cooling differential | 10 °F | 10 |
| `C2/H2` | Mode select | C2, cooling | |

The plant therefore cut out at 38 °F and back in at 48 °F, and the loop ran a sawtooth between them.
Unico puts the floor at exactly that setpoint: adjust the controller "no lower than 38 °F for
cooling". The logged distribution agrees, `IN` running a 38.4 to 45.9 °F fifth-to-95th percentile
while the master bedroom called ([3.8](#38-the-previous-plant-is-a-controlled-comparison)).

## K.2 How the Chiltrix differs

| | UniChiller | Chiltrix CX75 |
|---|---|---|
| Capacity control | On/off | Inverter, modulating |
| Sensed water | Leaving | **Return** |
| Set here | 38 °F leaving | **50 °F return** |
| Differential | 10 °F | 2 °C, restarting near 53.4 °F |
| Delivered band | 38 to 48 °F | 50 to 53.4 °F |
| Nominal capacity | 5 tons, one running | 4.3 tons |
| Separation | None; pumped into the primary | Four-pipe buffer tank |

The return-water target is the part that surprises, and Chiltrix documents it plainly: "for heating
and cooling, the set target refers to the return water temperature, in steady-state operation, the
leaving temper will be +/= 5C (9F). The normal cooling set target is 53F which implies a leaving
steady-state temperature of 44F." Because the buffer tank is fully mixed, the tank settles near the
target and the house sees the target rather than the leaving temperature.

## K.3 The parameters that matter

Read and set at the controller's LCD. The CX75's P and C codes match its controller display for every
value of interest here, which is what makes the Modbus map in [4.2](#42-the-sensor-package)
verifiable against the panel.

| Code | Function | Range | Factory | Note |
|---|---|---|---|---|
| **P109** | Cooling inlet target range | `0`: 10–25 °C, 50–77 °F. `1`: 5–25 °C, **41**–77 °F | `0` | **Set to `1` here.** Conditioned on "glycol no frozen at −10C" |
| P114 | DHC room humidity above which the unit lowers water temperature | 0–100 % | 50 % | |
| P115 | DHC room temperature above which the unit lowers water temperature | 10–32 °C | 27 °C | |
| P116 | DHC resting target when not actively controlling | 10–21 °C | 12 °C, 53.6 °F | |
| P117 | DHC maximum allowed target | 10–24 °C | 20 °C | |
| P118 | DHC minimum allowed target | 4–12 °C | 10 °C, 50 °F | |
| **P119** | DHC enable | On/Off | **Off** | |
| **P59** | **AC anti-freezing temperature** | −15 to 5 °C | **3 °C = 37.4 °F** | **Watches leaving water and latches E14.** The real limit on how cold the target may go |
| P52 | Water pump working mode | 0 not stop / 1 stop at target / 2 restart 1 min after each 15 min stop | 0 | Mode 0 keeps water moving and damps the tank swing |
| P53 | EC water pump C4 minimum speed | 20–80 % | 40 % | Raising it narrows the evaporator ΔT at low load, which lifts leaving water for the same target |
| P64 | AC water flow switch type | 0 switch / 1 flow meter / 2 DN50 / 3 SEN-HZG1WA | 1 | |
| P65 | AC minimum water flow | 3–80 L/min | **cx65/cx75: 20** | Below this the unit raises P5 |
| P71 | Cooling maximum set temperature | 15–35 °C | 25 °C | A ceiling, not the floor |
| C04, C05 | Inlet and outlet water temperature | | | Status |
| C13 | Usage-side water flow | 0–100 L/min | | Status, and the flow term in [4.3](#43-flow-without-a-flow-meter) |
| C67 | Cooling target temperature | 5–60 °C | | Status. Log it once the target moves |
| C68, C69, C70 | Room temperature, humidity, dew point | | | Status, readable only with P119 on |

**P109 was the gate and is now open.** At its factory `0` the controller will not accept a target
below 50 °F, which is where this system sits. It is now set to `1`, so the range runs to 41 °F.

**What the target costs on the leaving side.** The target governs return water and the unit makes
water colder than that by its evaporator ΔT, so the two move together:

| Return target | Leaving water at the 9 °F design ΔT | Note |
|---|---|---|
| 53 °F | 44 °F | Chiltrix's stated normal setting |
| **50 °F** | **41 °F** | Set here today. The IOM asks for ≥15 % glycol at this point |
| 46 °F | 37 °F | |
| 42 °F | 33 °F | |
| 41 °F | 32 °F | The P109 = 1 floor, permitted with glycol unfrozen at −10 °C |

**The 9 °F is a design figure, not a constant.** It is the ΔT in Chiltrix's own sizing formula,
`BTU = WF × ΔT × GPM`, at design flow and full load; at part load the real ΔT is smaller and the
leaving water correspondingly warmer. Read `C04` and `C05` to find the actual figure before assuming
the column above. The tank's 0.03 °F stratification is weakly suggestive of a smaller ΔT, since a
9 °F-colder stream entering a 37-gallon tank would have to mix very thoroughly to leave no trace, but
that is an inference and the controller settles it directly.

**This is where the two plants stop being comparable.** The UniChillers sensed **leaving** water and
the Chiltrix senses **return**, so a given loop temperature sits on opposite sides of each machine's
evaporator ΔT. Reproducing the old loop temperature of about 41 °F asks the Chiltrix for leaving
water near 33 °F, which is colder than the UniChillers ever produced, their floor being 38 °F.
Chiltrix permits it, and it costs capacity that this smaller plant may want on a design day.

Glycol decides whether P109 may change. **25 % propylene glycol freezes at about −10 °C and 30 % at
about −13 °C**, so the loop as it stands sits on the stated limit rather than inside it, and the
25 % to 30 % top-up already planned for heating season becomes the prerequisite
([7.1](#71-costs-nothing)). Measure the actual concentration before relying on either figure.

## K.4 Dynamic Humidity Control is the feedback loop you would have built

The obvious next thought is to feed humidity, or the master bedroom's Y2 call, back to the chiller so
it lowers water temperature on demand. The CX-series controller already does this. It accepts an
indoor temperature and humidity sensor on a 12 VDC and RS-485 pair and lowers the water target when
the room passes **P114** on humidity or **P115** on temperature. Chiltrix suggests siting the sensor
as you would a thermostat, centrally, and at the top of the stairway in a two-storey house.

**Both of the signals you would have wired arrive from that one sensor.** Humidity feedback is P114
directly. The Y2 signal is a statement that a zone cannot hold setpoint on stage 1, and P115 responds
to the same condition from the temperature side, so a Y2 wire into the chiller adds little that P115
does not already carry. That keeps Y2 as a measurement rather than a control input, which is the
better place for it: it stays the metric that scores every change
([4.6](#46-reading-the-master-bedrooms-fan-stage)).

Four things to hold in mind before enabling it.

**One sensor reads one room.** Siting it in the master bedroom optimises the binding zone and gives
the rest of the house colder water whenever that room is humid. The zone valves and thermostats stop
that from overcooling anyone, since colder water only reaches a zone that is calling, but it does
mean the whole plant's efficiency follows one bedroom.

**P109 still gates the floor.** P118 bottoms at 4 °C, and the cooling target range passes through
P109 regardless, so the glycol prerequisite applies to DHC exactly as it applies to a fixed lower
target.

**Do not run a second control loop on top of it.** Writing the target over Modbus from the Pi would
duplicate DHC with worse hardware and needs function code 6 or 16 into a register map that is
community-sourced and untested on this model ([4.2](#42-the-sensor-package)). Keep pivac read-only.

**Log C67 if DHC is enabled.** The target stops being a constant, so without it the loop temperature
will appear to wander for no visible reason on the dashboards. Record the change in `CLAUDE.md` too:
a second controller acting on water temperature is exactly the kind of thing that makes a system
unexplainable to whoever looks at it next.

---

## Sources

- [Chiltrix by Unico CX75 sell sheet](https://unicosystem.com/wp-content/uploads/2026/03/Chiltrix-by-Unico_CX75_Sell-Sheet.pdf)
- [Chiltrix CX50-1 installation and operation manual](https://www.chiltrix.com/documents/CX50-IOM-1.pdf)
- [Chiltrix CX65-1 installation and operation manual](https://www.chiltrix.com/documents/CX65-1-IOM.pdf) — C-parameter list, head and flow figures
- [Chiltrix VCT37C buffer tank specifications](https://www.chiltrix.com/documentation/vct37/vct37C-buffer-tank-specs.pdf)
- [Chiltrix Modbus RTU overview](https://www.chiltrix.com/systems-design-control/modbus-rtu/)
- [jasipsw/homeassistant-chiltrix-modbus](https://github.com/jasipsw/homeassistant-chiltrix-modbus) — community register map, CX34/CX35/CX50-2
- [gonzojive/heatpump](https://github.com/gonzojive/heatpump) and [sodabrew/chilctl](https://github.com/sodabrew/chilctl) — CX34 RS-485 tooling
- [Unico M Series chilled water cooling module, bulletin 20-020.3.020](https://unicosystem.com/wp-content/uploads/literatures/bulletin-20-020.3.020---2019_01.pdf)
- [Unico UniChiller installation and user's guide, bulletin 30-032](https://unicosystem.com/wp-content/uploads/literatures/bulletin_30-032_2011-01.pdf) — DTC programming, `S2`/`DIF 2`, the 38 °F cooling floor
- [Taco 00 Series 3-speed cartridge circulators](https://www.tacocomfort.com/product/00-series-3-speed-cartridge-circulators/)
- [Grundfos UPS 26-99 FC/BFC technical data](https://www.lockewell.com/pdf/grundfos/ups_26-99_fc_bfc.pdf)
- [BOVA-36HDN1-M18M installation instructions, Bosch 06.2016](https://blobanarus.blob.core.windows.net/boschthermotechnology-boschproducts/BOVA-36HDN1-M18M_Installation_instructions.pdf)
- [THX9321 Prestige 2.0 and THX9421 Prestige IAQ 2.0 with EIM, system installation guide 69-2490](https://customer.resideo.com/resources/Techlit/TechLitDocuments/69-0000s/69-2490.pdf) — installer setup option list, dehumidification and staging
