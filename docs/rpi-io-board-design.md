# Raspberry Pi I/O Board — Relay Monitoring Inputs

**Status:** Design, for the rebuild of the RPI-BC interface board. · **Owner:** David

Covers the relay-monitoring input stage on the Phoenix Contact **RPI-BC INT-PCB SET**
(Mouser 651-2202994) inside the RPI-BC DIN housing: how many channels the terminals allow, why
the inputs are optoisolated rather than resistor-conditioned, the circuit, and the GPIO map.

Covers the 24 V supply for the input stage in §3.1 and the board side of the DS2482 1-wire
bridge in §8. The 1-wire bus itself, including the DS2482 procedure, is a separate document,
`docs/ds18b20-bus-topology.md`.

---

## 1. What sets the channel count

Four 4-position PTSM connectors give sixteen positions. They ship with the INT-PCB SET, so they
are not a separate order. One position per connector carries that group's field common, and **J4
position 1 carries the +14 V supply** (§3.1), leaving **11 monitored channels — seven in service
and four spare**.

Three quad packages give twelve optocoupler channels, so one is built with no connector position
behind it. That is why the parts list and the bench test in §6.1 both count in twelves.

**A single shared common would give fifteen channels and is the wrong trade.** These are pluggable
connectors, so putting the only common on one of them means unplugging that connector disables
every channel on the board, including the twelve wired elsewhere. Servicing one group would take
the whole thing down. A shared return also converges every channel's current on one contact, so a
degrading connection there presents as all fifteen channels misbehaving at once, which is a far
harder fault to chase than three going dead together.

Four spare already covers the known expansion: restoring the leak-pan input displaced by `CHIL`,
and a stage-2 `Y2` sense for the master bedroom. Three more channels bought at the cost of
unpluggability is not worth it.

Electrically either choice is fine; a group's three LEDs draw about 15 mA through a contact rated
4 A. The argument is entirely about service and diagnosis.

The Pi could carry 21 inputs, so the terminals still bind first. A later expansion is a connector
problem, never a pin problem.

## 2. Why optoisolation rather than a resistor network

A GPIO pad has already died on this system. **GPIO 26 is shorted to ground** and cannot be driven
high even as an output, diagnosed 2026-07-01 and attributed to the 2026-06-23 power event. That is
the failure mode this stage exists to stop, and a rebuild is the moment to address it.

A resistor network is a real alternative and it is worth being honest about how close it comes.
The series resistor that limits fault current and the pull-up that sets the idle level form a
divider, so they trade against each other: 1 kΩ series with a 10 kΩ pull-up holds a closed contact
at 0.3 V, well under the 0.8–1.0 V input-low threshold, limits a 24 V field fault to about 24 mA,
and needs three commodity passives per channel.

| Arrangement | Closed level | Wetting current | Field fault | Isolated |
|---|---|---|---|---|
| as built today: no series, internal ~50 kΩ pull-up | 0 V | 66 µA | unlimited into the pad | no |
| 1 kΩ series, internal ~50 kΩ pull-up | 65 mV | 65 µA | limits to ~24 mA at 24 V | no |
| 1 kΩ series, 10 kΩ pull-up, 100 nF | 0.3 V | 0.3 mA | limits to ~24 mA at 24 V | no |
| **Optocoupler** | **~0.2 V** | **2.9 mA** | **stopped outright** | **yes** |

**Wetting current is not the argument, and an earlier revision of this section was wrong to make
it.** The generic guidance is that dry contacts passing only tens of microamps grow oxide films and
read intermittently. This installation has run seven channels at 66 µA for over a year with no
intermittent reads, so 0.3 mA from a resistor network would be a fivefold improvement on something
already adequate. Service history beats the rule of thumb here.

The argument that survives is galvanic isolation. **GPIO 26 is dead**, and a resistor network
limits fault current into the pad without stopping it — a sustained short from a field wire to 24 V
still pushes ~24 mA into a clamp diode rated for a few. Isolation removes the shared ground between
the Pi and the control panel entirely, so no field wiring can reach the Pi's reference at all.

That said, the evidence does not prove isolation would have saved GPIO 26, because the failure was
never root-caused. "Attributed to the 2026-06-23 power event" is a hypothesis. If a transient
coupled onto a long field wire, a series resistor and a filter capacitor would probably have
absorbed it; if it arrived through the Pi's own supply, isolation would not have helped either.
Optoisolation is chosen because it is unconditionally correct rather than because it is the proven
cure, and because the parts were already on hand.

## 3. The circuit

One channel, repeated twelve times. The optocoupler replaces the GPIO-side resistors entirely; the
only resistor left is on the field side, setting LED current.

```
   FIELD SIDE (isolated)                 |            PI SIDE
                                         |
  +24 VDC ──[ 4.7 kΩ ]──┐                |          3.3 V
                        │                |            │
                     ┌──┴──┐             |      [ internal ~50 kΩ pull-up ]
                     │  ▼  │  LED        |            │
                     │ ─┴─ │             |            ├──────────────► GPIO
                     └──┬──┘             |            │
                        │                |          ┌─┴─┐
             CDP relay ─┴─ contact       |          │ ／│  phototransistor
                        │                |          └─┬─┘
  24 V common ──────────┘                |            │
                                         |          Pi GND
        connector pin 4                  |
```

