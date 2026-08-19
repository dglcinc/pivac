# DS18B20 provisioning — addressing, labelling and calibration

**Purpose:** bench work on the four secondary-loop probes before they go on the pipe. Enumerate each
probe's ROM address, establish which physical probe carries which address, calibrate them in pairs,
and record the result somewhere it cannot be lost.

**Where this runs:** David's M2 MacBook, with the probes on an Arduino over USB. It needs no Pi and
no network.

**Why it comes first:** the probes answer criteria 3 and 4 of
[`unico-cooling-assessment-and-tuning.md`](unico-cooling-assessment-and-tuning.md) §4.2, and the
measurement they produce is a *difference* of a few degrees. An uncalibrated pair carries ±36 % on a
5 °F loop ΔT, which is larger than the effects being measured. Calibration is not optional polish
here.

---

## 1. What you need

| Item | Note |
|---|---|
| 4 × DS18B20 stainless probe | The secondary-loop set: Loop A supply and return, Loop B supply and return |
| Arduino, any | UNO R4 WiFi is the house standard; anything with a digital pin works for this |
| 1 × 4.7 kΩ resistor | External bus pull-up. Do not substitute the internal pull-up |
| Breadboard and jumpers | |
| Insulated vessel, ice, water, a stirrer | Two bath points, §6 |
| `arduino-cli` or the Arduino IDE | `arduino-cli` is installed on the **Pi** at `~/bin`, not necessarily on the M2. Check before assuming |

Libraries: `OneWire` and `DallasTemperature`.

```bash
arduino-cli lib install OneWire DallasTemperature
```

## 2. Wire the bus

Normal power, not parasitic. Parasitic mode works and makes a marginal bus harder to debug, which is
the wrong trade on a bench that exists to remove doubt.

```
 VDD (red)    ── 5 V
 GND (black)  ── GND
 DQ  (yellow) ── D2 ──┬── 4.7 kΩ ── 5 V
                      │
              (all four probes share DQ)
```

Put all four on the one bus. Reading them together is the point: §3 identifies them by watching one
address move while the others hold still.

## 3. Enumerate the addresses

```cpp
#include <OneWire.h>
#include <DallasTemperature.h>

OneWire bus(2);
DallasTemperature sensors(&bus);

void printRom(const DeviceAddress a) {
  for (uint8_t i = 0; i < 8; i++) {            // full 8-byte ROM, as printed on a tag
    if (a[i] < 16) Serial.print('0');
    Serial.print(a[i], HEX);
  }
  Serial.print(",28-");                        // Linux w1 name: serial bytes reversed
  for (int8_t i = 6; i >= 1; i--) {
    if (a[i] < 16) Serial.print('0');
    Serial.print(a[i], HEX);
  }
}

void setup() {
  Serial.begin(115200);
  while (!Serial) {}
  sensors.begin();
  sensors.setResolution(12);                   // 0.0625 °C, the part's finest
  Serial.print("# devices: ");
  Serial.println(sensors.getDeviceCount());
  Serial.println("# millis,rom,w1,degF");
}

void loop() {
  sensors.requestTemperatures();
  for (uint8_t i = 0; i < sensors.getDeviceCount(); i++) {
    DeviceAddress a;
    if (!sensors.getAddress(a, i)) continue;
    Serial.print(millis()); Serial.print(",");
    printRom(a);
    Serial.print(",");
    Serial.println(sensors.getTempF(a), 4);
  }
  delay(1000);
}
```

`Serial.print(x, HEX)` emits uppercase. **Lowercase the w1 name when transcribing** — Linux presents
it lowercase, and a case mismatch in `config.yml` will not match the bus.

Flash and watch:

```bash
arduino-cli board list
arduino-cli compile -b arduino:renesas_uno:unor4wifi ds18b20_scan
arduino-cli upload  -b arduino:renesas_uno:unor4wifi -p /dev/cu.usbmodemXXXX ds18b20_scan
arduino-cli monitor -p /dev/cu.usbmodemXXXX -c baudrate=115200
```

Expect four devices. Fewer means a wiring fault or a marginal pull-up, and it is worth fixing on the
bench rather than discovering on a pipe in a ceiling.

## 4. Establish which physical probe is which

