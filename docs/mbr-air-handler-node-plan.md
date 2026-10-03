# Master bedroom air-handler node: wiring and sketch plan

An Arduino UNO R4 WiFi at the master bedroom's Unico M2430 reads five signals: the water entering and
leaving the coil, the air entering and leaving the air handler, and the thermostat's Y2 call, which
is the high fan stage. pivac polls it over WiFi and publishes to Signal K, the same path the DHW
and boiler pressure boards use. The case for measuring this coil, and the physics the data feeds,
are in `docs/unico-cooling-assessment-and-tuning.md` §4.4, §4.6, §5.10 and Appendices E to G. This
document is the build: wiring, the sketch, the pivac side and the checks.

The node carries no water flow meter. Pin D3 is left free for one, since Appendix E.6 says Loop A
needs a per-coil meter before the node can report capacity in BTU/h. Without it the node still
answers the questions that matter now: whether the coil is short of water, short of air or
overloaded when the room loses setpoint, and how much of each call runs on the high fan stage.

The first question is already pressing. The room runs 2 °F over setpoint from late morning into
early afternoon at the same hours whatever the outdoor temperature, with the water side and the strainer measured sound (§5.10 of the
assessment). The return-air sensor shows whether the room is warm or only the thermostat is, and
`y2` shows whether the coil was already on its high fan stage while it lost ground.

## 1. What the node measures

| Signal | Sensor | Pin | Field |
|---|---|---|---|
| Water to coil | DS18B20 | D2 | `wsup` |
| Water from coil | DS18B20 | D2 | `wret` |
| Return air | 10K NTC | A0 | `aret` |
| Supply air | 10K NTC | A1 | `asup` |
| Y2 call | H11AA1 opto | D6 | `y2`, `y2_s` |

All temperatures go out in °F at two decimals, and pivac converts them to Kelvin. `y2` is the call
right now, 0 or 1. `y2_s` counts the seconds Y2 has been asserted since boot, so the Pi can take
the stage-2 fraction from its derivative without missing a short burst between polls. The line
also carries `uptime_ms` and `rssi`, for diagnosing reboots and the attic's WiFi.

## 2. Board and power

The board is an UNO R4 WiFi, the same as every other pivac node, with a screw-terminal proto
shield on top so every field wire lands on a screw. The R4's pins run at 5 V, and its ADC reads
14 bits against the board's own 5 V rail.

Power it from a 5 V USB-C supply on a receptacle near the air handler. That keeps the Arduino's
ground off the air handler's 24 VAC control transformer, which the Y2 opto exists to isolate. If
no receptacle is in reach, an isolated 24 VAC to 5 V DC converter on R and C will do, but never
rectified 24 VAC into VIN. Rectified 24 VAC peaks near 34 V, and the R4's VIN is rated to 24 V.

## 3. Wiring

### 3.1 Water temperatures, DS18B20 on D2

Both probes share one 1-Wire bus on D2, with one 4.7 kΩ pull-up from D2 to 5 V. Each probe has
three wires: red to 5 V, black to GND, yellow (data) to D2. Run them powered, never parasitic.

```
 5V ──┬──────────────── red (both probes)
      │
   [4.7 kΩ]
      │
 D2 ──┴──────────────── yellow (both probes)
 GND ────────────────── black (both probes)
```

The sketch addresses each probe by its ROM, set in the zone's `.ino`, so supply and return can
never swap if the bus enumerates them in a different order. Record both ROMs in this document at
the build; the printed tags on these probes are unreliable.

Strap each probe to bare, cleaned copper on the coil's supply and return, as close to the coil
connections as the pipe allows and at least five diameters from a fitting. Use thermal compound
and a stainless clamp, then 25 mm of insulation extending 100 mm each side (Appendix E.3). Mount
the two identically, so a residual mounting error is common to both and cancels out of the ΔT.
Strain-relieve each cable an inch or two behind the probe.

### 3.2 Air temperatures, 10K NTC on A0 and A1

Each NTC sits on the low side of a divider fed from the board's 5 V, the rail the ADC also uses as
its reference, so supply variation cancels.

