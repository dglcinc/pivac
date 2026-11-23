# CLAUDE.md — pivac (project-specific)

> Working style, machine detection, and GitHub conventions are in the global context:
> `~/.claude/CLAUDE.md`, a symlink to `<github-dir>/claude-contexts/global.md`

## What This Project Does

**pivac** collects data from Raspberry Pi sensors and outputs standardized JSON. It's a read-only monitoring tool for HVAC/home automation, feeding downstream systems (Signal K, InfluxDB, Grafana, WilhelmSK mobile app).

**Licensing:** code is PolyForm Noncommercial 1.0.0 (`LICENSE`), documents and board designs CC BY-NC 4.0 (`LICENSE-DOCS`); commercial use needs a separate licence from David. Every new source file starts with `SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0` and `Copyright David Lewis` in its comment syntax, and every new doc in `docs/` with the same two lines as HTML comments naming `CC-BY-NC-4.0`. `hardware/vendor/` keeps its makers' terms. The README's Licensing section is the public statement.

## Running the Project

```bash
# From a git clone (no install needed)
python scripts/pivac-provider.py [module_names] [options]

# Examples
python scripts/pivac-provider.py pivac.GPIO --format pretty
python scripts/pivac-provider.py pivac.OneWireTherm pivac.TED5000 --daemon

# Options: --loglevel DEBUG|INFO|WARNING|ERROR|CRITICAL
#          --daemon [N]   (run forever, or N iterations)
```

**Config file lookup order:**
1. `$PIVAC_CFG` (env var)
2. `/etc/pivac/config.yml` (system install)
3. `config/config.yml` (git clone)

**Important:** `/etc/pivac/config.yml` must include a `pivac_config:` section containing a nested `signalk:` block with `host`, `port`, `username`, and `password` for the WebSocket connection to work. See `config/config.yml.sample` for the format.

**Testing a module standalone** (no Signal K needed — outputs plain JSON to stdout):
```bash
source ~/pivac-venv/bin/activate
python -c "import pivac.ArduinoSensor as m; import json; print(json.dumps(m.status(), indent=2))"
```

## Architecture

### Module System

Each sensor type is a standalone module in `pivac/`. The orchestrator (`scripts/pivac-provider.py`) dynamically loads modules listed in `config.yml` using `importlib.import_module()` and calls their `status()` function. Only keys starting with `pivac.` are treated as modules; `pivac_config:` is reserved for framework settings.

If a config section includes a `module:` key, that value is used as the Python import path instead of the section name — allowing multiple config sections to share a single implementation (e.g., two Arduino sensors with different IPs both pointing to `pivac.ArduinoSensor`).

**Every module must implement:**
```python
def status(config={}, output="default") -> dict:
    ...
```

Modules return a plain dict (default output) or Signal K delta structure.

### Data Flow

```
config.yml → pivac.set_config() → pivac-provider.py → module.status() → WebSocket → Signal K
```

Each service authenticates to Signal K via HTTP JWT (`/signalk/v1/auth/login`), then pushes delta messages over a persistent WebSocket connection (`/signalk/v1/stream`). Falls back to stdout if Signal K is unavailable.

### Core Utilities (`pivac/__init__.py`)

- `set_config(file)` — load YAML config
- `propagate_defaults(config)` — copy top-level config keys down to each input entry (used by most modules)
- `sk_init_deltas()`, `sk_add_source()`, `sk_add_value()` — Signal K delta helpers

### Signal K Output

Modules always emit Signal K delta messages:
```json
{"updates": [{"source": {"label": "rpi:hostname"}, "values": [...]}]}
```

The spec-reviewed omissions are intentional: `context` is omitted (server correctly defaults to `vessels.self`), `timestamp` is omitted (server fills it in on receipt), and `source.type` is omitted (no standard type value exists for RPi providers). These are not bugs.

### Config `propagate` Key

Modules support a `propagate` list — config keys listed there are copied from the top-level module config into each entry under `inputs:`, unless overridden at the input level.

### Process Management

Each module runs as a dedicated systemd service (`scripts/systemd/pivac-*.service`), installed to `/etc/systemd/system/`. All services run as user `pi`, use `PIVAC_CFG=/etc/pivac/config.yml`, and have `Restart=always` with `RestartSec=10`.

Signal K settings are at `/home/pi/.signalk/settings.json` — `pipedProviders` is intentionally empty (pivac now self-manages via WebSocket).

