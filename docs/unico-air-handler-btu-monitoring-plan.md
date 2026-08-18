# Plan — Unico 2430 Air-Handler BTU Monitoring

**Status:** Design / not yet built.
**Date:** 2026-08-18.
**Target:** One **Unico M2430** air handler with a **chilled-water coil used for both heating
and cooling** (two-pipe changeover off the buffer tank). First of potentially several.

**Two facts that shape the design more than anything else:**

- The air handler runs a **Unico Smart Controller with a software-configurable ECM blower**,
  so **CFM is commanded, not guessed** (§7.2). This removes the hardest unknown on the air
  side — and replaces it with a much better diagnostic.
- A **Honeywell IAQ thermostat on RedLink** is attached to this air handler, and
  `pivac.RedLink` **already publishes that zone's humidity**
  (`environment.inside.thermostat.<ZONE>.humidity`, `pivac/RedLink.py:331`). That is the
  entering-air humidity this project would otherwise need new hardware to get (§7.3).
- **Topology confirmed (David, 2026-08-18): the HZ-432 drives one zone valve per zone, each
  feeding its own air handler. There are no dampers.** So this node measures one coil with its
  own dedicated blower — CFM per handler is constant, and the RedLink thermostat maps 1:1 to
  the air handler. But the zones **share a circulator**, which makes per-zone water flow a
  variable rather than a constant (§4.6) — this is the fact that decides whether you buy a flow
  meter — though on Loop B in cooling it is a single-zone loop and constant (§2.5).

**Goal:** Measure the actual BTU/hr the coil delivers, and enough surrounding state to tell
*why* it isn't delivering more. Feed it into pivac like every other sensor
(Arduino → `pivac.*` → Signal K → InfluxDB → Grafana).

---

## 0. Priorities (David, 2026-08-18)

The objective is summer comfort and capacity across both cooling systems, the two Bosch BOVA
zones and the Chiltrix zones. Efficiency and running cost are secondary. Heating is rarely a
problem, so monitor it and leave it alone.

| Primary | Secondary / monitor-only |
|---|---|
| Cooling capacity and where it is lost | Boiler condensing (§4.8): monitor, do not chase |
| Latent capacity and humidity | System COP, kW/ton, pump energy |
| The BOVA (DX) zones (§0.2) | Unbuffered-heating short cycling (§2.5e) |
| Airflow, on both systems | Heating season, except as a calibration window (§7.2) |

The BOVA zones have no water side, so §2.2 (glycol), §2.6 (tees) and §4.5 (flow meter) do not
apply to them. The air-side instrumentation does, and for those zones it is most of the job.
Efficiency metrics stay in the plan only where they fall out of data already collected, and
they never justify buying hardware.

### 0.1 The first question is already answerable from existing data

Every cooling unit in the house is individually metered, verified live 2026-08-18:
`electrical.emporia.house.bova_great_room`, `…bova_kitchen`, `…chiltrix`. That settles the
question this plan exists to answer: on a hot afternoon, is a drooping zone running its
equipment at maximum?

| Droop (zone temp − `coolset`) | Equipment power | Diagnosis |
|---|---|---|
| High | at or near max, near-continuous | Capacity-limited: needs more capacity, more airflow, or less load |
| High | well below max | Control-limited: the unit is not trying. Modulation, staging, or sensing |
| Low, but the room feels wrong | any | Latent: check `…thermostat.<ZONE>.humidity`. Sensible is fine, moisture is not |

Join `environment.inside.thermostat.<ZONE>.temperature`, `.coolset` and `.humidity` with
`environment.outside.thermostat.temperature` and the three power measurements. Run this before
buying anything; it decides which zone deserves instrumentation first.

> ⚠️ Droop data is quantitative only from 2026-08-18. `pivac.OneWireTherm` and `pivac.RedLink`
> both emitted whole-Kelvin temperatures until then, and `RedLink` truncated rather than
> rounded, so every zone read up to 1.8 °F cold and droop was biased low. PRs #118 and #119
> fixed both; they now emit 2-decimal Kelvin, and setpoints keep Honeywell's half-degree steps.
> InfluxDB history before that date stays quantised, so start any droop analysis at the fix date.

### 0.2 The BOVA (DX) zones use the same air-side rig with no water side

The kitchen (`BOS1`) and great room (`BOS2`) are Unico air handlers on Bosch BOVA inverter
condensers. Two 10K NTCs in the supply and return plenums (§4.4), plus the commanded ECM
airflow, give measured sensible capacity:

```
Q_sensible = 1.08 × CFM_commanded × ΔT_air
```

Latent comes from the zone's RedLink humidity (§7.3), and the condenser's power is already
metered, which supplies an EER cross-check. No water plumbing and no flow meter.

> Airflow drives capacity on these units because the compressor modulates on suction pressure.
> The thermostat's `Y2` selects the air handler's second-stage fan speed, so a second-stage call
> reaches the compressor through airflow rather than through any wire to the condenser (§0.3).
> Low airflow is therefore self-reinforcing: less air over the coil lowers suction pressure, the
> compressor modulates down, capacity falls, and the room drifts further. A zone can read as
> control-limited, with the compressor below maximum, and be airflow-limited at the same time,
> because the airflow causes the modulation.
>
> Two thermistors plus the existing CT separate the cases:
>
> | Air ΔT | Condenser power | Meaning |
> |---|---|---|
> | High | low | Airflow-starved, self-limiting through suction pressure |
> | normal | at max | Capacity-limited at these conditions |
> | low | low | Not calling, or short-cycling |
>
> A thermistor clamped to the suction line is a cheap addition. A persistently cold suction line
> with low airflow indicates starvation or freezing.

### 0.3 Can `Y2` be signalled, or the compressor driven higher? — answered from the IOM

Checked against the **BOVA-36HDN1-M18M Installation Instructions** (Bosch Thermotechnology,
06.2016) — the exact model installed here.

#### `Y2` — no, and it is not a wiring omission

**`Y2` does not appear anywhere in the manual (zero occurrences).** The low-voltage hook-up
(Figure 26) gives the terminal blocks as:

| Block | Terminals |
|---|---|
| Outdoor unit | `C` `Y` `B` `D/W` — *B and D/W on heat-pump models only* |
| Indoor unit | `G` `R` `C` `W1` |
| Thermostat | `W2` `B` `C` `R` `Y` `G` |

The condenser accepts **one `Y`** — a single 24 V cooling call. §15.1 states the unit "adopts
the same 24VAC control as any conventional Heat Pump" and does all staging *internally*. There
is no second-stage input on the condenser and nothing to wire to it.

> **`Y2` is not useless, though — it belongs to the *air handler*.** The thermostat's `Y2` drives
> the Unico blower's **second-stage fan speed**, and that is how a second-stage call reaches the
> compressor: **indirectly, through air.** More airflow puts more heat into the coil, which
> raises evaporator pressure, which ramps the compressor (§0.3 below). So `Y2` controls airflow, not the compressor. **A disabled `Y2` fan wire
> starves the coil on exactly the hot days when the second stage is called for**, and because the
> compressor modulates on suction pressure it responds by slowing down, which is the
> self-reinforcing failure in §0.2. Confirm `Y2` is connected and functional at the air handler
> before diagnosing anything else on a BOVA zone.

#### Suction pressure has one adjustment, and it is already set

Suction pressure is a *dependent* variable: it is the result of load, airflow, and charge, so
it cannot be "managed" directly to make the compressor work harder. What the manual does expose
is the **target** it modulates toward (§15.1, verbatim):

> "The compressor's speed is controlled based on coil pressures monitored by pressure
> transducer… the compressor speed will modulate relative to **evaporator pressure during
> cooling operation**… The target pressure can automatically adjust based on compressor
> operation so optimal capacity can be achieved. **Target pressure can manually be adjusted
> (SW4)** to achieve improved dehumidification and capacity demands."

`SW4` on the outdoor control board (Table 8):

| Switch | ON | OFF |
|---|---|---|
| SW4-1 | *Not used* | |
| SW4-2 | *Not used* | |
| SW4-3 | Adaptive capacity output disable | Adaptive capacity output enable |
| SW4-4 | Accelerated cooling/heating | Normally cooling/heating |

**Both are already set on the great-room unit** — SW4-4 accelerated on both units, and SW4-3
switched on in July, after which its board display read **75–77 Hz**. There is no third
capacity switch. **The compressor is already running as hard as the controls allow.**

> **Which relocates the problem, and confirms where this plan should spend.** If the unit is at
> maximum commanded speed and the zone still drifts, the constraint is **downstream of the
> compressor** — refrigerant **mass flow** (charge) or **evaporator heat transfer** (airflow),
> not control. §0.2 is built to separate that pair, which is why two
> thermistors on that air handler are worth more here than any further control tinkering.
> The outstanding **subcooling check** is the other half: the manual makes subcooling the *only*
> recommended charging method above 55 °F outdoor ambient (weigh-in below that), and prior notes
> carry a target of **10 ± 2 °F**.

#### ⚠️ SW4-3 may be trading away the comfort you want

The manual ties SW4 to "improved **dehumidification** *and* capacity demands" — the two are a
**tradeoff**, not a package. Disabling adaptive capacity holds the target evaporator pressure
*higher*, which means a **warmer coil**, which means **less moisture removal**. Since the
objective in §0 is comfort rather than raw sensible output, a great room sitting at 77 °F *and*
humid could be **worse off** with SW4-3 on, even if sensible capacity rose.

**This is now testable, and it was not before.** Both BOVAs have their own CT, and RedLink logs
per-zone humidity. **Run SW4-3 OFF for a few comparable hot days and compare droop *and*
humidity against the SW4-3 ON period.** If droop is unchanged and humidity falls, adaptive
capacity was the better setting all along.

#### Two board features

- **"Forced operation button"** (control-board legend items 16/21, with its own display code) —
  a **service/commissioning** function that runs the unit independent of the thermostat. Useful
  for a controlled capacity test; **not** a capacity boost and not for continuous operation.
- **"Digital tube display"** (item 18) — the Hz readout already used once. Read it *during* the
  air-side measurements so commanded frequency, air ΔT and condenser watts are captured
  together; that triple distinguishes a starved coil from a maxed one.

