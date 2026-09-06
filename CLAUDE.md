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

> **The DHW board's recirc-temp firmware is on `main` in `~/github/Arduino`** (verified 2026-08-26). The DS18B20 added to the **.114 DHW board** on 2026-05-31 serves the `temp` field → `environment.inside.hvac.dhw.recirc.temperature`, and `ArduinoPSI_Domestic.ino` defines `ONE_WIRE_BUS 2` while the shared `ArduinoPSI_impl.h` guards every temperature block on that macro, so the Domestic sketch emits `{'psi', 'temp', 'uptime_ms'}` and the BoilerLoop sketch is byte-for-byte unchanged. It reached `main` through `83e1cae`; the `feat/dhw-recirc-ds18b20` branch is the older unmerged route to the same code. **Reflashing .114 from the repo is safe** and will not drop the recirc temperature — build the `ArduinoPSI_Domestic` sketch, which additionally needs the `OneWire` and `DallasTemperature` libraries. Not checked: whether the board's flashed build is newer than `main`.
>
> **The recirc sensor's identity is recorded here because the sketch isn't.** The DS18B20 on the .114 board is printed tag **`28FFE715A0160328`** = w1 name **`28-0316a015e7ff`**. Identified 2026-08-10 by elimination — it is the fifth of a batch of five DS18B20s and the only one of the five *not* enumerated on the Pi's w1 bus — then confirmed against the physical tag. The elimination argument is what makes this solid; the tag merely agrees (see the tag-reliability warning under Known Operational Behaviours). Without this note the ROM exists nowhere in either repo and would be lost if the board had to be rebuilt.

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
| pivac-chiltrix          | pivac.ChiltrixModbus    | **Chiltrix CX75** heat pump, all 45 Modbus registers | RS-485 → UNO R4 on USB |
| pivac-loop-delta        | pivac.LoopDelta         | Gated per-run loop ΔT (derived; reads Signal K)   | none — derived |
| pivac-grafana-alerts    | pivac.GrafanaAlerts     | Grafana alert state → Signal K notifications (derived; reads Grafana's API) | 127.0.0.1:4000 |

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
- Grafana API token: `~/.config/grafana-claude-agent.key` (mode 600) on **both** the Pi and the Mac — service account `sa-1-claude`, Admin role. Use it as `-H "Authorization: Bearer $(cat ~/.config/grafana-claude-agent.key)"` against `http://127.0.0.1:4000/grafana/api/...` on the Pi. **Never ask for the Grafana admin password; this is the credential.** The poller's own Viewer token (service account `pivac-alerts`) lives only in the `pivac.GrafanaAlerts` block of `/etc/pivac/config.yml`.
- WireGuard keys (unused, kept for reference): `/etc/wireguard/`

## Remote Access

All remote access goes through nginx on the Pi (`10.0.0.82`) over HTTPS. No VPN required.

**External hostname:** `68lookout.dglc.com` → public IP `74.89.220.182` (DNS on AWS Route53; update manually if ISP IP changes)

**Network topology (double-NAT):** Internet → fiber router (`192.168.1.x`) → Unifi router (`10.0.0.x`) → Pi (`10.0.0.82`). TCP ports 80 and 443 are forwarded at both hops.

**Pi network interfaces (wired since 2026-06-16):** `eth0` (`d8:3a:dd:b1:ad:4d`) is DHCP-reserved to `10.0.0.82`, route metric 100. `wlan0` is a fallback at fixed `10.0.0.130` on SSID `redux`, locked to 5 GHz with power-save disabled, metric 600; failover is automatic by metric, but the port forwards target `.82` only, so external access does not fail over. The profile is `redux` (file `/etc/NetworkManager/system-connections/Wireless connection 1.nmconnection`, PSK system-owned). If `wlan0` fails to rejoin and `journalctl -u NetworkManager` shows `no-secrets`, re-set the PSK with `nmcli connection modify redux wifi-sec.psk <pw>` and `nmcli connection up redux`. Re-enable the radio from a console with `nmcli radio wifi on`. History in `docs/operational-notes.md`.

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
- **Page 1** (template `"1"`, 14+ slots): main dashboard — 5 thermostat room tiles, 4 HVAC water temp gauges (In/UBT/LBT/Out), switch bank, 2 PSI gauges, Sentry widgets
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

**Grafana runtime facts (learned 2026-07-20):** Grafana listens on **port 4000** (not 3000) and serves under the `/grafana/` sub-path — API base is `http://127.0.0.1:4000/grafana/api/...`, authenticated with the service-account token at `~/.config/grafana-claude-agent.key` (see Key File Locations; the admin password is set, not admin/admin, and is not needed). This is a **Grafana 13 unified-storage** install: live dashboards are stored in the **`resource` table** of `/var/lib/grafana/grafana.db`, NOT the legacy `dashboard` table (which is stale — reading it will mislead you). Inspect live panels with `python3 sqlite3` (no `sqlite3` CLI on the Pi). Run InfluxQL directly via the v1 endpoint: `curl -G http://localhost:8086/query --data-urlencode 'db=pivac' --data-urlencode 'q=...' -H "Authorization: Token <active influx token>"`.

**Panel alignment:** every timeseries panel on PivacR pins `custom.axisWidth: 50` so all plot areas share a left edge — keep new panels consistent. Don't set a per-panel `axisLabel` (it renders left of the ticks and pushes that panel's plot right). Note: **state-timeline panels can't set axis/row-label width** (Grafana #85040), so boolean/status data that must line up with the numeric-axis panels should be a **timeseries with stepped lines**, not a state-timeline.

