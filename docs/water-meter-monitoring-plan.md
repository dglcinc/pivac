# Domestic Water Consumption Monitoring — Implementation Plan

**Status:** DRAFT FOR REVIEW — 2026-06-15
**Goal:** Add a new pivac data source that reads the house's **Sensus iPerl** domestic water meter over radio, publishes consumption/flow to Signal K, and plots it in Grafana.

This plan is structured so you can sign off (or redirect) on the open decisions in §1 before any code is written. Everything below §1 assumes the **recommended** answers to those decisions; if you pick differently, the affected sections are called out.

---

## 0. What we're working with

| Item | Detail |
|------|--------|
| Meter | Sensus **iPerl** domestic water meter |
| Radio protocol | **Wireless M-Bus (wM-Bus)**, EN 13757-4 — *not* the North-American SCM/rtlamr protocol |
| Link mode | **T1** (meter is a one-way transmitter; broadcasts every **4–8 s**) |
| Frequency | **868.95 MHz** (see §1.4 — you noted "858 MHz"; the iPerl/wM-Bus default is 868.95) |
| Encryption | **AES-128, CBC-with-IV** |
| Default AES key | `E6C88800DEB868C0D6A84880CE982840` (the documented iPerl factory key) |
| New MCU | Arduino **UNO R4 WiFi** ("same model as the other two") — Renesas RA4M1 main MCU **at 5 V logic** + ESP32-S3 WiFi coprocessor |
| Radio | **CC1101** sub-GHz transceiver (3.3 V **only** — 5 V destroys it) |
| Level shifter | HiLetgo 4-channel bidirectional (BSS138) 3.3 V↔5 V |
| Carrier board | DIYables breadboard shield for Uno |

**Key research finding:** the iPerl + that exact default key is the **wM-Bus** ecosystem, which is mature and well-trodden. The reference implementations are:

- **`wmbusmeters/wmbusmeters`** — canonical Linux daemon; has a tested **iPerl driver** and the AES-CBC-IV decrypt. Runs on a Raspberry Pi and supports a CC1101 over SPI directly.
- **`SzczepanLeon/esphome-components`** (the `wmbus` component) — CC1101 + ESP, decodes/decrypts iPerl telegrams natively; the decode C++ is portable reference code.
- **`LSatan/SmartRC-CC1101-Driver-Lib`** and **`jgromes/RadioLib`** — CC1101 drivers. RadioLib supports the Renesas UNO R4 architecture.
- **`alex-icesoft/esp32_cc1101_wmbus`** — minimal "receive wM-Bus T1 frames via CC1101" reference (ESP32/PlatformIO).
- **`mfurga/cc1101`** — clean Arduino CC1101 library.

The whole proven decode/decrypt stack targets **ESP/Linux**, not the Renesas RA4M1. That fact drives decision §1.2.

---

## 1. Open decisions (please review before implementation)

### 1.1 Reuse the existing `pivac.ArduinoSensor` module, or write a dedicated `pivac.WaterMeter`?

The existing two pressure boards already publish a single-quoted JSON dict over a tiny HTTP server (e.g. `{'psi' : 18.4, 'temp' : 120.5}`), and `pivac.ArduinoSensor` polls `http://<ip>/`, parses it, and maps each field to a Signal K path (see `pivac/ArduinoSensor.py`). A board that exposes `{'volume_m3' : 1234.567, 'flow_lph' : 0, 'rssi' : -72}` would work with **zero new Python** — just a new config block pointing `module: pivac.ArduinoSensor`.

You asked specifically for a *new module*. A dedicated module is worth it only if pivac needs to do real work the board can't/shouldn't: deriving flow from the totalizer, decoding alarm/leak/tamper flags, validating the meter ID, or — under §1.2 Strategy B — doing the actual wM-Bus decrypt on the Pi.

- **Recommended:** decide this *together with* §1.2. If the board emits clean decoded values (Strategy A), reuse `ArduinoSensor` and skip a new module. If the Pi does the decode (Strategy B), write `pivac.WaterMeter`.

