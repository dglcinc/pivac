# Domestic Water Consumption Monitoring — Implementation Plan

**Status:** DRAFT FOR REVIEW — 2026-06-15 (rev 2)
**Goal:** Add a new pivac data source that reads the house's **Sensus iPerl** domestic water meter over radio, publishes consumption/flow to Signal K, and plots it in Grafana.

> **Architecture (rev 3): recommended = remote UNO R4 node over WiFi (Appendix A); Pi-direct kept as the alternative.** The meter is read over the air, so the receiver can live anywhere on WiFi. Two real constraints rule the production Pi *out* as the receiver host: (1) its GPIO header is already largely consumed by `pivac.GPIO` (BCM 17/27/22/5/6/13/26/16/12) + the 1-Wire bus, and (2) wiring a CC1101 to it means **powering down and opening up the live Signal K / InfluxDB / Grafana / nginx box**. A standalone **UNO R4 WiFi node** (the board you already have) running the CC1101 as a "dumb radio" that forwards raw telegrams over WiFi — with `wmbusmeters`/Python on the Pi doing the decode/decrypt — avoids both: no Pi GPIO, no disassembly, and it can sit near the meter for good reception. It also reuses the exact HTTP-poll pattern your two pressure boards already use. **Both receiver options remain fully documented:** the recommended node path is **Appendix A**; the Pi-direct path (CC1101 on the Pi GPIO + `wmbusmeters`) is the body §3–§4, retained as the alternative for when no node is wanted and the header/downtime are acceptable.

This plan is structured so you can sign off (or redirect) on the open decisions in §1 before any code is written.

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
| Host | **Raspberry Pi** `10.0.0.82` (the production pivac/SignalK/InfluxDB/Grafana box) — GPIO is **3.3 V**, native match for the radio |
| Radio | **CC1101** sub-GHz transceiver (3.3 V **only** — 5 V destroys it); use an **868 MHz** variant with an SMA antenna jack (e.g. EBYTE E07-900M10S) |
| ~~Arduino UNO R4 WiFi~~ | **Not used** (rev 2) — no physical meter connection to be near, so a remote node adds nothing |
| ~~HiLetgo level shifter / DIYables shield~~ | **Not used** (rev 2) — Pi GPIO is already 3.3 V |

**Key research finding:** the iPerl + that exact default key is the **wM-Bus** ecosystem, which is mature and well-trodden. The reference implementations are:

- **`wmbusmeters/wmbusmeters`** — canonical Linux daemon; has a tested **iPerl driver** and the AES-CBC-IV decrypt. Runs on a Raspberry Pi and supports a CC1101 over SPI directly.
- **`SzczepanLeon/esphome-components`** (the `wmbus` component) — CC1101 + ESP, decodes/decrypts iPerl telegrams natively; the decode C++ is portable reference code.
- **`LSatan/SmartRC-CC1101-Driver-Lib`** and **`jgromes/RadioLib`** — CC1101 drivers. RadioLib supports the Renesas UNO R4 architecture.
- **`alex-icesoft/esp32_cc1101_wmbus`** — minimal "receive wM-Bus T1 frames via CC1101" reference (ESP32/PlatformIO).
- **`mfurga/cc1101`** — clean Arduino CC1101 library.

The whole proven decode/decrypt stack targets **ESP/Linux**, not the Renesas RA4M1. That fact drives decision §1.2.

---

## 1. Open decisions (please review before implementation)

### 1.1 Architecture — RESOLVED: remote UNO R4 WiFi node (raw-forward), not the Pi

The receiver is read over the air, so where it physically sits is the whole question. Hanging the CC1101 off the production Pi's GPIO was the rev-2 plan, but two constraints rule it out:

1. **Pin contention** — `pivac.GPIO` already uses BCM 17/27/22/5/6/13/26/16/12 and `pivac.OneWireTherm` owns the 1-Wire bus. Even where SPI0 is free, the header is crowded and the live config claims more than the sample.
2. **Production downtime + physical risk** — wiring to the header means shutting down and opening the box that runs Signal K, InfluxDB, Grafana, and nginx. Not worth it for one sensor.

