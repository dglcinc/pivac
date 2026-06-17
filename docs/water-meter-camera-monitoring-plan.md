# Domestic Water Consumption Monitoring — Camera/CV Plan

**Status:** DRAFT FOR REVIEW — 2026-06-16
**Goal:** Add a `pivac.WaterMeter` module that reads the **Sensus iPerl** meter's LCD
totalizer from an RTSP camera (same pattern as `pivac.Sentry`), publishes the
cumulative reading to Signal K, and plots flow in Grafana.

> **Relationship to the radio plan.** `docs/water-meter-monitoring-plan.md` (merged
> as PR #67) covers the **wM-Bus radio** approach (CC1101 + `wmbusmeters` decode).
> This document is the **camera/CV alternative**, chosen because the camera is
> already installed and aimed at the meter. The two approaches share the **same
> Signal K path and Grafana/alert design** (§4–§5), so only the acquisition front
> end differs. If the lighting gate (§1) proves impractical, the radio plan remains
> the documented fallback.

---

## 0. Empirical assessment (done 2026-06-16)

Captured live frames from the meter camera (`10.0.0.85:554`, Tapo, 2560×1440 H.264)
and analyzed them, **before and after a lighting change**.

**Before lighting change — LCD unreadable:**

| Finding | Result |
|---------|--------|
| **Focus / resolution** | **Excellent.** Fine printed text (`SENSUS`, `iPERL®`, serial `91957598`, `3/4" S`, `Mfg Date 09/2023`) is sharp; digit-scale features resolve well. Camera placement and lens are not a limiter. |
| **Camera mode** | **IR / low-light mono** — meter in a dark pit, monochrome image. |
| **LCD legibility** | **Zero.** Uniform grey rectangle, no visible segments, stable across a 24 s burst. Histeq + 2.5× contrast stretch reveal nothing. |

**Root cause:** a reflective/transflective LCD modulates only **visible** light; with no
visible illumination in the pit there is essentially no segment contrast, so the digits
vanish. (Opposite of the Sentry's 7-segment **LED**, which IR renders perfectly — hence
Sentry is locked to Night and the water meter must have visible light.)

**After lighting change — GATE PASSED ✅:**

| Finding | Result |
|---------|--------|
| **LCD legibility** | **Readable.** Digits clearly visible — reading ≈ `062696462` with the **`Gal`** unit indicator lit. |
| **Stability** | **Excellent.** Reading is pixel-identical across a multi-frame burst (static, no flow) — ideal for the median + monotonic checks. |
| **Remaining margin issues (optimize, not blocking)** | Slight brightness gradient + minor top-right glare; image still monochrome low-light mode. |

**Conclusion:** the camera/CV approach is **viable**. The lighting gate (§1) is **met**.
Two non-blocking margin-wideners remain: (a) even out / further diffuse the light to lift
the dimmer digits and kill residual glare; (b) **lock the camera mode** so the display's
appearance stays stable for calibration (Sentry precedent).

---

## 1. Lighting gate (Step 0 — PASSED 2026-06-16)

A lighting change made the LCD readable (§0). The measures below are retained for
reference; items 1/3/4 are now **optional margin-wideners**, item 2 (lock the mode) is
**still required** before calibration so the display appearance can't drift.

Add visible illumination and keep the camera mode stable, then re-capture and confirm
machine-readable digits. Cheapest → most involved:

1. **Add an always-on visible light in the pit.** The Tapo C120's night vision is
   IR-only (no white floodlight), so it cannot self-light the LCD in visible. Use a
   small **off-axis (≥45°), diffused** white LED, **sealed/outdoor-rated** for the wet
   pit, positioned so its reflection does not bounce straight into the lens (off-axis +
   diffuse is what prevents specular glare on the register glass). Tap the existing
   camera power run if possible.
2. **Force the camera to Day / color mode** (Tapo app → Night Vision = **Off/Day**,
   not Auto) so it uses the visible light and reads the LCD in proper dark-on-light
   polarity. Mirror image of the Sentry rule (Sentry stays **Night**; the water meter
   stays **Day**). **Document this as a locked setting** — Auto switching will break
   reads exactly like it did on the Sentry.
3. **If glare persists:** add a **circular polarizer / polarizing film** over the lens
   to cut the specular reflection off the LCD glass.
4. **Even out illumination** (re-aim/diffuse, or a second small light) so all digits
   are lit consistently.

**Re-assessment criteria (go/no-go):** a fresh day-mode frame must show the digits
with a clear segment-vs-background luma separation across **all** digit positions, no
saturating glare over any digit, and a stable reading when no water is flowing. Re-run
the §0 capture/measure before committing to the build.

---

## 2. iPerl display behaviour (calibration inputs)

- The iPerl register shows a multi-digit **cumulative totalizer** plus on-screen
  icons/units, and **cycles** between screens (reading ↔ rate-of-flow ↔ diagnostics)
  on a timer — directly analogous to the Sentry display cycling through modes.
- The CV must therefore **capture across the cycle** and select the **consumption
  reading** screen, identifying it from the on-LCD unit/icon (the iPerl's equivalent of
  Sentry's indicator lights). This screen-ID step is the main new calibration item.
- Confirm during calibration: digit count, presence/position of a decimal point, and
  the **display units** (US iPerl is typically gallons or cubic feet, utility-
  configured). We publish the **raw reading**; the unit is documented, not converted.

---

## 3. Module design — `pivac.WaterMeter` (modeled on `pivac.Sentry`)

New `pivac/WaterMeter.py` implementing the standard `status(config={}, output="default")`
contract. Reuse Sentry's structure wholesale; the deltas are LCD-specific:

- **RTSP capture loop** — copy Sentry's `_open_stream` / drain-buffer / poll-until-
  deadline pattern verbatim (incl. `OPENCV_FFMPEG_LOGLEVEL=8` to silence libavcodec
  spam and the deferred `cv2`/`numpy` import).
- **Display extraction** — reuse `_get_display_crop` (perspective-warp from
  calibration).
- **7-segment decode, polarity inverted.** Sentry treats a *bright* region as a lit
  segment; for the LCD a lit segment is **darker** than its background. Implement by
  inverting the digit crop (`255 - gray`) up front, then reuse Sentry's
  `_SEGMENT_RECTS` / `_SEGMENT_MAP` / threshold logic unchanged. Add digit positions
  for all iPerl digits (Sentry has 3; the iPerl has more) via calibration.
- **Screen selection** — analogous to Sentry's `_read_indicators`: detect which screen
  is showing from the on-LCD unit/icon ROI and only accept digits from the consumption
  screen.
- **Misread hardening** — keep Sentry's per-read **range-sanity** + **median-of-
  samples** vote, and **add a monotonic/jump check** unique to a cumulative meter: a
  new reading must be **≥** the last accepted reading and within a plausible delta;
  reject otherwise. This is a strong validator a totalizer affords that the Sentry
  temperatures do not.
- **Emit** the totalizer to Signal K (§4). Publish the meter's raw cumulative value;
  derive flow downstream.

### 3.1 Calibration helper

A `scripts/wm-calibrate.py` modeled on `scripts/sentry-calibrate.py`: pull a reference
day-mode frame, set the `display_warp` corners, the per-digit boxes, and the
screen-indicator ROI(s).

### 3.2 Config block (in `/etc/pivac/config.yml`; sample in `config/config.yml.sample`)

```yaml
pivac.WaterMeter:
    rtsp_url: "rtsp://USER:PASS@10.0.0.85:554/stream1"   # Pi config only — never in repo
    cycle_timeout: 30
    min_samples: 3
    display_warp: { corners: [...], dst_w: ..., dst_h: ... }   # from wm-calibrate.py
    digit_positions: [ { x, y, w, h }, ... ]                   # N digits
    screen_indicators: { consumption: { x, y } }              # which-screen ROI(s)
    max_reading_jump: <plausible per-cycle delta>             # monotonic guard
```

Secrets (RTSP credentials) live only in `/etc/pivac/config.yml`, same discipline as
the Sentry/Tapo and Graph creds.

---

## 4. Signal K output

Reuse the path the radio plan reserved so Grafana/alerts are front-end-agnostic:

| SK path | Value | Notes |
|---------|-------|-------|
| `environment.water.domestic.consumption` | number, **raw meter reading** (monotonic cumulative) | the iPerl totalizer; flow derived downstream. Document the display unit (gal or ft³). |

Emit only when a consumption-screen reading passes the sanity + monotonic checks;
otherwise skip the cycle so the freshness alert (§5) covers prolonged gaps rather than
republishing a stale/garbage value (same policy as Sentry).

---

## 5. systemd, Grafana, alerting

- **`pivac-watermeter.service`** — copy an existing `pivac-arduino-*.service` (user
  `pi`, `PIVAC_CFG=/etc/pivac/config.yml`, `Restart=always`, `RestartSec=10`). Fold
  into CLAUDE.md's restart/stop/log lists and the Active Services table.
- **Grafana** — "Domestic Water Flow" timeseries via
  `non_negative_difference(mean("value"))` on
  `environment.water.domestic.consumption` (datasource `bdxaqnfllu5fkf`, InfluxQL);
  optional cumulative + daily-usage panels. Mirror DHW-panel styling.
- **Alert (deferred until feed is stable)** — `watermeter-stale` in
  `grafana/provisioning/alerting/sensor-freshness.yaml` routing to `graph-bridge`;
  30 m staleness using the same `value < sentinel` + `noDataState: Alerting` trick as
  the other freshness rules.

---

## 6. Build sequence

0. **Lighting gate (§1)** — add visible light, lock camera to Day, re-capture, confirm
   readable digits. **Hard gate.**
1. **Calibrate (§3.1)** — `wm-calibrate.py` to set warp + digit boxes + screen ROI.
2. **Module (§3)** — write `pivac/WaterMeter.py`; standalone-test against the live
   stream until reads are stable across many cycles (incl. monotonic guard).
3. **Config + service (§3.2, §5)** — config block, `pivac-watermeter.service`; verify
   deltas land in Signal K.
4. **Grafana (§5)** — flow panel; confirm plotting; (later) freshness alert.
5. **Docs** — CLAUDE.md Active Services table, Current Modules, deployment/stop/log
   lists, SK paths, and a "lock camera to Day" note alongside the Sentry "lock to
   Night" rule.
6. **PR** — branch + PR (module + service + Grafana + config sample + docs).

---

## 7. Risks & open questions

- **Lighting/glare (§1)** — the live gate; reflective LCD needs even, glare-free
  visible light. Ladder: off-axis diffused LED → polarizer → second light → (last
  resort) radio plan.
- **Power + weatherproofing in the pit** — the added light needs power and must be
  sealed for a wet meter pit.
- **Display cycling / screen ID (§2)** — must reliably pick the consumption screen
  amid the iPerl's screen rotation.
- **Units (§2)** — confirm gal vs ft³ at calibration; document, don't convert.
- **Day/Night lock (§1.2)** — Auto mode will silently break reads (Sentry precedent).
