# DS18B20 Bus Topology and the DS2482 Migration

**Status:** Reference. Written after the 2026-08-22 bus collapse, when adding the four
secondary-loop probes took the w1 bus from four healthy devices to zero. · **Owner:** David

Covers why the bus fails as it grows, how to wire it so it does not, and how to move off the
Pi's bit-banged `w1-gpio` master to a DS2482 hardware bridge. Machine facts here were verified
live on the Pi (`10.0.0.82`, Raspberry Pi 4 Model B Rev 1.5, kernel `6.18.34+rpt-rpi-v8`).

---

## 1. The failure this prevents

`w1_search: max_slave_count 64 reached` is an electrical fault, not sixty-four sensors. The
kernel's ROM search walks the address tree one bit at a time. When bit timing is unreliable it
reads both branches as present at every node, manufactures phantom devices until it hits the
64-device ceiling, and settles at a `w1_master_slave_count` of **0**. Healthy sensors go dark
alongside the new ones.

The failure is silent in pivac. `pivac-1wire` stays `active` and logs only
`OneWireTherm bus now has 0 sensor(s)`. The 30-minute Grafana freshness alerts are what
actually report it, and only for sensors whose outage exceeds their window.

Read the pin before assuming a short. `raspi-gpio get 4` returning `level=1` means the line
idles high and the pull-up is alive, so the problem is signalling integrity rather than a dead
short.

## 2. Why a star topology fails and a chain does not

In a star, every probe's captive lead runs independently back to a common point near the Pi.
Each lead is an unterminated transmission line. The falling edge of every 1-wire time slot
travels down all of them at once, reflects off the open far ends, and returns at a delay set by
each branch's length. Four branches kept those echoes clear of the master's sample point. Eight
put them on top of the bit it is trying to read.

A daisy chain is one trunk that leaves the master, visits each sensor location in physical
order, and ends at the last one. Each probe joins the trunk where it passes, on the shortest
stub that reaches. There is one line, one far end, and one reflection instead of eight.

## 3. Verify before rewiring

Do these in order. Rewiring first risks pulling cable to fix a probe fault that no topology
change can cure.

**Bisect the bus.** Add probes back one at a time against
`cat /sys/bus/w1/devices/w1_bus_master1/w1_master_slave_count`, starting with **PA1A**
(`28-000000cc0c90`), which logged `err=-5`. A probe that kills the bus every time is that probe
or its wiring. A bus that fails only past a device count is electrical loading, and §4–§6 apply.

**Confirm each probe's pinout on the bench.** Stainless-probe wire colours are not consistent
between batches, and a probe with DQ and VDD swapped takes the whole bus down. Put each one on
the UNO R4 rig used for the PA1–PA5 calibration and confirm it enumerates before it goes near
the Pi.

**Supply voltage is already ruled out.** The Pi's bus runs at 3.3 V throughout, so the
DS18B20's `0.7 × VDD` input-high threshold sits at 2.31 V and the bus reaches it with margin.
The mode is recorded here so it is not re-investigated: a probe powered from 5 V needs 3.5 V to
register a logic high, which a 3.3 V bus never delivers, and it degrades with loading rather
than failing outright. `docs/ds18b20-provisioning.md` specifies 5 V for the Arduino bench rig,
where that is correct. Carrying it across to the Pi is what would introduce the fault.

## 4. Building the chain

Pick a route that passes near the tees, the buffer tank, and both secondary loops. Run one trunk
along it. Put a junction at each sensor where the trunk arrives, the probe lands, and the trunk
continues out, all on the same three terminals. Wago 221s or a small DIN block work; use
gel-filled splices anywhere damp.

Then cut each probe lead to the shortest length that reaches its junction. That is the point of
the exercise, and coiling the slack instead defeats it. Trimming a DS18B20 lead is a normal,
reversible modification.

