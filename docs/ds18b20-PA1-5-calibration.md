# DS18B20 PA1–PA5 calibration record

Ten DS18B20 stainless probes for the secondary-loop pairs, addressed, labelled, and ice-point
calibrated on the bench (David's Mac, UNO R4 WiFi over USB, `arduino-cli`). Enumeration and
calibration followed [`ds18b20-provisioning.md`](ds18b20-provisioning.md).

## Method

- Bus on D2, external 4.7 kΩ pull-up to 5 V, normal (non-parasitic) power, 12-bit resolution.
- Identified each probe by inserting it alone into ice water and watching which ROM's temperature
  moved; assigned **PA1A → PA5B in insertion order**.
- Calibration bath: circulating ice-water slush, packed with ice, stirred. Reference = Fluke
  Thermapen ONE held co-located with the bundled probes at **32.0–32.1 °F** during the logging
  window; anchor taken as **32.05 °F**.
- Offsets from a 257 s stable window (soak7): per-probe SD 0.009–0.057 °F, split-half agreement
  within ±0.03 °F, bath mean flat within ±0.02 °F for the full 5 min.
- Reproducibility: the pair A–B differences match an independent earlier stable run (soak4) to
  ~0.05 °F. Absolute per-sensor offsets reproduce to ~0.13 °F.

**Offset convention:** add the offset to the raw reading to correct it. `offset = 32.05 − mean`.
A DS18B20's absolute spec is ±0.5 °C (±0.9 °F), so the 1.4 °F spread across the ten is expected
sensor-to-sensor variation; the ~0.5 °F mean low bias is a batch characteristic.

## Ice-point offsets

| Label | ROM (printed) | w1 name | mean °F | offset °F (add) | offset K (add) |
|---|---|---|---|---|---|
| PA1A | `28900CCC000000A5` | `28-000000cc0c90` | 30.991 | +1.059 | +0.588 |
| PA1B | `28569BC9000000EF` | `28-000000c99b56` | 31.289 | +0.761 | +0.423 |
| PA2A | `28A9C01A000000D5` | `28-0000001ac0a9` | 32.382 | −0.332 | −0.184 |
| PA2B | `2854911A000000B5` | `28-0000001a9154` | 31.901 | +0.149 | +0.083 |
| PA3A | `2879E8C90000005E` | `28-000000c9e879` | 31.424 | +0.626 | +0.348 |
| PA3B | `28C115C9000000B2` | `28-000000c915c1` | 31.212 | +0.838 | +0.466 |
| PA4A | `28148BC900000088` | `28-000000c98b14` | 31.208 | +0.842 | +0.468 |
| PA4B | `28A8A01A000000F3` | `28-0000001aa0a8` | 31.792 | +0.258 | +0.143 |
| PA5A | `28286ECB00000017` | `28-000000cb6e28` | 31.474 | +0.576 | +0.320 |
| PA5B | `28DA8C1A000000DC` | `28-0000001a8cda` | 31.889 | +0.161 | +0.089 |

## Pair ΔT-zero corrections

For a pair reading ΔT = T_A − T_B, the corrected ΔT adds `(offset_A − offset_B)`. Reproducible to
~0.05 °F, so trustworthy for supply/return ΔT.

| Pair | offset_A − offset_B (°F) | (K) |
|---|---|---|
| PA1 | +0.298 | +0.166 |
| PA2 | −0.481 | −0.267 |
| PA3 | −0.212 | −0.118 |
| PA4 | +0.583 | +0.324 |
| PA5 | +0.415 | +0.231 |

## Caveats and next steps

- **Single point (ice) only.** Slope is unverified. For chilled-loop duty (~45 °F) a second bath
  point tightens absolute accuracy across the operating range; per the provisioning doc, 45 °F is
  the point that counts. DS18B20s are quite linear, so the ice offset is a good first correction.
- **Config units.** pivac stores temperatures in Kelvin (`OneWireTherm` reads `Unit.KELVIN`), so
  apply the K column if the `offsets:` map is in Kelvin; the °F column is the bench measurement.
- **Verify w1 names on the Pi.** These names were derived on the Mac by reversing the printed ROM
  serial bytes (CRC-validated). Before trusting `config.yml`, confirm each `28-…` appears under
  `/sys/bus/w1/devices/` on the Pi.
- Mount on **copper at the tees, not PEX** (provisioning doc §7 / assessment §4.2).

Raw logs and the scan sketch are archived in the session memory dir
(`ds18b20-PA-icepoint-soak7.csv`, `-soak4.csv`, `ds18b20-PA-scan.ino`).
