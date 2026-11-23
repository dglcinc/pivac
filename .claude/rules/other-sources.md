---
paths:
  - "pivac/RedLink.py"
  - "pivac/Emporia.py"
  - "pivac/Sprinkler.py"
  - "pivac/DomesticWater.py"
  - "pivac/ArduinoSensor.py"
  - "pivac/WaterMeter.py"
  - "scripts/emporia-*.py"
  - "scripts/arduino-watchdog.sh"
  - "scripts/systemd/arduino-watchdog.*"
  - "tests/test_emporia_*.py"
  - "tests/test_redlink_*.py"
  - "tests/test_arduino_*.py"
  - "docs/emporia-notes.md"
---

# RedLink, Emporia, sprinkler, water and the pressure Arduinos

<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
<!-- Copyright David Lewis -->

Loaded when a file under its `paths:` is read; `CLAUDE.md` says to read it first for any work on the thermostats, the Emporia panels, irrigation, domestic water, the two pressure boards or the Shelly plugs. Rules here; the measurements and incident history behind them are in the docs named.

## Related Repositories

The Arduino pressure sensors (10.0.0.114 and 10.0.0.219) are programmed from a separate repo at `~/github/Arduino`. Each is an Arduino UNO R4 WiFi running a minimal HTTP server. See that repo's CLAUDE.md for hardware details, known issues (including hardcoded WiFi credentials), and deployment notes.

> **The DHW board's recirc-temp firmware is on `main` in `~/github/Arduino`** (verified 2026-08-26). The DS18B20 added to the **.114 DHW board** on 2026-05-31 serves the `temp` field → `environment.inside.hvac.dhw.recirc.temperature`, and `ArduinoPSI_Domestic.ino` defines `ONE_WIRE_BUS 2` while the shared `ArduinoPSI_impl.h` guards every temperature block on that macro, so the Domestic sketch emits `{'psi', 'temp', 'uptime_ms'}` and the BoilerLoop sketch is byte-for-byte unchanged. It reached `main` through `83e1cae`; the `feat/dhw-recirc-ds18b20` branch is the older unmerged route to the same code. **Reflashing .114 from the repo is safe** and will not drop the recirc temperature — build the `ArduinoPSI_Domestic` sketch, which additionally needs the `OneWire` and `DallasTemperature` libraries. Not checked: whether the board's flashed build is newer than `main`.
>
> **The recirc sensor's identity is recorded here because the sketch isn't.** The DS18B20 on the .114 board is printed tag **`28FFE715A0160328`** = w1 name **`28-0316a015e7ff`**. Identified 2026-08-10 by elimination — it is the fifth of a batch of five DS18B20s and the only one of the five *not* enumerated on the Pi's w1 bus — then confirmed against the physical tag. The elimination argument is what makes this solid; the tag merely agrees (see the tag-reliability warning under Known Operational Behaviours). Without this note the ROM exists nowhere in either repo and would be lost if the board had to be rebuilt.

### RedLink (`docs/operational-notes.md`)

