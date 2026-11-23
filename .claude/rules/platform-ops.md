---
paths:
  - "scripts/systemd/**"
  - "scripts/nas-image-backup.sh"
  - "scripts/sd-clone.sh"
  - "scripts/pivac-services.sh"
  - "scripts/pivac-provider.py"
  - "pivac/__init__.py"
  - "docs/operational-notes.md"
  - "docs/new-pi-cutover.md"
---

# Platform operations: the Pi, Signal K, nginx, WilhelmSK and backups

<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
<!-- Copyright David Lewis -->

Loaded when a file under its `paths:` is read; `CLAUDE.md` says to read it first for any work on the Pi itself, Signal K, nginx, WilhelmSK, the network or a backup. Rules here; the measurements and incident history behind them are in the docs named.

## Network and WilhelmSK

**Pi network interfaces (Pi 4 Rev 1.5 `88:a2:9e:3c:c3:73`, on the rev B INT and rev C EXT I/O boards since 2026-10-11, wired since 2026-06-16):** `eth0` (`88:a2:9e:3c:c3:73`) is DHCP-reserved to `10.0.0.82` on the UCG, route metric 100. `wlan0` (`88:a2:9e:3c:c3:74`) is a fallback on SSID `redux`, DHCP-reserved to `10.0.0.130` on the UCG (the profile itself is `ipv4.method auto`), locked to 5 GHz with power-save disabled, metric 600; failover is automatic by metric, but the port forwards target `.82` only, so external access does not fail over. The profile is `redux` (file `/etc/NetworkManager/system-connections/Wireless connection 1.nmconnection`, PSK system-owned). If `wlan0` fails to rejoin and `journalctl -u NetworkManager` shows `no-secrets`, re-set the PSK with `nmcli connection modify redux wifi-sec.psk <pw>` and `nmcli connection up redux`. Re-enable the radio from a console with `nmcli radio wifi on`. History in `docs/operational-notes.md`.

