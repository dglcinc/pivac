# Plan — Unico 2430 Air-Handler BTU Monitoring

**Status:** Design / not yet built.
**Date:** 2026-08-18.
**Target:** One Unico M2430 air handler with a chilled-water coil serving both heating and
cooling, on two-pipe changeover off the buffer tank. The first of potentially several.

Three facts shape the design more than anything else.

The air handler runs a Unico Smart Controller with a software-configurable ECM blower, so CFM is
a commanded value (§7.2). That removes the hardest unknown on the air side and replaces it with
a better diagnostic.

A Honeywell IAQ thermostat on RedLink is attached to this air handler, and `pivac.RedLink`
already publishes that zone's humidity (`environment.inside.thermostat.<ZONE>.humidity`,
`pivac/RedLink.py:331`). That supplies the entering-air humidity this project would otherwise
need new hardware to obtain (§7.3).

The HZ-432 drives one zone valve per zone, each feeding its own air handler, with no dampers. So
this node measures one coil with its own dedicated blower, per-handler CFM is constant, and the
RedLink thermostat maps one-to-one to the air handler. The zones share a circulator, which makes
per-zone water flow a variable and decides whether you buy a flow meter (§4.6), except on Loop B
in cooling, where it is a single-zone loop and constant (§2.5).

**Goal:** Measure the BTU/hr the coil delivers, plus enough surrounding state to explain any
shortfall. Feed it into pivac like every other sensor: Arduino → `pivac.*` → Signal K → InfluxDB
→ Grafana.

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

### 0.3 Signalling `Y2` and driving the compressor higher, answered from the IOM

Checked against the BOVA-36HDN1-M18M Installation Instructions (Bosch Thermotechnology,
06.2016), the model installed here.

#### `Y2` has no terminal on the condenser

`Y2` appears nowhere in the manual. The low-voltage hook-up (Figure 26) gives the terminal
blocks as:

| Block | Terminals |
|---|---|
| Outdoor unit | `C` `Y` `B` `D/W`, with B and D/W on heat-pump models only |
| Indoor unit | `G` `R` `C` `W1` |
| Thermostat | `W2` `B` `C` `R` `Y` `G` |

The condenser accepts one `Y`, a single 24 V cooling call. §15.1 states the unit "adopts the
same 24VAC control as any conventional Heat Pump" and stages internally. The condenser has no
second-stage input and nothing to wire to it.

> `Y2` belongs to the air handler. The thermostat's `Y2` drives the Unico blower's second-stage
> fan speed, which is how a second-stage call reaches the compressor: through air. More airflow
> puts more heat into the coil, raising evaporator pressure and ramping the compressor. A
> disabled `Y2` fan wire therefore starves the coil on the hot days the second stage exists for,
> and the compressor answers by slowing down, the self-reinforcing failure in §0.2. Confirm `Y2`
> is connected and working at the air handler before diagnosing anything else on a BOVA zone.

#### Suction pressure has one adjustment, and it is already set

Suction pressure is a dependent variable, set by load, airflow and charge, so it cannot be
managed directly to make the compressor work harder. The manual exposes the target it modulates
toward (§15.1, verbatim):

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

Both are already set on the great-room unit: SW4-4 accelerated on both units, and SW4-3 switched
on in July, after which its board display read 75–77 Hz. No third capacity switch exists, so the
compressor already runs as hard as the controls allow.

> That relocates the problem. A unit at maximum commanded speed with a zone still drifting is
> constrained downstream of the compressor, in refrigerant mass flow from charge or in evaporator
> heat transfer from airflow. §0.2 separates that pair, which is why two thermistors on that air
> handler return more than further control adjustment. The outstanding subcooling check covers
> the other half: the manual makes subcooling the only recommended charging method above 55 °F
> outdoor ambient, with weigh-in below that, and prior notes carry a target of 10 ± 2 °F.

#### ⚠️ SW4-3 may be trading away the comfort you want

The manual ties SW4 to improved dehumidification and capacity demands, and those trade against
each other. Disabling adaptive capacity holds the target evaporator pressure higher, giving a
warmer coil and less moisture removal. The §0 objective is comfort rather than raw sensible
output, so a great room sitting at 77 °F and humid could be worse off with SW4-3 on even as
sensible capacity rises.

This is testable. Both BOVAs have their own CT and RedLink logs per-zone humidity, so run SW4-3
off for a few comparable hot days and compare droop and humidity against the SW4-3 on period. If
droop holds steady while humidity falls, adaptive capacity was the better setting.

#### Two board features

The forced operation button, control-board legend items 16 and 21 with its own display code, is
a service and commissioning function that runs the unit independent of the thermostat. It suits
a controlled capacity test and should stay out of continuous operation.

The digital tube display, item 18, carries the Hz readout. Read it during the air-side
measurements so commanded frequency, air ΔT and condenser watts are captured together. That
triple distinguishes a starved coil from a maxed one.

#### It does work on its own, and airflow is how you help it