- **All five thermostats run 2 cycles per hour on both stages in heat and cool, and a 1 °F stage 2 differential (ISU 3030) in heat and cool, since 2026-09-17** (kids room and master bedroom cool rate since 2026-09-16; the stage 2 rate shows only on a thermostat configured two-stage). The cool rate was the default 3, which was producing 10-minute calls and 10-minute gaps at 50 % duty on the kids room; at 2 it makes calls of 12 to 22 minutes with gaps of 10 to 18 at the same duty. The rate has no say at full demand: a continuous kids room call (11 hours on 2026-09-16 at a 73 °F hold with 72–78 °F outside, the room holding 73 °F) is load, with precedent of 9 and 10 hours in the month before, and one degree of setpoint is worth about 20 points of evening duty (0.72 at 73 °F, 0.53 at 74 °F). Loop A ΔT on its calls follows the fan stage and the tank band (ΔT ÷ (room − supply) is 0.12 cycling and 0.16–0.22 at full demand; 2.0–2.5 °F on 55–57 °F supply, 3.6–4.9 °F on 50–52 °F), so compare ΔT only at like supply temperature and duty. Both are two-stage in heat and cool with stage 2 as the air handler's high fan, which the RedLink payload cannot show; staging is 3010 Advanced, 3020 No, 3030 1 °F, so the high fan means a room at least 1 °F off setpoint. 3030 offers only Comfort or whole degrees; under Comfort a continuous call held the high fan for hours with the display reading the setpoint (master bedroom four hours on 2026-09-17), and leaving the installer menu restarts the staging. The kids coil is sound (3.7 °F loop ΔT calling alone, zero droop at half duty), so cycling there is a thermostat setting and never a coil question; evidence in `docs/unico-cooling-assessment-and-tuning.md` Appendix J.
- **A humidity step in one zone only, alongside a domestic draw, is a shower**, never a coil or water-temperature finding: check `environment.water.domestic.flowRate` and the `DHW` relay (`electrical.ac.switch.utility.DHW.statenum`; every relay is stored under `.statenum` and `.state`, and the bare path returns nothing) for the 20 minutes before the step and the other four zones' humidity for a flat line. On 2026-09-17 the kids room went 52 → 59 % in ten minutes at 16:55 EDT at the end of an 18-minute draw, with `DHW` closed 16:40–17:15, while the other four zones held within a point. Through the eight hours before it the room held 51–54 % on 47–54 °F loop A supply, so the 12 °C target dries the room. Every dehumidification call reads as ordinary cooling in RedLink (`statenum` −1).
- **A zone calling in RedLink while `HPCALL` stays open and the HZ-432's zone light stays dark is a wiring break between that zone's EIM and the panel**, since the thermostat is wireless to the EIM and keeps reporting the call (a loose R and C pair in the master bedroom EIM after the node install, 2026-10-20; the relay normally leads RedLink's state by about 24 s). The air-handler node shows it as coil water far below loop A's supply with the duct pair in its fan-off pattern, and the `LoopDelta` gate cannot see it, so its deltas read as flowing. Evidence in `docs/operational-notes.md`.
- Cold-start login takes ~75 s on the Pi; expect it after every restart and the Sunday 00:00 reboot. `force_close=True` + IPv4-only are required. Devices refresh in parallel under a 12 s deadline; **do not raise it** (20 s doubled the failure rate, about 12 % to 25 %, in the one trial of 2026-05-08; retest before relying on it after a Honeywell-side change). The session resets only on `AuthError`, `APIRateLimited`, `SessionTimedOut` or `UnauthorizedError`. `APIRateLimited` holds the module out for 10 min; do not restart to "fix" it. After a DNS outage with no `APIRateLimited` in the log, `restart pivac-redlink` is the right move. Baseline is 5–17 s gaps and 15–25 % per-device timeouts with occasional tile flicker, all Honeywell-side. Runs at `--loglevel WARNING` because `ERROR` drops the cycle warnings. Per-device refresh failures log at INFO; the journal carries one hourly rollup (`RedLink refresh failures in the last 60 min: KIDS ROOM 71/240, …`) and a warning when a device misses 10 refreshes in a row, so a share well above 30 % or an `in a row` line is the signal.

## Emporia Setup (first time only)

Before enabling `pivac-emporia.service`, run the discovery script to get device GIDs:
```bash
source ~/pivac-venv/bin/activate
python ~/github/pivac/scripts/emporia-discover.py --username YOUR_EMAIL --password YOUR_PASSWORD
```
Copy the suggested config block into `/etc/pivac/config.yml`, replacing the GID placeholders with real values.

Token is cached at `/etc/pivac/emporia-tokens.json` after first successful login.

### Emporia (`docs/emporia-notes.md`)

- **Live circuits:** house `chiltrix`, `bova_kitchen`, `bova_great_room` (metered inside `utility_sub_panel`), `wall_oven`, `utility_sub_panel`, `hall_sub_panel`, `microwave_refrigerator`, `downstairs_bath_floor`, `dont_know` plus `main`/`balance`; apartment `air_conditioner`, `furnace`, `clothes_washer`, `kitchen_plugs_1`, `kitchen_plugs_2`, `garage_entry_basement`, `gfi_garage_outlets`, `trophy_a` plus `main`/`balance`. Renamed and retired names stay in InfluxDB as orphans with their history, and a rename needs a `signalk` restart.
- **Apartment ports since 2026-09-26:** 4 `Clothes Washer`, 5 `Kitchen Plugs 1`, 6 `Air Conditioner` (one CT at multiplier 2.0, by decision, so its 120 V standby load may read low), 7 `Furnace`, 8 `Garage, Entry, Basement`, 9 `Kitchen Plugs 2`, 11 `Trophy A`, 12 `Upstairs Back`, 13 `Upstairs Front`, 14 `GFI Garage Outlets`. **Ports 12 and 13 return no usage since they were labelled** (22:36Z on 2026-09-26; port 12 read 32 W unlabelled until then), so `upstairs_back` and `upstairs_front` are not live and their load sits in `balance`. Ports 1, 2, 3 and 10 of the apartment Vue are suspect and out of use. `clothes_washer` and `trophy_a` read 0 W with their loads off. The per-circuit record starts at 17:56 EDT on 2026-09-26; `air_conditioner` and `furnace` run back to 2026-08-11. The Chiltrix pair on the house panel (ports 10 and 13) came from the apartment. A label can be set from the Pi with PyEmVue's `update_channel`.
- **240 V loads want a merged pair (one CT per leg, same circuit name) at multiplier 1.0.** ×2 on a single CT only works for a balanced load and hides standby draw; ×2 on a pair doubles it. History for the four paired circuits before 2026-07-04 is half scale.
- A run of `400 Client Error … /customers` every cycle while RedLink's warning rate stays normal is an Emporia cloud outage: it self-heals with no restart (2 h 40 min on 2026-09-16), the module logs in with the password every cycle until it does, and no Grafana rule watches `electrical.emporia.*`, so nothing announces the gap. Emporia's cloud keeps the minutes, so the gap is fillable afterwards with `scripts/emporia-backfill.py` (dry run, then `--write`; bound it by the last and first live points).
- Circuit names refresh on `name_refresh_s` (1 h) and sanitize to `[a-z0-9_]`; `tests/test_emporia_sanitize.py` asserts every in-service name sanitizes to itself.
- **Grafana panel 10:** `main` stays unstacked, `balance` must be plotted, and a nested CT needs two corrections (subtract it from its parent *and* add it back to `balance`, because Emporia's balance is not nesting-aware). Colours are by load family with a `byName` override per series: blue cooling, yellow subpanels, green loads, grey balance, purple `main`. Panel 11 (apartment) gives each load its own hue instead of a family, with blue, red and green for its three largest loads (air conditioner, furnace, GFI garage outlets), grey for `balance` and purple for `main`; it matches raw field names, so a rename silently reverts that series to the palette.

### Sprinkler and irrigation (`docs/operational-notes.md`)

- Meter: DAE AS200U-75P, 1 gal/pulse, on OpenSprinkler SN1 + GND. `fpr = 1.0`, `flow_scale 1.0`, calibrated 2026-06-20 to 1 %. OpenSprinkler does no unit conversion: set the Flow Pulse Rate unit dropdown to gal/pulse or the app reads 3.8× low (pivac is independent of it). Auth is md5 of the OS device password (`{"result":2}` when wrong). `/jl` `flow` is an average rate. Recalibrate with `fpr_new = fpr × (true ÷ reported)`.
- House #68 is even, so OpenSprinkler Program 1 is restricted to even days (§ 237-10, June–Sept, 12:01–10 am and 6 pm–midnight). No deduct meter, so irrigation bills at the domestic tiers plus sewer, ≈ $1.19/100 gal.

### Pressure Arduinos

- **The DHW expansion tank is an Amtrol ST-25 since about noon on 2026-10-17** (an ST-12 before). In the 21 hours after the swap, `electrical.ac.arduinoPSI.psi` (.114) ran 51.5–69.0 psi, against 40.9–87.0 over the four days before. A water-heater recovery with no draw now raises the pressure 3–4 psi, against 11–19 psi to 73–86 psi before, so a rise of 10 psi or more on a no-draw recovery means the tank's air charge has gone. Its precharge is 60 psi, the static cold supply pressure, which is Amtrol's rule; the 10.3-gallon tank then predicts a 4–5 psi rise for the 0.4–0.7 gal a recovery expands, which is what it shows. The precharge can only be read or set with the tank's water side isolated and drained.
- Both boards occasionally time out (one WARNING, self-recover). After a mains blip the .219 board sometimes fails to rejoin WiFi; `arduino-watchdog.timer` power-cycles the shared Shelly after 15 min down and `arduino-{dhw,hydronic}-psi-stale` email at 30 min. Manual recovery: `curl "http://10.0.0.61/rpc/Switch.Set?id=0&on=false"; sleep 8; curl "http://10.0.0.61/rpc/Switch.Set?id=0&on=true"`. A low `uptime_ms` means a recent reboot; `http=000` means off WiFi.

## Shelly Plugs (remote power-cycling)

Two **Shelly Plug US Gen4** (`S4PL-00116US`, FW `1.7.99-plugusg4prod1`) on WiFi SSID `redux`, **local API auth disabled** (open RPC), also cloud-connected. From a four-pack; two spare units not yet powered. Each is **DHCP with a UCG fixed-IP reservation** (device stays portable — the reservation pins the IP by MAC, no factory reset needed to relocate; set via the UCG classic API `PUT /proxy/network/api/s/default/rest/user/<_id>` with `use_fixedip/fixed_ip/network_id`).

| Name | MAC | IP (reserved) | Cloud id | Powers |
|------|-----|---------------|----------|--------|
| **Arduinos** | `ac:eb:e6:f4:b9:30` | `10.0.0.61` | `acebe6f4b930` | The two UNO-R4 pressure boards (.114 DHW + .219 boiler) → the `arduino-watchdog` power-cycle target |
| **PivacPower** | `ac:eb:e6:f6:45:20` | `10.0.0.118` | `acebe6f64520` | General pivac-side mains (the Pi) |

**Power-on default:** both plugs run `initial_state="on"` (set 2026-06-23) so mains returning restores power unattended.

**Naming** lives in three places that do not sync (Shelly cloud label, local device name, UCG client name); all three currently agree.

**Control (local, no cloud):**
- Power-cycle: `POST http://<ip>/rpc/Switch.Set -d '{"id":0,"on":false}'` then `…"on":true` (also usable as `GET …/rpc/Switch.Set?id=0&on=false`).
- Power/energy: `GET http://<ip>/rpc/Switch.GetStatus` (Gen4 exposes W + Wh) — basis for a future `pivac.Shelly` module → `electrical.*` if ever integrated.
- Identity probe (no creds): `curl http://<ip>/shelly`. Discover any Shelly by probing `/shelly` across ARP hosts, or query the UCG client list (faster, authoritative).

**Cloud Control API (off-LAN, configured 2026-06-23):** Auth Cloud Key at `~/.config/shelly/cloud.key` (mode 600), region server at `~/.config/shelly/cloud.server` = `shelly-266-eu.shelly.cloud`. Example: `curl -X POST https://<server>/device/all_status --data-urlencode "auth_key=$(cat ~/.config/shelly/cloud.key)"` → both plugs' `switch:0.output`/`apower`. On-LAN prefer local RPC + UCG; cloud is for remote only. Key is account-wide (revoke/regenerate at `control.shelly.cloud` → Authorization Cloud Key) — **never put it in chat or the repo.**

## Arduino Watchdog (auto-recovery for the pressure boards)

`arduino-watchdog.timer` runs `scripts/arduino-watchdog.sh` every 5 min (`OnBootSec=5min`, then `OnUnitActiveSec=5min`). It pings the two pressure boards (10.0.0.114 DHW, 10.0.0.219 boiler/hydronic) and, if **either** is unreachable for a sustained `DOWN_THRESHOLD_S` (default **900 s / 15 min**), power-cycles the shared "Arduinos" Shelly plug (`10.0.0.61`, open local RPC) via `Switch.Set off → sleep 8 → on`, rate-limited to at most once per `CYCLE_MIN_INTERVAL_S` (default **3600 s / 1 h**). This is the self-healing counterpart to the `arduino-*-psi-stale` freshness alerts: the alerts tell you, the watchdog fixes it.

**Design notes:** Tunables are env-overridable in the `.service` (`DOWN_THRESHOLD_S`, `CYCLE_MIN_INTERVAL_S`, `OFF_DWELL_S`, `PROBE_RETRIES`). Watch it with `journalctl -u arduino-watchdog -n 30` (silent on the happy path — logs only when a board is down or a cycle is issued).

Deploy after editing the script/units:
```bash
sudo cp ~/github/pivac/scripts/systemd/arduino-watchdog.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now arduino-watchdog.timer
```

## Modules

| Module | Source |
|--------|--------|
| `ArduinoSensor` | Arduino HTTP sensor — **multi-field**: loops over `inputs` (key = response field name); inputs with `type: temperature` convert to Kelvin and emit `{sk_path}.{outname}.temperature`. Shared via `module:` override by `pivac.ArduinoPSI` (.114 = **DHW** pressure + recirc temp `environment.inside.hvac.dhw.recirc.temperature`) and `pivac.ArduinoThermPSI` (.219 = **boiler/hydronic** pressure). NB names are inverted vs role — see Active Services note. **`pivac.DomesticWater` (.188) *wraps* ArduinoSensor** rather than sharing it via `module:` — see its own Current Modules entry. |
| `DomesticWater` | DAE MJ-75a domestic water meter (UNO R4 WiFi, `10.0.0.188`). Wraps `pivac.ArduinoSensor` (one node GET) and passes through `environment.water.domestic.{flowRate,consumption,flowing,runDuration,runningFor}`, then **adds `.runVolume`** — gallons consumed during the current draw, computed **Pi-side** (no firmware) by snapshotting the `consumption` totalizer on the `flowing` 0→1 edge and reporting the delta; **holds the last draw's total while idle** (resets to 0 when the next draw starts). State lives in the daemon (module globals). `run_s`/`runtime` (from the node) → `.runDuration`/`.runningFor` = this draw's duration for the WilhelmSK tiles. |
| `Emporia` | Emporia Vue Gen 2 power monitors — polls two panels (house 200A, apartment 100A) via PyEmVue, emits per-circuit Watts to `electrical.emporia.<panel>.<circuit>`. **Channels sharing a circuit name are summed** — the house panel's 240 V circuits use one CT per leg (ch 1+2 `utility_sub_panel`, 3+4 `hall_sub_panel`, 5+6 `wall_oven`; the names in service are the Live circuits list above), so per-channel emission would halve them (see Known Operational Behaviours). |
| `WaterMeter` | Sensus iPerl water-meter **LCD** via Tapo RTSP camera (`10.0.0.85`) — reads the cumulative gallons totalizer via perspective-warp + **whole-glyph template matching** (NOT segment thresholding — a reflective LCD's "off" segments aren't black). Emits `environment.water.domestic.consumption` (gal) + `.flowing`. See `docs/water-meter-camera-monitoring-plan.md`. |
| `Sprinkler` | OpenSprinkler irrigation flow via the local HTTP API (`10.0.0.17:5000`) — polls `/jc`, computes `(flcrt/flwrt)*fpr*60*flow_scale`, emits `environment.water.irrigation.flowRate` (gal/min) + `.active`. Auth = **md5(device password)** in config `password_md5` (Pi-only secret). Overlaid on the domestic flow panels (Grafana). |

## Reference docs

| Doc | Covers |
|-----|--------|
| `docs/emporia-notes.md` | Emporia circuit history, paired-CT scaling, nested-CT corrections, panel 10/11 conventions |
