# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working Style

- **Execute without repeated check-ins.** Before a multi-step task, state the plan briefly and confirm once. Then carry out all steps without asking permission at each one.
- **Targeted edits, not rewrites.** When modifying an existing file, make surgical changes to the relevant lines. Do not rewrite or reorder content that isn't changing — it creates noise in diffs and risks dropping things accidentally.
- **PR workflow for code and docs.** Always create a feature branch and open a pull request for code changes, README updates, and module documentation. Only push directly to `master` for meta/context files (CLAUDE.md files). When in doubt, use a PR.
- **Keep CLAUDE.md current.** After significant changes — new architecture, bug fixes, new devices, deployment changes — update this file and include it in the commit.
- **No unnecessary confirmation loops.** Don't ask "should I proceed?" or "does this look right?" mid-task. Finish the work, then summarize what was done.
- **Commit message quality.** Write commit messages that explain why, not just what. Reference the problem being solved, not just the files changed.
- **Prose over bullets in explanations.** When explaining an approach or decision, write in sentences rather than fragmenting everything into bullet lists.

## What This Project Does

**pivac** collects data from Raspberry Pi sensors and outputs standardized JSON. It's a read-only monitoring tool for HVAC/home automation, feeding downstream systems (Signal K, InfluxDB, Grafana, WilhelmSK mobile app).

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

## Related Repositories

The Arduino pressure sensors (10.0.0.114 and 10.0.0.219) are programmed from a separate repo at `~/github/Arduino`. Each is an Arduino UNO R4 WiFi running a minimal HTTP server. See that repo's CLAUDE.md for hardware details, known issues (including hardcoded WiFi credentials), and deployment notes.

## Active Services and Devices

| systemd service         | Module                  | Device                           | IP / Source  |
|-------------------------|-------------------------|----------------------------------|--------------|
| pivac-1wire             | pivac.OneWireTherm      | DS18B20 1-wire temperature sensors | GPIO       |
| pivac-redlink           | pivac.RedLink           | Honeywell thermostat             | internet     |
| pivac-gpio              | pivac.GPIO              | GPIO input pins (relays/switches)| GPIO         |
| pivac-arduino-psi       | pivac.ArduinoSensor     | Hydronic pressure (Fusch 100PSI) | 10.0.0.114   |
| pivac-arduino-therm-psi | pivac.ArduinoSensor     | DHW pressure (Fusch 200PSI)      | 10.0.0.219   |
| pivac-emporia           | pivac.Emporia           | Emporia Vue Gen 2 (house + apt)  | Emporia cloud |

## Key File Locations

- Pivac code: `~/github/pivac/`
- Live config: `/etc/pivac/config.yml`
- Systemd services: `/etc/systemd/system/pivac-*.service`
- Signal K config: `~/.signalk/settings.json`
- Python venv: `~/pivac-venv/` (always use this)
- nginx site config: `/etc/nginx/sites-available/pivac`
- TLS certificate: `/etc/letsencrypt/live/68lookout.dglc.com/` (auto-renews via certbot timer)
- Grafana config: `/etc/grafana/grafana.ini`

## Remote Access

All remote access goes through nginx on the Pi (`10.0.0.82`) over HTTPS. No VPN required.

**External hostname:** `68lookout.dglc.com` → public IP `74.89.220.182` (DNS on AWS Route53; update manually if ISP IP changes)

**Network topology (double-NAT):** Internet → fiber router (`192.168.1.x`) → Unifi router (`10.0.0.x`) → Pi (`10.0.0.82`). TCP ports 80 and 443 are forwarded at both hops.

| URL | Service | Auth |
|-----|---------|------|
| `https://68lookout.dglc.com/admin/` | Signal K admin UI | Signal K own auth |
| `https://68lookout.dglc.com/signalk/` | Signal K API + WebSocket | Signal K own auth |
| `https://68lookout.dglc.com/grafana/` | Grafana | Grafana own login |
| `https://68lookout.dglc.com/sprinkler/` | OpenSprinkler (`10.0.0.17:5000`) | OpenSprinkler own auth |

**WilhelmSK mobile app:** host `68lookout.dglc.com`, port `443`, SSL enabled.

**Signal K behind proxy — Trust Proxy:** The `/signalk/` nginx location block passes `X-Forwarded-Proto: https` and `X-Forwarded-For`. Signal K's "Trust Proxy" setting (Server → Settings in the admin UI) must be enabled for Signal K to use these headers when constructing endpoint URLs. Without it, Signal K advertises `ws://localhost:3000/...` instead of `wss://68lookout.dglc.com/...`, breaking WilhelmSK's WebSocket connection. Verify with: `curl -s https://68lookout.dglc.com/signalk/ | python3 -m json.tool` — `signalk-ws` should show `wss://68lookout.dglc.com/signalk/v1/stream`.

**nginx reload after config changes:**
```bash
sudo nginx -t && sudo systemctl reload nginx
```