Suction pressure is the load signal. Evaporator pressure settles where heat arriving at the coil
balances heat the compressor removes, so a hotter, wetter return puts more heat into the
refrigerant, raises evaporator pressure, and the control ramps the compressor up. That is a
closed loop on actual thermal load, and it beats a `Y2` contact, which only proxies load from
room temperature. `Y2` would add nothing at the condenser even if the terminal existed.

The catch is that the loop sees load as delivered to the coil, `airflow × enthalpy difference`.
It cannot separate low load from ample load with too little air to carry it, since both present
as low suction pressure. With constrained airflow a hot room therefore produces a slow
compressor, and the effect is self-reinforcing (§0.2).

Airflow is the adjustment, and using it is the control working as designed:

```
more CFM → more heat into the coil → higher suction pressure → compressor ramps up
```

Two paths deliver it, and they stack. The thermostat's `Y2` selects the blower's second-stage
speed on a second-stage call, raising airflow only when the zone asks for more, and it must be
connected for a BOVA zone to reach full capacity on a hot day. The base CFM setting on the Unico
Smart Controller sets the floor both stages work from, in software, free and reversible.

> ⚠️ Do not raise suction pressure artificially. Overcharging or interfering with the pressure
> transducer raises the number without raising capacity, and the board runs low-pressure
> protection in cooling and compression-ratio protection off that same transducer, so a falsified
> signal defeats the protections. Feed the coil more heat rather than misreporting it.

More CFM means a warmer coil, so sensible capacity rises and dehumidification falls, the same
tension as the SW4-3 question above. A zone can reach setpoint and still feel clammy, which
matters because the §0 objective is comfort.

> ⚠️ The great room carries three sensible-biased settings at once: `Y2` fan connected, base CFM
> raised, and `SW4-3` on, which holds the coil warmer. All three trade latent for sensible in the
> same direction, so watch humidity there rather than temperature.
> `environment.inside.thermostat.GREAT_ROOM.humidity` is already logged, and droop is
> quantitative from 2026-08-18 (§2.6.0). If that zone holds setpoint while reading humid against
> the others, give `SW4-3` back first, since it costs the least capacity now that airflow is
> unconstrained.

Judging an airflow change costs nothing. Both BOVAs have their own CT and RedLink logs per-zone
humidity, so compare droop and humidity across comparable hot days. Two thermistors (§0.2) also
show whether air ΔT moved as expected, confirming the airflow changed rather than the ECM merely
being told to change it.

> The structural limit is that the Unico blower and the BOVA compressor do not communicate.
> `Y2` couples the thermostat to the blower, so airflow follows the thermostat's two-stage demand
> rather than the compressor's state. The Smart Controller's only interface is USB for changing
> settings, and the air handler pauses while fan speed changes, which puts dynamic load-following
> airflow out of reach. Reverse-engineering the USB protocol would not help, because the pause is
> the blocker. CFM is a static setting, so plan around that.

#### A static CFM sets where the compressor operates

The compressor is the only dynamic element in the pair, and it modulates on suction pressure,
which is set by how much heat the airflow delivers. The static CFM setting therefore decides
where in its modulation range the compressor lives. Higher CFM raises suction pressure, so the
compressor runs faster and makes more sensible capacity at a warmer coil with less
dehumidification. Lower CFM does the reverse.

That converts an apparently open-ended control problem into a small, finite tuning exercise over
two static settings, both free to change, with measurable outcomes.

| Setting | Options | Effect |
|---|---|---|
| Unico CFM | a few settings via USB | Sets the compressor's operating point |
| SW4-3 | ON / OFF | Adaptive capacity disabled or enabled |

Evaluate each combination on droop and humidity over comparable hot days, both already logged per
zone. Nothing here needs solving dynamically; it needs measuring, which §0.2's two thermistors
plus the existing CT and RedLink humidity supply.

> CFM is therefore a seasonal setting, like the Loop B pump tap (§2.5b). Peak summer wants more
> airflow for maximum sensible with the compressor pushed high, and shoulder season wants less
> for better dehumidification at part load. A USB change twice a year is practical even though a
> dynamic one is not, and it belongs on the manual seasonal list already holding the pump tap and
> the glycol top-up.

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

### 2.2 K is 481 for a 25 % glycol loop

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

The air handler measures whether this coil is delivering. The mechanical room measures whether
the plant is healthy, and several of those sensors cost less and return more than the coil node.
Ranked by value per dollar against the §0 objective, summer comfort and capacity.

#### Tier 1

| Sensor | Where | Why |
|---|---|---|
| 4× DS18B20, supply and return on each secondary loop | Loop A and Loop B, at the tees | §2.6.4. Starvation, flow ratios, mixing, loop-idle detection. The highest-value addition in this document |
| 1× DS18B20, boiler return | Boiler return, before the primary tee | Condensing verification. Monitor-only per §0 |
| 1× T/RH sensor, room ambient | Mechanical room, away from the boiler | Standby losses, and the Pi's thermal ceiling. See below |
| Leak and flood detection | Pan under boiler, buffer tank, booster pump | Closes a regression. See below |