> ⚠️ **Do not read the printed tag to decide this.** A probe already in service on this system was
> found carrying **two** tags, the spare belonging to another sensor
> (`CLAUDE.md`, Known Operational Behaviours). The ROM is read from the chip, so the bus is always
> authoritative and no data is at risk; the label is what lies.

With all four reading and the serial monitor scrolling:

1. Close your hand around one probe for about 20 seconds.
2. Watch which address rises. That is the probe in your hand.
3. Mark that probe physically — a wrap of tape with the **last four hex digits** of its ROM is
   enough to be unambiguous and short enough to survive on a probe body.
4. Let it settle, then repeat for the remaining three.

Cross-check each one by unplugging it and confirming that address drops out of the scan. Two
independent confirmations per probe costs a couple of minutes and removes the single failure mode
that would silently invert a ΔT later.

## 5. Validate the ROM before you write it down

Byte 8 is a CRC-8/Maxim over the first seven. `OneWire::crc8(rom, 7) == rom[7]` checks it. A ROM that
fails is a transcription error rather than a bad part.

The mapping between the printed form and the Linux device name reverses the six serial bytes:

```
printed  28 FF 16 68 A3 16 05 4F
         └┬┘ └──────┬──────┘ └┬┘
       family    serial      CRC

w1 name  28-0516a36816ff        serial bytes reversed, lowercase
```

## 6. Calibrate in pairs

What the loop sensors measure is a difference of a few degrees between two probes, so **agreement
within a pair matters more than absolute accuracy**. A DS18B20 is ±0.5 °C absolute out of the box and
far more repeatable than that against another DS18B20 in the same bath, which is the property this
step captures. Full rationale in the assessment's §G.1.

For each pair (Loop A supply + return, then Loop B supply + return):

1. Bundle the two probes together so they sit in the same water, touching.
2. Ice bath first: crushed ice and water, stirred continuously. Give it five minutes to settle.
3. Log **15 minutes at the production sample rate** — 1 s here is fine and averages down.
4. Second point at working temperature: chilled water near **45 °F**, stirred, another 15 minutes.
   Chilled duty is where these probes earn their keep, so this is the point that counts.
5. Record the mean difference at each point.

```bash
arduino-cli monitor -p /dev/cu.usbmodemXXXX -c baudrate=115200 | tee loopA_ice.csv
```

Read the result this way:

- **Offset stable across both baths** — take the mean difference as the pair offset and put it in
  `offsets:` in `config.yml`.
- **Offset different at the two points** — the pair has a slope rather than an offset. Use the
  45 °F figure, since that is the operating point, and note the discrepancy in the table below.
- **Difference above about 0.5 °F** — suspect the bath rather than the probes. An unstirred bath
  stratifies by more than the error being chased.

Stir throughout. A still ice bath is not 32 °F everywhere, and it will manufacture an offset that is
really a temperature gradient.

## 7. Record the map before anything is installed

Fill this in and **commit it**. The DS18B20 on the 10.0.0.114 board has a ROM that exists in neither
repo, recoverable only because it was written into `CLAUDE.md` by elimination after the fact. Do not
create a second instance of that.

| Role | ROM (printed form) | w1 name | Pair | Offset at 45 °F | Marked |
|---|---|---|---|---|---|
| `LOOPA_SUP` | | | A | | |
| `LOOPA_RET` | | | A | | |
| `LOOPB_SUP` | | | B | | |
| `LOOPB_RET` | | | B | | |

Then mount them on **copper at the tees, not on PEX** — PEX conducts about a thousand times worse,
and the full mounting and insulation procedure is in the assessment's §4.2 under "Mounting the four
loop probes".

## 8. The 10K NTCs are a different job

The two Honeywell 10K NTC duct sensors for the air-handler node have no bus address, so none of the
above applies. They are analog, read through a ratiometric divider, and calibrated by fitting
Steinhart-Hart or a beta curve against known points. That procedure is in the assessment's §E.4, and
it is only worth doing when the air-handler node is built.

## 9. While the Arduino tooling is out on the M2

Two standing items live on that machine and nowhere else.

**Re-capture the .114 DHW board's recirc-temperature sketch.** It exists only on the M2 and on the
board itself, was never committed, and flashing the repo's psi-only sketch onto that board would
silently drop `environment.inside.hvac.dhw.recirc.temperature`. Commit it to `~/github/Arduino`.

**Check whether `~/github/Arduino` has anything else uncommitted**, for the same reason.