So the chosen path is a **standalone UNO R4 WiFi node** (already on hand) carrying the CC1101 as a **dumb radio**: it captures raw wM-Bus T1 telegrams and serves them over WiFi as single-quoted JSON, exactly like the two existing pressure boards. `pivac.WaterMeter` on the Pi fetches that feed and runs the decode + AES decrypt (via `wmbusmeters` or Python). This needs **no Pi GPIO and no disassembly**, lets the node sit near the meter for reception, and reuses the proven HTTP-poll pattern. **Full detail in Appendix A** (raw-forward variant). The Pi-direct path (§3–§4) is retained as the alternative.

> Why raw-forward and not on-board decode: the UNO R4's Renesas RA4M1 is outside the proven wM-Bus/AES ecosystem (that runs on ESP/Linux). Keeping the board dumb sidesteps that entirely. If you later want a board that decodes locally, use an **ESP32**, not the R4 (Appendix A notes both).

### 1.2 Radio reception at the node's location

The node should sit where it both hears the meter and reaches WiFi. The iPerl beacons every 4–8 s at utility-readable power, and a proper **868 MHz SMA antenna** on the CC1101 usually closes a normal in-house distance — but **prove it early** (§5 step 3: confirm telegrams arrive with usable RSSI from the node's intended spot). Mitigations: external/higher-gain 868 MHz antenna → reposition the node → confirm WiFi signal there too (the existing pressure boards have a documented history of 2.4 GHz drop-and-recover, so check the node's AP coverage). The node's mobility is precisely the advantage the Pi lacked.

### 1.3 Will the default AES key actually decrypt *your* meter?

The vendor line (confirmed in `wmbusmeters` issue threads) is that iPerl uses **one shared mBus key for all meters**, which is why the factory default circulates — but some users still hit "decrypted content failed check." We can't know until we listen. **Decryption success is gated on the `2F2F` marker** appearing at the start of the decrypted payload; its presence = right key, its absence = wrong key. There is a discovery/validation step in §5 for exactly this. If the default key fails, the fallback is to request the key from the water utility (you noted you don't have one).

### 1.4 Frequency: confirm 868.95 MHz and the CC1101 band variant

You wrote 858 MHz; the iPerl/wM-Bus T1 standard is **868.95 MHz**. Two things to verify before/at first power-on: (a) the CC1101 module is the **868/900 MHz** variant, **not** the 433 MHz one — buying 433 is the single most common failure and it will *never* hear the meter; an **EBYTE E07-900M10S** (SMA antenna jack) is the recommended module. (b) The exact TX frequency — a quick spectrum scan or trying 868.95 / 868.3 confirms it.

---

## 2. Bill of materials