#### Should it "just work"? Yes — and the way to help it is to *feed* the loop, not fool it

**Suction pressure *is* the load signal.** Evaporator pressure settles where heat arriving at
the coil balances heat the compressor removes. A hotter, wetter return means more heat into the
refrigerant, higher evaporator pressure, and the control ramps the compressor up. That is a
genuine closed loop on **actual thermal load** — arguably better than a `Y2` contact, which is
only a proxy for load derived from room temperature. So in principle it *does* just work, and
`Y2` would add nothing even if the terminal existed.

**The catch is exactly the one you are circling.** The loop sees load *as delivered to the
coil*, which is `airflow × enthalpy difference`. It **cannot distinguish "low load" from
"plenty of load but not enough air to carry it"** — both present as low suction pressure. So
with constrained airflow, a hot room produces a *slow* compressor, which is the opposite of what
you want and is self-reinforcing (§0.2).

**Airflow is therefore the adjustment, and using it is the control working as designed:**

```
more CFM → more heat into the coil → higher suction pressure → compressor ramps up
```

There are two ways to deliver it, and they stack:

- **The thermostat's `Y2`**, which selects the blower's second-stage speed on a second-stage
  call. This is the demand-following half — it only raises airflow when the zone asks
  for more. **It must be connected for a BOVA zone to reach full capacity on a hot day.**
- **The base CFM setting** on the Unico Smart Controller, which sets the floor both stages work
  from. Software, free, reversible (§0.3 below).

> **⚠️ Do not raise suction pressure artificially.** Overcharging or interfering with the
> pressure transducer would raise the number without raising real capacity — and the board runs
> **low-pressure protection (cooling)** and **compression-ratio protection** off that same
> transducer, so a falsified signal defeats the protections. Feed the coil more heat; do not
> lie to it about how much heat it is getting.

**The tradeoff, which matters because the objective is comfort (§0):** more CFM means a
**warmer coil**, so sensible capacity rises and **dehumidification falls** — the same tension as
the SW4-3 question above. A zone can be pushed to setpoint and still feel clammy.

> **⚠️ The great room now carries three sensible-biased settings at once** — `Y2` fan connected,
> base CFM raised, and `SW4-3` on (adaptive capacity disabled, which holds the coil warmer). All
> three trade latent for sensible in the same direction, so **humidity is the thing to watch
> there**, not temperature. `environment.inside.thermostat.GREAT_ROOM.humidity` is already
> logged, and droop is quantitative from 2026-08-18 (§2.6.0). If that zone holds setpoint but
> reads humid against the other zones, **`SW4-3` off is the setting to give back first** — it
> costs the least capacity now that airflow is no longer the constraint.

**Judging an airflow change costs nothing.** Both BOVAs have their own CT and RedLink logs
per-zone humidity, so compare **droop *and* humidity** across comparable hot days. Two
thermistors (§0.2) additionally show whether air ΔT moved as expected, confirming airflow
changed rather than the ECM merely being told to change it.

> **The structural limit.** The Unico blower and the BOVA compressor **do not communicate** —
> `Y2` couples the *thermostat* to the blower, not the blower to the compressor, so airflow
> follows the thermostat's two-stage demand rather than the compressor's actual state. The
> **Smart Controller's
> only interface is USB for changing settings, and the air handler pauses while fan speed is
> changed** — so dynamic, load-following airflow is off the table. Reverse-engineering the USB
> protocol would not help: the pause is the blocker, not the protocol. **CFM is a static
> setting. Plan around that rather than against it.**

#### A static CFM sets where the compressor operates

This is the useful mental model, and it follows directly from §0.3. The compressor is the only
dynamic element in the pair, and it modulates on suction pressure, which is set by how much heat
the airflow delivers. So:

> **The static CFM setting decides *where in its modulation range the compressor lives*.**
> Higher CFM → higher suction pressure → the compressor runs faster and makes more sensible
> capacity, at a warmer coil and less dehumidification. Lower CFM → the opposite.

That converts an apparently open-ended control problem into a **small, finite tuning exercise**:
two static settings, both free to change, with measurable outcomes.

| Setting | Options | Effect |
|---|---|---|
| Unico CFM | a few settings via USB | Sets the compressor's operating point (above) |
| SW4-3 | ON / OFF | Adaptive capacity disabled vs enabled (§0.3) |

Evaluate each combination on **droop *and* humidity** over comparable hot days — both already
logged per zone. There is no need to solve this dynamically; there is a need to **measure which
static pair is best**, which is exactly what §0.2's two thermistors plus the existing CT and
RedLink humidity deliver.

> **CFM is therefore a seasonal setting, like the Loop B pump tap (§2.5b).** Peak summer wants
> more airflow (maximum sensible, the compressor pushed high); shoulder season wants less
> (better dehumidification at part load). A USB change twice a year is entirely practical even
> though a dynamic one is not — and it is the same kind of manual seasonal ritual already
> established for the pump tap and the glycol top-up. **If you adopt it, add it to that list.**

**Source:** [BOVA-36HDN1-M18M Installation Instructions (Bosch, 06.2016)](https://blobanarus.blob.core.windows.net/boschthermotechnology-boschproducts/BOVA-36HDN1-M18M_Installation_instructions.pdf)

---

## 1. Two corrections before anything else

The Honeywell "10K sensors" are thermistors, not flow sensors. The 10K parts bundled with the
Prestige/IAQ thermostat (C7089U outdoor, C7735A duct) are 10 kΩ-at-77 °F NTC temperature
sensors. They suit supply and return air temperature, and the plan uses them that way, but they
measure temperature. Water flow is a separate purchase (§4).

`pivac.ArduinoSensor` rounds temperatures to whole Kelvin, so it cannot be used as it stands
(`pivac/ArduinoSensor.py:65`):

```python
kelvin = int(round(_to_kelvin(raw, scfg.get("scale", "fahrenheit"))))
```

1 K is 1.8 °F. This project rests on ΔT values of 10–20 °F, so quantising each endpoint to
1.8 °F destroys the measurement before it reaches Signal K. This is the largest blocker in the
existing code. §6 proposes a `rounding:` key, matching the convention `pivac.OneWireTherm`
carries at line 113.

---

## 2. The physics that decides the whole design

### 2.1 The water side measures total capacity; air-side dry bulb measures sensible only

The water side carries everything the coil moved, sensible and latent:

```
Q_total [BTU/hr] = K × GPM × ΔT_water[°F]
```

Air-side dry bulb carries the sensible part alone:

```
Q_sensible [BTU/hr] = 1.08 × CFM × ΔT_air[°F]
```

In cooling these disagree by design. Everything the coil spends condensing water vapour appears
in the water ΔT and not in the air dry-bulb ΔT. On a high-velocity Unico coil the latent
fraction is large, with SHR typically 0.70 to 0.75, so the air-side figure lands 25 to 30 %
below the water-side figure. That gap is the dehumidification.

Heating has no latent load, so the two sides must agree. That makes heating season the
calibration window (§7.2).

### 2.2 K is 481, not 500, because the loop is 25 % glycol

The textbook constant 500 assumes pure water (8.337 lb/gal × 60 × Cp 1.0). With glycol:

```
K = 500.2 × SG × Cp
```

| Fluid | SG | Cp (BTU/lb·°F) | K | Error if you use 500 |
|---|---|---|---|---|
| Water | 1.000 | 1.000 | 500 | — |
| 25 % propylene glycol @ 45 °F *(loop today)* | ~1.028 | ~0.935 | ~481 | +4 % high |
| 25 % propylene glycol @ 140 °F | ~1.010 | ~0.955 | ~483 | +3.5 % high |
| 30 % propylene glycol @ 45 °F *(planned, pre-winter)* | ~1.035 | ~0.920 | ~476 | +5 % high |
| 25 % ethylene glycol @ 45 °F | ~1.035 | ~0.900 | ~466 | +7 % high |

Confirm the glycol type, propylene or ethylene, and verify the concentration with a
refractometer rather than trusting the fill record. Keep `K` in config rather than firmware.
This single number carries a 4 to 7 % systematic bias into every BTU figure the system will
ever produce, which repays ten minutes with a refractometer.

> ⚠️ The planned 25 % to 30 % glycol change creates a discontinuity in the dataset. Three things
> happen at once, and unanticipated they read as a fault.
>
> 1. `K` drops from about 481 to about 476. Update `fluid_k` in `config.yml` on the day of the
>    change. Left stale, every subsequent BTU figure runs about 1 % high. This is why the
>    constant lives in config while the Arduino computes no BTUs (§5): it becomes a `git pull`
>    rather than a reflash.
> 2. Real capacity drops slightly. Higher glycol lowers specific heat and raises viscosity,
>    which reduces flow at the same pump head and slightly worsens the heat-transfer
>    coefficient. Expect a step down of a few percent in capacity and UA.
> 3. Re-measure GPM afterwards if you are running the fixed-flow shortcut (§4.6). The viscosity
>    change moves the operating point on the pump curve, so a flow figure taken at 25 % no
>    longer applies at 30 %.
>
> Add a Grafana annotation on the changeover date. A year from now an unexplained step in the UA
> trend invites a fouling diagnosis.

### 2.3 ΔT precision sets the accuracy of every capacity figure

Capacity error is directly proportional to ΔT error. At a design ΔT_water of 10 °F:

| Per-sensor error | Worst-case ΔT error | Capacity error |
|---|---|---|
| DS18B20 datasheet absolute (±0.9 °F) | ±1.8 °F | ±18 % |
| After matched-pair calibration (±0.05 °F) | ±0.1 °F | ±1 % |

A ±18 % measurement cannot answer whether the coil is delivering its maximum, so **matched-pair
calibration is mandatory** (§7.1). The DS18B20's resolution, 0.0625 °C at 12-bit, and its
repeatability are both excellent. Only the absolute accuracy is poor, and absolute accuracy is
what cancels out of a difference once the offset is characterised.

The same argument covers the 10K NTCs and disposes of a second problem with them. Honeywell 10K
sensors come in more than one resistance curve, Type II at about 32.6 kΩ at 32 °F and Type III
at about 29.5 kΩ. Guessing wrong costs several degrees absolute, but two duct sensors of the
same part calibrated as a pair make the curve error common-mode, and it drops out of ΔT. Verify
the curve regardless with an ice bath: the two types differ by about 10 % at 32 °F, which any
multimeter resolves.

### 2.4 The two ΔTs move in opposite directions, which is why both are worth measuring

The water and air deltas are linked by the energy balance, so when capacity falls, the delta
that moved identifies the constrained side.

| Signature | ΔT_water | ΔT_air | Capacity | Diagnosis |
|---|---|---|---|---|
| Water-starved | up | down | down | Closed or throttled balancing valve, plugged strainer, air-bound coil, failing circulator, zone valve not fully opening |
| Air-starved | down | up | down | Dirty filter, collapsed or undersized duct, blower speed tap, iced coil |
| Plant-limited | normal | normal | down | Entering water temperature is wrong: buffer tank off setpoint, chiller undersized for the load, changeover fault |
| Overpumped | low | normal | at spec | Capacity fine, pump energy wasted. Throttle the balancing valve |

A single delta is ambiguous. Both together isolate the fault.

> ⚠️ A constant-airflow ECM suppresses the air-starved signature until it is severe. The table
> above describes a fixed-speed blower. A constant-airflow ECM holds CFM against rising static
> pressure by drawing more torque, so a moderately dirty filter changes neither ΔT_air nor
> capacity, and shows up only as increased blower watts, which nothing here meters. The
> air-starved signature then appears abruptly and late, once the motor runs out of authority.
> The early warning is the CFM ratio in §7.2. A stable ΔT_air is not evidence of a healthy air
> side.

---

### 2.5 System topology: primary/secondary with two loops

```
  boiler ──[Grundfos UP26-99F]──┐                    ┌── Loop A [UP26-99F, hi/med/lo]
                                ├── PRIMARY HEADER ──┤     └─ lower fam. room · kids · master BR
 chiller ──[Taco, model TBD]────┘  (closely spaced   └── Loop B [UP26-99F, hi/med/lo]
                                       tees)               └─ utility room · kitchen · great room
```

Each source carries its own primary pump; no separate always-on primary circulator exists.
Primary flow is whatever the active source pump delivers, the Taco in cooling and the boiler's
UP26-99F in heating. One three-speed circulator serves each secondary loop, with HZ-432 zone
valves per zone.

The primary return routes to the active source: to the boiler loop when heating, to the chiller
buffer tank when cooling. The buffer tank therefore serves the chilled side only, and heating
runs unbuffered (§2.5e).

Pump settings as of 2026-08-18:

| | Setting | Notes |
|---|---|---|
| Boiler primary (UP26-99F) | HIGH | |
| Chiller primary (Taco) | HIGH | model pending |
| Loop A secondary (UP26-99F) | LOW | 3 zones |
| Loop B secondary (UP26-99F) | LOW | 1 zone summer, 3 winter (§2.5b) |

The seasonal asymmetry drives most of what follows:

| | Loop A | Loop B |
|---|---|---|
| Summer (chilled) | all 3 zones on chilled water | utility room only; kitchen and great room cool via their BOVAs |
| Winter (hot) | all 3 zones | all 3 zones |

**a) Loop B in cooling is a single-zone loop, hydraulically isolated.** One zone valve open and
one pump running leaves nothing to share flow with. If the 2430 is the utility room its
cooling-season flow is constant, the fixed-GPM shortcut in §4.6 holds for the whole cooling
season, and it becomes the easiest first instrumentation target. The loop becomes shared only
in winter, when kitchen and great room join it.