Keep the trunk linear. No branch at the master, no spur that doubles back, and nothing left
hanging as a stub beyond the probe leads themselves.

### 4.1 Distribution blocks, and when they count as a chain

A commoned 1-to-4 block whose fourth port feeds the next block is a daisy chain **if the blocks
are distributed along the run**, and a star if they are all clustered at the Pi. The blocks are
not what decides it. Stub length is.

All ports of such a block are one electrical node with no impedance between them, so a signal
arriving sees every port diverge at once. Put four of them side by side at the Pi and each probe's
full-length lead is still a stub off a common junction, which is the star in §2 with extra
hardware. Mount one **at each sensor location**, run the trunk block to block, and cut each probe
lead short enough to reach only its local block, and the chained blocks *are* the trunk. That is
a proper chain, and a more serviceable one than splicing.

The sensors here fall into four natural pairs, which maps onto four blocks:

| Block | Probes | Location |
|---|---|---|
| 1 | `IN`, `OUT` | the closely spaced tees |
| 2 | `UBT`, `LBT` | buffer tank, upper and lower |
| 3 | `LOOPA_SUP`, `LOOPA_RET` | loop A, kids and master bedroom |
| 4 | `LOOPB_SUP`, `LOOPB_RET` | loop B, lower family room, kitchen, great room |

Each block carries trunk-in, trunk-out and two probes, so a 4-conductor lever block per conductor
is exactly the right size. Three blocks per location, one each for DQ, VDD and GND.

The blocks also give a per-probe series resistor somewhere sensible to live, in that probe's DQ
port, if a lead cannot be trimmed short. A chain with short stubs does not need §6 at all.

### 4.3 The enclosure side is already right; the hub is outside it

The 1-wire bus leaves the **RPI-BC EXT-PCB HBUS SET** (Mouser 651-2202995) on a **single**
3-position header, as 18 AWG solid to the first breakout. That is the trunk exit this document
asks for, so the enclosure side needs no change and the pull-up, plus the DS2482 if it is fitted,
simply stay on that board beside the header.

**The branching therefore happens at the first breakout, and that is the node to inspect.** If
eight probe leads fan out from it, the star in §2 is there, one connection outside the housing,
and everything in §4–§6 applies to that point rather than to anything on the Pi. If instead it
feeds block-to-block as in §4.1, the topology is already a chain and the fault is electrical
loading, which sends the diagnosis to the pull-up and §5.3 instead.

Establishing which of the two it is costs nothing and settles where the work goes. Nothing inside
the enclosure needs opening for it.

**One exception: the outdoor ambient run is a second branch.** It leaves the enclosure separately,
so the node at the header is a Y rather than a single trunk, and the outdoor cable is almost
certainly the longest on the bus. Length is capacitance, so that one branch probably dominates the
RC budget in §5.1 on its own. Measure with it connected, or the number will flatter the bus.

### 4.4 Restoring the outdoor sensor without re-breaking the bus

There are spare bench-calibrated probes for this: PA3 went to the tank and PA1/PA2 to the loops,
leaving the **PA4 and PA5 pairs** unused, with ice-point offsets already recorded in
`docs/ds18b20-PA1-5-calibration.md`.

**Sequence it last.** Reconnecting the longest branch on the bus is the same class of change as
adding the four loop probes, and doing it before the pull-up and topology are settled risks
reproducing the collapse with one more variable in play. Order: bisect, fix the pull-up, add the
loop probes, then outdoor.

**Better, give it its own bus.** A second DS2482-100 at address `0x19` — the AD0/AD1 pins select
`0x18`–`0x1B` — presents a completely independent 1-wire master. Put the outdoor run on one and
the mechanical room on the other, and neither can take the other down: a fault on a cable that
runs outside through weather and a wall stops being able to blank the buffer-tank probes. The
DS2482-800 does the same thing in one package across eight channels, though only the `-100` and
`ds2484` are named in the kernel module's alias table, so confirm channel handling before buying
one.