Relay closed → LED lit → phototransistor conducts → GPIO reads LOW.

The whole board is that channel twelve times against three rails:

![Complete board schematic](rpi-io-board-schematic.svg)

Two things read off it that the single-channel view hides. The **`24 V COM` rail touches no channel**
— it exists only to tie the four connector pin-4 positions and the supply return together, because
each channel's return path leaves the board through its relay and comes back on that net. And the
**Pi ground rail is a twelve-way net of its own**, since every phototransistor emitter returns to it.
That rail and the `+V` rail are the two longest conductors on the board and the two that must never
meet.

**Polarity already matches.** `pivac/GPIO.py` computes
`presult = GPIO.input(pin) == (pullmode == "pulldown")`, so under the configured
`pullmode: "pullup"` a LOW pin reports as active. No `config.yml` change, and no InfluxDB
measurement is orphaned.

**The Pi side needs no components at all.** The phototransistor sinks milliamps against the
roughly 66 µA the internal pull-up sources, so the internal pull-up suffices. And the GPIO node is
now a short trace from the phototransistor to the pin, never leaving the board, so there is nothing
for an external pull-up or a filter capacitor to protect against — those belong to a
resistor-conditioned input, where the field wire runs to the pin itself. Contact bounce does not
change this: it modulates the LED on the field side, but `pivac.GPIO` polls every few seconds, so
at worst one sample lands mid-bounce in the cycle where a relay changes state and the next poll
corrects it.

**Connector pin 4 is the 24 V common, not Pi ground.** Bonding it to Pi ground destroys the
isolation this stage exists for. Label it `24V COM`, never `GND`.

### 3.1 Powering the input stage

The panel's 24 V is **AC**, from the same transformer that energises the relay coils, and that
decides the supply question. The LTV-847's LED reverse-breaks down near 5–6 V, so 24 VAC puts
about 34 V peak across it on every negative half-cycle and a bare quad optocoupler fails quickly.

**The sense loop runs on an isolated DC supply, and the voltage is free.** The LED only needs
current, so any isolated DC source works with the resistor sized to it. Nothing on the Pi side
changes with the choice.

| Supply | LED resistor | Current | Dissipation |
|---|---|---|---|
| 5 V | 820 Ω | 4.6 mA | 17 mW |
| 12 V | 2.2 kΩ | 4.9 mA | 53 mW |
| **14.7 V** (this build) | **4.7 kΩ** | **2.87 mA** | 39 mW |
| 24 V | 4.7 kΩ | 4.85 mA | 110 mW |
| rectified 24 VAC (~32.5 V) | **same 4.7 kΩ, in 1/2 W** | 6.7 mA | 0.21 W |

**A 12 V DC wall wart measuring 14.7 V is the build value, and 4.7 kΩ is the resistor.** Measure
rather than trusting the label — the load is 58 mA against a wart rated for several hundred, so an
unregulated unit sits near its peak, and this one reads 2.7 V above its marking.

**4.7 kΩ is chosen because it spans both supplies**, giving 2.87 mA now and 6.7 mA on rectified
24 VAC later, so the upgrade swaps only the wattage rating and never the value or the arithmetic.
2.87 mA is well inside what the stage needs: the optocoupler must sink 66 µA to hold the pin low
and delivers about 1 mA at that drive even at a worst-case transfer ratio, a 15× margin, while
running the LED gently slows the ageing that erodes transfer ratio over a decade. On the contact
side it is 43× the 66 µA that has been adequate in service for a year.

Lower voltage costs margin on the field wiring, not function. Wetting depends on voltage as well as
current, so a higher-voltage loop punches through contact oxide that a low one can sit on top of,
and a transient coupled from the panel's switched inductive loads is a larger fraction of 5 V than
of 24 V. 12 V keeps most of that margin.

**The upgrade path is the panel's own 24 VAC**, which removes the wall wart. Add a bridge rectifier
and a **100 µF, 50 V** capacitor at the same board input and change the twelve resistors to 4.7 kΩ
at 1/2 W; nothing else moves, so leave board space at the input for them. Measure the transformer
open-circuit first — control transformers often read 26–28 VAC at light load, rectifying to 36–39 V
rather than 32.5. Capacity is not a constraint: 58 mA of DC draws roughly 150–200 mA RMS through a
capacitor-input rectifier. The capacitor is not optional on that path, because unsmoothed the LEDs
go dark near each zero crossing and `pivac.GPIO` samples instantaneously, so channels read inactive
at random.

**The transformer's exact voltage does not matter, which is why 4.7 kΩ was the right forced
choice.** Control transformers read high at light load, and rectified output is `VAC × 1.414 − 1.4`
for the two diode drops:

| Transformer | Rectified | LED current | Resistor dissipation |
|---|---|---|---|
| 24 VAC | 32.5 V | 6.7 mA | 0.21 W |
| **25.9 VAC** (measured, this panel) | **35.2 V** | **7.24 mA** | **0.246 W** |
| 28 VAC | 38.2 V | 7.9 mA | 0.29 W |
| 30 VAC | 41.0 V | 8.5 mA | 0.34 W |