**b) Loop B's speed tap is a seasonal setting.** Set to LOW on 2026-08-18. That circulator is
sized and tapped for three zones in winter but drives one zone in summer, so no single tap
suits the whole year.

| Season | Zones on Loop B | Right tap |
|---|---|---|
| Summer (chilled) | 1, utility room only | LOW. Anything more overpumps a single coil |
| Winter (hot) | 3: utility, kitchen, great room | Higher. LOW across three zones risks starving them |

Overpumping a single coil produces an implausibly small water ΔT of 3 to 5 °F rather than 8 to
12 °F, wastes pump energy, and raises mixing risk (§2.5f). Under-pumping three zones produces
zones that cannot hold setpoint on a cold design day. Treat a very low measured ΔT as a
finding in either direction, rather than a sensor fault.

> ⚠️ Raise this again before heating season. Nothing automates it; it is a manual switch on the
> pump. Add it to the seasonal ritual that already carries the manual breaker-off at the chiller
> and the 25 % to 30 % glycol top-up (§2.2). Left on LOW into winter it would starve the kitchen
> and great room in heating, and would present as a boiler or zone-valve fault rather than a
> pump setting.

While nothing on this loop is instrumented, watch the utility room. If the loop is overpumped,
the room should hold setpoint on LOW exactly as it does on MED, because coil capacity saturates
above design flow (§7.7) and only pump energy changes. No comfort change is the success case
here. If the room instead starts drifting on hot afternoons, LOW sits below design flow for that
coil and should go back to MED. Either outcome is informative and costs nothing, though it
remains a comfort judgement until the coil is instrumented.

**c) Primary HIGH against secondary LOW is the correct asymmetry, so reverse mixing is
unlikely.** A three-speed circulator's LOW runs roughly 50 to 60 % of its HIGH flow at a given
head, so two secondaries on LOW land near one primary on HIGH. The primary header is short and
wide where the secondaries are long and branch-heavy, which pushes the balance further toward
the primary. Primary flow should comfortably exceed combined secondary flow, the condition
closely spaced tees require (§2.5f). Treat the `wsup − IN` check as verification rather than as
a predicted fault.

**d) The same asymmetry raises the sharper question: are the secondaries under-pumped?** Both
secondary loops run on LOW, and each carries three zones in winter, Loop A year-round. The
capacity-versus-flow curve saturates above design flow and falls off steeply below it (§7.7), so
under-pumping is where capacity is lost, and this configuration under-pumps before it
over-pumps. That makes it the more likely finding and the more valuable one.

Water ΔT measures it directly. Above about 15 °F means starved, against a design of 8 to 12 °F.
The worst case is a design-day call with all three zones on a loop open at once. If confirmed,
the remedy ladder is §7.7, and its first rung is free because the secondary taps have two more
speeds above where they sit today.

**e) Cooling is buffered; heating is not.** The primary pump belongs to its source and generally
runs only when that source runs. If a source stops while a secondary pump keeps circulating,
primary flow reaches zero, the secondary recirculates its own return water, and the coil
receives return temperature while the zone still calls.

In cooling the buffer tank prevents this, which is its job. The primary return routes through
the tank, leaving a reservoir of chilled water between compressor cycles.

In heating the primary return goes to the boiler loop and bypasses the tank, so no thermal
reservoir exists. A single small Unico zone calling against a Trinity Ti-200 is a very large
turndown, and an unbuffered condensing boiler at far-below-minimum load short-cycles. Short
cycling costs efficiency and is hard on the boiler.

> This is visible today without new hardware. `hvac.boiler.sentry.gasInputValue` and
> `hvac.boiler.sentry.burnerOn` are already in InfluxDB. Plot burner cycles per hour against the
> number of zones calling. Many short cycles on a one-zone call is the unbuffered-heating
> signature, and the remedy is a buffer or hydraulic separator on the heating side rather than
> anything this node measures. Use `gasInputValue` as the trustworthy signal: CLAUDE.md records
> that `burnerOn` under-reports during calls before the 2026-07-20 LED recalibration.

> Check the cooling side too, since a buffer tank helps only while it holds charge.
> `electrical.emporia.house.chiltrix` separates idle at about 10 W from compressor-running at up
> to 3.6 kW, so correlate the coil's `wsup` against it. Entering water temperature degrading
> during compressor-off periods means the tank is undersized for the cycle or is bypassed. That
> CT covers the Chiltrix circuit, so whether it also sees the Taco depends on how the pump is
> powered (§10).

**f) Primary/secondary decoupling fails by reverse mixing at the tees.** Closely spaced tees
deliver full primary supply temperature only while secondary flow stays at or below primary
flow. A secondary pump drawing more than the primary supplies makes up the deficit by pulling
water backwards from the return tee, blending return water into the supply. Cooling then sends
warmer water to the coil and heating sends cooler. Capacity drops, the symptom resembles a plant
that cannot keep up, and the usual misdiagnosis is an undersized chiller.

> Verification costs one comparison (§2.5c). Compare the node's `wsup`, the water entering this
> coil, against `environment.inside.hvac.IN.temperature`, the primary supply already in
> InfluxDB:
>
> - In cooling, `wsup` warmer than `IN` by more than pipe gain means reverse mixing, with the
>   secondary overpumping relative to primary flow.
> - In heating, `wsup` cooler than `IN` means the same fault with the opposite sign.
>
> Combined secondary flow has to stay under primary flow when both secondary pumps run. Today's
> taps, primary HIGH and secondaries LOW, should satisfy that comfortably. This constraint bounds
> how far the secondaries can be raised if §2.5d proves right and the zones are starved. Raising
> a secondary tap trades a starvation problem for a mixing problem, and `wsup − IN` locates the
> line. Past it, the primary taps already sit at HIGH, so the next step is a larger primary pump.
> Plot `wsup − IN` as a first-class series: it is nearly free and catches a design-level fault
> that coil-side analysis cannot find. Confirm `IN`/`OUT` are the primary header before relying
> on the sign (§10).

---

### 2.6 `IN` and `OUT` straddle the tees, which makes them worth more than a coil node

`IN` sits on the primary supply just before the closely spaced tees and `OUT` on the primary
return just after them. They bracket the entire secondary-side extraction.

#### 2.6.0 ⚠️ Quantitative ΔT data starts 2026-08-18

`pivac.OneWireTherm` reads in Kelvin whenever the output is Signal K
(`pivac/OneWireTherm.py:99`), so the config's `rounding` is a precision setting. It is set to
`rounding: 2`, about 0.018 °F, which captures the DS18B20's full 0.0625 °C resolution and
propagates to every sensor.

