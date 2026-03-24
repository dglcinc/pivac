# CLAUDE.md — pivac (project-specific)

> Working style, machine detection, and GitHub conventions are in the global context:
> `<github-dir>/claude-contexts/CLAUDE.md`

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
| pivac-sentry            | pivac.Sentry            | NTI Trinity Ti-200 boiler (Tapo C120 RTSP) | 10.0.0.19 |

## Key File Locations

- Pivac code: `~/github/pivac/`
- Live config: `/etc/pivac/config.yml`
- Systemd services: `/etc/systemd/system/pivac-*.service`
- Signal K config: `~/.signalk/settings.json`
- Python venv: `~/pivac-venv/` (always use this)
- nginx site config: `/etc/nginx/sites-available/pivac`
- nginx Basic Auth credentials: `/etc/nginx/.htpasswd` (user: dglcinc)
- TLS certificate: `/etc/letsencrypt/live/68lookout.dglc.com/` (auto-renews via certbot timer)
- Grafana config: `/etc/grafana/grafana.ini`
- WireGuard keys (unused, kept for reference): `/etc/wireguard/`

## Remote Access

All remote access goes through nginx on the Pi (`10.0.0.82`) over HTTPS. No VPN required.

**External hostname:** `68lookout.dglc.com` → public IP `74.89.220.182` (DNS on AWS Route53; update manually if ISP IP changes)

**Network topology (double-NAT):** Internet → fiber router (`192.168.1.x`) → Unifi router (`10.0.0.x`) → Pi (`10.0.0.82`). TCP ports 80 and 443 are forwarded at both hops.

| URL | Service | Auth |
|-----|---------|------|
| `https://68lookout.dglc.com/admin/` | Signal K admin UI | nginx Basic Auth |
| `https://68lookout.dglc.com/signalk/` | Signal K API + WebSocket | Signal K own auth |
| `https://68lookout.dglc.com/grafana/` | Grafana | Grafana own login |
| `https://68lookout.dglc.com/sprinkler/` | OpenSprinkler (`10.0.0.17:5000`) | nginx Basic Auth |