This costs nothing in software. Sensors from every master appear flat under
`/sys/bus/w1/devices/`, `OneWireTherm` iterates that directory, and the `28-*` names are
properties of the chips, so a split bus needs no config change and orphans no history.

**Alerting, when it returns.** `environment.outside.temperature` gets a freshness rule under a
**new UID** rather than reviving `outside-onewire-stale`. That UID is named in the `deleteRules:`
block in `sensor-freshness.yaml`, which CLAUDE.md says to leave in place permanently, and a UID
cannot sit in both `rules:` and `deleteRules:`. A new UID sidesteps the conflict and leaves the
delete block doing its job.

`sentry-outdoor-divergence` needs no change. It was repointed to
`environment.outside.thermostat.temperature` when the probe was repurposed and works as written; a
restored DS18B20 becomes a third outdoor source rather than a required one.

Should the star be there and re-cabling be unattractive, that breakout is the hub §6 describes, so
its per-branch 100 Ω resistors belong at that block rather than back on the extension board. Fitted
at the header they would sit on the trunk, in series with every probe at once, which damps nothing
and merely adds to the pull-up's load.

### 4.2 Which conductors have to follow the chain

The topology requirement is on **DQ**, and **GND has to follow it** because GND is DQ's return
path. The loop enclosed by the two is what sets inductance and pickup, so they belong in the same
cable end to end, ideally the same twisted pair. Giving DQ the long chained route while picking
GND up from a convenient local earth is the failure this rule exists to prevent.

**VDD is DC power and its topology is electrically irrelevant.** Eight DS18B20s draw roughly
12 mA between them, which over 30 m of 24 AWG drops about 30 mV. Chain it anyway, in the same
cable, because there is nothing to gain from a second run.

Fit a **100 nF ceramic across VDD and GND at each block**. It supplies the conversion-current
transient locally instead of pulling it down the trunk, and it costs pennies.

The single pull-up stays at the master end regardless. One for the whole bus, never one per block.

## 5. Cable and pairing

The rule people get wrong is that **DQ and GND must share one twisted pair**, so the data line has
its return conductor adjacent. Pairing DQ with VDD instead couples them and puts the pair's mutual
capacitance directly on the data line.

| T568B conductor | Signal | Pi header (while on `w1-gpio`) |
|---|---|---|
| white/orange | DQ | GPIO 4, physical pin 7 |
| orange | GND | physical pin 9 |
| blue | VDD | **3.3 V**, physical pin 1 |
| white/blue | GND | same GND |

Leave the green and brown pairs open at both ends. Do not put anything spare on DQ.

### 5.1 Cable category barely matters; capacitance does

**CAT6 over CAT5e buys close to nothing here.** CAT6's advantages — tighter twist, a spline,
23 AWG instead of 24, controlled NEXT — are all specified in the 100–250 MHz domain. Standard-speed
1-Wire runs at roughly 15 kbps. Mutual capacitance is the parameter that matters and the two
categories sit within a few percent of each other, near 50 pF/m. Use whichever is already on the
shelf, solid core rather than stranded.

Capacitance matters because it sets the rising edge, and the rising edge is what the failure
actually is. In a read slot the master releases the line and samples about 15 µs in, so after its
own low pulse there is roughly 9 µs for the line to climb past the DS18B20's `0.7 × VDD`
threshold, about 1.2 time constants. Take a 30 m trunk at ~50 pF/m, so about 1.5 nF, plus a couple
of hundred pF of sensor pin capacitance:

| Pull-up | τ = RC | 1.2τ | Verdict |
|---|---|---|---|
| 4.7 kΩ | ~8 µs | ~9.6 µs | misses the sample point |
| 2.2 kΩ | ~3.7 µs | ~4.5 µs | passes with margin |
| DS2482 active | driven, sub-µs | — | not a limitation |