Boiler return temperature is worth recording and not worth chasing (§0). A Trinity Ti-200
condenses only when return water sits below the flue-gas dew point, roughly 130 °F. Above that
it loses most of the condensing gain, on the order of 10 % efficiency. Hydronic air-handler coils
are commonly designed around 140 to 180 °F supply, which puts return water above the threshold,
so this boiler may never condense in this application and nobody would know. The Sentry already
supplies boiler supply temperature (`hvac.boiler.sentry.waterTemp`) and outdoor temperature; one
DS18B20 on the return completes the picture. Confirming non-condensing would point to outdoor
reset, lowering supply temperature in mild weather, which trades coil capacity for efficiency.
Capacity is the priority and heating is rarely the problem, so record the number and leave it
alone. It stays in Tier 1 only because it is one more probe on a bus already being extended.

Room ambient explains a problem CLAUDE.md already documents. The Pi is a fanless Pi 4 running at
about 76 °C with 83 °C peaks during Sentry capture bursts, grazing the 80 °C soft-temp limit,
and CLAUDE.md notes that ambient boiler-room heat matters while offering no way to measure it. A
room temperature series turns that from hypothesis into correlation and shows whether ventilation
would return more than further `daemon_sleep` tuning, which CLAUDE.md says cannot fix the peaks.
Humidity comes free with the same sensor: a mechanical room that runs humid in summer carries
mold and corrosion risk, and flags chilled-pipe sweating from insulation gaps.

> ⚠️ Leak detection was lost rather than retired. CLAUDE.md records that BCM 25 carried the
> booster-pump leak pan as `SCALA` until 2026-08-11, when the input was renamed in place to
> `CHIL` to sense the chiller call, and the leak-pan signal stopped being published. That traded
> one input for another, and the result is that a room holding the boiler, buffer tank, DHW,
> booster pump and the domestic water main has no water detection. Free GPIO inputs with existing
> wire runs are BCM 13/33, 16/36 and 24/18. Avoid BCM 26, which CLAUDE.md documents as a
> permanently dead pad. This is the cheapest insurance in the document and has nothing to do with
> BTUs.

#### Tier 2

| Sensor | Why |
|---|---|
| Flow meter on the primary loop | §2.6.1. Whole-house delivered BTU, system COP, boiler delivered-versus-fired efficiency. Converts every ratio in §2.6.2 into an absolute number |
| 2× DS18B20, Chiltrix entering and leaving water | Chiller-side ΔT. With `electrical.emporia.house.chiltrix` this gives chiller COP directly, separate from distribution losses. Skip if the CX75 exposes them over Modbus (§10) |
| CTs on the circulators | Definitive pump-running state, better than the §2.6.3 inference, plus pump energy accounting that makes the §7.7 flow tradeoff measurable. A failing circulator shows as changed draw. Needs spare Emporia channels, and CLAUDE.md records that four CTs were borrowed from the apartment panel for the Chiltrix |

#### Tier 3

| Sensor | Why |
|---|---|
| Differential-pressure transducer across a secondary loop | An alternative to a flow meter: read ΔP and look up flow on the pump curve. Often taps existing ports, so no pipe cutting, which suits a reluctance to open a glycol loop |
| Boiler flue temperature | Direct efficiency indicator. High flue temperature is heat going up the stack, and it complements the condensing check above |
| Condensate trap float switch | A blocked trap shuts a condensing boiler down, and it fails at the worst time of year |
| CO detector with a monitored contact | Safety rather than optimisation, but this is a gas appliance in an occupied building and the GPIO inputs already exist |

#### Wiring

Tier 1's five DS18B20s go on the Pi's existing 1-wire bus, taking it from 4 sensors to 9, well
within 1-Wire's addressing limits. Watch total cable length and topology: prefer a daisy chain
over a star, and consider dropping the pull-up to 2.2–3.3 kΩ as the bus grows, which §5 of
`docs/circ-loop-temp-monitoring-plan.md` covers. `pivac.OneWireTherm` re-scans every cycle since
2026-07-06, so sensors added live appear within one daemon cycle and need no restart.

The T/RH sensor and the leak detector are not 1-Wire. RH wants I²C, so it belongs on an Arduino
or a small dedicated node, and a leak pan is a dry contact into a spare GPIO.

---

## 5. Firmware contract

The Arduino emits raw measurements and computes no BTUs. The DHW board's recirc-temperature
sketch was never committed and exists only on the M2 MacBook, so reflashing that board would
silently drop a sensor. Firmware is the expensive, fragile place for anything that might change.
Calibration offsets, the glycol constant `K`, and the capacity arithmetic all belong in
`config.yml` and Python, where they are version-controlled and deploy with a `git pull`.

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

Emit two decimal places on every temperature. The precision has to survive as far as the delta
(§6).

Reuse the scaffolding proven in `DomesticWater.ino`: a D-pin reed or pulse interrupt with
debounce, an EEPROM totalizer with a magic marker, a 10 s rolling flow window, the RA4M1
watchdog, and bounded WiFi and HTTP handling. Add the 12-bit DS18B20 read and the two averaged
ADC reads.