### 1.2 Where does the wM-Bus decode + AES decrypt run? (the central risk)

The radio capture is easy on the R4; the **3-of-6 decode + frame assembly + AES-128-CBC decrypt + iPerl payload parse** is the hard part, and every proven implementation runs on ESP32 or Linux, *not* the RA4M1.

| | **Strategy A — full decode on the R4 WiFi** | **Strategy B — "dumb radio", decode on the Pi** *(recommended)* | **Strategy C — no Arduino at all** |
|---|---|---|---|
| Arduino does | RadioLib CC1101 RX → port 3-of-6 + frame assembly + AES (tiny-AES-c / RA4M1 SCE) + iPerl parse → serve clean JSON | RadioLib CC1101 RX → serve **raw telegram hex** (+ RSSI) over HTTP/MQTT | nothing — CC1101 wires straight to the Pi's 3.3 V SPI |
| Pi / pivac does | Poll JSON, emit deltas (reuse `ArduinoSensor`) | New `pivac.WaterMeter`: fetch raw hex, run decode+decrypt+parse (port `wmbusmeters` logic in Python, or shell out to `wmbusmeters`), emit deltas | Run `wmbusmeters` daemon; thin pivac module tails its output → deltas |
| Fits existing pivac poll pattern | **Best** (identical to pressure boards) | Good (new module, but normal HTTP poll) | Different (daemon, not a board) |
| Risk / effort | **Highest** — port wM-Bus + AES to RA4M1; unproven there | **Low–moderate** — hard crypto stays in proven `wmbusmeters` on the Pi; Arduino stays a "minimal HTTP server" like the others | **Lowest** — `wmbusmeters` natively supports CC1101-on-Pi |
| Uses your Arduino + parts | ✅ | ✅ | ❌ (parts unused) |

- **Recommended: Strategy B.** It keeps the Arduino in the same "dumb minimal HTTP server" role as the other two boards (matching their character and your hardware purchase), while the fragile decrypt/parse runs where it's already proven — `wmbusmeters` on the Pi. Strategy A is the cleanest *integration* fit but carries the real risk of porting wM-Bus+AES to the Renesas chip. Strategy C is listed for honesty (lowest risk) but is set aside because you explicitly want to deploy the Arduino.
- This plan is written for **Strategy B** below, with Strategy-A deltas noted inline.

### 1.3 Will the default AES key actually decrypt *your* meter?

The vendor line (confirmed in `wmbusmeters` issue threads) is that iPerl uses **one shared mBus key for all meters**, which is why the factory default circulates — but some users still hit "decrypted content failed check." We can't know until we listen. **Decryption success is gated on the `2F2F` marker** appearing at the start of the decrypted payload; its presence = right key, its absence = wrong key. There is a discovery/validation step in §5 for exactly this. If the default key fails, the fallback is to request the key from the water utility (you noted you don't have one).

### 1.4 Frequency: confirm 868.95 MHz and the CC1101 band variant

You wrote 858 MHz; the iPerl/wM-Bus T1 standard is **868.95 MHz**. Two things to verify before/at first power-on: (a) the CC1101 module is the **868/900 MHz** variant, **not** the 433 MHz one — buying 433 is the single most common failure and it will *never* hear the meter; an **EBYTE E07-900M10S** (SMA antenna jack) is the recommended module. (b) The exact TX frequency — a quick spectrum scan or trying 868.95 / 868.3 confirms it.

---

## 2. Bill of materials (you already have these)

- Arduino UNO R4 WiFi
- CC1101 868/900 MHz module (confirm band — §1.4; recommend E07-900M10S w/ 868 MHz antenna)
- HiLetgo 4-channel BSS138 bidirectional logic level converter
- DIYables breadboard shield for Uno
- Jumper wires, 868 MHz antenna

---

## 3. Wiring diagram

### 3.1 The level-shifting problem, stated

The CC1101 is a **3.3 V** device; the UNO R4 WiFi drives **5 V** logic. So:

- **Arduino → CC1101 lines MUST be shifted down 5 V → 3.3 V** to avoid destroying the radio: **SCK, MOSI, CSN**.
- **CC1101 → Arduino lines are 3.3 V → 5 V**: **MISO, GDO0** (and optional GDO2). 3.3 V is *usually* read as logic-HIGH by the R4, but routing MISO through the shifter removes all doubt.

The 4-channel converter therefore carries the **whole SPI bus** (MOSI, MISO, SCK, CSN) — which is exactly why a 4-channel part fits. **GDO0** (the data/interrupt line wM-Bus reception depends on) is a 3.3 V→5 V output and connects **directly**; if it ever proves marginal on the R4 input, add a 5th shifted channel (a second converter) for it. GDO2 is typically unused for T1 reception.

### 3.2 Connection table

VCC for the CC1101 comes from the Arduino **3V3** pin. The level converter's **LV** side = 3.3 V (to CC1101), **HV** side = 5 V (to Arduino).

| CC1101 pin | → level converter (LV side) | HV side → Arduino UNO R4 | Notes |
|------------|----------------------------|--------------------------|-------|
| VCC        | — (direct)                 | **3V3**                  | 3.3 V power **only** — never 5 V |
| GND        | — (direct)                 | **GND**                  | common ground (incl. converter GND both sides) |
| SCK        | LV1                        | HV1 → **D13 (SCK)**      | 5 V→3.3 V down-shift (mandatory) |
| MOSI (SI)  | LV2                        | HV2 → **D11 (MOSI)**     | 5 V→3.3 V down-shift (mandatory) |
| MISO (SO)  | LV3                        | HV3 → **D12 (MISO)**     | 3.3 V→5 V up-shift (for reliable read) |
| CSN (CS)   | LV4                        | HV4 → **D10 (CS)**       | 5 V→3.3 V down-shift (mandatory) |
| GDO0       | — (direct)                 | **D2** (interrupt-capable)| 3.3 V→5 V; direct is OK, shift if marginal |
| GDO2       | — (unused)                 | —                        | not needed for T1 |

Level converter power: **LV = 3V3** (Arduino 3V3), **HV = 5V** (Arduino 5V), **GND** tied to Arduino GND on both sides.

> On the UNO R4, hardware SPI is fixed to **D11/D12/D13** (MOSI/MISO/SCK) and the ICSP header; only the CS pin is free to choose (D10 used here). GDO0 must be on an interrupt-capable pin — all R4 digital pins qualify.

### 3.3 ASCII layout

```
   Arduino UNO R4 WiFi (5V)            BSS138 4-ch converter           CC1101 (3.3V)
   ----------------------              ---------------------           -------------
   5V  ───────────────────────────────► HV  ◄─── LV ──────────────────► 3V3 ──► VCC
   GND ───────────────────────────────► GND(HV)  GND(LV) ─────────────► GND
   D13 SCK  ──────────────────► HV1 ───────────────── LV1 ───────────► SCK
   D11 MOSI ──────────────────► HV2 ───────────────── LV2 ───────────► MOSI (SI)
   D12 MISO ◄────────────────── HV3 ───────────────── LV3 ◄────────── MISO (SO)
   D10 CS   ──────────────────► HV4 ───────────────── LV4 ───────────► CSN
   D2  GDO0 ◄────────────────────────── (direct, 3.3V→5V) ──────────── GDO0
                                                                       ANT ──► 868 MHz antenna
```

Mount the CC1101 + converter on the DIYables shield; keep the antenna clear of the board and away from the boiler-room metal.

---

## 4. Arduino sketch (Strategy B — "dumb radio" forwarder)

A new sketch in the `~/github/Arduino` repo (its own sketch dir, alongside `ArduinoPSI_Domestic` / `ArduinoPSI_BoilerLoop`), reusing the existing boards' proven scaffolding: WiFi connect with the RA4M1 **watchdog + escalating reconnect + `NVIC_SystemReset()` fallback + `uptime_ms`** hardening that was added to the other two boards (Arduino PR #6).

**Responsibilities:**