That is the whole story of a bus that worked at four probes on short leads and died when cable was
added. Scale the numbers to the real run length; the shape does not change.

**Shielded cable is a genuine tradeoff, not an upgrade.** It rejects pickup, which matters with an
inverter-driven Chiltrix compressor and contactors in the same room, but conductor-to-shield
capacitance adds to the DQ load and pushes the table above in the wrong direction. Start with plain
UTP. Reach for shielded only if the symptom is intermittent CRC errors rather than a dead bus, and
stiffen the pull-up if you do. Ground the shield at the master end only.

**Conductor gauge is not a variable here; twist is.** The run from the Pi to the first block is
18 AWG solid, which is fine and marginally better than 24 AWG on resistance, a quantity that was
already irrelevant at 12 mA. Heavier copper does not load DQ. What untwisted cable costs is the
controlled loop area between DQ and its return, which is what cancels magnetic pickup from
contactors, pumps and the inverter compressor. Parallel-conductor cable such as 18/3 or 18/5
thermostat wire often measures *lower* mutual capacitance than CAT5e, because the conductors are
not held tightly together, so it trades noise immunity for RC headroom rather than being worse
outright.

Keep it. Mixing 18 AWG for the first leg with twisted pair further out is fine: at these edge rates
a change of cable type is a weak partial reflection, while an open stub is a total one. The stubs
are what matter. If the cable carries spare conductors, leave them open — never parallel them onto
DQ.

### 5.3 Measure the bus instead of estimating it

The RC table above assumes a run length. The real number takes a minute with a multimeter in
capacitance mode: disconnect the far end of the trunk, lift DQ at the master, and measure DQ to
GND across the installed cable with the probes still attached. That reading is the C in `τ = RC`,
so it says directly whether the fitted pull-up clears the roughly 9 µs the master allows before it
samples.

| Measured DQ-GND | 4.7 kΩ, 1.2τ | 2.2 kΩ, 1.2τ |
|---|---|---|
| 500 pF | 2.8 µs | 1.3 µs |
| 1 nF | 5.6 µs | 2.6 µs |
| 1.5 nF | 8.5 µs | 4.0 µs |
| 3 nF | 17 µs | 7.9 µs |

Anything approaching 9 µs is the diagnosis, and the row it lands on says whether a resistor swap
is sufficient or the DS2482's driven edge is required.

### 5.2 The wiring, end to end

```
MASTER END                                    ONE CABLE, CHAINED BLOCK TO BLOCK
──────────                                    ────────────────────────────────

  3.3 V ──────┬──────────────────────────────────────────────►  VDD  (blue)
              │
          [ 2.2 kΩ ]   one pull-up, master end only
              │
  GPIO 4 ─────┴──────────────────────────────────────────────►  DQ   (white/orange)
  or DS2482 IO
                                                                GND  (orange)
  GND ─────────────────────────────────────────────────────────►     + white/blue


                    ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
   master ═════════►│ BLOCK 1 │═►│ BLOCK 2 │═►│ BLOCK 3 │═►│ BLOCK 4 │  trunk ends
                    │  tees   │  │  tank   │  │ loop A  │  │ loop B  │  here, no
                    └─┬─────┬─┘  └─┬─────┬─┘  └─┬─────┬─┘  └─┬─────┬─┘  loop back
                      │     │      │     │      │     │      │     │
                     IN    OUT    UBT   LBT   A_SUP A_RET  B_SUP B_RET
                      └── short trimmed stubs, one probe each ──┘


   INSIDE ONE BLOCK   three 4-way lever connectors, one per conductor

     DQ   [ trunk in | trunk out | probe 1 | probe 2 ]
     VDD  [ trunk in | trunk out | probe 1 | probe 2 ]──┐
     GND  [ trunk in | trunk out | probe 1 | probe 2 ]──┴─ 100 nF across VDD-GND
```