- **CC1101 868/900 MHz module** (confirm band — §1.4; recommend **E07-900M10S** with an SMA jack + 868 MHz antenna). The 433 MHz variant will not work.
- Female–female jumper wires (8) to the Pi 40-pin header.
- *(Option 1 / recommended needs nothing else — the Pi's GPIO is 3.3 V, so the radio connects directly. The Arduino UNO R4 WiFi, HiLetgo level shifter, and DIYables shield are only needed for **Option 2** / Appendix A.)*

---

## 3. Wiring — CC1101 → Raspberry Pi GPIO

The Pi's GPIO is **3.3 V**, the same as the CC1101, so the wiring is direct — **no level shifter**. Use the Pi's hardware **SPI0** bus plus two GPIOs for the radio's interrupt/data lines (GDO0, GDO2). GDO24/GDO25 are chosen only because they sit next to the SPI pins on the header.

### 3.1 Connection table

| CC1101 pin | Pi signal | BCM | Physical pin | Notes |
|------------|-----------|-----|--------------|-------|
| VCC / VDD  | 3.3 V     | —      | **1** (or 17) | 3.3 V **only** — never 5 V |
| GND        | GND       | —      | 6 (or 9/20/25/39) | common ground |
| SI (MOSI)  | SPI0 MOSI | GPIO10 | **19** | SPI |
| SO (MISO)  | SPI0 MISO | GPIO9  | **21** | SPI |
| SCLK (CLK) | SPI0 SCLK | GPIO11 | **23** | SPI |
| CSN (CS)   | SPI0 CE0  | GPIO8  | **24** | chip select |
| GDO0       | GPIO24    | GPIO24 | **18** | packet-received interrupt (wmbusmeters keys off this) |
| GDO2       | GPIO25    | GPIO25 | **22** | sync/FIFO status |

### 3.2 ASCII layout

```
        Pi 40-pin header                         CC1101 (3.3 V)
        ----------------                         --------------
   3.3V [ 1] ──────────────────────────────────► VCC
   GND  [ 6] ──────────────────────────────────► GND
   GPIO24 [18] ◄──────────────────────────────── GDO0   (interrupt)
   MOSI [19] ──────────────────────────────────► SI (MOSI)
   GPIO25 [22] ◄──────────────────────────────── GDO2
   MISO [21] ◄────────────────────────────────── SO (MISO)
   SCLK [23] ──────────────────────────────────► SCLK
   CE0  [24] ──────────────────────────────────► CSN
                                                  ANT ──► 868 MHz SMA antenna
```

Keep the antenna clear of the Pi's metal/enclosure and route it toward the meter where practical (§1.2).

### 3.3 Enable SPI on the Pi

```bash
sudo raspi-config        # Interface Options → SPI → Enable
# (or add `dtparam=spi=on` to /boot/firmware/config.txt)
sudo reboot
ls -l /dev/spidev0.*      # expect /dev/spidev0.0 after reboot
```

---

## 4. Receiver software — `wmbusmeters` on the Pi

No firmware to write — `wmbusmeters` drives a directly-attached CC1101 over SPI/GPIO and does the wM-Bus T1 reassembly + AES-128-CBC decrypt + iPerl parse natively (the path tracked in wmbusmeters issue #1713).

1. **Install** `wmbusmeters` on the Pi (`apt`, or build from source for the latest CC1101 support). Confirm the version includes the directly-attached-CC1101 device backend.
2. **Configure the device** for a Pi-attached CC1101 with the GDO/SPI pins from §3 (the device line names the SPI dev + GDO0 GPIO; bandwidth/freq for T1 @ 868.95 MHz). Run it first in **foreground/`--analyze` mode** to watch frames arrive (§5).
3. **Add the meter** (driver `iperl`, the confirmed meter ID, the AES key) once §5 validates the key. wmbusmeters then emits decoded JSON per telegram — `total_m3` and any iPerl flow/alarm fields — to stdout / a file / a shell pipe / MQTT.
4. **Run it as a service** (`wmbusmetersd` has its own systemd unit) so it's always listening; pivac consumes its output (§6).

This replaces the entire rev-1 Arduino sketch section.

---

## 5. Discovery & key validation (one-time, before wiring into pivac)

Done on the Pi (or a laptop) with `wmbusmeters`, before committing config:

1. Install `wmbusmeters` on the Pi (`apt` or build) with the CC1101 wired per §3 and SPI enabled.
2. Run in **scan/analyze mode** to list every meter ID heard, **and confirm reception** at the Pi's location (§1.2) — telegrams arriving every 4–8 s with usable RSSI. Identify ours (cross-check against the ID printed on the physical meter). *This is the go/no-go on the Pi-direct approach.*
3. Add the iPerl with the default key and confirm the **`2F2F` check passes** (= correct key, decryption working). If it fails → the default key is wrong for this utility; escalate to requesting the key (decision §1.3).
4. Record the confirmed **meter ID**, **frequency**, and **key** — these go into the Pi-side config, **never into the repo** (same rule as the Tapo/RTSP and Graph secrets: live only in `/etc/pivac/config.yml`, mode-guarded).

---

## 6. New pivac module — `pivac.WaterMeter`

New file `pivac/WaterMeter.py` implementing the standard `status(config={}, output="default")` contract.

> **This section describes the Pi-direct (Option 1) ingest**, where `wmbusmeters` owns the CC1101 and the module just reads its decoded output. For the **recommended remote-node path (Option 2)** the module instead fetches the node's raw-telegram feed over HTTP and runs the decode itself — see **Appendix A §A.3**. Both end on the same Signal K paths (§6.1) and config shape; only the input source differs.

Its job is to bridge `wmbusmeters`' decoded output (§4) into Signal K deltas. Since the decode/decrypt is already done by `wmbusmeters`, the module is thin.

**Ingest options** (pick one — the module is small either way):

- **(a) Read `wmbusmeters`' JSON output file/socket** (recommended). Configure `wmbusmetersd` to write the latest reading per meter to a file (or MQTT topic); `status()` reads it, picks the configured meter ID, and emits the totalizer. No coupling to wmbusmeters internals beyond its stable JSON.
- **(b) Shell out to `wmbusmeters --listento` once per cycle** to grab the most recent telegram. Simpler config, but spawns a process each poll.

**Flow (option a):**

1. Read the latest `wmbusmeters` JSON for the configured **meter ID** (e.g. `/run/wmbusmeters/<id>.json`).
2. Extract `total_m3` (and any flow/alarm fields if present).
3. Emit Signal K deltas (via `sk_init_deltas` / `sk_add_source` / `sk_add_value`).
4. If the reading is older than a freshness threshold, skip emitting (so the §7 staleness alert fires rather than republishing a stale value).

**Config block** (in `/etc/pivac/config.yml`; sample sketch in `config/config.yml.sample`):

```yaml
pivac.WaterMeter:
    description: Domestic water consumption from the iPerl meter (CC1101 on Pi + wmbusmeters)
    enabled: true
    meter_id: "12345678"               # confirmed in §5
    source: /run/wmbusmeters/12345678.json   # wmbusmetersd JSON output for this meter
    max_age_s: 120                     # ignore readings older than this
    inputs:
        total_m3:
            sk_path: environment.water.domestic
            outname: consumption        # → environment.water.domestic.consumption  (m³ cumulative)
```

> **Secrets:** the AES key lives in the `wmbusmeters` config (`/etc/wmbusmeters.conf` or `/etc/wmbusmeters.d/`, root-readable), **never in this repo**. The pivac config only needs the (non-secret) meter ID and the output path — same secrets discipline as the Tapo/RTSP and Graph credentials.

### 6.1 Signal K paths

Signal K has **no standard path for domestic-water consumption** (its `tanks.*` model is for tank *levels*, not metered throughput), so we use a custom namespace — consistent with how pivac already uses custom/non-standard paths (`environment.inside.hvac.dhw.recirc.temperature`, `electrical.emporia.*`).

| SK path | Value | Notes |
|---------|-------|-------|
| `environment.water.domestic.consumption` | number, **m³ cumulative** | the iPerl lifetime totalizer; monotonic. Flow is derived downstream (§7), not published, to avoid double sources of truth. |
| `environment.water.domestic.flowRate` *(optional)* | number | only if the iPerl telegram exposes a reliable instantaneous flow field; otherwise omit and derive in Grafana. |

Publishing the **totalizer** (not a pre-computed flow) is deliberate: it's the meter's ground truth, survives restarts, and lets InfluxDB/Grafana compute flow over any window with `difference()` / `derivative()`.

### 6.2 systemd services

Two units:

- **`wmbusmeters` daemon** — its own packaged `wmbusmetersd.service` (the receiver; owns the CC1101 + the AES key). Enable it.
- **`pivac-watermeter.service`** — new, copied from an existing `pivac-arduino-*.service`: user `pi`, `PIVAC_CFG=/etc/pivac/config.yml`, `Restart=always`, `RestartSec=10`. Add `After=wmbusmeters.service` so it starts after the receiver. (If `wmbusmetersd` runs as root and writes to `/run/wmbusmeters/`, make sure user `pi` can read that path.)

Then fold `pivac-watermeter` (and note `wmbusmeters`) into the documented restart/stop lists in CLAUDE.md (Standard Deployment Procedure, SD-maintenance stop set, Checking Logs).

---

## 7. Grafana panel

Add a panel to the pivac dashboard JSON (`grafana/dashboards/*.json`, auto-provisioned — edit JSON, commit, `git pull` on the Pi). Datasource: the `pivac` bucket via the InfluxQL-compat datasource (`bdxaqnfllu5fkf`); measurement = the full SK path, field = `value`.

- **Primary panel — "Domestic Water Flow"**: time-series of flow derived from the totalizer. InfluxQL: `non_negative_difference(mean("value"))` on `environment.water.domestic.consumption`, grouped by a sensible window (e.g. `time(1m)`), unit L/min or m³/h.
- **Secondary (optional) — cumulative consumption**: raw totalizer as a stat/graph, plus a daily-usage bar via `non_negative_difference` over `time(1d)`.

Mirror the styling of the existing DHW panel so it sits naturally on the board.

**Freshness alert (optional, mirrors existing pattern):** a `watermeter-stale` rule in `grafana/provisioning/alerting/sensor-freshness.yaml` routing to the `graph-bridge` contact point — 30 m staleness on `environment.water.domestic.consumption`, same `value < <sentinel>` + `noDataState: Alerting` trick used by the other freshness alerts. (The meter transmits every 4–8 s, so true silence for 30 m is a real fault — `wmbusmeters` down, CC1101 dead, or meter battery.) Defer until the feed is proven stable.

---

## 8. Implementation sequence (recommended path — remote UNO R4 node)

1. **Buy/confirm** the CC1101 is the **868/900 MHz** variant with an antenna (§1.4, §2). ← gate
2. **Hardware**: wire CC1101 ↔ UNO R4 via the 4-ch level shifter on the DIYables shield (Appendix A §A.1).
3. **Sketch bring-up + reception check**: flash the raw-forward sketch (Appendix A §A.2); from the node's intended spot near the meter, confirm over serial that T1 telegrams arrive every 4–8 s with usable RSSI, and that the node holds WiFi there. **Go/no-go on placement** — if reception or WiFi is poor, reposition / better antenna (§1.2) before continuing.
4. **Key validation (§5)**: feed a captured telegram to `wmbusmeters` on the Pi with the iPerl + default key; confirm the `2F2F` check passes. **Hard gate** — if the key fails, stop and resolve §1.3.
5. **Deploy the node**: reserve a DHCP-by-MAC IP in UniFi (like the other boards); confirm `curl http://<node-ip>/` from the Pi returns the raw-telegram JSON.
6. **pivac module (§6 + Appendix A §A.3)**: write `pivac.WaterMeter` (fetch node feed → `wmbusmeters`/Python decode → deltas), config block, `pivac-watermeter.service`; verify deltas land in Signal K (`environment.water.domestic.consumption`).
7. **Grafana (§7)**: add the flow panel; confirm data plots; (later) add the freshness alert.
8. **Docs**: update `CLAUDE.md` — Active Services & Devices table (new board, MAC/IP), Current Modules, deployment/stop/log lists, SK paths. Update the Arduino repo CLAUDE.md with the new board's MAC/IP/sketch.
9. **PRs**: pivac (module + service + Grafana + config sample + docs); Arduino repo (sketch). Branch + PR per workflow.

> For the **Pi-direct alternative** instead, the sequence is: wire CC1101 → Pi GPIO (§3) during a maintenance window, enable SPI, run `wmbusmeters` against the local CC1101, then steps 4/6–9 as above (no node, no Arduino-repo work).

## 9. Risks & open questions (carried from §1)

- **Radio reception + WiFi at the node's spot** (§1.2) — proven go/no-go in step 3. Ladder: better 868 MHz antenna → reposition the node → verify 2.4 GHz AP coverage there (the pressure boards have a drop/recover history).
- **Default AES key may not decrypt this meter** (§1.3) — validated early in step 4; fallback is utility key request.
- **Exact TX frequency / CC1101 band** (§1.4) — confirm the 868/900 MHz module variant and scan the actual frequency.
- **Signal K has no standard water-consumption path** — using a documented custom path (§6.1).
- **Node WiFi stability** — reuse the other boards' watchdog/auto-reconnect hardening (Arduino PR #6) so a 2.4 GHz drop self-recovers.
- **Secrets handling** — the AES key stays in the `wmbusmeters` config, out of the repo (§6).

## 10. Two documented options (both retained)

This plan keeps **both** receiver options fully specified, so the choice can flip without re-deriving anything:

| | **Option 2 — remote UNO R4 node over WiFi** *(recommended)* | **Option 1 — CC1101 on the Pi GPIO** *(alternative)* |
|---|---|---|
| Receiver host | Standalone UNO R4 WiFi near the meter (Appendix A) | Production Pi GPIO/SPI (§3, §4) |
| Pi GPIO used | **None** | SPI0 + 2 GPIOs — contends with `pivac.GPIO`/1-Wire |
| Touches the live Pi | **No** — joins WiFi, polled over HTTP | **Yes** — power down + open the box to wire the header |
| Placement | Near the meter (best reception) | Fixed at the Pi's location |
| Level shifting | Required — UNO R4 is 5 V (4-ch BSS138) | None — Pi is 3.3 V |
| Decode/decrypt | Raw-forward → `wmbusmeters`/Python on the Pi | `wmbusmeters` on the Pi |
| Custom firmware | Arduino sketch (Appendix A §A.2) | None |
| Main downside | A board + sketch to maintain | Pin contention **and** production downtime/disassembly (§1.1) |

**Decision:** go with **Option 2 (remote UNO R4, raw-forward)** — it avoids the Pi's pin contention and the disassembly of the live monitoring box, sits near the meter for reception, and reuses the existing pressure-board pattern. Option 1 stays documented as the fallback for a future scenario where a node isn't wanted and opening the Pi is acceptable. If on-board decode is ever preferred over raw-forward, use an **ESP32** (proven wM-Bus/AES), not the RA4M1-based UNO R4.

Also noted but not pursued:
- **RTL-SDR dongle instead of CC1101** — plug-and-play on USB and handy for discovery, but a heavier/more-power-hungry receiver and overkill for one fixed meter; the CC1101 is the lean purpose-built choice.

---

## Appendix A — Option 2: remote Arduino/ESP node (full detail)

Use this if reception at the Pi is poor and the receiver needs to sit near the meter. The node captures wM-Bus T1 frames on a CC1101 and either decodes on-board or forwards raw telegrams to `wmbusmeters` on the Pi; pivac then ingests the result. **On a UNO R4 WiFi** (5 V logic) the CC1101 needs the 4-channel level shifter; **on an ESP32** (3.3 V) it does not, and the on-board decode/decrypt path is far better supported — prefer an ESP32 if doing full on-board decode.

### A.1 Wiring — CC1101 ↔ UNO R4 WiFi (5 V, via the 4-ch level shifter)

The CC1101 is a **3.3 V** device; the UNO R4 WiFi drives **5 V** logic. So:

- **Arduino → CC1101 lines MUST be shifted down 5 V → 3.3 V** to avoid destroying the radio: **SCK, MOSI, CSN**.
- **CC1101 → Arduino lines are 3.3 V → 5 V**: **MISO, GDO0** (and optional GDO2). 3.3 V is *usually* read as logic-HIGH by the R4, but routing MISO through the shifter removes all doubt.

The 4-channel converter carries the **whole SPI bus** (MOSI, MISO, SCK, CSN) — which is exactly why a 4-channel part fits. **GDO0** (the data/interrupt line wM-Bus reception depends on) connects **directly** (3.3 V→5 V); if it ever proves marginal, add a 5th shifted channel. GDO2 is typically unused for T1.

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

Mount the CC1101 + converter on the DIYables shield; keep the antenna clear of the board and away from boiler-room metal. *(On an ESP32 the level shifter is omitted — wire the CC1101's SPI + GDO0/GDO2 straight to the ESP32's 3.3 V GPIO, as in the SzczepanLeon/MarkLabs guides.)*

### A.2 Arduino sketch (raw-forward variant)

A new sketch in the `~/github/Arduino` repo (its own sketch dir, alongside `ArduinoPSI_Domestic` / `ArduinoPSI_BoilerLoop`), reusing the existing boards' proven scaffolding: WiFi connect with the RA4M1 **watchdog + escalating reconnect + `NVIC_SystemReset()` fallback + `uptime_ms`** hardening (Arduino PR #6).

**Responsibilities:**

1. **Init CC1101 via RadioLib** for wM-Bus **T1**: 868.95 MHz, ~103 kbps, 2-FSK, ~50 kHz deviation, ~270–325 kHz RX bandwidth, T1 sync word, GDO0 as async data / packet-ready interrupt. (Crib the register set from `alex-icesoft/esp32_cc1101_wmbus` / SzczepanLeon's CC1101 init — same chip.)
2. **Capture frames** in the GDO0 ISR into a ring buffer; keep the most recent N raw telegrams (with capture time-since-boot and RSSI/LQI).
3. **Optionally pre-filter** to telegrams whose wM-Bus manufacturer/device-type bytes match Sensus iPerl, to cut HTTP payload size (full decode still happens on the Pi).
4. **Serve over WiFi**, matching the house pattern — a minimal HTTP server on `:80` returning a single-quoted dict line, e.g.:
   ```
   {'mfct':'SEN','id':'12345678','rssi':-72,'raw':'2C44...<hex>','age_ms':1840,'uptime_ms':3600000}
   ```
   (`raw` is the hex wM-Bus telegram; `id` is the meter ID parsed from the *unencrypted* header so the Pi can pick the right meter without decrypting.)

**Full-on-board-decode variant (ESP32-preferred):** instead of `raw`, the sketch decrypts (tiny-AES-c / ESP32 mbedTLS) and parses, emitting `{'volume_m3':1234.567,'flow_lph':0,'rssi':-72,'uptime_ms':...}`. Highest integration fit (a clean dict pivac can poll with `ArduinoSensor`), but the decode/decrypt port is the hard part and is proven on ESP, not the RA4M1.

**Libraries:** `RadioLib` (CC1101) for radio; `WiFiS3` (UNO R4) or ESP32 WiFi for networking; `tiny-AES-c` / mbedTLS only for the on-board-decode variant.

**Bring-up checks:** serial prints `Watchdog armed.`; confirm CC1101 detected (version register read); print every raw telegram + RSSI to confirm frames arrive every 4–8 s.

### A.3 pivac side for Option 2

- **Raw-forward variant:** `pivac.WaterMeter` fetches `http://<node-ip>/`, picks the telegram for the configured meter ID, then either shells out to `wmbusmeters` (feeding the raw hex) or decodes in Python (`cryptography`/`pycryptodome`, AES-128-CBC with the IV from the telegram header) → emits the same `environment.water.domestic.consumption` delta. The board gets a DHCP-by-MAC reservation in UniFi like the other two.
- **On-board-decode variant:** no new module needed — a config block with `module: pivac.ArduinoSensor` and `inputs: {volume_m3: {sk_path: environment.water.domestic, outname: consumption}}` reuses the existing poller verbatim.

Either variant lands on the same Signal K paths (§6.1) and Grafana panel (§7), so only the receiver front-end differs between Option 1 and Option 2.

---

## Sources

- [MarkLabs — Sensus iPerl wM-Bus via CC1101 + ESPHome](https://marklabs.pl/en/sensus-iperl-water-meter-home-assistant-wmbus-cc1101-esphome/) (wiring, 868 MHz, 4–8 s interval, AES-128, E07-900M10S)
- [MarkLabs — iPerl meter ID & AES key config](https://marklabs.pl/en/sensus-iperl-esphome-yaml-meter-id-aes-key-configuration/)
- [wmbusmeters issue #253 — iPerl shared mBus key / decrypt failures](https://github.com/wmbusmeters/wmbusmeters/issues/253)
- [wmbusmeters issue #928 / #878 — Sensus iPerl driver discussion](https://github.com/wmbusmeters/wmbusmeters/issues/928)
- [wmbusmeters issue #1713 — using a CC1101 (868 MHz) directly on a Raspberry Pi](https://github.com/wmbusmeters/wmbusmeters/issues/1713)
- [f4exb/picc1101 — Raspberry Pi ↔ CC1101 over SPI/GPIO (wiring reference)](https://github.com/f4exb/picc1101)
- [SzczepanLeon/esphome-components — wmbus component (CC1101, T1/C1, 868.95 MHz); basis for a remote-node fallback](https://github.com/SzczepanLeon/esphome-components)
- [eydam-prototyping/cc1101 — CC1101 driver for Raspberry Pi](https://github.com/eydam-prototyping/cc1101)
