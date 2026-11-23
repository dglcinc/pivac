---
paths:
  - "pivac/OneWireTherm.py"
  - "tests/test_onewire_*.py"
  - "tests/test_offset_points.py"
  - "scripts/w1-proof.sh"
  - "docs/onewire-notes.md"
  - "docs/ds18b20-*.md"
  - "docs/air-handler-probe-calibration-*.md"
---

# 1-wire DS18B20

<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
<!-- Copyright David Lewis -->

Loaded when a file under its `paths:` is read; `CLAUDE.md` says to read it first for any work on a temperature probe, its offsets, the DS2482 bus or a ΔT built from probes. Rules here; the measurements and incident history behind them are in the docs named.

### 1-wire DS18B20 (`docs/onewire-notes.md`; bus electrics `docs/ds18b20-bus-topology.md`; offsets `docs/ds18b20-PA1-5-calibration.md`)

| Name | w1 ROM | Probe | Offset (K) | Where |
|------|--------|-------|-----------|-------|
| IN | `000000c98b14` | PA4A | +0.468 | primary, before the tees |
| OUT | `0000001aa0a8` | PA4B | +0.143 | primary, after the tees |
| UBT | `000000c9e879` | PA3A | +0.348 | buffer tank, upper |
| LBT | `000000c915c1` | PA3B | +0.466 | buffer tank, lower |
| LOOPA_SUP | `000000cc0c90` | PA1A | +0.653 | loop A (kids, master) |
| LOOPA_RET | `0000001a9154` | PA2B | +0.171 | loop A |
| LOOPB_SUP | `0000001ac0a9` | PA2A | −0.062 | loop B (family, kitchen, great room) |
| LOOPB_RET | `000000c99b56` | PA1B | +0.474 | loop B |