**WilhelmSK layout file:** `iphone.wlyt` lives at `~/OneDrive - DGLC/Claude/iphone.wlyt` on the Mac (also the Cowork working folder). To import after edits: copy to "On My iPad" in Files app (can't open directly from OneDrive due to iOS sandboxing), then tap to open in WilhelmSK. Or AirDrop from Mac.

Layout has 2 pages:
- **Page 1** (template `"1"`, 14+ slots): main dashboard — 5 thermostat room tiles, 4 HVAC water temp gauges (In/UBT/LBT/Out), switch bank, 2 PSI gauges, Sentry widgets
- **Page 2** (template `"5"`): Grafana WebGauge + SwitchBank

Sentry widgets use these SK paths (all under `hvac.boiler.sentry.*`):
- `hvac.boiler.sentry.waterTemp` — °F, WaterTempGauge type
- `hvac.boiler.sentry.gasInputValue` — integer 40–240, TextGaugeConfig type

**Important — Signal K behind nginx:** The `/signalk/` location block must include `proxy_set_header X-Forwarded-Proto https` and `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for`. Without these, Signal K constructs its WebSocket discovery URL as `ws://localhost:3000/...` instead of `wss://68lookout.dglc.com/...`, causing WilhelmSK to attempt a plain WebSocket connection on port 80, which nginx redirects (301) and breaks the handshake. Signal K's "Trust Proxy" setting must also be enabled in the admin UI. nginx must also forward `/skServer/` (the admin API) and `/plugins/` (plugin routes): WilhelmSK pairs for push notifications by posting to `/plugins/push-notifications/registerDevice`, and without that block the request 404s at nginx (added 2026-09-06). It must also forward `location = /login` to Signal K's root login, which is where WilhelmSK posts its credentials; without it every login 404ed at nginx from at least 2026-09-24 until 2026-10-08, and the app ran on read-only access. `location /security/` is there for the same reason: WilhelmSK approves a device access request with `PUT /security/access/requests/<id>/approved`, which 405ed at nginx until 2026-10-08. An access-request alert whose request has expired cannot be cleared by any API; `restart signalk` drops it.

## Backup Automation

`nas-image-backup.timer` runs `nas-image-backup.service` on the 1st of each month at 03:00 local time. The service runs `scripts/nas-image-backup.sh`, which mounts the NFS share, stops the disk-writing services, runs `image-backup` against `/mnt/nas-pi-backups/pivac.img`, and restarts services on EXIT. Typical incremental: ~2 minutes downtime. See `~/CLAUDE.md` Backup section for the full architecture (NAS share, NFS+ACL gotcha, bootstrap caveats).

> **⚠️ Every pivac unit has `Requires=signalk.service`, so the script's `systemctl stop signalk` stops them ALL, and any unit missing from `START_SVCS` stays dead after the backup.** When adding a pivac service, add it to both `STOP_SVCS` and `START_SVCS` in `scripts/nas-image-backup.sh`. Stopping InfluxDB fails every Grafana rule's query, so the script holds a Grafana silence on all rules from before the stop until 15 min after the restart (60 min at most, so a hung backup still alerts); the email bridge and `pivac.GrafanaAlerts` both honour it. The silence uses the Admin token at `~/.config/grafana-claude-agent.key`, and the journal logs `Grafana silence <id> ends in N min`, or a WARNING if it could not be set. If any path is still stale after the silence ends, its alert fires then; check `systemctl list-units 'pivac-*' --all` for units the restart missed.

> **nginx is deliberately NOT in this script's stop set.** It holds no database, and stopping it blacks out the `mlb.dglc.com` bowling proxy and trips the mlb-availability alert. The SD-maintenance stop list above does stop it, because there the card is being pulled.

> **Image sizing and exclusions:** `image-backup` never resizes an existing image on incrementals, so `pivac.img` was grown to the full card size (the image's MBR disk identifier must equal the live card's, `0xf8c4a716` since the 2026-09-26 cutover (set that day), because an incremental copies the card's `cmdline.txt` and `fstab` verbatim and `image-backup` only rewrites their `PARTUUID=` in extract mode; after a card change set it with `sfdisk --disk-id pivac.img 0x<id>` before the next run), and the script passes `-o '--exclude=/home/pi/thinclient_drives'` for the xrdp FUSE mount that root cannot traverse. Both were the 2026-06-01 first-run failures; details in `docs/operational-notes.md`.

`sd-clone.timer` runs `sd-clone.service` weekly (Sunday 02:00 local time). The service runs `scripts/sd-clone.sh`, which auto-discovers the populated slot of the USB SD reader by USB VID:PID `05e3:0764` (Anker USB 3.0 Micro SD Card Reader, Genesys Logic chipset), refuses if the target matches the booted disk, then calls `rpi-clone <target> -U` and **rewrites `root=PARTUUID=` in the clone's `/boot/firmware/cmdline.txt` to the target's disk identifier** (billw2's rpi-clone only looks for `/boot/cmdline.txt`, so on Bookworm every clone before 2026-09-07 was unbootable: kernel loads, then waits for the old card's root partition). The script exits 2 if that rewrite cannot be verified. No service stop — `rpi-clone` is designed for live cloning. First run repartitions and takes ~30 min; subsequent incrementals are ~3 min. The clone is a directly bootable hot-recovery spare: pull live SD, drop the spare in, reboot. **The USB reader must be on the live Pi with a card in it.** Install dependency: `rpi-clone` from `~/github/rpi-clone` (billw2/rpi-clone), copied to `/usr/local/sbin/`.

## Platform

- **The provider WebSocket is read as well as written** (PR #86): a reader thread answers Signal K's 30 s pings. Before it, every service was heartbeat-killed ~60 s after connect and lost ~30 s of deltas per cycle. Regression signature: `auth/login` climbing ~6/min in the signalk journal plus `Broken pipe → reconnect` warnings. The 4–7 s tap-to-tile floor on the water tiles is physics.
- The boot-time WebSocket race is handled by backoff. `/etc/crontab` reboots the Pi every Sunday at 00:00; tiles flicker briefly.
- A whole-Pi "hang" was WiFi power-save; the Pi is wired now. Check host versus service first (ping/ARP from another box), then `vcgencmd get_throttled` and `nmcli device status`.
- **The journal is capped at 1 GB** (`/etc/systemd/journald.conf.d/50-persistent.conf`, since 2026-09-27; 200 MB before held 26 hours). The Pi was brought to kernel 6.18.50, Grafana 13.2.2, Node 24.21 and Signal K 2.33.0 the same day. OpenCV stays at 4.13, because the Sentry reader is calibrated on it; do not take 5.0 in a routine upgrade. The GitHub CLI apt repository needs its keyring refreshed from `https://cli.github.com/packages/githubcli-archive-keyring.gpg` when `apt update` reports a missing key.
- **`vcgencmd get_rsts` tells a power loss from a watchdog reset.** `0x1000` is a power-on reset, which is what the 2026-09-07 19:40 EDT restart was: power bumped during the 1-wire rewire, which also opened the H1 pigtail joint (DS2482 status: line high, no presence) until the CAT6 re-pull replaced it that evening. A watchdog or software reset sets a different bit. The journal ends mid-line either way, because `RuntimeWatchdogSec=15` is set. Fetch InfluxDB analysis data one measurement at a time with `aggregateWindow` all the same; a wide `group()` + `pivot()` over a week of 1-minute data across ~25 series is the heaviest thing the Pi has been asked to do.
- The WaterMeter camera reader is retired (`pivac-watermeter` stopped 2026-06-17 and disabled 2026-06-27); `environment.water.domestic.*` comes from `pivac-domestic-water` since 2026-07-03.
- **`navigation.position` is the house, seeded from `~/.signalk/baseDeltas.json`** (40.89929, −74.43873, added 2026-09-06), and the same file carries the relay `order` metadata for the WilhelmSK SwitchBank. Keep it: WilhelmSK 1.18 and 1.19 crash on every launch while a `notifications.mob` entry carries a null position (`SignalKSource.m:1028` subscripts an `NSNull`), and the server fills that field from `navigation.position`. The MOB button in the app's top bar exists only with "Use V2 Notification API" checked, which is also what makes silence, acknowledge and clear work on pivac alarms. If an MOB is raised by accident: `DELETE /signalk/v2/api/notifications/<id>` with an admin JWT, then `restart signalk` to drop the frozen path.
- **Grafana inside WilhelmSK:** every device shares the `admin` login, so a theme tap on one changes all (fix: `preferences` table `user_id=1`, or `?theme=dark` on the widget URL). Blank panels after hours in the background are the web view's JavaScript stopped, fixed in the app (sbender9/Wilhelm#155). nginx's `/grafana/` block has no WebSocket headers, so Grafana Live fails with 400, harmlessly.
- WaterMeter glyph templates: `/etc/pivac/wm-templates/` (Pi-local calibration, **not** in repo — `<glyph>_<n>.png`, multiple exemplars per digit; drop in updated/new glyphs and the module hot-reloads on mtime change, no restart)

## Signal K Upgrade (if needed)

The admin console upgrade fails with ENOTEMPTY. Use the manual procedure:
```bash
sudo systemctl stop signalk
sudo rm -rf /usr/lib/node_modules/.signalk-server-*
sudo npm install -g signalk-server@latest
sudo systemctl start signalk
```

## Reference docs

| Doc | Covers |
|-----|--------|
| `docs/operational-notes.md` | RedLink internals, relay roster and zone map, GPIO 26, sprinkler calibration and watering rules, Shelly plugs, watchdog design, dashboard panel transforms, network, backup history |
| `docs/valve-lever-replacement.md` | 316 stainless replacement lever for the rusted A.Y. McDonald ball valves: stem, flat-pattern dimensions, ordering and bending; `hardware/valve-lever/` holds the DXF, 1:1 SVG and generator |
| `docs/butterfly-handle-replacement.md` | Replacement for the red butterfly handle on the hose-end drain valves (M6×1 nut, 5 × 8 mm double-D drive, groove-and-lug stop): dimensions from the broken base, 85 mm rising wings, 316L print; `hardware/butterfly-handle/` holds the CadQuery generator, STEP, STL and 1:1 SVG |