**WilhelmSK mobile app:** host `68lookout.dglc.com`, port `443`, SSL enabled. Uses the `/signalk/` path which has no Basic Auth (WilhelmSK doesn't support it). **WilhelmSK Grafana widget:** use `https://68lookout.dglc.com/grafana/` — Basic Auth must be absent from this path or the app crashes.

**WilhelmSK layout file:** `Default.wlyt` lives at `~/OneDrive - DGLC/Claude/Default.wlyt` on the Mac (also the Cowork working folder). To import after edits: copy to "On My iPad" in Files app (can't open directly from OneDrive due to iOS sandboxing), then tap to open in WilhelmSK. Or AirDrop from Mac.

Layout has 2 pages:
- **Page 1** (template `"1"`, 14+ slots): main dashboard — 5 thermostat room tiles, 3 HVAC water temp gauges (In/CRW/Out), switch bank, 2 PSI gauges, Sentry widgets
- **Page 2** (template `"5"`): Grafana WebGauge + SwitchBank

Sentry widgets use these SK paths (all under `hvac.boiler.sentry.*`):
- `hvac.boiler.sentry.waterTemp` — °F, WaterTempGauge type
- `hvac.boiler.sentry.gasInputValue` — integer 40–240, TextGaugeConfig type

**Important — Signal K behind nginx:** The `/signalk/` location block must include `proxy_set_header X-Forwarded-Proto https` and `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for`. Without these, Signal K constructs its WebSocket discovery URL as `ws://localhost:3000/...` instead of `wss://68lookout.dglc.com/...`, causing WilhelmSK to attempt a plain WebSocket connection on port 80, which nginx redirects (301) and breaks the handshake. Signal K's "Trust Proxy" setting must also be enabled in the admin UI.

**nginx reload after config changes:**
```bash
sudo nginx -t && sudo systemctl reload nginx
```

## InfluxDB Version

The Pi runs **InfluxDB 2** (not v1). Use the `influx` CLI with Flux queries — InfluxQL `SHOW MEASUREMENTS` / `SHOW DATABASES` syntax does not apply. Key commands:

```bash
influx bucket list
influx query 'import "influxdata/influxdb/schema" schema.measurements(bucket: "pivac")'
```

Grafana datasource `bdxaqnfllu5fkf` uses the `pivac` bucket via InfluxQL compatibility mode (`dbName: pivac`). Panel queries use InfluxQL syntax (measurement = full SK path, field = `value`).

## Grafana Dashboard Provisioning

**Already completed on this Pi** — provisioning config and systemd override are in place. Dashboards auto-update within 30 seconds of a `git pull`.

Dashboards are version-controlled in `grafana/dashboards/` and loaded automatically by Grafana via a provisioning config. Two one-time setup steps are required on a new Pi:

**1. Copy the provisioning config:**
```bash
sudo cp ~/github/pivac/grafana/provisioning/dashboards/pivac.yaml /etc/grafana/provisioning/dashboards/
```

**2. Create a systemd override so Grafana can read `/home/pi` (blocked by default via `ProtectHome=true`):**
```bash
sudo mkdir -p /etc/systemd/system/grafana-server.service.d
sudo tee /etc/systemd/system/grafana-server.service.d/pivac-dashboards.conf <<'EOF'
[Service]
ProtectHome=read-only
EOF
sudo systemctl daemon-reload && sudo systemctl restart grafana-server
```

After that, any `git pull` on the Pi will automatically update dashboards within 30 seconds (Grafana polls the directory). To update dashboards: edit the JSON in `grafana/dashboards/`, commit, and pull on the Pi. Since `allowUiUpdates: true`, you can also edit in the Grafana UI — but those changes won't persist unless you export the JSON and commit it back.

The second datasource UID `bdj9fji0j5logc` (used by Relays, Temps, Stats, Chiller Time, DHW panels) is a Signal K-managed InfluxDB datasource. It does not appear in the Grafana datasources API but is still functional.

## Grafana Sub-path Configuration

Grafana is configured to serve from `/grafana/` sub-path. Key settings in `/etc/grafana/grafana.ini`:
```ini
root_url = https://68lookout.dglc.com/grafana/
serve_from_sub_path = true
```
If these are lost, Grafana will redirect to `/login` with an internal URL and break the proxy.

## Emporia Setup (first time only)

Before enabling `pivac-emporia.service`, run the discovery script to get device GIDs:
```bash
source ~/pivac-venv/bin/activate
python ~/github/pivac/scripts/emporia-discover.py --username YOUR_EMAIL --password YOUR_PASSWORD
```
Copy the suggested config block into `/etc/pivac/config.yml`, replacing the GID placeholders with real values.

Token is cached at `/etc/pivac/emporia-tokens.json` after first successful login.

## Standard Deployment Procedure

After a `git pull`:
```bash
sudo systemctl restart pivac-1wire pivac-redlink pivac-gpio pivac-arduino-psi pivac-arduino-therm-psi pivac-emporia pivac-sentry
journalctl -u pivac-1wire -u pivac-redlink -u pivac-gpio -u pivac-arduino-psi -u pivac-arduino-therm-psi -u pivac-emporia -u pivac-sentry -n 50 --no-pager
```

If systemd service files were changed:
```bash
sudo cp ~/github/pivac/scripts/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
```

## Checking Logs

```bash
# All pivac services
journalctl -u pivac-1wire -u pivac-redlink -u pivac-gpio -u pivac-arduino-psi -u pivac-arduino-therm-psi -u pivac-emporia -u pivac-sentry -n 50 --no-pager

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
| `Sentry` | NTI Trinity Ti-200 boiler controller via Tapo C120 RTSP camera — reads display via 7-segment CV, emits boiler state to `hvac.boiler.sentry.*` |

## pivac.Sentry Module

**Status:** Fully deployed. `pivac-sentry.service` installed, enabled, and running (2026-03-23).

### Camera Hardware

- **Device:** Tapo C120 IP camera
- **IP address:** `10.0.0.19`
- **RTSP stream URLs:**
  - High quality: `rtsp://USERNAME:PASSWORD@10.0.0.19:554/stream1`
  - Standard quality: `rtsp://USERNAME:PASSWORD@10.0.0.19:554/stream2`
- **Authentication:** Requires a dedicated RTSP username/password set in the Tapo app under Advanced Settings → Camera Account. These credentials are **not** the Tapo cloud account login. Store them only in `/etc/pivac/config.yml` on the Pi — never in the repo or in chat.

### Purpose

Read the Sentry 2100 controller display on the NTI Trinity Ti-200 boiler using the Tapo C120 and emit values as Signal K deltas. The display shows boiler operating data via a 3-digit 7-segment LED, four green LED indicators, and four indicator lights.

### Sentry 2100 Display Hardware

- **3-digit 7-segment LED display**: Shows water temp (°F), outdoor air temp (°F), gas input value (40–240 scale for Ti-200), DHW temp (°F), or error/menu codes (`ER1`–`ER6`, `ER9`, `ASO`, `ASC`, `RUN`, `LO`, `HI`, `dIF`, etc.)
- **4 green LED indicators** (right side of display): Burner/Bruleur, Circ., Circ. Aux., Thermostat Demand — reflect live state regardless of display mode
- **4 indicator lights** (below display): Water Temp, Air, Gas Input Value, DHW Temp — tell you which value the 3-digit display is currently showing
- **Display cycling**: When active, display cycles through modes roughly every 5 seconds (water temp → gas input → outdoor air → DHW temp). Indicator lights identify which mode is active in any given frame.
- **Gas Input Value scale**: 40–240 maps to BTU/hr via the Ti-200 conversion chart in the boiler manual (NTI Trinity Ti100-200 Boiler Installation and Operation Manual, pages 38–50, 61–66).

### Capture Strategy

On each poll cycle, the module opens the RTSP stream and captures frames every ~2.5 seconds for up to 15 seconds (configurable). Each frame is processed immediately — indicator lights determine the display mode, then the digit value is read. The loop exits early once all expected modes have been seen. This ensures all four value types are updated on every poll cycle, giving Grafana clean time series without sparse data gaps. If the boiler is idle and only one mode is visible, the loop times out and emits whatever was captured.

### Computer Vision Approach

**7-segment digit recognition** uses segment state detection (not general-purpose OCR): for each of the three digit positions, the seven segment bounding boxes are checked for brightness against a threshold. The 7-bit segment pattern maps to a character. This handles digits 0–9 and all special LED characters (E, r, A, S, O, C, etc.) needed for error codes.

**LED and indicator detection** uses HSV color space: green LEDs are isolated by hue/saturation range, and brightness in each ROI determines on/off state.

**One-time calibration required**: The module config must specify pixel coordinates for the display ROI, each digit's segment boxes, each LED, and each indicator light. These are stable as long as the camera doesn't move. A calibration utility (`scripts/sentry-calibrate.py`) saves a reference frame from the RTSP stream and helps identify coordinates.

### Signal K Paths

| SK path | Type | Notes |
|---------|------|-------|
| `hvac.boiler.sentry.waterTemp` | number | °F as shown on display; emitted when water_temp indicator lit |
| `hvac.boiler.sentry.outdoorTemp` | number | °F as shown on display; emitted when air indicator lit |
| `hvac.boiler.sentry.gasInputValue` | number | Raw 40–240 scale; emitted when display shows gas input |
| `hvac.boiler.sentry.dhwPriority` | number (0/1) | 1 when DHW priority indicator is lit |
| `hvac.boiler.sentry.errorCode` | string | e.g. `ER3`; null when no error |
| `hvac.boiler.sentry.burnerOn` | number (0/1) | Burner LED state |
| `hvac.boiler.sentry.circOn` | number (0/1) | Circ pump LED state |
| `hvac.boiler.sentry.circAuxOn` | number (0/1) | Circ aux LED state |
| `hvac.boiler.sentry.thermostatDemand` | number (0/1) | Thermostat demand LED state |

Temperature values are raw °F as shown on the display. Boolean indicators are emitted as integer 0/1 (not Python bool) so that InfluxDB stores them as float and Grafana can plot them with mean() aggregation. **Important:** if you ever need to reset these measurements in InfluxDB, you must also restart Signal K after reseeding — the `signalk-to-influxdb2` plugin caches field types in memory and will re-write booleans until the process restarts.

### Config Format

```yaml
pivac.Sentry:
  rtsp_url: "rtsp://USERNAME:PASSWORD@10.0.0.19:554/stream1"
  cycle_timeout: 15          # seconds to wait for full display cycle
  frame_interval: 2.5        # seconds between captured frames
  brightness_threshold: 150  # 0-255, min brightness for a lit segment/LED
  display_roi:               # pixel coords in full camera frame — set during calibration
    x: 120
    y: 80
    w: 200
    h: 60
  digit_positions:           # relative to display_roi — left, middle, right digits
    - {x: 10, y: 5, w: 55, h: 50}
    - {x: 75, y: 5, w: 55, h: 50}
    - {x: 140, y: 5, w: 55, h: 50}
  leds:                      # pixel coords in full frame
    burner:            {x: 350, y: 100}
    circ:              {x: 350, y: 125}
    circ_aux:          {x: 350, y: 150}
    thermostat_demand: {x: 350, y: 175}
  indicators:
    water_temp:        {x: 130, y: 155}
    air:               {x: 160, y: 155}
    gas_input:         {x: 190, y: 155}
    dhw_temp:          {x: 220, y: 155}
```

Note: coordinate values above are placeholders — real values come from calibration.

### Dependencies

- `opencv-python-headless` — frame capture and image processing (headless avoids GUI deps on Pi)
- `numpy` — already in venv

### Implementation Checklist

- [x] Set RTSP camera account credentials in Tapo app (Advanced Settings → Camera Account)
- [x] Add RTSP credentials to `/etc/pivac/config.yml` on Pi
- [x] Implement `scripts/sentry-calibrate.py` — captures reference frame and annotates ROIs
- [x] Run calibration: perspective warp corners, digit positions, LED/indicator coords set
- [x] Populate config with real ROI coordinates (`mode_stable_frames: 3`, `cycle_timeout: 30`)
- [x] Implement `pivac/Sentry.py`
- [x] Create `scripts/systemd/pivac-sentry.service`
- [x] Install service on Pi (`sudo cp`, `daemon-reload`, `enable`, `start`) and verify logs

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

Key packages: `RPi.GPIO`, `w1thermsensor`, `pytemperature`, `lxml`, `requests`, `mechanize`, `beautifulsoup4`, `PyYAML`, `websocket-client`