1. **Init CC1101 via RadioLib** for wM-Bus **T1**: 868.95 MHz, ~103 kbps, 2-FSK, ~50 kHz deviation, ~270–325 kHz RX bandwidth, sync word for T1, GDO0 as async data / packet-ready interrupt. (Crib the register set from `alex-icesoft/esp32_cc1101_wmbus` / SzczepanLeon's CC1101 init — it's the same chip.)
2. **Capture frames** in the GDO0 ISR into a ring buffer; keep the most recent N raw telegrams (with capture time-since-boot and RSSI/LQI).
3. **Optionally pre-filter** to telegrams whose wM-Bus manufacturer/device-type bytes match Sensus iPerl, to cut HTTP payload size (full decode still happens on the Pi).
4. **Serve over WiFi**, matching the house pattern — a minimal HTTP server on `:80` returning a single-quoted dict line, e.g.:
   ```
   {'mfct':'SEN','id':'12345678','rssi':-72,'raw':'2C44...<hex>','age_ms':1840,'uptime_ms':3600000}
   ```
   (`raw` is the hex wM-Bus telegram; `id` is the meter ID parsed from the *unencrypted* header so the Pi can pick the right meter without decrypting.)

**Strategy-A delta:** instead of `raw`, the sketch would decrypt (tiny-AES-c or the RA4M1 SCE peripheral) and parse, emitting `{'volume_m3':1234.567,'flow_lph':0,'rssi':-72,'uptime_ms':...}`. This is the higher-risk port.

**Libraries:** `RadioLib` (CC1101, Renesas-supported) for radio; `WiFiS3` (built-in R4 WiFi) for networking; `tiny-AES-c` only under Strategy A.

**Bring-up checks:** serial prints `Watchdog armed.`; confirm CC1101 is detected (version register read); print every raw telegram + RSSI so we can eyeball that frames are arriving every 4–8 s.

---

## 5. Discovery & key validation (one-time, before wiring into pivac)

Done on the Pi (or a laptop) with `wmbusmeters`, before committing config:

1. Install `wmbusmeters` on the Pi (`apt` or build). It can listen via the Arduino's raw feed (Strategy B) or, for discovery only, a temporary CC1101-on-Pi / rtl-sdr.
2. Run in **scan/analyze mode** to list every meter ID heard. Identify ours (cross-check against the ID printed on the physical meter).
3. Add the iPerl with the default key and confirm the **`2F2F` check passes** (= correct key, decryption working). If it fails → the default key is wrong for this utility; escalate to requesting the key (decision §1.3).
4. Record the confirmed **meter ID**, **frequency**, and **key** — these go into the Pi-side config, **never into the repo** (same rule as the Tapo/RTSP and Graph secrets: live only in `/etc/pivac/config.yml`, mode-guarded).

---

## 6. New pivac module — `pivac.WaterMeter` (Strategy B)

New file `pivac/WaterMeter.py` implementing the standard `status(config={}, output="default")` contract.

**Flow:**

