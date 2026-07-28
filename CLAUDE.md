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

> **⚠️ The DHW board's recirc-temp firmware is NOT in the repo.** The DS18B20 added to the **.114 DHW board** on 2026-05-31 (serving the `temp` field → `environment.inside.hvac.dhw.recirc.temperature`) runs a sketch that lives **only on David's MacBook (M2) and on the board itself** — it was never committed to `~/github/Arduino`. Flashing the repo's psi-only sketch onto .114 would **silently drop the recirc temperature**. The .219 boiler board serves `psi` only and matches the repo. Re-capture the .114 sketch from M2 before any reflash of that board.

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
| ~~pivac-watermeter~~ (STOPPED + DISABLED 2026-06-27) | pivac.WaterMeter | Sensus iPerl LCD (Tapo RTSP) — camera-CV retired, ESP32-CAM TBD | 10.0.0.85 |
| pivac-sprinkler         | pivac.Sprinkler         | OpenSprinkler irrigation flow (local API)  | 10.0.0.17:5000 |
| pivac-domestic-water    | pivac.DomesticWater     | **Domestic** water meter (DAE MJ-75a, 0.1 gal/pulse) on UNO R4 WiFi | 10.0.0.188 |

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
- WaterMeter glyph templates: `/etc/pivac/wm-templates/` (Pi-local calibration, **not** in repo — `<glyph>_<n>.png`, multiple exemplars per digit; drop in updated/new glyphs and the module hot-reloads on mtime change, no restart)
- nginx site config: `/etc/nginx/sites-available/pivac`
- nginx bowling proxy config: `/etc/nginx/sites-available/mlb.dglc.com` (proxies `mlb.dglc.com` → Mac Mini `10.0.0.84:5001`)
- nginx Basic Auth credentials: `/etc/nginx/.htpasswd` (user: dglcinc)
- TLS certificate: `/etc/letsencrypt/live/68lookout.dglc.com/` (auto-renews via certbot timer)
- Grafana config: `/etc/grafana/grafana.ini`
- WireGuard keys (unused, kept for reference): `/etc/wireguard/`

## Remote Access

All remote access goes through nginx on the Pi (`10.0.0.82`) over HTTPS. No VPN required.

**External hostname:** `68lookout.dglc.com` → public IP `74.89.220.182` (DNS on AWS Route53; update manually if ISP IP changes)

**Network topology (double-NAT):** Internet → fiber router (`192.168.1.x`) → Unifi router (`10.0.0.x`) → Pi (`10.0.0.82`). TCP ports 80 and 443 are forwarded at both hops.

**Pi network interfaces (2026-06-16 — moved off WiFi to wired):** The Pi is **primary on wired ethernet** — `eth0` MAC `d8:3a:dd:b1:ad:4d`, UniFi DHCP-reserved to `10.0.0.82` (route metric 100). `wlan0` is a **WiFi fallback** — fixed IP `10.0.0.130`, joined to SSID `redux` locked to **5 GHz** (`802-11-wireless.band a`, AP in the utility room, ≈-45 dBm), power-save **disabled** (`802-11-wireless.powersave 2`), route metric 600. Failover is automatic by route metric; both settings persist in the `redux` NetworkManager profile across reboots. **Caveat:** the port-forwards target `10.0.0.82`/eth0 only, so the WiFi fallback keeps the Pi alive + SSH-reachable (at `.130`) + collecting data if the wire drops, but external `68lookout.dglc.com` access would **not** auto-fail-over (would need parallel forwards to `.130`). To re-enable WiFi from a console if ever disabled: `nmcli radio wifi on`. The `redux` profile is backed by `/etc/NetworkManager/system-connections/Wireless connection 1.nmconnection` (NM connection *name* `redux` ≠ the *filename*); its on-disk keyfile holds the PSK with `psk-flags=0` (system-owned), `band=a`, and `powersave=2`, which is what lets it autoconnect unattended after a reboot/drop. **If `wlan0` ever fails to rejoin and `journalctl -u NetworkManager` shows `failed (reason 'no-secrets')`, the PSK isn't usable unattended** — re-set it with `nmcli connection modify redux wifi-sec.psk <pw>` (system-owns it, flags 0) and `nmcli connection up redux`. Reconnect manually any time with `nmcli connection up redux`.

| URL | Service | Auth |
|-----|---------|------|
| `https://68lookout.dglc.com/admin/` | Signal K admin UI | nginx Basic Auth |
| `https://68lookout.dglc.com/signalk/` | Signal K API + WebSocket | Signal K own auth |
| `https://68lookout.dglc.com/grafana/` | Grafana | Grafana own login |
| `https://68lookout.dglc.com/sprinkler/` | OpenSprinkler (`10.0.0.17:5000`) | nginx Basic Auth |
| `https://mlb.dglc.com/` | Bowling League Tracker (Mac Mini `10.0.0.84:5001`) | Bowling app auth |