```
 5V ──[ 10.0 kΩ 0.1 % ]──┬── A0 (return air)       5V ──[ 10.0 kΩ 0.1 % ]──┬── A1 (supply air)
                         │                                                 │
                    NTC lead 1 ═══ shielded pair ═══ NTC          NTC lead 1 ═══ shielded pair ═══ NTC
                         │                                                 │
                  0.1 µF to GND                                     0.1 µF to GND
 GND ────────────── NTC lead 2                     GND ────────────── NTC lead 2
                    shield to GND at the board only                   shield to GND at the board only
```

Fit the 0.1 µF capacitor at the pin, on the shield, rather than at the sensor. Run each sensor on
its own two-conductor shielded cable with the drain grounded at the board end alone.

Measure each sensor's resistance at room temperature before wiring. About 10 kΩ at 77 °F
confirms a 10K part. Honeywell also sells 20K duct sensors, and a 20K part wants a 20.0 kΩ
reference resistor instead.

Put the return sensor in the return plenum ahead of the coil, out of sight of the coil face. Put
the supply sensor in the supply plenum after the blower and before the first takeoff, where the
blower has mixed the air. Shield both from radiation, seal the supply probe's body, and route its
leads downward, because in cooling it sits in air near saturation (Appendix E.4).

### 3.3 Y2 call, H11AA1 on D6

Y2 is 24 VAC and must never reach a pin. An H11AA1 takes AC directly through its two antiparallel
LEDs, so it needs no bridge, and it isolates the control transformer from the Arduino.

```
 Y2 (air handler) ──[ 3.3 kΩ ½ W ]── pin 1 ┐
                                           H11AA1
 C  (air handler) ──────────────────── pin 2 ┘      pin 3, pin 6 not connected

 5V ──[ 10 kΩ ]──┬── D6
                 ├── pin 5 (collector)
            1 µF │
 GND ────────────┴── pin 4 (emitter)
```

At 24 VAC the LED current is about 7 mA RMS and the resistor dissipates 0.17 W, so ½ W leaves
margin up to the 28 VAC an unloaded transformer can show. The transistor pulls D6 low while Y2 is
asserted, so the sketch inverts it. The 1 µF capacitor holds D6 low through the zero crossings,
when neither LED conducts, and lets it rise about 10 ms after Y2 drops. The sketch also takes a
window of samples (§4.6), so the input reads a clean level with or without the capacitor.

Before connecting anything, measure Y2 to C at the air handler with a meter, once with the zone
idle and once on a high-fan call. The call should read 24 to 28 VAC. With stage 2 off, a reading
above about 3 VAC is leakage through the thermostat's output, which is enough to half-turn-on the
opto. In that case use a 24 VAC coil relay instead (Functional Devices RIBU1C in the parts list):
coil across Y2 and C, dry contact between D6 and GND, and `INPUT_PULLUP` on D6. A relay coil needs
tens of milliamps to pull in and ignores leakage.

Read the air handler's terminal strip to confirm which screw carries Y2 before landing a wire.
`docs/unico-cooling-assessment-and-tuning.md` Appendix J describes the thermostat's staging.

### 3.4 Shield terminal map

| Terminal | Wire |
|---|---|
| 5V | DS18B20 red ×2, 4.7 kΩ, both 10.0 kΩ, 10 kΩ |
| GND | DS18B20 black ×2, NTC lead 2 ×2, shields, H11AA1 pin 4 |
| D2 | DS18B20 yellow ×2 |
| A0 | Return-air NTC lead 1 |
| A1 | Supply-air NTC lead 1 |
| D6 | H11AA1 pin 5 |
| D3 | Free, for the flow meter |

The H11AA1 and its resistors sit on the shield's prototyping area. Y2 and C arrive on their own
two-position terminal block, kept at the far edge from the 5 V parts, and nothing on the 24 VAC
side shares a rail with the Arduino.

Avoid D0 and D1 (serial), D4 and D5 (CAN) and D10 to D13 (SPI). The free general-purpose pins
after this build are D3, D7, D8 and D9.

## 4. Sketch

### 4.1 Layout in the Arduino repo

The sketch lives in `~/github/Arduino` beside the pressure and water sketches, built to take more
zones without copying code:

