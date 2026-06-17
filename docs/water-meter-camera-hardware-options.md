# Water Meter Camera — Hardware Form-Factor Options (AI-on-the-edge vs. compact custom)

**Status:** DRAFT / DECISION PENDING — 2026-06-16
**Goal:** Decide the *physical* acquisition hardware for reading the Sensus iPerl LCD,
given that the **OCR software problem is already solved** (see
`water-meter-camera-monitoring-plan.md`, PR #68). This doc captures the
AI-on-the-edge-device option and reconciles it with the validated custom-CV pipeline.

> **Companion to `water-meter-camera-monitoring-plan.md` (PR #68).** That doc is the
> validated **custom CV** design (warp → illumination-flatten → whole-glyph template
> match → flow-aware decimals) running on the Pi against the Tapo RTSP stream at
> `10.0.0.85`. This doc does **not** replace it — it evaluates whether to swap the
> *hardware front end* for a compact, self-lit device. The downstream (Signal K path,
> Grafana, alerting) is identical regardless of which front end wins.

---

## 0. Why this is a hardware decision, not a software one

As of 2026-06-16 the camera/OCR path is **proven on this exact meter**:

- A Tapo camera is mounted at the meter (`10.0.0.85`); the **lighting gate passed** —
  with added visible light the LCD reads cleanly (`0626984.29 Gal`, pixel-stable when
  no water flows).
- A **custom CV pipeline is validated** (read `0626984` correctly from a live frame):
  perspective-warp → illumination-flatten → **whole-glyph template matching** (per-segment
  thresholding fails on a reflective LCD), plus flow-aware decimal logic (read the two
  fractional digits only when stable = no flow, else floor to integer gallon) and a
  monotonic guard.

So the OCR is **working**. The remaining dissatisfaction is purely **physical**: the
Tapo C120 is bulky and its illumination is a clumsy ~10″ USB light bar — both awkward in
a tight plumbing space where the meter must stay accessible. The question this doc
answers is: **what camera + light hardware gets a compact, out-of-the-way install?**

---

## 1. The AI-on-the-edge-device option (`jomjol/AI-on-the-edge-device`)

A mature, purpose-built ESP32-CAM firmware for reading utility meters on-device
(TensorFlow Lite digit recognition), exposing the result over **REST (`/json`) and
MQTT**. Years of community hardening; there is even a published **Sensus iPerl mount**
and independent ESP32-CAM iPerl prior art (`sarabveer/sensus-iperl-water-meter`).

**Why it fits the complaint:**

- **~40 mm self-contained module** flush against the meter glass inside a small 3D-printed
  shroud — shrinks the camera and removes the separate light fixture.
- **Flash-on-capture:** it pulses its LED only for the ~once-a-minute capture, then it's
  off. This *eliminates the always-on light entirely* (vs. the continuously-on bar) — the
  single biggest win for "not in the way / nothing glowing in the pit."
- **Zero Pi load** — OCR runs on-device; pivac just polls `/json` (the `ArduinoSensor`
  HTTP pattern). A `pivac.WaterMeter` ingest module would be ~30 lines.

**The catch — on-axis glare (flagged by our own lighting analysis).** A reflective LCD
needs **off-axis, diffused** light to avoid a specular hotspot bouncing straight back
into the lens (the custom-CV plan §1 calls for "off-axis ≥45°, diffused"). The
ESP32-CAM's integrated flash sits **on-axis**, next to the lens — the geometry we
explicitly want to avoid on this display. It's *tunable* (PWM the LED down, add a
diffuser, a polarizer film over the lens, or design the shroud to tilt the module so the
specular lobe misses the sensor), but it is the thing to **prove before committing** —
not a slam dunk. A WS2812B **ring-light** board (below) is diffuse but still roughly
on-axis.

**Firmware-stability caveat:** the production-stable firmware targets the **original
ESP32** (AI-Thinker ESP32-CAM). **ESP32-S3 support is still experimental.** This steers
hardware choice (§2).

---

## 2. Currently-available Amazon hardware

AI-on-the-edge **requires a microSD slot** (models/config/web UI) and benefits from a
**flash LED** + **≥4 MB PSRAM** + **OV2640**.

| Option | What it is | Verdict |
|---|---|---|
| **AI-Thinker ESP32-CAM** (OV2640, microSD, ≥4 MB PSRAM) — buy a kit bundling the **ESP32-CAM-MB USB programmer**, or a **USB-C variant** | The reference board; runs the **stable** firmware. ~$10–15. | ✅ **Recommended for the prototype.** Lowest risk. Caveat: PSRAM is a clone lottery — buy AI-Thinker-branded / well-reviewed and verify ≥4 MB after flashing. Single on-axis flash LED = most glare-prone (the thing to test). |
| **"AI-On-The-Edge-Cam" ESP32-S3 + PoE** (Prokyber / allexoK; Amazon **B0FVMFBG22**, also Tindie ~$28) | Purpose-built for this project: **PoE**, **WS2812B ring light** (even/diffuse/dimmable — best anti-glare), OV2640, 8 MB PSRAM, low-power. | ⚠️ **Best illuminator, but experimental S3 firmware** + thin stock. Attractive if there's an ethernet drop at the meter (no WiFi). Pick only if willing to ride beta firmware. |
| **Seeed XIAO ESP32S3 Sense** | Capable S3 cam board, easy to buy. | ❌ Experimental S3 firmware **and no bright flash LED** — bad for a dark reflective LCD. |
| **FREENOVE ESP32-Wrover CAM** | Common Amazon ESP32 cam | ❌ **No microSD slot** → AI-on-the-edge can't store its models/config. Skip. |

---

## 3. The two compact paths

| | **A. AI-on-the-edge ESP32-CAM** | **B. Keep validated CV, shrink the hardware** |
|---|---|---|
| Camera | ~40 mm, flush-mounted | Swap the bulky Tapo for a smaller camera feeding the Pi |
| Light | Integrated, **flash-on-capture (no permanent light)** — but **on-axis/glare risk** | Compact **off-axis diffused** LED (small sealed COB puck / short LED strip) replacing the 10″ bar — correct geometry, but still always-on |
| OCR | AI-on-the-edge's on-device model (re-tune ROIs/flow in its UI) | **Already-validated template-match reader** — no rework |
| Pi load | Zero (on-device) | Same as Sentry (RTSP/snapshot decode on Pi) |
| Risk | On-axis glare on glossy LCD; iPerl re-tuning in a new framework | Finding a *small* camera that locks day-mode + close-focuses as well as the Tapo |
| Throws away | The validated CV pipeline (kept as proven fallback) | Nothing |

**Hybrid worth noting:** an ESP32-CAM can also serve JPEG snapshots over HTTP; the Pi
could pull those into the *existing validated CV reader* instead of using
AI-on-the-edge's OCR. Keeps the validated software **and** the compact hardware — at the
cost of triggering/illumination glue. Only worth it if AI-on-the-edge's on-device OCR
disappoints.

---

## 4. Recommendation

Since the only real problem is physical and AI-on-the-edge is the **only** option that
removes the permanent light entirely (flash-on-capture) *and* shrinks the camera, it's
worth a **cheap prototype — gated on the glare question our own data flagged**:

1. Buy one ~$12 **AI-Thinker ESP32-CAM** (microSD + flash LED + USB programmer).
2. Flash AI-on-the-edge; test whether a **glare-free** read is achievable with the LED
   dimmed/diffused inside a shroud on this glossy LCD.
3. **If glare is beatable** → compact, light-free, Pi-offloaded win. Write `pivac.WaterMeter`
   to poll `/json` → `environment.water.domestic.consumption` (gallons; publish raw
   totalizer, derive flow downstream).
4. **If on-axis glare is unbeatable** → fall back to **Path B**: the validated Tapo-side
   CV already works, so just swap the clumsy light bar for a small **off-axis diffused**
   LED (and optionally a smaller camera) — zero software rework. The **WS2812B ring-light
   board** is the middle upgrade if a single flash LED is too harsh but all-in-one is
   still wanted.

---

## 5. Open questions for next session

- **Is the bulk mostly the camera or mostly the light bar?** If mostly the light bar,
  Path B (keep everything, shrink only the light) is by far the least work.
- **Ethernet at the meter?** If yes, the PoE ring-light board becomes much more
  attractive (dodges WiFi entirely — relevant given the recent Pi WiFi saga).
- **Glare prototype result** (the hard gate for Path A).
- **Does the iPerl display ever cycle screens?** Both live captures showed the `Gal`
  consumption screen; confirm during calibration (the reader verifies the `Gal`
  indicator before accepting either way).

---

## Sources

- [jomjol/AI-on-the-edge-device](https://github.com/jomjol/AI-on-the-edge-device) ·
  [Hardware Compatibility](https://jomjol.github.io/AI-on-the-edge-device-docs/Hardware-Compatibility/) ·
  [Dedicated hardware (disc. #2963)](https://github.com/jomjol/AI-on-the-edge-device/discussions/2963) ·
  [Working hardware list (disc. #1732)](https://github.com/jomjol/AI-on-the-edge-device/discussions/1732)
- [AI-On-The-Edge-Cam ESP32-S3 PoE board — CNX Software](https://www.cnx-software.com/2025/06/20/ai-on-the-edge-cam-esp32-s3-board-aims-to-digitize-legacy-utility-meters/) ·
  [Amazon B0FVMFBG22](https://www.amazon.com/AI-Edge-Cam-Esp32-S3-antena-Camera/dp/B0FVMFBG22)
- [ESP32-S3-EYE NOT supported (disc. #779)](https://github.com/jomjol/AI-on-the-edge-device/discussions/779)
- [sarabveer/sensus-iperl-water-meter (ESP32-CAM iPerl prior art)](https://github.com/sarabveer/sensus-iperl-water-meter) ·
  [How to read a Sensus iPerl (9-digit LCD)](https://engineerfix.com/how-to-read-a-sensus-iperl-water-meter/)
