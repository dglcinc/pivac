# Domestic Water Consumption Monitoring — Implementation Plan

**Status:** DRAFT FOR REVIEW — 2026-06-15 (rev 2)
**Goal:** Add a new pivac data source that reads the house's **Sensus iPerl** domestic water meter over radio, publishes consumption/flow to Signal K, and plots it in Grafana.

> **Architecture (rev 4): recommended = a wM-Bus USB dongle on the Pi (IMST iM871A-USB).** The meter is read over the air, so the receiver only needs to be a USB stick. The production Pi can't host a *GPIO* radio — its header is largely consumed by `pivac.GPIO` (BCM 17/27/22/5/6/13/26/16/12) + the 1-Wire bus, and wiring one means powering down and opening the live Signal K / InfluxDB / Grafana / nginx box. A **USB wM-Bus dongle** sidesteps all of that: it's hot-plugged into a USB port (no GPIO, no disassembly, no Arduino, no custom sketch), decodes in hardware (low CPU), and `wmbusmeters` reads it natively (`im871a` driver). The only thing it shares with the abandoned Pi-direct CC1101 is **living at the Pi's location** — if reception there is poor, the fallback is the remote WiFi node that can sit near the meter.
>
> **Three receiver front-ends, all documented; everything downstream (decode → Signal K → Grafana) is identical:**
> 1. **USB dongle on the Pi** — *recommended_* (§2A, §4). Simplest; no GPIO, no disassembly.
> 2. **Remote UNO R4 WiFi node** — fallback if the Pi is too far from the meter (Appendix A). Uses the board you already have.
> 3. **CC1101 on the Pi GPIO** — §3–§4; now **superseded by the dongle** (the dongle does the same job without GPIO/soldering/downtime). Kept for reference only.

This plan is structured so you can sign off (or redirect) on the open decisions in §1 before any code is written.

> **Chosen for this build (rev 5):** the **remote UNO R4 WiFi node** (Appendix A) — David already has the Arduino, CC1101, level shifter, and shield, so it's $0 vs ~$100 for the Würth AMB8465-M dongle. The dongle remains the documented zero-fuss upgrade if the node proves troublesome. So the build order is: **start with Appendix A**; §3–§4 (dongle / CC1101-on-Pi) are the alternatives.

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

### 1.1 Architecture — RESOLVED: remote UNO R4 node for this build (dongle = upgrade)

The receiver only has to be a radio that gets telegrams to the Pi, and three front-ends can do it (full trade-offs in §10). The Pi's GPIO is effectively out — its header is crowded (`pivac.GPIO` uses BCM 17/27/22/5/6/13/26/16/12; `pivac.OneWireTherm` owns the 1-Wire bus) and wiring a GPIO radio means opening the live production box. That leaves two good choices: a **USB dongle** (simplest if buying) or a **remote WiFi node** (uses parts already on hand).

**Chosen for this build: the remote UNO R4 node** (Appendix A). David already owns the UNO R4, CC1101, level shifter, and shield, so it's **$0 vs ~$100** for a dongle, and the node can sit near the meter for the best reception. It runs the CC1101 as a dumb radio that forwards raw telegrams over WiFi; `pivac.WaterMeter` on the Pi fetches that feed and runs the decode + AES decrypt (via `wmbusmeters`/Python). No Pi GPIO, no disassembly, and it reuses the exact HTTP-poll pattern the two pressure boards already use.

> Why raw-forward, not on-board decode: the UNO R4's Renesas RA4M1 is outside the proven wM-Bus/AES ecosystem (ESP/Linux). Keeping the board dumb sidesteps that. For on-board decode later, use an **ESP32**, not the R4 (Appendix A notes both).

**Upgrade path if the node is troublesome** (sketch debugging, WiFi drops, reception): the **Würth Elektronik AMB8465-M** USB dongle — the US-available purpose-built wM-Bus adapter, **in stock at DigiKey USA** (PN **1917-1022-ND**, MPN 2605056083001; ~$100), driven by wmbusmeters' `amb8465` driver. ⚠️ The **-M USB adapter**, not the bare `AMB8465` solder-down module (DigiKey 1917-1020-ND). The commonly-cited IMST **iM871A-USB** is EU-only (import). An **RTL-SDR** (Nooelec / RTL-SDR Blog V4, ~$30, US-available) also works via `rtlwmbus` but decodes in software (more CPU, dropouts) — cheap backup. The **CC1101-on-Pi-GPIO** path (§3) is superseded by any dongle.