| Path | Contents |
|---|---|
| `AirHandler/AirHandler_impl.h` | All logic |
| `AirHandler_MBR/AirHandler_MBR.ino` | Zone constants, then `#include` |
| `AirHandler_MBR/AirHandler_impl.h` | Symlink to the shared file |
| `AirHandler_MBR/arduino_secrets.h` | WiFi credentials, gitignored |

This is the pattern `ArduinoPSI_impl.h` already uses for the two pressure boards. A second zone is
a new folder with its own `.ino`, its own ROMs and its own secrets.

The zone file defines only what differs between air handlers:

```cpp
// AirHandler_MBR.ino
#define ZONE_TAG       "MBR"
// DS18B20 ROMs, read from the serial log in bring-up mode (section 4.8)
#define ROM_WSUP       { 0x28, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 }
#define ROM_WRET       { 0x28, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 }
// NTC curve: nominal resistance at 25 C and beta, from the data sheet, then checked (section 6)
#define NTC_R0_OHM     10000.0f
#define NTC_BETA       3950.0f
#define NTC_RREF_OHM   10000.0f
#include "AirHandler_impl.h"
```

### 4.2 Reliability scaffolding, copied from `ArduinoPSI_impl.h`

The new header reuses the pressure boards' proven skeleton unchanged: the RA4M1 watchdog armed
first in `setup()` and refreshed each `loop()` at 5 s, the bounded `connectWiFi()` that resets the
board with `NVIC_SystemReset()` after 20 s, the 2 s cap on serving one HTTP client, and the
single-line single-quoted response that `pivac.ArduinoSensor` parses with `ast.literal_eval`.
`loop()` must never block, so every sensor read below is non-blocking.

### 4.3 Loop timing

| Task | Cadence | Blocking |
|---|---|---|
| Watchdog refresh | Every loop | No |
| WiFi check | Every 1 s | No |
| Y2 sample | Every loop | No |
| ADC sample, A0 and A1 | Every loop, into accumulators | No |
| Air temperature publish | Each 1 s block | No |
| DS18B20 read and restart | Every 2 s | No |
| HTTP client | When one connects | 2 s cap |
| LED matrix | Every 1 s | No |

### 4.4 Water temperatures

`DallasTemperature` with `setResolution(12)` and `setWaitForConversion(false)`, exactly as the DHW
board runs it. Every 2 s the sketch reads both probes by ROM with `getTempF(rom)`, then calls
`requestTemperatures()` to start the next conversion, which takes 750 ms and so is always finished
by the following read. A read that returns `DEVICE_DISCONNECTED_F` (−196.6 °F) or the power-on
value of exactly 185.0 °F is a fault, and the field is left out of the response (§4.7).

### 4.5 Air temperatures

`analogReadResolution(14)` in `setup()`. Each loop adds one reading from A0 and one from A1 to a
running sum; once a second the sketch divides by the count, converts, and stores the result. The
WiFi status call is the slow part of a loop, which is why it runs once a second, and the loop then
turns over hundreds of times a second, more than the 100 to 256 samples Appendix E.4 asks for.

The conversion, with the NTC on the low side of the divider:

```cpp
float ntcF(float counts) {
  if (counts < 50 || counts > 16333) return NAN;            // open or shorted sensor
  float r  = NTC_RREF_OHM * counts / (16383.0f - counts);   // NTC resistance, ohms
  float k  = 1.0f / (1.0f / 298.15f + logf(r / NTC_R0_OHM) / NTC_BETA);
  return (k - 273.15f) * 9.0f / 5.0f + 32.0f;
}
```

The beta equation is within a few tenths of a degree of Steinhart-Hart from 40 to 100 °F, and the
two-point check in §6 measures the residual. Near room temperature one ADC count is about 0.01 °F,
so averaging, not resolution, sets the floor. Per-sensor offsets belong in pivac's config, never in
the sketch.

### 4.6 Y2

Each loop reads D6. A low sample sets `y2` to 1 at once. `y2` returns to 0 only after D6 has read
high on every sample for 100 ms, twelve mains half-cycles, so the zero crossings cannot drop it
even without the capacitor, and a loop stalled for up to 2 s on an HTTP client cannot either: the
first sample after the stall either confirms the call or starts the 100 ms clock. On each 0 to 1
change the sketch notes the time; on each 1 to 0 change it adds the elapsed time to a running
total. `y2_s` is that total plus the current call if one is open, in whole seconds since boot.