## Grafana Sub-path Configuration

Grafana is configured to serve from `/grafana/` sub-path. Key settings in `/etc/grafana/grafana.ini`:
```ini
root_url = https://68lookout.dglc.com/grafana/
serve_from_sub_path = true
```
If these are lost, Grafana will redirect to `/login` with an internal URL and break the proxy.

## Emporia Setup (first time only)

**Already completed on this Pi** — `pivac-emporia.service` is installed, enabled, and running. Device GIDs: house = `194331`, apartment = `265129`. Token cached at `/etc/pivac/emporia-tokens.json`.

If setting up on a new system, run the discovery script to find GIDs:
```bash
source ~/pivac-venv/bin/activate
python ~/github/pivac/scripts/emporia-discover.py --username YOUR_EMAIL --password YOUR_PASSWORD
```
Copy the suggested config block into `/etc/pivac/config.yml`, then install and start the service.

## Standard Deployment Procedure

After a `git pull`:
```bash
sudo systemctl restart pivac-1wire pivac-redlink pivac-gpio pivac-arduino-psi pivac-arduino-therm-psi pivac-emporia
journalctl -u pivac-1wire -u pivac-redlink -u pivac-gpio -u pivac-arduino-psi -u pivac-arduino-therm-psi -u pivac-emporia -n 50 --no-pager
```

If systemd service files were changed:
```bash
sudo cp ~/github/pivac/scripts/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
```

## Checking Logs

```bash
# All pivac services
journalctl -u pivac-1wire -u pivac-redlink -u pivac-gpio -u pivac-arduino-psi -u pivac-arduino-therm-psi -u pivac-emporia -n 50 --no-pager

# Single service
journalctl -u pivac-redlink -n 50 --no-pager

# Signal K server
journalctl -u signalk -n 50 --no-pager
```

## Known Operational Behaviours (Not Bugs)

- **Arduino timeouts**: Both Arduinos (10.0.0.114 and 10.0.0.219) occasionally go unresponsive. Logged as a single WARNING. Self-recover; occasional power cycle needed.
- **RedLink ConnectionResetError**: Honeywell's server occasionally drops HTTPS connections. Self-recovering. Logged as ERROR but normal.
- **RedLink TimeoutError**: Honeywell's server occasionally accepts a connection but stalls mid-response. The 30-second socket timeout (`request_timeout` in config) causes these to fail fast and retry. Logged as ERROR but normal; recovers on the next poll cycle.
- **OneWireTherm SensorNotReadyError**: 1-wire sensors occasionally not ready mid-conversion. Transient, self-recovering.
- **Boot-time WebSocket race**: Pivac services start before Signal K is fully ready. The provider retries the initial WebSocket connection with exponential backoff (up to 6 attempts). No intervention needed.
- **Emporia / PyEmVue API compatibility**: PyEmVue has had multiple undocumented breaking changes (Unit.WATTS removed, get_device_list_usage return type changed, populate_device_properties takes a single device). All fixed in PR #17 against pyemvue 0.18.9. If Emporia starts failing after a `pip upgrade pyemvue`, check those call sites first.

## Adding a New Module

1. Create `pivac/MyModule.py` implementing `status(config={}, output="default")`
2. Add a section to `config.yml` named `pivac.MyModule`
3. Create a systemd service file in `scripts/systemd/`
4. The provider script will auto-discover it

## Current Modules

| Module | Source |
|--------|--------|
| `GPIO` | RPi GPIO pin state |
| `OneWireTherm` | DS18B20 1-Wire temperature sensors |
| `TED5000` | Energy monitor (XML over HTTP) — currently disabled |
| `RedLink` | Honeywell thermostat (web scraping) |
| `FlirFX` | FLIR camera temperature/humidity — currently disabled |
| `ArduinoSensor` | Arduino HTTP sensor (hydronic pressure, DHW pressure) — shared implementation for `pivac.ArduinoPSI` and `pivac.ArduinoThermPSI` config sections via `module:` override |
| `Emporia` | Emporia Vue Gen 2 power monitors — polls two panels (house 200A, apartment 100A) via PyEmVue, emits per-circuit Watts to `electrical.emporia.<panel>.<circuit>` |

## Signal K Upgrade (if needed)

The admin console upgrade fails with ENOTEMPTY. Use the manual procedure:
```bash
sudo systemctl stop signalk
sudo rm -rf /usr/lib/node_modules/.signalk-server-*
sudo npm install -g signalk-server@latest
sudo systemctl start signalk
```

## Python Environment

Always use the pivac venv:
```bash
source ~/pivac-venv/bin/activate
pip install <package> --break-system-packages
```

## Dependencies

Key packages: `RPi.GPIO`, `w1thermsensor`, `pytemperature`, `lxml`, `requests`, `mechanize`, `beautifulsoup4`, `PyYAML`, `websocket-client`, `pyemvue`