Nothing branches at the master, the trunk terminates at block 4, and every probe lead is trimmed
to reach only its own block.

## 6. Pull-up, and the mitigation that needs no new cable

One pull-up for the whole bus, at the master end, from DQ to 3.3 V. Never one per sensor. For
eight probes on a longer run, drop 4.7 kΩ to **2.2 kΩ**. The DS18B20 sinks 4 mA at 0.4 V, so
3.3 V / 2.2 kΩ = 1.5 mA is comfortable and even 1.5 kΩ stays in spec. This is the cheapest thing
to try and it changes no wiring.

If re-running the trunk is impractical, keep the star and fit a **100 Ω series resistor in each
branch's DQ line at the hub**. It damps the reflection returning off that branch. This is the
standard mitigation from Maxim AN148, "Guidelines for Reliable Long Line 1-Wire Networks", and
it costs a handful of resistors rather than a cable pull.

### 6.1 Where the resistors go

One resistor per branch, in series with **DQ only**, at the hub end. It has to sit between the
common node and that branch's outgoing wire so it damps the reflection returning off that stub.
Fitted at the sensor end it does nothing. VDD and GND bus straight through, unbroken.

The value is chosen for mechanics rather than dissipation. Only the talking sensor's own branch
carries pull-down current, roughly 1.5 mA against a 2.2 kΩ pull-up, so 100 Ω adds about 0.15 V to
the low level the master sees against a `0.3 × VDD` input-low threshold. Power in the resistor is
about 0.2 mW. Anything from 22 Ω to 120 Ω works; 1/4 W metal film is far more than enough.

These apply to a star. A daisy chain does not want them, so settle topology first.

**One resistor on the trunk instead of four on the branches does not work.** Put it between the
incoming trunk and a commoned block and the four branches still meet at a node with nothing
between them, so a reflection arriving up one branch re-radiates into the other three unimpeded.
Damping requires the resistor to sit *between* the junction and each stub, where that stub's
reflection crosses it twice. Upstream of the junction it is on the wrong side of the problem, and
it costs about 0.14 V of low-level margin for nothing, since every pull-down now works through it.

**The idea does work at the other end.** A single 22–100 Ω in series at the *master's* DQ pin is
source-series termination: it absorbs reflections when they arrive back at the driver and softens
the driven falling edge. That is a legitimate one-resistor experiment, it takes two minutes on the
extension board, and it is free to try before committing to anything. It is weaker than per-branch
damping because it does nothing about energy bouncing between branches at the far junction, but on
a bus with only two branches — the mechanical-room trunk and the outdoor run — there is little
bouncing to do, and it may be enough on its own.

### 6.2 A build that survives a utility room

Put the resistors on a small FR4 board in a DIN enclosure on the same rail as the Pi's
Phoenix Contact carrier. The rules that matter are mechanical, not electrical.

- **Pluggable terminal blocks, one 3-pole per branch** (DQ / VDD / GND). Pluggable means a probe
  can be lifted during a bisect without disturbing the other seven.
- **No mid-air solder joints and no wire nuts.** Every conductor lands in a screw or spring
  terminal, and the board is mechanically fixed rather than hanging on its own wiring.
- **Ferrules on every stranded conductor** entering a screw terminal.
- **Strain relief at the enclosure entry.** A tugged cable is the most common failure in a
  mechanical room, well ahead of any component.
- **Label each branch with its probe name** — IN, OUT, UBT, LBT, LOOPA_SUP and so on — matching
  the convention in `docs/PhoenixContact-BC-RPI-label.docx`.

The commercial version of this board is a 1-Wire hub with a port per probe, which implements the
same per-branch damping and gives plug-in RJ45 ports. It costs more and needs no building.

## 7. Moving to a DS2482 hardware bridge

