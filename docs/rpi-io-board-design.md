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

Four 4-position PTSM connectors give sixteen positions. They ship with the INT-PCB SET, so they are not a separate order. One per connector carries that group's
field common, leaving **12 monitored channels** — seven in service and five spare.

**A single shared common would give fifteen channels and is the wrong trade.** These are pluggable
connectors, so putting the only common on one of them means unplugging that connector disables
every channel on the board, including the eleven wired elsewhere. Servicing one group would take
the whole thing down. A shared return also converges every channel's current on one contact, so a
degrading connection there presents as all fifteen channels misbehaving at once, which is a far
harder fault to chase than three going dead together.

Four spare against seven in service — J4 position 1 carries the supply — already covers the known expansion — restoring the leak-pan
input displaced by `CHIL`, and a stage-2 `Y2` sense for the master bedroom. Three more channels
bought at the cost of unpluggability is not worth it.

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

**BCM 7–11 are left entirely unspent.** That is the SPI block, and keeping it contiguous means SPI
can be enabled later for an ADC or a display without disturbing a relay channel. BCM 19 was the
cancelled YOFF rewire and is free; its `config.yml` entry stays commented out.

## 6. Build notes

The durability rules are the same as the 1-wire enclosure work in
`docs/ds18b20-bus-topology.md` §6.2: ferrules on stranded conductors, strain relief at the
housing entry, no mid-air solder joints, and every channel labelled with the name it publishes
under so the board matches `docs/PhoenixContact-BC-RPI-label.docx`.

**Check the wire gauge against the terminals.** PTSM 0,5 accepts **24–20 AWG**, 0.5 mm² nominal.
18 AWG is 0.82 mm² and will not land in them, so any 18 AWG field run has to transition to smaller
wire before the board.

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

Place every part without soldering and check it fits: three DIP packages, twelve resistors, and the
wiring to the four PTSM connectors. Confirm the board clears the DIN housing with the cover on
before committing to a layout — the RPI-BC carrier is not generous.

Orient all three packages **the same way**, notch in the same direction. Mixed orientation is the
single most common way this build goes wrong, and it is invisible once the ICs are in.

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
bus on 3-position headers, and it can host GPIO channels beyond the twelve here. Do that only if
twelve is genuinely exhausted.

**Keep switched 24 V field wiring away from the 1-wire bus.** DQ is a slow open-drain line with a
passive pull-up and no differential rejection, and it is the bus that has already collapsed once.
Relay field wiring switches inductive loads, so bundling the two out of the same housing invites
exactly the pickup the twisted-pair guidance in `docs/ds18b20-bus-topology.md` §5 exists to
prevent. Optoisolation protects the *Pi*; it does nothing about two cables sharing a tray.

If the extension board does take relay channels, put them at the opposite end from the 1-wire
headers and bring their field wiring out of a separate entry. The DS2482, its pull-up and its
decoupling want that board space anyway, and they belong beside the 1-wire terminals rather than
across the housing from them.

Twelve channels against seven in service, with the leak-pan input and a `Y2` sense as the known
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