**Water "net of irrigation" convention:** irrigation water flows *through* the domestic meter, so the raw `environment.water.domestic.consumption` totalizer double-counts irrigation. The "Used" stat panels and the hourly bar panel show **Domestic (net) = domestic total − irrigation** (irrigation = `INTEGRAL(environment.water.irrigation.flowRate, 1m)`), green = net domestic, yellow = irrigation. InfluxQL can't subtract across measurements in one query, so it's done with a Grafana transform chain `joinByField(Time) → calculateField(binary A−B) → organize(exclude gross)`. The two aggregates must land on the **same timestamp** to join: `SPREAD` returns the range-start time but `INTEGRAL` returns **epoch 0**, so both stat queries force one epoch-aligned bucket with `GROUP BY time(3650d) fill(0)` (hourly panels `GROUP BY time(1h)` align naturally). The flow-rate panels (18/19) intentionally still show *gross* domestic (they're rates, not totals).

**ΔT panel (21, `Loop ΔT — Primary and Secondary Pairs`) plots differences:** primary `OUT − IN` and `RET − SUP` on each secondary, warm side minus cold side throughout, so all three read positive in cooling. Same `joinByField → calculateField → organize` chain as the water panels, with the Kelvin→°F conversion done per query. **The axis uses soft limits of −2 to +8 °F, never a hard min/max**, because the sign carries information (heating inverts every pair, a backwards pair reads negative without going stale, and a heating delta of 20 °F would clip). **Do not re-enable `axisCenteredZero`**; it halved the usable height. Reasoning in `docs/operational-notes.md`.

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
**Rule files** (every rule routes to `graph-bridge`; thresholds, runbooks and the retired-rule evidence are in `docs/grafana-alerting-notes.md`):
- `redlink-stale.yaml` — `redlink-stale` (30 m), `redlink-stale-fast` (10 m), `redlink-error-burst` (`consecutiveErrors > 2` for 5 m; runbook says query `lastErrorType`).
- `sensor-freshness.yaml` — 30 m staleness on `hydronic-{in,ubt,lbt,out}`, `loop-{a,b}-{supply,return}`, `circ-temp-stale`, and `arduino-{dhw,hydronic}-psi-stale`. Kelvin paths use the never-true sentinel `value < 100`, PSI `< -1`, all `noDataState: Alerting`. Deletes `hydronic-crw-stale`, `outside-onewire-stale` and `outside-temp-divergence`.
- `domestic-water.yaml` — `domestic-flow-continuous` (3 h with no irrigation), `domestic-flow-high` (net of irrigation > 12 gpm), `domestic-water-stale`. Irrigation NoData is replaced with 0 so a down sprinkler service cannot disarm leak alerting.
- `sentry-boiler.yaml` — `sentry-watertemp-stale`, `sentry-cycle-stale` (both firing = reader dead; only waterTemp = the CV cannot read the digits), `sentry-outdoor-divergence`. °F paths use sentinel `< -100`.
- `chiltrix.yaml` — `chiltrix-pump-only-flow-low` (`startupFlow` < 40 L/min for 30 m, **the** fouling alarm) and `chiltrix-modbus-stale`. Deletes `chiltrix-flow-approaching-trip` and `chiltrix-run-duration-excessive`, both retired because running flow and run length are controlled outputs.

**Ship a rule on a metric that does not exist yet as `isPaused: true`**: under `noDataState: Alerting` it emails on every evaluation. Unpause once the metric publishes and verify against the `alert_rule` table.

**Every rule is also mirrored into Signal K as a notification** by `pivac.GrafanaAlerts` (`pivac-grafana-alerts.service`), so WilhelmSK shows the same alarms the email path sends: `notifications.pivac.<rule uid with - → _>`, `normal` while quiet and `warn`/`alert`/`alarm` by `severity` label while firing, silences honoured. Grafana stays the evaluator. The whole set republishes every cycle, so a restart on either side self-heals within one cycle and a dead poller leaves every path stale together. Its Viewer token lives in the module's block of `/etc/pivac/config.yml` (see `config/config.grafana-alerts-sample.yml`).

**Test the bridge end-to-end:**
```bash
curl -sS -X POST http://127.0.0.1:8125/alert -H 'Content-Type: application/json' \
     -d '{"status":"firing","title":"test","alerts":[{"status":"firing","labels":{"alertname":"x"},"annotations":{"summary":"hello"}}]}'
```
Should return `ok` and an email arrives at `david@dglc.com`.

> **⚠️ Removing an alert rule needs an explicit `deleteRules:` block — provisioning is ADDITIVE (learned 2026-08-06).** Deleting a rule from `groups: … rules:` does **not** remove it from Grafana. It keeps evaluating with `provenance=file` (so it's also uneditable/undeletable in the UI) indefinitely. Verified live: after the CRW→UBT rename, `hydronic-crw-stale`, `outside-onewire-stale` and `outside-temp-divergence` all survived the copy + `systemctl restart grafana-server` (16 rules in the `alert_rule` table when the YAML defined 7), and the two staleness rules would have emailed on **every** evaluation since their metrics no longer existed and both carry `noDataState: Alerting`. The fix is a top-level block in the same file:
> ```yaml
> deleteRules:
>   - orgId: 1
>     uid: hydronic-crw-stale
> ```
> Leave the block in place permanently — deleting an already-absent rule is a no-op, and removing it would let a stale Grafana DB resurrect the UID. **Always verify after a rule removal** rather than trusting the restart:
> ```bash
> sudo python3 -c "import sqlite3;c=sqlite3.connect('file:/var/lib/grafana/grafana.db?mode=ro',uri=True);[print(r) for r in c.execute('select uid,title from alert_rule order by title')]"
> ```

**Deployment after editing the YAMLs or the bridge:**
```bash
# script/service:
sudo cp ~/github/pivac/scripts/systemd/grafana-graph-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl restart grafana-graph-bridge
# provisioning YAMLs (Grafana copies, not symlinks — must restart to pick up changes):
sudo cp ~/github/pivac/grafana/provisioning/alerting/*.yaml /etc/grafana/provisioning/alerting/
sudo chown root:grafana /etc/grafana/provisioning/alerting/{contact-points,redlink-stale,sensor-freshness,domestic-water,sentry-boiler,chiltrix}.yaml
sudo chmod 640         /etc/grafana/provisioning/alerting/{contact-points,redlink-stale,sensor-freshness,domestic-water,sentry-boiler,chiltrix}.yaml
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
sudo systemctl restart pivac-1wire pivac-redlink pivac-gpio pivac-arduino-psi pivac-arduino-therm-psi pivac-emporia pivac-sentry pivac-watermeter pivac-sprinkler pivac-domestic-water pivac-chiltrix pivac-loop-delta pivac-grafana-alerts
journalctl -u pivac-1wire -u pivac-redlink -u pivac-gpio -u pivac-arduino-psi -u pivac-arduino-therm-psi -u pivac-emporia -u pivac-sentry -u pivac-watermeter -u pivac-sprinkler -u pivac-domestic-water -u pivac-chiltrix -u pivac-loop-delta -u pivac-grafana-alerts -n 50 --no-pager
```

If systemd service or timer files were changed:
```bash
sudo cp ~/github/pivac/scripts/systemd/*.service ~/github/pivac/scripts/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
```

**Before SD card maintenance, extended downtime, or rsync** — stop all services that write to disk:
```bash
sudo systemctl stop pivac-1wire pivac-redlink pivac-gpio pivac-arduino-psi pivac-arduino-therm-psi pivac-emporia pivac-sentry pivac-watermeter pivac-sprinkler pivac-domestic-water pivac-chiltrix pivac-loop-delta pivac-grafana-alerts signalk influxdb nginx
```
Stop order matters: pivac services first (they push to Signal K), then signalk (writes its own store and feeds influxdb), then influxdb (the database), then nginx (terminates external connections including the `mlb.dglc.com` bowling proxy). The bowling app DB is on the Mac Mini — stop `com.dglc.bowling-app` there separately if doing Mac maintenance. Services with `Restart=always` will restart automatically on boot; nginx does not, so start it explicitly after the swap: `sudo systemctl start nginx`.

## Backup Automation

`nas-image-backup.timer` runs `nas-image-backup.service` on the 1st of each month at 03:00 EDT. The service runs `scripts/nas-image-backup.sh`, which mounts the NFS share, stops the disk-writing services, runs `image-backup` against `/mnt/nas-pi-backups/pivac.img`, and restarts services on EXIT. Typical incremental: ~2 minutes downtime. See `~/CLAUDE.md` Backup section for the full architecture (NAS share, NFS+ACL gotcha, bootstrap caveats).

> **⚠️ Every pivac unit has `Requires=signalk.service`, so the script's `systemctl stop signalk` stops them ALL, and any unit missing from `START_SVCS` stays dead after the backup.** When adding a pivac service, add it to both `STOP_SVCS` and `START_SVCS` in `scripts/nas-image-backup.sh`. A burst of staleness alerts around 03:00 on the 1st is normal; if any path is still stale after ~03:10, check `systemctl list-units 'pivac-*' --all` for units the restart missed.

> **nginx is deliberately NOT in this script's stop set.** It holds no database, and stopping it blacks out the `mlb.dglc.com` bowling proxy and trips the mlb-availability alert. The SD-maintenance stop list above does stop it, because there the card is being pulled.

> **Image sizing and exclusions:** `image-backup` never resizes an existing image on incrementals, so `pivac.img` was grown to the full card size (the MBR disk identifier must stay `0xf9199e61` for the image's `PARTUUID=` references to boot), and the script passes `-o '--exclude=/home/pi/thinclient_drives'` for the xrdp FUSE mount that root cannot traverse. Both were the 2026-06-01 first-run failures; details in `docs/operational-notes.md`.

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
journalctl -u pivac-1wire -u pivac-redlink -u pivac-gpio -u pivac-arduino-psi -u pivac-arduino-therm-psi -u pivac-emporia -u pivac-sentry -u pivac-watermeter -u pivac-sprinkler -u pivac-domestic-water -u pivac-chiltrix -u pivac-loop-delta -u pivac-grafana-alerts -n 50 --no-pager

# Single service
journalctl -u pivac-redlink -n 50 --no-pager

# Signal K server
journalctl -u signalk -n 50 --no-pager
```

## Reference docs

Rules live in this file; the evidence, measurements and incident history behind them live in `docs/`. When a rule here needs its reasoning, read the doc before acting.

| Doc | Covers |
|-----|--------|
| `docs/chiltrix-modbus.md` | Chiltrix CX75: Modbus wiring and register map, E14 and P5 lockouts, Y-strainer fouling, why only `startupFlow` works as a fouling signal |
| `docs/chiltrix-cycling-tuning-plan.md` | Chiltrix cycling-reduction parameter plan |
| `docs/onewire-notes.md` | DS18B20 roster history, bus fault diagnosis, decoupled and cross-connected probes, dead-leg ΔT, precision fixes, module behaviour |
| `docs/ds18b20-bus-topology.md` | 1-wire bus build procedure, EXT board, DS2482 migration, electrical background |
| `docs/ds18b20-PA1-5-calibration.md` | Probe offsets, pair corrections, reproducibility |
| `docs/sentry-cv-notes.md` | Sentry display reader: capture strategy, CV method, LED thresholds, drift recalibration, phantom digits, thermal tuning |
| `docs/emporia-notes.md` | Emporia circuit history, paired-CT scaling, nested-CT corrections, panel 10/11 conventions |
| `docs/grafana-alerting-notes.md` | Per-rule descriptions, thresholds and the evidence behind retired rules |
| `docs/operational-notes.md` | RedLink internals, relay roster and zone map, GPIO 26, sprinkler calibration and watering rules, network, backup and dashboard history |
| `docs/cdp-chiller-rework-plan.md` | Single-chiller conversion: relay hardware, zone → equipment map, label |

## Known Operational Behaviours (Not Bugs)

Rules only. The measurements, incident history and reasoning behind each rule are in the doc named for the group; read that doc before changing anything the rule covers.

### Chiltrix CX75 (`docs/chiltrix-modbus.md`)

- **Modbus link:** `A3`/`B3` on connector `P5`, A/B only, no ground, no bias, no terminator (the chiller biases the pair itself at 3.18 V). Modbus RTU 9600 8N1, slave 1, **function 03 only, never 6 or 16**, though 140–146 are writable. Ground the cable shield **at the Arduino end only**: floating it lost 65 % of frames at 55 Hz and none at idle, so link quality measured at idle is meaningless. `SW1` on the main board is the compressor model encode; there is no Modbus parameter on the panel. Diagnose with the failure code (`TMO` vs `CRC`), and use Chiltrix's own register document, never the community maps.
- **Register map:** 140 on/off, 141 mode, 142 cooling target (whole °C), 202 ambient, 205 outlet, 281 inlet (all ÷10 °C), 213 flow (÷10 L/min), 227 compressor Hz, 256 current (÷10 A). `inlet` is water going TO the chiller and `outlet` water returning FROM it, so `281 − 205` is positive in cooling; compare temperatures at idle, never during a transient. Every address 0–359 answers, so a response proves nothing and `registerCount` is link health. 181 addresses are published (the confirmed set plus `P00`–`P139` as `raw.r<addr>`); address = parameter number is verified, but trust numeric matches over raw enum values. Register `65` reads 14 against the manual's `P65` = 20; confirm on the panel before reasoning about the low-flow trip.
- **Keep the return-water target at 50 °F / 10 °C.** `P59` antifreeze trips at 3 °C on *leaving* water and the evaporator ΔT runs ~9 °F below the *return* target, so 49 °F is the floor. The controller stores whole °C, so set it in °C and read it back (48 °F becomes 8 °C, leaving water on the trip). E14 needs a breaker power cycle; the panel's Error reset does not clear it. To run colder: glycol → `P59` → target; `P109` only opens the range. If E14 recurs at 50 °F, check flow, charge and the leaving-water sensor, flow first.
- **`P5` is the low-flow alarm (`P65` trip, 20 L/min) and the Y-strainer is the first suspect**, fouled by scale from the boiler side of the shared loop. `C13` is the live flow readout; it reads 0 at idle because the pump only runs on a call, so read it in the 1–2 min pump-only window at the start of a run (54 L/min after cleaning). The failure signature is a chiller that runs a few minutes at a time while the loop warms, and, more quietly, sits above its own return target all afternoon. Never raise the autofill on this glycol loop; top up manually with premixed glycol to 21–23 psi.
- **Flow while running is a controlled output**, trimmed off inlet temperature (register 281) with the compressor, so raw flow, flow ÷ Hz, inlet against target, end-of-cycle inlet and run duration all fail as fouling signals. The **startup plateau** (`.startupFlow`, clean 50.5–54 L/min) is the one comparable measurement, and under 40 L/min is the alarm. The chiller restarts on its own 2 °C hysteresis (`P12`), and `P52` = 0 means the pump never fully stops. Any capacity analysis using data before 2026-08-22 is measuring a flow-restricted plant. Commissioned 2026-08-04; the first blockage took 18 days.
- **Serial bridge:** UNO R4 on the Pi's USB at `/dev/ttyACM0` (serial `E8F60AA93AA8`); a charge-only cable is the first failure to check. Sketches in `~/github/Arduino` (`ChiltrixModbus`, `ChiltrixScan`, `RS485Blast`). Opening the port does not reset the board, and a running `watch` eats one character, so any serial client must quiesce to the prompt first and time out its reads. Drop `TMO` rows before analysing a log. `chiltrix-logger.service` is retired; `pivac-chiltrix` declares `Conflicts=` on it.

### 1-wire DS18B20 (`docs/onewire-notes.md`; bus electrics `docs/ds18b20-bus-topology.md`; offsets `docs/ds18b20-PA1-5-calibration.md`)

| Name | w1 ROM | Probe | Offset (K) | Where |
|------|--------|-------|-----------|-------|
| IN | `000000c98b14` | PA4A | +0.468 | primary, before the tees |
| OUT | `0000001aa0a8` | PA4B | +0.143 | primary, after the tees |
| UBT | `000000c9e879` | PA3A | +0.348 | buffer tank, upper |
| LBT | `000000c915c1` | PA3B | +0.466 | buffer tank, lower |
| LOOPA_SUP | `000000cc0c90` | PA1A | +0.653 | loop A (kids, master) |
| LOOPA_RET | `0000001a9154` | PA2B | +0.171 | loop A |
| LOOPB_SUP | `0000001ac0a9` | PA2A | −0.062 | loop B (family, kitchen, great room) |
| LOOPB_RET | `000000c99b56` | PA1B | +0.474 | loop B |

- All eight publish under `environment.inside.hvac.*` in Kelvin at `rounding: 2`. Loop offsets are stated at 45 °F; the 140 °F heating-season values sit in a `config.yml` comment and pair ΔT needs them too. UBT/LBT are finished at the ice point (the tank runs chilled only); IN/OUT stay single-point by decision. Calibrated spares: `0316a00f04ff` +0.153, `0516a36816ff` +0.496, `0516a365d8ff` +0.056; `0516a36332ff` has broken leads. `LOOPA_SUP`/`LOOPB_SUP` history before 2026-08-29 is interchanged, and `IN − OUT` steps by +0.585 °F at 2026-08-23 and changes precision at 2026-08-18.
- **The DHW recirc probe** (`0316a015e7ff`, tag `28FFE715A0160328`) hangs off the .114 Arduino and reaches Signal K through `pivac.ArduinoSensor`, which has no `offset` support. Its +0.274 K correction (stated at 120 °F, deliberately not 45 °F) is parked on its config entry, unapplied. `environment.outside.temperature` does not exist; outdoor air is RedLink only.
- **Retiring or renaming a sensor needs a signalk restart**: config edit → `restart pivac-1wire` → `restart signalk`; Signal K otherwise keeps the old path frozen at its last value. The same recipe applies to relays and Emporia circuits. `environment.outside` 404s for ~80 s after a signalk restart until RedLink re-logs in.
- **Bus health:** 2.2 kΩ pull-up at the master, 3.3 V. `max_slave_count 64 reached` means marginal bit timing (cable capacitance against the pull-up), never 64 sensors. `presence=1 roms=0` means devices alive and timing marginal; `presence=0` means power or a broken lead. Bisect by adding probes one at a time while watching `w1_master_slave_count`. The Arduino bench rig needs 5 V on both supply and pull-up. pivac logs only `bus now has 0 sensor(s)`; the freshness alerts are what report a dead bus.
- **Printed tags are unreliable; the bus is authoritative.** Identify a probe by unplugging it and watching `/sys/bus/w1/devices/`. The label is the full 8-byte ROM; the w1 name reverses the six serial bytes.
- **A decoupled probe reports fresh, plausible, wrong data forever.** Detect it by swing (coupled 7–14 °F over a cycling window, decoupled 1–2) and pairwise correlation (a loop's own pair reading −0.02 is impossible; two decoupled probes correlate with each other). Cross-connected probes show the same way, so group by measured correlation, never by label, and check the sign of every pair after any install: OUT runs 5–6 °F above IN in cooling. 85.0 °C exactly, the rails, or CRC errors are chip faults; anything plausible is mounting. Strain-relieve the cable an inch behind the probe.
- **An idle loop's ΔT is fiction**: the dead legs off the tees hold a plausible positive ΔT with the pump off, and loop A's supply tracks `IN` within 0.2 °F in every state. Gate every loop ΔT on a switch, never a probe (`pivac.LoopDelta` gates on `CHIL` narrowed to each loop's zones; RedLink zone state lags the relay by ~48 s). The first minute of a run is not a measurement either. Never aggregate a short-cycling signal into buckets near its own period.
- **Module behaviour:** the bus is rescanned every cycle (boot race and dropouts self-heal without a restart), a failing sensor is skipped without silencing the rest, and `SensorNotReadyError` is transient. `rounding: 2` is a precision setting (0.018 °F); never put it back to 0, which quantized every ΔT to 1.8 °F steps. RedLink had the matching defect and truncated (up to 1.8 °F cold, always downward) before 2026-08-18. Neither fix is retroactive.

### Emporia (`docs/emporia-notes.md`)

- **Live circuits:** house `chiltrix`, `bova_kitchen`, `bova_great_room` (metered inside `utility_sub_panel`), `wall_oven`, `utility_sub_panel`, `hall_sub_panel` plus `main`/`balance`; apartment `air_conditioner`, `furnace` plus `main`/`balance`. Renamed and retired names stay in InfluxDB as orphans with their history, and a rename needs a `signalk` restart.
- **The apartment's missing circuits are borrowed CTs**, moved to instrument the Chiltrix; that is deliberate, and `main`/`balance` stay correct. `electrical.emporia.house.chiltrix` depends on that hardware. Expect to repoint Grafana panel 11 when CTs return under new names.
- **240 V loads want a merged pair (one CT per leg, same circuit name) at multiplier 1.0.** ×2 on a single CT only works for a balanced load and hides standby draw; ×2 on a pair doubles it. History for the four paired circuits before 2026-07-04 is half scale.
- Circuit names refresh on `name_refresh_s` (1 h) and sanitize to `[a-z0-9_]`; `tests/test_emporia_sanitize.py` asserts every in-service name sanitizes to itself.
- **Grafana panel 10:** `main` stays unstacked, `balance` must be plotted, and a nested CT needs two corrections (subtract it from its parent *and* add it back to `balance`, because Emporia's balance is not nesting-aware). Colours are by load family with a `byName` override per series: blue cooling, yellow subpanels, green loads, grey balance, purple `main`. Panel 11 matches raw field names, so a rename silently reverts that series to the palette.

### Relays and GPIO (`docs/cdp-chiller-rework-plan.md`, `docs/operational-notes.md`)

- **Inputs:** ZV 17, DHW 27, BLR 22, BOS2 5, BOS1 6, DEHUM 12, CHIL 25. ZV is deliberately not plotted on the Relays panel. Zone → source: `CHIL` serves MASTER_BR, DSTRS_FAM_ROOM and KIDS_ROOM; `BOS1` KITCHEN (`bova_kitchen`); `BOS2` GREAT_ROOM. The Bosch inputs report the *call* in parallel, never proof the compressor ran, and `CHIL` runs to buffer-tank setpoint, so it is correlated with zone demand rather than identical. Dropping or renaming a relay: config edit → `restart pivac-gpio` → `restart signalk`; no `.wlyt` change.
- **GPIO 26 (pin 37) is dead** (pad shorted since the 2026-06-23 power event), so its YOFF plateau Jun 23 → Jul 1 is fabricated. **YOFF is retired, not pending**: winter shutdown is a manual breaker-off at the chiller, so do not move the wire. Free inputs with wire runs: BCM 13, 16, 24. Suspected-stuck pin: disconnect, `raspi-gpio get` under `pu`/`pd`, then `op dh`; a pad the driver cannot raise is dead.

### RedLink (`docs/operational-notes.md`)

- Cold-start login takes ~75 s on the Pi; expect it after every restart and the Sunday 00:00 reboot. `force_close=True` + IPv4-only are required. Devices refresh in parallel under a 12 s deadline; **do not raise it** (20 s doubled the failure rate). The session resets only on `AuthError`, `APIRateLimited`, `SessionTimedOut` or `UnauthorizedError`. `APIRateLimited` holds the module out for 10 min; do not restart to "fix" it. After a DNS outage with no `APIRateLimited` in the log, `restart pivac-redlink` is the right move. Baseline is 5–17 s gaps and 15–25 % per-device timeouts with occasional tile flicker, all Honeywell-side. Runs at `--loglevel WARNING` because `ERROR` drops the cycle warnings.

### Sprinkler and irrigation (`docs/operational-notes.md`)

- Meter: DAE AS200U-75P, 1 gal/pulse, on OpenSprinkler SN1 + GND. `fpr = 1.0`, `flow_scale 1.0`, calibrated 2026-06-20 to 1 %. OpenSprinkler does no unit conversion: set the Flow Pulse Rate unit dropdown to gal/pulse or the app reads 3.8× low (pivac is independent of it). Auth is md5 of the OS device password (`{"result":2}` when wrong). `/jl` `flow` is an average rate. Recalibrate with `fpr_new = fpr × (true ÷ reported)`.
- House #68 is even, so OpenSprinkler Program 1 is restricted to even days (§ 237-10, June–Sept, 12:01–10 am and 6 pm–midnight). No deduct meter, so irrigation bills at the domestic tiers plus sewer, ≈ $1.19/100 gal.

### Pressure Arduinos

- Both boards occasionally time out (one WARNING, self-recover). After a mains blip the .219 board sometimes fails to rejoin WiFi; `arduino-watchdog.timer` power-cycles the shared Shelly after 15 min down and `arduino-{dhw,hydronic}-psi-stale` email at 30 min. Manual recovery: `curl "http://10.0.0.61/rpc/Switch.Set?id=0&on=false"; sleep 8; curl "http://10.0.0.61/rpc/Switch.Set?id=0&on=true"`. A low `uptime_ms` means a recent reboot; `http=000` means off WiFi.

### Platform

- **The provider WebSocket is read as well as written** (PR #86): a reader thread answers Signal K's 30 s pings. Before it, every service was heartbeat-killed ~60 s after connect and lost ~30 s of deltas per cycle. Regression signature: `auth/login` climbing ~6/min in the signalk journal plus `Broken pipe → reconnect` warnings. The 4–7 s tap-to-tile floor on the water tiles is physics.
- The boot-time WebSocket race is handled by backoff. `/etc/crontab` reboots the Pi every Sunday at 00:00; tiles flicker briefly.
- A whole-Pi "hang" was WiFi power-save; the Pi is wired now. Check host versus service first (ping/ARP from another box), then `vcgencmd get_throttled` and `nmcli device status`.
- The WaterMeter camera reader is retired (`pivac-watermeter` stopped 2026-06-17); `environment.water.domestic.*` comes from `pivac-domestic-water` since 2026-07-03.
- **Grafana inside WilhelmSK:** every device shares the `admin` login, so a theme tap on one changes all (fix: `preferences` table `user_id=1`, or `?theme=dark` on the widget URL). Blank panels after hours in the background are the web view's JavaScript stopped, fixed in the app (sbender9/Wilhelm#155). nginx's `/grafana/` block has no WebSocket headers, so Grafana Live fails with 400, harmlessly.


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
| `ChiltrixModbus` | Chiltrix CX75 over RS-485 Modbus RTU (A3/B3, 9600 8N1, slave 1, function 03), bridged by an UNO R4 on USB running the `ChiltrixScan` sketch. **Read only — function 03, never 6 or 16**, though 140–146 are writable. Drives the sketch's `s <from> <to>` range-read rather than its `watch`, which caps at 6 registers. Publishes 181 addresses: the confirmed set under named paths (`hvac.chiller.chiltrix.*`, temperatures in **Kelvin**) and `P00`–`P139` under `.raw.r<addr>`. Also emits `.evaporatorDelta`, `.runDuration` and `.startupFlow`. ~6.8 s per cycle at `daemon_sleep: 30`. |
| `LoopDelta` | **Derived** — reads Signal K rather than hardware, so it never contends for the 1-wire bus or the GPIO pins and opens no second Honeywell session. Publishes `environment.inside.hvac.{primary,LOOPA,LOOPB}.deltaT` every cycle, taking **three values with three meanings: a number is a live measurement, `0` means the loop is not measuring** (idle, or within `settle_s` of a start while the probes still hold their stagnant values), **and a GAP means a source is stale or the module is down**. Publishing 0 for idle rather than nothing is what keeps that third case readable, since idle-as-gap conflates a stopped pump with a dead service. In **Kelvin**: a difference, so °F is `*9/5` with **no** offset. `.flowing` (0/1) is emitted every cycle. Gated on the `CHIL` relay, narrowed to each secondary's zones. See the dead-leg note in Known Operational Behaviours. |
| `GrafanaAlerts` | **Derived** — polls Grafana (`127.0.0.1:4000/grafana`, service-account token in config) and publishes every alert rule as a Signal K notification under `notifications.pivac.<uid>`: `normal` while quiet, `warn`/`alert`/`alarm` by severity while firing, silences honoured via the Alertmanager API. Publishes nothing at all when Grafana is unreadable, so a dead link shows as stale rather than quiet. See the Alerting section. |
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

### Operating rules

The capture strategy, the computer-vision method and every incident behind these rules are in `docs/sentry-cv-notes.md`.

- **Camera day/night mode MUST stay locked** (Tapo app → Advanced → Night Vision = Night, Night Boost = Off). On Auto the image shifts with the boiler-room lights and the reader manufactures a hundreds digit. Check the lock without credentials by comparing colour channels of a frame: IR is true greyscale.
- **Thresholds:** `led_ratio 1.05` (the dim green status LEDs reach only 1.11–1.17× background under IR), `indicator_ratio 1.15` (bright mode indicators), `digit_threshold_factor 0.65` with `display_bg_percentile 40` (one display-wide threshold; a per-digit threshold read glare on a blank digit as a phantom `1`). Each cycle takes a median of samples per mode, votes LED states across frames, and applies per-mode range sanity (water 40–205 °F, and 185 °F when the burner LED is dark).
- **Calibration drift recurs roughly monthly** (2026-07-28, 2026-08-23); any physical work in the boiler room can bump the camera, so check the decode rate afterwards. First check: `journalctl -u pivac-sentry | grep "nothing decoded"`. Recalibrate `display_warp` by measuring: capture ~400 frames, grid-search the quad offline, keep `dst_w`/`dst_h`/`digit_positions` fixed (the hundreds cell is a half digit), and validate against RedLink outdoor and the DHW recirc temperature, because a constant misread scores perfectly on consistency. Corners since 2026-08-23: `TL(1150,649) TR(1318,641) BR(1307,717) BL(1142,728)`. A border-lit drift detector was tried and does not discriminate per cycle.
- **Thermal:** fanless Pi 4. Live config (Pi-local) runs `daemon_sleep: 30` + `cycle_timeout: 20`; brief 83 °C peaks per capture burst tap the soft limit and are benign, and a fan is the only fix. Do not throttle the in-cycle frame rate (it breaks the consecutive-frame mode debounce), and keep `cycle_timeout` ≥ 20 s to catch all four modes.
- Runs at `--loglevel WARNING`. `scripts/sentry-calibrate.py` carries stale per-crop threshold logic; do not trust its decodes over the module's. `burnerOn`/`circOn`/`circAuxOn`/`thermostatDemand` history before 2026-07-20 under-reports during calls.

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
- **New known operational behaviour** — add the rule to Known Operational Behaviours and the evidence to the matching doc in `docs/` (see Reference docs); rules here, history there

After updating here, also update `claude-contexts/pi-CLAUDE.md` if the change affects the Pi's overall role (e.g. new nginx site, new service). On the Pi, `~/CLAUDE.md` is a symlink to `~/github/claude-contexts/pi-CLAUDE.md` (created by `claude-contexts/setup.sh`), so a single `git pull` propagates the update:
```bash
git -C ~/github/claude-contexts pull
```
If `~/CLAUDE.md` is a regular file rather than a symlink (legacy Pi setup that pre-dates `setup.sh`), delete it and re-run `setup.sh` once to convert it to a symlink — after that, pulls suffice.