- All eight publish under `environment.inside.hvac.*` in Kelvin at `rounding: 2`. **Every temperature sensor uses `offsets:`** (`pivac.offset_at` interpolates on the reading; `offset:` is the single-point form): each loop probe carries `{45: cooling, 140: heating}`, and `IN`, `OUT`, `UBT` and `LBT` hold only their ice point, `{32: x}`. **The ten-probe batch of 2026-11 (PA9A/B to PA13A/B) reads 6.2 to 7.0 °F low, every probe; none of it goes into service without its offset.** PA9 is the utility node's water pair, PA10 the great room's, PA11 the kitchen's, PA12 the kids room's; PA5 is the master bedroom's and carries a cooling and a heating column. `LOOPA_SUP`/`LOOPB_SUP` history before 2026-08-29 is interchanged. Spares, ROMs, per-probe offsets and the NTC pairs: `docs/onewire-notes.md`, Roster and offsets in full, and `docs/air-handler-probe-calibration-2026-11-01.md`.
- **The DHW recirc probe** (`0316a015e7ff`, tag `28FFE715A0160328`) hangs off the .114 Arduino and reaches Signal K through `pivac.ArduinoSensor`, carrying PA6B's `offsets: {45: 0.348, 140: 0.254}` on the `temp` input, +0.29 K at 100 °F; its history steps up about 0.5 °F at 2026-11-01 19:49 EST. `environment.outside.temperature` does not exist; outdoor air is RedLink only.
- **Retiring or renaming a sensor needs a signalk restart**: config edit → `restart pivac-1wire` → `restart signalk`; Signal K otherwise keeps the old path frozen at its last value. The same recipe applies to relays and Emporia circuits. `environment.outside` 404s for ~80 s after a signalk restart until RedLink re-logs in.
- **DS2482 bring-up (EXT board, new Pi):** a chip that answers `i2cdetect` at `0x18` but logs `DS2482 reset failed` has VCC or ground open and is running on pull-up leakage; it passes at a 10 kHz I²C clock and fails at 50 kHz, so do not chase signal integrity — measure 3.3 V between chip pins 1 and 3 first (the bench fault was the GND rail not bridged to link position 5). Delete the `w1-gpio` line from config.txt rather than commenting it (`raspi-config` and a cloud-init `runcmd` both re-enable it) and confirm no `onewire` node in the device tree before reading any result. `ds2482-init.service` instantiates the master; the procedure is §8 of `docs/ds18b20-bus-topology.md`.
- **Bus health:** the DS2482 supplies the pull-up; no external resistor. **The EXT board hangs vertically below the Pi, solder side out, so the H plugs read GND · DATA · VCC left to right from the front**; that is the socket's V/D/G pin order seen from behind, and the label says so. **The trunk is CAT6 since the evening of 2026-09-07**, paired per rule 4 of `docs/ds18b20-bus-topology.md` (DATA with one GND, VCC with the other, spare pairs open at both ends), which replaced the flaky 22 AWG lever-connector pigtail. A swapped conductor at one end read on the DS2482 as DATA held low with phantom `Family 40` devices, then as an open once disturbed; eight probes with clean CRCs on every sweep is the proof it is right. Plug order at H1 is VCC · DATA · GND; with VCC and GND reversed the bus reads empty (line high, no presence, no short) and neither the probes nor the board were damaged by several minutes of it. **Read the chip's own status to split open from short from presence:** unbind the driver (`echo 1-0018 > /sys/bus/i2c/drivers/ds2482/unbind`), `i2cset -y 1 0x18 0xF0`, then `i2cset -y 1 0x18 0xB4; i2cget -y 1 0x18` and decode bit 1 = presence, bit 2 = short, bit 3 = line level; rebind afterwards. Line high with no presence is an open trunk or dead probes; presence with a count of 0 is marginal timing. `max_slave_count 64 reached` means marginal bit timing (cable capacitance against the pull-up), never 64 sensors. `presence=1 roms=0` means devices alive and timing marginal; `presence=0` means power or a broken lead. Bisect by adding probes one at a time while watching `w1_master_slave_count`. The Arduino bench rig needs 5 V on both supply and pull-up. pivac logs only `bus now has 0 sensor(s)`; the freshness alerts are what report a dead bus.
- **Printed tags are unreliable; the bus is authoritative.** Identify a probe by unplugging it and watching `/sys/bus/w1/devices/`. The label is the full 8-byte ROM; the w1 name reverses the six serial bytes.
- **Mount a loop pair for ΔT, not for accuracy.** Copper at the tees, never PEX; probe axial and greased, 2–3 in thermal lead-in, ~10 pipe diameters of insulation each side, supply probe *after* the zone pump, and **strain relief an inch or two behind each probe**. Mount both probes of a pair identically so residual conduction error is common-mode and cancels out of the ΔT — an offset cannot remove a mounting bias.
- **A decoupled probe reports fresh, plausible, wrong data forever.** Detect it by swing (coupled 7–14 °F over a cycling window, decoupled 1–2) and pairwise correlation (a loop's own pair reading −0.02 is impossible; two decoupled probes correlate with each other). Cross-connected probes show the same way, so group by measured correlation, never by label, and check the sign of every pair after any install: OUT runs 5–6 °F above IN in cooling. 85.0 °C exactly, the rails, or CRC errors are chip faults; anything plausible is mounting. Strain-relieve the cable an inch behind the probe.
- **An idle loop's ΔT is fiction**: the dead legs off the tees hold a plausible positive ΔT with the pump off, and loop A's supply tracks `IN` within 0.2 °F in every state. Gate every loop ΔT on a switch, never a probe (`pivac.LoopDelta` gates the primary on `HPCALL` or `DHWX` and each secondary on `HPCALL` narrowed to its zones: any heat or cool call on `zones`, a heat call only on `heat_zones`, which are the kitchen and great room on loop B because they cool on their own Bosch units; RedLink zone state lags the relay by ~48 s, and its fan-only state of 0.5 opens no gate). The first minute of a run is not a measurement either. The master bedroom node's coil pairs are gated the same way, on `HPCALL` narrowed to `MASTER_BR`: its air pair holds a 4 to 5 °F room-to-duct difference with the fan off. Never aggregate a short-cycling signal into buckets near its own period.
- **Module behaviour:** the bus is rescanned every cycle (boot race and dropouts self-heal without a restart), a failing sensor is skipped without silencing the rest, and `SensorNotReadyError` is transient. `rounding: 2` is a precision setting (0.018 °F); never put it back to 0, which quantized every ΔT to 1.8 °F steps. RedLink had the matching defect and truncated (up to 1.8 °F cold, always downward) before 2026-08-18. Neither fix is retroactive.

## Reference docs

| Doc | Covers |
|-----|--------|
| `docs/onewire-notes.md` | DS18B20 roster history, bus fault diagnosis, decoupled and cross-connected probes, dead-leg ΔT, precision fixes, module behaviour |
| `docs/ds18b20-bus-topology.md` | 1-wire bus build procedure, EXT board, DS2482 migration, electrical background |
| `docs/ds18b20-PA1-5-calibration.md` | Probe offsets, pair corrections, reproducibility |
