# Plan — Hot-Water Circulator-Loop Temperature Monitoring

**Status:** DRAFT / not yet implemented · **Created:** 2026-05-31 · **Owner:** David

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

**Success criteria:** `environment.inside.hvac.CIRC.temperature` publishes to
Signal K every poll cycle in Kelvin; Grafana plots it; an email fires if it
goes stale (>30m) or drops below the "pump probably dead" threshold.

---

## 2. Current-state facts (grounded 2026-05-31)

- The DHW pressure Arduino at **`10.0.0.219`** (UNO R4 WiFi) currently serves:
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
  `pivac-arduino-psi` (10.0.0.114) and `pivac-arduino-therm-psi` (10.0.0.219).
- Live config shape for the DHW Arduino (`/etc/pivac/config.yml`):
  ```yaml
  pivac.ArduinoThermPSI:
      module: pivac.ArduinoSensor
      enabled: true
      ipaddr: 10.0.0.219
      sk_path: electrical.ac.arduinoThermPSI
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
- The Arduino firmware repo (`git@github.com:dglcinc/Arduino.git`, default
  branch `main`): active compile/upload copy is on the **Mac** at
  `~/OneDrive - DGLC/Claude/github/Arduino/`; a **read-only reference clone is
  now on the Pi** at `~/github/Arduino`. Compile + upload is **Mac-only** (USB,
  no OTA).
- Firmware structure: two sketches, `ArduinoPSI_BoilerLoop` (hydronic,
  10.0.0.114) and `ArduinoPSI_Domestic` (DHW, 10.0.0.219). They share ONE
  implementation file — `ArduinoPSI_Domestic/ArduinoPSI_impl.h` is a **symlink**
  to `ArduinoPSI_BoilerLoop/ArduinoPSI_impl.h`. The `.ino` files differ only in
  `SENSOR_MAX_PSI` / `SENSOR_MAX_V`. The HTTP response is built with
  `sprintf(jsonResponse, "{'psi' : %f}", psi)` into a `char jsonResponse[100]`.
- WiFi creds live in a **gitignored `arduino_secrets.h`** (`SECRET_SSID` /
  `SECRET_PASS`) per sketch folder — NOT hardcoded in the `.ino` (corrects an
  older note). Hardware: UNO R4 WiFi, analog sensor on A0 @ 14-bit, LED-matrix
  display, `WiFiS3`.

---

## 3. Architecture decision — reuse the DHW Arduino (10.0.0.219)

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

> **Decision needed from David:** confirm the recirc-loop sensor location is a
> reasonable cable run from the `10.0.0.219` enclosure. If not, switch to a new
> Arduino (see §9 alternative).

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

Notes:
- UNO R4 WiFi I/O is 5 V; DS18B20 runs 3.0–5.5 V, so 5 V + 4.7 kΩ to 5 V is
  correct.
- Pick any unused digital pin for `ONE_WIRE_BUS`; **D2** is used throughout this
  plan. Make sure it doesn't collide with the pin the pressure sensor or any
  status LED already uses in the existing sketch.
- For a long run, twist DQ with GND and consider dropping the pull-up to
  2.2–3.3 kΩ.
- The pressure sensor stays on its existing analog pin, untouched.

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

### 7b. Config — add the `temp` input to the existing DHW section

One service, one HTTP GET, two values. The per-input `sk_path` override is
preserved by `propagate_defaults` (it only fills when absent). Edit
`/etc/pivac/config.yml` (live) and mirror in `config/config.yml.sample`:

```yaml
pivac.ArduinoThermPSI:
    description: DHW pressure + hot-water recirc-loop temperature (shared Arduino 10.0.0.219)
    module: pivac.ArduinoSensor
    enabled: true
    ipaddr: 10.0.0.219
    sk_path: electrical.ac.arduinoThermPSI       # default for non-override inputs (psi)
    propagate:
        - sk_path
    daemon_sleep: 1
    inputs:
        psi:
            outname: psi
        temp:
            outname: CIRC
            type: temperature
            scale: fahrenheit                    # the unit the Arduino emits
            sk_path: environment.inside.hvac     # override → groups with IN/CRW/OUT
