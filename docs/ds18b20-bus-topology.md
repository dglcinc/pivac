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

### 4.3 The first branch point is on the accessory board

The 1-wire bus leaves the **RPI-BC EXT-PCB HBUS SET** (Mouser 651-2202995) on **two** 3-position
plugs, both 18 AWG solid: the mechanical-room trunk on one, the outdoor ambient run on the other.
The bus therefore forks inside the enclosure, at the board, before either cable reaches a breakout.
The pull-up, plus the DS2482 if it is fitted, stay on that board upstream of both plugs.

That fork is what makes §6.1's per-branch damping cheap here. The junction is already accessible
with one plug per branch, so a 100 Ω can sit between the common node and each outgoing cable
without opening anything downstream.

**The mechanical-room side is already a chain, so §4's re-cabling does not apply to it.** Three
headers sit along the run, each built from Phoenix Contact **ST 1,5/S QUATTRO** feed-through
blocks, one commoned 4-terminal block per conductor. The trunk enters a header, the local probes
land on the spare terminals, and the trunk leaves for the next one. That is exactly §4.1's
distributed-block pattern, which is why the 2026-08-24 diagnosis went to the pull-up rather than
to topology. The first header carries two of the loop probes and the last carries the other two;
the middle one carries the original four and uses two blocks per conductor to find the terminals.

The one departure is a **10 ft stub** from the middle header out to the two tank probes, rather
than the trunk routing through them. It costs the capacitance of its length, about 340 pF. Since
§5.3 establishes that RC rather than reflection is what binds this bus, that capacitance counts
the same wherever it sits, so the stub is a length problem and not a topology one.

Terminal budget follows from the block size. A quattro gives four terminals: the first header
spends them on trunk-in, trunk-out and two probes, and the last on trunk-in and three probes.
Both are full, so adding a probe at either point needs a second block and a bridge.

**The outdoor run is almost certainly the longest cable on the bus.** Length is capacitance, so
that one branch probably dominates the RC budget in §5.1 on its own. §5.3 measures the two plugs
separately, which is what shows whether it does.

**An outdoor cable with no probe on the end is pure cost.** The AMB probe was repurposed as LBT,
so until §4.4 restores a sensor there, that branch contributes its full capacitance and an
open-ended reflection while returning no data. Unplugging it at the board is free RC headroom and
removes one of the two branches outright.

### 4.4 Restoring the outdoor sensor without re-breaking the bus

There is one spare bench-calibrated pair for this: PA3 went to the tank, PA1 and PA2 to the loops,
and PA4 to IN and OUT, leaving **PA5** with its ice-point offsets already recorded in
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
its per-branch 100 Ω resistors belong at that block. The pair at the accessory board damps the
board-level fork between the two plugs, which is a different junction. Those sit upstream of the
breakout's own eight branches and do nothing for them, so the two sets of resistors address
separate problems and neither substitutes for the other.

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

**Conductor gauge is not the variable; the conductor count is.** The run from the Pi to the first
block is 18 AWG solid, which is fine — resistance was already irrelevant at 12 mA, and heavier
copper barely moves DQ's capacitance. What matters is how many grounded conductors sit beside the
data line. A twisted pair gives DQ one return. Jacketed 3-conductor thermostat cable puts it
between VDD and GND, **both of which are AC ground**, so it sees roughly twice as much; a
5-conductor run can be worse again.

**Measured here rather than estimated, this chain runs 112 pF/m** on 20 AWG 3-conductor and
18 AWG 5-conductor, against ~50 pF/m for CAT5e. So parallel-conductor thermostat wire is not the
RC bargain its loose spacing suggests: wider spacing does lower the capacitance between any given
pair, and sandwiching the data line between two grounded conductors more than takes it back. What
untwisted cable does still cost is the controlled loop area between DQ and its return, which is
what cancels magnetic pickup from contactors, pumps and the inverter compressor.