**WilhelmSK mobile app:** host `68lookout.dglc.com`, port `443`, SSL enabled. Uses the `/signalk/` path which has no Basic Auth (WilhelmSK doesn't support it). **WilhelmSK Grafana widget:** use `https://68lookout.dglc.com/grafana/` — Basic Auth must be absent from this path or the app crashes.

**WilhelmSK layout file:** `iphone.wlyt` lives at `~/OneDrive - DGLC/Claude/iphone.wlyt` on the Mac (also the Cowork working folder). To import after edits: copy to "On My iPad" in Files app (can't open directly from OneDrive due to iOS sandboxing), then tap to open in WilhelmSK. Or AirDrop from Mac.

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

**Already provisioned.** Dashboards auto-update within 30s of `git pull`. To update dashboards: edit JSON in `grafana/dashboards/`, commit, and pull on the Pi. Since `allowUiUpdates: true`, you can also edit in the Grafana UI — but those changes won't persist unless you export the JSON and commit it back. One-time new-Pi setup steps are in the git history.

The second datasource UID `bdj9fji0j5logc` (used by Relays, Temps, Stats, Chiller Time, DHW panels) is a Signal K-managed InfluxDB datasource. It does not appear in the Grafana datasources API but is still functional.

**Grafana runtime facts (learned 2026-07-20):** Grafana listens on **port 4000** (not 3000) and serves under the `/grafana/` sub-path — API base is `http://127.0.0.1:4000/grafana/api/...` (admin password is set; not admin/admin). This is a **Grafana 13 unified-storage** install: live dashboards are stored in the **`resource` table** of `/var/lib/grafana/grafana.db`, NOT the legacy `dashboard` table (which is stale — reading it will mislead you). Inspect live panels with `python3 sqlite3` (no `sqlite3` CLI on the Pi). Run InfluxQL directly via the v1 endpoint: `curl -G http://localhost:8086/query --data-urlencode 'db=pivac' --data-urlencode 'q=...' -H "Authorization: Token <active influx token>"`.

**Panel alignment:** every timeseries panel on PivacR pins `custom.axisWidth: 50` so all plot areas share a left edge — keep new panels consistent. Don't set a per-panel `axisLabel` (it renders left of the ticks and pushes that panel's plot right). Note: **state-timeline panels can't set axis/row-label width** (Grafana #85040), so boolean/status data that must line up with the numeric-axis panels should be a **timeseries with stepped lines**, not a state-timeline.

**Water "net of irrigation" convention:** irrigation water flows *through* the domestic meter, so the raw `environment.water.domestic.consumption` totalizer double-counts irrigation. The "Used" stat panels and the hourly bar panel show **Domestic (net) = domestic total − irrigation** (irrigation = `INTEGRAL(environment.water.irrigation.flowRate, 1m)`), green = net domestic, yellow = irrigation. InfluxQL can't subtract across measurements in one query, so it's done with a Grafana transform chain `joinByField(Time) → calculateField(binary A−B) → organize(exclude gross)`. The two aggregates must land on the **same timestamp** to join: `SPREAD` returns the range-start time but `INTEGRAL` returns **epoch 0**, so both stat queries force one epoch-aligned bucket with `GROUP BY time(3650d) fill(0)` (hourly panels `GROUP BY time(1h)` align naturally). The flow-rate panels (18/19) intentionally still show *gross* domestic (they're rates, not totals).

**Shared-y-axis gotcha (timeseries panels):** Grafana only merges two series onto a single y-axis when they share the *same explicit* `axisPlacement` value **and** the same unit grouping. A series on `axisPlacement: auto` and another forced to `left` do **not** dedupe — Grafana renders two stacked left axes, each auto-scaled independently (doubles the left margin and puts the series on different numeric scales). `auto` ≠ `left`. To co-plot close-magnitude series (e.g. the DHW panel's PSI ~64 + recirc temp ~110 °F) on one scale: set *every* series to the same explicit placement and drop differing units (make both unitless) so the axes aren't split by unit. Tradeoff: dropping the unit removes the unit suffix from that series' tooltip. (Fixed on the DHW panel in PRs #65/#66.)

## Grafana Sub-path Configuration

Grafana is configured to serve from `/grafana/` sub-path. Key settings in `/etc/grafana/grafana.ini`:
```ini
root_url = https://68lookout.dglc.com/grafana/
serve_from_sub_path = true
```
If these are lost, Grafana will redirect to `/login` with an internal URL and break the proxy.

## Grafana Alerting → Microsoft Graph email bridge

Grafana's built-in SMTP is disabled (DSM/M365 tenants no longer accept SMTP AUTH for outbound). Instead, alerts route to a small webhook bridge running on the Pi that calls **Microsoft Graph `sendMail`** using the same Azure AD app the bowling-league-tracker uses.

**Components:**
- `scripts/grafana_graph_bridge.py` — stdlib HTTP server listening on `127.0.0.1:8125/alert`. Reformats Grafana's webhook JSON, gets a Graph access token via client-credentials, calls `/v1.0/users/{sender}/sendMail`.
- `scripts/systemd/grafana-graph-bridge.service` — runs as user `pi`, `EnvironmentFile=-/etc/pivac/graph.env`, `Restart=always`.
- `/etc/pivac/graph.env` (mode 640, root:pi, **not** in the repo) — holds `GRAPH_TENANT_ID`, `GRAPH_CLIENT_ID`, `GRAPH_CLIENT_SECRET`, `GRAPH_SENDER_EMAIL`, `ALERT_RECIPIENT`. Same Azure AD app as `~utilityserver/github/bowling-league-tracker/.env` on the Mac Mini.
- `grafana/provisioning/alerting/contact-points.yaml` — defines the `graph-bridge` webhook receiver (POSTs to the bridge) and a default policy that routes everything to it.
- `grafana/provisioning/alerting/redlink-stale.yaml` — three RedLink alerts, all routing to `graph-bridge`:
  - `redlink-stale` (warning) — last 30m of `environment.inside.thermostat.MASTER_BR.temperature`. Canonical "definitely broken" signal. `noDataState: Alerting`.
  - `redlink-stale-fast` (info) — same metric, 10m window. Earlier warning that data flow has stopped. `noDataState: Alerting`.
  - `redlink-error-burst` (warning) — fires when `environment.inside.thermostat.redlink.consecutiveErrors > 2` for 5m. Reads the new health-counter the module emits every cycle. `noDataState: OK` (the freshness alerts cover the no-data case). The runbook in the alert directs the responder to query `environment.inside.thermostat.redlink.lastErrorType` to identify the failure mode (e.g. `UnexpectedResponse` = aiosomecomfort can't parse Honeywell's reply, signal that the library or scraper fallback may be needed).
- `grafana/provisioning/alerting/sensor-freshness.yaml` — 1-wire freshness + outdoor cross-check, group `sensor-data-freshness`, all routing to `graph-bridge`. All temps are stored in **Kelvin**, so the staleness rules reuse the same `value < 100` never-true sentinel as `redlink-stale` and rely on `noDataState: Alerting`:
  - `hydronic-{in,crw,out}-stale` (warning) — per-sensor 30m staleness on `environment.inside.hvac.{IN,CRW,OUT}.temperature`. One rule each so the email names which sensor dropped (the per-sensor isolation fix means a single bad DS18B20 no longer stales the others). OUT's runbook flags its history of intermittent w1-bus dropouts.
  - `outside-onewire-stale` (warning) — 30m staleness on `environment.outside.temperature` (the physical AMB DS18B20).
  - `outside-temp-divergence` (info) — fires when `abs(environment.outside.temperature − environment.outside.thermostat.temperature) > 8 K` (~14 °F) sustained for 1h. Catches a single drifting/failed outdoor sensor while its data is still "fresh". `noDataState: OK` so a thermostat with no outdoor sensor (thermostat path absent) never trips it. Baseline divergence observed ≈1 K.
  - `circ-temp-stale` (warning) — 30m staleness on `environment.inside.hvac.dhw.recirc.temperature` (the DHW recirc-loop DS18B20 on the Arduino at 10.0.0.114). Freshness only; the pump-health/"loop cold" alert is intentionally deferred (on-demand/aquastat loop — see `docs/circ-loop-temp-monitoring-plan.md` §8.3).
  - `arduino-dhw-psi-stale` / `arduino-hydronic-psi-stale` (warning, added 2026-07-16) — 30m staleness on the two pressure Arduinos' PSI paths (`electrical.ac.arduinoPSI.psi` = DHW board 10.0.0.114; `electrical.ac.arduinoThermPSI.psi` = boiler/hydronic board 10.0.0.219 — names inverted vs role, see Active Services). PSI is never negative so the never-true sentinel is `value < -1` + `noDataState: Alerting` (same shape as `domestic-water-stale`). These boards were previously the only sensors with **no** freshness alert — a 2026-07-16 mains blip left the .219 board off WiFi and silently stale for 16h. Each rule's runbook points at the `arduino-watchdog` auto-recovery (below) and the manual Shelly power-cycle recipe.
- `grafana/provisioning/alerting/domestic-water.yaml` — domestic water meter leak + freshness alerts (group `domestic-water`, added 2026-07-03), all routing to `graph-bridge`. **Both leak rules are irrigation-aware** — sprinkler water flows *through* the domestic meter, so OpenSprinkler's `environment.water.irrigation.*` gates them (irrigation NoData is replaced with 0 so a down sprinkler service can't silently disarm leak alerting):
  - `domestic-flow-continuous` (warning) — `flowing == 1` for the entire trailing 3h **and** irrigation never active in that window (an overnight multi-zone run would otherwise false-trip every time). Catches running toilets / slow leaks. `noDataState: OK`.
  - `domestic-flow-high` (warning) — **net** household flow (domestic − irrigation `flowRate`) averaging > 12 gpm over 15m, `for: 10m`. Stays armed *during* sprinkler runs. Threshold is a first guess pending a usage baseline.
  - `domestic-water-stale` (warning) — 30m freshness on `environment.water.domestic.consumption` (never-true `< -1` sentinel + `noDataState: Alerting`, same pattern as sensor-freshness). Node keeps counting locally during an outage (EEPROM totalizer), so consumption catches up on recovery.

- `grafana/provisioning/alerting/sentry-boiler.yaml` — Sentry boiler-display alerts, group `sentry-boiler`, all routing to `graph-bridge` (added 2026-07-28). Unlike the 1-wire rules these paths are raw **°F**, not Kelvin, so the never-true staleness sentinel is `value < -100`:
  - `sentry-watertemp-stale` (warning) — 30m staleness on `hvac.boiler.sentry.waterTemp`. The direct alert for the calibration-drift failure below. `noDataState: Alerting`.
  - `sentry-cycle-stale` (warning) — 30m staleness on `hvac.boiler.sentry.gasInputValue`, which is emitted **every** cycle (idle-fills to 0), so it stops only if the service/camera/RTSP died. Pairs with the rule above: **both firing = reader dead; only waterTemp firing = the CV can no longer read the digits.** That distinction is readable straight from the email, without logging in.
  - `sentry-outdoor-divergence` (info) — `hvac.boiler.sentry.outdoorTemp` (°F) vs `environment.outside.temperature` (K, converted in a math node) differing >10 °F for 2h. The **only** rule that can catch a CV emitting *fresh but wrong* values — the mode that hid the 2026-07-28 drift for 12 days. Threshold/duration are deliberately loose (the two sensors sit apart and see different sun; baseline divergence ≈1–4 °F). `noDataState: OK`.

**Test the bridge end-to-end:**
```bash
curl -sS -X POST http://127.0.0.1:8125/alert -H 'Content-Type: application/json' \
     -d '{"status":"firing","title":"test","alerts":[{"status":"firing","labels":{"alertname":"x"},"annotations":{"summary":"hello"}}]}'
```
Should return `ok` and an email arrives at `david@dglc.com`.

**Deployment after editing the YAMLs or the bridge:**
```bash
# script/service:
sudo cp ~/github/pivac/scripts/systemd/grafana-graph-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl restart grafana-graph-bridge
# provisioning YAMLs (Grafana copies, not symlinks — must restart to pick up changes):
sudo cp ~/github/pivac/grafana/provisioning/alerting/*.yaml /etc/grafana/provisioning/alerting/
sudo chown root:grafana /etc/grafana/provisioning/alerting/{contact-points,redlink-stale,sensor-freshness,domestic-water,sentry-boiler}.yaml
sudo chmod 640         /etc/grafana/provisioning/alerting/{contact-points,redlink-stale,sensor-freshness,domestic-water,sentry-boiler}.yaml
sudo systemctl restart grafana-server
```

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
sudo systemctl restart pivac-1wire pivac-redlink pivac-gpio pivac-arduino-psi pivac-arduino-therm-psi pivac-emporia pivac-sentry pivac-watermeter pivac-sprinkler pivac-domestic-water
journalctl -u pivac-1wire -u pivac-redlink -u pivac-gpio -u pivac-arduino-psi -u pivac-arduino-therm-psi -u pivac-emporia -u pivac-sentry -u pivac-watermeter -u pivac-sprinkler -u pivac-domestic-water -n 50 --no-pager
```

If systemd service or timer files were changed:
```bash
sudo cp ~/github/pivac/scripts/systemd/*.service ~/github/pivac/scripts/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
```

**Before SD card maintenance, extended downtime, or rsync** — stop all services that write to disk:
```bash
sudo systemctl stop pivac-1wire pivac-redlink pivac-gpio pivac-arduino-psi pivac-arduino-therm-psi pivac-emporia pivac-sentry pivac-watermeter pivac-sprinkler pivac-domestic-water signalk influxdb nginx
```
Stop order matters: pivac services first (they push to Signal K), then signalk (writes its own store and feeds influxdb), then influxdb (the database), then nginx (terminates external connections including the `mlb.dglc.com` bowling proxy). The bowling app DB is on the Mac Mini — stop `com.dglc.bowling-app` there separately if doing Mac maintenance. Services with `Restart=always` will restart automatically on boot; nginx does not, so start it explicitly after the swap: `sudo systemctl start nginx`.

## Backup Automation

`nas-image-backup.timer` runs `nas-image-backup.service` on the 1st of each month at 03:00 EDT. The service runs `scripts/nas-image-backup.sh`, which mounts the NFS share, stops the disk-writing services, runs `image-backup` against `/mnt/nas-pi-backups/pivac.img`, and restarts services on EXIT. Typical incremental: ~2 minutes downtime. See `~/CLAUDE.md` Backup section for the full architecture (NAS share, NFS+ACL gotcha, bootstrap caveats).

> **nginx is deliberately NOT in this script's stop set** (unlike the SD-maintenance stop list in Standard Deployment Procedure, which legitimately stops it because you're pulling the card). nginx holds no database, so quiescing it adds nothing to image consistency, but stopping it blacks out the `mlb.dglc.com` bowling proxy (whose DB lives on the Mac Mini, unaffected by Pi service stops) and trips the Grafana mlb-availability alert. Observed 2026-06-01: the first auto-run woke David with an mlb alert that was purely the backup window. The script now keeps nginx up — mlb stays available throughout the ~2-min backup.

> **Two failure modes fixed 2026-06-01** (first monthly auto-run failed on both): **(1)** the `.img` root partition was sized to usage + minimal slack at 2026-05-08 bootstrap (54.4 G) and the live root outgrew it (54.9 G) → rsync `ENOSPC`. `image-backup` never resizes an existing image on incrementals. Fix: grew `pivac.img` in place to the full card size (`truncate` to 119.2 G → `parted resizepart 2 100%` → `e2fsck` → `resize2fs`), restoring the MBR disk identifier to `0xf9199e61` afterward (parted regenerates it; it must match the source card so the image's `PARTUUID=` fstab/cmdline refs stay bootable). Now ~63 G free inside the image. **(2)** rsync exit 23 on `/home/pi/thinclient_drives`, an `xrdp-chansrv` FUSE mount that exists only while an RDP session is active — root can't traverse it. Fix: the script now passes `image-backup -o '--exclude=/home/pi/thinclient_drives'`. The 2026-05-08 bootstrap missed both because the system was smaller and had no live RDP session.

`sd-clone.timer` runs `sd-clone.service` weekly (Sunday 02:00 EDT). The service runs `scripts/sd-clone.sh`, which auto-discovers the populated slot of the USB SD reader by USB VID:PID `05e3:0764` (Anker USB 3.0 Micro SD Card Reader, Genesys Logic chipset), refuses if the target matches the booted disk, then calls `rpi-clone <target> -U`. No service stop — `rpi-clone` is designed for live cloning. First run repartitions and takes ~30 min; subsequent incrementals are ~3 min. The clone is a directly bootable hot-recovery spare: pull live SD, drop the spare in, reboot. Install dependency: `rpi-clone` from `~/github/rpi-clone` (billw2/rpi-clone), copied to `/usr/local/sbin/`.

## Shelly Plugs (remote power-cycling)

Two **Shelly Plug US Gen4** (`S4PL-00116US`, FW `1.7.99-plugusg4prod1`) on WiFi SSID `redux`, **local API auth disabled** (open RPC), also cloud-connected. From a four-pack; two spare units not yet powered. Each is **DHCP with a UCG fixed-IP reservation** (device stays portable — the reservation pins the IP by MAC, no factory reset needed to relocate; set via the UCG classic API `PUT /proxy/network/api/s/default/rest/user/<_id>` with `use_fixedip/fixed_ip/network_id`).

| Name | MAC | IP (reserved) | Cloud id | Powers |
|------|-----|---------------|----------|--------|
| **Arduinos** | `ac:eb:e6:f4:b9:30` | `10.0.0.61` | `acebe6f4b930` | The two UNO-R4 pressure boards (.114 DHW + .219 boiler) → the `arduino-watchdog` power-cycle target |
| **PivacPower** | `ac:eb:e6:f6:45:20` | `10.0.0.118` | `acebe6f64520` | General pivac-side mains (the Pi) |

**Power-on default:** both set to `initial_state="on"` (2026-06-23) so after a mains outage the plug auto-restores power and the Pi + Arduinos boot unattended (out-of-box default was `"off"`, which would have left gear dark after a blip). Set via `POST /rpc/Switch.SetConfig {"id":0,"config":{"initial_state":"on"}}`.

**Naming is 3 independent layers that don't auto-sync:** Shelly app/cloud label (rename in app only — local API can't reach it), local device name (`Sys.SetConfig {"device":{"name":…}}`), and UCG client name. All three are currently consistent on both plugs.

**Control (local, no cloud):**
- Power-cycle: `POST http://<ip>/rpc/Switch.Set -d '{"id":0,"on":false}'` then `…"on":true` (also usable as `GET …/rpc/Switch.Set?id=0&on=false`).
- Power/energy: `GET http://<ip>/rpc/Switch.GetStatus` (Gen4 exposes W + Wh) — basis for a future `pivac.Shelly` module → `electrical.*` if ever integrated.
- Identity probe (no creds): `curl http://<ip>/shelly`. Discover any Shelly by probing `/shelly` across ARP hosts, or query the UCG client list (faster, authoritative).

**Cloud Control API (off-LAN, configured 2026-06-23):** Auth Cloud Key at `~/.config/shelly/cloud.key` (mode 600), region server at `~/.config/shelly/cloud.server` = `shelly-266-eu.shelly.cloud`. Example: `curl -X POST https://<server>/device/all_status --data-urlencode "auth_key=$(cat ~/.config/shelly/cloud.key)"` → both plugs' `switch:0.output`/`apower`. On-LAN prefer local RPC + UCG; cloud is for remote only. Key is account-wide (revoke/regenerate at `control.shelly.cloud` → Authorization Cloud Key) — **never put it in chat or the repo.**

## Arduino Watchdog (auto-recovery for the pressure boards)

`arduino-watchdog.timer` runs `scripts/arduino-watchdog.sh` every 5 min (`OnBootSec=5min`, then `OnUnitActiveSec=5min`). It pings the two pressure boards (10.0.0.114 DHW, 10.0.0.219 boiler/hydronic) and, if **either** is unreachable for a sustained `DOWN_THRESHOLD_S` (default **900 s / 15 min**), power-cycles the shared "Arduinos" Shelly plug (`10.0.0.61`, open local RPC) via `Switch.Set off → sleep 8 → on`, rate-limited to at most once per `CYCLE_MIN_INTERVAL_S` (default **3600 s / 1 h**). This is the self-healing counterpart to the `arduino-*-psi-stale` freshness alerts: the alerts tell you, the watchdog fixes it.

**Why it exists:** the pivac provider services have `Restart=always`, but that cannot recover a board that is off WiFi — the service isn't crashing, the *board* is dark. After a power event the .219 board in particular sometimes reboots but fails to rejoin WiFi and sits stale until power-cycled (root-caused 2026-07-16: a mains blip cycled both boards + rebooted the Pi; .114 rejoined, .219 stayed dark 16h until a manual Shelly cycle). The watchdog automates exactly that manual recovery.

**Design notes:** state lives in tmpfs (`/run/arduino-watchdog/`) so it resets on reboot — boards get a fresh grace period after a power event rather than being cycled on stale state. Cycling the shared plug briefly drops the *healthy* board too (recovers in seconds — accepted tradeoff). It **only** touches the Arduinos' plug (`.61`), never the Pi's own plug (PivacPower `.118`). A truly dead board (reboots but never rejoins) is cycled at most once/hour and the freshness alert emails in parallel. Tunables are env-overridable in the `.service` (`DOWN_THRESHOLD_S`, `CYCLE_MIN_INTERVAL_S`, `OFF_DWELL_S`, `PROBE_RETRIES`). Watch it with `journalctl -u arduino-watchdog -n 30` (silent on the happy path — logs only when a board is down or a cycle is issued).

Deploy after editing the script/units:
```bash
sudo cp ~/github/pivac/scripts/systemd/arduino-watchdog.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now arduino-watchdog.timer
```

## Checking Logs

```bash
# All pivac services
journalctl -u pivac-1wire -u pivac-redlink -u pivac-gpio -u pivac-arduino-psi -u pivac-arduino-therm-psi -u pivac-emporia -u pivac-sentry -u pivac-watermeter -u pivac-sprinkler -u pivac-domestic-water -n 50 --no-pager

# Single service
journalctl -u pivac-redlink -n 50 --no-pager

# Signal K server
journalctl -u signalk -n 50 --no-pager
```

## Known Operational Behaviours (Not Bugs)

- **Provider WebSocket must be READ, not just written (root-caused + fixed 2026-07-05, PR #86)**: Signal K's ws interface heartbeats every client each `wsPingInterval` (default 30 s) and terminates any client that hasn't ponged by the next sweep — and Python `websocket-client` only auto-answers pings inside `recv()`. The provider was send-only, so **every pivac service's WS connection was heartbeat-killed ~60 s after connect, then silently lost up to ~30 s of deltas** (writes into the dead socket don't error until the TCP RST) before `Broken pipe` forced a re-login — a chronic ~90 s connect/blackout/reconnect cycle (~6 re-logins/min in the signalk journal, ~30 s data gaps per cycle per service). Invisible on slow thermostat paths; glaring on the 1 Hz domestic-water tiles (20–40 s WilhelmSK "display lag", initially misdiagnosed as an app bug — see `claude-contexts/wilhelm/water-tile-lag-diagnosis.md`). Fix: `pivac-provider.py` runs a daemon reader thread per connection (drains frames → pongs sent → close detected immediately). **Diagnostic signature if it ever regresses:** `journalctl -u signalk | grep -c auth/login` climbing ~6/min + `Broken pipe → reconnect attempt` warnings across services. NB some pre-fix "Honeywell flakiness" / RedLink 30–60 s path gaps were likely really these blackout windows. Post-fix tap-to-tile latency floor is ~4–7 s (0.1 gal/pulse meter physics + 1 Hz pivac poll + ~1 Hz app refresh) — that part is not a bug.
- **Sprinkler flow — meter REPLACED + recalibrated 2026-06-20**: The irrigation flow sensor is now a **DAE AS200U-75P** (¾", single-jet, **1 gal/pulse**, NSF61, 2-wire dry-contact reed) wired to OpenSprinkler **SN1 + GND** (no polarity, no power), replacing the oversized/unreliable GREDIA hall sensor (≤0.0025 gal/pulse AND >50 Hz over most of its range — a bad OS match; see `docs/domestic-water-node-build-spec.md` for the full meter-selection rationale). `pivac.Sprinkler` computes flow as `(flcrt/flwrt)*fpr*60*flow_scale` gal/min from the `/jc` API. **`fpr = 1.0`** (in `/etc/pivac/config.yml`; `flow_scale` 1.0), **confirmed by a clean meter-register calibration 2026-06-20**: a 5-min "Middle Next to House" run moved the AS200U register **28.0 gal in ~5.1 min ≈ 5.5 gpm**, matching pivac's reported steady **5.4** / mean **5.57** gpm to within ~1% (meter is ±1.5%). The old contaminated GREDIA-era `fpr=0.0025`/`0.00524` figures **and their InfluxDB irrigation data (`environment.water.irrigation.flowRate`/`.active`, ~12k pts) were deleted** — Grafana's Irrigation series starts fresh from here. NB `flcrt/flwrt` is OS's *realtime flow proxy*, not a raw pulse count, so `fpr` is empirically calibrated against the meter, not assumed from gal/pulse — though here they coincide at 1.0. Because the AS200U is exactly 1 gal/pulse, the OS **device** `fpr` is now representable as **1.00** (set in the app → Edit Options → Advanced) so the OS app/`/jl` log read correctly too; pivac keeps `fpr=1.0` explicitly regardless. `/jl` flow-log entry format = `[program, station, duration_s, end_unixtime, flow]` — **`flow` is the run's *average flow rate*, not a volume**; multiply by `duration_s/60` for gallons, or read pivac's continuously-integrated total in Grafana (verified 2026-06-21: pivac integral 983.9 gal ≈ meter 984 gal for an overnight 6-zone run). **OS UI unit-label gotcha:** OpenSprinkler does *no* unit conversion — it stores flow as the bare number `pulse_count × fpr`, which with `fpr=1.0` on the 1-gal/pulse AS200U is *already gallons*. The unit shown in the app (logs, water-use totals) is only a cosmetic label set by the **Flow Pulse Rate unit dropdown** (Edit Options → Advanced, beside the `1.00` value). If that dropdown is left at the default **L/pulse**, every flow readout is tagged "L" while the values are actually gallons — converting them (÷3.785) makes usage look ~3.8× low. Fix = set the dropdown to **gal/pulse**, keep the value **1.00**. This is display-only: it does not affect the calibration, and **pivac/Grafana are independent of it** (pivac applies its own config `fpr`, not the device label). Auth is **md5 of the OS *device* password** (`/jc` returns `{"result":2}` when wrong) — **not** the nginx `/sprinkler/` Basic-Auth login. To recalibrate: clean zone run, read register before/after, `fpr_new = fpr × (true_gpm ÷ pivac_gpm)`.
- **Irrigation watering schedule + cost basis (Mountain Lakes NJ, resolved 2026-07-06)**: 68 Lookout Rd is house **#68 → even → even-day watering**. Borough ordinance § 237-10 mandates **June–Sept odd/even-day watering by house number, only 12:01–10am & 6pm–midnight, none Jul 31 / Aug 31**. Set **OpenSprinkler Program 1 restriction = Even days** (kept the 1:00am start; OS even/odd auto-skips the 31st, so Jul31/Aug31 are covered). There is **no borough deduct meter**, so irrigation is billed at the domestic water tiers **plus** $0.6938/100gal sewer (marginal ≈ **$1.19/100gal**) — sprinkler water is *not* sewer-exempt here without a deduct meter. Pre-change it ran daily at weather-level 149%, ~830 gal/run-day (~8,486 gal/30d); the even-day change should roughly halve that — verify by integrating `environment.water.irrigation.flowRate` (InfluxDB, AS200U meter) over ~2 weeks. OS query recipe: `md5=$(sudo grep -A30 pivac.Sprinkler /etc/pivac/config.yml | grep password_md5 | awk '{print $2}')`; then `/jp?pw=$md5` (programs), `/jo` (options incl. `wl` weather level), `/jc` (rain-delay `rd`, flow) against `http://10.0.0.17:5000`. The full municipal-code KB (grep-indexed) is at `~/OneDrive - DGLC/Claude/mountain-lakes-code/` — see global memory `reference/mountain-lakes-code.md`; water rates + watering rules distilled in its `water-schedule-reference.md` (§ 111-3C rates, § 237-10 restrictions).
- **WaterMeter (domestic iPerl) camera-CV reader RETIRED 2026-06-17 — `pivac-watermeter.service` STOPPED**: the Tapo-RTSP + custom-CV approach (`pivac/WaterMeter.py`, binary template matching) proved **unreliable** — it doesn't generalize across digit positions (read true `627713` as `627177`) and direct 7-segment decode fails on this low-contrast LCD; it was emitting garbage spikes/under-reports. Root cause is low LCD contrast that better lighting can't fix here (and the Tapo rig isn't a good permanent install). **Path forward = an AI-on-the-edge ESP32-CAM** (on-device trained CNN + self-lit close-up imaging) — see `docs/water-meter-camera-hardware-options.md` (currently on PR #68 branch). The bad domestic InfluxDB data was deleted. **Superseded 2026-07-03: `environment.water.domestic.*` has a live source again — the `pivac-domestic-water` service reading the DAE MJ-75a pulse meter** (see the Active Services table; the ESP32-CAM/camera path is dead). The `pivac.WaterMeter` module + `/etc/pivac/wm-templates/` remain in the repo but the service is stopped.
- **Whole-Pi "hung again" was WiFi, not pivac (root-caused + fixed 2026-06-16)**: Symptom was the entire Pi off the network (ping "Host is down", ARP `incomplete`) — *not* a hung service. Root cause was **WiFi power-save on a weak 2.4 GHz link**: the radio slept, the AP dropped the station, the supplicant failed to re-associate, DNS started failing (`Name or service not known` across RedLink/Emporia/Sentry), then the host fell fully off the wire and needed a power-cycle. Ruled out as causes: power (`vcgencmd get_throttled` = `0x0`), SD/filesystem (no ext4/IO errors), temp (54.5°C), signal (-58 dBm is fine). **Permanent fix: moved the Pi to wired ethernet** (see Remote Access → Pi network interfaces). If a future hang recurs, first check whether it's the whole host (ping/ARP from another LAN box) vs a single service, then `vcgencmd get_throttled` and `nmcli device status` before assuming pivac.
- **RedLink after a network/DNS outage needs a clean restart**: When the Pi boots into (or rides through) a DNS-less window, `pivac-redlink` accumulates a half-broken Honeywell session *and* a repeatedly-dropping SignalK WebSocket (`Broken pipe` → reconnect), and limps for many cycles even after DNS recovers. Once `getent hosts mytotalconnectcomfort.com` resolves again, `sudo systemctl restart pivac-redlink` gives it a fresh login + fresh WebSocket and all 5 rooms republish within ~2 min. This is **not** the `APIRateLimited` case the rate-limit note warns against restarting — check the logs for `APIRateLimited` first; if absent, restart is the right move.
- **Arduino timeouts**: Both Arduinos (10.0.0.114 and 10.0.0.219) occasionally go unresponsive. Logged as a single WARNING. Self-recover; occasional power cycle needed.
- **Pressure board stuck off WiFi after a power event — now auto-recovered (2026-07-16)**: A brief **mains power failure** cycles both pressure Arduinos (shared Shelly `.61`) *and* reboots the Pi (on PivacPower `.118`, `initial_state=on`). The Pi and the .114 DHW board reliably rejoin WiFi; the **.219 boiler/hydronic board sometimes does not** and sits dark — the pivac service stays `active` (the board is offline, not the service), the module logs only a single WARNING, and (until 2026-07-16) there was no freshness alert, so `electrical.ac.arduinoThermPSI.psi` went silently stale for **16h** before a manual Shelly power-cycle recovered it. Two mitigations now exist: **(1)** `arduino-watchdog.timer` auto-power-cycles the `.61` Shelly after a board is unreachable >15m (see Arduino Watchdog section); **(2)** `arduino-{dhw,hydronic}-psi-stale` Grafana alerts email at 30m staleness. Diagnostic: a low `uptime_ms` in the board's `GET /` = recently rebooted (power event); `Destination Host Unreachable` / `http=000` = off WiFi. Manual recovery is the Shelly cycle: `curl "http://10.0.0.61/rpc/Switch.Set?id=0&on=false"; sleep 8; curl "http://10.0.0.61/rpc/Switch.Set?id=0&on=true"` (drops both boards briefly).
- **RedLink slow first call after restart**: Login + discover takes ~75s on the Pi (vs ~1.7s on macOS). After that, cached-session polls run in ~1.6s. The slow first call is Python 3.13 + Honeywell's redirect-heavy login flow with TLS handshakes; not a bug. The service runs at `--loglevel WARNING` so the cycle warning + per-device refresh failures are visible — at `--loglevel ERROR` the WARNING-level cycle log was silently dropped, hiding ~56s outliers and unhandled-exception session resets that masqueraded as "occasional flicker".
- **RedLink uses force_close + IPv4-only**: `aiohttp.TCPConnector(force_close=True, family=socket.AF_INET)` is required on the Pi — Python 3.13 + aiohttp's keep-alive pool hangs the second HTTPS request to mytotalconnectcomfort.com indefinitely, and IPv6 attempts add seconds to login. Don't remove these settings without re-validating on the Pi.
- **RedLink transient API errors**: Honeywell's mobile API occasionally returns timeouts, dropped connections, or `SessionTimedOut`. The `aiosomecomfort` library raises a typed exception which the module catches, logs as WARNING, tears down the session, and retries on the next poll. Per-device refresh failures are isolated — if one of the five thermostats stalls, the others still publish.
- **RedLink parallel refresh + per-device deadline**: Devices are refreshed concurrently via `asyncio.gather(..., return_exceptions=True)` and each `dev.refresh()` is bounded by `REFRESH_DEADLINE = 12s` via `asyncio.wait_for`. Independent of `request_timeout` in config — that knob only governs the aiosomecomfort client used for login (which legitimately needs ~75s on Pi cold start; cutting it short causes `AuthError: Null cookie connection error 200`). A WARNING fires if any cycle exceeds 20s.
- **RedLink: don't reset session on transient timeouts**: `status()` only calls `_reset()` for `AuthError`, `APIRateLimited`, `SessionTimedOut`, or `UnauthorizedError` — not for plain `TimeoutError` or other transients. Earlier code reset on every exception, which forced a fresh ~75s login on every transient, producing visible 60–90s flicker in WilhelmSK during otherwise normal Honeywell flakiness. `_connect()` also splits login from discover so a discover-time timeout doesn't burn the auth session. `UnauthorizedError` (Honeywell 401 "Key Expired?") is raised inside `dev.refresh()` and was originally swallowed by `_refresh_one`'s catch-all — every device hit the same 401 every cycle and the session never recovered until the service was restarted by hand (observed 2026-05-12 after ~2 days of continuous uptime). `_refresh_all` now re-raises any `UnauthorizedError` from the gather results so `status()` can `_reset()` and re-login on the next cycle.
- **RedLink: 12s deadline beats 20s, empirically**: Bumping `REFRESH_DEADLINE` from 12s to 20s **doubled** the per-device failure rate (~12% → ~25%) — Honeywell appears to rate-limit parallel requests, and a longer deadline lets the rate-limiter saturate. Longer cycles also caused mid-cycle WebSocket-to-SignalK disconnects, producing 100s+ gaps on individual SK paths during reconnect windows. Don't raise `REFRESH_DEADLINE` "to give it more time" — that's the wrong direction.
- **RedLink baseline freshness**: Steady-state SK delta gaps for any one path are 5–17s typical, with occasional 30–60s gaps when one specific device times out 2–3 cycles in a row. Per-device timeout rate hovers around 15–25% on the Pi (Honeywell + force_close=True + Pi network combination); failed devices skip a cycle but the cycle itself completes fast and the others publish. WilhelmSK widgets will show occasional dark-green/red flicker on individual paths during multi-cycle device timeouts — this is Honeywell-side and not currently fixable in our code.
- **RedLink rate-limiting**: If too many fresh logins happen in close succession, `aiosomecomfort` raises `APIRateLimited` (its own `MIN_LOGIN_TIME = 600s` guard). Module logs a warning and skips the cycle. Persistent session caching means this should be rare in steady state. **Recovery floor is ~10 min**: even after the root cause clears, the rate limiter holds the module out until `MIN_LOGIN_TIME` expires. Verified during a 2026-05-08 alert simulation — real outages will look the same. Don't restart the service to "fix" an apparent stuck-cooldown; just wait.
- **OneWireTherm SensorNotReadyError**: 1-wire sensors occasionally not ready mid-conversion. Transient, self-recovering.
- **Boot-time WebSocket race**: Pivac services start before Signal K is fully ready. The provider retries the initial WebSocket connection with exponential backoff (up to 6 attempts). No intervention needed.
- **Weekly Sunday-midnight reboot**: `/etc/crontab` runs `reboot now` every Sunday at 00:00 EDT as a routine system reset. All pivac services (`Restart=always`) come back automatically. Expect one cold-start RedLink cycle (~100s discover timeout, then ~75s login) in the first post-reboot minute — the documented "slow first call after restart" path. WilhelmSK thermostat tiles will flicker dark briefly around 00:00 every Sunday; not a regression. See `~/CLAUDE.md` "This Machine" for the reboot rationale.
- **OneWireTherm per-sensor isolation (FIXED 2026-05-31, PR pending)**: `pivac.OneWireTherm.status()` now wraps the per-sensor read in a try/except inside the `for sensor in sensors` loop (same isolation pattern as RedLink `_refresh_one`). A transient `SensorNotReadyError` (or any per-sensor failure) is logged as a WARNING (`OneWireTherm sensor <id> read failed (...); skipping this cycle`) and the loop `continue`s, so the healthy sensors still publish. **Prior behaviour (the bug):** any one DS18B20 throwing mid-cycle bubbled up to `pivac-provider.py:171`'s module-level catch, the whole cycle was skipped, and NO 1-wire values published — all three hydronic water-temp gauges (In/CRW/Out) went stale together even when only one sensor was bad. Confirmed live 2026-05-31: sensor `0516a365d8ff` (OUT) dropped off the w1 bus and silenced IN/CRW/AMB for ~7.5h; after the weekly reboot it re-enumerated and reads normally (the dropout was intermittent, not a dead sensor). Note this isolates the *per-cycle read*; the older crash-loop on `NoSensorFoundError` at module import (when the bus is so unreliable a configured sensor won't instantiate at all) is a separate failure mode still recovered only by reboot — `sensors = W1ThermSensor.get_available_sensors()` runs once at import (line 19).
- **OneWireTherm bus is now re-scanned every cycle — boot-race empty enumeration self-heals (FIXED 2026-07-06, PR pending)**: `pivac.OneWireTherm` used to scan the w1 bus **once at import** (`sensors = W1ThermSensor.get_available_sensors()`, line 19). The kernel takes a few seconds to enumerate the DS18B20s after a cold boot, but the systemd service starts immediately — so on essentially **every power cycle** the module cached an empty/partial sensor list and ran `active` but silently published nothing until a manual `restart pivac-1wire`. Root-caused live 2026-07-06 (power cycle 11:41:55 → service started 11:42:13 → all 1-wire SK paths stale, no journal errors). Fix: `status()` now calls `_scan_sensors()` at the top of every cycle, so a bus that isn't ready at boot — **or a sensor that drops off and returns mid-run** (the OUT-sensor dropout case in the isolation note above) — recovers on its own within one daemon cycle, **no restart**. The scan is a cheap `/sys/bus/w1/devices/` directory read; a state change logs `OneWireTherm bus now has N sensor(s)` at WARNING; a scan that raises keeps the last-known list. Verified live: import-time empty list → 0 values one cycle → 4 values the next after the bus enumerated. **Consequence:** the manual-restart recipe below (and the "recovered only by reboot" import-time caveat in the isolation note) is now only needed for a bus so broken it never enumerates at all.
- **OneWireTherm after physical repin/rewire — self-heals within one cycle now (was: restart the service; FIXED 2026-07-06)**: previously, if `pivac-1wire` started while the DS18B20 pins were disconnected (e.g. boot during hardware work), it ran with an **empty sensor list and silently published nothing** — service `active`, zero errors, all 1-wire SK paths stale — and needed `sudo systemctl restart pivac-1wire` once the wires were back. With the per-cycle re-scan above, reconnecting the wires now recovers automatically within one daemon cycle once `/sys/bus/w1/devices/` shows the `28-*` sensors; a manual restart is no longer required (still harmless). Do **not** reboot for this.
- **GPIO 26 (physical pin 37) is DEAD — do not reuse (diagnosed 2026-07-01)**: the pad is internally shorted to ground — reads `level=0` with the wire disconnected under pull-up *and* pull-down, and even driving it as an **output high** can't raise it (`raspi-gpio set 26 op dh` → still `level=0`). Permanent silicon damage, almost certainly from the 2026-06-23 power event (Shelly plug move); it survived warm reboots, the weekly reboot, and a full power-off with all pins disconnected. Consequence: the **YOFF "active" plateau from Jun 23 → Jul 1 in InfluxDB/Grafana is fabricated data** (dead pin reading constant LOW), not real HVAC state. **YOFF is currently DISABLED (commented out in `/etc/pivac/config.yml`), publishing nothing** — the wire is physically still on dead pin 37 (David deferred the move), so any configured pin would fabricate data. **Pending fix:** move the wire to **physical pin 35 (GPIO 19** — verified healthy, follows both pulls**)**, then uncomment the `19:`/`outname: YOFF` lines in the config's `pivac.GPIO` `inputs:` and `sudo systemctl restart pivac-gpio`. Until then the YOFF SK path is intentionally stale. **YOFF is a winter-only signal (set to disable air conditioning), so its true state is 0/inactive all summer** — no data is being missed right now, but the rewire must happen **before heating season**, and the first genuine confirmation of contact won't come until YOFF first asserts in winter. Diagnostic recipe for a suspected-stuck input: disconnect the wire, then `raspi-gpio get <n>` under `pu`/`pd` — a healthy floating pin follows the pull; if it doesn't, try `op dh` — if the output driver can't raise it either, the pad is dead and the signal must move to a spare GPIO.
- **Emporia paired-CT circuits were half-scale before 2026-07-04 (FIXED)**: the house panel's four 240 V circuits (`utility_sub_panel`, `hall_subpanel`, `wall_oven`, `bosch_bova`) are each monitored by **two CTs, one per leg** (channels 1+2, 3+4, 5+6, 7+8, same circuit name, multiplier 1.0 — the *correct* Emporia hardware setup). `pivac.Emporia` used to emit each channel separately, so both legs landed on the same SK path and the second overwrote the first — **InfluxDB history for those four measurements before 2026-07-04 ~16:30 EDT is one leg only (≈½ actual for balanced 240 V loads)**. Clamp-verified: BOVA at 9.4–9.5 A/leg ≈ 2.27 kW while Emporia showed ~1.15 kW. The module now sums same-named channels before emitting (energy balance closes: main = Σ circuits + balance). Do **not** "fix" this by setting a ×2 multiplier in the Emporia app on these circuits — that would double each leg and make the summed value 2× high. The ×2 multiplier is only for single-CT 240 V circuits (the apartment's `air_cond` is set up that way, correctly). Any capacity analysis based on pre-fix data (e.g. the "both BOVAs at ⅓ max" zone analysis) must be rescaled ×2.

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
| `ArduinoSensor` | Arduino HTTP sensor — **multi-field**: loops over `inputs` (key = response field name); inputs with `type: temperature` convert to Kelvin and emit `{sk_path}.{outname}.temperature`. Shared via `module:` override by `pivac.ArduinoPSI` (.114 = **DHW** pressure + recirc temp `environment.inside.hvac.dhw.recirc.temperature`) and `pivac.ArduinoThermPSI` (.219 = **boiler/hydronic** pressure). NB names are inverted vs role — see Active Services note. **`pivac.DomesticWater` (.188) *wraps* ArduinoSensor** rather than sharing it via `module:` — see its own Current Modules entry. |
| `DomesticWater` | DAE MJ-75a domestic water meter (UNO R4 WiFi, `10.0.0.188`). Wraps `pivac.ArduinoSensor` (one node GET) and passes through `environment.water.domestic.{flowRate,consumption,flowing,runDuration,runningFor}`, then **adds `.runVolume`** — gallons consumed during the current draw, computed **Pi-side** (no firmware) by snapshotting the `consumption` totalizer on the `flowing` 0→1 edge and reporting the delta; **holds the last draw's total while idle** (resets to 0 when the next draw starts). State lives in the daemon (module globals). `run_s`/`runtime` (from the node) → `.runDuration`/`.runningFor` = this draw's duration for the WilhelmSK tiles. |
| `Emporia` | Emporia Vue Gen 2 power monitors — polls two panels (house 200A, apartment 100A) via PyEmVue, emits per-circuit Watts to `electrical.emporia.<panel>.<circuit>`. **Channels sharing a circuit name are summed** — the house panel's 240 V circuits use one CT per leg (ch 1+2 utility_sub_panel, 3+4 hall_subpanel, 5+6 wall_oven, 7+8 bosch_bova), so per-channel emission would halve them (see Known Operational Behaviours). |
| `Sentry` | NTI Trinity Ti-200 boiler controller via Tapo C120 RTSP camera — reads display via 7-segment CV, emits boiler state to `hvac.boiler.sentry.*` |
| `WaterMeter` | Sensus iPerl water-meter **LCD** via Tapo RTSP camera (`10.0.0.85`) — reads the cumulative gallons totalizer via perspective-warp + **whole-glyph template matching** (NOT segment thresholding — a reflective LCD's "off" segments aren't black). Emits `environment.water.domestic.consumption` (gal) + `.flowing`. See `docs/water-meter-camera-monitoring-plan.md`. |
| `Sprinkler` | OpenSprinkler irrigation flow via the local HTTP API (`10.0.0.17:5000`) — polls `/jc`, computes `(flcrt/flwrt)*fpr*60*flow_scale`, emits `environment.water.irrigation.flowRate` (gal/min) + `.active`. Auth = **md5(device password)** in config `password_md5` (Pi-only secret). Overlaid on the domestic flow panels (Grafana). |

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

**LED and indicator detection** uses a **grayscale spot/background brightness ratio** (`_roi_is_lit`): an LED counts as lit when its 8px centre spot is ≥ `ratio`× the surrounding 25px background. (Not HSV/hue — the camera is IR-grayscale in Night mode, so colour is unavailable.)

> **Sentry LED misread — burner/pump read OFF during calls; IR-calibrated two-threshold fix (2026-07-20):** The four green boiler **status** LEDs (burner/circ/circ_aux/thermostat_demand) and the bright **display-mode** indicators (water/air/gas/dhw_temp) shared one lit-threshold `led_ratio=1.15`. Because the camera is locked in **IR/Night** mode and green LEDs emit almost no near-IR, a *lit* status LED only reaches **~1.11–1.17×** background, so **burnerOn and circAuxOn (the DHW pump) read 0 for most of every DHW call even with gas input pinned at 85–240** (burner physically firing) — the flicker looked like real short-cycling but was a CV misread. Root-caused live by cross-checking `gasInputValue>0` against `burnerOn=0`, then measuring the lit LEDs during a forced DHW call: burner 1.11–1.15, circ_aux 1.13–1.17, off LEDs 0.85–0.96 (clean gap), bright indicators 1.29–1.46. Fix = split the threshold: **`led_ratio` default 1.05** (dim green status LEDs, mid-gap) and **`indicator_ratio` default 1.15** (bright indicators — kept high so the lower LED threshold can't cause a false display-mode read that would misassign water/gas/outdoor values). The old 1.15 calibration ("lit ~1.21–1.23") predates the permanent Night/IR lock that dimmed the green LEDs. Live config carries `led_ratio: 1.05` + `indicator_ratio: 1.15`; verified live 2026-07-20 (burner/pump now solid-on through a call). **Historical InfluxDB `burnerOn`/`circOn`/`circAuxOn`/`thermostatDemand` before this date under-report during calls** — treat pre-fix boiler-LED history as unreliable (gasInputValue/status are the trustworthy pre-fix signals).

**One-time calibration required**: The module config must specify pixel coordinates for the display ROI, each digit's segment boxes, each LED, and each indicator light. These are stable as long as the camera doesn't move. A calibration utility (`scripts/sentry-calibrate.py`) saves a reference frame from the RTSP stream and helps identify coordinates.

> **Sentry calibration drift — the display moved in frame; recalibrate `display_warp` (root-caused + fixed 2026-07-28):** the camera's view shifted **~10 px up / 2 px left**, which pushed the `display_warp` quad off the **top** of the digits and clipped segment **`a`** on every one of them. Clipped `a` measured ~206 against a lit-bar of ~210, so it read *off*: an `8` decoded to the unmapped pattern `?0111111`, a `0` decoded as `8`. Measured over 400 live frames: **`water_temp` fell to 2% clean decodes** (95/98 frames unmapped) → `waterTemp` went **stale**, `gas_input` read `8` where the display plainly showed `0` (rejected as out-of-range, then masked by the PR #92 idle-fill emitting 0 anyway), and `air` read **78 °F while the real outdoor DS18B20 said 69.5 °F**. Degradation began **~2026-07-16** (water_temp capture 100% → 90%, decaying to 86%) and ran **12 days** unnoticed, because **every other `hvac.boiler.sentry.*` path kept publishing normally** — they are emitted every cycle regardless of what decodes, so the service looked healthy from outside. **Fix = re-aim the quad**, corners now `TL(1154,645) TR(1322,637) BR(1311,713) BL(1146,724)` in `/etc/pivac/config.yml` (Pi-local; a timestamped `config.yml.bak-*` is left beside it). Post-fix: water 99% / gas 100% / air 96% clean, and `waterTemp` back to full capture rate.
>
> **Recalibration recipe** (what actually worked — don't hand-guess coordinates):
> 1. **Read the display by eye first.** Grab a frame, crop generously around the display, and gamma-compress the blown IR highlights (`clip((px-120)/130,0,1)**0.45`) — unlit segments show as grey ghosts, lit ones white. Without this the saturated digits are unreadable and you cannot tell a `0` from an `8`.
> 2. **Get independent ground truth** before trusting any decode: `environment.outside.temperature` (DS18B20) pins `air` to within a few °F, and `environment.inside.hvac.dhw.recirc.temperature` sanity-bounds `waterTemp`. This is what proved 71 right and 78 wrong.
> 3. **Measure, don't guess:** threshold a frame, take column/row runs of lit pixels, and compare their bbox to the configured quad. Here digits spanned raw x 1143–1326 / y 641–724 against a quad of x 1148–1324 / y 647–730 — the top was clipped.
> 4. Capture ~400 frames once (`np.save` a small sub-region), then **grid-search the quad offline** (translate + scale about its centroid), scoring by *fraction of frames decoding cleanly and in-range* × *agreement with the per-mode median*. **Keep `dst_w`/`dst_h` and `digit_positions` fixed** — the hundreds position is a **half digit** whose `1` sits at the left of its cell, so auto-deriving digit boxes from lit-pixel clusters breaks it.
> 5. Validate the winner across **all** frames and **all three modes** before writing config, then `sudo systemctl restart pivac-sentry` and confirm freshness.
>
> **Beware self-consistency:** a constant misread scores perfectly on "consistent". Only external ground truth (step 2) distinguishes right from merely stable. **Dead end (do not retry):** a geometric drift detector (share of the warped crop's border reading as lit) — pooled over 400 frames it looked clean (0.01 aimed vs 0.07 drifted) but **per cycle it does not discriminate** (a correctly aimed quad scored 0.10 live while the broken one scored 0.07), because the digits legitimately reach the quad's left/right edges. The module instead logs `'<mode>' was displayed but nothing decoded this cycle` — unambiguous, and the signal that was missing: a mode decoding to an unknown pattern never reached `samples`, so the older `only N plausible read(s)` warning **never fired at all**. `pivac-sentry` also now runs at `--loglevel WARNING` (at `ERROR` these are dropped — the same trap documented for RedLink). Alerting gap closed by `sentry-boiler.yaml` (above); `scripts/sentry-calibrate.py` still carries a **stale copy** of the pre-2026-06-28 per-crop threshold logic, so don't trust its decodes over the module's.

**Camera day/night mode MUST stay locked** (Tapo app → Advanced → Night Vision = **Night**, Night Boost = **Off** — *not* Auto). On Auto, the camera flips between day/color and IR/night when the boiler-room lights change; that image shift makes the 7-segment reader misfire (phantom hundreds digit — e.g. outdoor 67→167, gas→410, water 87→187). Verified root cause of the 2026-05-31 "jumping values." The module is also hardened against transient misreads (PR #62): per-mode **range-sanity** (rejects out-of-range reads) + a **median-of-samples** vote per cycle (`min_samples`, default 3) so a one-frame misread loses to the median, and it sets `OPENCV_FFMPEG_LOGLEVEL=8` to silence the libavcodec H.264 SEI log spam (~72k lines/3h).

> **Phantom-hundreds guard on `water_temp` (2026-06-27):** a phantom hundreds digit on an *idle* reading (real ~98 °F → 198) survives both PR #62 defenses — 198 is under the old 220 ceiling, and if the bad frame persists the per-cycle median agrees with it. Diagnosed when the camera was *already* correctly locked to Night/IR (verified live via `pytapo` `getDayNightMode()` → `'on'`, `switch_mode: 'common'`), so the day/night-flip explanation above did **not** apply to that episode — the misread came from transient IR glare/compression on individual frames, not a mode flip. Two-layer fix: (1) absolute `water_temp` ceiling tightened **220 → 205** (boiler water physically peaks ~200 °F); (2) a **burner-aware idle ceiling** — when the burner LED is dark this frame, a `water_temp` ≥ `water_idle_ceiling` (default **185 °F**, config-overridable) is rejected as the phantom spike. Firing reads (burner LED lit) are bounded only by the absolute range so genuine peaks pass; the early-cooldown band (~165–180 just after the burner drops) stays below 185 so the real cooldown curve is preserved. Logic lives in `_reading_sane(mode, value, burner_on, idle_ceiling)` + the **lazy** burner read in `_poll_cycle` (only evaluated when a water_temp read is ≥ idle_ceiling — most frames skip it); covered by `tests/test_sentry_guard.py` (dependency-free, `python tests/test_sentry_guard.py`).

> **Phantom-hundreds ROOT-CAUSE fix — display-wide digit threshold (2026-06-28):** the guards above (median, idle ceiling, range-sanity) were band-aids over a bad read. Root cause was in `_read_display`: the lit/off threshold was computed **per-digit-crop** as `mean + factor*(max-mean)`. On a **blank** digit (the hundreds position for any temp < 100 — i.e. most of idle) the crop holds only dark background + IR glare, so its *own* max set the bar and the brightest glare pixel cleared it → a manufactured phantom "1" (real ~84 read as 184). Because it was a real-looking "1", it survived the bit-pattern ghost list **and** persisted across a whole cycle (so the per-cycle median agreed with it) **and** landed under the 185 idle ceiling (84+100=184). Fix: compute **one display-wide threshold** = `bg + factor*(p99 - bg)` where `bg` = `display_bg_percentile` (40th) and `p99` tracks a genuinely-lit segment (the units digit is always lit), then apply that same absolute bar to every digit. A blank digit now stays blank regardless of glare — its off-segments (~130–190 on live data) fall far below the ~206 bar, while real lit segments saturate ~255. Same philosophy the **LEDs** always used (`_roi_is_lit`, absolute ratio vs background — which is why LEDs never had this bug). Validated live: stable across `digit_threshold_factor` 0.60–0.75 (set **0.65**), and it cleaned up single-frame garbage the per-crop method produced. New config keys `digit_threshold_factor` (now **0.65**, display-wide semantics) + `display_bg_percentile` (40). Pure helpers `_display_threshold` / `_decode_segments` are unit-tested in `tests/test_sentry_guard.py` with **real captured segment brightnesses** incl. a blank-digit-plus-glare case. The PR #62 median, PR #78 idle ceiling, and 40–205 range remain as cheap secondary backstops but should rarely fire now. **LED states are also voted across the cycle's frames** (majority) instead of a single last-frame read, so `burnerOn`/`status` no longer flicker Run↔Idle on one glare frame. **Still to confirm:** an overnight idle period below 100 °F (blank hundreds) showing zero 1xx spikes — expected observable in Grafana.

> **Sentry CPU / thermal-throttle fix (2026-06-27):** `pivac-sentry` was pegging **~1.6 cores continuously** (5d18h CPU over ~85h wall = ~162%) and had pushed the Pi to **84 °C with the soft-temp-limit actively throttling** (`vcgencmd get_throttled` = `0xe0008`; baseline ~54 °C). Cause: the daemon loop had **no `daemon_sleep`** (fell to the provider's 0.5s default) so RTSP-decode + 7-seg CV cycles ran back-to-back. Fix = `daemon_sleep: 15` in the Sentry config block (`/etc/pivac/config.yml`; documented in `config/config.sentry-sample.yml`) → CPU **~69%**, temp **~75 °C**, throttle bit cleared to `0xe0000` (sticky "has-occurred" history only), with a reliable ~15–30s data cadence. **Lever for more headroom:** raise `daemon_sleep` toward 30. **Dead end (do not retry):** a per-frame `grab()`-skip throttle (process CV at ~3–10 fps instead of full framerate) was tried and **reverted** — it's fundamentally incompatible with the `mode_stable_frames` *consecutive-frame* debounce (too few same-mode frames per display dwell → modes never reach `min_samples` → only `status` publishes). Full-framerate-within-a-cycle is required; throttle cycle *frequency* via `daemon_sleep`, not in-cycle frame rate.

> **Sentry thermal is ultimately cooling-bound — this is a fanless Pi 4 (2026-07-22):** the host is a **Raspberry Pi 4 Model B with no active cooling** (no OS-managed fan / cooling device), so under the multi-core RTSP-decode + CV burst it heats fast and the Pi 4's **80 °C soft-temp limit** is easy to graze. Re-tuned the Sentry block to `daemon_sleep: 30` + **`cycle_timeout: 20`** (`/etc/pivac/config.yml`; was `daemon_sleep: 15` + `cycle_timeout: 30` — the `cycle_timeout` had drifted to 30, doubling the per-cycle busy burst vs the `config.sentry-sample.yml` default of 15, which is why CPU/heat exceeded the 2026-06-27 "~69% / ~75 °C" figures). Result: CPU **~1.6 cores → ~1.25**, sustained/floor temp back to **~76 °C**, and the *continuous* throttle cleared — but **brief ~83 °C peaks during each capture burst still tap the soft-limit** (`0xe0008` flickers to `0xe0000`). This residual is **benign** (soft limit = gentle freq nudge, well under the 85 °C hard limit) and **can't be tuned away in software without degrading mode capture** — `cycle_timeout` must stay ≥ ~20 s to catch all 4 display modes (~5 s each) when the boiler is actively cycling. **The only real fix for the peaks is active cooling (add a fan).** Ambient matters too (summer boiler-room heat). Levers if needed: raise `daemon_sleep` (lowers average/floor, not peaks) or lower `cycle_timeout` toward 15 (lowers peaks, risks missing a mode). These two config values are **Pi-local only** (live `/etc/pivac/config.yml`, not in the repo).

### Signal K Paths

| SK path | Type | Notes |
|---------|------|-------|
| `hvac.boiler.sentry.waterTemp` | number | °F as shown on display; emitted when water_temp indicator lit |
| `hvac.boiler.sentry.outdoorTemp` | number | °F as shown on display; emitted when air indicator lit |
| `hvac.boiler.sentry.gasInputValue` | number | Raw 40–240 scale; emitted when display shows gas input |
| `hvac.boiler.sentry.status` | string | `"Idle"` \| `"Call"` \| `"Run"` \| `"dh2o"` \| error code (e.g. `"ER3"`); emitted every cycle so WilhelmSK stays fresh |
| `hvac.boiler.sentry.dhwPriority` | number (0/1) | 1 when DHW priority indicator is lit |
| `hvac.boiler.sentry.burnerOn` | number (0/1) | Burner LED state |
| `hvac.boiler.sentry.circOn` | number (0/1) | Circ pump LED state |
| `hvac.boiler.sentry.circAuxOn` | number (0/1) | Circ aux LED state |
| `hvac.boiler.sentry.thermostatDemand` | number (0/1) | Thermostat demand LED state |

Temperature values are raw °F as shown on the display. Boolean indicators are emitted as integer 0/1 (not Python bool) so that InfluxDB stores them as float and Grafana can plot them with mean() aggregation. **Important:** if you ever need to reset these measurements in InfluxDB, you must also restart Signal K after reseeding — the `signalk-to-influxdb2` plugin caches field types in memory and will re-write booleans until the process restarts.

### Config Format

Key config fields (real coordinate values live in `/etc/pivac/config.yml` on the Pi):

- `rtsp_url` — RTSP stream URL with credentials
- `cycle_timeout` — seconds to wait for full display cycle (default 15)
- `frame_interval` — seconds between captured frames (default 2.5)
- `brightness_threshold` — 0–255 min brightness for a lit segment/LED (default 150)
- `display_roi` — `{x, y, w, h}` pixel rect in full camera frame (set during calibration)
- `digit_positions` — list of 3 `{x, y, w, h}` rects relative to `display_roi` (left, middle, right digits)
- `leds` — `{burner, circ, circ_aux, thermostat_demand}` each `{x, y}` in full frame
- `indicators` — `{water_temp, air, gas_input, dhw_temp}` each `{x, y}` in full frame

### Dependencies

- `opencv-python-headless` — frame capture and image processing (headless avoids GUI deps on Pi)
- `numpy` — already in venv

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

Key packages: `RPi.GPIO`, `w1thermsensor`, `pytemperature`, `lxml`, `requests`, `PyYAML`, `websocket-client`, `aiosomecomfort` (RedLink — Honeywell mobile API client; replaced the old `mechanize` + `beautifulsoup4` HTML scraper)

## Keeping This File Current

Push CLAUDE.md changes directly to master (no PR needed). Update this file when:

- **New or changed systemd service** — update the Active Services table, the deployment restart command in Standard Deployment Procedure, and the stop command in the SD card maintenance note
- **nginx changes** — new site, proxy target, or auth change: update Key File Locations and the Remote Access URL table
- **New hardware or device** — new sensor, new IP, new module: update Active Services table and add a module entry to Current Modules
- **InfluxDB/Grafana structural changes** — new datasource UID, new bucket, new dashboard: update the InfluxDB Version and Grafana sections
- **Signal K path changes** — update the Sentry Signal K Paths table or wherever paths are documented
- **New known operational behaviour** — add to Known Operational Behaviours

After updating here, also update `claude-contexts/pi-CLAUDE.md` if the change affects the Pi's overall role (e.g. new nginx site, new service). On the Pi, `~/CLAUDE.md` is a symlink to `~/github/claude-contexts/pi-CLAUDE.md` (created by `claude-contexts/setup.sh`), so a single `git pull` propagates the update:
```bash
git -C ~/github/claude-contexts pull
```
If `~/CLAUDE.md` is a regular file rather than a symlink (legacy Pi setup that pre-dates `setup.sh`), delete it and re-run `setup.sh` once to convert it to a symlink — after that, pulls suffice.
