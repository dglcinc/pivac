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

**Check VDD is on 3.3 V.** The DS18B20's input-high threshold is 0.7 × VDD. A probe powered from
the Pi's 5 V rail needs 3.5 V to register a logic high, while a bus pulled up to 3.3 V never
gets there. It often works and degrades as loading and cable length grow, which matches a bus
that was clean at four devices and collapsed at eight. Note `docs/ds18b20-provisioning.md`
specifies 5 V because that rig is an Arduino; copying it to the Pi is out of spec.

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

## 5. Cable and pairing

Use CAT5/CAT6 or shielded 3-conductor. With CAT5 the rule people get wrong is that **DQ and GND
must share one twisted pair**, so the data line has its return conductor adjacent. Pairing DQ
with VDD couples them and loads the data line with the pair's mutual capacitance.

| CAT5 conductor | Signal | Pi header (while on `w1-gpio`) |
|---|---|---|
| Pair 1, solid | DQ | GPIO 4, physical pin 7 |
| Pair 1, stripe | GND | physical pin 9 |
| Pair 2, solid | VDD | **3.3 V**, physical pin 1 |
| Pair 2, stripe | GND | same GND |

Leave the remaining pairs open. On shielded cable, ground the shield at the Pi end only.

## 6. Pull-up, and the mitigation that needs no new cable

One pull-up for the whole bus, at the master end, from DQ to 3.3 V. Never one per sensor. For
eight probes on a longer run, drop 4.7 kΩ to **2.2 kΩ**. The DS18B20 sinks 4 mA at 0.4 V, so
3.3 V / 2.2 kΩ = 1.5 mA is comfortable and even 1.5 kΩ stays in spec. This is the cheapest thing
to try and it changes no wiring.

If re-running the trunk is impractical, keep the star and fit a **100 Ω series resistor in each
branch's DQ line at the hub**. It damps the reflection returning off that branch. This is the
standard mitigation from Maxim AN148, "Guidelines for Reliable Long Line 1-Wire Networks", and
it costs a handful of resistors rather than a cable pull.

## 7. Moving to a DS2482 hardware bridge

The Pi's `w1-gpio` overlay bit-bangs the protocol in software. It has no active pull-up, no
slew-rate control, and its timing jitters whenever the kernel services an interrupt. The DS2482
generates 1-Wire timing in hardware and drives an active pull-up, which is what a long
eight-probe run in a mechanical room wants.

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
2. Confirm VDD is on 3.3 V.
3. Drop the pull-up to 2.2 kΩ.
4. Re-cable as a daisy chain, or fit 100 Ω series resistors per branch if the star has to stay.
5. Fit the DS2482 if the bus is still marginal at eight probes.

Each step is cheaper than the one after it, and each is independently reversible.