Every row is inside the 3–10 mA the stage wants and inside a 1/2 W part. A 2.7 kΩ sized for the
wall wart alone would have drawn 13.7 mA at 0.51 W on a 28 VAC transformer and needed a 1 W
resistor.

**Check the capacitor's voltage rating against the measured transformer.** At this panel's
25.9 VAC the rectified 35.2 V is 70 % of a 100 µF **50 V** part, inside the 80 % an electrolytic
wants. Above about 28 VAC the rectified 41 V reaches 82 % and the part should be 63 V instead.

What that path gives back is the failure-mode distinction. Sharing the coil transformer means a
control-power failure also removes the ability to report it, since every channel reads inactive and
that is indistinguishable from an idle system. It is narrow in practice — the boiler and chiller
stop running, loop temperatures drift, and `CHIL` never asserts on a hot day, all already alerted
on.

Do not fit per-channel AC-input optocouplers in place of the bridge. They chop at line frequency,
which puts the same sampling problem on every channel and needs an RC filter on each to fix.

**Feed 24 V once, at the board.** The resistor and the LED are board-mounted, so no supply
conductor goes out to the relays. Field wiring keeps the topology it already has: one conductor per
channel from the board to that relay's N/O pole, and one common daisy-chained along the string.
Only the common changes character — it is now the transformer common returning to connector pin 4,
where today it is Pi board ground.

**The supply lands on J4 rather than a board terminal, so the housing never has to be opened.**
`+V` goes to **J4 position 1** and the return uses **J4 position 4**, which is already the COM net,
so the cost is one spare channel — BCM 18 — leaving four spares against a known expansion of two.
Unplugging J4 then de-energises every channel, which is acceptable because J4 is the expansion
connector with nothing in service on it, and it doubles as a single-point service disconnect for
the sense loop.

**Label that position `+14V` on both the board and the plug, and keep it at the end of the
connector.** A live position sitting among dry-contact positions is a hazard: a relay contact wired
into it by mistake puts a direct short from the supply to COM through that contact. The conductor
also leaves the enclosure without current limiting, so mount the supply at the housing and keep the
run short. The reverse-protection diode can sit in the barrel adapter's screw terminal rather than
on the board, which keeps it outside the case too.

**The board is the common point, so no panel-side terminal block is involved.** Each group's common
daisy-chains along its relays and returns to pin 4 of that group's connector; the four pin-4
positions tie together on the board, and the supply's V− lands there once. The property that
justified four commons in §1 still holds, because the split lives at the connectors: pulling J2
disconnects its common without touching J1's. No additional feed-throughs are needed.

Two failure modes follow from the change. A channel conductor shorted to the 24 V common lights
that LED and reads permanently **active** — a false "on" rather than a false "off", which is the
safer direction for a monitoring input but worth labelling for. And a channel conductor shorted to
chassis or to Pi ground now does nothing at all, which is the entire point of the stage.

## 4. Parts

| Item | Part | Notes |
|---|---|---|
| Optocoupler | **LTV-847** (or PC847), quad, DIP-16 | 3 packages cover 12 channels. Through-hole, suits perfboard. `LTV-817`/`PC817` DIP-4 if singles are preferred. |
| LED resistor | **4.7 kΩ**, 1/4 W, 1% metal film | one per channel — twelve. 1/2 W if the 24 VAC upgrade is fitted |
| ~~GPIO filter~~ | not needed | see below |
| DC supply | 12 V wall wart (load is 58 mA) | feeds the sense loop — see §3.1 for sizing |
| Bridge rectifier | **DB107**, DIP-4 through hole, 1 A / 1000 V | later, if moving to the panel's 24 VAC |
| Smoothing capacitor | **100 µF, 50 V** radial electrolytic, 105 °C | only with the bridge, across the rectified feed |

Channel-to-channel isolation inside the quad package is absent, which is fine here because every
channel already shares the same 24 V common. Only the field-to-Pi barrier matters.

Sizing, at 24 VDC with an LED forward drop near 1.2 V:

- On a regulated 24 VDC supply, 4.7 kΩ → **4.85 mA**, dissipating 0.11 W, comfortable in 1/4 W.
- On rectified 24 VAC (~32.5 V), 4.7 kΩ → **6.7 mA**, dissipating 0.21 W, so a **1/2 W** part.
- At a worst-case current transfer ratio of 50 %, collector current is about 2.4 mA against the
  66 µA the pull-up needs — roughly 36× margin, so saturation is not in question.
- Running the LED near 5 mA rather than 20 mA also slows the LED ageing that erodes transfer ratio
  over a decade of continuous duty.
- For more wetting current use 2.2 kΩ, which gives 10.4 mA but dissipates 0.24 W and therefore
  needs a **1/2 W** resistor.

**If any input is live 24 VAC rather than a dry contact**, that channel needs a bridge rectifier
ahead of the LED, or an AC-input optocoupler such as the **LTV-814** whose bidirectional LED
accepts either polarity. An AC-input part chops at line frequency, so filter it or let the poll
interval average it. The CDP relays provide dry contacts, so this applies only if the scheme
changes.

