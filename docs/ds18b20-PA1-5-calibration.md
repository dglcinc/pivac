# DS18B20 ice-point calibration record

Fourteen DS18B20 stainless probes, addressed, labelled, and ice-point calibrated on the bench
(David's Mac, UNO R4 WiFi over USB, `arduino-cli`). Ten are the PA1–PA5 loop probes; four are
older probes recovered from earlier service.

## Method

- Bus on D2, external 4.7 kΩ pull-up to **5 V**, normal (non-parasitic) power, 12-bit resolution.
  The pull-up and the probe supply must both be 5 V: the UNO R4 runs its logic at 5 V, so a 3.3 V
  pull-up idles below the input-high threshold. The bus then answers a reset with a presence pulse
  but the ROM search — which reads individual bits in ~15 µs windows — returns nothing.
- Identified each PA probe by inserting it alone into ice water and watching which ROM's
  temperature moved; assigned **PA1A → PA5B in insertion order**.
- Calibration bath: circulating ice-water slush, packed with ice, stirred. Reference = Fluke
  Thermapen ONE held co-located with the bundled probes during the logging window.
- Offsets are the mean of a stable window: per-probe SD 0.009–0.060 °F, bath flat within ±0.02 °F.

**Offset convention:** add the offset to the raw reading to correct it. `offset = reference − mean`.
A DS18B20's absolute spec is ±0.5 °C (±0.9 °F), so the ~1.4 °F spread across a batch is expected
sensor-to-sensor variation.

## Ice-point offsets

Reference 32.00 °F for the 2026-08-29 window, 32.05 °F for 2026-08-22.

| Label | ROM (printed) | w1 name | mean °F | offset °F (add) | offset K (add) | measured |
|---|---|---|---|---|---|---|
| PA1A | `28900CCC000000A5` | `28-000000cc0c90` | 30.878 | +1.122 | +0.623 | 2026-08-29 |
| PA1B | `28569BC9000000EF` | `28-000000c99b56` | 31.195 | +0.805 | +0.447 | 2026-08-29 |
| PA2A | `28A9C01A000000D5` | `28-0000001ac0a9` | 32.278 | −0.278 | −0.154 | 2026-08-29 |
| PA2B | `2854911A000000B5` | `28-0000001a9154` | 31.862 | +0.138 | +0.077 | 2026-08-29 |
| PA3A | `2879E8C90000005E` | `28-000000c9e879` | 31.424 | +0.626 | +0.348 | 2026-08-22 |
| PA3B | `28C115C9000000B2` | `28-000000c915c1` | 31.212 | +0.838 | +0.466 | 2026-08-22 |
| PA4A | `28148BC900000088` | `28-000000c98b14` | 31.208 | +0.842 | +0.468 | 2026-08-22 |
| PA4B | `28A8A01A000000F3` | `28-0000001aa0a8` | 31.792 | +0.258 | +0.143 | 2026-08-22 |
| PA5A | `28286ECB00000017` | `28-000000cb6e28` | 31.474 | +0.576 | +0.320 | 2026-08-22 |
| PA5B | `28DA8C1A000000DC` | `28-0000001a8cda` | 31.889 | +0.161 | +0.089 | 2026-08-22 |
| CRW | `28FF040FA016039F` | `28-0316a00f04ff` | 31.818 | +0.182 | +0.101 | 2026-08-29 |
| AMB | `28FF1668A316054F` | `28-0516a36816ff` | 31.207 | +0.793 | +0.441 | 2026-08-29 |
| OUT | `28FFD865A3160552` | `28-0516a365d8ff` | 32.000 | +0.000 | +0.000 | 2026-08-29 |
| DHW recirc | `28FFE715A0160328` | `28-0316a015e7ff` | 31.440 | +0.560 | +0.311 | 2026-08-29 |

The last four are the probes that served as CRW, the outdoor ambient, and OUT before the PA batch
replaced them, plus the DHW recirc probe on the Arduino at 10.0.0.114. They carry `FF` in their
serial where the PA batch carries `000000`, which distinguishes the two families at a glance.

**`28-0516a36332ff` (the former IN) is not calibrated** — it failed to enumerate during the
2026-08-29 session while its three siblings answered.

## Pair ΔT-zero corrections

For a pair reading ΔT = T_A − T_B, the corrected ΔT adds `(offset_A − offset_B)`.

| Pair | offset_A − offset_B (°F) | (K) | measured |
|---|---|---|---|
| PA1 | +0.318 | +0.177 | 2026-08-29 |
| PA2 | −0.415 | −0.231 | 2026-08-29 |
| PA3 | −0.212 | −0.118 | 2026-08-22 |
| PA4 | +0.583 | +0.324 | 2026-08-22 |
| PA5 | +0.415 | +0.231 | 2026-08-22 |

## Reproducibility

PA1 and PA2 were measured twice, a week apart, in independently made baths. Absolute offsets agree
to −0.011…+0.063 °F (mean +0.038); the PA1 pair difference agrees to 0.020 °F.

**The PA2 pair difference agrees only to 0.066 °F**, outside the ±0.05 °F the other pairs hold, and
PA2A is also the noisiest probe in the set at SD 0.060. PA2A is one of the two probes that came off
the wall thermally decoupled, so it has been handled since its first calibration. Take a second
window on that pair before relying on its ΔT correction.

A shared bath error moves every probe together and cancels out of a pair difference, which is why
the pair numbers are the trustworthy ones and the absolute offsets inherit the reference's accuracy.

## Caveats and next steps

- **Single point (ice) only.** Slope is unverified. For chilled-loop duty (~45 °F) a second bath
  point tightens absolute accuracy across the operating range. DS18B20s are quite linear, so the
  ice offset is a good first correction.
- **Config units.** pivac stores temperatures in Kelvin (`OneWireTherm` reads `Unit.KELVIN`), so
  apply the K column if the `offsets:` map is in Kelvin; the °F column is the bench measurement.
- **The DHW recirc offset cannot be applied where that probe sits.** It reaches Signal K through
  `pivac.ArduinoSensor`, which has no `offset` support — the key exists only in `OneWireTherm`.
  Applying it means moving the probe onto the 1-wire bus or adding offset support to that module.
- **Verify w1 names on the Pi.** Confirm each `28-…` appears under `/sys/bus/w1/devices/` before
  trusting `config.yml`.
- **The printed tag is not a reliable physical identifier in this set** — one probe was found
  carrying a second probe's tag. The ROM is read from the chip, so the bus is authoritative; to tie
  a ROM to a physical probe, unplug it and watch which entry disappears.
- Mount on **copper at the tees, not PEX** (assessment §4.2).

Raw logs and the scan sketch are archived in the session memory dir
(`ds18b20-icepoint-soak-20260829.csv`, `ds18b20-PA-icepoint-soak7.csv`, `-soak4.csv`,
`ds18b20-PA-scan.ino`).