The corollary is to leave spare conductors **floating at both ends**. A grounded spare next to DQ
adds capacitance and returns nothing.

Keep it. Mixing 18 AWG for the first leg with twisted pair further out is fine: at these edge rates
a change of cable type is a weak partial reflection, while an open stub is a total one. The stubs
are what matter. If the cable carries spare conductors, leave them open — never parallel them onto
DQ.

### 5.3 Measure the bus instead of estimating it

The RC table above assumes a run length. The real number takes a few minutes with a multimeter in
capacitance mode.

**Only the master end comes apart.** Unplug both 3-position connectors at the accessory board and
leave everything downstream exactly as installed: every probe attached, every branch connected,
nothing touched at any far end. Disconnecting a far end would remove the capacitance being
measured.

**Measure the two plugs separately and add the readings.** The branches are in parallel from the
master's point of view and parallel capacitances sum, so the total is the same either way, and
measuring them apart also says how much of the budget the outdoor run accounts for on its own.
Combining them physically is awkward with two connectors and buys nothing.

On each free cable in turn, tie **VDD to GND** and measure from **DQ** to that pair. The supply
holds VDD at AC ground in normal operation, so the DQ-to-VDD coupling is part of what the pull-up
charges; leave VDD floating and the reading comes in low. Null the test leads with the meter's REL
or ZERO function first, since lead capacitance runs 30–100 pF against a reading expected in the
hundreds of pF to low nF.

```
STEP 1 — unplug both connectors at the accessory board

  EXT-PCB HBUS SET                      INSTALLED CABLES — untouched
  ────────────────                      ────────────────────────────

    3.3 V ──[ pull-up ]──┐                VDD ○ ┐
                         ├── GPIO 4       DQ  ○ ├─ mechanical-room trunk:
    GND ─────────────────┘                GND ○ ┘  breakout, all probes

    pull-up and GPIO stay on               VDD ○ ┐
    this side, out of the reading          DQ  ○ ├─ outdoor run
                                           GND ○ ┘

STEP 2 — on each cable in turn, tie VDD to GND, meter from DQ to that pair

                    DQ  ○──────────────────┐
                                        ┌──┴──────────────┐
                    VDD ○──┬──────────  │  DMM            │
                           │            │  capacitance    │
                    GND ○──┴──────────  │  (leads REL'd)  │
                                        └─────────────────┘

STEP 3 — add the two readings
```

The sum is the C in `τ = RC`, and the master allows roughly 9 µs for the line to rise before it
samples:

| Measured DQ-GND | 4.7 kΩ, 1.2τ | 2.2 kΩ, 1.2τ |
|---|---|---|
| 500 pF | 2.8 µs | 1.3 µs |
| 1 nF | 5.6 µs | 2.6 µs |
| 1.5 nF | 8.5 µs | 4.0 µs |
| 3 nF | 17 µs | 7.9 µs |

Anything approaching 9 µs is the diagnosis, and the row it lands on says whether a resistor swap
is sufficient or the DS2482's driven edge is required.

**Two budgets, and the difference decides everything here.** The 9 µs above is the *guaranteed*
worst case: the master holds low about 6 µs in a write slot, and the DS18B20 is specified to
sample anywhere from 15 to 60 µs after the falling edge, so only the 15 µs end is promised. Real
parts sample near 30 µs, which puts the working budget closer to **24 µs**. Design to 9 µs; expect
failure near 24.

**Measured on this bus, 2026-08-24.** Main loop with its four probes, **1.75 nF**. Outdoor run,
bare cable with no probe fitted, **1.95 nF**. Time to reach `0.7 × VDD`, which is 1.2τ:

| Bus | C | 4.7 kΩ | 2.2 kΩ |
|---|---|---|---|
| Main loop, 4 probes | 1.75 nF | 9.9 µs | 4.6 µs |
| Main loop, 8 probes | ~2.35 nF | 13.3 µs | 6.2 µs |
| Main 4 + outdoor — the bus that ran until 6 Aug | 3.70 nF | **20.9 µs** | 9.8 µs |
| Main 8 + outdoor — the bus that collapsed 22 Aug | ~4.30 nF | **24.3 µs** | 11.4 µs |

**The collapse lands exactly where the real sampling point predicts.** The configuration that
worked for months sat at 20.9 µs and the one that died sat at 24.3 µs, on either side of ~24. That
also explains why the failure was total rather than gradual: crossing the threshold corrupts every
bit of the ROM search at once, which is the §1 phantom-device signature.

This supersedes §2's reflection argument as the explanation for *this* bus. At 1-wire edge rates a
round trip down even 40 m settles in a few hundred nanoseconds, far inside the sample point, while
the RC arithmetic predicts the observed failure to within a few percent. Star topology still costs
capacitance through captive-lead length, so §4 stands on that ground rather than on echoes.

**2.2 kΩ carries the whole bus, outdoor included**, at 11.4 µs against the ~24 µs where it
actually broke — roughly 2× margin, where 4.7 kΩ gave it 1.15×. Only the main-loop-only cases
clear the 9 µs guaranteed window, so a fully populated bus still relies on real-part behaviour.
That is the argument for §4.4's separate DS2482 bus, which is now a robustness choice rather than
an arithmetic requirement.

A probe adds about 25 pF, so fitting one changes none of this. Cable length is the whole story, and
the inventory closes against the measurement exactly:

| Segment | Length |
|---|---|
| Pi → header 1, 18 AWG 5-conductor | 15 ft |
| header 1 → header 2 | 1.5 ft |
| header 2 → header 3 | 3 ft |
| header 2 → tank probes, stub | 10 ft |
| eight probe leads, untrimmed | 16 ft |
| **total conductor** | **45.5 ft / 13.9 m** |

13.9 m at 112 pF/m is 1.55 nF; eight DS18B20 pins at 25 pF each add 200 pF; the sum is 1.75 nF,
which is what the meter read. **Note what dominates: the probe leads are 16 ft of the 45.5.**

**Confirmed live 2026-08-24: eight probes on 2.2 kΩ enumerate and hold.** All eight appear in
`w1_master_slave_count`, publish through `pivac.OneWireTherm`, and both loop pairs read the right
sign. The predicted 6.2 µs sits inside even the 9 µs guaranteed window, against the 24.3 µs that
took the bus down at 4.7 kΩ.

**Trimming the probe leads is the cheapest headroom left.** At 16 ft they are 35% of the conductor.
Cut to roughly 6 in each, the bus sheds 12 ft — about 410 pF at 112 pF/m — and drops to 1.34 nF.
The outdoor branch's 1.95 nF then fits alongside it at 3.29 nF, inside the 3.4 nF that 2.2 kΩ
guarantees. That is what buys the outdoor sensor back onto this bus without a second master.

**Practical length on cable like this**, designing to the guaranteed 9 µs window at 112 pF/m:

| Pull-up | C ceiling | Total conductor |
|---|---|---|
| 4.7 kΩ | 1.6 nF | ~14 m / 47 ft |
| 2.2 kΩ | 3.4 nF | ~30 m / 100 ft |
| 1.5 kΩ | 5.0 nF | ~45 m / 146 ft |
| DS2482 | not binding | 200–300 m |

At 45.5 ft this bus sits at 45% of the 2.2 kΩ budget, which is the 6.2 µs against 9 µs above. It
was over the 4.7 kΩ row before a single loop probe was added.

1.5 kΩ is the floor for a passive pull-up on 3.3 V: 2.2 mA stays inside the DS18B20's 4 mA sink,
and going lower eats low-level margin. Past that the DS2482's driven edge is the only way up.
"Total conductor" counts every branch and every probe lead, which is why a 60 ft chain can already
sit at the limit.

