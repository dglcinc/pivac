# Domestic Water Consumption Monitoring — Implementation Plan

**Status:** DRAFT FOR REVIEW — 2026-06-15 (rev 2)
**Goal:** Add a new pivac data source that reads the house's **Sensus iPerl** domestic water meter over radio, publishes consumption/flow to Signal K, and plots it in Grafana.

> **Architecture decided (rev 2):** the meter is read **over the air** — there is no physical connection to it — so a dedicated Arduino node buys nothing. The CC1101 transceiver wires **directly onto the Raspberry Pi's GPIO/SPI** (Pi is 3.3 V, matching the radio — no level shifter, no Arduino, no shield), and `wmbusmeters` on the Pi does the decode/decrypt. This was "Strategy C" in rev 1 and is now the chosen path. The Arduino-based strategies (A/B) are retained in §10 only as fallbacks for the one scenario that would resurrect them: poor radio reception at the Pi's location (§1.2).

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

### 1.1 Architecture — RESOLVED: CC1101 direct on the Pi (no Arduino)

The meter is read over radio with no physical connection, so a dedicated node only earns its place if it improves *reception* — and the simplest deployment is to hang the CC1101 off the production Pi's own GPIO/SPI and let `wmbusmeters` (already a Linux-native, tested iPerl decoder) do the decode + AES decrypt there. No Arduino, no level shifter, no shield, no custom sketch, no porting wM-Bus/AES to a constrained MCU. **This is the chosen path.** (The Arduino "Strategy A/B" options from rev 1 survive only in §10 as the fallback if §1.2 reception is poor.)

### 1.2 The one real risk — radio reception at the Pi's location

The only thing the Pi-direct approach gives up versus a node placed next to the meter is **proximity to the transmitter**. The iPerl beacons every 4–8 s at utility-readable power, and a proper **868 MHz SMA antenna** on the CC1101 usually closes a normal in-house distance — but this is the item to **prove early** (§5 step 2: confirm telegrams actually arrive at the Pi with usable RSSI). Mitigations, in order: external/higher-gain 868 MHz antenna → relocate antenna on a short coax → only if all that fails, fall back to a remote ESP32+CC1101 node near the meter feeding the Pi (§10). Don't build the remote node speculatively.

### 1.3 Will the default AES key actually decrypt *your* meter?

The vendor line (confirmed in `wmbusmeters` issue threads) is that iPerl uses **one shared mBus key for all meters**, which is why the factory default circulates — but some users still hit "decrypted content failed check." We can't know until we listen. **Decryption success is gated on the `2F2F` marker** appearing at the start of the decrypted payload; its presence = right key, its absence = wrong key. There is a discovery/validation step in §5 for exactly this. If the default key fails, the fallback is to request the key from the water utility (you noted you don't have one).

### 1.4 Frequency: confirm 868.95 MHz and the CC1101 band variant

You wrote 858 MHz; the iPerl/wM-Bus T1 standard is **868.95 MHz**. Two things to verify before/at first power-on: (a) the CC1101 module is the **868/900 MHz** variant, **not** the 433 MHz one — buying 433 is the single most common failure and it will *never* hear the meter; an **EBYTE E07-900M10S** (SMA antenna jack) is the recommended module. (b) The exact TX frequency — a quick spectrum scan or trying 868.95 / 868.3 confirms it.

---

## 2. Bill of materials

- **CC1101 868/900 MHz module** (confirm band — §1.4; recommend **E07-900M10S** with an SMA jack + 868 MHz antenna). The 433 MHz variant will not work.
- Female–female jumper wires (8) to the Pi 40-pin header.
- *(Not used: the Arduino UNO R4 WiFi, HiLetgo level shifter, and DIYables shield. The Pi's GPIO is 3.3 V, so the radio connects directly.)*

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

New file `pivac/WaterMeter.py` implementing the standard `status(config={}, output="default")` contract. Its job is to bridge the `wmbusmeters` daemon's decoded output (§4) into Signal K deltas. Since the decode/decrypt is already done by `wmbusmeters`, the module is thin.

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

## 8. Implementation sequence

1. **Buy/confirm** the CC1101 is the **868/900 MHz** variant with an antenna (§1.4, §2). ← gate
2. **Hardware**: wire CC1101 → Pi GPIO per §3; enable SPI (`/dev/spidev0.0`).
3. **Receiver bring-up + reception check (§5)**: install `wmbusmeters`, run in analyze mode, confirm T1 telegrams arrive every 4–8 s with usable RSSI. **Go/no-go on Pi-direct** — if reception is poor, work §1.2 mitigations before continuing.
4. **Key validation (§5)**: add the iPerl + default key, confirm the `2F2F` check passes. **Hard gate** — if the key fails, stop and resolve §1.3.
5. **Receiver as a service**: enable `wmbusmetersd` writing per-meter JSON to `/run/wmbusmeters/`; verify it survives reboot.
6. **pivac module (§6)**: write `pivac.WaterMeter`, config block, `pivac-watermeter.service`; verify deltas land in Signal K (`environment.water.domestic.consumption`).
7. **Grafana (§7)**: add the flow panel; confirm data plots; (later) add the freshness alert.
8. **Docs**: update `CLAUDE.md` — Active Services table, Current Modules, deployment/stop/log lists, SK paths, and a note that the Pi now hosts a CC1101 on the GPIO header + `wmbusmeters`. Update `pi-CLAUDE.md` (new service on the Pi).
9. **PR**: pivac (module + service + Grafana + config sample + docs). Branch + PR per workflow. No Arduino-repo work.

## 9. Risks & open questions (carried from §1)

- **Radio reception at the Pi's location** (§1.2) — the central risk now; proven go/no-go in step 3. Mitigation ladder: better antenna → relocate antenna → remote ESP32 node (§10).
- **Default AES key may not decrypt this meter** (§1.3) — validated early in step 4; fallback is utility key request.
- **Exact TX frequency / CC1101 band** (§1.4) — confirm the 868/900 MHz module variant and scan the actual frequency.
- **Signal K has no standard water-consumption path** — using a documented custom path (§6.1).
- **Physical change to the production Pi** — adding the CC1101 to the GPIO header touches the live `10.0.0.82` box; wire it during a maintenance window and note the header pins are now occupied.
- **Secrets handling** — the AES key stays in the `wmbusmeters` config, out of the repo (§6).

## 10. Alternatives considered (not chosen)

- **Remote ESP32 + CC1101 node near the meter, feeding the Pi.** The fallback if §1.2 reception at the Pi is poor. An ESP32 (not the Renesas UNO R4 — the wM-Bus/CC1101 stack is proven on ESP) running `SzczepanLeon/esphome-components` decodes locally and pushes to Home Assistant/MQTT, or forwards raw telegrams to `wmbusmeters` on the Pi. More hardware and a second device to maintain; only justified if proximity is genuinely required.
- **Arduino UNO R4 WiFi node (rev-1 plan).** Dropped — the RA4M1 is outside the proven wM-Bus/AES ecosystem (that stack is ESP/Linux), and with no physical meter connection the board offered no advantage over the Pi-direct path. The purchased Arduino/shield/level-shifter are freed for another project.
- **RTL-SDR dongle instead of CC1101.** Works for discovery and is plug-and-play on USB, but it's a heavier/more-power-hungry receiver and overkill for one fixed meter; the CC1101 is the lean purpose-built choice.

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