InfluxDB history before 2026-08-18 is integer Kelvin at 1.8 °F granularity, because
`rounding: 0` was in force until then. A ΔT built from two such readings moves in 1.8 °F steps
with up to ±1.8 °F of error:

| Quantity | True value | What the old data can say |
|---|---|---|
| Secondary ΔT | 10 °F | ±18 %, about 6 distinct values across the operating range |
| Primary ΔT | 4 °F | ±45 %, two or three distinct values. Unusable |

Every ΔT analysis below must therefore start at 2026-08-18. The pre-fix period cannot be
recovered; the information is not in it. `pivac.RedLink` carried the same defect and truncated
rather than rounded, biasing every zone temperature up to 1.8 °F low, and is fixed as of the
same date.

> Resetting `rounding` to `0` stops everything in §2.6 from working. Keep it at 2 or higher. If
> a WilhelmSK gauge shows noisy decimals, set the precision in the app.

#### 2.6.1 One flow meter on the primary measures the whole house

```
Q_all_zones = K × GPM_primary × (IN − OUT)
```

Because `IN` and `OUT` bracket the tees, this is total delivered capacity across every hydronic
zone, from sensors already installed. Adding the one missing term also gives system COP in
cooling, against `electrical.emporia.house.chiltrix`, and delivered-versus-fired efficiency in
heating, against `hvac.boiler.sentry.gasInputValue`.

This is the highest-value flow meter in the system, and it sits on the primary rather than on a
coil. One sensor answers whether the plant is efficient and how much heat the house is moving,
which per-coil instrumentation cannot reach.

#### 2.6.2 The flow ratio falls out of temperatures alone

Closely spaced tees mix, and mixing is arithmetic. With one secondary loop active, primary
supply `T_ps` (= `IN`), primary return `T_pr` (= `OUT`), and secondary return `T_sr`:

```
T_pr = [ (GPM_pri − GPM_sec)·T_ps  +  GPM_sec·T_sr ] / GPM_pri
```

which rearranges to

```
GPM_sec / GPM_pri  =  (T_ps − T_pr) / (T_ps − T_sr)  =  ΔT_primary / ΔT_secondary
```

The ratio of the two ΔTs is the flow ratio. It holds in both regimes: a secondary that overdraws
pulls back through the return tee and the ratio exceeds 1, which is the reverse-mixing
condition.

| ΔT_pri / ΔT_sec | Meaning |
|---|---|
| < 1 | Primary flow exceeds secondary. Healthy decoupling, coil gets full primary temperature |
| ≈ 1 | Flows matched, on the edge |
| > 1 | Secondary overdraws. Reverse mixing, coil entering temperature degraded (§2.5f) |

A supply sensor on each loop gives the same answer a second way. Loop supply temperature equal
to `IN` means no mixing, and divergence from it means mixing. Two independent routes to the same
conclusion, both from thermometers.

One accuracy caveat. This is a ratio of two differences, so when primary flow greatly exceeds
secondary, ΔT_primary is small and its relative error dominates. At a 0.4 flow ratio and a 10 °F
secondary ΔT, primary ΔT is 4 °F, which works after §2.6.0 and pair calibration and fails
before. `IN` and `OUT` need the same matched-pair treatment as §7.1, and have almost certainly
never had it.

#### 2.6.3 Loop B idling isolates Loop A, and the sensors detect it themselves

In summer Loop B serves only the utility room, so whenever that zone is not calling, `IN − OUT`
reflects Loop A alone, the single-secondary case §2.6.2 assumes.

The utility zone has no RedLink thermostat, so its call state is not in pivac. It need not be.
A loop with its pump off and its zone valve shut shows supply and return converging and both
drifting toward ambient, so `|ΔT_loopB| < ~1 °F` is a reliable idle flag and no GPIO input is
required. CLAUDE.md lists BCM 13/33, 16/36 and 24/18 as free inputs with existing wire runs if a
hard signal is ever wanted.

#### 2.6.4 What four DS18B20s measure

Add supply and return on each secondary loop, `LOOPA_SUP`, `LOOPA_RET`, `LOOPB_SUP` and
`LOOPB_RET`, on the Pi's existing 1-wire bus, taking it from 4 sensors to 8. With `IN` and `OUT`
they yield five things, with no Arduino and no flow meter:

- Per-loop ΔT, answering the starvation question from §2.5d, where above 15 °F means starved.
- Per-loop flow ratio (§2.6.2), including whether reverse mixing occurs and under which
  combination of calls.
- A mixing check, loop supply against `IN` (§2.6.2).
- Loop-idle detection (§2.6.3), which enables the Loop A isolation.
- Loop-level attribution: whether a shortfall belongs to Loop A, Loop B, or the plant.

One primary flow meter (§2.6.1) then converts every ratio into an absolute GPM and every ΔT into
absolute BTU/hr, for all loops at once.

This sets the order of work. The per-coil Arduino node remains the only way to attribute within
a loop and the only route to the air-side sensible and latent split, but it sits after the loop
sensors and the primary flow meter, which cost less and answer larger questions.

> Name these once. They become InfluxDB measurement names, and CLAUDE.md records four renames
> that each orphaned history. Choose `LOOPA_SUP`, `LOOPA_RET`, `LOOPB_SUP` and `LOOPB_RET` now
> and do not revisit. Adding paths needs no Signal K restart; only removing them does.
>
> While editing that config block, note the `0316a015e7ff: Unassigned` entry. It is the ROM of
> the DS18B20 on the .114 DHW Arduino, which is not on the Pi's bus. OneWireTherm iterates found
> sensors and looks names up, so it is harmless, but it misleads beside eight real entries and
> deserves a clarifying comment or removal.

---

## 3. Scope boundary

Out of scope, so the change stays reviewable:

- The DX/BOVA zones, kitchen and great room. Those are refrigerant rather than water, and none
  of the hydronic analysis applies to them.
- The boiler and Sentry path, DHW, domestic water, irrigation, and the two pressure Arduinos.
- The existing 1-Wire bus on the Pi (`pivac.OneWireTherm`). The new water sensors go on the
  Arduino (§4.1).
- No InfluxDB data is deleted and no existing Signal K path is renamed.

---

## 4. Hardware

### 4.1 Everything hangs off one Arduino at the air handler

All sensors go on the node rather than split between the node and the Pi's 1-Wire bus, for
three reasons.

Simultaneity comes first. `Q = K × GPM × ΔT` holds only if flow and both temperatures are
sampled at the same instant, and two collectors polling on different schedules cannot deliver
that.

Cable length comes second. 1-Wire is finicky over long runs, and the Pi's bus already has a
documented history of the OUT sensor dropping off for hours (CLAUDE.md, 2026-05-31). A 30 cm run
inside the air handler cabinet carries none of that risk.

Precedent comes third. The DHW board at 10.0.0.114 already runs a DS18B20 on an UNO R4 alongside
its analog sensor, so the pattern is proven on this system.

One board per air handler, DHCP-reserved by MAC in UniFi like the others.

### 4.2 Bill of materials

| Qty | Item | Notes |
|---|---|---|
| 1 | Arduino UNO R4 WiFi | Same as every other pivac node; the 14-bit ADC suffices (§4.4) |
| 2 | DS18B20, stainless probe | Water supply and return. Waterproof probe version |
| 2 | Brass thermowell or pipe clamp with insulation | See §4.3 |
| 1 | 4.7 kΩ resistor | 1-Wire pull-up, DQ to 5 V. External, not the internal pull-up |
| 2 | Honeywell 10K NTC duct sensors | Already on hand. Supply and return air |
| 2 | 10.0 kΩ 0.1 % metal-film resistor | Divider reference. Tolerance becomes temperature error |
| 2 | 0.1 µF ceramic | ADC anti-alias, across the NTC leg |
| 1 | Water flow sensor, pulse output | §4.5, the one substantive decision |
| 1 | 5 V PSU or USB supply | Consider the Arduinos Shelly (§8) |
| — | Pipe insulation, cable glands, enclosure | |

Optional, for Phase 2 (§7.3):

| Qty | Item | Notes |
|---|---|---|
| 1 | SHT41 or SHT31 T/RH sensor, I²C | Return-air humidity for the latent split. Probably unnecessary, since the IAQ thermostat supplies it through RedLink (§7.3). Measure before buying |

### 4.3 Water temperature: thermowell against strap-on

A thermowell is the correct method and a strap-on is acceptable with proper insulation.

A brass thermowell, ½" NPT into a tee, puts the probe in the stream and reads fast and
unambiguously. It requires cutting the pipe and draining that section of a glycol loop.

A strap-on clamps the DS18B20 to bare, cleaned copper with thermal compound, then buries it
under at least 25 mm of insulation extending 100 mm either side. On copper at these flow rates
it reads within a few tenths of a °F of the fluid. Skimping on insulation ruins strap-on
installs: an uninsulated probe reads somewhere between the water and the room, and the error
differs on the hot and cold pipes, which is the worst case for a ΔT.

Draining a glycol loop is a chore, so strap-on with thorough insulation is the pragmatic choice,
provided you run the in-situ pair calibration in §7.1, which measures and removes this class of
installation error.

Mount both probes on straight pipe, at least 5 diameters downstream of any fitting, as close to
the coil connections as possible, so the measurement covers the coil rather than the piping run.

### 4.4 Air temperature: reading the 10K NTCs

Standard ratiometric divider, one per sensor:

```
 5V ──[ 10.0 kΩ 0.1% ]──┬── A0  (and A1 for the second)
                        │
                     [ 10K NTC ]
                        │
                       GND         0.1 µF from A0 to GND
```

The ratiometric arrangement is the point. The divider is fed from the same 5 V the ADC uses as
its reference, so supply variation cancels. Do not add a separate precision reference.

Set `analogReadResolution(14)` on the RA4M1. Near room temperature the divider gives about
31 mV/°F against a 0.305 mV LSB, roughly 0.01 °F per count, so noise dominates rather than
resolution. Average 100 to 256 samples per reported reading. Convert with Steinhart-Hart or a
beta fit using the curve confirmed by the ice-bath test in §2.3, keeping the coefficients in
firmware as sensor-physics constants and the per-sensor offset in config (§6). Self-heating is
negligible in a moving airstream, about 0.6 mW in a 10 kΩ leg.