1. `requests.get("http://<ipaddr>/", timeout=2)` → parse the board's dict (same `ast.literal_eval` + regex approach as `ArduinoSensor`, since the boards emit single-quoted pseudo-JSON).
2. Select the telegram(s) matching the configured **meter ID**.
3. **Decode + decrypt + parse** the raw wM-Bus hex. Two implementation options, pick at build time:
   - **(a) Shell out to `wmbusmeters`** in `--analyze`/stdin mode, feeding the raw hex, and read back the JSON it emits (`total_m3`, `target_m3`, flow, alarm flags). Lowest-effort, reuses the tested driver.
   - **(b) Port the decode in Python** — 3-of-6 decode, frame assembly, `AES-128-CBC` via `cryptography`/`pycryptodome` with the IV built from the telegram header, then parse the iPerl DIF/VIF fields. More code, no external process.
   - **Recommended: (a)** for v1 — fastest to a trustworthy reading; revisit (b) only if the subprocess overhead matters at the poll cadence (it won't).
4. Emit Signal K deltas (via `sk_init_deltas` / `sk_add_source` / `sk_add_value`).

**Config block** (in `/etc/pivac/config.yml`; sample sketch in `config/config.yml.sample`):

```yaml
pivac.WaterMeter:
    description: Domestic water consumption from the iPerl meter via Arduino wM-Bus bridge
    enabled: true
    ipaddr: 10.0.0.XXX            # DHCP-by-MAC like the other boards; reserve in UniFi
    meter_id: "12345678"          # confirmed in §5
    aes_key_env: WATERMETER_KEY   # key read from env/secret file, NOT inline in config
    inputs:
        total_m3:
            sk_path: environment.water.domestic
            outname: consumption   # → environment.water.domestic.consumption  (m³ cumulative)
```

> **Secrets:** the AES key and meter ID are sensitive-ish; keep the key out of the repo. Either an `/etc/pivac/*.env` file (like `graph.env`) read by the service, or inline only in the un-committed `/etc/pivac/config.yml`. The sample file uses placeholders.

**Strategy-A delta:** if the board already decodes, no `pivac.WaterMeter` is needed — add a config block pointing `module: pivac.ArduinoSensor` with `inputs: {volume_m3: {sk_path: environment.water.domestic, outname: consumption}}`.

### 6.1 Signal K paths

Signal K has **no standard path for domestic-water consumption** (its `tanks.*` model is for tank *levels*, not metered throughput), so we use a custom namespace — consistent with how pivac already uses custom/non-standard paths (`environment.inside.hvac.dhw.recirc.temperature`, `electrical.emporia.*`).

| SK path | Value | Notes |
|---------|-------|-------|
| `environment.water.domestic.consumption` | number, **m³ cumulative** | the iPerl lifetime totalizer; monotonic. Flow is derived downstream (§7), not published, to avoid double sources of truth. |
| `environment.water.domestic.flowRate` *(optional)* | number | only if the iPerl telegram exposes a reliable instantaneous flow field; otherwise omit and derive in Grafana. |

Publishing the **totalizer** (not a pre-computed flow) is deliberate: it's the meter's ground truth, survives restarts, and lets InfluxDB/Grafana compute flow over any window with `difference()` / `derivative()`.

### 6.2 systemd service

New `scripts/systemd/pivac-watermeter.service`, copied from an existing `pivac-arduino-*.service`: user `pi`, `PIVAC_CFG=/etc/pivac/config.yml`, `Restart=always`, `RestartSec=10`. If Strategy B option (a) is used, ensure `wmbusmeters` is installed and on `PATH` for the service.

Then fold `pivac-watermeter` into the documented restart/stop lists in CLAUDE.md (Standard Deployment Procedure, SD-maintenance stop set, Checking Logs).

---

## 7. Grafana panel

Add a panel to the pivac dashboard JSON (`grafana/dashboards/*.json`, auto-provisioned — edit JSON, commit, `git pull` on the Pi). Datasource: the `pivac` bucket via the InfluxQL-compat datasource (`bdxaqnfllu5fkf`); measurement = the full SK path, field = `value`.

- **Primary panel — "Domestic Water Flow"**: time-series of flow derived from the totalizer. InfluxQL: `non_negative_difference(mean("value"))` on `environment.water.domestic.consumption`, grouped by a sensible window (e.g. `time(1m)`), unit L/min or m³/h.
- **Secondary (optional) — cumulative consumption**: raw totalizer as a stat/graph, plus a daily-usage bar via `non_negative_difference` over `time(1d)`.

Mirror the styling of the existing DHW panel so it sits naturally on the board.

**Freshness alert (optional, mirrors existing pattern):** a `watermeter-stale` rule in `grafana/provisioning/alerting/sensor-freshness.yaml` routing to the `graph-bridge` contact point — 30 m staleness on `environment.water.domestic.consumption`, same `value < <sentinel>` + `noDataState: Alerting` trick used by the other freshness alerts. (The meter transmits every 4–8 s, so true silence for 30 m is a real fault — board down, radio dead, or meter battery.) Defer until the feed is proven stable.

---

## 8. Implementation sequence

1. **Confirm §1 decisions** (board strategy, module-vs-reuse, frequency). ← gate
2. **Hardware**: wire per §3 on the DIYables shield; power on; confirm CC1101 detected over SPI.
3. **Sketch bring-up**: flash the radio-RX sketch; watch serial for T1 telegrams arriving every 4–8 s with sane RSSI.
4. **Discovery & key validation (§5)**: confirm meter ID + that the default key passes the `2F2F` check. **Hard gate** — if the key fails, stop and resolve §1.3 before building the rest.
5. **Arduino HTTP feed**: add the WiFi HTTP server (Strategy B raw-hex JSON); reserve a DHCP IP by MAC in UniFi; verify `curl http://<ip>/` from the Pi.
6. **pivac module (§6)**: write `pivac.WaterMeter` (or the `ArduinoSensor` reuse path), config block, systemd unit; verify deltas land in Signal K (`environment.water.domestic.consumption`).
7. **Grafana (§7)**: add the flow panel; confirm data plots; (later) add the freshness alert.
8. **Docs**: update `CLAUDE.md` — Active Services table, Current Modules, deployment/stop/log lists, SK paths; update the Arduino repo CLAUDE.md with the new board's MAC/IP/sketch.
9. **PRs**: pivac (module + service + Grafana + config sample + docs); Arduino repo (sketch). Branch + PR per workflow.

## 9. Risks & open questions (carried from §1)

- **R4/RA4M1 vs the ESP-centric wM-Bus ecosystem** — the reason Strategy B is recommended. If Strategy A is chosen, budget real time to port wM-Bus + AES to Renesas and validate on-board decrypt.
- **Default AES key may not decrypt this meter** (§1.3) — validated early in step 4; fallback is utility key request.
- **Exact TX frequency / CC1101 band** (§1.4) — confirm the 868/900 MHz module variant and scan the actual frequency.
- **Signal K has no standard water-consumption path** — using a documented custom path (§6.1).
- **Secrets handling** — AES key + meter ID stay out of the repo (§6).

## 10. Alternatives considered (not chosen)

- **Strategy C — CC1101 straight onto the Pi + `wmbusmeters` daemon, no Arduino.** Technically the lowest-risk, lowest-effort path (native 3.3 V SPI, no level shifter, `wmbusmeters` supports it out of the box). Set aside only because you want to deploy the Arduino and already have the parts. Worth keeping in mind as the bail-out if the Arduino radio path proves troublesome.

---

## Sources

- [MarkLabs — Sensus iPerl wM-Bus via CC1101 + ESPHome](https://marklabs.pl/en/sensus-iperl-water-meter-home-assistant-wmbus-cc1101-esphome/) (wiring, 868 MHz, 4–8 s interval, AES-128, E07-900M10S)
- [MarkLabs — iPerl meter ID & AES key config](https://marklabs.pl/en/sensus-iperl-esphome-yaml-meter-id-aes-key-configuration/)
- [wmbusmeters issue #253 — iPerl shared mBus key / decrypt failures](https://github.com/wmbusmeters/wmbusmeters/issues/253)
- [wmbusmeters issue #928 / #878 — Sensus iPerl driver discussion](https://github.com/wmbusmeters/wmbusmeters/issues/928)
- [SzczepanLeon/esphome-components — wmbus component (CC1101, T1/C1, 868.95 MHz)](https://github.com/SzczepanLeon/esphome-components)
- [alex-icesoft/esp32_cc1101_wmbus — T1-mode CC1101 receiver reference](https://github.com/alex-icesoft/esp32_cc1101_wmbus)
- [LSatan/SmartRC-CC1101-Driver-Lib](https://github.com/LSatan/SmartRC-CC1101-Driver-Lib)
- [jgromes/RadioLib — CC1101, Renesas UNO R4 support](https://github.com/jgromes/RadioLib)
- [mfurga/cc1101 — Arduino CC1101 library](https://github.com/mfurga/cc1101)