The Pi's `w1-gpio` overlay bit-bangs the protocol in software. It has no active pull-up, no
slew-rate control, and its timing jitters whenever the kernel services an interrupt. The DS2482
generates 1-Wire timing in hardware and drives an active pull-up, which is what a long
eight-probe run in a mechanical room wants.

Fitting it first, ahead of §4–§6, is defensible and is probably the right call for an eight-probe
run. It is the case the part exists for, it buys one round of downtime instead of three, and once
it is in the master stops being a variable in any future diagnosis. Two things it does not fix.
**An active pull-up shortens the rising edge on a capacitively loaded line; it does not cancel the
reflections a star topology sends back off eight open stubs.** And no master survives a probe with
DQ and VDD swapped. The §3 bisect is therefore not optional whichever master is fitted, and since
it needs no parts it can run while the bridge ships.

The DS2482-100 is the safe choice. The DS2484 adds adjustable 1-Wire timing and weak-pull-up
resistance in hardware, which would help on a marginal line, but the stock Linux driver exposes
only the configuration register — `active_pullup`, and `extra_config` for the APU/PPM/SPU/1WS
bits — so that tuning is out of reach without driver work.

### 7.1 What is already true on this Pi

| Fact | Value |
|---|---|
| Kernel driver | `ds2482.ko.xz` present in `6.18.34+rpt-rpi-v8` |
| Driver binds | `i2c:ds2482` and `i2c:ds2484` |
| `active_pullup` module parameter | defaults to `1` (enabled), which is what we want |
| Device-tree overlay | **none ships** — only `w1-gpio*.dtbo`, so instantiate over sysfs |
| I²C on the header | **currently off** (`dtparam=i2c_arm=off`, line 6) |
| Live config file | `/boot/firmware/config.txt` (`/boot/config.txt` is a "do not edit" stub) |
| `i2c-tools` | not installed |

`/dev/i2c-20` and `/dev/i2c-21` already exist. Those are the HDMI DDC buses, not the header. The
header bus appears as `/dev/i2c-1` once `i2c_arm` is on.

### 7.2 Hardware

A DS2482-100 breakout, or a DS2484; the same driver binds both. Tie AD0 and AD1 to GND for
address `0x18` (the pair selects `0x18`–`0x1B`).

**Mount the bridge at the Pi.** I²C is a short-range bus and must not carry the mechanical-room
run. The long cable belongs on the 1-Wire side, which is the whole reason for fitting the part.

| DS2482 pin | Goes to |
|---|---|
| VDD | 3.3 V, physical pin 1 |
| GND | physical pin 9 |
| SDA | GPIO 2, physical pin 3 |
| SCL | GPIO 3, physical pin 5 |
| IO (1-Wire) | trunk DQ |

Remove the discrete 4.7 kΩ pull-up. The DS2482 supplies its own weak pull-up plus the active
pull-up, and an external resistor fights it. The Pi already has 1.8 kΩ pull-ups on GPIO 2 and 3;
if the breakout carries its own I²C pull-ups as well, one extra board in parallel is tolerable.

GPIO 2 and 3 are free on this Pi. `pivac.GPIO` watches BCM 17, 27, 22, 5, 6, 12 and 25, and
`raspi-gpio get 2,3` reports both as unclaimed inputs, so enabling I²C displaces nothing.

**Match the DQ rail to the sensors' VDD.** The DS18B20's absolute-maximum DQ rating is VDD + 0.3 V,
so a master driving DQ to 5 V into probes powered from 3.3 V damages them. Check which rail a
breakout powers the DS2482 from before wiring it in, since some Pi 1-Wire boards also carry a
separate 5 V pin that is auxiliary network power rather than the data line.

Worth knowing: the bridge is what makes 5 V reachable at all. GPIO 4 is not 5 V tolerant, so
`w1-gpio` pins the bus at 3.3 V. With the DS2482 the Pi only ever sees I²C, so the 1-Wire side can
run at 5 V, which is the native 1-Wire voltage and buys noise margin on a long run. Moving there
means lifting the probes' VDD to 5 V at the same time. Do not mix the two rails.