### 4.7 Response

One line, single-quoted, fields only for sensors that read correctly this cycle:

```
{'wsup' : 49.81, 'wret' : 55.37, 'aret' : 76.12, 'asup' : 58.40, 'y2' : 1, 'y2_s' : 4312, 'rssi' : -61, 'uptime_ms' : 84213021}
```

A faulted sensor is left out of the line entirely, never sent as a sentinel. `pivac.ArduinoSensor`
has no sentinel handling: it would convert −999 °F to Kelvin and publish it as a reading. A missing
key makes it log one warning and skip that path, so Signal K shows the path going stale, which the
freshness alert reports. Build the line with `snprintf` into a 256-byte buffer, appending each
field only if its value is finite.

### 4.8 Bring-up mode

On boot, before WiFi, the sketch prints every ROM on the 1-Wire bus and the raw ADC counts for A0
and A1 to the serial port for ten seconds. That is how the two ROMs get into the zone's `.ino`:
warm one probe in a hand, watch which ROM's reading rises, and record which pipe it goes on. The
same log confirms each NTC reads mid-scale (about 8,000 counts at room temperature) before it goes
into a plenum.

### 4.9 LED matrix

The matrix cycles each second through `S58` (supply air), `R76` (return air) and `W6` (water ΔT,
return minus supply), with a dot in the corner while Y2 is asserted. Anyone opening the cabinet can
see the node is alive and the call it is seeing without a laptop.

## 5. pivac and Signal K

### 5.1 Data path

pivac polls the board over HTTP, as it does the pressure boards. The board holds no Signal K
credentials or token, the calibration offsets stay in version-controlled config on the Pi, and
the watchdog, freshness alerts and backup restarts already cover this shape of service. Pushing to
Signal K from the board would need a JWT stored in its flash, renewed when it expires, and a
WebSocket client on the R4, and it would bypass all of that.

### 5.2 Config

The section is named for the air handler and loads `pivac.ArduinoSensor`. When a flow meter
arrives, the `module:` line changes to the `pivac.UnicoAH` wrapper of Appendix F.2, which adds the
derived capacities, and no Signal K path changes.

```yaml
pivac.UnicoAH_MBR:
    description: Master bedroom Unico M2430, coil water and air temperatures and the Y2 call
    module: pivac.ArduinoSensor
    enabled: true
    ipaddr: 10.0.0.xxx
    rounding: 2
    inputs:
        wsup:
            sk_path: environment.inside.hvac.ah.mbr.water
            outname: supply
            type: temperature
            offset: 0.0     # kelvin, from the pair calibration in section 6
        wret:
            sk_path: environment.inside.hvac.ah.mbr.water
            outname: return
            type: temperature
            offset: 0.0
        aret:
            sk_path: environment.inside.hvac.ah.mbr.air
            outname: return
            type: temperature
            offset: 0.0
        asup:
            sk_path: environment.inside.hvac.ah.mbr.air
            outname: supply
            type: temperature
            offset: 0.0
        y2:
            sk_path: environment.inside.hvac.ah.mbr
            outname: y2
        y2_s:
            sk_path: environment.inside.hvac.ah.mbr
            outname: y2Seconds
        uptime_ms:
            sk_path: environment.inside.hvac.ah.mbr
            outname: uptimeMs
```

### 5.3 Signal K paths

| Path | Unit |
|---|---|
| `environment.inside.hvac.ah.mbr.water.supply.temperature` | K |
| `environment.inside.hvac.ah.mbr.water.return.temperature` | K |
| `environment.inside.hvac.ah.mbr.air.supply.temperature` | K |
| `environment.inside.hvac.ah.mbr.air.return.temperature` | K |
| `environment.inside.hvac.ah.mbr.y2` | 0/1 |
| `environment.inside.hvac.ah.mbr.y2Seconds` | s |
| `environment.inside.hvac.ah.mbr.uptimeMs` | ms |