**Fallback:** the dongle lives at the Pi, so it shares the Pi-direct reception question. If the Pi is too far from the meter, switch to the **remote UNO R4 WiFi node** (the board you have), which sits near the meter and forwards raw telegrams over WiFi — full detail in **Appendix A**. The **CC1101-on-Pi-GPIO** path (§3–§4) is now **superseded by the dongle** and kept for reference only.

### 1.2 Radio reception — at the Pi (dongle) or at the node

For the dongle, the question is whether the **Pi's location** hears the meter; for the node, whether its **chosen spot** does (and reaches WiFi). The iPerl beacons every 4–8 s at utility-readable power. **Prove it early** (§5 step 3: confirm telegrams arrive with usable RSSI). Mitigations for the dongle: a **short USB extension** to get it out of any metal enclosure → relocate the Pi's antenna run → if still poor, fall back to the remote node. For the node: better 868 MHz antenna → reposition → verify 2.4 GHz AP coverage there (the pressure boards have a drop/recover history). The node's mobility is its one advantage over the dongle.

### 1.3 Will the default AES key actually decrypt *your* meter?

The vendor line (confirmed in `wmbusmeters` issue threads) is that iPerl uses **one shared mBus key for all meters**, which is why the factory default circulates — but some users still hit "decrypted content failed check." We can't know until we listen. **Decryption success is gated on the `2F2F` marker** appearing at the start of the decrypted payload; its presence = right key, its absence = wrong key. There is a discovery/validation step in §5 for exactly this. If the default key fails, the fallback is to request the key from the water utility (you noted you don't have one).

### 1.4 Frequency: confirm 868.95 MHz and the CC1101 band variant

You wrote 858 MHz; the iPerl/wM-Bus T1 standard is **868.95 MHz**. Two things to verify before/at first power-on: (a) the CC1101 module is the **868/900 MHz** variant, **not** the 433 MHz one — buying 433 is the single most common failure and it will *never* reliably hear the meter; an **EBYTE E07-900M10S** (SMA jack, 855–925 MHz) is the recommended module. (b) The exact TX frequency — a quick spectrum scan or trying 868.95 / 868.3 confirms it.

> **Identifying a CC1101 module's band (this trips everyone):** the CC1101 *chip* tunes all of 315/433/868/915, so Amazon listings quote all four — but each *board* has an antenna matching network + antenna fixed for **one** band. A board silkscreened **433 is a 433 board**; tuning it to 868 loses ~10–20 dB of sensitivity (front-end mismatch) and won't hear the meter through walls. Tell the real band by: **silkscreen marking** (authoritative), **antenna length** (433 ≈ 16 cm vs 868 ≈ 8 cm — roughly half), or **model number** (E07-M1101D = 433-only; E07-900M10S = 868/915). Swapping just the antenna does **not** fix it — the on-board matching is still wrong. Buy a board explicitly marked/sold as **868**.

---

## 2. Bill of materials

### 2A. Recommended — USB dongle on the Pi (buy one item)

- **Würth Elektronik AMB8465-M** wM-Bus USB adapter — **US-stocked at DigiKey** (PN **1917-1022-ND**, MPN **2605056083001**). Plug into a Pi USB port; that's the entire hardware build. Driven by wmbusmeters' `amb8465` driver.
  - ⚠️ Buy the **-M USB adapter**, not the bare `AMB8465` module (DigiKey 1917-1020-ND, solder-down chip).
  - Alternatives: **IMST iM871A-USB** (EU import — not US-stocked); **RTL-SDR** (Nooelec NESDR / RTL-SDR Blog V4, US/Amazon, via `rtlwmbus` — more CPU). **Not** a CUL stick (telegram-length limits).
  - Optional: a short **USB extension cable** to position the dongle out of the Pi's enclosure for better reception.
- *(Nothing else — no GPIO wiring, no level shifter, no Arduino.)*

### 2B. Fallback — remote UNO R4 node (parts you already have)

- CC1101 868/900 MHz module (SMA jack + 868 MHz antenna; **not** the 433 MHz variant), UNO R4 WiFi, HiLetgo 4-ch level shifter, DIYables shield, jumper wires. See Appendix A.

### 2C. Reference only — CC1101 on the Pi GPIO (superseded by 2A)

- CC1101 868/900 MHz module + 8 jumper wires to the Pi header. See §3.

---

## 3. Wiring — CC1101 → Raspberry Pi GPIO *(reference only — superseded by the USB dongle, §2A)*

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

No firmware to write — `wmbusmeters` does the wM-Bus T1 reassembly + AES-128-CBC decrypt + iPerl parse natively. It reads from any supported front-end; only the **device line** differs between the dongle and the CC1101.