Handle disconnected sensors explicitly. A DS18B20 that fails to read returns −127, and an open
NTC divider rails to full scale. Emit a −999 sentinel rather than a plausible number, so the Pi
can drop the sample instead of computing a confident and wrong BTU figure.

---

## 6. pivac integration

### 6.1 `pivac.ArduinoSensor` needs a `rounding:` key

`ArduinoSensor` hardcodes `int(round(...))` on every `type: temperature` field. Add an optional
per-input `rounding:` key defaulting to `0`, which leaves every existing input byte-for-byte
unchanged:

```python
digits = scfg.get("rounding", 0)
k = _to_kelvin(raw, scfg.get("scale", "fahrenheit"))
kelvin = int(round(k)) if digits == 0 else round(k, digits)
```

This mirrors `pivac.OneWireTherm` (`pivac/OneWireTherm.py:113`), which has carried the same
per-sensor `rounding` key all along, so the concept already exists in the codebase and simply
never reached the Arduino path. The DHW recirc input keeps `rounding: 0` and its InfluxDB series
stays undisturbed. The new inputs use `rounding: 2`.

### 6.2 `pivac.UnicoAH` wraps `ArduinoSensor` rather than replacing it

The pattern follows `pivac.DomesticWater`: call through for the raw fields, then append derived
values. All physics stays in Python and all constants stay in config.

Derived per cycle:

```
ΔT_water  = wsup - wret                       (°F, sign follows mode)
ΔT_air    = asup - aret
Q_total   = K × GPM × |ΔT_water|              (BTU/hr)
Q_sens    = 1.08 × CFM × |ΔT_air|             (BTU/hr, needs CFM, §7.2)
SHR       = Q_sens / Q_total                  (cooling only)
UA        = Q_total / |aret - wsup|           (BTU/hr·°F, the fouling metric, §7.4)
running   = flow > flow_threshold             (0/1)
```

Gate everything on `running`. A ΔT computed on a dead coil is noise, and a UA computed on a
near-zero denominator is a divide-by-zero waiting to happen. Emit zero or null for the derived
values while the coil is off, and suppress the first 5 minutes after a start, because the coil,
the water in it, and the duct mass all need to reach steady state before the energy balance
closes.

### 6.3 Signal K paths

> Name these carefully now. The Signal K path becomes the InfluxDB measurement name, and
> CLAUDE.md records four renames, CRW to UBT, AMB to LBT, the relay roster and the Emporia
> circuits, that each orphaned their history. Adding a second air handler later must not force a
> rename of the first, which is why the path carries a `<unit>` level.

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

> ⚠️ A ΔT must never pass through `type: temperature`. That branch adds 273.15, which is correct
> for an absolute temperature and destroys a difference. Emit the deltas as plain untyped numbers
> from the wrapper module. A `deltaT` of 10 °F arriving in InfluxDB as 283.15 looks like a
> plausible temperature and survives review.

### 6.4 Config sketch

```yaml
pivac.UnicoAH_MBR:
    description: Unico M2430 hydronic air handler capacity monitoring
    module: pivac.UnicoAH
    enabled: true
    ipaddr: 10.0.0.xxx
    daemon_sleep: 15
    sk_path: environment.inside.hvac.ah.mbr

    # --- physics constants (see §2.2) ---
    fluid_k: 481.0          # 25% PG; ~476.0 after the 30% top-up (§2.2)
    nominal_cfm:            # commanded airflow from the Unico Smart Controller (§7.2)
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
            rounding: 2     # required, see §6.1
        # ... wret / asup / aret identically
        flow:
            sk_path: environment.inside.hvac.ah.mbr.water
            outname: flowRate
```

---

## 7. Calibration and analysis

### 7.1 Matched-pair calibration, before install

Per §2.3 this turns a ±18 % measurement into a ±1 % one, so it is required rather than optional.

1. Wire all four sensors to the board on the bench, running the final firmware.
2. Bundle the two water probes together in a stirred bath. An insulated jug of water serves;
   stability matters far more than knowing the true temperature.
3. Log for at least 15 minutes at the production sample rate, and take the mean difference
   rather than a spot reading.
4. Repeat at a second temperature spanning the working range, ice water and hand-hot, to learn
   whether the offset holds constant or drifts with temperature. Fit a slope instead of a
   constant if it drifts materially.
5. Repeat steps 2 to 4 for the two air NTCs.
6. Write the offsets into `offsets:` in config. Keep them out of firmware, because they need
   annual re-verification.

Acceptance: with offsets applied, the two water probes in a common bath should agree within
0.1 °F. Failing that, a 10 °F ΔT cannot be trusted to better than a few percent.

### 7.2 CFM is commanded, which turns the energy balance into a diagnostic

The Unico Smart Controller's ECM is configured in software, so read the commanded airflow per
mode off the controller and put it in `nominal_cfm`. That removes the hardest unknown on the air
side, and sensible capacity needs no derivation.

The energy balance then serves a different purpose. Heating carries no latent load (§2.1), so
the two sides must agree and the balance solves for airflow:

```
CFM_derived = (K × GPM × ΔT_water) / (1.08 × ΔT_air)      [heating only]
```