```

Resulting Signal K paths:
- `electrical.ac.arduinoThermPSI.psi` (unchanged)
- `environment.inside.hvac.CIRC.temperature` (**new**, Kelvin)

> **Decision needed from David:** the outname/path. `CIRC` →
> `environment.inside.hvac.CIRC.temperature` groups it with the existing
> hydronic gauges. Alternatives: `DHWRECIRC`, or a dedicated
> `environment.inside.hvac.dhw.recirc` namespace. Also confirm `CIRC` doesn't
> clash conceptually with the existing `CRW` sensor.

**Alternative (separate service):** instead of adding `temp` to
`ArduinoThermPSI`, add a standalone `pivac.CircLoopTemp` section (same
`module: pivac.ArduinoSensor`, same `ipaddr: 10.0.0.219`, only the `temp`
input) with its own `pivac-circ-temp.service`. Pros: independent
enable/disable and restart. Cons: a second HTTP GET to the same Arduino each
cycle and another unit file. Prefer the single-section approach unless you want
the isolation.

---

## 8. Surfacing — Grafana + WilhelmSK

1. **Grafana panel:** add `environment.inside.hvac.CIRC.temperature` (InfluxQL
   measurement = full path, field = `value`) to the existing hydronic
   water-temp panel, alongside In/CRW/Out. Convert K→°F in the panel like the
   others.
2. **Freshness alert:** add a `circ-temp-stale` rule to
   `grafana/provisioning/alerting/sensor-freshness.yaml` (group
   `sensor-data-freshness`), copy of `outside-onewire-stale` but
   `measurement: environment.inside.hvac.CIRC.temperature`, `noDataState:
   Alerting`, routing to `graph-bridge`. (Temps are Kelvin, so reuse the
   `value < 100` never-true sentinel.)
3. **Pump-health alert (the point of this project):** add a `circ-loop-cold`
   threshold rule — fires when `environment.inside.hvac.CIRC.temperature` falls
   **below ~305 K (~90 °F)** sustained for, say, 15–30 min during a period the
   loop should be hot. That's the "pump lost prime / failed" signal → email so
   David can re-prime. `noDataState: OK` (the freshness rule covers no-data).
   Threshold and window need tuning once we see the loop's normal hot/cold
   range; treat 90 °F / 20 min as a starting guess.
   > **Decision needed:** does the recirc run 24/7, or on a schedule/timer? If
   > scheduled, the cold-alert needs to respect the "should be hot" window
   > (Grafana mute timing or a time-of-day condition) to avoid false alarms
   > during intentional off periods.
4. **WilhelmSK (optional):** add a WaterTempGauge for the CIRC path to
   `iphone.wlyt` (see pivac CLAUDE.md "WilhelmSK layout file" for the
   import dance).

---

## 9. Deployment runbook (order of operations)

Do the firmware first so the new field exists before pivac looks for it (the
generalised module just warns on a missing field, so order is not strictly
required, but this avoids noise).

1. **Wire** the DS18B20 to `10.0.0.219` per §5 (power the Arduino down first).
2. **Flash** the updated sketch from the Mac; confirm
   `curl http://10.0.0.219` returns both `'psi'` and `'temp'`.
3. **pivac code:** land the generalised `ArduinoSensor.py` (feature branch +
   PR). Before deploy, run the backward-compat tests in §10.
4. **Config:** edit `/etc/pivac/config.yml` (§7b) and `config.yml.sample`.
   Back up the live config first:
   `sudo cp /etc/pivac/config.yml /etc/pivac/config.yml.bak-$(date +%F-%H%M%S)`.
5. **Deploy + restart** the one service:
   `git pull && sudo systemctl restart pivac-arduino-therm-psi`
   (no new unit file needed — same service, extra input). If you chose the
   separate-service alternative, install `pivac-circ-temp.service` and
   `daemon-reload` first.
6. **Grafana:** add the panel + the two alert rules; deploy per pivac CLAUDE.md
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
print(json.dumps(m.status({'ipaddr':'10.0.0.219','inputs':{'temp':{'outname':'CIRC','type':'temperature','scale':'fahrenheit','sk_path':'environment.inside.hvac'}}}, 'signalk'), indent=2))"
```
Expect the pressure call to return the same `psi` value as before, and the temp
call to return a Kelvin delta at `environment.inside.hvac.CIRC.temperature`.

**After deploy:**
```bash
# fresh value flowing to Signal K
curl -s http://localhost:3000/signalk/v1/api/vessels/self/environment/inside/hvac/CIRC/temperature | python3 -m json.tool
# pressure still publishing (no regression)
journalctl -u pivac-arduino-therm-psi -n 30 --no-pager
```
- Confirm the CIRC value is plausible for a hot recirc loop and timestamp is
  fresh.
- Sanity-check by briefly comparing the probe reading to a known reference.

---

## 11. Rollback

- **pivac:** revert the `ArduinoSensor.py` change (the module is shared — a bad
  parse would affect both pressure services, hence the §10 regression test).
  Restore `/etc/pivac/config.yml` from the `.bak` and restart
  `pivac-arduino-therm-psi`.
- **Grafana:** delete the two new rules from `sensor-freshness.yaml`, redeploy.
- **Firmware:** re-flash the previous sketch (keep the prior `.ino` tagged in
  the Mac repo). The DS18B20 wiring can stay; an unused field is harmless.

---

## 12. Open decisions for David

1. **Cable run** — is the recirc-loop sensor location a comfortable run from the
   `10.0.0.219` enclosure? (If not → new dedicated Arduino, §3.)
2. **Naming** — `CIRC` / `environment.inside.hvac.CIRC.temperature` OK, or
   prefer `DHWRECIRC` / a `dhw.recirc` namespace? Any clash with `CRW`?
3. **Recirc schedule** — 24/7 or on a timer? Drives the pump-cold alert's
   "should be hot" window (§8.3).
4. **Cold-alert threshold** — start at ~90 °F / 20 min, then tune from observed
   data. Agree on a starting point.
5. **Single section vs separate service** — add `temp` to `ArduinoThermPSI`
   (recommended) or a standalone `pivac-circ-temp` service?

---

## 13. Status checklist

- [ ] Cable-run / location confirmed (decision §12.1)
- [ ] Naming + schedule + threshold decided (§12.2–12.4)
- [ ] DS18B20 wired to 10.0.0.219 (§5)
- [ ] Firmware updated + flashed; `curl` shows `'temp'` (§6)
- [ ] `ArduinoSensor.py` generalised + regression-tested (§7a, §10) — PR: ____
- [ ] Config updated (live + sample) (§7b)
- [ ] Service restarted; CIRC publishing fresh Kelvin to SK (§9.5, §10)
- [ ] Grafana panel added (§8.1)
- [ ] Freshness + pump-cold alerts added (§8.2–8.3) — PR: ____
- [ ] CLAUDE.md updated; this checklist closed out