## 5. GPIO map

Reserved and unavailable: **GPIO 2 and 3**, spent on the DS2482's I²C (§8), **GPIO 0 and 1** (pins 27/28) for
the HAT ID EEPROM, **GPIO 26 dead permanently**, and **GPIO 14/15 kept as a serial console** —
the recovery path on a headless DIN-mounted Pi when the network drops, which has happened here.
**GPIO 4 is deliberately left unassigned**, even though the DS2482 frees it. Rollback to
`w1-gpio` needs the pin, so a relay channel there would make this board depend on the migration
succeeding. Leaving it out keeps the board correct in both states; promote it to a spare only
once the bridge has run through a heating season.

`dtparam=spi=off` and the commented-out I²S line leave BCM 7–11 and 18–21 as plain GPIO. Leave
both settings alone.

The seven existing channels keep their pins, so no field wiring moves and no measurement history
is orphaned. Channels are grouped by what they watch rather than by pin order, so a connector can
be unplugged without splitting a system.

| Connector | Pin 1 | Pin 2 | Pin 3 | Pin 4 |
|---|---|---|---|---|
| **J1** — boiler / DHW | `ZV` — BCM 17 | `DHW` — BCM 27 | `BLR` — BCM 22 | **24 V COM** |
| **J2** — cooling | `CHIL` — BCM 25 | `BOS1` — BCM 6 | `BOS2` — BCM 5 | **24 V COM** |
| **J3** — mixed | `DEHUM` — BCM 12 | spare — BCM 23 | spare — BCM 24 | **24 V COM** |
| **J4** — power + expansion | **`+14V` supply in** | spare — BCM 13 | spare — BCM 19 | **24 V COM** (also the supply return) |

J2 puts the three cooling sources together, matching the zone-to-source map in
`docs/cdp-chiller-rework-plan.md` §3, so a cooling question is answered from one connector.

### 5.1 Header pins, and finding pad 1

Wiring the fan-out needs physical pin numbers, not just BCM numbers:

| Physical | BCM | This board | | Physical | BCM | This board |
|---|---|---|---|---|---|---|
| 1 | — | 3V3 → DS2482 VDD | | 22 | 25 | `CHIL` |
| 3 | 2 | DS2482 SDA | | 29 | 5 | `BOS2` |
| 5 | 3 | DS2482 SCL | | 31 | 6 | `BOS1` |
| 8 / 10 | 14 / 15 | serial console — leave | | 32 | 12 | `DEHUM` |
| 9 | — | GND → DS2482, emitter rail | | 33 | 13 | spare |
| 11 | 17 | `ZV` | | 35 | 19 | spare |
| 13 | 27 | `DHW` | | 37 | 26 | **dead — do not use** |
| 15 | 22 | `BLR` | | 27 / 28 | 0 / 1 | ID EEPROM — leave |
| 16 | 23 | spare | | 7 | 4 | left unassigned (§8) |
| 18 | 24 | spare | | 19,21,23,24,26 | 7–11 | SPI block — leave |

Grounds are physical **6, 9, 14, 20, 25, 30, 34, 39**; 3V3 is **1** and **17**; 5V is **2** and **4**.

**Find pad 1 on the board rather than deducing it.** A footprint marks pin 1, almost always as a
square pad among round ones, sometimes as a silkscreen `1` or a corner dot. The customer drawing is
a *simplified representation* that renders every pad as an identical circle, so it cannot settle
this — but the board itself will.

**Mounting face-down does reverse the apparent order**, so a standard Pi pinout diagram read
straight onto the carrier puts the odd and even rows on the wrong sides. That is a real trap, and it
is also why deducing pad 1 from which way the Pi faces is the hard way round: the footprint already
knows, and the mating is fixed by the socket.

**Confirm with the eight ground pins, which is faster than ringing out forty.** Grounds sit at
physical 6, 9, 14, 20, 25, 30, 34 and 39 — an irregular spacing no other net shares — so finding
those eight with a continuity meter pins the orientation, the numbering direction *and* the
row order at once, with nothing left ambiguous. Every other pad then follows by counting, and the
handful you actually use are worth confirming individually anyway.

That single ground net is also what the emitter rail lands on, so the check produces its first
wiring target as a by-product.

**BCM 7–11 are left entirely unspent.** That is the SPI block, and keeping it contiguous means SPI
can be enabled later for an ADC or a display without disturbing a relay channel. BCM 19 was the
cancelled YOFF rewire and is free; its `config.yml` entry stays commented out.

## 6. Build notes

The durability rules are the same as the 1-wire enclosure work in
`docs/ds18b20-bus-topology.md` §6.2: ferrules on stranded conductors, strain relief at the
housing entry, no mid-air solder joints, and every channel labelled with the name it publishes
under so the board matches `docs/PhoenixContact-BC-RPI-label.docx`.

