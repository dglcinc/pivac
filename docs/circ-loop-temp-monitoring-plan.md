# Plan — Hot-Water Circulator-Loop Temperature Monitoring

**Status:** decisions resolved (§12); firmware flashed + pivac code/sample/alert done (PR #59); remaining = live-config edit + Grafana panel + deploy/verify on Pi · **Created:** 2026-05-31 · **Owner:** David

Living plan doc. Update the Status checklist at the bottom as steps complete.

---

## 1. Objective

Add a 5th DS18B20 temperature sensor that reads the **domestic hot-water (DHW)
recirculation loop** temperature, so we can:

1. Verify the recirc pump is actually circulating hot water (loop stays hot).
2. Get alerted when the loop goes cold — the signature of a pump that has lost
   prime / failed — so David can re-prime it.

The sensor data flows into Signal K → InfluxDB → Grafana/WilhelmSK like the
other temperatures, and gets a freshness alert plus a "loop went cold" alert
through the existing Grafana → Graph email bridge.

**Success criteria:** `environment.inside.hvac.dhw.recirc.temperature` publishes to
Signal K every poll cycle in Kelvin; Grafana plots it; an email fires if it
goes stale (>30m). A pump-health ("loop never gets hot") alert is deferred until
we've observed the loop's real on-demand/aquastat duty cycle — a static cold
threshold would false-alarm on this loop (see §8.3).

---

## 2. Current-state facts (grounded 2026-05-31; IP/module corrected 2026-06-01)

> **⚠️ CORRECTION (2026-06-01):** the DHW board is **`10.0.0.114`**, served by the
> **`pivac.ArduinoPSI`** section (delta `electrical.ac.arduinoPSI.psi`) — NOT
> `.219`/`ArduinoThermPSI` as the first draft of this plan assumed. The two Arduino
> module/delta names are **inverted** vs physical role (`arduinoThermPSI`/`.219` is
> the boiler/hydronic board, lower-range 100 PSI sensor; `arduinoPSI`/`.114` is DHW,
> 200 PSI). Verified against the WilhelmSK gauge titles ("Potable DHW PSI" ←
> `arduinoPSI`) and the boards' WiFi MACs (DHW = `c0:4e:30:11:6f:3c`). See CLAUDE.md
> "Active Services and Devices". **The recirc-loop probe therefore belongs on
> `pivac.ArduinoPSI` (.114).** Where older text below still says `.219`/`ArduinoThermPSI`
> for the DHW board, read `.114`/`ArduinoPSI`.

- The DHW pressure Arduino at **`10.0.0.114`** (UNO R4 WiFi, section
  `pivac.ArduinoPSI`) currently serves:
  ```
  <!DOCTYPE HTML>
  <html>
  {'psi' : 13.687136}
  </html>
  ```
  Single-quoted pseudo-JSON inside HTML boilerplate.
- `pivac/ArduinoSensor.py` polls `http://<ipaddr>`, regex-extracts the `{...}`
  line, parses it with `ast.literal_eval` (NOT `json.loads` — single-quoted
  keys are Python literals, not JSON), and reads a **hardcoded `['psi']`** key.
  It is *not* multi-field today.
- The shared module is used by two services via `module: pivac.ArduinoSensor`:
  `pivac-arduino-psi` → **`10.0.0.114` (DHW board)** and `pivac-arduino-therm-psi`
  → **`10.0.0.219` (boiler/hydronic board)**.
- Live config shape for the DHW Arduino (`/etc/pivac/config.yml`):
  ```yaml
  pivac.ArduinoPSI:                       # the DHW board (inverted legacy name)
      module: pivac.ArduinoSensor
      enabled: true
      ipaddr: 10.0.0.114
      sk_path: electrical.ac.arduinoPSI
      propagate: [sk_path]
      daemon_sleep: 1
      inputs:
          psi:
              outname: psi
  ```
  → emits `electrical.ac.arduinoThermPSI.psi`.
- `pivac.set_config()` (in `pivac/__init__.py`) calls
  `propagate_defaults(p, p["inputs"], p["propagate"])` — it copies a top-level
  key (e.g. `sk_path`) into each input **only if that key is absent** on the
  input. So a per-input `sk_path` override is respected.
- All temperatures in Signal K / InfluxDB are stored in **Kelvin** (e.g. the
  hydronic gauges `environment.inside.hvac.{IN,CRW,OUT}.temperature` read
  ~285–340 K). The new sensor must publish Kelvin for gauge/alert consistency.
- The Arduino firmware repo (`github.com/dglcinc/Arduino`, default branch
  `main`): active compile/upload copy is on the **Mac** at `~/github/Arduino`
  (working copy, branch `main`, `arduino_secrets.h` populated). A reference
  clone also exists on the Pi at `~/github/Arduino`. Compile + upload is
  **Mac-only** (USB, no OTA).
- Firmware structure: two sketches, `ArduinoPSI_BoilerLoop` (boiler/hydronic,
  10.0.0.219, 100 PSI) and `ArduinoPSI_Domestic` (DHW, 10.0.0.114, 200 PSI). They share ONE
  implementation file — `ArduinoPSI_Domestic/ArduinoPSI_impl.h` is a **symlink**
  to `ArduinoPSI_BoilerLoop/ArduinoPSI_impl.h`. The `.ino` files differ only in
  `SENSOR_MAX_PSI` / `SENSOR_MAX_V`. The HTTP response is built with
  `sprintf(jsonResponse, "{'psi' : %f}", psi)` into a `char jsonResponse[100]`.
- WiFi creds live in a **gitignored `arduino_secrets.h`** (`SECRET_SSID` /
  `SECRET_PASS`) per sketch folder — NOT hardcoded in the `.ino` (corrects an
  older note). Hardware: UNO R4 WiFi, analog sensor on A0 @ 14-bit, LED-matrix
  display, `WiFiS3`.

---

## 3. Architecture decision — reuse the DHW Arduino (10.0.0.114, `pivac.ArduinoPSI`)

**Recommended: reuse the existing DHW pressure Arduino.** It is a UNO R4 WiFi
with plenty of free digital pins; one DS18B20 adds a single 1-Wire bus on one
GPIO. The sketch returns both values in one response:
`{'psi' : 13.69, 'temp' : 120.5}`.

**Why reuse:**
- No new device, IP reservation, power supply, or WiFi credentials to manage.
- The DHW pressure sensor and the recirc loop are plumbing-adjacent (both on the
  DHW side), so the DS18B20 cable run to the same enclosure is short.
- One firmware, one place to maintain.

**Trade-off (accepted):** coupling. If `10.0.0.219` hangs (the documented
occasional "Arduino timeouts" behaviour), DHW pressure *and* circ temp go stale
together. For monitoring (not control) this is fine; the freshness alert names
which value dropped.

**The one physical gate:** cable run length from the DS18B20's mounting point on
the recirc loop pipe back to the Arduino enclosure. DS18B20 in normal
(non-parasitic) 3-wire mode tolerates several metres, and 10 m+ is achievable
with twisted-pair + a stronger pull-up. If the loop sensor location is far from
the `10.0.0.219` enclosure (more than a comfortable cable run), fall back to a
**new dedicated Arduino** at its own IP — same firmware, `temp`-only response,
its own pivac config section. Everything else in this plan is identical.

> **DECIDED (2026-05-31):** reuse `10.0.0.219` — cable run confirmed comfortable.
> Coupling trade-off accepted (DHW pressure + circ temp stale together if the
> board hangs; freshness alert names which value dropped).

---

## 4. Bill of materials

- 1× DS18B20 (already on hand — same type as the other four). Bare or
  stainless-probe version; probe is better for clamping to a pipe.
- 1× 4.7 kΩ resistor (pull-up). (2.2–3.3 kΩ if the cable run is long.)
- 3-conductor cable to reach the loop (twisted pair preferred for long runs).
- Pipe-clamp or thermal pad + insulation to couple the probe to the recirc pipe
  and shield it from ambient air (so it reads pipe temp, not room temp).

---

## 5. Wiring — DS18B20 → Arduino UNO R4 WiFi

Normal power (3-wire) mode, **not** parasitic. 1-Wire data line needs a pull-up
to VCC.

```
 DS18B20                         Arduino UNO R4 WiFi
 ----------------                -------------------
 VDD  (red)   ───────────────────► 5V
 GND  (black) ───────────────────► GND
 DQ   (yellow/white) ────┬────────► D2   (ONE_WIRE_BUS pin — any free digital pin)
                         │
                       [4.7 kΩ]
                         │
 5V  ────────────────────┘         (pull-up between DQ and 5V)
```

### Pin assignments

| DS18B20 lead | UNO R4 WiFi pin | Notes |
|---|---|---|
| VDD (red) | **5V** (power header) | DS18B20 runs 3.0–5.5 V; logic is 5 V, so power from 5V |
| GND (black) | any **GND** | three available (two on the power header, one by D13) |
| DQ / data (yellow/white) | **D2** | `ONE_WIRE_BUS`; any free digital pin — D2 confirmed free (below) |
| 4.7 kΩ pull-up | between **DQ and 5V** | mandatory — see "Why the external resistor" |

**D2 is confirmed free.** Grounded against the live firmware (`ArduinoPSI_impl.h`,
2026-05-31): the sketch uses **only `A0`** (analog pressure sensor) and the
**internal LED matrix** (driven by dedicated RA4M1 pins, not the header). It uses
no digital GPIO, I²C, SPI, Serial1, or interrupts — so the whole digital header is
available. The pressure sensor on A0 and the matrix are untouched by this change.

If you ever pick a pin other than D2, avoid the special-function pins: D0/D1
(Serial1), D4/D5 (CAN), D10–D13 (SPI; D13 also the onboard LED), A4/A5 (I²C). The
cleanly-free general-purpose pins are **D2, D3, D6, D7, D8, D9**. 1-Wire is polled
by DallasTemperature (no interrupt needed), but D2/D3 are interrupt-capable if that
ever matters.

### Why the external resistor (don't rely on the internal pull-up)

The UNO R4's Renesas RA4M1 has **software-enabled internal pull-ups**
(`pinMode(pin, INPUT_PULLUP)`), but they're **weak** (~25–50 kΩ) and **cannot**
substitute for the external 4.7 kΩ. 1-Wire is an open-drain bus that needs a stiff
pull-up to charge line capacitance and produce clean, fast rising edges (more so as
the cable lengthens); the weak internal pull-up gives sloppy edges and intermittent
or failed reads, and the OneWire library tri-states the pin for signaling rather
than depending on the idle-high pull-up. So **keep the external 4.7 kΩ to 5V.**
Note also there is **no internal pull-*down*** on the R4 — the Arduino Renesas core
exposes only `INPUT`/`OUTPUT`/`INPUT_PULLUP`/`OUTPUT_OPENDRAIN` (no `INPUT_PULLDOWN`);
irrelevant here since 1-Wire needs a pull-up, but worth knowing.

- UNO R4 WiFi I/O is 5 V; DS18B20 runs 3.0–5.5 V, so 5 V + 4.7 kΩ to 5 V is
  correct. Pull DQ up to the **same 5 V rail** that powers VDD, not 3.3 V.
- For a long run, twist DQ with GND and drop the pull-up to **2.2–3.3 kΩ** (a
  *stronger* external resistor — never the internal pull-up).

---

## 6. Arduino firmware changes

### Architecture constraint (important)

`ArduinoPSI_Domestic/ArduinoPSI_impl.h` is a **symlink** to
`ArduinoPSI_BoilerLoop/ArduinoPSI_impl.h` — there is ONE shared implementation
file, and **both** boards compile from it. So the DS18B20 code must be
**compile-guarded** so it activates only on the DHW board. We gate on
`ONE_WIRE_BUS`, defined only in `ArduinoPSI_Domestic.ino`; the hydronic board
(10.0.0.114) never sees the temp code and its `{'psi' : ...}` response is
unchanged. Edit the shared `impl.h` once (the symlink propagates).

### Libraries (add to each board's `libraries/` folder for arduino-cli)
- `OneWire` (Paul Stoffregen)
- `DallasTemperature` (Miles Burton)

### `ArduinoPSI_Domestic.ino` — define the pin (this sketch only)
```cpp
#define SENSOR_MAX_PSI 200.0f
#define SENSOR_MAX_V   5.0f

#define ONE_WIRE_BUS   2          // DS18B20 DQ on D2 — enables temp on this board only

#include "ArduinoPSI_impl.h"
```

### `ArduinoPSI_impl.h` (shared) — guarded additions

Top of file, after the existing includes (`WiFiS3.h`, `arduino_secrets.h`, …):
```cpp
#ifdef ONE_WIRE_BUS
#include <OneWire.h>
#include <DallasTemperature.h>
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature ds18b20(&oneWire);
float         tempF        = DEVICE_DISCONNECTED_F;  // last good read
unsigned long lastTempRead = 0;
#endif
```

In `setup()`, after `analogReadResolution(14);`:
```cpp
#ifdef ONE_WIRE_BUS
  ds18b20.begin();
  ds18b20.setResolution(12);             // 0.0625 °C
  ds18b20.setWaitForConversion(false);   // non-blocking — don't stall loop()/HTTP
  ds18b20.requestTemperatures();         // kick off the first conversion
#endif
```

In `loop()`, alongside the existing `millis()`-based display timer (read the
finished conversion and start the next every ~3 s — never blocks):
```cpp
#ifdef ONE_WIRE_BUS
  if (millis() - lastTempRead >= 3000) {
    tempF = ds18b20.getTempFByIndex(0);  // result of the previous request
    ds18b20.requestTemperatures();       // start the next (returns immediately)
    lastTempRead = millis();
  }
#endif
```

Replace the single-field response builder (currently
`sprintf(jsonResponse, "{'psi' : %f}", psi);`):
```cpp
#ifdef ONE_WIRE_BUS
          sprintf(jsonResponse, "{'psi' : %f, 'temp' : %f}", psi, tempF);
#else
          sprintf(jsonResponse, "{'psi' : %f}", psi);
#endif
          client.println(jsonResponse);
```
`jsonResponse[100]` has room (`{'psi' : 13.687136, 'temp' : 120.500000}` ≈ 40
chars). Keep single quotes — pivac parses with `ast.literal_eval`, not JSON.

Resulting DHW response:
```
<!DOCTYPE HTML>
<html>
{'psi' : 13.687136, 'temp' : 120.500000}
</html>
```

### Disconnected-probe behaviour
`getTempFByIndex(0)` returns `DEVICE_DISCONNECTED_F` (≈ -196.6 °F) if the probe
is missing/miswired — it publishes through pivac as an obviously-wrong value
(≈ 146 K after conversion) that the "loop cold" alert (§8.3) catches, rather
than silent garbage. Verify `ds18b20.getDeviceCount() == 1` after wiring.

### Deploy (Mac-only)
WiFi creds: a gitignored `arduino_secrets.h` must exist in the sketch folder
(copy from `arduino_secrets.h.example`, fill in `SECRET_SSID`/`SECRET_PASS`).
Only the DHW board needs reflashing; the hydronic board is untouched.
```bash
arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi \
  --libraries ArduinoPSI_Domestic/libraries ArduinoPSI_Domestic
arduino-cli upload  --fqbn arduino:renesas_uno:unor4wifi \
  --port /dev/cu.usbmodem<id> ArduinoPSI_Domestic
```
(`arduino-cli board list` for the port.)

---

## 7. pivac changes

### 7a. Generalise `pivac/ArduinoSensor.py` (multi-field + temperature→Kelvin)

Replace the hardcoded single-`psi` logic with a loop over `config["inputs"]`,
where each input key is the **field name in the Arduino's response dict**.
Inputs marked `type: temperature` are converted to Kelvin and emitted at
`{sk_path}.{outname}.temperature` (matching the OneWireTherm convention);
everything else passes through as `{sk_path}.{outname}` exactly as today
(backward compatible with both existing pressure services).

```python
import requests
import logging
import re
import ast
import pytemperature

logger = logging.getLogger(__name__)


def _to_kelvin(value, scale):
    if scale == "kelvin":
        return float(value)
    if scale == "celsius":
        return pytemperature.c2k(float(value))
    return pytemperature.f2k(float(value))   # default: fahrenheit


def status(config={}, output="default"):
    result = {}

    if "ipaddr" not in config:
        logger.error("No IP address specified in config file.")
        raise ValueError
    if "inputs" not in config:
        logger.error("No inputs specified in config file.")
        raise ValueError
    sensors = config["inputs"]

    if output == "signalk":
        from pivac import sk_init_deltas, sk_add_source, sk_add_value
        deltas = sk_init_deltas()
        sk_source = sk_add_source(deltas)

    try:
        r = requests.get("http://%s" % config["ipaddr"], timeout=2)
        logger.debug("Got request: %s" % r.text)
        # Single-quoted pseudo-JSON inside HTML, e.g. {'psi' : 18.4, 'temp' : 120.5}.
        # ast.literal_eval (not json.loads): single-quoted keys are Python, not JSON.
        parsed = ast.literal_eval(re.findall(r'.*\{.*\}', r.text)[0])

        for field, scfg in sensors.items():
            if field not in parsed:
                logger.warning("Arduino at %s: field '%s' missing from response %s",
                               config["ipaddr"], field, parsed)
                continue
            raw = parsed[field]
            outname = scfg["outname"]
            sk_path = scfg["sk_path"]          # propagated from top level unless overridden

            if scfg.get("type") == "temperature":
                scale = scfg.get("scale", "fahrenheit")
                if output == "signalk":
                    sk_add_value(sk_source, "%s.%s.temperature" % (sk_path, outname),
                                 int(round(_to_kelvin(raw, scale))))
                else:
                    result[outname] = raw
            else:
                if output == "signalk":
                    sk_add_value(sk_source, "%s.%s" % (sk_path, outname), raw)
                else:
                    result[outname] = raw

    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        logger.warning("Arduino at %s unreachable (timeout)" % config["ipaddr"])
    except Exception as e:
        logger.warning("Arduino at %s: failed to parse response: %s" % (config["ipaddr"], e))

    if output == "signalk":
        logger.debug("deltas = %s" % deltas)
        return deltas
    else:
        logger.debug("result = %s" % result)
        return result
```

**Backward-compat check:** the existing `inputs: {psi: {outname: psi}}` (with
`sk_path` propagated) has no `type`, so it takes the pass-through branch and
still emits `{sk_path}.psi` — identical to today. The `DEVICE_DISCONNECTED_F`
sentinel (≈ -196.6 °F) converts to ~146 K and reads as an obviously-wrong,
plottable value (and trips the "loop cold" alert), rather than crashing.

### 7b. Config — add the `temp` input to the DHW section (`pivac.ArduinoPSI`, .114)

One service, one HTTP GET, two values. The per-input `sk_path` override is
preserved by `propagate_defaults` (it only fills when absent). The DHW board is
`pivac.ArduinoPSI` / `10.0.0.114` (inverted legacy name — see the §2 correction).
Edit `/etc/pivac/config.yml` (live) and mirror in `config/config.yml.sample`:

```yaml
pivac.ArduinoPSI:                                # the DHW board (.114), inverted name
    description: DHW pressure + hot-water recirc-loop temperature (Arduino 10.0.0.114)
    module: pivac.ArduinoSensor
    enabled: true
    ipaddr: 10.0.0.114
    sk_path: electrical.ac.arduinoPSI            # default for non-override inputs (psi)
    propagate:
        - sk_path
    daemon_sleep: 1
    inputs:
        psi:
            outname: psi
        temp:
            outname: recirc
            type: temperature
            scale: fahrenheit                    # the unit the Arduino emits
            sk_path: environment.inside.hvac.dhw # override → dedicated DHW namespace
```

Resulting Signal K paths:
- `electrical.ac.arduinoPSI.psi` (unchanged — DHW pressure)
- `environment.inside.hvac.dhw.recirc.temperature` (**new**, Kelvin)

> **DECIDED (2026-05-31):** dedicated `dhw.recirc` namespace →
> `environment.inside.hvac.dhw.recirc.temperature` (outname `recirc`, sk_path
> override `environment.inside.hvac.dhw`). Chosen over `CIRC`/`DHWRECIRC` to
> avoid any conceptual clash with the `CRW` hydronic sensor; it sits in its own
> DHW sub-namespace rather than alongside IN/CRW/OUT.

**Alternative (separate service):** instead of adding `temp` to
`ArduinoThermPSI`, add a standalone `pivac.CircLoopTemp` section (same
`module: pivac.ArduinoSensor`, same `ipaddr: 10.0.0.219`, only the `temp`
input) with its own `pivac-circ-temp.service`. Pros: independent
enable/disable and restart. Cons: a second HTTP GET to the same Arduino each
cycle and another unit file. Prefer the single-section approach unless you want
the isolation.

> **DECIDED (2026-05-31):** single config section — add `temp` to
> `ArduinoThermPSI`. No separate service.

---

## 8. Surfacing — Grafana + WilhelmSK

1. **Grafana panel:** add `environment.inside.hvac.dhw.recirc.temperature` (InfluxQL
   measurement = full path, field = `value`) to the existing hydronic
   water-temp panel, alongside In/CRW/Out. Convert K→°F in the panel like the
   others.
2. **Freshness alert:** add a `circ-temp-stale` rule to
   `grafana/provisioning/alerting/sensor-freshness.yaml` (group
   `sensor-data-freshness`), copy of `outside-onewire-stale` but
   `measurement: environment.inside.hvac.dhw.recirc.temperature`, `noDataState:
   Alerting`, routing to `graph-bridge`. (Temps are Kelvin, so reuse the
   `value < 100` never-true sentinel.)
3. **Pump-health alert — DEFERRED (2026-05-31).** The pump runs **on demand /
   by aquastat**, so the loop is intentionally cold much of the time; a static
   `circ-loop-cold` threshold (the original 90 °F / 20 min idea) would
   false-alarm constantly and is therefore *not* being built now. Instead:
   deploy the sensor with only the freshness alert (§8.2), observe the real
   hot/cold duty cycle for a few days, then design a duty-cycle-aware health
   signal — e.g. "loop never reached hot in the last 24 h", or a cold check
   gated to a known recirc window. Revisit once we have data.
   > **DECIDED (2026-05-31):** schedule = on-demand/aquastat; threshold =
   > observe-first. No cold-threshold alert in the initial deploy.
4. **WilhelmSK (optional):** add a WaterTempGauge for the `dhw.recirc` path to
   `iphone.wlyt` (see pivac CLAUDE.md "WilhelmSK layout file" for the
   import dance).

---

## 9. Deployment runbook (order of operations)

Do the firmware first so the new field exists before pivac looks for it (the
generalised module just warns on a missing field, so order is not strictly
required, but this avoids noise).

1. **Wire** the DS18B20 to the DHW board **`10.0.0.114`** per §5 (power the Arduino down first).
2. **Flash** the updated `ArduinoPSI_Domestic` sketch from the Mac; confirm
   `curl http://10.0.0.114` returns both `'psi'` and `'temp'`. *(Done 2026-06-01.)*
3. **pivac code:** land the generalised `ArduinoSensor.py` (feature branch +
   PR). Before deploy, run the backward-compat tests in §10.
4. **Config:** edit `/etc/pivac/config.yml` (§7b) and `config.yml.sample`.
   Back up the live config first:
   `sudo cp /etc/pivac/config.yml /etc/pivac/config.yml.bak-$(date +%F-%H%M%S)`.
5. **Deploy + restart** the one service (the DHW board's service is
   **`pivac-arduino-psi`**, the inverted name):
   `git pull && sudo systemctl restart pivac-arduino-psi`
   (no new unit file needed — same service, extra input). If you chose the
   separate-service alternative, install `pivac-circ-temp.service` and
   `daemon-reload` first.
6. **Grafana:** add the panel + the freshness alert rule (§8.2; the pump-health
   alert §8.3 is deferred); deploy per pivac CLAUDE.md
   "Deployment after editing the YAMLs" (copy YAML, chown root:grafana, chmod
   640, `systemctl restart grafana-server`).
7. **Docs:** update pivac CLAUDE.md (Active Services table note, Signal K paths,
   the new alert in the alerting section) and this plan's Status checklist.

---

## 10. Verification & test plan

**Before deploy (standalone, no Signal K):**
```bash
source ~/pivac-venv/bin/activate
# regression: both existing pressure Arduinos still parse with the new module
python -c "import pivac; pivac.set_config('/etc/pivac/config.yml'); \
import pivac.ArduinoSensor as m, json; \
print(json.dumps(m.status({'ipaddr':'10.0.0.114','inputs':{'psi':{'outname':'psi','sk_path':'electrical.ac.arduinoPSI'}}}), indent=2))"
# new: temp field from the DHW Arduino (after firmware flashed)
python -c "import pivac.ArduinoSensor as m, json; \
print(json.dumps(m.status({'ipaddr':'10.0.0.114','inputs':{'temp':{'outname':'recirc','type':'temperature','scale':'fahrenheit','sk_path':'environment.inside.hvac.dhw'}}}, 'signalk'), indent=2))"
```
Expect the pressure call to return the same `psi` value as before, and the temp
call to return a Kelvin delta at `environment.inside.hvac.dhw.recirc.temperature`.

**After deploy:**
```bash
# fresh value flowing to Signal K
curl -s http://localhost:3000/signalk/v1/api/vessels/self/environment/inside/hvac/dhw/recirc/temperature | python3 -m json.tool
# pressure still publishing (no regression)
journalctl -u pivac-arduino-psi -n 30 --no-pager
```
- Confirm the `dhw.recirc` value is plausible for a hot recirc loop and timestamp
  is fresh.
- Sanity-check by briefly comparing the probe reading to a known reference.

---

## 11. Rollback

- **pivac:** revert the `ArduinoSensor.py` change (the module is shared — a bad
  parse would affect both pressure services, hence the §10 regression test).
  Restore `/etc/pivac/config.yml` from the `.bak` and restart
  `pivac-arduino-psi` (the DHW board's service, .114).
- **Grafana:** delete the two new rules from `sensor-freshness.yaml`, redeploy.
- **Firmware:** re-flash the previous sketch (keep the prior `.ino` tagged in
  the Mac repo). The DS18B20 wiring can stay; an unused field is harmless.

---

## 12. Decisions (RESOLVED 2026-05-31)

1. **Cable run** — ✅ **Reuse the DHW Arduino `10.0.0.114` (`pivac.ArduinoPSI`).** Run
   confirmed comfortable; coupling trade-off accepted (§3). *(Originally written as
   `.219` — corrected 2026-06-01, see §2 banner.)*
2. **Naming** — ✅ **`dhw.recirc` namespace** → `environment.inside.hvac.dhw.recirc.temperature`
   (outname `recirc`, sk_path override `environment.inside.hvac.dhw`). Avoids any
   clash with `CRW`; own DHW sub-namespace, not alongside IN/CRW/OUT (§7b).
3. **Recirc schedule** — ✅ **On-demand / aquastat.** Loop is intentionally cold
   much of the time.
4. **Cold-alert threshold** — ✅ **Observe-first, no static threshold.** Combined
   with #3, the naive cold alert is **deferred**; ship freshness-only, gather
   duty-cycle data, then design a smarter health signal (§8.3).
5. **Single section vs separate service** — ✅ **Single section** — add `temp` to
   `pivac.ArduinoPSI` (the DHW board, .114). No separate service.

---

## 13. Status checklist

- [x] Cable-run / location confirmed — reuse 10.0.0.219 (§12.1)
- [x] Naming + schedule + threshold decided (§12.2–12.5)
- [x] DS18B20 wired to the DHW board 10.0.0.114 (§5) *(2026-06-01)*
- [x] Firmware updated + flashed; `curl http://10.0.0.114` shows `'temp'` (§6) *(2026-06-01)*
- [x] `ArduinoSensor.py` generalised + regression-tested (§7a, §10) — PR #59
- [x] Config **sample** updated (§7b) — PR #59; live `/etc/pivac/config.yml` still TODO
- [ ] Live config edited (`pivac.ArduinoPSI`, .114); service `pivac-arduino-psi` restarted; `dhw.recirc` publishing fresh Kelvin to SK (§9.4–9.5, §10)
- [ ] Grafana panel added (§8.1)
- [x] Freshness alert `circ-temp-stale` added (§8.2) — PR #59 *(deploy to Pi only after sensor is live — noDataState: Alerting)*
- [ ] Pump-health alert designed from observed data (§8.3, deferred)
- [x] CLAUDE.md Arduino role/IP map corrected (master, 2026-06-01); close out remaining items at deploy
