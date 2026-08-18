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
  meter — though on Loop B in cooling it is a single-zone loop and genuinely constant (§2.5).

**Goal:** Measure the actual BTU/hr the coil delivers, and enough surrounding state to tell
*why* it isn't delivering more. Feed it into pivac like every other sensor
(Arduino → `pivac.*` → Signal K → InfluxDB → Grafana).

---

## 1. Two corrections before anything else

**1. The Honeywell "10K sensors" are thermistors, not flow sensors.** The 10K parts bundled
with the Prestige/IAQ thermostat (C7089U outdoor, C7735A duct) are **10 kΩ-at-77 °F NTC
temperature sensors**. That is exactly what you want for supply/return *air* temperature —
the plan below uses them that way — but they measure temperature, not flow. The water flow
measurement is a separate purchase (§4).

**2. `pivac.ArduinoSensor` rounds temperatures to whole Kelvin — it cannot be used as-is for
this.** `pivac/ArduinoSensor.py:65`:

```python
kelvin = int(round(_to_kelvin(raw, scfg.get("scale", "fahrenheit"))))
```

1 K = 1.8 °F. The whole project rests on ΔT values of 10–20 °F, so quantising each endpoint
to 1.8 °F destroys the measurement before it reaches Signal K. **This is the single biggest
blocker in the existing code** and §6 proposes the fix (a `rounding:` key, matching the
convention `pivac.OneWireTherm` already has at line 113).

---

## 2. The physics that decides the whole design

### 2.1 The water side is the truth; the air side dry-bulb is not

- **Water side** carries *everything* the coil moved — sensible **and** latent:

  ```
  Q_total [BTU/hr] = K × GPM × ΔT_water[°F]
  ```

- **Air side, dry-bulb only** carries the **sensible** part:

  ```
  Q_sensible [BTU/hr] = 1.08 × CFM × ΔT_air[°F]
  ```

In **cooling** these do **not** agree, and they are not supposed to. Everything the coil
spends condensing water vapour shows up in the water ΔT and *not* in the air dry-bulb ΔT.
On a high-velocity Unico coil the latent fraction is large (SHR typically ~0.70–0.75), so
expect the air-side dry-bulb number to land **25–30 % below** the water-side number in
cooling. If you see that gap, nothing is broken — that gap *is* the dehumidification.

In **heating** there is no latent, so the two sides **must** agree. That makes heating season
your calibration window (§7.2).

### 2.2 `K` is not 500 — the loop is 25 % glycol

The textbook constant 500 assumes pure water (8.337 lb/gal × 60 × Cp 1.0). With glycol:

```
K = 500.2 × SG × Cp
```

| Fluid | SG | Cp (BTU/lb·°F) | **K** | Error if you use 500 |
|---|---|---|---|---|
| Water | 1.000 | 1.000 | **500** | — |
| 25 % propylene glycol @ 45 °F *(loop today)* | ~1.028 | ~0.935 | **~481** | +4 % high |
| 25 % propylene glycol @ 140 °F | ~1.010 | ~0.955 | **~483** | +3.5 % high |
| **30 % propylene glycol @ 45 °F** *(planned, pre-winter)* | ~1.035 | ~0.920 | **~476** | +5 % high |
| 25 % ethylene glycol @ 45 °F | ~1.035 | ~0.900 | **~466** | +7 % high |

**Action:** confirm the glycol *type* (propylene vs ethylene) and verify the *concentration*
with a refractometer rather than trusting the fill record. Put `K` in config, not in firmware.
A single number in `config.yml` is a 4–7 % systematic bias on every BTU figure you will ever
compute, so it is worth ten minutes with a refractometer.