### 5.4 Bus health is measurable, not just "it enumerates"

Three signals, all free, all in sysfs:

**CRC failures.** Every `w1_slave` read ends `crc=XX YES` or `NO`. Read each sensor repeatedly and
count the `NO`s. `w1_therm` retries internally, so one reaching sysfs means several consecutive
failures — a `NO` rate above zero is a bus with no margin.

**Search stability.** `w1_master_slave_count` polled over time must never dip below the expected
count. This is the sharpest indicator available, because the ROM search is the most timing-critical
operation on the bus and the one that failed on 22 August. A bus that reads fine but searches
unreliably is a bus about to collapse.

**`ext_power`.** Each probe reports `1` for externally powered, `0` for parasitic. A `0` on a bus
wired for external power means VDD is not reaching that probe.

```bash
ok=0; bad=0; miss=0
for i in $(seq 1 40); do
  [ "$(cat /sys/bus/w1/devices/w1_bus_master1/w1_master_slave_count)" -ne 8 ] && miss=$((miss+1))
  for d in /sys/bus/w1/devices/28-*; do
    case "$(head -1 $d/w1_slave)" in *YES*) ok=$((ok+1));; *) bad=$((bad+1));; esac
  done
  sleep 4
done
echo "crc_ok=$ok crc_fail=$bad sweeps_not_8=$miss"
grep . /sys/bus/w1/devices/28-*/ext_power
```

**Measured 2026-08-24, immediately after the pull-up change.** Forty sweeps over about seven
minutes: **320 reads, 0 CRC failures, 0 sweeps returning other than eight devices, all eight
reporting `ext_power=1` at 12-bit resolution.** Forty clean ROM searches out of forty is the
evidence that the 6.2 µs figure is real margin rather than luck; on 320 clean reads the error rate
sits under roughly 1% at 95% confidence.

### 5.5 Planned end state

Three changes take this bus from 1.75 nF to roughly 670 pF. Two of them cost nothing but time.

| Change | Now | After | Saves |
|---|---|---|---|
| Trim probe leads, 2 ft → 6 in | 546 pF | 137 pF | **409 pF** |
| Take ~7.5 ft of slack out of the trunk and tank runs | — | — | **~240 pF** |
| Trunk and tank to CAT5e/CAT6, ~22 ft at 50 pF/m | 1007 pF | 335 pF | **~430 pF** |
| Eight DS18B20 pins | 200 pF | 200 pF | 0 |
| **Total** | **1753 pF** | **~670 pF** | **~62%** |

At 2.2 kΩ that is **1.85 µs against the 9 µs guaranteed budget, about 5× margin**, up from 6.2 µs
today. Redo the outdoor run the same way and it falls from 1.95 nF to roughly 870 pF, so the whole
bus with outdoor restored lands near 1.57 nF and stays inside the guaranteed window with room for
several more probes. That is the version of this bus that stops needing attention.

**Order by payoff against effort.** Trimming and de-slacking together take 1753 pF to about
1100 pF, a 37 % cut with no cable bought. The re-pull adds the remaining 25 %.

**Why CAT cable wins here has nothing to do with its category.** CAT5e and CAT6 are both specified
to 100 Ω with a velocity factor near 0.67, and `C = 1/(Z₀·v)` forces both to ~50 pF/m; choosing
between them is not worth a moment's thought. The gain is entirely that §5's pairing gives DQ
**one** grounded neighbour where 3-conductor thermostat cable gives it two. That is the same
mechanism §5.1 measures as 112 pF/m against 50.

**Two things to get right on the re-pull.** DQ and GND share one twisted pair and VDD sits on a
different pair, per §5; pairing DQ with VDD couples the data line to the supply and discards the
benefit. And leave the spare pairs open at both ends, never grounded and never paralleled onto DQ,
since a grounded conductor beside DQ is precisely what makes the present cable expensive.