### 7.3 Sourcing

| Option | Notes |
|---|---|
| `DS2482S-100+` from Digi-Key | SOIC-8, a few dollars, US stock. Mount on a SOIC-8 adapter alongside the §6.2 resistor board so one enclosure carries both. Needs hand-soldering. |
| AB Electronics **1 Wire Pi Plus** | DS2482-100 Pi HAT, ESD protection on the 1-Wire port, four I²C addresses, RJ-12 out, 5 V aux input. UK, ships worldwide. Check clearance inside the DIN carrier before committing to a HAT. |
| Sheepwalk Electronics **RPI3** | DS2482-100 Pi adapter with screw terminals and RJ45, address-jumper selectable. Purpose-built for this. UK, small vendor. |
| 7Semi / Artekit breakouts | Plain DS2482-100 breakouts, no Pi form factor. |

Fit ESD protection on the 1-Wire port if the board does not carry it. A long run into a mechanical
room is an antenna, and the DS2482 is the only thing between it and the Pi.

### 7.3 Enable I²C and retire the bit-banged master

Edit `/boot/firmware/config.txt`: set line 6 to `dtparam=i2c_arm=on`, and comment out
`dtoverlay=w1-gpio` under `[all]` at line 52. Leaving both in place creates two w1 masters and
makes it ambiguous which one owns a sensor. Then reboot.

```bash
sudo apt install -y i2c-tools
i2cdetect -y 1          # expect a device at 0x18
```

Nothing at `0x18` means AD0/AD1 are not grounded as assumed, or the board is not on 3.3 V.

### 7.4 Instantiate the bridge

```bash
sudo modprobe ds2482
echo ds2482 0x18 | sudo tee /sys/bus/i2c/devices/i2c-1/new_device
cat /sys/bus/w1/devices/w1_bus_master1/w1_master_slave_count
ls /sys/bus/w1/devices/
```

`w1_bus_master1` reappears backed by the DS2482, and the `28-*` device names are unchanged.

### 7.5 Make it survive a reboot

Load the module at boot:

```bash
echo ds2482 | sudo tee /etc/modules-load.d/ds2482.conf
```

The `new_device` write does not persist, so add `scripts/systemd/ds2482-init.service`:

```ini
[Unit]
Description=Instantiate the DS2482 1-Wire master on I2C
After=sysinit.target
Before=pivac-1wire.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'test -e /sys/bus/w1/devices/w1_bus_master1 || echo ds2482 0x18 > /sys/bus/i2c/devices/i2c-1/new_device'

[Install]
WantedBy=multi-user.target
```

```bash
sudo cp ~/github/pivac/scripts/systemd/ds2482-init.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now ds2482-init
```

Start ordering is a convenience rather than a requirement. `pivac.OneWireTherm` re-scans the bus
at the top of every cycle, so a master that appears late self-heals within one daemon cycle.

### 7.6 What does not change

pivac needs no code change and `/etc/pivac/config.yml` needs no edit. `w1thermsensor` reads
`/sys/bus/w1/devices/28-*`, the ROM-derived names are properties of the chips, and the PR #122
calibration offsets key off those same names.

### 7.7 Rollback

Uncomment `dtoverlay=w1-gpio`, move the trunk DQ back to GPIO 4, refit the pull-up to 3.3 V, and
reboot. `dtparam=i2c_arm=on` and the module-load file are harmless if left in place.

## 8. Order of operations

1. Bisect the bus one probe at a time, starting with PA1A, and bench-check each probe's pinout.
2. Drop the pull-up to 2.2 kΩ.
3. Re-cable as a daisy chain, or fit 100 Ω series resistors per branch if the star has to stay.
4. Fit the DS2482 if the bus is still marginal at eight probes.

Each step is cheaper than the one after it, and each is independently reversible.