> **⚠️ The planned 25 % → 30 % glycol change is a dataset discontinuity — plan for it.**
> Three things happen at once when the loop is topped up before winter, and if they are not
> anticipated they will read as a fault:
>
> 1. **`K` drops ~481 → ~476.** Update `fluid_k` in `config.yml` **on the day of the change**.
>    Leave it stale and every subsequent BTU figure is ~1 % high. This is precisely why the
>    constant lives in config and the Arduino computes no BTUs (§5) — it is a `git pull`, not
>    a reflash.
> 2. **Real capacity drops slightly.** Higher glycol means lower specific heat, higher
>    viscosity, and therefore lower flow at the same pump head and a modestly worse
>    heat-transfer coefficient. Expect a small genuine step down in capacity and UA — **a few
>    percent, not a fault.**
> 3. **Re-measure GPM after the change** if you are on the Phase-0 fixed-flow shortcut (§4.6).
>    The viscosity change moves the operating point on the pump curve, so a flow figure
>    measured at 25 % is no longer the right constant at 30 %.
>
> **Add a Grafana annotation on the changeover date.** A year from now, an unexplained step in
> the UA trend is exactly the kind of thing that gets misdiagnosed as fouling.

### 2.3 ΔT precision is the entire ballgame

Capacity error is directly proportional to ΔT error. At a design ΔT_water of 10 °F:

| Per-sensor error | Worst-case ΔT error | Capacity error |
|---|---|---|
| DS18B20 datasheet absolute (±0.9 °F) | ±1.8 °F | **±18 %** |
| After matched-pair calibration (±0.05 °F) | ±0.1 °F | **±1 %** |

A ±18 % measurement cannot answer "am I getting maximum BTUs". **Matched-pair calibration is
mandatory, not optional** (§7.1). The good news: DS18B20 *resolution* (0.0625 °C at 12-bit)
and *repeatability* are both excellent — it is only the absolute accuracy that is poor, and
absolute accuracy is exactly what cancels out of a difference once you have characterised the
offset.

The same argument applies to the 10K NTCs, and there it also disposes of a second problem:
Honeywell 10K sensors come in more than one resistance curve (Type II ≈ 32.6 kΩ at 32 °F,
Type III ≈ 29.5 kΩ at 32 °F). Guessing wrong costs several degrees absolute — but if both
duct sensors are the same part and you calibrate them as a pair, the curve error is
common-mode and drops out of ΔT. **Verify the curve anyway** with an ice bath: the two types
differ by ~10 % at 32 °F, which is unmissable on any multimeter.

### 2.4 The two ΔTs move in *opposite* directions — this is why measuring both is worth it

Your instinct to capture both the water and air deltas is the most valuable part of this
design. They are linked by the energy balance, so when capacity is down, *which* delta moved
tells you which side is the constraint:

| Signature | ΔT_water | ΔT_air | Capacity | Diagnosis |
|---|---|---|---|---|
| Water-starved | **up** | down | down | Closed/throttled balancing valve, plugged strainer, air-bound coil, failing circulator, zone valve not fully opening |
| Air-starved | down | **up** | down | Dirty filter, collapsed/undersized duct, blower speed tap, iced coil |
| Plant-limited | normal | normal | down | Entering water temp is wrong — buffer tank not at setpoint, chiller undersized for the load, changeover fault |
| Overpumped | **low** | normal | at spec | Capacity fine, pump energy wasted — throttle the balancing valve |

A single delta is ambiguous. Both deltas together isolate the fault. That is the payoff.

> **⚠️ The constant-airflow ECM suppresses the air-starved signature until it is severe.**
> The row above describes a fixed-speed blower. A constant-airflow ECM *holds* CFM against
> rising static pressure by drawing more torque, so a moderately dirty filter produces **no
> change in ΔT_air and no loss of capacity** — it shows up only as increased blower watts,
> which nothing here meters. The air-starved signature appears abruptly and late, once the
> motor runs out of authority. **The early warning is the CFM ratio in §7.2, not the air
> delta.** Do not read a stable ΔT_air as evidence the air side is healthy.

---

### 2.5 System topology — primary/secondary, two loops, and what it implies

Confirmed by David 2026-08-18:

```
   boiler ──┐                            ┌──── Loop A pump (Grundfos UP26-99F, hi/med/lo)
            ├──►  PRIMARY LOOP HEADER ───┤       └─ lower fam. room · kids room · master BR
  chiller ──┘      (closely spaced tees) └──── Loop B pump (Grundfos UP26-99F, hi/med/lo)
                                                 └─ utility room · kitchen · great room
```