**Use 22 AWG for new runs, and no run needs a gauge transition.** PTSM 0,5 is rated **24–20 AWG**,
0.5 mm² nominal. The **18 AWG** already in service is 0.82 mm², above that rating, and it lands and
works — but it stuffs the terminal, and the finer gauge is the better choice wherever a run is
being made or remade. 22 AWG is on hand along with 20 and 24, all inside the rated range. Ferrules
apply only to stranded conductors; solid lands directly.

**Vestigial line to remove with this build.** `pivac/GPIO.py:17` runs
`os.system('modprobe w1-gpio')` at import, a leftover from when the GPIO and 1-wire modules shared
setup. It is harmless — without the device-tree overlay the module instantiates no master — but it
is actively misleading once the DS2482 owns the bus, so it goes when §8 lands.

### 6.1 Assembly sequence

Written for someone comfortable with a soldering iron who has not built many boards. The ordering
matters more than the technique: each step verifies the one before it, so a mistake is found while
it is still cheap to fix.

**Consider adding three DIP-16 sockets to the order.** They let the board be powered and measured
before any optocoupler is committed, they remove soldering heat from the ICs entirely, and a dead
channel later becomes a swap rather than a desolder. They are the one addition worth making to an
order that is otherwise closed.

#### The board itself

From Phoenix Contact's customer drawing 00914691/00 for ident 2202994, in
`~/OneDrive - DGLC/Claude/HVAC Manuals/phoenix contact pcb.pdf`:

| | |
|---|---|
| Board | 59 × 85 mm, 1.6 mm thick |
| Matrix | **2.54 mm pitch, ⌀1.0 mm plated holes** |
| Terminal area A | `PSTD 0,65×0,65/40-2,54` — the 40-position Pi header |
| Terminal area B | `PTSM 0,5/4-HH-2,5-THR` — the 4-position connector footprints, 2.5 mm pitch |

Two features decide the wiring. **The Pi header fans out on traces into the matrix**, so every GPIO
arrives at its own matrix pad and the Pi-side connection is pad to pad — no wiring to the header
itself. And **the matrix is isolated pads with no bus strips**, so the `+V` and COM rails have to be
built rather than picked up. The drawing is marked *simplified representation*, so confirm that
second point with a continuity check across two adjacent holes before laying anything out; it takes
ten seconds and the whole rail plan depends on it.

**The cross-hatched bands are restricted areas**, defined as such in the drawing's own General
Information block. They mark where something mechanical intrudes — housing ribs, standoffs, the Pi
above, connector bodies — so nothing may occupy that space.

**They matter more here than on a normal build, because they are on the back and so is all the
wiring.** Every rail and every point-to-point run goes on the solder side, since socket pads are
unreachable from the other face. So the restricted bands and the wiring plan compete for the same
surface, and that is the constraint most likely to force a layout change.

What the drawing does not give is the permitted height — whether a band is a total keep-out or
allows something low-profile. Formed 22 AWG lying flat is a fraction of a millimetre proud and may
well pass where a component body would not. **Settle it against the board and the housing during the
Step 1 dry-fit, cover on**, and route the rails clear of the bands if there is any doubt. This is
the reason that dry-fit is a step rather than a formality.

#### Interconnect — how a connection is actually made

Deciding this up front is what keeps the wiring short, and short wiring is what makes the rest of
the sequence easy to verify. The whole board is **three rails, twelve resistors and 22 point-to-point
runs** — the runs being an LED cathode and a phototransistor collector for each of the eleven landed
channels.

**Three rails, one continuous conductor each.** Two are on the field side: `+V` feeding twelve
resistors, and `24 V COM` tying the four connector pin-4 positions together. The third is on the Pi
side: **every phototransistor emitter returns to Pi ground**, so twelve emitters share one rail to a
ground pad on the header fan-out. Run each as a single length of **bare 22 AWG solid copper** rather
than a chain of jumpers. It is lower impedance, obvious to trace a year later, and it is what makes
Step 3 diagnostic: a rail fault shows as a *run* of dead pads with a clear starting point, where a
chain of jumpers gives one dead pad and no indication of which joint failed.

**All three go on the solder side.** Socket pads are unreachable from the component side once the
socket is in, so the ground rail has no choice; the other two follow it so there is one convention
rather than two.

**Only the `+V` rail can run straight through its targets, and the reason generalises.** Its targets
are the twelve resistor leads, and *you* place those — so put all twelve upper leads in one row and
run the rail along it, soldering to each. The other two rails serve pins whose positions are fixed
by a part, and in both cases the pins they must reach alternate with pins they must not touch.

**Along a DIP's top edge the pins run C E C E C E C E** — collector on 16, emitter on 15, collector
on 14, and so on — so a rail laid down that pin row shorts every phototransistor it passes. **At a
connector only pin 4 is COM**; pins 1–3 are channels, so a rail along the connector pin row shorts
all eleven channels to COM.

**So those two rails run in a free row offset from the pins they serve, with a short stub down to
each target** — twelve stubs for the ground rail, four for COM. One hole pitch is enough offset.
Either cut individual stubs, or form the rail wire into a comb with a tab at each target and lay it
once; the comb is tidier and the stubs are easier to correct.

