---
paths:
  - "pivac/Sentry.py"
  - "scripts/sentry-*.py"
  - "tests/test_sentry_*.py"
  - "docs/sentry-cv-notes.md"
  - "grafana/provisioning/alerting/sentry-boiler.yaml"
---

# pivac.Sentry: the boiler display reader

<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
<!-- Copyright David Lewis -->

Loaded when a file under its `paths:` is read; `CLAUDE.md` says to read it first for any work on the Sentry reader, its camera, its calibration or the boiler's display values. Rules here; the measurements and incident history behind them are in the docs named.

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

### Operating rules

The capture strategy, the computer-vision method and every incident behind these rules are in `docs/sentry-cv-notes.md`.

- **Camera day/night mode MUST stay locked** (Tapo app → Advanced → Night Vision = Night, Night Boost = Off). On Auto the image shifts with the boiler-room lights and the reader manufactures a hundreds digit. **The camera must look at the display at an angle, never face-on**: face-on, the display's window throws the camera's own infrared back from every segment and lens, so unlit segments read as a full `188` and all eight lights as lit (2026-10-24). Colour mode in a dark room raises the gain until the digits bloom together, and the 10-diopter close-up lens blurred the view, so the camera runs the 4-diopter lens at its old distance. At the angled mount the reader holds through the shop lights switching on and off (margin 52–56 dark, 87–91 lit, tracker score 0.82 or better). Check the lock without credentials by comparing colour channels of a frame: IR is true greyscale.
- **Thresholds:** `led_ratio 1.05` (status LEDs 0.55–0.70 dark; at the angled mount `burnerOn` and `circAuxOn` followed the `DHW` relay minute for minute through both DHW calls of the night of 2026-10-25, with no low-margin warning, so lit and dark sit at least 0.15 apart), `indicator_ratio 1.15` (mode indicators 0.58–0.80 dark, 1.55–1.60 lit), both judged on a lens spot of `lens_spot_radius` 4 px against a background of `lens_bg_radius` 25 px. Those radii scale with the lens size in the frame (10 and 83 suited the 3.4× view of the short-lived closer mount), so re-measure the dark and lit ratios after any mount change, `digit_threshold_factor 0.65` with `display_bg_percentile 40` (one display-wide threshold; a per-digit threshold read glare on a blank digit as a phantom `1`). Each cycle takes a median of samples per mode, votes LED states across frames, and applies per-mode range sanity (water 40–205 °F, and 185 °F when the burner LED is dark).
- **The reader publishes its own calibration health every cycle**: `hvac.boiler.sentry.decodeMargin` is the lit/unlit segment separation in grey levels (sound 40–60, under 20 is a knife edge) and `.decodeMisses` counts modes shown but not decoded. `sentry-decode-margin` fires on an hour's mean under 20, and any firing `source: sentry` rule makes the email bridge capture 300 frames, evaluate them under the live quad and mail the report with the eyecheck image (subject `[Sentry eyecheck]`, at most once per 30 min). The fix stays manual. **Choose a quad on margin, never on clean rate alone**: score candidates with `sentry-warp-search.py`, require 40 or more on every ±1 px neighbour, and calibrate on captures from both thermal states (soon after a DHW call and well after) whose digits between them include a `6` or `5` and a hundreds `1`. The 09-09 quad was 100 % clean on `7`, `1`, `0`, `8` and read every `6` as an `8` two days later, and the display does not move between the states: the content does. The module's segment rectangles sample the middle of each segment for this reason; widening them makes both states worse (`docs/sentry-cv-notes.md`, 2026-09-12).
- **Calibration drift recurs roughly monthly, and after every visit to the boiler room**; check the decode rate after any physical work there. First check: `journalctl -u pivac-sentry | grep "nothing decoded"`, and check `waterTemp` and `outdoorTemp` for going stale, because a large move logs nothing. The reader tracks translation creep itself, up to 15 px at a score of 0.6 or better (`registrationX`/`Y`/`Score`; reference in `/var/lib/pivac/sentry-registration.npz`, directory owned by `pi`, reset whenever `display_warp`, `leds` or `indicators` change). A larger knock, a rescaled view or a day/night flip needs a manual recalibration with `scripts/sentry-warp-search.py`. Recalibrate by measuring: capture ~400 frames, including one while the burner fires and both thermal states; keep `dst_w`/`dst_h`/`digit_positions` fixed; judge against the digits on the eyecheck image and against RedLink outdoor and the DHW recirc temperature, never the clean rate alone. Corners since 2026-10-26: `TL(910,455) TR(1046,457) BR(1039,527) BL(902,523)`. Procedures for large knocks and the incident list: `docs/sentry-cv-notes.md`, Calibration drift in full.
- **`leds:` and `indicators:` drift with the camera too — re-aim them in the same pass as `display_warp`, never the quad alone.** They are absolute frame coordinates. Left behind through the 07-28 and 08-23 quad recalibrations, all eight slid off their lenses onto the bright bezel, which lifted `burner`'s dark reading to 1.040–1.051 against its 1.05 threshold and made `burnerOn` report noise: 371 samples lit while `gasInputValue` was 0, and 69 % of ON runs one sample long. Aimed coordinates since the 2026-10-25 move are LEDs `burner(1073,453) circ(1073,479) circ_aux(1074,505) thermostat_demand(1073,529)` and indicators `water_temp(910,541) air(954,541) gas_input(997,544) dhw_temp(1041,544)`; a dark LED then reads about 0.6. Locate all eight by dark-blob centroid on the per-pixel minimum of the capture (every lens is unlit somewhere in 600 frames), in a window no wider than ±12 px seeded by eye from a gridded zoom; a ±22 px window on the mean image put three LEDs on the bezel at 0.93–0.95 dark. **A drifted spot reads the bezel, not the LED**, so it barely moves when the LED lights — the old `burner` spot swung +0.012 across a real DHW call while the aimed one swung +0.421, and `circ_aux` there read the running pump as off for all ten samples. Check the swing, not the level. The module warns when a spot sits within 0.03 of its threshold for most of a cycle — grep `lit-threshold` alongside `nothing decoded`.
- **Do the frame captures from a Mac, not the Pi.** The camera is an ordinary LAN RTSP source, and capturing from the M2 works alongside a running `pivac-sentry` without stopping it or loading a fanless Pi 4. Crop at capture time and keep frames `uint8`: stacking 200 full-res float64 frames is ~5.9 GB and rebooted the Pi on 2026-09-06.
- **Validate `air` against `environment.outside.thermostat.temperature` (RedLink), not `environment.outside.temperature`** — the latter is a stale InfluxDB orphan that still answers `last(value)` with a months-old reading. The boiler's own outdoor sensor reads warm because it has drifted low (NTI 6000083604, 20.7 kΩ at 39 °F on 2026-11-14 against about 27.5 kΩ for a sound 10k), by about `11.85 − 0.1 × RedLink` °F at night (5 °F at 65 °F, 8 °F at 35–45 °F), so compare a search's `air` against that offset; the search's 5 °F "do not apply" check does not allow for it. **The Sentry 2100 runs HI 175, RES 82, DIF 10, LO 160 since 2026-11-14** (HI 190, RES 100, LO 180 before), a curve set for that drift to give 126 °F water at 35 °F and 160 °F at 0 °F on RedLink's scale; a sound replacement sensor goes with HI 160, RES 80. The replacement, a BAPI BA/10K-2-O-BB2 (10K Type II), was ordered 2026-11-15; the day it is fitted, remove the drift term from `sentry-outdoor-divergence`, which otherwise fires within about 2 h. `sentry-outdoor-divergence` fires when the reading leaves the modelled drift by 5 °F for 2 h. Basis and checks: `docs/chiltrix-shoulder-season-heating-plan.md` §9.1.
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
| `hvac.boiler.sentry.decodeMargin` | number | Lit minus unlit segment separation, grey levels; sound 40–60, under 20 alerts (`sentry-decode-margin`) |
| `hvac.boiler.sentry.decodeMisses` | number | Display modes shown this cycle but not decoded; emitted every cycle |
| `hvac.boiler.sentry.registrationX` / `.registrationY` | number | Camera creep in px the reader moved its quad and lens spots by this cycle (since 2026-09-13) |
| `hvac.boiler.sentry.registrationScore` | number | Match of the panel's fixed structure against the saved reference; 1.0 at the reference, held below 0.6 |

Temperature values are raw °F as shown on the display. Boolean indicators are emitted as integer 0/1 (not Python bool) so that InfluxDB stores them as float and Grafana can plot them with mean() aggregation. **Important:** if you ever need to reset these measurements in InfluxDB, you must also restart Signal K after reseeding — the `signalk-to-influxdb2` plugin caches field types in memory and will re-write booleans until the process restarts.

Display hardware, config fields and dependencies: `docs/sentry-cv-notes.md`.

## Reference docs

| Doc | Covers |
|-----|--------|
| `docs/sentry-cv-notes.md` | Sentry display reader: capture strategy, CV method, LED thresholds, drift recalibration, phantom digits, thermal tuning, display hardware, config fields |
