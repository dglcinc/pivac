# Unico Hydronic Cooling — Assessment and Tuning

**Date:** 2026-08-18.
**Status:** Assessment complete against existing instrumentation. Remedies proposed, none built.
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
- [4. Measurements that would close the gaps](#4-measurements-that-would-close-the-gaps)
  - [4.1 Free: read the pipe and the pump](#41-free-read-the-pipe-and-the-pump)
  - [4.2 Four DS18B20s on the secondary loops](#42-four-ds18b20s-on-the-secondary-loops)
  - [4.3 Flow without a flow meter](#43-flow-without-a-flow-meter)
  - [4.4 Air-side sensors on one air handler](#44-air-side-sensors-on-one-air-handler)
  - [4.5 A flow meter on the primary](#45-a-flow-meter-on-the-primary)
- [5. Why the secondary delta-T is low](#5-why-the-secondary-delta-t-is-low)
  - [5.1 Primary delta-T is held at a setpoint](#51-primary-delta-t-is-held-at-a-setpoint)
  - [5.2 What that means for the 8 to 12 degree target](#52-what-that-means-for-the-8-to-12-degree-target)
  - [5.3 Elevation adds no pump head in a closed loop](#53-elevation-adds-no-pump-head-in-a-closed-loop)
  - [5.4 What elevation does affect](#54-what-elevation-does-affect)
  - [5.5 Friction head on the index circuits](#55-friction-head-on-the-index-circuits)
  - [5.6 Loop A on LOW is short for the master bedroom](#56-loop-a-on-low-is-short-for-the-master-bedroom)
  - [5.7 What is still unresolved](#57-what-is-still-unresolved)
- [6. Verdict](#6-verdict)
  - [6.1 What optimal means here](#61-what-optimal-means-here)
  - [6.2 Scorecard](#62-scorecard)
  - [6.3 Conclusion](#63-conclusion)
- [7. Remedy ladder, cheapest first](#7-remedy-ladder-cheapest-first)
  - [7.1 Costs nothing](#71-costs-nothing)
  - [7.2 Under $100](#72-under-100)
  - [7.3 $100 to $500](#73-100-to-500)
  - [7.4 $500 to $2,000](#74-500-to-2000)
  - [7.5 Above $2,000, and the last resort](#75-above-2000-and-the-last-resort)
  - [7.6 What not to do](#76-what-not-to-do)
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

---

## 1. Purpose and how to read this

The question is whether the hydronic cooling system is delivering what it can, and if not, what
to change. The system holds every setpoint today, so this is an optimisation exercise rather
than a fault hunt.

Three observations started it. Secondary-loop water rarely shows the 8 to 12 °F ΔT that a hydronic
coil is designed around. One circulator serves several air handlers on each secondary loop, which
raises the question of whether any single coil gets its share. Three of the five zones sit a storey
above the mechanical room, with one coil in the attic, which raises the question of pump head.

Section 5 answers all three, and the middle one turns out to be the live problem. The low ΔT is a
control setpoint held by a modulating pump, and raising it would cost capacity and
dehumidification, so it should be left alone. Elevation costs no pump head at all in a closed loop.
The shared-circulator concern is real: the two zones sharing Loop A's 105 ft index circuit read
humid, and the one zone with a circulator to itself over 15 ft reads dry.

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

| Zone | Level | Loop | Order on the loop | Cooling source |
|---|---|---|---|---|
| Kids room | Ground | A | first | Chiltrix |
| Master bedroom | Second, coil in attic | A | second | Chiltrix |
| Downstairs family room and utility area | Ground | B | first | Chiltrix |
| Kitchen | Second | B | second | Bosch BOVA (`BOS1`) |
| Great room | Second | B | third | Bosch BOVA (`BOS2`) |

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
| Chiller primary | Taco 0015-MSF3-IFC | HIGH assumed, unverified | 1/20 HP, 18 GPM and 17 ft maximum |
| Loop A secondary | Grundfos UP26-99F | LOW | 2 zones year-round |
| Loop B secondary | Grundfos UP26-99F | LOW | 1 zone in summer, 3 in winter |

The chiller primary is materially the smallest pump in the system. A Taco 0015-MSF3-IFC is a
1/20 HP circulator against the UP26-99F's 1/6 HP, and its 17 ft maximum head is roughly half the
Grundfos figure. Section 5 tests whether that matters.

> Verify the Taco's speed switch position. It is recorded as HIGH and has not been read since the
> model was identified. The primary must out-flow the combined secondaries for the closely spaced
> tees to work ([Appendix C](#appendix-c--primarysecondary-hydraulics)), and this is the pump
> with the least margin.

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

Primary ΔT binned against chiller power over 24 hours appears in
[5.1](#51-primary-delta-t-is-held-at-a-setpoint), and it carries this document's central
finding.

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

| Zone | Loop | Coils sharing the circulator | Run to coil | Mean RH |
|---|---|---|---|---|
| Downstairs family room | B | 1 in summer | ~15 ft | **45.9 %** |
| Master bedroom | A | 2 | ~105 ft, coil in attic | 50.9 %, peak 60 % |
| Kids room | A | 2 | ~75 ft | 53.7 %, peak 59 % |

**The driest zone in the house is the one chilled-water coil with a circulator to itself over a
15 ft run. The two humid ones share a circulator across a 105 ft loop.** Water flow raises
dehumidification, because more flow holds the whole coil nearer entering water temperature and
keeps more of its surface below the air dewpoint
([B.6](#b6-water-flow-and-dehumidification-move-together)). A Loop A coil getting less flow than
the Loop B coil would read exactly this way.

Two other explanations fit the same data. Bedrooms carry higher latent load per unit of sensible
load than a family room, so a coil sized on sensible satisfies temperature before it has removed
enough moisture. And the master bedroom's coil sits in an attic, where duct leakage draws hot
humid air into the return. Section 7 separates them, and the first test costs nothing.

This is the one measured shortfall against the stated objective.

### 3.4 The buffer tank is fully mixed

Upper and lower tank probes differ by 0.03 °F. The tank holds thermal mass and provides no
stratification, so its state is one temperature rather than a charge profile.

Two consequences follow. Tank depletion shows as the whole tank warming rather than as a
descending thermocline, so watch `UBT` absolute rather than `UBT − LBT`. And the second probe is
currently redundant, which makes relocating it to the chiller's own leaving-water line a free
upgrade, discussed in [7.1](#71-costs-nothing).

> Confirm the two probes sit at different heights on the tank before concluding the
> tank is mixed. Two sensors mounted close together would produce the same reading for a
> different reason.

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

Three questions remain open, and each needs a sensor the house does not have.

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

---

## 4. Measurements that would close the gaps

Ordered by cost. Each entry states what it settles.

### 4.1 Free: read the pipe and the pump

Three unknowns need no purchase and change the analysis materially.

**Secondary main pipe size.** [5.5](#55-friction-head-on-the-index-circuits) puts the Loop A index
circuit anywhere from about 13 ft to about 30 ft depending on it, which is the difference between
a circulator that covers the master bedroom on LOW and one that never did. Read the stamp on the
pipe.

**The Taco's speed switch.** Recorded as HIGH, unverified since the model was identified. The
primary must out-flow both secondaries combined, which sets the ceiling on raising Loop A.

**Whether balancing valves exist on the branches.** This decides whether a starved zone can be
fixed by redistribution or only by more total flow.

### 4.2 Four DS18B20s on the secondary loops

Roughly $20 of parts on the Pi's existing 1-wire bus, taking it from four sensors to eight.
Supply and return on each loop, named `LOOPA_SUP`, `LOOPA_RET`, `LOOPB_SUP` and `LOOPB_RET`.

They deliver five things at once. Per-loop ΔT answers the starvation question directly. Loop
supply against `IN` detects reverse mixing. The ratio of primary to secondary ΔT gives the ratio
of secondary to primary flow with no flow meter
([Appendix C](#appendix-c--primarysecondary-hydraulics)). Supply and return converging identifies
an idle loop, which isolates Loop A whenever Loop B is quiet. And a shortfall becomes
attributable to Loop A, Loop B or the plant.

This is the highest-value addition in the document. `pivac.OneWireTherm` re-scans the bus every
cycle, so sensors added live appear within one daemon cycle with no restart.

> Fix these four names once. The Signal K path becomes the InfluxDB measurement name, and four
> prior renames each orphaned their history.

### 4.3 Flow without a flow meter

Chiller output is recoverable from the Emporia CT and an efficiency assumption, and flow follows
from output and ΔT:

```
Q       [BTU/hr]  =  EER × P_electrical [W]
GPM     [gal/min] =  Q / (K × ΔT)                    K = 481 for 25 % propylene glycol
```

Applied across the power bands in [5.1](#51-primary-delta-t-is-held-at-a-setpoint), this
returns a flow that climbs with load rather than a constant:

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

---

## 5. Why the secondary delta-T is low

### 5.1 Primary delta-T is held at a setpoint

Water ΔT is output divided by flow:

```
ΔT = Q / (K × GPM)
```

Under fixed flow, ΔT must scale with output. Doubling the chiller's work should roughly double
its ΔT. Binning 24 hours of data by chiller power shows it does not.

| Chiller power band | Mean power | Mean primary ΔT | 2-minute samples |
|---|---|---|---|
| Idle | 35 W | 3.22 °F | 223 |
| 0.5 to 1.2 kW | 1,102 W | 5.00 °F | 144 |
| 1.2 to 1.8 kW | 1,482 W | 5.04 °F | 237 |
| 1.8 to 2.4 kW | 2,040 W | 5.13 °F | 62 |
| 2.4 to 3.0 kW | 2,699 W | 5.18 °F | 46 |
| Above 3.0 kW | 3,283 W | 5.87 °F | 8 |

**Chiller power varies threefold across those bands while primary ΔT moves 17 %.** Fixed flow
cannot produce that. Flow must rise with load, roughly in proportion, which is the signature of a
variable-speed circulator regulating to a target ΔT of about 5 °F.

The Chiltrix CX series drives its water circulator from an inverter and controls it to hold a set
water ΔT, so the most likely mechanism is the chiller's own pump doing its job. That leaves the
Taco's role on the primary open ([9](#9-open-questions)).

Read the confidence carefully. Most of this window predates the two-decimal fix, so each
individual ΔT reading is quantised to 1.8 °F. The band means average 46 to 237 samples each,
which holds their standard error near 0.1 to 0.2 °F. Across the four well-populated bands,
spanning 1,102 to 2,699 W, the mean moves 0.18 °F. The flatness is far larger than the noise.
The top band rests on 8 samples and should be treated as indicative.

### 5.2 What that means for the 8 to 12 degree target

A regulated ΔT is a setpoint. Nothing on the coil side moves it, because the pump answers any
change in load by changing flow to keep the difference where it was told to keep it. Balancing
valves, pump taps and coil cleaning all leave a controlled ΔT at its target.

**The 8 to 12 °F band is therefore unreachable by tuning, and reaching it means raising the
control target.** That converts the question from a hydraulic problem into a settings problem.

**Do not raise it.** Raising the target ΔT lowers flow, and lower flow costs both capacity and
dehumidification. Water leaving the coil warmer means the average coil surface sits warmer, so
more of the coil rises toward the entering-air dewpoint and stops condensing
([B.6](#b6-water-flow-and-dehumidification-move-together)). The objective ranks comfort first, and
humidity is already the marginal axis in the two Loop A bedrooms
([3.3](#33-humidity-is-the-marginal-axis)). Trading latent capacity for a tidier number is the
wrong direction for this house.

The present 5 °F ΔT is therefore working in the system's favour. High flow holds the coils close to
entering water temperature, which is what keeps their surfaces below the air dewpoint. What it
costs is pump energy, which the objective ranks last.

That leaves one legitimate use for the setting. If a design-day test ever shows the plant
saturating while the loops still run a 5 °F ΔT, the chiller is making all the capacity it can and
the loops are moving more water than they need. Raising the target then recovers pump energy with
no comfort cost. Until that test happens, leave it alone.

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

Head depends on pipe size, and the difference between plausible sizes is larger than every other
term in the calculation.

Assumptions: type L copper, 25 % propylene glycol at 45 °F carrying a 1.25 friction multiplier
over water, ¾" branches, 5 GPM per coil, and 40 % added to pipe length for fittings. Flow tapers
as coils tee off, so each leg is computed at the flow it carries. The branch, coil and zone-valve
allowance is 9.9 ft in every row and does not vary with main size.

**Loop A, index circuit the master bedroom, both coils calling at 10 GPM total:**

| Main size | Tees to kids branch, 10 GPM | To master coil, 5 GPM | Branch, coil, valve | Total | Velocity at 10 GPM |
|---|---|---|---|---|---|
| 1" | 12.9 ft | 1.4 ft | 9.9 ft | **~30 ft** | 3.9 ft/s |
| 1¼" | 4.1 ft | 0.5 ft | 9.9 ft | **~16 ft** | 2.6 ft/s |
| 1½" | 1.7 ft | 0.2 ft | 9.9 ft | **~13 ft** | 1.8 ft/s |

**Loop B, index circuit the great room, all three coils calling at 15 GPM total, the winter case:**

| Main size | To family branch, 15 GPM | To kitchen branch, 10 GPM | To great room, 5 GPM | Branch, coil, valve | Total |
|---|---|---|---|---|---|
| 1" | 5.3 ft | 4.3 ft | 1.0 ft | 9.9 ft | **~25 ft** |
| 1¼" | 1.7 ft | 1.4 ft | 0.3 ft | 9.9 ft | **~15 ft** |
| 1½" | 0.7 ft | 0.6 ft | 0.1 ft | 9.9 ft | **~12 ft** |

Loop B in summer drives one coil over a 15 ft run, which needs under 12 ft at any pipe size and
is the easiest duty in the system.

Velocity gives an independent read on pipe size. Ten GPM in 1" copper runs 3.9 ft/s, at the 4 ft/s
limit that governs erosion and noise, and 15 GPM in the same pipe runs 5.8 ft/s, well past it. **If
the Loop B mains are 1", that loop was never sized to carry three coils at 5 GPM each in winter.**
Loop A at 1" is borderline rather than clearly wrong.

### 5.6 Loop A on LOW is short for the master bedroom

A UP26-99F on LOW delivers roughly 10 to 12 ft of head at zero flow and less as flow rises.
Against the [5.5](#55-friction-head-on-the-index-circuits) estimates, LOW covers the master
bedroom circuit only if the mains are 1½", falls short at 1¼", and falls a long way short at 1".
Loop B on LOW covers its summer single-coil duty comfortably at any size.

**That asymmetry matches the humidity measurement.** The Loop B family-room coil has a whole
circulator to itself over 15 ft and reads 45.9 % RH. The two Loop A coils share one circulator
across a 105 ft index circuit and read 50.9 % and 53.7 %, peaking at 60 % and 59 %. More water
flow removes more moisture
([B.6](#b6-water-flow-and-dehumidification-move-together)), so an under-pumped Loop A produces
exactly the pattern in [3.3](#33-humidity-is-the-marginal-axis).

The remedy is free and reversible. Loop A's circulator has two speeds above where it sits, and
raising it is the first item in [7.1](#71-costs-nothing).

One ceiling bounds it. Secondary flow must stay under primary flow or the tees mix backwards
([Appendix C](#appendix-c--primarysecondary-hydraulics)). Primary flow rises with load to about
15 GPM and falls to about 8 GPM at part load ([4.3](#43-flow-without-a-flow-meter)), so the margin
is widest when the chiller works hardest and narrowest when it idles. Loop A on MEDIUM plus Loop B
on LOW should stay inside it, and the four loop sensors in
[4.2](#42-four-ds18b20s-on-the-secondary-loops) confirm it directly.

Distribution within Loop A is the second question. Two coils on one fixed-speed circulator with no
balancing share what the pump delivers by relative resistance, and the master bedroom sits at the
far end of the run behind the kids branch. It is the coil most likely to be short when both call
together, which is the design-day case, and it is unmeasured.

### 5.7 What is still unresolved

Regulated primary flow explains the primary ΔT and says nothing about either secondary loop. Three
possibilities remain for the loops themselves, and one measurement separates them.

| Condition | Loop supply against `IN` | Loop ΔT against primary ΔT | Consequence |
|---|---|---|---|
| Decoupled and healthy | equal | at or above | None. The coils see tank temperature |
| Secondary overpumped | equal | below | Pump energy wasted. Coil capacity and dehumidification are unharmed |
| Reverse mixing at the tees | warmer in cooling | below | Real capacity loss, presenting as an undersized chiller |

Loop supply temperature against `IN` is the discriminator, and it needs two of the four sensors in
[4.2](#42-four-ds18b20s-on-the-secondary-loops).

The evidence leans toward the first row. Implied primary flow reaches 15 GPM at high load
([4.3](#43-flow-without-a-flow-meter)), both secondaries run on LOW, and reverse mixing requires
combined secondary flow to exceed the primary. That ordering is comfortable rather than proven, and
it inverts on a design day if the primary is already at its ceiling while three Loop A zone valves
open together.

## 6. Verdict

### 6.1 What optimal means here

Six criteria, in the order the objective ranks them.

1. Every zone holds setpoint on a design day.
2. Humidity stays near 50 % RH in occupied zones.
3. Coil entering water temperature matches the tank, so no capacity is lost at the tees.
4. Each zone gets its share of flow when all zones on its loop call together.
5. The plant retains reserve capacity at design conditions.
6. Pump and plant energy are no higher than the above requires.

### 6.2 Scorecard

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Zones hold setpoint | **Pass at 80 °F** | Zero droop on all five zones, 8 h |
| 2 | Humidity near 50 % | **Marginal, and it tracks the loops** | 60 % peak master bedroom and 59 % kids room, both on Loop A, against 45.9 % in the family room alone on Loop B ([3.3](#33-humidity-is-the-marginal-axis)) |
| 3 | No loss at the tees | **Unknown** | Needs loop supply against `IN` ([4.2](#42-four-ds18b20s-on-the-secondary-loops)) |
| 4 | Fair share between zones | **Suspect on Loop A** | 105 ft index circuit, no balancing, and LOW covers it only at 1½" mains ([5.6](#56-loop-a-on-low-is-short-for-the-master-bedroom)) |
| 5 | Reserve at design | **Untested** | 54 % idle at 80 °F, but 6 tons of coil on a 4.3-ton chiller |
| 6 | Energy proportionate | **Suspect** | Primary flow reaches ~15 GPM against a ~10.6 GPM design figure ([4.3](#43-flow-without-a-flow-meter)) |

### 6.3 Conclusion

**The system is operating well against its stated objective and is not operating at its limit.**
Every zone holds setpoint with the plant idle more than half the time on a warm evening, which is
the outcome the objective asks for. Nothing here needs fixing to restore comfort.

The low ΔT has a cause outside the distribution and is better left alone. Primary ΔT holds near
5 °F while chiller power varies threefold, so flow is being modulated to keep it there
([5.1](#51-primary-delta-t-is-held-at-a-setpoint)). Reaching 8 to 12 °F means raising that control
target, which lowers flow, and lower water flow costs both capacity and dehumidification
([B.6](#b6-water-flow-and-dehumidification-move-together)). The 5 °F the system runs today is part
of why the coils keep their surfaces below the air dewpoint. It costs pump energy, which the
objective ranks last.

**The measured shortfall is humidity, and it falls along the loop split.** The one chilled-water
coil with a circulator to itself over a 15 ft run reads 45.9 % RH. The two sharing a circulator
across a 105 ft index circuit read 50.9 % and 53.7 %, peaking at 60 % and 59 %. More water flow
removes more moisture, and Loop A on LOW covers the master bedroom circuit only if the mains are
1½" ([5.6](#56-loop-a-on-low-is-short-for-the-master-bedroom)). Raising Loop A one speed tests
that for free, and it is the first thing to do.

Two things remain unverified. Distribution between the two Loop A coils is unbalanced by
construction and unmeasured, which matters most on the design day nobody has yet observed. And
whether the tees mix backwards is unknown, which section 7 resolves for about $20.

---

## 7. Remedy ladder, cheapest first

### 7.1 Costs nothing

**Raise Loop A's secondary circulator from LOW to MEDIUM.** The first thing to try, and the only
free action aimed straight at the measured shortfall. Loop A's two coils read 50.9 % and 53.7 % RH
against 45.9 % for the single Loop B coil, more water flow removes more moisture, and LOW covers
the 105 ft master-bedroom circuit only at 1½" mains
([5.6](#56-loop-a-on-low-is-short-for-the-master-bedroom)). Watch both zones' humidity and
temperature across a few comparable hot days. Revert if the tees start mixing, which the loop
sensors in [4.2](#42-four-ds18b20s-on-the-secondary-loops) would show as loop supply drifting above
`IN`.

**Lower the chiller's leaving-water setpoint by 2 to 3 °F.** The second route to a colder coil
surface, independent of flow, and the one that works if Loop A proves adequately pumped. It costs
efficiency, which the objective ranks second. Both zones' RH is already logged, so the result is
readable within a few comparable days. Keep the setpoint above the point where the coil frosts and
above the chiller's own minimum. Change one of these two at a time.

**Read the Taco's speed switch and set it to 3.** The primary must out-flow both secondaries
combined, and this is the smallest pump in the system at 1/20 HP. Do this before raising Loop A.

**Read the secondary main pipe size.** It swings the Loop A head estimate from about 13 ft to
about 30 ft ([5.5](#55-friction-head-on-the-index-circuits)) and decides whether balancing or a
bigger pump is the answer if raising the tap falls short.

**Move the redundant lower buffer-tank probe to the chiller's leaving-water line.** `UBT` and `LBT`
differ by 0.03 °F, so the second reading carries no information where it is. On the chiller outlet
it gives the reference that makes every mixing and distribution-loss figure absolute. This is a
sensor relocation with no purchase.

**Add a design-day saturation alert.** Chiller power pinned near 3,537 W for an extended period
with droop above zero on more than one zone is the signature of the plant running out, and it is
the condition none of the sampled days contained. Grafana already has the two series.

**Confirm the attic coil's automatic air vent and the expansion-tank position** relative to both
secondary circulators ([5.4](#54-what-elevation-does-affect)). Visual checks.

**Raise Loop B's tap before heating season**, with the 25 % to 30 % glycol top-up. Loop B carries
one coil in summer and three in winter, and [5.5](#55-friction-head-on-the-index-circuits) puts
its winter index circuit at 15 to 25 ft. Set `fluid_k` to 476 on the day of the top-up and add a
Grafana annotation.

### 7.2 Under $100

**Four DS18B20s on the secondary loops, about $20.** This is the highest-value purchase in the
document. It resolves criteria 3 and 4, gives per-loop flow through the ratio method with no
meter, and detects reverse mixing ([4.2](#42-four-ds18b20s-on-the-secondary-loops)).

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

**A flow meter on the primary, $200 to $400.** Converts every ratio in this document into
absolute BTU/hr and yields system COP against the existing Chiltrix CT
([4.5](#45-a-flow-meter-on-the-primary)). Buy this before any per-coil meter.

**Static balancing valves on the Loop A branches, roughly $60 to $120 per branch installed.**
The direct answer to criterion 4. Set so each zone gets design flow in the worst case with all
three open. Mechanical, no controls, and aimed at the maldistribution that the 105 ft index
circuit makes likely. Do this only after the loop sensors confirm maldistribution exists.

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

**ΔT-controlled or ΔP-controlled ECM secondary circulators, $500 to $900 each.** A ΔT-controlled
circulator modulates speed to hold a target loop ΔT, which is the mechanical answer to the
question that opened this document. A ΔP-controlled unit holds per-branch flow steady as zone
valves open and close. Either removes the three-speed tap and its seasonal adjustment.

### 7.5 Above $2,000, and the last resort

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

### 7.6 What not to do

**Do not chase an 8 to 12 °F ΔT.** It would mean raising the chiller's target and cutting flow,
and lower water flow costs capacity and dehumidification in a house whose measured shortfall is
humidity ([5.2](#52-what-that-means-for-the-8-to-12-degree-target)). The number is a design
convention, and this system is better off without it.

**Do not throttle a valve to move the ΔT either.** The ΔT is held by a control loop, so throttling
makes the pump work harder against the restriction and arrive at the same target
([5.1](#51-primary-delta-t-is-held-at-a-setpoint)).

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
| 1 | Read the Taco speed switch and set it to 3; read the secondary main pipe size; check for branch balancing valves | — | [4.1](#41-free-read-the-pipe-and-the-pump) |
| 2 | Raise Loop A from LOW to MEDIUM; watch master bedroom and kids room RH for a few comparable hot days | — | Criterion 2, and it tests criterion 4 |
| 3 | If step 2 does not move humidity, lower the chiller leaving-water setpoint 2 to 3 °F | — | Criterion 2 by the other route |
| 4 | Relocate the redundant `LBT` probe to the chiller leaving-water line | — | Criterion 3 |
| 5 | Add the design-day saturation alert; wait for one 95 °F afternoon | — | Criterion 5 |
| 6 | Four DS18B20s on the secondary loops | ~$20 | Criteria 3 and 4, and it confirms step 2 |
| 7 | Restore leak detection; add mechanical-room T/RH | ~$35 | Regression, and the Pi's thermal ceiling |
| 8 | Two 10K NTCs in the zone the RH comparison identifies | on hand | Sensible against latent |
| 9 | Flow meter on the primary | $200–400 | Absolute capacity and system COP |
| 10 | Branch balancing on Loop A, if step 6 shows maldistribution | $200–400 | Criterion 4 |
| 11 | The air-handler node | ~$300 | Per-coil attribution |

Steps 1 to 5 cost nothing and should run before any purchase. Step 2 is the one most likely to move
the measured shortfall, and steps 2 and 3 change one variable each so their effects stay separable.
Step 6 is the decision point for the rest: it either confirms the healthy-decoupling reading in
[5.7](#57-what-is-still-unresolved) and shows whether step 2 delivered more flow, or it finds
mixing or maldistribution and sends the work to step 10.

---

## 9. Open questions

- What holds the primary ΔT at 5 °F, and where is its setpoint? The Chiltrix CX series drives its
  circulator from an inverter against a target water ΔT, which fits the measurement
  ([5.1](#51-primary-delta-t-is-held-at-a-setpoint)). Confirm from the unit's controller, and
  find the adjustment. Needed to interpret every water-side figure here, and to know whether the
  loops can be re-pumped without the chiller answering by changing its own flow.
- Does the CX75 carry its own internal circulator, and if so what is the Taco 0015-MSF3-IFC doing?
  A 17 ft shutoff head cannot pass 15 GPM through an evaporator the CX65 rates at 16 ft of drop at
  10 GPM, so the two cannot both be the whole story ([4.3](#43-flow-without-a-flow-meter)).
- What size are the two secondary mains? It moves the Loop A index-circuit head from about 13 ft
  to about 30 ft, which decides whether LOW was ever adequate
  ([5.5](#55-friction-head-on-the-index-circuits)).
- Which speed is the Taco 0015-MSF3-IFC set to?
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
- Confirm `UBT` and `LBT` are at different tank heights
  ([3.4](#34-the-buffer-tank-is-fully-mixed)).

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
| Summer, chilled | 1, the lower family room | LOW. Anything more only adds pump energy |
| Winter, hot | 3: family room, kitchen, great room | Higher. Its winter index circuit needs 15 to 25 ft ([5.5](#55-friction-head-on-the-index-circuits)) |

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

## A.4 Existing instrumentation

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
> all ([5.1](#51-primary-delta-t-is-held-at-a-setpoint)).

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

The family room has a RedLink thermostat, `DSTRS_FAM_ROOM`, so its call state is already in pivac
and the isolation windows can be selected from data on hand. The loop sensors confirm it
independently: a loop with its pump off and its zone valve shut shows supply and return
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

One board per air handler, DHCP-reserved by MAC in UniFi like the others.

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
| SHT41 temperature and humidity, optional | A4/A5 | I²C |

Avoid D0/D1 (Serial1), D4/D5 (CAN) and D10 to D13 (SPI). The free general-purpose pins on the R4
are D2, D3, D6, D7, D8 and D9, and this design uses two.

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
 'flow' : 4.92, 'volume' : 10432.5, 'uptime_ms' : 84213}
```

| Field | Unit | Meaning |
|---|---|---|
| `wsup` | °F | Water entering the coil |
| `wret` | °F | Water leaving the coil |
| `asup` | °F | Supply, or leaving, air |
| `aret` | °F | Return, or entering, air |
| `flow` | gal/min | Rolling-window instantaneous flow |
| `volume` | gal | Lifetime totalizer, EEPROM-persisted |
| `uptime_ms` | ms | A low value means a recent reboot, the same power-event diagnostic the pressure boards use |

Emit two decimal places on every temperature. The precision has to survive as far as the delta.

Reuse the scaffolding proven in `DomesticWater.ino`: a D-pin pulse interrupt with debounce, an
EEPROM totalizer with a magic marker, a 10 s rolling flow window, the RA4M1 watchdog, and bounded
WiFi and HTTP handling. Add the 12-bit DS18B20 read and the two averaged ADC reads.

Handle disconnected sensors explicitly. A DS18B20 that fails to read returns −127, and an open NTC
divider rails to full scale. Emit a −999 sentinel rather than a plausible number, so the Pi can
drop the sample instead of computing a confident and wrong figure.

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

The four secondary-loop sensors in [4.2](#42-four-ds18b20s-on-the-secondary-loops) go on the Pi's
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
([5.1](#51-primary-delta-t-is-held-at-a-setpoint)).

---

# Appendix H — Utility-room instrumentation

The air handler measures whether one coil is delivering. The mechanical room measures whether the
plant is healthy, and several of those sensors cost less and return more than the coil node.

## H.1 Tier 1

| Sensor | Where | Why |
|---|---|---|
| 4× DS18B20, supply and return on each secondary loop | Loop A and Loop B, at the tees | Starvation, flow ratios, mixing, loop-idle detection. The highest-value addition in this document ([4.2](#42-four-ds18b20s-on-the-secondary-loops)) |
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

## Sources

- [Chiltrix by Unico CX75 sell sheet](https://unicosystem.com/wp-content/uploads/2026/03/Chiltrix-by-Unico_CX75_Sell-Sheet.pdf)
- [Chiltrix CX50-1 installation and operation manual](https://www.chiltrix.com/documents/CX50-IOM-1.pdf)
- [Chiltrix CX65-1 installation and operation manual](https://www.chiltrix.com/documents/CX65-1-IOM.pdf)
- [Taco 00 Series 3-speed cartridge circulators](https://www.tacocomfort.com/product/00-series-3-speed-cartridge-circulators/)
- [Grundfos UPS 26-99 FC/BFC technical data](https://www.lockewell.com/pdf/grundfos/ups_26-99_fc_bfc.pdf)
- [BOVA-36HDN1-M18M installation instructions, Bosch 06.2016](https://blobanarus.blob.core.windows.net/boschthermotechnology-boschproducts/BOVA-36HDN1-M18M_Installation_instructions.pdf)