**Rails bare, point-to-point runs insulated.** That is what makes the crossings a non-issue: an
insulated cathode run passing over a bare rail is not a short, and the cathode runs do have to cross
the `+V` rail, because anodes and cathodes alternate along the package's bottom edge. **Sleeve only
where a rail crosses a rail** — the `+V` feed coming up from J4.1 past the COM rail is the one place
that happens.

**The `+V` rail and the Pi ground rail must never meet, and they are the two that look most alike.**
Both are bare wire spanning most of the board, and bridging them destroys the isolation the whole
stage exists for. Keep them on opposite sides of the DIP row, matching the pin-1-to-8 versus
pin-9-to-16 split, and route them so they never approach each other.

**The resistor is the connection, not something a wire connects to.** Each channel needs 4.7 kΩ from
the `+V` rail to its LED anode, so place the resistor to span that gap directly: one lead into a
free hole on the rail row, the other reaching the socket's anode pad. That is the whole connection.
Twelve resistors, no jumper wires on that leg at all. Stand a resistor on end if a horizontal span
will not reach; the lead can be formed to any multiple of 2.54 mm.

**Everything else: 22 AWG solid insulated, formed to right angles.** Strip a few millimetres, bend
the wire flat to the board with pliers, and run it. It lies flatter and traces better than fine
stranded wire. 30 AWG Kynar exists for dense boards where wires must share holes, and this board is
not dense enough to need it.

Two mechanical rules matter more than the wire choice.

**A wire and a socket pin share the pad, never the hole.** The holes are ⌀1.0 mm and 22 AWG is
0.64 mm, so the wire fits a hole on its own but cannot go into one the pin already fills. Forcing it
lifts the pad. The sequence is: solder the socket pin in the hole as normal, then on the solder side
tin the wire end a few millimetres, lay it **flat across the annular ring** — the exposed copper
around that hole — against the pin's existing solder fillet, and reflow so the solder wets both.
One pad, two conductors, one continuous fillet.

**Do not wrap wire around a pin, and do not tack it to the side of one.** Neither is a gas-tight
joint on a short flat socket pin, both are fatigue points, and both interfere with seating a chip.
Wire wrapping is a real technique but it needs wire-wrap sockets with long square posts, 30 AWG
wire and a tool, and the added height fights the housing clearance checked in Step 1.

**If the ring feels too tight to work on, use the adjacent hole instead.** Run the wire through a
free hole next to the pin, then link that hole to the socket pad with a short piece of bare wire on
the solder side. Both ends of the insulated run are then plain through-hole joints and only the
2.54 mm link is a surface joint. It costs one extra joint per channel and is easier to inspect.

**This applies at every socket pin, resistors included** — a resistor lead cannot enter an occupied
hole any more than a wire can, and it is one of the *larger* things you might try, not one of the
smaller ones. A ¼ W axial lead is **0.5–0.6 mm**, about the same as the socket pin's own tail, so
0.6 + 0.5 overruns a 1.0 mm hole outright. The rail end of each resistor drops into its own free
hole comfortably; only the anode end lands on a ring.

**What actually fits alongside a pin**, taking a machined socket's ⌀0.5 mm round tail as the case
that binds — two circles inside a 1.0 mm hole cannot exceed 1.0 mm across together, so the
conductor's ceiling is 0.5 mm before any allowance for solder:

| Conductor | Diameter | Shares a pin hole? |
|---|---|---|
| 20 AWG solid | 0.81 mm | no |
| 22 AWG solid | 0.64 mm | no |
| ¼ W resistor lead | 0.5–0.6 mm | no |
| 24 AWG solid | 0.51 mm | no — at the ceiling, no room for solder |
| 26 AWG solid | 0.41 mm | yes, but tight |
| 28 AWG solid | 0.32 mm | yes |
| 30 AWG wire-wrap | 0.25 mm | yes, with room for solder to flow |

**Measure your own pin before trusting the table.** A machined turned-pin socket has a round tail
near ⌀0.5 mm and is the tight case; a stamped dual-wipe socket has a flat blade around
0.5 × 0.25 mm, which pushed against the hole wall leaves noticeably more room and may take 24 AWG.
Thirty seconds with calipers settles which you have.

**A conductor that merely fits is not the goal — solder has to fit too.** A joint packed to the wall
wicks badly and sets up cold. That is why 30 AWG is the gauge people actually use for this, and why
26 AWG is the honest ceiling rather than 24. Plating takes a few hundredths off the nominal 1.0 mm
as well.

**The deciding argument is sequencing, not fit.** A wire can only enter a hole beside a pin if it
goes in *before* the pin is soldered, or if a finished joint is reheated — which risks unseating the
socket. So hole-sharing forces every run to be placed and routed during Step 2, before the bare-board
power-on check of Step 3 has confirmed anything. Ring landing keeps the two independent: solder the
sockets, verify the board empty, then wire, and change one run later without disturbing a socket
joint.

**So the recommendation stands.** Sharing a hole is not the technique here, and the ring landing
needs no clearance at all — which is what makes 22 AWG workable despite being far too large to
share. Every other lead and wire end drops straight through a hole, because
the GPIO fan-out pads, the connector positions and the rail rows all hold nothing.