Since the ECM's commanded value is known, comparing the two returns more than either number
alone. Track `CFM_derived / CFM_commanded` as a first-class series.

| Ratio | Meaning |
|---|---|
| ≈ 1.0 | The measurement chain is validated end to end: flow-meter calibration, all four temperature offsets, and the blower agree. This doubles as the acceptance test for the build |
| Drifting down over weeks or months | The ECM is losing its fight with static pressure, from a dirty filter or a developing duct restriction. This is the early warning the ECM otherwise hides (§2.4), since it masks restriction by drawing more torque until it cannot |
| Sudden step | Something changed physically: a filter swap, a damper position, a sensor knocked loose, or the controller reconfigured |
| Persistently off 1.0 from day one | A calibration error rather than a fault. Suspect the flow meter's K-factor first, then the temperature offsets |

This coil runs heating and cooling off the same water, so the check comes free every winter.
Carry `nominal_cfm` into cooling afterwards to split total capacity into sensible and latent.

Capture the commanded CFM per mode. A Smart Controller is typically configured with different
airflow for heating and cooling, and possibly per stage or demand level, so `nominal_cfm` should
be a small map keyed by mode rather than one number.

Two minor caveats, both small beside everything else here: air density differs by about 5 %
between 110 °F and 55 °F supply air, and the balance assumes steady state, which §7.6 enforces.

### 7.3 Phase 2 humidity may already be available

Entering-air wet-bulb drives a chilled-water coil's capacity and splits total capacity into
sensible and latent. It needs entering dry-bulb, available at full precision from the `aret`
NTC, plus entering RH.

The IAQ thermostat supplies the RH. `pivac.RedLink` publishes
`environment.inside.thermostat.<ZONE>.humidity` for every zone today (`pivac/RedLink.py:331`, as
a 0 to 1 fraction). Return air is room air, so the zone thermostat's RH proxies entering-air RH
well; the error comes from duct leakage and infiltration into the return rather than from the
model.

Phase 2 is therefore a software join rather than a hardware purchase. Combining the `aret`
dry-bulb with the RedLink humidity for the same zone gives entering enthalpy, which supplies a
true SHR and latent split independent of the stored CFM, a CFM derivation that works in cooling
through `Q_total = 4.5 × CFM × Δh` rather than only in winter (§7.2), and the physically correct
denominator for coil performance in §7.4.

Two caveats. Take temperature from the node's own NTC and only humidity from the thermostat,
since RedLink temperatures now carry 2 decimals but still lag the node. RedLink also polls on its
own schedule with a documented 15 to 25 % per-device timeout rate, so the humidity series is
coarser and gappier than the node's own data; interpolate and tolerate gaps rather than dropping
the sample.

Add an SHT41 in the return plenum only if that proves inadequate, and measure first. Supply
humidity is not proposed either way: off a wet coil that air sits at 90 to 98 % RH, which is hard
to measure accurately and hard on the sensor.

### 7.4 What "maximum BTUs" means, and how to tell if you have it

Capacity depends on five things: entering water temperature, water flow, air flow, entering air
wet-bulb, and coil cleanliness. Raw BTU/hr is therefore not a target, since it varies with
weather. Two normalised metrics work better.

UA is the fouling and health metric:

```
UA = Q_total / |T_return_air − T_water_supply|
```

This divides out both the weather and the plant, leaving coil effectiveness. At a given GPM and
CFM, UA should hold constant. Plotted over months, a steady decline means fouling, either
air-side dirt or water-side scale and sludge, and it is the clearest available signal that the
coil is degrading. This is the most valuable series the project produces.

Capacity against the manufacturer's rating is the second. Pull the Unico coil rating table at
your EWT, GPM and CFM and compare. That answers whether you fall short of design, a separate
question from whether you fall short of last year.

Then apply the §2.4 table. Sort the steady-state samples by capacity, take the worst decile, and
find which delta is anomalous. That identifies the constraint.

### 7.5 The highest-value analysis needs no new hardware

These series already flow into InfluxDB and bear directly on the question:

| Existing series | Use |
|---|---|
| `electrical.emporia.house.chiltrix` (W) | Plant power, the denominator of COP |
| `environment.inside.hvac.UBT/LBT.temperature` | Buffer tank stratification: is the plant keeping up? |
| `environment.inside.hvac.IN/OUT.temperature` | Primary header supply and return: plant-level ΔT, and the reference for the reverse-mixing check `wsup − IN` (§2.5c) |
| `environment.inside.thermostat.<zone>.temperature` | Zone response: is the room recovering? |
| `environment.inside.thermostat.<zone>.humidity` | Entering-air RH, which supplies the latent split (§7.3) |
| `environment.outside.thermostat.temperature` | Load normalisation |
| `electrical.ac.switch.utility.CHIL` and `BLR` | Changeover mode, chilled against hot water. See the caveat below |
| `electrical.ac.switch.utility.ZV` | Any zone valve open. System-level, same caveat |
| `electrical.ac.arduinoThermPSI.psi` | Loop pressure. A drop precedes air-bound-coil symptoms |

