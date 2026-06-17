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

## 2. iPerl display behaviour (confirmed from live frames 2026-06-16)

- The register shows a **9-digit cumulative totalizer**: **7 integer digits + a decimal
  point + 2 fractional digits** (tenths and hundredths of a gallon), with a **`Gal`**
  unit indicator below. Example observed: `0626984.29`.
- **The two fractional digits spin while water flows.** A single frame catches them
  mid-update, so they smear/ghost during flow but are crisp when no water is moving.
  This is a *signal*: their stability across the per-cycle frames distinguishes
  **flow vs. no-flow** (see §3 decimal logic) — not merely glare.
- The integer digits change slowly (once per gallon) and read **cleanly and reliably**
  in every frame.
- Confirm during calibration whether the display also cycles to other screens
  (rate-of-flow/diagnostics); both live captures showed the `Gal` consumption screen, so
  screen-cycling may be minimal. The reader still verifies the `Gal` indicator before
  accepting a reading. Units are **gallons**; we publish the raw reading, not converted.

---

## 3. Module design — `pivac.WaterMeter` (NOT a Sentry algorithm port)

New `pivac/WaterMeter.py` implementing the standard `status(config={}, output="default")`
contract. **Only the capture/warp scaffolding transfers from Sentry; the digit reader is
new.** A reflective LCD has faint *inactive*-segment ghosting (off ≠ black), so Sentry's
per-segment brightness threshold cannot cleanly tell on from off — confirmed empirically
(Otsu/threshold binaries were unusable). The reader is **whole-glyph template matching**,
which uses the entire digit shape (the way the display is actually read by eye) and is
robust to the LCD's low, uneven contrast.

**Validated pipeline (proven on a live frame 2026-06-16 — read `0626984` integer part
correctly):**

1. **Capture** — Sentry's `_open_stream` / drain-buffer pattern (incl.
   `OPENCV_FFMPEG_LOGLEVEL=8` and deferred `cv2`/`numpy` import). Grab ~8 frames over ~5s
   per cycle.
2. **De-skew** — detect the 4 LCD corners (bright-glass contour → `approxPolyDP`) and
   **perspective-warp** to a flat rectangle (the display is rotated/skewed in the frame).
   Corners can be auto-detected or pinned in config (found: TL `(1142,346)`,
   TR `(1651,342)`, BR `(1668,499)`, BL `(1150,499)`; rectified to 560×160).
3. **Illumination-flatten** — divide the digit band by a large-sigma Gaussian blur to
   remove the brightness gradient/glare (plain Otsu floods; this does not).
4. **Segment digits** — 7 integer digits at a fixed ~55px pitch, then a decimal-point
   gap, then 2 fractional digits. Boxes from calibration (not an even 9-way split — the
   decimal gap breaks uniform spacing).
5. **Classify** — per digit cell, normalized cross-correlation against a **template
   library** of glyphs 0–9; take the best match. Templates are bootstrapped from labeled
   real captures (averaged per glyph as more frames arrive).
6. **Screen check** — confirm the `Gal` consumption indicator before accepting.

**Flow-aware decimal logic (the key behavioural rule):**

- Read the **decimal digits only when they are stable across the per-cycle frames**
  (= no flow) → publish the exact total (e.g. `626984.29`).
- When the decimals **change across frames** (= flowing) → they are untrustworthy →
  publish the **integer-gallon floor** (`626984`) for that cycle. Flooring is always
  conservative, so it never overshoots and never trips the monotonic guard; the next
  static read re-syncs the exact total. Emit a derived **`flowing`** boolean too.
- **Monotonic guard** (cumulative-meter validator): a new accepted total must be
  **≥** the last and within `max_reading_jump`; reject otherwise. Combined with always
  flooring during flow, the published series is guaranteed non-decreasing.
- Keep a **median-of-samples** vote on the integer digits per cycle (Sentry pattern) to
  drop one-frame misreads.

### 3.1 Calibration helper

A `scripts/wm-calibrate.py` modeled on `scripts/sentry-calibrate.py`: pull a reference
frame, set/confirm the `display_warp` corners, the 9 digit boxes (7 integer + 2 decimal),
the `Gal` indicator ROI, and **capture/label glyph templates** for the library. The meter
advances slowly, so it will accumulate all ten glyphs over repeated runs (currently only
0/2/4/6/8/9 are on the display).

### 3.2 Config block (in `/etc/pivac/config.yml`; sample in `config/config.yml.sample`)

```yaml
pivac.WaterMeter:
    rtsp_url: "rtsp://USER:PASS@10.0.0.85:554/stream1"   # Pi config only — never in repo
    daemon_sleep: 15            # seconds between cycles (framework key) — ~5s capture on top → ~20s period
    capture_seconds: 5          # per-cycle frame-grab window (flow-stability detection)
    int_digits: 7
    dec_digits: 2               # tenths/hundredths gallon — read only when stable (no flow)
    display_warp: { corners: [...], dst_w: 560, dst_h: 160 }   # from wm-calibrate.py
    digit_boxes: [ {x,y,w,h}, ... ]            # 9 boxes; decimal gap is non-uniform
    gal_indicator: { x: ..., y: ... }          # consumption-screen confirm
    template_dir: /etc/pivac/wm-templates       # glyph library (0-9)
    max_reading_jump: 50        # gal; monotonic guard rejects bigger single-cycle jumps
```

Secrets (RTSP credentials) live only in `/etc/pivac/config.yml`, same discipline as
the Sentry/Tapo and Graph creds.

---

## 4. Signal K output

Reuse the path the radio plan reserved so Grafana/alerts are front-end-agnostic:

| SK path | Value | Notes |
|---------|-------|-------|
| `environment.water.domestic.consumption` | number, **gallons** (monotonic cumulative) | the iPerl totalizer; exact `.NN` when static, integer floor during flow. Flow derived downstream. |
| `environment.water.domestic.flowing` | number (0/1) | derived from decimal-digit instability across the per-cycle frames; 1 = water moving |

Emit only when a `Gal`-screen reading passes the sanity + monotonic checks; otherwise
skip the cycle so the freshness alert (§5) covers prolonged gaps rather than republishing
a stale/garbage value (same policy as Sentry).

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