**Count the work before starting, because it is more than it looks.** 46 of the 48 socket pins get
soldered: 12 resistor anode leads, 12 emitters onto the Pi ground rail, 11 cathodes and 11
collectors. The two spare are the twelfth channel's cathode and collector, which have nowhere to go
until a connector position frees up. Only **22 of those are discrete wires** needing strip, form and
route — the emitters are twelve tacks along one continuous rail, and the resistor leads come formed.

**That count is the honest argument for 30 AWG wire-wrap wire, which is thin enough to enter the
hole beside the pin** where 22 AWG is not: a 1.0 mm hole with a 0.64 × 0.25 mm socket pin in it has
room for a 0.25 mm conductor, which is what the gauge exists for. Against that, 22 AWG strips with
ordinary tools, holds a formed shape, and is far easier to trace. Soldering to an occupied pad is
routine work rather than a special technique — melt the existing fillet, feed the tinned end in — so
22 AWG remains the recommendation, but the choice is a trade rather than obvious.

**Keep the two sides of each package apart, because that is what the board is for.** Pins 1–8 are
the field side at 14 V and pins 9–16 are the Pi side. Route those two families on opposite sides of
the package and leave a clear channel beneath each DIP with no crossing nets. The optocoupler gives
you the isolation barrier internally; wiring that carries a field conductor across the Pi-side pins
bridges around it, and no amount of care inside the package compensates.

**Seating a socket:** solder two diagonal corner pins first, check the socket sits flat against the
board, then solder the remaining fourteen. A socket soldered at an angle cannot be corrected
without removing it. Leave the optocouplers out of the sockets until Step 4.

#### Step 0 — identify the pinout with a meter, before anything is soldered

**Do this even though the expected arrangement is written below.** Getting it wrong destroys all
four channels in a package at once, and the arrangement here could not be verified against
Lite-On's datasheet — both their PDF host and SnapEDA refuse automated retrieval.

Put the meter in **diode-test** mode and probe one chip:

- Across an **LED pair** (red on anode, black on cathode) it reads roughly **1.1 V**, and **open**
  with the leads reversed. That identifies both the LED half of the package and which pin is the
  anode.
- Across a **phototransistor pair** it reads **open both ways** — there is no diode junction to
  find.

The expected arrangement, with pin 1 at the notch and numbering counter-clockwise:

| Channel | LED anode | LED cathode | Emitter | Collector |
|---|---|---|---|---|
| 1 | 1 | 2 | 15 | 16 |
| 2 | 3 | 4 | 13 | 14 |
| 3 | 5 | 6 | 11 | 12 |
| 4 | 7 | 8 | 9 | 10 |

So LEDs occupy pins 1–8 and phototransistors 9–16. **Write down what the meter actually says** and
work from that, not from this table.

#### Step 1 — dry-fit the layout

Everything mounts in the INT-PCB's own prototyping area, so no daughter board is needed. Place
every part without soldering and check it fits: three DIP packages, twelve resistors, and the
wiring to the four PTSM connectors. Confirm the board clears the DIN housing with the cover on
before committing to a layout — the RPI-BC carrier is not generous.

Orient all three packages **the same way**, notch in the same direction. Mixed orientation is the
single most common way this build goes wrong, and it is invisible once the ICs are in.

**Which way is decided for you.** Pins 1–8 are the LEDs and 9–16 the phototransistors, and on a DIP
with the notch at the left end pins 1–8 run along the bottom edge and 9–16 along the top. The board
fixes the rest: the Pi header is at the top and the PTSM connectors at the bottom. So **notch left,
phototransistor side facing the header, LED side facing the connectors** puts every run on its short
path and keeps the field and Pi wiring on opposite sides of each package, which is the separation
§3 asks for.

![Proposed board floor plan](rpi-io-board-layout.svg)

The bands drawn in copper are fixed by the drawing; everything else is a proposal to check against
the board before committing. `C`/`E` and `A`/`K` on the package edges are what force the offset
rails: the ground rail cannot follow the `C E C E` row and the COM rail cannot follow the connector
row.

**One prerequisite the drawing does not give you: which fan-out pad is which GPIO.** The header's
traces run into the matrix unlabelled, so ring them out with a continuity meter — probe from each
header pin to the pads near it — and write the map down before placing anything. Eleven of those
pads are wiring targets and getting one wrong moves a relay's identity, which then shows up in
InfluxDB as a renamed measurement rather than as an obvious fault.

#### Step 2 — solder in height order

Lowest first, so the board rests flat on the bench each time it is flipped:

1. **Twelve resistors**, lying flat.
2. **The `+V` rail and COM rail** — the wiring that ties J4 position 1 to all twelve resistors, and
   the four connector pin-4 positions together.
3. **IC sockets**, if used.
4. **Connector and terminal wiring** last, being tallest.

#### Step 3 — power on with no optocouplers fitted

This is the step that makes the rest safe. With no ICs in the sockets there is no current path, so
every LED anode pad should read **the full supply voltage relative to COM** — about 14.0 V after
the 1N4007's drop.