One circulator per secondary loop, three speed taps each. Zone valves (HZ-432) per zone.

**The seasonal asymmetry is the important part:**

| | Loop A | Loop B |
|---|---|---|
| **Summer (chilled)** | all 3 zones on chilled water | **only the utility room** — kitchen and great room cool via their BOVAs |
| **Winter (hot)** | all 3 zones | all 3 zones |

Three consequences fall straight out of this:

**a) Loop B in cooling is a single-zone loop — hydraulically isolated.** With one zone valve
open and one pump running, there is nothing to share flow with. **If the 2430 is the utility
room, its cooling-season flow genuinely is constant**, the fixed-GPM shortcut in §4.6 is valid
for the whole cooling season, and it is by far the easiest first instrumentation target. It
only becomes a shared loop in winter, when kitchen and great room join it.

**b) Loop B in summer is probably overpumped.** That circulator is sized and speed-tapped for
*three* zones in winter. Running the same tap for **one** zone in summer drives far more flow
through that single coil than design — which shows up as an implausibly small water ΔT (3–5 °F
rather than 8–12 °F), wasted pump energy, and elevated mixing risk (below). **Dropping Loop B
to LOW for the cooling season is a free, reversible experiment** and the instrumentation in
this plan is exactly what proves whether it helped. Treat a very low measured ΔT as a finding,
not a sensor fault.

**c) Primary/secondary decoupling has a specific failure mode: reverse mixing at the tees.**
Closely spaced tees only deliver full primary supply temperature to a secondary loop while
**secondary flow ≤ primary flow**. If a secondary pump draws *more* than the primary supplies,
the deficit is made up by pulling water **backwards** from the return tee — blending return
water into the supply. In cooling that means warmer water reaching the coil; in heating,
cooler. Capacity drops and it looks exactly like "the plant can't keep up", so it gets
misdiagnosed as an undersized chiller.

> **You can already detect this, and it costs one comparison.** The node's `wsup` (water
> entering this coil) against `environment.inside.hvac.IN.temperature` (primary supply, already
> in InfluxDB):
>
> - **In cooling, `wsup` warmer than `IN` by more than pipe gain ⇒ reverse mixing.** The
>   secondary pump is overpumping its loop relative to primary flow.
> - **In heating, `wsup` cooler than `IN` by the same logic ⇒ same fault, opposite sign.**
>
> With **both** secondary pumps running, combined secondary flow is what has to stay under
> primary flow — so the worst case is a winter day with both loops calling, and the fix is a
> speed tap, not a bigger chiller. **Plot `wsup − IN` as a first-class series.** It is nearly
> free and it catches a design-level fault that no amount of coil-side analysis would find.
> (Confirm `IN`/`OUT` really are the primary header before relying on the sign — §10.)

---

## 3. Scope boundary (what this plan does *not* touch)

Explicitly out of scope, so the change stays reviewable:

- The DX/BOVA zones (kitchen, great room) — those are refrigerant, not water, and none of
  this applies to them.
- The boiler / Sentry path, DHW, domestic water, irrigation, the two pressure Arduinos.
- The existing 1-Wire bus on the Pi (`pivac.OneWireTherm`) — the new water sensors go on the
  **Arduino**, not the Pi bus (§4.1).
- No InfluxDB data is deleted and no existing Signal K path is renamed.

---

## 4. Hardware

### 4.1 Why everything hangs off one Arduino at the air handler

Put **all** sensors on the node, not split between the node and the Pi's 1-Wire bus:

- **Simultaneity.** `Q = K × GPM × ΔT` is only valid if flow and both temperatures are
  sampled at the same instant. Split across two collectors polling on different schedules,
  they are not.
- **Cable length.** 1-Wire is finicky over long runs; the Pi's bus already has a documented
  history of the OUT sensor dropping off for hours at a time (CLAUDE.md, 2026-05-31).
  A 30 cm run inside the air handler cabinet has none of that risk.