These match Appendix F.3, whose `<unit>` level lets a second air handler arrive as `ah.kids`
without renaming this one. The water and air ΔT are computed in Grafana from the pairs, and the
stage-2 fraction is the derivative of `y2Seconds` over the time `MASTER_BR.statenum` reads −1.

### 5.4 pivac changes

1. `pivac/ArduinoSensor.py` gains a per-input `offset:` in Kelvin, applied before rounding, as
   `pivac.OneWireTherm` already does. The same change lets the DHW recirc probe's parked +0.274 K
   correction be applied.
2. `scripts/systemd/pivac-ah-mbr.service`, a copy of `pivac-arduino-psi.service` running
   `pivac.UnicoAH_MBR` at `--loglevel WARNING`.
3. `scripts/nas-image-backup.sh`: add `pivac-ah-mbr` to both `STOP_SVCS` and `START_SVCS`.
4. `grafana/provisioning/alerting/sensor-freshness.yaml`: one freshness rule on
   `ah.mbr.air.return.temperature`, shipped `isPaused: true` and unpaused once the path publishes.
5. `scripts/arduino-watchdog.sh` is not extended. The new board is not on the Arduinos Shelly plug,
   so the watchdog cannot power-cycle it; its own WDT and WiFi reset are the recovery.
6. `CLAUDE.md`: the Active Services table, the restart, stop and log commands, the Current
   Modules entry, and the board's MAC and IP. The Arduino repo's `CLAUDE.md` gains the board in its
   hardware table.
7. A DHCP reservation on the UCG for the board's MAC.

## 6. Calibration and commissioning

1. On the bench, bundle the two DS18B20s in a stirred insulated jug and log 15 minutes at room
   temperature and 15 in ice water. The mean difference at each point is the pair offset; split it
   between the two `offset:` keys (Appendix G.1).
2. Put both NTCs in the same jug beside a DS18B20 at the same two points. The ice bath checks
   `NTC_BETA`: if both NTCs read the same error at 32 °F and at room temperature, it is an offset;
   if the error changes between the two points, adjust beta until it doesn't, then set offsets.
3. With the node installed, set the thermostat's fan to On with no call for 20 minutes. `asup` and
   `aret` should then agree within 0.3 °F, and the return air should track the RedLink room
   temperature within the thermostat's whole-degree reporting.
4. On the first cooling call, `wret` must read above `wsup` and `asup` below `aret`. A reversed
   sign is a swapped probe.
5. Force a high-fan call at the thermostat and confirm `y2` reads 1 within one poll, then 0 when it
   ends, and that `y2Seconds` advanced by the length of the call.

## 7. Parts