One sweep of twelve pads confirms supply polarity, the J4 wiring, the reverse-protection diode, and
all twelve resistor joints. **Anything reading 0 V is an open resistor or a missed joint; anything
reading negative means the supply is backwards** and the diode has done its job.

Power down before proceeding.

#### Step 4 — fit the optocouplers, then test each channel on the bench

With the board powered and connected to the Pi, short a channel's field pins together at the
connector — that simulates a closed relay contact. Two things should happen:

- **The LED lights.** It is infrared and invisible to the eye, but a **phone camera sees it** as a
  faint white or purple glow. That is a free confirmation that the field side is working.
- **The GPIO goes low.** Check it directly with `raspi-gpio get <bcm>`, which reports `level=0`.

Walk all twelve channels this way before any field wiring is connected. A channel that lights its
LED but does not pull the pin low is an orientation or socket-seating problem; one that does
neither is on the field side.

#### Step 5 — check for solder bridges

DIP pins sit 0.1 in apart and a bridge between two of them is easy to make and hard to see. Check
continuity between **every adjacent pin pair** on each package, and between neighbouring resistor
joints. On the LED side a bridge shorts one channel's cathode to the next channel's anode, which
makes two channels move together — a confusing fault to chase later, and a two-minute check now.

#### Step 6 — field wiring

Only now connect the panel. §6's rules apply: ferrules on stranded conductors, strain relief at the
housing entry, no mid-air joints, and every channel labelled with the name it publishes under.
Land `+14V` on J4 position 1 **last**, and confirm the label is on both the board and the plug
before the connector is ever inserted.


## 7. The extension board, and why relay wiring stays off it

The **RPI-BC EXT-PCB HBUS SET** (Mouser 651-2202995) in the adjacent housing carries the 1-wire
bus on 3-position headers, and it can host GPIO channels beyond the eleven here. Do that only if
eleven is genuinely exhausted.

**Keep switched 24 V field wiring away from the 1-wire bus.** DQ is a slow open-drain line with a
passive pull-up and no differential rejection, and it is the bus that has already collapsed once.
Relay field wiring switches inductive loads, so bundling the two out of the same housing invites
exactly the pickup the twisted-pair guidance in `docs/ds18b20-bus-topology.md` §5 exists to
prevent. Optoisolation protects the *Pi*; it does nothing about two cables sharing a tray.

If the extension board does take relay channels, put them at the opposite end from the 1-wire
headers and bring their field wiring out of a separate entry. The DS2482, its pull-up and its
decoupling want that board space anyway, and they belong beside the 1-wire terminals rather than
across the housing from them.

Eleven channels against seven in service, with the leak-pan input and a `Y2` sense as the known
additions, means this should not come up. Recorded so the option is a decision rather than a
discovery.

## 8. The DS2482 1-wire bridge belongs in this rebuild

The parts are on hand, and fitting the bridge during the board rebuild buys one round of downtime
instead of two. The full procedure — enabling I²C, instantiating over sysfs, pinning it with a
systemd unit, and rollback — is `docs/ds18b20-bus-topology.md` §7. What follows is only what the
board build has to get right.

**Mount it at the Pi, inside this housing.** I²C is a short-range bus and must never carry the
mechanical-room run; the long cable stays on the 1-Wire side, which is the whole reason for the
part. Tie AD0 and AD1 to GND for address `0x18`.

| DS2482 pin | Goes to |
|---|---|
| VDD | 3.3 V, physical pin 1 |
| GND | physical pin 9 |
| SDA | GPIO 2, physical pin 3 |
| SCL | GPIO 3, physical pin 5 |
| IO | trunk DQ |

**Two things come off the board when it goes in.** The discrete **2.2 kΩ** 1-Wire pull-up — the
DS2482 supplies its own weak pull-up plus an active one, and an external resistor fights both —
and any driver-side series damping resistor, whose only job is softening a weakly driven edge and
which therefore works against the part's sole contribution. Per-branch damping at a distribution
block would survive a master swap, but this bus is a chain and wants none.

**Keep the DQ rail at 3.3 V.** `w1-gpio` pinned that for you because GPIO 4 is not 5 V tolerant;
the bridge does not, and a master driving DQ to 5 V into probes powered from 3.3 V exceeds their
VDD + 0.3 V absolute maximum. The 1-Wire side *can* move to 5 V for noise margin once the Pi only
ever sees I²C, but the probes' VDD has to move at the same time. Do not mix the rails.

**GPIO 4 still stays unassigned**, even though the bridge frees it. Rollback to `w1-gpio` needs it,
and a relay channel sitting on that pin would make this board depend on the migration succeeding.
Promote it to a spare only once the bridge has run through a heating season.

**This is the section §7's warning is really about.** The 24 V feed of §3.1 is new switched wiring
entering the same enclosure as a slow open-drain line with a passive pull-up and no differential
rejection — the bus that has already collapsed once. Optoisolation protects the *Pi*; it does
nothing about two cables sharing a tray. Bring the 24 V and the relay field wiring in through a
separate entry from the 1-wire trunk, and put the DS2482 and its decoupling beside the 1-wire
terminals rather than across the housing from them.