1. **Install** `wmbusmeters` on the Pi (`apt`, or build from source for the latest device support).
2. **Configure the device:**
   - **Recommended — AMB8465-M dongle:** plug it in, find its port (`dmesg | grep tty` → e.g. `/dev/ttyUSB0`, FTDI), set the device to `amb8465:/dev/ttyUSB0:t1` (or `c1,t1`). No GPIO, no SPI to enable. *(iM871A is `im871a:/dev/ttyUSB0:t1`; RTL-SDR is `rtlwmbus`.)*
   - *Reference — CC1101 on GPIO:* enable SPI (§3.3) and use the directly-attached-CC1101 device line naming the SPI dev + GDO0 GPIO + T1 params (wmbusmeters issue #1713).
   Run first in **foreground/`--analyze` mode** to watch frames arrive (§5).
3. **Add the meter** (driver `iperl`, the confirmed meter ID, the AES key) once §5 validates the key. wmbusmeters then emits decoded JSON per telegram — `total_m3` and any iPerl flow/alarm fields — to stdout / a file / a shell pipe / MQTT.
4. **Run it as a service** (`wmbusmetersd` has its own systemd unit) so it's always listening; pivac consumes its output (§6).

> For the **remote-node fallback (Appendix A)**, `wmbusmeters` instead receives raw hex forwarded by the node (fed via stdin/`--analyze` or a network feed) rather than owning a local radio.

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

> **This section describes ingest when `wmbusmeters` owns a local radio on the Pi** — the recommended **USB dongle**, or the reference CC1101-on-GPIO — and the module just reads its decoded JSON output. For the **remote-node fallback** the module instead fetches the node's raw-telegram feed over HTTP and decodes it — see **Appendix A §A.3**. All paths end on the same Signal K paths (§6.1) and config shape; only the input source differs.

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

**Freshness alert (optional, mirrors existing pattern):** a `watermeter-stale` rule in `grafana/provisioning/alerting/sensor-freshness.yaml` routing to the `graph-bridge` contact point — 30 m staleness on `environment.water.domestic.consumption`, same `value < <sentinel>` + `noDataState: Alerting` trick used by the other freshness alerts. (The meter transmits every 4–8 s, so true silence for 30 m is a real fault — `wmbusmeters` down, dongle/radio dead, or meter battery.) Defer until the feed is proven stable.

---

## 8. Implementation sequence (this build — remote UNO R4 node)

1. **Radio:** start with the **on-hand 433-marked CC1101** as a no-cost test (§1.4). It's band-mismatched for 868 (~10–20 dB sensitivity loss), so give it the best shot: place it **right next to the meter** and fit a **~8.2 cm quarter-wave wire** (or an 868/915 antenna) instead of the 433 coil. If it can't hear the meter even up close (step 3), buy a true **868** module (EBYTE E07-900M10S, ~$8–12) and reuse everything else.
2. **Hardware**: wire CC1101 ↔ UNO R4 via the 4-ch level shifter on the DIYables shield (Appendix A §A.1).
3. **Sketch bring-up + reception check**: flash the raw-forward sketch (Appendix A §A.2); from a spot near the meter, confirm over serial that T1 telegrams arrive every 4–8 s with usable RSSI, and that the node holds WiFi there. **Interpreting it:** frames decode → done; *any* 868 RF/frames but no decode → radio is fine, it's a key/ID issue (step 4); **nothing even inches from the meter** → the 433 board's mismatch is the limiter → get an 868 module. Persistent reception trouble with a proper 868 radio → the AMB8465-M dongle is the upgrade.
4. **Key validation (§5)**: feed a captured telegram to `wmbusmeters` on the Pi with the iPerl + default key; confirm the `2F2F` check passes. **Hard gate** — if the key fails, stop and resolve §1.3.
5. **Deploy the node**: reserve a DHCP-by-MAC IP in UniFi (like the other boards); confirm `curl http://<node-ip>/` from the Pi returns the raw-telegram JSON.
6. **pivac module (§6 + Appendix A §A.3)**: write `pivac.WaterMeter` (fetch node feed → `wmbusmeters`/Python decode → deltas), config block, `pivac-watermeter.service`; verify deltas land in Signal K (`environment.water.domestic.consumption`).
7. **Grafana (§7)**: add the flow panel; confirm data plots; (later) add the freshness alert.
8. **Docs**: update `CLAUDE.md` — Active Services & Devices table (new board, MAC/IP), Current Modules, deployment/stop/log lists, SK paths. Update the Arduino repo CLAUDE.md with the new board's MAC/IP/sketch.
9. **PRs**: pivac (module + service + Grafana + config sample + docs); Arduino repo (sketch). Branch + PR per workflow.

> **Dongle upgrade path** instead (no Arduino): buy the AMB8465-M, plug into the Pi, set `wmbusmeters` to `amb8465:/dev/ttyUSB0:t1`, then steps 4/6–9 (no node, no sketch, no Arduino-repo work).

## 9. Risks & open questions (carried from §1)

- **Radio reception + WiFi at the node's spot** (§1.2) — proven go/no-go in step 3. Ladder: better 868 MHz antenna → reposition the node → verify 2.4 GHz AP coverage there → if persistent, the AMB8465-M dongle at the Pi is the upgrade.
- **Node WiFi stability** — reuse the pressure boards' watchdog/auto-reconnect hardening (Arduino PR #6) so a 2.4 GHz drop self-recovers.
- **Default AES key may not decrypt this meter** (§1.3) — validated early in step 4; fallback is utility key request.
- **CC1101 band variant** (§1.4) — confirm the module is the **868/900 MHz** version, not 433 (it would never hear the meter); confirm the meter is on T1 @ 868.95.
- **Signal K has no standard water-consumption path** — using a documented custom path (§6.1).
- **Secrets handling** — the AES key stays in the `wmbusmeters` config, out of the repo (§6).

## 10. Three documented options (all retained)

The choice can flip without re-deriving anything. Everything downstream of the receiver (decode → Signal K → Grafana) is identical across all three.

| | **Dongle on the Pi** *(recommended)* | **Remote UNO R4 node** *(fallback)* | **CC1101 on Pi GPIO** *(superseded)* |
|---|---|---|---|
| Hardware | iM871A-USB stick (§2A) | UNO R4 + CC1101 + shifter (Appendix A) | CC1101 + jumpers (§3) |
| Pi GPIO used | **None** (USB) | **None** (WiFi) | SPI0 + 2 GPIOs — contends with `pivac.GPIO`/1-Wire |
| Touches the live Pi | **No** — hot-plug USB | **No** — joins WiFi, polled over HTTP | **Yes** — power down + open the box to wire the header |
| Placement | Fixed at the Pi's location | Near the meter (best reception) | Fixed at the Pi's location |
| Decode/decrypt | `wmbusmeters` on the Pi (hardware) | Raw-forward → `wmbusmeters`/Python on the Pi | `wmbusmeters` on the Pi |
| Custom firmware | None | Arduino sketch (Appendix A §A.2) | None |
| Effort | **Lowest** — plug in, configure | Highest — build + sketch + maintain | Medium — wire + downtime |
| Main downside | Tied to Pi location | A board + sketch to maintain | Pin contention **and** production downtime/disassembly (§1.1) |

**Decision (this build):** go with the **remote UNO R4 node** (Appendix A) — David already owns all the parts, so it's $0 vs ~$100 for the dongle, and it can sit near the meter for reception. If the node proves troublesome (sketch debugging, WiFi drops, reception), the **Würth AMB8465-M dongle** (DigiKey US PN 1917-1022-ND) is the zero-fuss upgrade: lowest effort, no GPIO, no disassembly, hardware decode. The **CC1101-on-Pi-GPIO** path is superseded by the dongle and kept for reference only.

Also noted:
- **iM871A-USB** — the frequently-cited equivalent, but effectively EU-only (not US-stocked); import only.
- **RTL-SDR** — a US-available USB SDR (~$30, Nooelec / RTL-SDR Blog) that also works (`rtlwmbus`), good for discovery, but decodes in software (more CPU, runs warm, more dropouts). Backup choice.

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
- [wmbusmeters — Supported Devices (im871a, amb8465, rtlwmbus, …)](https://github.com/wmbusmeters/wmbusmeters/blob/master/README.md)
- [DigiKey US — Würth AMB8465-M wM-Bus 868 MHz USB adapter (PN 1917-1022-ND)](https://www.digikey.com/en/products/detail/wurth-electronics-inc/AMB8465-M/8258132)
- [IMST iM871A-USB (EU source)](https://wireless-solutions.de/products/m-bus/im871a-usb/)
- [wmbusmeters/rtl-wmbus — RTL-SDR software receiver for wM-Bus](https://github.com/wmbusmeters/rtl-wmbus)
- [f4exb/picc1101 — Raspberry Pi ↔ CC1101 over SPI/GPIO (wiring reference)](https://github.com/f4exb/picc1101)
- [SzczepanLeon/esphome-components — wmbus component (CC1101, T1/C1, 868.95 MHz); basis for a remote-node fallback](https://github.com/SzczepanLeon/esphome-components)
- [eydam-prototyping/cc1101 — CC1101 driver for Raspberry Pi](https://github.com/eydam-prototyping/cc1101)