| Ref | Part | Qty | Digi-Key | Amazon |
|---|---|---|---|---|
| U1 | Arduino UNO R4 WiFi, ABX00087 | 1 | [ABX00087](https://www.digikey.com/en/products/detail/arduino/ABX00087/20371539) | [search](https://www.amazon.com/s?k=Arduino+UNO+R4+WiFi+ABX00087) |
| — | Adafruit Proto-ScrewShield, 196 (kit) | 1 | [196](https://www.digikey.com/en/products/detail/adafruit-industries-llc/196/5011063) | [search](https://www.amazon.com/s?k=Adafruit+Proto-Screwshield+196+Arduino) |
| T1, T2 | DFRobot DFR0198, DS18B20 stainless probe | 3 | [DFR0198](https://www.digikey.com/en/products/detail/dfrobot/DFR0198/7597054) | [search](https://www.amazon.com/s?k=DFRobot+DFR0198+waterproof+DS18B20) |
| R1 | Yageo MFP-25BRD52-4K7, 4.7 kΩ | 1 | [MFP-25BRD52-4K7](https://www.digikey.com/en/products/detail/yageo/MFP-25BRD52-4K7/2058823) | [search](https://www.amazon.com/s?k=4.7k+ohm+1%2F4W+metal+film+resistor+through+hole) |
| R2, R3 | Yageo MFP-25BRD52-10K, 10.0 kΩ 0.1 % 25 ppm | 2 | [MFP-25BRD52-10K](https://www.digikey.com/en/products/detail/yageo/MFP-25BRD52-10K/2059114) | [search](https://www.amazon.com/s?k=10k+ohm+0.1%25+25ppm+1%2F4W+metal+film+resistor) |
| C1, C2 | Kemet C315C104M5U5TA, 0.1 µF 50 V | 2 | [C315C104M5U5TA](https://www.digikey.com/en/products/detail/kemet/C315C104M5U5TA/817927) | [search](https://www.amazon.com/s?k=0.1uF+50V+ceramic+capacitor+radial+through+hole) |
| U2 | Vishay H11AA1, AC-input opto, DIP-6 | 1 | [H11AA1](https://www.digikey.com/en/products/detail/vishay-semiconductor-opto-division/H11AA1/1731509) | [search](https://www.amazon.com/s?k=H11AA1+optocoupler+DIP-6) |
| R4 | Yageo MFR50SFTE52-3K3, 3.3 kΩ ½ W | 1 | [MFR50SFTE52-3K3](https://www.digikey.com/en/products/detail/yageo/MFR50SFTE52-3K3/9151462) | [search](https://www.amazon.com/s?k=3.3k+ohm+1%2F2W+resistor+through+hole) |
| R5 | Yageo MFR-25FBF52-10K, 10 kΩ | 1 | [MFR-25FBF52-10K](https://www.digikey.com/en/products/detail/yageo/MFR-25FBF52-10K/13219) | [search](https://www.amazon.com/s?k=10k+ohm+1%2F4W+1%25+metal+film+resistor) |
| C3 | Kemet C330C105K5R5TA, 1 µF 50 V X7R | 1 | [C330C105K5R5TA](https://www.digikey.com/en/products/detail/kemet/C330C105K5R5TA/818165) | [search](https://www.amazon.com/s?k=1uF+50V+X7R+ceramic+capacitor+radial+through+hole) |
| W1, W2 | Belden 8451, 2 × 22 AWG shielded, 100 ft | 1 | [8451 010100](https://www.digikey.com/product-detail/en/belden-inc/8451-010100/BEL1311-100-ND/7007722) | [search](https://www.amazon.com/s?k=Belden+8451+22+AWG+2+conductor+shielded+cable) |
| PS1 | Raspberry Pi SC0218, 5.1 V 3 A USB-C | 1 | [SC0218](https://www.digikey.com/en/products/detail/raspberry-pi/RPI-USB-C-power-supply-Black-US/10258759) | [search](https://www.amazon.com/s?k=Raspberry+Pi+15W+USB-C+power+supply+SC0218) |
| K1 | Functional Devices RIBU1C, if Y2 leaks (§3.3) | 0–1 | [RIBU1C](https://www.digikey.com/en/products/detail/aim-dynamics/RIBU1C/28531178) | [B000LESCI2](https://www.amazon.com/Functional-Devices-RIBU1C-Enclosed-Pilot/dp/B000LESCI2) |

The two 10K NTC duct sensors are on hand. The links were found by search on 2026-10-03, and
Digi-Key refused automated page loads, so check stock and status on each page before ordering.

1. R1 is a 0.1 % part only because Digi-Key's 1 % 4.7 kΩ page could not be found; any 4.7 kΩ
   ¼ W resistor works as the pull-up.
2. C1 and C2 are Z5U, which is fine for an ADC filter. C3 showed a 30-week factory lead time, and
   any 1 µF 50 V ceramic, X7R or X5R, through-hole substitutes.
3. R4 is metal film at ±1 %; carbon film CFR-50JB-52-3K3 at ±5 % serves as well.
4. The Proto-ScrewShield is a kit, soldered before anything else goes on it.
5. Add a small enclosure with two cable glands for the attic, and thermal compound, stainless worm
   clamps and 25 mm pipe insulation for the water probes.

## 8. More zones

A second zone needs another board and parts kit, a folder `AirHandler_<ZONE>` with its own ROMs and
secrets, a config section `pivac.UnicoAH_<ZONE>` with `ah.<zone>` paths, and its own service. The
kids room is next on Loop A; together the two nodes split Loop A's flow and load between its
coils. On the kitchen and great room, which cool on the Bosch units, the water probes read only in
heating and the air pair carries the cooling side.