Probe placement matters more than probe accuracy. Put the return sensor in the return plenum
upstream of the coil, out of line of sight of the coil face. Put the supply sensor in the supply
plenum downstream of the blower and before the first takeoff, because on a Unico the blower does
the mixing and a sensor at the coil face reads a stratified, unrepresentative slice. Shield both
from radiation, since a sensor that can see a 45 °F coil reads low regardless of air
temperature. In cooling the supply sensor sits in roughly 95 % RH air, so seal the probe body
and route the leads downward to stop condensate wicking into the cable.

### 4.5 Water flow: the one substantive purchase

Sizing, for an M2430 at a nominal 2 tons:

```
24,000 BTU/hr ÷ (481 × 10 °F ΔT) ≈ 5 GPM
```

Specify for 3 to 8 GPM in ¾" to 1" pipe, with 25 % glycol, over a service range spanning chilled
duty near 45 °F and heating duty up to about 140 °F. That temperature span rules out most
domestic water meters.

| Option | Cost | Verdict |
|---|---|---|
| Hydronic paddlewheel or turbine with pulse output (Seametrics SPX, Omega FTB, Onicon F-1100), brass or stainless, rated 200 °F or above | $200–400 | Recommended. Rated for the fluid, the temperature, and continuous duty |
| Brass-body hall turbine (Digiten or Gredia class, 212 °F rated) | ~$25 | Workable budget path. Plastic rotor and bearing wear plus calibration drift in continuous hot glycol are the risks. Re-verify annually against the energy balance |
| Clamp-on ultrasonic | $$$ | No plumbing cut and glycol-agnostic. Best if you would rather not open the loop |
| DAE MJ-75a class, as on the domestic meter | ~$60 | Unsuitable. Nutating-disc domestic meters are typically rated to about 120 °F and are not intended for closed-loop glycol |

> CLAUDE.md documents a cheap hall turbine failing on the irrigation line, but the root cause was
> a mismatch with OpenSprinkler's pulse-rate handling, above 50 Hz at 0.0025 gal/pulse or less,
> rather than a defect in the sensor class. On a dedicated Arduino ISR a high pulse rate is an
> advantage, since it supplies instantaneous flow resolution. Rule out plastic turbines on
> temperature and duty cycle, and keep metal ones in consideration.

### 4.6 Whether you need a flow meter depends on which loop the 2430 is on

This single fact decides the bill of materials, and §2.5 splits it cleanly.

| If the 2430 is… | Cooling season | Winter | Verdict |
|---|---|---|---|
| Utility room (Loop B) | Single-zone loop, flow constant. Nothing to share with | Shares Loop B with kitchen and great room | Start without a meter. Measure GPM once, run all cooling season on a constant, add the meter before winter if the data warrants |
| Family room, kids or master (Loop A) | Shares with two other zones, which all call together on hot days | Same | Buy the meter. Per-zone flow varies exactly when it matters |

The utility room allows the whole chain to be commissioned cheaply, on constant flow, letting a
season of data decide whether the meter is worth buying. That is a better starting position than
Loop A, and worth weighing when choosing which handler to instrument first, even though Loop A
holds the comfort complaint.

Sharing matters on Loop A because three zone valves on one fixed-speed circulator are
hydraulically coupled. Opening a second valve lowers loop head, so flow through this coil drops.
Per-zone GPM becomes a function of how many other zones are calling, and it reaches its minimum
on design days when all three run together, which is when the capacity figure most needs to be
right. A fixed constant would be accurate single-zone and would overstate capacity whenever it
matters.

One cheap test settles it either way. At a steady outdoor condition, log this coil's ΔT_water
with one zone calling, then with two or three. A material rise in ΔT at the same entering water
temperature means the zones share flow. An afternoon decides a $200–400 purchase, and on Loop A
it quantifies the starvation directly.

The three-speed tap acts per loop rather than per zone. It changes total loop flow, raising or
lowering every zone together, and cannot redistribute between them. That distinction drives §7.7.

### 4.7 Pin map

| Signal | Pin | Notes |
|---|---|---|
| DS18B20 ×2, water supply and return | D2 | One shared 1-Wire bus, addressed by ROM. 4.7 kΩ to 5 V |
| Flow sensor pulse | D3 | Interrupt-capable. Debounce in the ISR |
| Return-air NTC | A0 | Divider per §4.4 |
| Supply-air NTC | A1 | Divider per §4.4 |
| SHT41 T/RH (Phase 2) | A4/A5 | I²C |

Avoid D0/D1 (Serial1), D4/D5 (CAN) and D10 to D13 (SPI). The free general-purpose pins on the R4
are D2, D3, D6, D7, D8 and D9, and this design uses two.

**Record both DS18B20 ROM addresses in this document during the build.** CLAUDE.md carries a
hard-won warning that the printed tags on these probes are unreliable as physical identifiers,
one probe having been found carrying two tags, and that the .114 board's DS18B20 ROM exists in
neither repo.

---

### 4.8 Utility-room instrumentation beyond this node

The air handler answers "is *this coil* delivering". The mechanical room answers "is the
*plant* healthy", and several of those sensors are cheaper and higher-value than the coil node.
Ranked by value per dollar **against the §0 objective: summer comfort and capacity.**

#### Tier 1 — do these

| Sensor | Where | Why |
|---|---|---|
| 4× DS18B20 — supply + return on each secondary loop | Loop A and Loop B, at the tees | §2.6.4. Starvation, flow ratios, mixing, loop-idle detection. The highest-value addition in this document |
| 1× DS18B20 — boiler *return* | Boiler return, before the primary tee | Condensing verification. Monitor-only per §0 — David is content for the boiler not to condense, so this is a "know the number" probe, not an optimisation target |
| 1× T/RH sensor — room ambient | Mechanical room, away from the boiler | Standby losses, and it explains a *documented* problem — see below |
| Leak / flood detection | Pan under boiler, buffer tank, booster pump | This is a regression — see below |

**Boiler return temperature: record it, do not chase it (§0).** A
Trinity Ti-200 is a *condensing* boiler, and it only condenses when return water is below the
flue-gas dew point — roughly **130 °F**. Above that you lose most of the condensing gain
(order 10 % efficiency). Hydronic air-handler coils are commonly designed around 140–180 °F
supply, which puts return water **above** the condensing threshold, so it is entirely possible
this boiler **never condenses in this application** and nobody would know. The Sentry already
gives boiler supply (`hvac.boiler.sentry.waterTemp`) and outdoor temp; one DS18B20 on the
return closes it. If it confirms non-condensing, the remedy would be **outdoor reset** — lower supply temperature
in mild weather — but that trades **coil capacity** for efficiency, and per §0 capacity is the
priority and heating is rarely the problem. **So: record it, do not act on it.** Kept in Tier 1
only because it is one probe on a bus that is already being extended.

**Room ambient explains a problem already in CLAUDE.md.** The Pi is a **fanless Pi 4** that runs
at ~76 °C with ~83 °C peaks during Sentry capture bursts, grazing the 80 °C soft-temp limit —
and CLAUDE.md explicitly notes "Ambient matters too (summer boiler-room heat)" while having no
way to measure it. A room temperature series turns that from a hypothesis into a correlation,
and tells you whether ventilation would buy more than any further `daemon_sleep` tuning (which
CLAUDE.md says cannot fix the peaks anyway). Humidity is a bonus: a mechanical room that runs
humid in summer is a mold and corrosion risk, and it also flags chilled-pipe sweating from
insulation gaps.

> **⚠️ Leak detection was lost, not retired.** CLAUDE.md records that BCM 25 carried the
> **booster-pump leak pan** as `SCALA` until 2026-08-11, when the input was renamed in place to
> `CHIL` to sense the chiller call — "the leak-pan signal is no longer published." That was a
> deliberate trade of one input for another, but the *result* is that a room containing the
> boiler, buffer tank, DHW, booster pump and the domestic water main **currently has no water
> detection at all.** Free GPIO inputs with existing wire runs are listed as BCM 13/33, 16/36
> and 24/18. This is the cheapest insurance in the whole document and it is not about
> BTUs. (Avoid BCM 26 — CLAUDE.md documents that pad as permanently dead.)

#### Tier 2 — high value, some cost

| Sensor | Why |
|---|---|
| Flow meter on the primary loop | §2.6.1 — whole-house delivered BTU, system COP, boiler delivered-vs-fired efficiency. Converts every ratio in §2.6.2 into an absolute number |
| 2× DS18B20 — Chiltrix entering/leaving water | Chiller-side ΔT; with `electrical.emporia.house.chiltrix` gives chiller COP directly, separate from distribution losses. Skip if the CX75 exposes these over Modbus (§10) |
| CTs on the circulators | Definitive pump-running state (better than the §2.6.3 inference), pump energy accounting so the §7.7 flow tradeoff is *measurable* rather than argued, and a failing circulator shows as changed draw. Needs spare Emporia channels — note CLAUDE.md records four CTs were borrowed from the apartment panel for the Chiltrix |

#### Tier 3

| Sensor | Why |
|---|---|
| Differential-pressure transducer across a secondary loop | An alternative to a flow meter: read ΔP, look up flow on the pump curve. Often taps existing ports, so no pipe cutting — attractive if opening a glycol loop is the objection |
| Boiler flue temperature | Direct efficiency indicator; high flue temp is heat going up the stack. Complements the condensing check above |
| Condensate trap float switch | A blocked condensate trap shuts a condensing boiler down. Cheap, and it fails at the worst time of year |
| CO detector with a monitored contact | Safety rather than optimization, but it is a gas appliance in an occupied building and the GPIO inputs are already there |

#### Wiring note

Tier 1's five DS18B20s go on the **Pi's existing 1-wire bus**, taking it from 4 sensors to 9.
That is well within 1-Wire's addressing limits, but watch total cable length and topology —
prefer a daisy chain over a star, and consider dropping the pull-up to **2.2–3.3 kΩ** as the
bus grows (§5 of `docs/circ-loop-temp-monitoring-plan.md` covers this). `pivac.OneWireTherm`
re-scans every cycle since 2026-07-06, so sensors can be added live and appear within one
daemon cycle with **no restart**. The T/RH sensor and the leak detector are not 1-Wire: RH
wants I²C (so it belongs on an Arduino, or a small dedicated node), and a leak pan is a dry
contact straight into a spare GPIO.