## Active Services and Devices

| systemd service         | Module                  | Device                           | IP / Source  |
|-------------------------|-------------------------|----------------------------------|--------------|
| pivac-1wire             | pivac.OneWireTherm      | DS18B20 1-wire temperature sensors | GPIO       |
| pivac-redlink           | pivac.RedLink           | Honeywell thermostat             | internet     |
| pivac-gpio              | pivac.GPIO              | GPIO input pins (relays/switches)| GPIO         |
| pivac-arduino-psi       | pivac.ArduinoSensor     | **DHW** pressure (Fusch 200PSI) + recirc-loop temp | 10.0.0.114 |
| pivac-arduino-therm-psi | pivac.ArduinoSensor     | **Boiler/hydronic** pressure (Fusch 100PSI) | 10.0.0.219 |
| pivac-emporia           | pivac.Emporia           | Emporia Vue Gen 2 (house + apt)  | Emporia cloud |
| pivac-sentry            | pivac.Sentry            | NTI Trinity Ti-200 boiler (Tapo C120 RTSP) | 10.0.0.19 |
| ~~pivac-watermeter~~ (stopped 2026-06-17, disabled 2026-06-27) | pivac.WaterMeter | Sensus iPerl LCD (Tapo RTSP) — camera-CV retired, ESP32-CAM TBD | 10.0.0.85 |
| pivac-sprinkler         | pivac.Sprinkler         | OpenSprinkler irrigation flow (local API)  | 10.0.0.17:5000 |
| pivac-domestic-water    | pivac.DomesticWater     | **Domestic** water meter (DAE MJ-75a, 0.1 gal/pulse) on UNO R4 WiFi | 10.0.0.188 |
| pivac-chiltrix          | pivac.ChiltrixModbus    | **Chiltrix CX75** heat pump, 184 Modbus addresses | RS-485 → UNO R4 on USB |
| pivac-loop-delta        | pivac.LoopDelta         | Gated per-run loop ΔT (derived; reads Signal K)   | none — derived |
| pivac-grafana-alerts    | pivac.GrafanaAlerts     | Grafana alert state → Signal K notifications (derived; reads Grafana's API) | 127.0.0.1:4000 |

**Air-handler nodes.** Each of the five Unico air handlers has an AirMaster Pico W carrier with the coil water pair, the supply and return air beads and the SCB tap on J4, powered from the Unico's 24 VAC. Each has two services: `pivac-ah-<zone>` (config section `pivac.UnicoAH_<Zone>`, loads `pivac.ArduinoSensor`) and `pivac-scb-<zone>` (section `pivac.UnicoSCB_<Zone>`, loads `pivac.UnicoSCB` with `node: http://<ip>/`). Paths sit under `environment.inside.hvac.ah.<zone>`. Every offset lives on the unit.

| Zone (`<zone>`) | AirMaster | Carrier | IP, host | Pico W MAC | Water pair | SCB |
|---|---|---|---|---|---|---|
| Master bedroom (`mbr`) | `AM-0001` | Rev B | 10.0.0.182, `master-bedroom` | `28:cd:c1:14:f6:a9` | PA5 | |
| Great room (`greatroom`) | `AM-0002` | Rev B | 10.0.0.183, `great-room` | `28:cd:c1:14:f6:ab` | PA10 | M3036 |
| Utility (`utility`) | `AM-0003` | Rev C | 10.0.0.184, `utility` | `28:cd:c1:17:4e:7f` | PA9 | M2430 |
| Kids room (`kids`) | `AM-0004` | Rev C | 10.0.0.187, `kids-room` | `28:cd:c1:17:4e:83` | PA12 | M1218 |
| Kitchen (`kitchen`) | `AM-0005` | Rev C | 10.0.0.191, `kitchen` | `28:cd:c1:17:4e:81` | PA11 | M3036 |

The per-node offsets, stored airflows, gates and history are in `.claude/rules/air-handlers.md`.

> **⚠️ The two Arduino module/delta names are inverted vs their physical roles — legacy, do NOT rename** (InfluxDB already holds history under these measurement names; renaming would orphan it). Verified 2026-06-01 against the WilhelmSK gauge wiring and the boards' WiFi MACs:
>
> | Board | WiFi MAC | IP | pivac module / SK delta | WilhelmSK gauge | Sketch |
> |-------|----------|----|--------------------------|-----------------|--------|
> | **DHW** | `c0:4e:30:11:6f:3c` (`esp32s3-116f3c`) | **10.0.0.114** | `pivac.ArduinoPSI` → `electrical.ac.arduinoPSI.psi` | "Potable DHW PSI" | `ArduinoPSI_Domestic` (200 PSI) |
> | **Boiler/hydronic** | `34:b7:da:66:1e:50` (`esp32s3-661e50`) | **10.0.0.219** | `pivac.ArduinoThermPSI` → `electrical.ac.arduinoThermPSI.psi` | "Hydronic PSI" | `ArduinoPSI_BoilerLoop` (100 PSI) |
>
> So `arduinoPSI`/`.114` is the DHW board and `arduinoThermPSI`/`.219` is the boiler — the opposite of what the names suggest. `electrical.ac.*` is also a misnomer (these are pressures, not AC electrical). The DHW recirc-loop DS18B20 (`environment.inside.hvac.dhw.recirc.temperature`) lives on the **DHW board → `pivac.ArduinoPSI` (.114)**. IPs are DHCP-assigned by MAC, so a board keeps its IP regardless of where it's plugged in.

## Key File Locations

- Pivac code: `~/github/pivac/`
- Live config: `/etc/pivac/config.yml`
- Systemd services: `/etc/systemd/system/pivac-*.service`
- Signal K config: `~/.signalk/settings.json`
- Python venv: `~/pivac-venv/` (always use this)
- nginx site config: `/etc/nginx/sites-available/pivac`
- nginx bowling proxy config: `/etc/nginx/sites-available/mlb.dglc.com` (proxies `mlb.dglc.com` → Mac Mini `10.0.0.84:5001`)
- nginx AirMaster proxy: `/etc/nginx/snippets/airmaster.conf` with the cookie map in `/etc/nginx/conf.d/airmaster-map.conf` (both Pi-local). A new or renamed unit needs its block and its name in the two regex lists there, then a reload; the block's contents are in `.claude/rules/air-handlers.md`.
- nginx catch-all: `/etc/nginx/sites-available/000-default-drop` is the `default_server` on 80 and 443. A request that names neither hostname (the public IP, `10.0.0.82`, a foreign name) is refused at the TLS handshake or closed with 444, so reach the Pi's web services by hostname, or by their own ports on the LAN.
- sshd: `/etc/ssh/sshd_config.d/10-key-only.conf` sets key-only logins, root included (`PermitRootLogin prohibit-password`). A new machine needs its public key appended to `~/.ssh/authorized_keys` from one that already has access; xrdp and VNC still take the password.
- nginx Basic Auth credentials: `/etc/nginx/.htpasswd` (user: dglcinc)
- TLS certificate: `/etc/letsencrypt/live/68lookout.dglc.com/` (auto-renews via certbot timer)
- Grafana config: `/etc/grafana/grafana.ini`
- Grafana API token: `~/.config/grafana-claude-agent.key` (mode 600) on **both** the Pi and the Mac — service account `sa-1-claude`, Admin role. Use it as `-H "Authorization: Bearer $(cat ~/.config/grafana-claude-agent.key)"` against `http://127.0.0.1:4000/grafana/api/...` on the Pi. **Never ask for the Grafana admin password; this is the credential.** The poller's own Viewer token (service account `pivac-alerts`) lives only in the `pivac.GrafanaAlerts` block of `/etc/pivac/config.yml`.
- WireGuard keys (unused, kept for reference): `/etc/wireguard/`
- Label printer: the Brother PT-E550W prints from the Mac over USB with no driver through `scripts/ptouch-cable-flag.py` (pyusb and Homebrew libusb; it enumerates as `PT-E500`, VID `04f9` PID `205f`, and macOS refuses raw CUPS queues, so the script speaks the raster protocol and reads the tape width from the printer's status). Two text lines per flag, centred, both blocks identical, half cut.
- Equipment manuals (Mac, OneDrive): `~/Library/CloudStorage/OneDrive-DGLC/HVAC Documentation/Equipment Manuals/` holds the full set, including the NTI Trinity Ti100-200 I&O manual (2015-05-12), the Taco, Honeywell and Unico manuals; the Chiltrix CX65-1 and CX50-2 IOMs are in `~/OneDrive - DGLC/Claude/HVAC Manuals/`. Read the manual for any equipment limit or setting before searching the web.

## Remote Access

All remote access goes through nginx on the Pi (`10.0.0.82`) over HTTPS. No VPN required.

**External hostname:** `68lookout.dglc.com` → public IP `74.89.220.182` (DNS on AWS Route53; update manually if ISP IP changes)

**Network topology (double-NAT):** Internet → fiber router (`192.168.1.x`) → Unifi router (`10.0.0.x`) → Pi (`10.0.0.82`). TCP ports 80 and 443 are forwarded at both hops.

**Pi network:** `eth0` (`88:a2:9e:3c:c3:73`) is DHCP-reserved to `10.0.0.82`. `wlan0` is the fallback at `10.0.0.130`; the port forwards target `.82` only, so external access does not fail over. Profile and recovery commands are in `.claude/rules/platform-ops.md`.

| URL | Service | Auth |
|-----|---------|------|
| `https://68lookout.dglc.com/admin/` | Signal K admin UI | nginx Basic Auth |
| `https://68lookout.dglc.com/signalk/` | Signal K API + WebSocket | Signal K own auth |
| `https://68lookout.dglc.com/plugins/` | Signal K plugin HTTP routes (WilhelmSK push pairing) | Signal K own auth |
| `https://68lookout.dglc.com/grafana/` | Grafana | Grafana own login |
| `https://68lookout.dglc.com/sprinkler/` | OpenSprinkler (`10.0.0.17:5000`) | nginx Basic Auth |
| `https://68lookout.dglc.com/airmaster` | AirMaster air-handler units: lands on `/airmaster/master-bedroom/` (10.0.0.182), with `/airmaster/great-room/` (10.0.0.183), `/airmaster/utility/` (10.0.0.184), `/airmaster/kids-room/` (10.0.0.187) and `/airmaster/kitchen/` (10.0.0.191) beside it; the page's tiles switch between them | nginx Basic Auth, then the unit's own login for changes |
| `https://mlb.dglc.com/` | Bowling League Tracker (Mac Mini `10.0.0.84:5001`) | Bowling app auth |

**WilhelmSK mobile app:** host `68lookout.dglc.com`, port `443`, SSL enabled. Uses the `/signalk/` path which has no Basic Auth (WilhelmSK doesn't support it). **WilhelmSK Grafana widget:** use `https://68lookout.dglc.com/grafana/` — Basic Auth must be absent from this path or the app crashes.

**nginx reload after config changes:**
```bash
sudo nginx -t && sudo systemctl reload nginx
```

## InfluxDB and Grafana

The Pi runs **InfluxDB 2**: use the `influx` CLI with Flux, or InfluxQL through the v1 endpoint (`curl -G http://localhost:8086/query --data-urlencode 'db=pivac'` with the Influx token). Measurement = full Signal K path, field = `value`. Grafana 13 listens on **port 4000** under `/grafana/`: API base `http://127.0.0.1:4000/grafana/api/`, token at `~/.config/grafana-claude-agent.key`. Live dashboards are in the `resource` table of `/var/lib/grafana/grafana.db`; the legacy `dashboard` table is stale. Dashboards provision from `grafana/dashboards/` within 30 s of a `git pull`. Alert rules provision from `grafana/provisioning/alerting/`, email through the Graph bridge and mirror into Signal K as `notifications.pivac.<uid>`. Read `.claude/rules/grafana.md` before any dashboard, query or alert work.

## Deployment, logs and maintenance stops

`scripts/pivac-services.sh` holds the one list of pivac units in service. `tests/test_claude_md_size.py` checks it against the lists in `scripts/nas-image-backup.sh`.

```bash
# After a git pull
~/github/pivac/scripts/pivac-services.sh restart
~/github/pivac/scripts/pivac-services.sh logs        # last 50 lines across every unit; `logs 200` for more

# One unit, and Signal K
journalctl -u pivac-redlink -n 50 --no-pager
journalctl -u signalk -n 50 --no-pager

# If systemd service or timer files were changed
sudo cp ~/github/pivac/scripts/systemd/*.service ~/github/pivac/scripts/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload

# Before SD card maintenance, extended downtime, or rsync
~/github/pivac/scripts/pivac-services.sh stop-all
```

`stop-all` stops the pivac units first (they push to Signal K), then signalk, then influxdb, then nginx, which also carries the `mlb.dglc.com` bowling proxy. Units with `Restart=always` return on boot; nginx does not, so run `sudo systemctl start nginx` after the swap. The bowling app's database is on the Mac Mini; stop `com.dglc.bowling-app` there separately for Mac maintenance. `pivac-watermeter` is stopped and disabled and is in no list.

## Topic files: read before working

This file holds what every session needs. The rules for each subsystem are in `.claude/rules/`, and each file loads by itself when a file under its `paths:` is read. **When the work touches a topic below and its file is not already in context, read it first**, including for work done over SSH, in InfluxDB or at the bench, where no repo file triggers the load. Each topic file ends with the table of `docs/` that hold its evidence.

| Topic | Read first | Evidence in `docs/` |
|---|---|---|
| Chiller, glycol loop, loop pressure, heating and cooling plant, HZ-432 | `.claude/rules/chiltrix.md` | `chiltrix-*`, `hydronic-*`, `unico-cooling-assessment-and-tuning.md` |
| AirMaster nodes, Unico air handlers, SCB, `LoopDelta` | `.claude/rules/air-handlers.md` | `airmaster/rev-a` to `rev-d`, `*air-handler*`, `unico-scb-*` |
| DS18B20 probes, offsets, the DS2482 bus, any ΔT | `.claude/rules/onewire.md` | `onewire-notes.md`, `ds18b20-*` |
| Relay inputs, GPIO, INT and EXT boards, board designs in `hardware/` | `.claude/rules/relays-io-boards.md` | `io-boards/` (`perfboard`, `rev-a` to `rev-c`), `cdp-chiller-rework-plan.md`, `new-pi-cutover.md` |
| Sentry reader, its camera, boiler display values | `.claude/rules/sentry.md` | `sentry-cv-notes.md` |
| Dashboards, InfluxDB queries, alert rules, the email bridge, push | `.claude/rules/grafana.md` | `grafana-alerting-notes.md` |
| RedLink thermostats, Emporia, sprinkler, domestic water, pressure Arduinos, Shelly plugs, Arduino watchdog | `.claude/rules/other-sources.md` | `emporia-notes.md`, `operational-notes.md` |
| The Pi, Signal K, nginx, WilhelmSK, network, backups, SD clone | `.claude/rules/platform-ops.md` | `operational-notes.md` |

## Hard rules

These hold whatever the task, whether or not a topic file is loaded.

1. **Chiltrix Modbus is function 03 only, never 6 or 16.** Set the chiller's targets on its panel, in °C, and read them back.
2. **Never raise the hydronic autofill regulator** or set it at or above the cold fill (20 psi). Top up with premixed glycol by hand.
3. **Never connect the Pi's wall adapter while EXT J4 is live.** The GH link between the boards has pin 1 at the bottom of both headers; mirrored, it puts 35 V on SDA.
4. **A rename of a Signal K path, relay, sensor or Emporia circuit is David's decision.** InfluxDB history is keyed on the name, so the old name's history stays behind as an orphan. `arduinoPSI` (.114) is the DHW board and `arduinoThermPSI` (.219) the boiler, inverted by legacy, and those two are never renamed.
5. **Retiring or renaming any path needs a `signalk` restart** after the module restart, or Signal K holds the old path frozen at its last value.
6. **Removing a Grafana alert rule needs a `deleteRules:` block**, left in place for good; verify against the `alert_rule` table. Ship a rule on a metric that does not exist yet as `isPaused: true`.
7. **Never ask for the Grafana admin password** or any password. Credentials are token files under `~/.config/`; secrets never go in the repo or the chat.
8. **OpenCV stays at 4.13** on the Pi; the Sentry reader is calibrated on it and logs a warning at start on any other version. The Sentry camera stays locked in Night mode and looks at the display at an angle.
9. **Do not raise the RedLink 12 s refresh deadline, and do not restart `pivac-redlink` to clear `APIRateLimited`.**
10. **Gate every loop ΔT on a switch, never a probe**, and identify a probe on the bus, never by its printed tag.
11. **GPIO 26 is dead; YOFF is retired.** Make continuity checks on an I/O board off the Pi.
12. **When a `pivac-*` unit is added or retired, change `scripts/pivac-services.sh` and both lists in `scripts/nas-image-backup.sh`**, or the unit stays dead after the monthly backup.
13. **Do heavy frame captures and InfluxDB pulls gently**: capture Sentry frames from a Mac, and fetch InfluxDB analysis data one measurement at a time with `aggregateWindow`.
14. **Read the equipment manual** (Key File Locations) for any equipment limit or setting before searching the web.

## Adding a New Module

1. Create `pivac/MyModule.py` implementing `status(config={}, output="default")`
2. Add a section to `config.yml` named `pivac.MyModule`
3. Create a systemd service file in `scripts/systemd/`
4. The provider script will auto-discover it
5. Add its unit to `scripts/pivac-services.sh` and to both lists in `scripts/nas-image-backup.sh`

## Current Modules

| Module | Source | Detail |
|--------|--------|--------|
| `GPIO` | Relay and switch inputs on the I/O boards | `relays-io-boards.md` |
| `OneWireTherm` | DS18B20 probes on the DS2482 bus | `onewire.md` |
| `RedLink` | Honeywell thermostats through the mobile API (`aiosomecomfort`) | `other-sources.md` |
| `ArduinoSensor` | Arduino or AirMaster HTTP JSON line; multi-field through `inputs`; shared through `module:` by `pivac.ArduinoPSI`, `pivac.ArduinoThermPSI` and the five `pivac.UnicoAH_*` sections | `other-sources.md`, `air-handlers.md` |
| `DomesticWater` | DAE MJ-75a meter on an UNO R4 WiFi (10.0.0.188); wraps `ArduinoSensor` and adds `.runVolume` | `other-sources.md` |
| `Emporia` | Two Emporia Vue Gen 2 panels through PyEmVue; channels sharing a circuit name are summed | `other-sources.md` |
| `Sentry` | NTI Trinity Ti-200 boiler display read by camera and 7-segment CV → `hvac.boiler.sentry.*` | `sentry.md` |
| `ChiltrixModbus` | Chiltrix CX75 over RS-485 Modbus through an UNO R4 on USB; read only → `hvac.chiller.chiltrix.*` | `chiltrix.md` |
| `LoopDelta` | Derived from Signal K: gated ΔT per loop and per air-handler coil pair; a number is live, `0` is idle, a gap is a stale source | `air-handlers.md` |
| `GrafanaAlerts` | Derived from Grafana's API: every alert rule → `notifications.pivac.<uid>` | `grafana.md` |
| `Sprinkler` | OpenSprinkler local API (10.0.0.17:5000) → `environment.water.irrigation.*` | `other-sources.md` |
| `UnicoSCB` | A Unico air handler's control board, read passively through its AirMaster node | `air-handlers.md` |
| `WaterMeter`, `TED5000`, `FlirFX` | Retired or disabled | `other-sources.md` |

## Python Environment

Always use the pivac venv. It was built without system site packages, so `pip` inside it needs no `--break-system-packages`:
```bash
source ~/pivac-venv/bin/activate
pip install <package>
```

## Dependencies

Key packages: `RPi.GPIO`, `w1thermsensor`, `pytemperature`, `requests`, `PyYAML`, `websocket-client`, `aiosomecomfort` (RedLink — Honeywell mobile API client; replaced the old `mechanize` + `beautifulsoup4` HTML scraper)

## Keeping These Files Current

`CLAUDE.md` loads in every session, so it has a ceiling of 30,000 characters, which `tests/test_claude_md_size.py` enforces. A new fact goes to the narrowest place that holds it:

- **A measurement, an incident, a date-stamped result or the reasoning behind a rule** goes in the matching doc in `docs/`.
- **A rule for one subsystem** goes in that subsystem's file in `.claude/rules/`, as a sentence or two that names the doc holding its evidence. A new doc gets a row in that file's Reference docs table.
- **This file changes only for** a new or retired service or device (the Active Services table, `scripts/pivac-services.sh`, the backup script's lists), a new module (one row in Current Modules), a new URL or key file location, a new topic file (the routing table), or a prohibition that must hold in every session (Hard rules).

Write each of these as the current position; the before and after belong in the commit message. `CLAUDE.md` and `.claude/rules/` changes push directly to master with no PR.

After a change that affects the Pi's overall role (a new nginx site, a new service), also update `claude-contexts/pi-CLAUDE.md`. On the Pi, `~/CLAUDE.md` is a symlink to it, so `git -C ~/github/claude-contexts pull` propagates the update.