> ⚠️ `CHIL` is a system-wide call rather than this zone's. It asserts when any water-cooled zone
> calls through the HZ-432, so with three zone valves on three air handlers it reads true during
> periods when this coil's valve is shut and its flow is zero. Never gate a per-air-handler
> calculation on `CHIL`. The correct gate is the node's own flow, `running = flow >
> flow_threshold` (§6.2), which is per-coil by construction.
>
> `CHIL` and `BLR` serve for changeover mode, telling you whether the arriving water is chilled
> or hot, which selects the sign convention, the mode's `nominal_cfm`, and whether a latent term
> exists. Even that is available without them: `wsup` near 45 °F means cooling and 120 to 140 °F
> means heating, so the node can determine its own mode from supply water temperature with the
> relays as a cross-check. Prefer the self-determining version, which stays correct through
> another relay-roster change.

> Consider one shortcut before the per-air-handler build. If `IN` and `OUT` are the primary-loop
> supply and return, one flow meter on the primary gives whole-system capacity, and with
> `electrical.emporia.house.chiltrix` it gives system COP from data already collected:
>
> ```
> COP = (K × GPM_primary × |T_IN − T_OUT|) / (W_chiltrix × 3.412)
> ```
>
> One sensor answers whether the plant is efficient. The per-air-handler build answers the
> complementary question, whether this zone is getting its share, which plant-level data cannot
> reach. One meter buys the other half cheaply. Confirm what `IN` and `OUT` sit on physically
> before relying on this, since it is an inference from the naming rather than a verified fact.

Check whether the CX75 exposes Modbus RTU. The Chiltrix CX-series publishes entering and leaving
water temperature, compressor state, and on some models flow. An RS485 adapter would then supply
plant-side data with no plumbing work. Verify against the unit's manual.

### 7.6 Sampling discipline

Gate on `running` and discard the first 5 minutes of every call (§6.2), or startup transients
will dominate the dataset while representing nothing.

Aggregate to 1 to 5 minute means before analysis. Instantaneous BTU/hr is noisy and nothing in
this problem changes quickly.

Collect at least one full heating and one full cooling season before drawing conclusions about
fouling. UA drift is a slow signal, and a month of data cannot separate it from seasonal
variation.

---

### 7.7 Would variable flow buy you BTUs?

Usually no for capacity, and yes for efficiency and fairness. The instrumentation in this plan
identifies which case applies.

Coil capacity against water flow is a saturating curve. Below design flow capacity climbs
steeply, and recovering from 50 % to 100 % of design flow can be worth 20 to 25 %. Above design
flow the curve flattens: 100 % to 150 % buys perhaps 3 to 5 %, while pumping power rises roughly
with the cube of flow. Flow below design therefore leaves real capacity available, usually
through the cheapest fix on the list. Flow at or above design offers almost nothing, because the
ceiling comes from entering water temperature and coil UA, and the extra flow burns pump watts.

Balancing redistributes capacity between zones rather than creating it. Total loop capacity comes
from the plant and the pump. Read the data accordingly:

| Symptom | Meaning | Right intervention |
|---|---|---|
| One room short while another overshoots | Maldistribution | Balance the branches, which is what balancing fixes |
| All rooms on a loop short together | Loop-wide shortfall | Speed tap, or the plant and its EWT. Balancing achieves nothing |
| Water ΔT very low, 3 to 5 °F | Overpumped | Lower the tap, and check for reverse mixing (§2.5f) |
| Water ΔT high, above 15 °F, with low capacity | Starved | More flow, or find the restriction |

The intervention ladder, cheapest first:

1. Check the existing speed taps. Free, already installed, and per §2.5b Loop B is a candidate
   for sitting one tap too high in summer. Do this before anything else.
2. Static balancing valves per branch, set so each zone gets design flow in the worst case with
   all zones open. Cheap, mechanical, no controls, and aimed directly at maldistribution.
3. Pressure-independent balancing valves per branch, which hold branch flow mechanically
   regardless of what other valves do. This answers "flow varies with how many zones are
   calling" and needs no controls.
4. Swap the UP26-99F for a ΔP-controlled ECM circulator, Grundfos ALPHA2 or MAGNA3 class.
   Constant-ΔP mode holds per-zone flow roughly steady as valves open and close and cuts pump
   energy substantially. This is the standard answer to varying flow and it is a drop-in
   replacement needing no custom control scheme and no pivac involvement.
5. Modulating zone valves under active control, giving variable per-handler flow. A custom pivac
   control loop would live here, and it is the last resort, because items 2 to 4 capture most of
   the benefit with no software, no failure modes and nothing to maintain.

Do not skip to item 5. A ΔP circulator with PIBVs solves the problem mechanically and
permanently. What pivac adds is measuring whether any of it worked, which you cannot do today,
and that is why the instrumentation comes first.

One caveat on pursuing lower flow: the Chiltrix has a minimum flow requirement, and the buffer
tank exists partly to satisfy it. Reducing secondary flow is safe because primary/secondary
decouples the two, but confirm that decoupling is intact (§2.5f) before assuming it.

### 7.8 Pump speed, and whether per-zone flow can be varied

#### 7.8.1 The right pump speed is the lowest tap that holds ΔT in band

Water ΔT is the readout, so the setting needs no calculation.

| Loop ΔT, every zone on that loop calling | Verdict |
|---|---|
| 8–12 °F | Design. Correct |
| Above 15 °F | Starved. Raise the tap |
| Below 6 °F | Overpumped. Lower the tap and check for reverse mixing (§2.5f) |

Against first principles, a 2-ton coil at 10 °F design ΔT on 25 % glycol needs
`24,000 ÷ (481 × 10) ≈ 5 GPM`, so a three-zone loop wants roughly 15 GPM at full call.

Pick the lowest tap that stays in band at the worst case, with all zones on that loop calling.
Lowest rather than highest for three reasons: capacity saturates above design flow (§7.7) so the
extra buys nothing, pump power rises steeply with flow, and secondary flow must stay under
primary flow to avoid reverse mixing (§2.5f).

> This is step 5 of the build order. The four secondary-loop DS18B20s (§2.6.4) measure it on the
> Pi's existing bus, with no Arduino and no flow meter.
>
> Mind what loop ΔT can and cannot show. It aggregates across every open zone, so a loop in band
> does not prove each zone is in band; one coil can starve while another runs generous and the
> aggregate still looks fine. Loop sensors answer whether the loop is pumped right, and only
> per-coil sensors answer whether a zone is getting its share. That gap is what the Arduino node
> fills, and why it stays on the roadmap.

#### 7.8.2 Per-zone flow should be stable rather than varying

Capacity saturates (§7.7), so varying flow with load returns little. What varies today is flow
with zone count: a coil gets generous flow calling alone and a fraction of it once its loop-mates
join. That is backwards, since the many-zones case is the design day.

The goal is therefore per-zone flow that holds steady regardless of what other zones do. Two
mechanical solutions deliver exactly that, and both adjust flow per zone in brass rather than
software.

| Solution | How it works | Notes |
|---|---|---|
| Pressure-independent balancing valves per branch | Hold branch flow at a set GPM mechanically, regardless of system ΔP | Answers the question directly. No controls, no failure modes, and often taps existing ports |
| ΔP-controlled ECM circulator (Grundfos ALPHA2 or MAGNA3) replacing a UP26-99F | Varies pump speed to hold constant differential pressure as valves open and close, keeping per-branch flow near-constant | Drop-in, and cuts pump energy substantially. The clean version of stepping the pump up when more zones call |

> Some three-speed circulators allow external speed selection by energising different windings,
> never two at once, and pivac will know zone-call state. Avoid that route. An ALPHA2 in
> constant-ΔP mode does the same job autonomously and continuously rather than in three steps,
> with a proper ECM instead of switched windings and no wiring hazard. If the goal is pump speed
> that follows demand, buy the pump.

#### 7.8.3 Modulating flow has a real use, and it is comfort rather than capacity

This aligns with the §0 objective. In cooling, water flow sets the coil surface temperature,
which sets the sensible and latent split. Higher flow gives a warmer coil, more sensible capacity
and less dehumidification. Lower flow gives a colder coil, less total capacity and more moisture
removed. A zone that holds setpoint yet feels clammy can therefore improve with reduced flow,
while its BTU output falls. This mirrors the CFM tradeoff in §0.3, so optimising BTU and
optimising comfort diverge on the water side too.

Heating carries no latent load and offers nothing to modulate; take flow up to saturation and
stop. Any modulating-flow project would earn its keep in cooling alone, on the humidity axis.

Defer it regardless. The zone valves are two-position, so this needs modulating or characterised
control valves per branch, Belimo CCV class with 0–10 V or 3-point actuation, something to drive
them, and flow measurement to close the loop. That inserts a software failure mode into both the
heating and cooling paths for a gain bounded by saturation. Exhaust §7.8.1 and §7.8.2 first,
since they are cheaper, mechanical and permanent.

> One ceiling bounds all of the above. Secondary flow must stay below primary flow (§2.5f), and
> both primary pumps already run on HIGH. A loop needing more flow than its primary can supply
> calls for a larger primary pump rather than a faster secondary, and no per-zone valve
> arrangement avoids that. The ΔT-ratio method in §2.6.2 shows how close to the ceiling you
> already are, from thermometers alone.

---

## 8. Operational integration

**Freshness alerts.** Add rules to `grafana/provisioning/alerting/sensor-freshness.yaml`
following the existing pattern: 30 min staleness, `noDataState: Alerting`, and a never-true
sentinel for the threshold. Temperatures publish in Kelvin, so reuse the `value < 100` sentinel.
`flowRate` is never negative, so use `value < -1`, the shape `domestic-water-stale` already uses.

**Watchdog.** `scripts/arduino-watchdog.sh` pings only `.114` and `.219` and power-cycles the
shared Arduinos Shelly at `10.0.0.61`. This board will sit at the air handler and probably on a
different circuit, leaving it without auto-recovery. Either extend the watchdog with a second
plug or accept alert-only coverage and record that choice.

**Grafana.** Add a new row following the house conventions: `custom.axisWidth: 50` on every
timeseries, no per-panel `axisLabel`, and stepped-line timeseries rather than state-timeline for
the boolean `running`, since state-timeline cannot set row-label width and will not align.
Panels: the two ΔTs on one axis, capacity, UA, and SHR.

**Restart order.** Config edit, then `restart pivac-unico-mbr`, then `restart signalk`. Signal K
freezes retired paths at their last value until the server restarts, which CLAUDE.md documents
three times for relays, 1-Wire and Emporia, and which will recur here during development.

---

## 9. Build order

Sequenced against the §0 objective, summer comfort and capacity across both systems.

### Costs nothing

1. Run the §0.1 analysis on existing data: droop against equipment power against humidity, per
   zone, on hot afternoons. All three cooling units have been individually metered since August.
   This decides which zone to instrument first and may answer the question outright.
2. ✅ Temperature-precision fixes deployed 2026-08-18, `pivac.OneWireTherm` (#118) and
   `pivac.RedLink` (#119). Droop and every ΔT are quantitative from that date and earlier history
   is not (§2.6.0).
3. Confirm which loop the 2430 is on (§4.6). ✅ Pump taps surveyed, primary HIGH and both
   secondaries LOW (§2.5). Loop B set to LOW (§2.5b); raise it again before heating season.

### Cheap, high value against the objective

4. Two 10K NTCs in whichever BOVA zone step 1 identifies (§0.2), giving measured sensible
   capacity and the airflow-starvation signature with no water side and no flow meter. This also
   verifies latent performance in a zone whose settings are biased toward sensible (§0.3).
5. Four DS18B20s on the two secondary loops (§2.6.4): starvation, mixing, flow ratios and
   loop-idle detection for the whole chilled side, on the Pi's existing bus.
6. Utility-room Tier 1 sensors (§4.8): room ambient, and restore leak detection, which closes a
   regression.

### The node itself

7. Verify the fluid (§2.2) and read commanded CFM per mode off the Smart Controller (§7.2).
   Consider doing the 30 % glycol top-up before commissioning, so the baseline sits on the final
   fluid.
8. Verify the NTC curve (§2.3) with an ice-bath check, Type II against Type III.
9. Bench-build the node with all four sensors and final firmware, then run matched-pair
   calibration (§7.1). Record the offsets and both DS18B20 ROM addresses in this document.
10. `ArduinoSensor` `rounding:` change (§6.1) as a PR. Small, isolated, backwards-compatible.
11. Install, DHCP-reserve by MAC, and add the config and service unit.
12. `pivac.UnicoAH` wrapper (§6.2) as a PR, then the Grafana row and freshness alerts (§8).
13. Join RedLink humidity (§7.3) for the latent split. Software only, and latent is comfort.

### Only if the data asks for it

14. Flow meter, primary loop first (§2.6.1), which converts every ratio into an absolute number
    for all loops and returns more than a per-coil meter.
15. Commissioning check (§7.2): in heating, `CFM_derived / CFM_commanded` should approach 1.0.
    This is the acceptance test for the whole chain. Heating is otherwise deprioritised, but it
    is the only latent-free window for validating the measurement.
16. `wsup − IN` reverse-mixing series (§2.5f), one subtraction, verification rather than
    diagnosis.
17. Collect a cooling season. Analyse per §7.4 and decide the flow question per §7.7.

## 10. Open questions

- Which loop is the 2430 on, utility room on Loop B or one of the Loop A zones? The most
  consequential unknown left, since it decides whether cooling-season flow is constant and
  therefore whether the flow meter is needed now or can wait a season (§4.6).
- Are there balancing valves on the branches today? Speed taps are known (§2.5), so per-branch
  balancing is the remaining unknown on the distribution side. It decides whether a starved loop
  can be fixed by redistribution or only by more total flow (§7.7).
- What is the Taco model on the chiller primary, and what is its curve? Needed to judge
  primary-against-secondary flow in cooling (§2.5c).
- Does the Taco run continuously through a cooling call or only with the compressor, and is it
  powered from the Chiltrix circuit and therefore visible in
  `electrical.emporia.house.chiltrix`?
- How many hydronic zones are there in total? Four water zones fit an HZ-432 exactly, three on
  Loop A plus utility on Loop B, but in winter the kitchen and great room take hot water too,
  implying more zone valves than one HZ-432 provides.
- In heating, does the hot water come from the NTI boiler or from the Chiltrix running as a heat
  pump? This does not affect the capacity measurement, since the water side is the water side,
  but it decides whether a heating-season efficiency figure is a COP against
  `electrical.emporia.house.chiltrix` or a combustion efficiency against gas input, which is a
  different calculation with a different denominator (§7.5).
- Are `IN` and `OUT` the primary-loop supply and return (§7.5)?
- Does the CX75 expose Modbus RTU (§7.5)?
- Which glycol, propylene or ethylene (§2.2)?
- Is there a balancing valve on this coil with a published flow chart (§4.6)?