---

## 5. Firmware contract

**The Arduino emits raw measurements only. It computes no BTUs.**

Rationale, and it is a repo-grounded one: the DHW board's recirc-temperature sketch was never
committed and exists only on the M2 MacBook, so reflashing that board would silently drop a
sensor. Firmware here is the *expensive, fragile* place to put anything you might want to
change. Calibration offsets, the glycol constant `K`, and the capacity maths all belong in
`config.yml` and Python, where they are version-controlled and deploy with a `git pull`.

Response dict, matching the existing single-quoted pseudo-JSON convention that
`ArduinoSensor` parses with `ast.literal_eval`:

```
{'wsup' : 118.42, 'wret' : 108.31, 'asup' : 96.10, 'aret' : 70.44,
 'flow' : 4.92, 'volume' : 10432.5, 'uptime_ms' : 84213}
```

| Field | Unit | Meaning |
|---|---|---|
| `wsup` | °F | Water entering the coil |
| `wret` | °F | Water leaving the coil |
| `asup` | °F | Supply (leaving) air |
| `aret` | °F | Return (entering) air |
| `flow` | gal/min | Rolling-window instantaneous flow |
| `volume` | gal | Lifetime totalizer, EEPROM-persisted |
| `uptime_ms` | ms | Low value ⇒ recently rebooted (power event) — same diagnostic as the pressure boards |

**Emit two decimal places on every temperature.** The precision has to survive all the way to
the delta; see §6.

Reuse the proven scaffolding from `DomesticWater.ino`: D-pin reed/pulse interrupt with
debounce, EEPROM totalizer with magic marker, 10 s rolling flow window, RA4M1 watchdog,
bounded WiFi/HTTP handling. Add the DS18B20 read (12-bit) and the two averaged ADC reads.

**Disconnected-sensor behaviour:** a DS18B20 that fails to read returns `-127` and an open NTC
divider rails to full scale. Emit a sentinel (`-999`) rather than a plausible-looking number,
so the Pi side can drop the sample instead of computing a confident, wrong BTU figure.

---

## 6. pivac integration

### 6.1 Required change to `pivac.ArduinoSensor` — add `rounding:`

`ArduinoSensor` currently hardcodes `int(round(...))` on every `type: temperature` field.
Add an optional per-input `rounding:` key, **defaulting to `0` so every existing input is
byte-for-byte unchanged**:

```python
digits = scfg.get("rounding", 0)
k = _to_kelvin(raw, scfg.get("scale", "fahrenheit"))
kelvin = int(round(k)) if digits == 0 else round(k, digits)
```

This mirrors `pivac.OneWireTherm` (`pivac/OneWireTherm.py:113`), which has had exactly this
per-sensor `rounding` key all along — so it is not a new concept in the codebase, just one
that never made it into the Arduino path. The DHW recirc input keeps `rounding: 0` and its
InfluxDB series is undisturbed; the new inputs use `rounding: 2`.

### 6.2 New module `pivac.UnicoAH` — wrapping, not replacing

Same pattern as `pivac.DomesticWater` wrapping `pivac.ArduinoSensor`: call through for the raw
fields, then append derived values. Keeps all physics in Python, all constants in config.

Derived, per cycle:

```
ΔT_water  = wsup - wret                       (°F, sign follows mode)
ΔT_air    = asup - aret
Q_total   = K × GPM × |ΔT_water|              (BTU/hr)
Q_sens    = 1.08 × CFM × |ΔT_air|             (BTU/hr, needs CFM — §7.2)
SHR       = Q_sens / Q_total                  (cooling only)
UA        = Q_total / |aret - wsup|           (BTU/hr·°F — the fouling metric, §7.4)
running   = flow > flow_threshold             (0/1)
```

**Gate everything on `running`.** A ΔT computed on a dead coil is noise, and a UA computed on
a near-zero denominator is a divide-by-zero waiting to happen. Emit `0`/null for the derived
values when the coil is off rather than propagating garbage — and additionally suppress the
first **5 minutes** after start, because the coil, the water in it, and the duct mass all need
to reach steady state before the energy balance closes.

### 6.3 Signal K paths

> **Name these carefully now.** The SK path *is* the InfluxDB measurement name. CLAUDE.md
> records four separate renames (CRW→UBT, AMB→LBT, the relay roster, the Emporia circuits)
> that each orphaned their history. Adding a second air handler later must not force a rename
> of the first, hence the `<unit>` level in the path.

| Path | Unit | Source |
|---|---|---|
| `environment.inside.hvac.ah.mbr.water.supply.temperature` | K | node |
| `environment.inside.hvac.ah.mbr.water.return.temperature` | K | node |
| `environment.inside.hvac.ah.mbr.air.supply.temperature` | K | node |
| `environment.inside.hvac.ah.mbr.air.return.temperature` | K | node |
| `environment.inside.hvac.ah.mbr.water.flowRate` | gal/min | node |
| `environment.inside.hvac.ah.mbr.water.consumption` | gal | node (totalizer, drift check) |
| `environment.inside.hvac.ah.mbr.water.deltaT` | °F | derived |
| `environment.inside.hvac.ah.mbr.air.deltaT` | °F | derived |
| `environment.inside.hvac.ah.mbr.capacity.total` | BTU/hr | derived |
| `environment.inside.hvac.ah.mbr.capacity.sensible` | BTU/hr | derived |
| `environment.inside.hvac.ah.mbr.capacity.ua` | BTU/hr·°F | derived |
| `environment.inside.hvac.ah.mbr.shr` | ratio | derived |
| `environment.inside.hvac.ah.mbr.running` | 0/1 | derived |

> **⚠️ A ΔT must never go through `type: temperature`.** That branch adds 273.15 — correct for
> an absolute temperature, catastrophic for a difference. Emit the deltas as plain untyped
> numbers from the wrapper module. A `deltaT` of 10 °F arriving in InfluxDB as 283.15 is the
> kind of bug that looks like a plausible temperature and survives review.

### 6.4 Config sketch

```yaml
pivac.UnicoAH_MBR:
    description: Unico M2430 hydronic air handler — capacity monitoring
    module: pivac.UnicoAH
    enabled: true
    ipaddr: 10.0.0.xxx
    daemon_sleep: 15
    sk_path: environment.inside.hvac.ah.mbr

    # --- physics constants (see §2.2) ---
    fluid_k: 481.0          # 25% PG today -> ~476.0 after the 30% top-up (§2.2)
    nominal_cfm:            # COMMANDED airflow from the Unico Smart Controller (§7.2)
        cooling: 900        #   read off the controller config, per mode
        heating: 800
    flow_gpm_fixed: null    # set a number for the Phase-0 constant-flow shortcut
    flow_threshold: 0.5     # gal/min below which the coil counts as off
    settle_seconds: 300     # ignore the first 5 min of a call

    # --- per-sensor calibration offsets, °F (see §7.1) ---
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
            rounding: 2     # REQUIRED — see §6.1
        # ... wret / asup / aret identically
        flow:
            sk_path: environment.inside.hvac.ah.mbr.water
            outname: flowRate
```

---

## 7. Calibration and analysis

### 7.1 Matched-pair calibration (do this before install — it is not optional)

Per §2.3 this is what turns a ±18 % measurement into a ±1 % one.

1. Wire all four sensors to the board **on the bench**, running the final firmware.
2. Bundle the two **water** probes together in a stirred bath (an insulated jug of water is
   fine — stability matters far more than knowing the true temperature).
3. Log for **≥15 minutes** at the production sample rate. Take the **mean difference**, not a
   spot reading.
4. Repeat at a second temperature spanning the working range — ice water and hand-hot — so you
   know whether the offset is constant or drifts with temperature. If it drifts materially,
   fit a slope instead of a constant.
5. Repeat steps 2–4 for the two **air** NTCs.
6. Write the offsets into `offsets:` in config. **Do not bake them into firmware** — you will
   want to re-verify them annually.

**Acceptance:** after applying offsets, the two water probes in a common bath should agree to
**within 0.1 °F**. If they do not, you cannot trust a 10 °F ΔT to better than a few percent.

### 7.2 CFM is *commanded*, not unknown — so the energy balance becomes a diagnostic

The Unico Smart Controller's ECM is configured in software, so **read the commanded airflow
per mode off the controller** and put it in `nominal_cfm`. That removes the hardest unknown on
the air side outright — no derivation needed to get sensible capacity.

The interesting part is what the energy balance is now *for*. In **heating there is no latent
load** (§2.1), so the two sides must agree, and you can solve the balance for airflow:

```
CFM_derived = (K × GPM × ΔT_water) / (1.08 × ΔT_air)      [heating only]
```

Because you already know what the ECM was *told* to deliver, comparing the two is far more
valuable than either number alone. **Track `CFM_derived / CFM_commanded` as a first-class
series:**

| Ratio | Meaning |
|---|---|
| ≈ 1.0 | The entire measurement chain is validated end to end — flow-meter calibration, all four temperature offsets, and the blower all agree. This is also your acceptance test for the whole build |
| Drifting down over weeks/months | The ECM is losing its fight with static pressure. Dirty filter or developing duct restriction. This is the *early* warning the ECM otherwise hides (§2.4) — it masks restriction by drawing more torque until it can't |
| Sudden step | Something changed physically — filter swap, damper position, a sensor knocked loose, or the controller reconfigured |
| Persistently ≠ 1.0 from day one | A calibration error, not a fault. Suspect the flow meter's K-factor first, then the temperature offsets |

Because this coil does **both** heating and cooling off the same water, you get this check
every winter for free. Then carry `nominal_cfm` into cooling to split total capacity into
sensible and latent.

**Capture the commanded CFM per mode.** A Smart Controller will typically be configured with
*different* airflow for heating and cooling, and possibly per stage or per demand level — so
`nominal_cfm` should be a small map keyed by mode, not one number. If the controller can
report its live commanded airflow over a serial/Modbus link, reading it directly is better
than a static config value; check the controller documentation.

