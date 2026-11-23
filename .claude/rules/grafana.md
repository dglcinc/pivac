---
paths:
  - "grafana/**"
  - "scripts/grafana_graph_bridge.py"
  - "scripts/systemd/grafana-graph-bridge.service"
  - "pivac/GrafanaAlerts.py"
  - "tests/test_grafana_alerts.py"
  - "docs/grafana-alerting-notes.md"
---

# Grafana, InfluxDB and alerting

<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
<!-- Copyright David Lewis -->

Loaded when a file under its `paths:` is read; `CLAUDE.md` says to read it first for any dashboard, datasource, InfluxDB query or alert-rule work. Rules here; the measurements and incident history behind them are in the docs named.

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

**Water "net of irrigation":** the Used stat panels and the hourly bars show domestic − irrigation through a `joinByField → calculateField → organize` transform chain, and both aggregates must land on one timestamp (`GROUP BY time(3650d) fill(0)`); the flow-rate panel 18 stays gross. Details in `docs/operational-notes.md`.

**ΔT panel (21)** plots warm minus cold for the primary and both secondaries on soft limits of −2 to +8 °F; never a hard min/max and never `axisCenteredZero`.

**Shared y-axis:** two series only share one axis with the same explicit `axisPlacement` and the same unit; `auto` ≠ `left`, and close-magnitude series must both be unitless.

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
- `scripts/systemd/grafana-graph-bridge.service` — runs as user `pi`, `EnvironmentFile=-/etc/pivac/graph.env`, `Restart=always`. A firing alert labelled `source: sentry` also makes the bridge run `sentry-warp-search.py --capture 300 --eyecheck` and mail the report and image as a follow-up (`SENTRY_EYECHECK_*` env overrides in the unit; an empty `SENTRY_EYECHECK_CMD` disables it).
- `/etc/pivac/graph.env` (mode 640, root:pi, **not** in the repo) — holds `GRAPH_TENANT_ID`, `GRAPH_CLIENT_ID`, `GRAPH_CLIENT_SECRET`, `GRAPH_SENDER_EMAIL`, `ALERT_RECIPIENT`. Same Azure AD app as `~utilityserver/github/bowling-league-tracker/.env` on the Mac Mini.
- `grafana/provisioning/alerting/contact-points.yaml` — defines the `graph-bridge` webhook receiver (POSTs to the bridge) and a default policy that routes everything to it.

**Rule files** live in `grafana/provisioning/alerting/` (`redlink-stale`, `sensor-freshness`, `domestic-water`, `sentry-boiler`, `chiltrix`, `zone-setpoints`). **Keep the zone setpoints within 2 °F of each other**; `zone-coolset-spread` and `zone-heatset-spread` (info) fire when any two differ by more than 2 °F for 2 h. `hz432-mode-changeover` (info) fires once per heat/cool changeover of the HZ-432; drop the firings caused by a power interruption to the boiler-room circuit from the count. The aquastat interlock is designed and not fitted, and fitting it is David's decision. Every rule routes to `graph-bridge`; thresholds, runbooks, the interlock record and retired-rule evidence are in `docs/grafana-alerting-notes.md`.

**Ship a rule on a metric that does not exist yet as `isPaused: true`**: under `noDataState: Alerting` it emails on every evaluation. Unpause once the metric publishes and verify against the `alert_rule` table.

**Every rule is also mirrored into Signal K as a notification** by `pivac.GrafanaAlerts` (`pivac-grafana-alerts.service`), so WilhelmSK shows the same alarms the email path sends: `notifications.pivac.<rule uid with - → _>`, `normal` while quiet and `warn`/`alert`/`alarm` by `severity` label while firing, silences honoured. Grafana stays the evaluator. The whole set republishes every cycle, so a restart on either side self-heals within one cycle and a dead poller leaves every path stale together. Its Viewer token lives in the module's block of `/etc/pivac/config.yml` (see `config/config.grafana-alerts-sample.yml`).

**Push to the phone** goes through the `signalk-push-notifications` plugin (id `push-notifications`, installed 2026-09-06 into `~/.signalk`, enabled with defaults in `~/.signalk/plugin-config-data/push-notifications.json`, remote push only). It pushes once per state change on any `notifications.*` path, so the poller's 30 s republish does not repeat it: a firing rule produces one push and its resolution another. Each phone pairs itself: WilhelmSK → Settings → Notifications → enable push, which posts to `/plugins/push-notifications/registerDevice` through nginx. A rule with severity `critical` (Signal K `alarm`) only bypasses the phone's silent mode if `alarmCritical` is set in the plugin config. To exercise the whole path, change the `lt` sentinel from `100` to `1000` inside the `- uid: redlink-stale` block of `/etc/grafana/provisioning/alerting/redlink-stale.yaml`, `sudo systemctl restart grafana-server`, and watch `notifications.pivac.redlink_stale` reach `warn` within about three minutes; then restore the file from the repo copy and restart again. The email path fires and resolves alongside.

**Test the bridge end-to-end:**
```bash
curl -sS -X POST http://127.0.0.1:8125/alert -H 'Content-Type: application/json' \
     -d '{"status":"firing","title":"test","alerts":[{"status":"firing","labels":{"alertname":"x"},"annotations":{"summary":"hello"}}]}'
```
Should return `ok` and an email arrives at `david@dglc.com`.

> **⚠️ Removing an alert rule needs an explicit `deleteRules:` block — provisioning is ADDITIVE (learned 2026-08-06).** Deleting a rule from `groups: … rules:` does **not** remove it from Grafana. It keeps evaluating with `provenance=file` (so it's also uneditable/undeletable in the UI) indefinitely. Evidence in `docs/grafana-alerting-notes.md`. The fix is a top-level block in the same file:
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
sudo chown root:grafana /etc/grafana/provisioning/alerting/{contact-points,redlink-stale,sensor-freshness,domestic-water,sentry-boiler,chiltrix,zone-setpoints}.yaml
sudo chmod 640         /etc/grafana/provisioning/alerting/{contact-points,redlink-stale,sensor-freshness,domestic-water,sentry-boiler,chiltrix,zone-setpoints}.yaml
sudo systemctl restart grafana-server
```

## Modules

| Module | Source |
|--------|--------|
| `GrafanaAlerts` | **Derived** — polls Grafana (`127.0.0.1:4000/grafana`, service-account token in config) and publishes every alert rule as a Signal K notification under `notifications.pivac.<uid>`: `normal` while quiet, `warn`/`alert`/`alarm` by severity while firing, silences honoured via the Alertmanager API. Publishes nothing at all when Grafana is unreadable, so a dead link shows as stale rather than quiet. See the Alerting section. |

## Reference docs

| Doc | Covers |
|-----|--------|
| `docs/grafana-alerting-notes.md` | Per-rule descriptions, thresholds, the evidence behind retired rules, and why provisioning is additive |
