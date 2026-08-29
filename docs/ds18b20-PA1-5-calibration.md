# DS18B20 ice-point calibration record

Fourteen DS18B20 stainless probes, addressed, labelled, and ice-point calibrated on the bench
(David's Mac, UNO R4 WiFi over USB, `arduino-cli`). Ten are the PA1–PA5 loop probes; four are
older probes recovered from earlier service.

## Two-point calibration (2026-08-29)

PA1, PA2 and the four recovered probes were measured at **two** bath points: an ice slush
referenced at 32.10 °F, and a **sous vide circulator at 100.0 °F**, both read with the Thermapen
held among the probe tips. Bath stability was 0.025 °F range over 14 minutes for the ice and
0.011 °F over 9 minutes for the circulator, so neither run is limited by drift.

`OneWireTherm` applies an offset but has no gain term, so the useful product of two points is not a
fit to install — it is the ability to state the offset **at the temperature where the probe works**.
The chilled loop runs near 45 °F, and that is the column deployed.

| Label | slope | offset °F @32 | @45 | @100 | @140 | **offset K @45 (deployed)** |
|---|---|---|---|---|---|---|
| PA1A | 0.9954 | +1.223 | +1.163 | +0.908 | +0.728 | **+0.646** |
| PA1B | 0.9955 | +0.904 | +0.845 | +0.594 | +0.423 | **+0.469** |
| PA2A | 1.0049 | −0.196 | −0.133 | +0.137 | +0.334 | **−0.074** |
| PA2B | 1.0039 | +0.238 | +0.287 | +0.499 | +0.653 | **+0.160** |
| PA6A | 1.0015 | +0.291 | +0.310 | +0.390 | +0.448 | **+0.172** |
| PA6B | 0.9977 | +0.660 | +0.630 | +0.502 | +0.410 | **+0.350** |
| PA7A | 1.0009 | +0.100 | +0.111 | +0.160 | +0.195 | **+0.062** |
| PA7B | 0.9943 | +0.891 | +0.816 | +0.500 | +0.270 | **+0.454** |

**Every slope is within 0.5% of unity**, so the error is nearly constant and the single-point ice
offsets were never far wrong — moving to the 45 °F value shifts each probe by at most 0.043 K.

**⚠️ Do not calibrate a 45 °F probe at 100 °F.** Distance from the operating point dominates, not
bath quality. Applying the `@100` offset at 45 °F costs up to **0.316 °F** (PA7B); applying the ice
offset costs at most **0.043 °F**. The better-controlled bath gives the worse calibration here,
because 45 °F is 13 degrees from the ice point and 55 from the circulator.

**⚠️ Heating season is a different operating point.** The loops run near **140 °F** in heating,
where the correct offsets differ from the deployed 45 °F values by up to 0.3 K (0.55 °F on PA7B).
Absolute readings carry that error; **pair ΔT does not**, because the two probes of a pair have
nearly identical slopes — PA1 at 0.9954/0.9955 and PA2 at 1.0049/1.0039 — so the PA1 pair
correction moves only 0.013 °F between 45 and 140 °F and PA2's moves 0.101 °F. The `@140` column
is **extrapolated 40 degrees past the hot anchor** and should be treated as indicative; a third
bath point would be needed to deploy it.

**A constant thermometer bias cancels from the slope.** Reading 32.00/99.90 instead of
32.10/100.00 shifts every offset by −0.10 °F and changes no slope, no pair correction and no ΔT.
The mean slope across the eight probes is 0.9993, which says the two references agree with each
other on the 68 °F span to about 0.05 °F.

**IN, OUT, UBT and LBT are still single-point ice values** from 2026-08-22. At 45 °F that is worth
under 0.04 K, so redoing them is optional.

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
- **⚠️ Filter the sentinel values before taking any mean.** DallasTemperature returns −127 °C
  (−196.6 °F) for a device that vanished mid-read, and a DS18B20 returns 85.0 °C (185 °F) when a
  conversion never completed. **One −196.6 row, logged as a probe was unplugged while its ROM was
  still enumerated, moved a 196-sample mean by 1.17 °F.**

**Offset convention:** add the offset to the raw reading to correct it. `offset = reference − mean`.
A DS18B20's absolute spec is ±0.5 °C (±0.9 °F), so the ~1.4 °F spread across a batch is expected
sensor-to-sensor variation.

## Ice-point offsets

Reference 32.10 °F for the 2026-08-29 window, 32.05 °F for 2026-08-22.

| Label | ROM (printed) | w1 name | mean °F | offset °F (add) | offset K (add) | measured |
|---|---|---|---|---|---|---|
| PA1A | `28900CCC000000A5` | `28-000000cc0c90` | 30.879 | +1.221 | +0.678 | 2026-08-29 |
| PA1B | `28569BC9000000EF` | `28-000000c99b56` | 31.197 | +0.903 | +0.502 | 2026-08-29 |
| PA2A | `28A9C01A000000D5` | `28-0000001ac0a9` | 32.286 | −0.186 | −0.103 | 2026-08-29 |
| PA2B | `2854911A000000B5` | `28-0000001a9154` | 31.866 | +0.234 | +0.130 | 2026-08-29 |
| PA3A | `2879E8C90000005E` | `28-000000c9e879` | 31.424 | +0.626 | +0.348 | 2026-08-22 |
| PA3B | `28C115C9000000B2` | `28-000000c915c1` | 31.212 | +0.838 | +0.466 | 2026-08-22 |
| PA4A | `28148BC900000088` | `28-000000c98b14` | 31.208 | +0.842 | +0.468 | 2026-08-22 |
| PA4B | `28A8A01A000000F3` | `28-0000001aa0a8` | 31.792 | +0.258 | +0.143 | 2026-08-22 |
| PA5A | `28286ECB00000017` | `28-000000cb6e28` | 31.474 | +0.576 | +0.320 | 2026-08-22 |
| PA5B | `28DA8C1A000000DC` | `28-0000001a8cda` | 31.889 | +0.161 | +0.089 | 2026-08-22 |
| CRW | `28FF040FA016039F` | `28-0316a00f04ff` | 31.825 | +0.275 | +0.153 | 2026-08-29 |
| AMB | `28FF1668A316054F` | `28-0516a36816ff` | 31.208 | +0.892 | +0.496 | 2026-08-29 |
| OUT | `28FFD865A3160552` | `28-0516a365d8ff` | 32.000 | +0.100 | +0.056 | 2026-08-29 |
| DHW recirc | `28FFE715A0160328` | `28-0316a015e7ff` | 31.440 | +0.660 | +0.367 | 2026-08-29 |

The last four are the probes that served as CRW, the outdoor ambient, and OUT before the PA batch
replaced them, plus the DHW recirc probe on the Arduino at 10.0.0.114. They carry `FF` in their
serial where the PA batch carries `000000`, which distinguishes the two families at a glance.

**`28-0516a36332ff` (the former IN) is not calibrated** — it failed to enumerate during the
2026-08-29 session while its three siblings answered.

## Pair ΔT-zero corrections

For a pair reading ΔT = T_A − T_B, the corrected ΔT adds `(offset_A − offset_B)`.

| Pair | offset_A − offset_B (°F) | (K) | measured |
|---|---|---|---|
| PA1 | +0.319 | +0.177 | 2026-08-29 |
| PA2 | −0.423 | −0.235 | 2026-08-29 |
| PA3 | −0.212 | −0.118 | 2026-08-22 |
| PA4 | +0.583 | +0.324 | 2026-08-22 |
| PA5 | +0.415 | +0.231 | 2026-08-22 |

## Reproducibility

PA1 and PA2 were measured twice, a week apart, in independently made baths. **The two runs'
absolute offsets differ by +0.087…+0.162 °F, mean +0.134** — a nearly uniform shift across all four
probes, which is the signature of the two baths' reference readings disagreeing rather than of four
sensors drifting together. The anchors were 32.05 and 32.10 °F, and a Thermapen ONE is specified to
±0.5 °F, so a disagreement of this size is well inside the reference's own accuracy. **Absolute
offsets inherit that accuracy and should be read as ±0.5 °F figures.**

The pair differences, which cancel any shared bath or reference error, are what reproduce: PA1
agrees to 0.021 °F.

**The PA2 pair difference agrees only to 0.058 °F**, outside the ±0.05 °F the other pairs hold, and
PA2A is also the noisiest probe in the set at SD 0.060. PA2A is one of the two probes that came off
the wall thermally decoupled, so it has been handled since its first calibration. Take a second
window on that pair before relying on its ΔT correction.


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