**Terminal budget, which the second GND conductor threatens.** Both GND conductors are one net and
merge at the terminals, so the run still lands as three connections. But a pass-through header
would otherwise spend all four of its GND quattro terminals on trunk-in and trunk-out, leaving none
for probes. Land both GND conductors of a run in a **single** terminal and the
one-block-per-conductor layout in §4.3 keeps working unchanged. Two 23 AWG is 0.52 mm² against the
ST 1,5's 1.5 mm² rating, so the cross-section is never the constraint.

How they land depends on which cable is pulled. **Stranded takes a twin ferrule**, 2 × 0.25 mm² for
24 AWG or 2 × 0.34–0.5 mm² for 23 AWG, which crimps both conductors into one pin at a consistent
clamping force. **Solid does not** — it will not compress predictably in a crimp, and the standard
termination is bare into the clamp, which two solid conductors of this size handle without help.
Check the ferrule's insulating collar clears the terminal throat before ordering; the collar is
bulkier than the conductors and is the dimension that actually limits.

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

**Treat this as secondary on this bus.** §5.3's measurement puts the failure squarely on rise
time, and the pull-up alone restores 2× margin. Fit the resistors only if the bus is still
unreliable at eight probes after the pull-up change.

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

**The two plugs on the accessory board put a junction within reach, so per-branch damping belongs
there.** One 100 Ω in each plug's DQ line, between the common node and that plug, is the
arrangement above with two branches instead of four. The pull-up sits at the common node with
GPIO 4. The cost is the 0.14 V of low-level margin already priced, plus about 4.5 % on the rise
constant, since charging current now flows through 2.2 kΩ and 100 Ω in series. Both are noise.

```
                              ┌──[ 100 Ω ]──── plug 1 DQ ── mechanical room
                              │
  GPIO 4 ─────────────────────┤──[ 100 Ω ]──── plug 2 DQ ── outdoor run
  (or DS2482 IO)              │
                          [ 2.2 kΩ ]
                              │
                            3.3 V
```

**The single-resistor alternative is source-series termination at the driver.** One 22–100 Ω
between GPIO 4 and the common node absorbs reflections as they arrive back at the source and
softens the driven falling edge. It is weaker than per-branch damping, doing nothing about energy
bouncing between the two branches at their junction, but it leaves the rise path at the bare
pull-up value. **Put the pull-up on the cable side of it**, not the GPIO side:

```
                              ┌──── plug 1 DQ ── mechanical room
                              │
  GPIO 4 ──────[ 100 Ω ]──────┤──── plug 2 DQ ── outdoor run
  (or DS2482 IO)              │
                          [ 2.2 kΩ ]
                              │
                            3.3 V
```

That ordering matters. With the pull-up on the cable side the rise is driven straight onto the
line, so the resistor costs nothing on the slow edge, and the master's input is high-impedance so
it reads the true line voltage with no divider error. The resistor then acts only where it is
wanted: on the master's own driven falling edge, and on reflections coming home. Wire it the other
way round, pull-up on the GPIO side, and every pull-down reads through a divider while the rise
time gets worse.

Fit the per-branch pair first. It is one extra resistor and it damps the junction that actually
exists.

**Remove it if the DS2482 goes in.** That part's whole contribution is a hard-driven edge from an
active pull-up, and a series resistor in front of it works against exactly that. Start without one
and add it back only if the bus is still marginal.

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
2. Unplug the outdoor cable at the board for as long as no probe sits on its far end. It costs
   capacitance and an open-ended reflection and returns nothing.
3. Measure DQ-to-GND capacitance per §5.3 and read the verdict off the table there.
4. Drop the pull-up to 2.2 kΩ.
5. Re-cable as a daisy chain, or fit 100 Ω series resistors per branch if the star has to stay.
6. Fit the DS2482 if the bus is still marginal at eight probes.

Each step is cheaper than the one after it, and each is independently reversible.