- **Precedent.** The DHW board (10.0.0.114) already runs a DS18B20 on an UNO R4 alongside its
  analog sensor, so the pattern is proven here.

One board per air handler. DHCP-reserve it by MAC in UniFi like the others.

### 4.2 Bill of materials

| Qty | Item | Notes |
|---|---|---|
| 1 | Arduino **UNO R4 WiFi** | Same as every other pivac node; 14-bit ADC is enough (§4.4) |
| 2 | **DS18B20**, stainless probe | Water supply + return. Waterproof probe version |
| 2 | Brass **thermowell** or pipe clamp + insulation | See §4.3 |
| 1 | 4.7 kΩ resistor | 1-Wire pull-up, DQ→5 V. **External — not the internal pull-up** |
| 2 | Honeywell **10K NTC** duct sensors | *You already have these.* Supply + return air |
| 2 | **10.0 kΩ 0.1 % metal-film** resistor | Divider reference. Tolerance → temperature error |
| 2 | 0.1 µF ceramic | ADC anti-alias, across the NTC leg |
| 1 | **Water flow sensor**, pulse output | §4.5 — the one real decision |
| 1 | 5 V PSU / USB supply | Consider the Arduinos Shelly (§8) |
| — | Pipe insulation, cable glands, enclosure | |

Optional (Phase 2, §7.3):

| Qty | Item | Notes |
|---|---|---|
| 1 | **SHT41** or SHT31 T/RH sensor, I²C | Return-air humidity → true SHR and latent split. **Probably unnecessary** — the IAQ thermostat already supplies this via RedLink (§7.3). Measure before buying |

### 4.3 Water temperature — thermowell vs strap-on

**Thermowell is correct; strap-on is acceptable if you insulate properly.**

