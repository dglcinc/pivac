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
| pivac-arduino-psi       | pivac.ArduinoSensor     | **DHW** pressure (Fusch 200PSI) + recirc-loop temp | 10.0.0.114 |
| pivac-arduino-therm-psi | pivac.ArduinoSensor     | **Boiler/hydronic** pressure (Fusch 100PSI) | 10.0.0.219 |
| pivac-emporia           | pivac.Emporia           | Emporia Vue Gen 2 (house + apt)  | Emporia cloud |
| pivac-sentry            | pivac.Sentry            | NTI Trinity Ti-200 boiler (Tapo C120 RTSP) | 10.0.0.19 |
| pivac-watermeter        | pivac.WaterMeter        | Sensus iPerl water meter LCD (Tapo RTSP)   | 10.0.0.85 |

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
sudo chown root:grafana /etc/grafana/provisioning/alerting/{contact-points,redlink-stale,sensor-freshness}.yaml
sudo chmod 640         /etc/grafana/provisioning/alerting/{contact-points,redlink-stale,sensor-freshness}.yaml
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
sudo systemctl restart pivac-1wire pivac-redlink pivac-gpio pivac-arduino-psi pivac-arduino-therm-psi pivac-emporia pivac-sentry pivac-watermeter
journalctl -u pivac-1wire -u pivac-redlink -u pivac-gpio -u pivac-arduino-psi -u pivac-arduino-therm-psi -u pivac-emporia -u pivac-sentry -u pivac-watermeter -n 50 --no-pager
```

If systemd service or timer files were changed:
```bash
sudo cp ~/github/pivac/scripts/systemd/*.service ~/github/pivac/scripts/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
```

**Before SD card maintenance, extended downtime, or rsync** — stop all services that write to disk:
```bash
sudo systemctl stop pivac-1wire pivac-redlink pivac-gpio pivac-arduino-psi pivac-arduino-therm-psi pivac-emporia pivac-sentry pivac-watermeter signalk influxdb nginx
```
Stop order matters: pivac services first (they push to Signal K), then signalk (writes its own store and feeds influxdb), then influxdb (the database), then nginx (terminates external connections including the `mlb.dglc.com` bowling proxy). The bowling app DB is on the Mac Mini — stop `com.dglc.bowling-app` there separately if doing Mac maintenance. Services with `Restart=always` will restart automatically on boot; nginx does not, so start it explicitly after the swap: `sudo systemctl start nginx`.

## Backup Automation

`nas-image-backup.timer` runs `nas-image-backup.service` on the 1st of each month at 03:00 EDT. The service runs `scripts/nas-image-backup.sh`, which mounts the NFS share, stops the disk-writing services, runs `image-backup` against `/mnt/nas-pi-backups/pivac.img`, and restarts services on EXIT. Typical incremental: ~2 minutes downtime. See `~/CLAUDE.md` Backup section for the full architecture (NAS share, NFS+ACL gotcha, bootstrap caveats).

> **nginx is deliberately NOT in this script's stop set** (unlike the SD-maintenance stop list in Standard Deployment Procedure, which legitimately stops it because you're pulling the card). nginx holds no database, so quiescing it adds nothing to image consistency, but stopping it blacks out the `mlb.dglc.com` bowling proxy (whose DB lives on the Mac Mini, unaffected by Pi service stops) and trips the Grafana mlb-availability alert. Observed 2026-06-01: the first auto-run woke David with an mlb alert that was purely the backup window. The script now keeps nginx up — mlb stays available throughout the ~2-min backup.

> **Two failure modes fixed 2026-06-01** (first monthly auto-run failed on both): **(1)** the `.img` root partition was sized to usage + minimal slack at 2026-05-08 bootstrap (54.4 G) and the live root outgrew it (54.9 G) → rsync `ENOSPC`. `image-backup` never resizes an existing image on incrementals. Fix: grew `pivac.img` in place to the full card size (`truncate` to 119.2 G → `parted resizepart 2 100%` → `e2fsck` → `resize2fs`), restoring the MBR disk identifier to `0xf9199e61` afterward (parted regenerates it; it must match the source card so the image's `PARTUUID=` fstab/cmdline refs stay bootable). Now ~63 G free inside the image. **(2)** rsync exit 23 on `/home/pi/thinclient_drives`, an `xrdp-chansrv` FUSE mount that exists only while an RDP session is active — root can't traverse it. Fix: the script now passes `image-backup -o '--exclude=/home/pi/thinclient_drives'`. The 2026-05-08 bootstrap missed both because the system was smaller and had no live RDP session.

`sd-clone.timer` runs `sd-clone.service` weekly (Sunday 02:00 EDT). The service runs `scripts/sd-clone.sh`, which auto-discovers the populated slot of the USB SD reader by USB VID:PID `05e3:0764` (Anker USB 3.0 Micro SD Card Reader, Genesys Logic chipset), refuses if the target matches the booted disk, then calls `rpi-clone <target> -U`. No service stop — `rpi-clone` is designed for live cloning. First run repartitions and takes ~30 min; subsequent incrementals are ~3 min. The clone is a directly bootable hot-recovery spare: pull live SD, drop the spare in, reboot. Install dependency: `rpi-clone` from `~/github/rpi-clone` (billw2/rpi-clone), copied to `/usr/local/sbin/`.

## Checking Logs

```bash
# All pivac services
journalctl -u pivac-1wire -u pivac-redlink -u pivac-gpio -u pivac-arduino-psi -u pivac-arduino-therm-psi -u pivac-emporia -u pivac-sentry -u pivac-watermeter -n 50 --no-pager

# Single service
journalctl -u pivac-redlink -n 50 --no-pager

# Signal K server
journalctl -u signalk -n 50 --no-pager
```

## Known Operational Behaviours (Not Bugs)

- **WaterMeter glyph library is incomplete (deployed 2026-06-16)**: the template library at `/etc/pivac/wm-templates/` currently covers digits **0,1,2,4,6,7,8,9** — **3 and 5 are still being captured** (the meter advances slowly). When a `3` or `5` appears in a digit position the reader can't match it (correlation below `min_corr`), so it **skips that cycle** rather than emit a wrong value → expect occasional gaps in `environment.water.domestic.consumption` until the library is completed. This is by design (gaps, not garbage); the `max_reading_jump` monotonic guard is a second filter. Also: the totalizer is **integer-gallon for now** (decimal-digit boxes not yet calibrated → `.flowing` stays 0); decimals/flow come online once those boxes are set. Update the library by dropping new `<glyph>_<n>.png` files into the templates dir — the module hot-reloads on mtime, no restart. **The camera must stay in its current locked mode + lighting** (mirror of the Sentry day/night lock); a mode/lighting change invalidates the warp + templates.
- **Whole-Pi "hung again" was WiFi, not pivac (root-caused + fixed 2026-06-16)**: Symptom was the entire Pi off the network (ping "Host is down", ARP `incomplete`) — *not* a hung service. Root cause was **WiFi power-save on a weak 2.4 GHz link**: the radio slept, the AP dropped the station, the supplicant failed to re-associate, DNS started failing (`Name or service not known` across RedLink/Emporia/Sentry), then the host fell fully off the wire and needed a power-cycle. Ruled out as causes: power (`vcgencmd get_throttled` = `0x0`), SD/filesystem (no ext4/IO errors), temp (54.5°C), signal (-58 dBm is fine). **Permanent fix: moved the Pi to wired ethernet** (see Remote Access → Pi network interfaces). If a future hang recurs, first check whether it's the whole host (ping/ARP from another LAN box) vs a single service, then `vcgencmd get_throttled` and `nmcli device status` before assuming pivac.
- **RedLink after a network/DNS outage needs a clean restart**: When the Pi boots into (or rides through) a DNS-less window, `pivac-redlink` accumulates a half-broken Honeywell session *and* a repeatedly-dropping SignalK WebSocket (`Broken pipe` → reconnect), and limps for many cycles even after DNS recovers. Once `getent hosts mytotalconnectcomfort.com` resolves again, `sudo systemctl restart pivac-redlink` gives it a fresh login + fresh WebSocket and all 5 rooms republish within ~2 min. This is **not** the `APIRateLimited` case the rate-limit note warns against restarting — check the logs for `APIRateLimited` first; if absent, restart is the right move.
- **Arduino timeouts**: Both Arduinos (10.0.0.114 and 10.0.0.219) occasionally go unresponsive. Logged as a single WARNING. Self-recover; occasional power cycle needed.
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
| `ArduinoSensor` | Arduino HTTP sensor — **multi-field**: loops over `inputs` (key = response field name); inputs with `type: temperature` convert to Kelvin and emit `{sk_path}.{outname}.temperature`. Shared via `module:` override by `pivac.ArduinoPSI` (.114 = **DHW** pressure + recirc temp `environment.inside.hvac.dhw.recirc.temperature`) and `pivac.ArduinoThermPSI` (.219 = **boiler/hydronic** pressure). NB names are inverted vs role — see Active Services note. |
| `Emporia` | Emporia Vue Gen 2 power monitors — polls two panels (house 200A, apartment 100A) via PyEmVue, emits per-circuit Watts to `electrical.emporia.<panel>.<circuit>` |
| `Sentry` | NTI Trinity Ti-200 boiler controller via Tapo C120 RTSP camera — reads display via 7-segment CV, emits boiler state to `hvac.boiler.sentry.*` |
| `WaterMeter` | Sensus iPerl water-meter **LCD** via Tapo RTSP camera (`10.0.0.85`) — reads the cumulative gallons totalizer via perspective-warp + **whole-glyph template matching** (NOT segment thresholding — a reflective LCD's "off" segments aren't black). Emits `environment.water.domestic.consumption` (gal) + `.flowing`. See `docs/water-meter-camera-monitoring-plan.md`. |

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

**Camera day/night mode MUST stay locked** (Tapo app → Advanced → Night Vision = **Night**, Night Boost = **Off** — *not* Auto). On Auto, the camera flips between day/color and IR/night when the boiler-room lights change; that image shift makes the 7-segment reader misfire (phantom hundreds digit — e.g. outdoor 67→167, gas→410, water 87→187). Verified root cause of the 2026-05-31 "jumping values." The module is also hardened against transient misreads (PR #62): per-mode **range-sanity** (rejects out-of-range reads) + a **median-of-samples** vote per cycle (`min_samples`, default 3) so a one-frame misread loses to the median, and it sets `OPENCV_FFMPEG_LOGLEVEL=8` to silence the libavcodec H.264 SEI log spam (~72k lines/3h).

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