Minor caveats, both ignorable next to everything else here: air density differs a little
between 110 °F and 55 °F supply air (~5 %), and the balance assumes steady state, which §7.6
already enforces.

### 7.3 Phase 2 — you may already have the humidity you need

Entering-air wet-bulb drives a chilled-water coil's capacity, and it is
what splits total into sensible and latent. Getting it needs entering dry-bulb (you will have
that at full precision from your own `aret` NTC) plus entering RH.

**The IAQ thermostat already supplies the RH.** `pivac.RedLink` publishes
`environment.inside.thermostat.<ZONE>.humidity` for every zone today
(`pivac/RedLink.py:331`, emitted as a 0–1 fraction). Return air *is* room air, so the zone
thermostat's RH is a good proxy for entering-air RH — the error is duct leakage and
infiltration into the return, not a modelling gap.

So Phase 2 is largely **a software join, not a hardware purchase**: combine your `aret`
dry-bulb with the RedLink humidity for the same zone to get entering enthalpy, which supplies

- **True SHR / latent split**, independent of the stored CFM;
- **A CFM derivation that works in cooling too**, via `Q_total = 4.5 × CFM × Δh`, so you are
  no longer restricted to the winter check in §7.2;
- The physically correct denominator for coil performance in §7.4.

Two caveats worth respecting. RedLink temperatures are rounded to whole Kelvin
(`int(ktemp)`, `pivac/RedLink.py:329`) — so take **temperature from your own NTC** and only
**humidity** from the thermostat. And RedLink polls on its own schedule with a documented
15–25 % per-device timeout rate, so the humidity series is coarser and gappier than the node's
own data; interpolate and tolerate gaps rather than dropping the sample.

**Add an SHT41 in the return plenum only if that proves inadequate** — measure first. Measuring
*supply* humidity is deliberately not proposed either way: off a wet coil that air sits at
90–98 % RH, which is both hard to measure accurately and hard on the sensor.

### 7.4 What "maximum BTUs" means, and how to tell if you have it

Capacity is a function of five things: **entering water temp, water flow, air flow, entering
air wet-bulb, and coil cleanliness.** Raw BTU/hr is therefore not a target — it legitimately
varies with weather. Two normalised metrics are:

**a) UA — the fouling and health metric**

```
UA = Q_total / |T_return_air − T_water_supply|
```

This divides out both the weather and the plant, leaving coil effectiveness. **At a given
GPM and CFM, UA should be constant.** Plot it over months: a steady decline is fouling
(air-side dirt or water-side scale/sludge) and is the clearest possible "your coil is getting
worse" signal. This is the single most valuable series this project produces.

**b) Capacity vs. the manufacturer's rating**

Pull the Unico coil rating table for your coil at your EWT/GPM/CFM and compare. That tells you
whether you are short of *design*, which is a different question from whether you are short of
*last year*.

**Then apply the §2.4 table.** Sort your steady-state samples by capacity, take the worst
decile, and look at which delta is anomalous. That is your constraint.

### 7.5 Use the data you already have — the highest-value analysis needs no new hardware

Already flowing into InfluxDB and directly relevant:

| Existing series | Use |
|---|---|
| `electrical.emporia.house.chiltrix` (W) | Plant power — the denominator of COP |
| `environment.inside.hvac.UBT/LBT.temperature` | Buffer tank stratification — is the plant keeping up? |
| `environment.inside.hvac.IN/OUT.temperature` | Primary header supply/return — plant-level ΔT, and the reference for the reverse-mixing check `wsup − IN` (§2.5c) |
| `environment.inside.thermostat.<zone>.temperature` | Zone response: is the room recovering? |
| `environment.inside.thermostat.<zone>.humidity` | Entering-air RH — the latent split, free (§7.3) |
| `environment.outside.thermostat.temperature` | Load normalisation |
| `electrical.ac.switch.utility.CHIL` / `BLR` | Changeover mode (chilled vs hot water) — *not* a per-zone gate, see below |
| `electrical.ac.switch.utility.ZV` | Any zone valve open — system-level, same caveat |
| `electrical.ac.arduinoThermPSI.psi` | Loop pressure — a drop precedes air-bound-coil symptoms |

> **⚠️ `CHIL` is a system-wide call, not this zone's.** It asserts when **any** water-cooled
> zone calls via the HZ-432, so with three zone valves on three air handlers it is true during
> plenty of periods when *this* coil's valve is shut and its flow is zero. **Never gate a
> per-air-handler calculation on `CHIL`** — the correct gate is the node's own flow
> (`running = flow > flow_threshold`, §6.2), which is per-coil by construction.
>
> What `CHIL` and `BLR` *are* good for is **changeover mode** — telling you whether the water
> arriving is chilled or hot, which selects the sign convention, the mode's `nominal_cfm`, and
> whether a latent term exists at all. Even that is available without them: `wsup` around 45 °F
> is cooling and around 120–140 °F is heating, so **the node can determine its own mode from
> the supply water temperature** and the relays are only a cross-check. Prefer the
> self-determining version — it keeps the node correct even if the relay roster changes again.

> **The shortcut worth considering before the per-air-handler build.** If `IN`/`OUT` are the
> primary-loop supply and return, then **one flow meter on the primary loop** gives you
> whole-system capacity — and combined with `electrical.emporia.house.chiltrix` you get
> **system COP**, today, from data you already collect:
>
> ```
> COP = (K × GPM_primary × |T_IN − T_OUT|) / (W_chiltrix × 3.412)
> ```
>
> That answers "is the plant efficient" for one sensor. The per-air-handler build answers a
> different and complementary question — "is *this zone* getting its share" — which plant-level data cannot answer. One meter
> buys the other half cheaply. **Confirm what `IN`/`OUT` are physically on before relying on
> this** — it is an inference from the naming, not a verified fact.

Also worth checking: **the Chiltrix CX-series exposes Modbus RTU** with entering/leaving water
temperature, compressor state, and on some models flow. If the CX75 does, an RS485 adapter
gets plant-side data with no plumbing work at all. Verify against the unit's manual.

### 7.6 Sampling discipline

- **Gate on `running` and discard the first 5 minutes** of every call (§6.2). Startup
  transients will otherwise dominate your dataset and they are not representative of anything.
- Aggregate to **1–5 minute means** before analysis. Instantaneous BTU/hr is noisy; nothing in
  this problem changes fast.
- Keep **at least one full heating and one full cooling season** before drawing conclusions
  about fouling — UA drift is a slow signal and a month of data cannot distinguish it from
  seasonal variation.

---

### 7.7 Would variable flow buy you BTUs?

You raised this as the likely next step. The honest answer is **usually no for capacity, yes
for efficiency and fairness** — and the instrumentation in this plan is what tells you which
case you are in.

**Coil capacity versus water flow is a saturating curve.** Below design flow, capacity climbs
steeply — recovering from 50 % to 100 % of design flow can be worth 20–25 % capacity. Above
design flow it flattens hard: going from 100 % to 150 % buys perhaps 3–5 %, while pumping power
rises roughly with the cube of flow. So:

- **Flow below design ⇒ real capacity on the table.** Fix it, and it is usually the cheapest
  fix available.
- **Flow at or above design ⇒ almost nothing to gain from more.** The ceiling is set by
  entering water temperature and coil UA, and more flow just burns pump watts.

**Balancing *redistributes* capacity between zones, it does not create
it.** Total loop capacity is set by the plant and the pump. So read your data this way:

| Symptom | Meaning | Right intervention |
|---|---|---|
| One room short while another overshoots | Maldistribution | Balance the branches — this is exactly what balancing fixes |
| All rooms on a loop short together | Loop-wide shortfall | Speed tap, or the plant (EWT). Balancing does nothing |
| Water ΔT very low (3–5 °F) | Overpumped | Lower the tap. Also check for reverse mixing (§2.5f) |
| Water ΔT high (>15 °F) with low capacity | Starved | More flow, or find the restriction |

**Intervention ladder, cheapest first:**

1. **Check the existing speed taps.** Free, already installed, and per §2.5b Loop B is a
   plausible candidate for being one tap too high in summer. Do this before anything else.
2. **Static balancing valves** per branch, set so each zone gets design flow in the *worst*
   case (all zones open). Cheap, mechanical, no controls, and it directly targets the
   maldistribution row above.
3. **Pressure-independent balancing valves (PIBV)** per branch — mechanically hold per-branch
   flow regardless of what other valves do. This is the clean answer to "flow varies with how
   many zones are calling" and needs no controls at all.
4. **Swap the UP26-99F for a ΔP-controlled ECM circulator** (Grundfos ALPHA2 / MAGNA3 class).
   Constant-ΔP mode holds per-zone flow roughly steady as valves open and close, and cuts pump
   energy substantially. **This is the standard "dynamic flow" answer and it is a drop-in
   replacement** — no custom control scheme, no pivac involvement required.
5. **Modulating zone valves under active control.** Variable per-handler flow. This
   is where a custom pivac control loop would live — and it is the *last* resort, because
   items 2–4 capture most of the benefit with no software, no failure modes, and nothing to
   maintain.

**Do not skip to 5.** A ΔP circulator plus PIBVs solves the stated problem mechanically and
permanently. The value pivac adds here is measuring whether any of it worked, which you cannot do today. That is why the
instrumentation comes first.

One caveat if you do pursue lower flow: the Chiltrix has a **minimum flow requirement**, and
the buffer tank exists partly to satisfy it. Reducing *secondary* flow is safe because
primary/secondary decouples the two — but confirm that decoupling is intact (§2.5f)
before assuming it.

### 7.8 The right pump speed, and whether per-zone flow can be varied dynamically

Two questions David raised once CFM turned out to be static (§0.3). They have different answers.

#### 7.8.1 The right pump speed is *measurable* — and it is the lowest tap that holds ΔT in band

You do not need to compute it. **Water ΔT is the readout:**

| Loop ΔT (with every zone on that loop calling) | Verdict |
|---|---|
| 8–12 °F | Right. This is design |
| > 15 °F | Starved — raise the tap |
| < 6 °F | Overpumped — lower the tap, and check for reverse mixing (§2.5f) |