- **Thermowell** (brass, ½" NPT into a tee): probe sits in the stream, fast and unambiguous.
  Requires cutting the pipe and draining that section of a glycol loop.
- **Strap-on**: DS18B20 clamped to bare, cleaned copper with thermal compound, then **fully
  buried under at least 25 mm of insulation extending 100 mm either side**. Reads within a few
  tenths of a °F of fluid temperature on copper at these flow rates. Skimping on the
  insulation is what ruins strap-on installs — an uninsulated probe reads somewhere between
  the water and the room and the error is *different* on the hot and cold pipes, which is the
  worst possible outcome for a ΔT.

Given the loop is glycol-filled and draining it is a chore, **strap-on with serious insulation
is the pragmatic choice** — provided you do the in-situ pair calibration in §7.1, which
measures and removes exactly this kind of installation error.

Mount both probes on **straight pipe, ≥5 diameters downstream of any fitting**, as close to
the coil connections as possible so you are measuring the coil and not the piping run.

### 4.4 Air temperature — reading the 10K NTCs

Standard ratiometric divider, one per sensor:

```
 5V ──[ 10.0 kΩ 0.1% ]──┬── A0  (and A1 for the second)
                        │
                     [ 10K NTC ]
                        │
                       GND         0.1 µF from A0 to GND
```

- **Ratiometric is the point.** Because the divider is fed from the same 5 V the ADC uses as
  reference, supply variation cancels. Do not add a separate precision reference.
- `analogReadResolution(14)` on the RA4M1. Near room temperature the divider gives ~31 mV/°F
  against a 0.305 mV LSB — about **0.01 °F per count**, so resolution is a non-issue and
  noise dominates. **Average 100–256 samples** per reported reading.
- Convert with Steinhart-Hart (or a beta fit) using the curve confirmed by the ice-bath test
  in §2.3. Put the coefficients in **firmware** (they are sensor-physics constants) but the
  **per-sensor offset in config** (§6).
- Self-heating is negligible in a moving airstream (~0.6 mW in a 10 kΩ leg).

**Probe placement matters more than probe accuracy:**

- **Return** sensor: in the return plenum, upstream of the coil, out of line-of-sight of the
  coil face.
- **Supply** sensor: in the supply plenum **downstream of the blower**, before the first
  takeoff. On a Unico the blower does the mixing; a sensor immediately at the coil face reads
  a stratified, unrepresentative slice.
- **Shield both from radiation.** A sensor that can "see" a 45 °F coil reads low regardless of
  air temperature.
- In cooling the supply sensor sits in ~95 % RH air — make sure the probe body is sealed and
  the leads exit downward so condensate cannot wick into the cable.

### 4.5 Water flow — the one real decision

Sizing, for an M2430 at nominal 2 tons:

```
24,000 BTU/hr ÷ (481 × 10 °F ΔT) ≈ 5 GPM
```

So specify for **3–8 GPM in ¾"–1" pipe**, with 25 % glycol, over a service range spanning
chilled (~45 °F) *and* heating (up to ~140 °F) duty. That temperature span rules out most
domestic water meters.

| Option | Cost | Verdict |
|---|---|---|
| **Hydronic paddlewheel / turbine, pulse out** (Seametrics SPX, Omega FTB, Onicon F-1100) — brass/SS, ≥200 °F | $200–400 | **Recommended.** Rated for the fluid, the temperature, and continuous duty |
| **Brass-body hall turbine** (Digiten/Gredia class, 212 °F rated) | ~$25 | Workable budget path; plastic rotor/bearing wear and calibration drift in continuous hot glycol are the risk. Re-verify annually against the energy balance |
| **Clamp-on ultrasonic** | $$$ | No plumbing cut, glycol-agnostic. Best if you would rather not open the loop |
| **DAE MJ-75a class** (as on the domestic meter) | ~$60 | **No.** Nutating-disc domestic meters are typically rated ~120 °F max and are not intended for closed-loop glycol |

> **A note on the GREDIA lesson.** CLAUDE.md documents a cheap hall turbine failing on the
> irrigation line, but the root cause there was a mismatch with **OpenSprinkler's** pulse-rate
> handling (>50 Hz and ≤0.0025 gal/pulse), not an inherent defect in the sensor class. On a
> dedicated Arduino ISR a **high** pulse rate is an advantage — it is what gives you
> instantaneous flow resolution. Do not rule out turbines on the strength of that note; rule
> out *plastic* ones on the strength of the temperature and duty cycle.

### 4.6 Do you need a flow meter? It depends which loop the 2430 is on

**This is the one fact that decides the BOM**, and §2.5 splits it cleanly:

| If the 2430 is… | Cooling season | Winter | Verdict |
|---|---|---|---|
| **Utility room** (Loop B) | **Single-zone loop — flow genuinely constant.** Nothing to share with | Shares Loop B with kitchen + great room | **Start without a meter.** Measure GPM once, run all cooling season on a constant, add the meter before winter if the data warrants |
| **Family room / kids / master** (Loop A) | Shares with two other zones, which all call together on hot days | Same | **Buy the meter.** Per-zone flow varies exactly when it matters |

If the target is the utility room you can commission the whole chain cheaply, on constant flow,
and let a season of data tell you whether the meter is worth it. That is a materially better
starting position than Loop A, and worth considering when choosing which handler to do first
even if Loop A is where the comfort complaint lives.

**Why sharing matters on Loop A.** Three zone valves on one fixed-speed circulator are
hydraulically coupled: opening a second valve lowers loop head, so **flow through this coil
drops**. Per-zone GPM becomes a function of how many other zones are calling — and it is
lowest on design days when all three run together, which is exactly when the capacity number
needs to be right. A fixed constant would be accurate single-zone and would silently overstate
capacity whenever it matters most.

**The cheap decisive test, either way:** at a steady outdoor condition, log this coil's
ΔT_water with **one zone calling**, then with **two or three**. If ΔT rises materially at the
same entering water temperature, the zones are sharing and flow is not constant. An afternoon
settles a $200–400 purchase — and on Loop A it also quantifies the starvation directly.

Note the three-speed tap is a **per-loop** lever, not per-zone: it changes total loop flow, so
it can raise everyone or lower everyone, but it cannot redistribute between zones. That
distinction drives §7.7.

### 4.7 Pin map

| Signal | Pin | Notes |
|---|---|---|
| DS18B20 ×2 (water supply + return) | **D2** | One shared 1-Wire bus, addressed by ROM. 4.7 kΩ → 5 V |
| Flow sensor pulse | **D3** | Interrupt-capable; debounce in the ISR |
| Return-air NTC | **A0** | Divider per §4.4 |
| Supply-air NTC | **A1** | Divider per §4.4 |
| *(Phase 2)* SHT41 T/RH | **A4/A5** | I²C |

Avoid D0/D1 (Serial1), D4/D5 (CAN), D10–D13 (SPI). Free general-purpose pins on the R4 are
D2, D3, D6, D7, D8, D9 — this uses two of them.

**Record both DS18B20 ROM addresses in this document when you build it.** CLAUDE.md already
carries a hard-won warning that the printed tags on these probes are not reliable physical
identifiers (one probe was found carrying two tags), and that the .114 board's DS18B20 ROM
exists nowhere in either repo. Do not repeat that.

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
| Drifting **down** over weeks/months | **The ECM is losing its fight with static pressure.** Dirty filter or developing duct restriction. This is the *early* warning the ECM otherwise hides (§2.4) — it masks restriction by drawing more torque until it can't |
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

Entering-air **wet-bulb** is what actually drives a chilled-water coil's capacity, and it is
what splits total into sensible and latent. Getting it needs entering dry-bulb (you will have
that at full precision from your own `aret` NTC) plus entering RH.

**The IAQ thermostat already supplies the RH.** `pivac.RedLink` publishes
`environment.inside.thermostat.<ZONE>.humidity` for every zone today
(`pivac/RedLink.py:331`, emitted as a 0–1 fraction). Return air *is* room air, so the zone
thermostat's RH is a good proxy for entering-air RH — the error is duct leakage and
infiltration into the return, not a modelling gap.

So Phase 2 is largely **a software join, not a hardware purchase**: combine your `aret`
dry-bulb with the RedLink humidity for the same zone to get entering enthalpy, which unlocks

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

### 7.4 What "maximum BTUs" actually means, and how to tell if you have it

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
| `electrical.emporia.house.chiltrix` (W) | **Plant power** — the denominator of COP |
| `environment.inside.hvac.UBT/LBT.temperature` | Buffer tank stratification — is the plant keeping up? |
| `environment.inside.hvac.IN/OUT.temperature` | Primary header supply/return — **plant-level ΔT**, and the reference for the reverse-mixing check `wsup − IN` (§2.5c) |
| `environment.inside.thermostat.<zone>.temperature` | Zone response — is the room actually recovering? |
| `environment.inside.thermostat.<zone>.humidity` | **Entering-air RH** — the latent split, free (§7.3) |
| `environment.outside.thermostat.temperature` | Load normalisation |
| `electrical.ac.switch.utility.CHIL` / `BLR` | **Changeover mode** (chilled vs hot water) — *not* a per-zone gate, see below |
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
> different and complementary question — "is *this zone* getting its share" — which is the one
> you actually asked, and which plant-level data cannot answer. Worth knowing that one meter
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

### 7.7 Would variable flow actually buy you BTUs?

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

**The key distinction: balancing *redistributes* capacity between zones, it does not create
it.** Total loop capacity is set by the plant and the pump. So read your data this way:

| Symptom | Meaning | Right intervention |
|---|---|---|
| One room short while another overshoots | Maldistribution | **Balance the branches** — this is exactly what balancing fixes |
| All rooms on a loop short together | Loop-wide shortfall | Speed tap, or the plant (EWT). Balancing does nothing |
| Water ΔT very low (3–5 °F) | Overpumped | Lower the tap. Also check for reverse mixing (§2.5c) |
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
5. **Modulating zone valves under active control.** Genuinely variable per-handler flow. This
   is where a custom pivac control loop would live — and it is the *last* resort, because
   items 2–4 capture most of the benefit with no software, no failure modes, and nothing to
   maintain.

**Do not skip to 5.** A ΔP circulator plus PIBVs solves the stated problem mechanically and
permanently. The value pivac adds here is **measuring whether any of it worked** — which is
precisely what you cannot do today, and precisely why the instrumentation comes first.

One caveat if you do pursue lower flow: the Chiltrix has a **minimum flow requirement**, and
the buffer tank exists partly to satisfy it. Reducing *secondary* flow is safe because
primary/secondary decouples the two — but confirm that decoupling really is intact (§2.5c)
before assuming it.

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

0. **Free levers first, before buying anything.** Confirm which loop the 2430 is on (§4.6);
   check both Grundfos speed taps and consider dropping Loop B to LOW for the cooling season
   (§2.5b). Neither costs anything and both change what the baseline data means.
1. **Phase 0 (§4.6)** — determine whether this zone is constant-flow. On Loop B in cooling it
   is by construction; on Loop A run the one-zone-vs-three ΔT test. This may remove the flow
   meter from the BOM for now.
2. **Verify the fluid (§2.2)** — glycol type and concentration by refractometer → set `fluid_k`.
   If the 30 % top-up is imminent, consider doing it **before** commissioning so the baseline
   is taken on the final fluid and there is no discontinuity to explain later.
3. **Read the commanded CFM per mode** off the Unico Smart Controller → `nominal_cfm` (§7.2).
4. **Verify the NTC curve (§2.3)** — ice-bath resistance check → Type II vs Type III.
5. **Bench-build the node**, all four sensors, final firmware.
6. **Matched-pair calibration (§7.1).** Record offsets. Record both DS18B20 ROM addresses here.
7. **`ArduinoSensor` `rounding:` change (§6.1)** → PR. Small, isolated, backwards-compatible —
   land it independently of everything else.
8. **Install**, DHCP-reserve by MAC, add config, add the service unit.
9. **`pivac.UnicoAH` wrapper (§6.2)** → PR.
10. **Grafana row + freshness alerts (§8)** → PR.
11. **Commissioning check (§7.2):** in heating, confirm `CFM_derived / CFM_commanded` ≈ 1.0.
    This is the acceptance test for the whole chain — if it fails, the flow meter or the
    temperature offsets are wrong, and no amount of later analysis will fix that.
12. **Join RedLink humidity (§7.3)** for the latent split. Software only.
13. **Add the `wsup − IN` reverse-mixing series (§2.5c).** One subtraction, no new hardware,
    and it catches a design-level fault that coil-side analysis cannot.
14. **Collect a season.** Then analyse per §7.4 and decide the flow question per §7.7.

---

## 10. Open questions

- **Which loop is the 2430 on — utility room (Loop B) or one of the Loop A zones?** This is
  the single highest-leverage unknown left: it decides whether cooling-season flow is constant,
  and therefore whether the flow meter is needed now or can wait a season (§4.6).
- **Are there any balancing valves on the branches today, and what are both Grundfos speed taps
  set to?** Free to check, and §2.5b suggests Loop B may be a tap too high in summer.
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
- Can the **Unico Smart Controller report its live commanded CFM** over serial/Modbus, or does
  `nominal_cfm` have to be a static config map? Does it vary airflow by stage/demand as well as
  by mode? (§7.2)
- Which glycol — propylene or ethylene? (§2.2)
- Is there a balancing valve on this coil with a published flow chart? (§4.6)

*Resolved by David 2026-08-18:* the blower is a software-configurable ECM (so CFM is commanded,
§7.2); the zone has an IAQ thermostat on RedLink (so entering-air RH is already collected,
§7.3); the loop goes to 30 % glycol before winter (§2.2); and **the HZ-432 drives one zone
valve per zone, each feeding its own air handler — there are no dampers.** That last one
confirms constant per-handler CFM and a clean 1:1 thermostat mapping, but it also means the
zones share a circulator, which is what put the flow meter back on the required list (§4.6)
and what makes `CHIL` invalid as a per-zone gate (§7.5).