Sanity-check against first principles: a 2-ton coil at 10 °F design ΔT on 25 % glycol needs
`24,000 ÷ (481 × 10) ≈ 5 GPM`, so a three-zone loop wants roughly **15 GPM** at full call.

**Pick the *lowest* tap that stays in band at the worst case** — all zones on that loop calling.
Lowest, not highest, for three reasons: capacity saturates above design flow (§7.7) so the extra
buys nothing; pump power rises steeply with flow; and **secondary flow must stay under primary
flow or you get reverse mixing** (§2.5f).

> **This is step 5 of the build order.** The four secondary-loop DS18B20s (§2.6.4)
> measure exactly this, on the Pi's existing bus, with no Arduino and no flow meter.
>
> **But mind what loop ΔT can and cannot tell you.** It is the *aggregate* across every open
> zone. A loop in band does **not** prove each zone is in band — one coil can be starved while
> another runs generous, and the aggregate looks fine. **Loop sensors answer "is this loop pumped
> right"; only per-coil sensors answer "is this zone getting its share."** That is the specific
> gap the Arduino node fills, and the reason it stays on the roadmap rather than being dropped.

#### 7.8.2 Dynamic per-zone flow — you want *stable* flow, not *varying* flow

The instinct is right but the target is inverted. Because capacity saturates (§7.7), there is
little to gain from varying flow with load. What varies today is flow with
zone count** — a coil gets generous flow calling alone and a fraction of it when its
loop-mates join, which is backwards, since the many-zones case is the design day.

**So the goal is per-zone flow that holds steady regardless of what other zones do.** Two
standard, purely mechanical solutions do exactly that — and note that both *are* "dynamically
adjusting flow per zone", just implemented in brass rather than software:

| Solution | How it works | Notes |
|---|---|---|
| Pressure-independent balancing valves (PIBV) per branch | Mechanically hold branch flow at a set GPM regardless of system ΔP | Directly answers the question. No controls, no failure modes. Often taps existing ports |
| ΔP-controlled ECM circulator (Grundfos ALPHA2 / MAGNA3) replacing a UP26-99F | Varies pump speed to hold constant differential pressure as valves open/close, so per-branch flow stays near-constant | Drop-in. Also cuts pump energy substantially. The clean version of "step the pump up when more zones call" |

> **On relay-switching the UP26-99F's three taps:** technically some 3-speed circulators allow
> external speed selection by energising different windings (never two at once), and pivac will
> know zone-call state. **Don't.** An ALPHA2 in constant-ΔP mode does the same job autonomously,
> continuously rather than in three steps, with a proper ECM instead of switched windings, and
> with no wiring hazard. If the goal is pump speed that follows demand, buy the pump.

#### 7.8.3 There *is* a real case for modulating flow — but it is comfort, not capacity

This aligns with the §0 objective. In **cooling**, water flow sets the coil
surface temperature, which sets the sensible/latent split:

- **Higher flow → warmer coil → more sensible, less dehumidification**
- **Lower flow → colder coil → less total capacity, but more moisture removed**

So for a zone that holds setpoint yet feels clammy, *reducing* flow can improve comfort while
*reducing* BTU output. **That is the exact mirror of the CFM tradeoff in §0.3** — and it means
"optimise BTU" and "optimise comfort" are not the same objective on the water side either.

**In heating there is no latent load, so there is nothing to modulate** — take flow up to
saturation and stop. Which means any modulating-flow project would earn its keep only in
cooling, on the humidity axis.

**What it would take, and why to defer it:** the zone valves are 2-position, so this needs
**modulating/characterised control valves** per branch (Belimo CCV class, 0–10 V or 3-point),
something to drive them, and flow measurement to close the loop. That inserts a software failure
mode into the heating *and* cooling path for a gain bounded by saturation. **Exhaust §7.8.1 and
§7.8.2 first** — they are cheaper, mechanical, and permanent.

> **A ceiling that bounds all of the above:** secondary flow must stay below primary flow
> (§2.5f), and **both primary pumps are already on HIGH.** If a loop turns out to need more flow
> than its primary can supply, the answer is a **larger primary pump**, not a faster secondary —
> and no per-zone valve arrangement avoids it. The ΔT-ratio method in §2.6.2 tells
> you how close to that ceiling you already are, from thermometers alone.

---

## 8. Operational integration

- **Freshness alert.** Add rules to `grafana/provisioning/alerting/sensor-freshness.yaml`
  following the existing pattern — 30 min staleness, `noDataState: Alerting`, with a
  never-true sentinel for the threshold. Temperatures publish in Kelvin, so reuse the
  `value < 100` sentinel; `flowRate` is never negative, so use `value < -1` (the shape already
  used by `domestic-water-stale`).
- **Watchdog.** `scripts/arduino-watchdog.sh` currently pings only `.114` and `.219`, and
  power-cycles the shared "Arduinos" Shelly at `10.0.0.61`. If this board is on a different
  circuit — likely, since it lives at the air handler — it gets **no auto-recovery**. Either
  extend the watchdog with a second plug, or accept alert-only and document that.
- **Grafana.** New row. Follow the house conventions: `custom.axisWidth: 50` on every
  timeseries, no per-panel `axisLabel`, and stepped-line timeseries rather than state-timeline
  for the boolean `running` (state-timeline cannot set row-label width, so it will not align).
  Panels: the two ΔTs on one axis, capacity, UA, and SHR.
- **Restart order.** Config edit → `restart pivac-unico-mbr` → `restart signalk`. Signal K
  freezes retired paths at their last value until the server restarts — documented three times
  in CLAUDE.md (relays, 1-Wire, Emporia) and it will bite here too during development.

---

## 9. Build order

Sequenced against the §0 objective: **summer comfort and capacity, both systems.**

### Costs nothing — do these first

1. **Run the §0.1 analysis on existing data.** Droop vs equipment power vs humidity, per zone,
   on hot afternoons. All three cooling units are individually metered as of August. **This
   decides which zone to instrument first** and may show the answer outright.
2. ✅ **Temperature-precision fixes deployed 2026-08-18** — `pivac.OneWireTherm` (#118) and
   `pivac.RedLink` (#119). Droop and every ΔT are quantitative from that date; earlier history
   is not (§2.6.0).
3. **Confirm which loop the 2430 is on** (§4.6). ✅ Pump taps surveyed — primary HIGH, both
   secondaries LOW (§2.5); Loop B set to LOW (§2.5b), **raise again before heating season.**

### Cheap, high value against the objective

4. **Two 10K NTCs in whichever BOVA zone step 1 identifies** (§0.2) — measured sensible capacity
   plus the airflow-starvation signature, with no water side and no flow meter. Also the way to
   verify a zone's latent performance once its settings are biased toward sensible (§0.3).
5. **Four DS18B20s on the two secondary loops** (§2.6.4) — starvation, mixing, flow ratios and
   loop-idle detection for the entire chilled side, on the Pi's existing bus.
6. **Utility-room Tier 1 sensors** (§4.8) — room ambient, and **restore leak detection**, which
   is a regression rather than a gap.

### The node itself

7. **Verify the fluid** (§2.2) and **read commanded CFM per mode** off the Smart Controller
   (§7.2). Consider doing the 30 % glycol top-up *before* commissioning so the baseline is on
   the final fluid.
8. **Verify the NTC curve** (§2.3) — ice-bath check, Type II vs Type III.
9. **Bench-build the node**, all four sensors, final firmware. **Matched-pair calibration
    (§7.1)** — record offsets and both DS18B20 ROM addresses in this document.
10. **`ArduinoSensor` `rounding:` change (§6.1)** → PR. Small, isolated, backwards-compatible.
11. **Install**, DHCP-reserve by MAC, add config and the service unit.
12. **`pivac.UnicoAH` wrapper (§6.2)** → PR. **Grafana row + freshness alerts (§8)** → PR.
13. **Join RedLink humidity (§7.3)** for the latent split — software only, and latent is comfort.

### Only if the data asks for it

14. **Flow meter**, primary loop first (§2.6.1) — it converts every ratio into an absolute
    number for *all* loops, which is better value than a per-coil meter.
15. **Commissioning check (§7.2):** in heating, `CFM_derived / CFM_commanded` ≈ 1.0. This is the
    acceptance test for the whole chain — heating is otherwise deprioritised, but it is the only
    latent-free window in which to validate the measurement.
16. **`wsup − IN` reverse-mixing series (§2.5f)** — one subtraction, verification not diagnosis.
17. **Collect a cooling season.** Analyse per §7.4, decide the flow question per §7.7.

## 10. Open questions

- **Which loop is the 2430 on — utility room (Loop B) or one of the Loop A zones?** This is
  the most consequential unknown left: it decides whether cooling-season flow is constant,
  and therefore whether the flow meter is needed now or can wait a season (§4.6).
- **Are there any balancing valves on the branches today?** Speed taps are known (§2.5);
  per-branch balancing is the remaining unknown on the distribution side, and it is what decides
  whether a starved loop can be fixed by redistribution or only by more total flow (§7.7).
- **What is the Taco model on the chiller primary, and what is its curve?** Needed to judge
  primary-vs-secondary flow in cooling (§2.5c).
- **Does the Taco run continuously through a cooling call, or only with the compressor?** And
  is it powered from the Chiltrix circuit (i.e. visible in `electrical.emporia.house.chiltrix`)
  or separately?
- **How many hydronic zones are there in total?** Four water zones fit an HZ-432 exactly
  (3 on Loop A + utility on Loop B), but in winter kitchen and great room take hot water too,
  which implies more zone valves than one HZ-432 has. Worth pinning down before assuming the
  zone-valve roster.
- **In heating, where does the hot water come from — the NTI boiler, or the Chiltrix running as
  a heat pump?** It does not affect the capacity measurement at all (the water side is the
  water side), but it decides whether a heating-season efficiency figure is a **COP** against
  `electrical.emporia.house.chiltrix` or a **combustion efficiency** against gas input, which
  is a different calculation with a different denominator (§7.5).
- Are `IN`/`OUT` the primary-loop supply/return? (§7.5)
- Does the CX75 expose Modbus RTU? (§7.5)
- Which glycol — propylene or ethylene? (§2.2)
- Is there a balancing valve on this coil with a published flow chart? (§4.6)

