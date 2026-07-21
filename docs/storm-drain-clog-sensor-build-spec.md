# Storm-Drain Clog Sensor Node — Build Spec

**Status:** Design/spec. Nothing built or ordered yet.
**Goal:** Detect when the driveway storm drain (bottom-right corner) has clogged — water
backs up ~6" deep in the corner and then overflows into a limited-capacity overflow area.
Give a **push email alert** (via the existing Grafana → `graph-bridge` bridge) as soon as water
starts standing in the corner, with maximum lead time before the 6" overflow. Data lands in
Signal K → InfluxDB → Grafana like every other pivac sensor.

This is a **binary threshold** problem ("has water reached height X?"), not a level
measurement — so the design is deliberately a couple of simple switches, not an analog level
sensor. The controller is a new **UNO R4 WiFi** node living in the protected building **~20 ft**
from the drain, fed by a passive low-voltage cable — the same dry-contact-to-GPIO pattern the
[DomesticWater node](domestic-water-node-build-spec.md) uses for its reed meter.

---

## 1. Decisions & scope

**Decided (from the design conversation):**
- **One threshold — clog is binary.** A partial clog just drains slowly; it doesn't back up.
  Water *standing* in the corner is the clog signal, full stop. So a single sensor placed
  **low (~2–3")** — above incidental splash/puddle but well below the 6" overflow — catches a
  clog as soon as water starts pooling, giving the most lead time before overflow. No
  "clog-forming vs. imminent" staging (rejected — severity isn't the signal, standing water is).
  - Set the height **on site**: low enough to trip early on real backup, high enough to ignore a
    passing splash. (A second electrode near the overflow lip is a cheap *optional* redundancy /
    "still not cleared" escalation ping — not part of the core alert.)
- **Sensor isolated from debris with a stilling well.** The pine needles/grit that clog the
  drain would also foul a bare float, so the float(s) live inside a capped perforated PVC pipe
  standing in the corner (§4). This is the single most important reliability element.
- **Passive sensor at the drain, controller in the building.** No power or microcontroller
  outdoors — just dry-contact switches on a ~20 ft cable back to the UNO R4 WiFi node on a USB
  supply in the protected space. (Rejected: a battery/solar wireless node outside — more
  failure modes, no upside given the short run.)
- **Freezing is explicitly out of scope.** The drain isn't needed in freezing weather, so a
  frozen/ice-locked float in deep winter is an accepted non-issue. No heater. This is why a
  simple float or optical point sensor is fine and we don't over-engineer for ice.
- **pivac stays read-only.** The node just serves status; pivac polls it. No actuation.

**Open items to confirm before building:**
1. **A spare UNO R4 WiFi board** — all three existing boards are deployed (`.114`/`.219`/`.188`),
   so this node needs a **new** board (§2). (An ESP32 dev board would also work and is cheaper,
   but a UNO R4 WiFi drops straight into the existing `ArduinoPSI_*`/`DomesticWater` firmware
   scaffolding with zero porting — recommended.)
2. **WiFi reach** on SSID `redux` at the building, and a **USB power** outlet there.
3. **Cable route** — direct-burial vs. existing conduit for the ~20 ft run, and the real
   distance (20 ft is the stated protected-area distance; add slack).
4. **Overflow-lip height** measured in the corner, to set the two float heights.

---

## 2. Bill of materials

| # | Item | Suggested part | Notes |
|---|------|----------------|-------|
| 1 | Level sensor | **Primary: 2× stainless/graphite contact electrodes** (one sense rod at the trip height + one reference rod just below it) — *or* **1× reed float switch** (dry-contact alternative). Optional: a cheap "liquid-level/contact detector" board for a clean digital output. | See §3 — with the stilling well, bare contact electrodes (no moving parts) are the recommendation; a float is the off-the-shelf dry-contact equivalent. One detection level (§1). |
| 2 | Controller | **Arduino UNO R4 WiFi** (new — all spares are deployed) | WiFiS3 HTTP server; reuses existing scaffolding |
| 3 | Stilling well | ~24" of **2–3" PVC** + cap + a few ¼" holes drilled near the base | Keeps pine needles off the sensor; damps ripple |
| 4 | Sensor mount | Bulkhead/M10 threaded ports or a small bracket to fix the electrodes/float at the trip height inside the well | Set ~2–3" per §1 |
| 5 | Cable | **~25 ft direct-burial multiconductor** — 18/4 sprinkler wire, *or* **Cat5e in conduit** (8 conductors, cheap, plenty spare) | 2 conductors (float) or 3 (electrode drive+sense+GND); spares cover the optical option |
| 6 | Field junction | Small **IP67** potted/gel-filled junction at the drain end | The only wet connection; keep it sealed |
| 7 | Node power | **5 V USB-C supply** | Board runs on USB in the protected building — no field power |
| 8 | Surge protection | Per input: ~1 kΩ series resistor + **TVS/clamp diode to 3V3** (or an RC + Schottky clamp) at the GPIO | Outdoor line entering a building is a transient path — see the dead-GPIO-26 lesson in CLAUDE.md |
| 9 | Enclosure | Small project box for the node inside the building | Not weather-rated (indoors) |

> **Minimum float build = items 1–8.** The optical-sensor variant (§3, no moving parts) swaps
> item 1 and uses two more cable conductors to carry 5 V out to the sensors.

---

## 3. Sensor options & recommendation

All options mount **inside the stilling well** at the single trip height (§1). Freezing is a
non-issue (§1), which widens the field. **The stilling well is the key enabler here:** because the
water inside it is debris-free, the sensor no longer has to survive pine needles and grit, so the
simplest possible detector — bare **contact electrodes**, no moving part at all — becomes the
best choice. A float is now optional, not required.

### 3.1 Contact / conductivity electrodes — **recommended** (no moving parts)
Two small stainless (or graphite) electrodes at the trip height; when water rises to bridge them
the circuit conducts and it reads "wet." **Nothing to jam, wear, silt up, or float-lock** — which
is exactly why a stilling well makes this the right call: the debris that would have been the
electrodes' one weakness never reaches them.
- **Layout:** a **sense rod at the ~2–3" trip height** + a **reference rod just below it** (both
  bridged only once water stands that deep). Two electrodes, two conductors, one detection level.
- **Electrolysis mitigation:** don't hold DC on the electrodes. Either **pulse/alternate the
  excitation** briefly to sample (Arduino toggles a drive pin, reads the sense pin, ~ms), or use
  a cheap ready-made "liquid-level/contact" detector board (transistor/op-amp front-end) that
  outputs a clean digital HIGH/LOW to the GPIO. Stainless/graphite electrodes further slow wear.
- **Conductivity caveat:** storm runoff carries enough dissolved solids to conduct reliably; only
  near-distilled water would be marginal (not a concern for driveway runoff). Set the detect
  threshold generously — you only need "clearly wet vs. clearly dry."

### 3.2 Vertical stem float switch (reed) — simplest firmware, off-the-shelf
A magnetic float rides a fixed stem; a sealed reed closes as it passes. Gives a **crisp trip at a
precise height** and is a **plain dry contact → `INPUT_PULLUP` GPIO, identical to the
DomesticWater meter reed** (zero firmware porting, no excitation circuit). The tradeoff vs. §3.1
is the one moving part — now riding *clean* water in the well, so the fouling risk is largely
gone anyway. Pick this if you'd rather buy a finished part and skip any electrode front-end.
One single float at the ~2–3" trip height is all that's needed. Stainless/PP wetted parts;
"stainless steel vertical float switch reed." Generic reeds are a few dollars.

### 3.3 Optical (infrared prism) point sensor — no-moving-parts alternative
IR LED/phototransistor in a prism tip: dry = internal reflection, submerged = light escapes,
output flips. Also no moving part, and a clean digital output. Costs more than electrodes, is a
**powered 3-wire** device (needs 5 V out — trivial over the 20 ft cable), and a film on the prism
can bias it (the well largely prevents this). "Optomax LLC200D3SH" or a generic "photoelectric
liquid level sensor." Reasonable, but electrodes (§3.1) do the same job for less.

**Recommendation:** with the stilling well in place, go with **contact electrodes (§3.1)** — a
sense rod + reference rod at the ~2–3" trip height. No moving parts, cheapest, and the well
removes their only real weakness. Excite them with brief pulses (or a cheap detector board) to
avoid corrosion. If you'd rather not build any front-end at all, **a reed float (§3.2)** is the
drop-in dry-contact alternative with identical downstream wiring/firmware — either is a good
answer, and the rest of this spec (§5–§10) treats both as "a clean digital wet-at-level signal."

---

## 4. Physical install — the stilling well

```
        driveway corner (fills ~6" deep when clogged)
        ┌──────────────────────────────────────────────┐
        │   overflow lip ~6"  ····························│····▶ overflow area (limited)
        │   ── sense rod ~2–3" (clogged) ─────────────────│
        │        ┌───┐  ← 2–3" capped PVC "stilling well" │
        │        │ ┊ │     with ¼" holes near the base    │
        │  ~~~~~~│ ▪ │~~~~~~~~~~ water level ~~~~~~~~~~~~~~ │
        │        │ ▪ │  ← electrodes (or float) in clean   │
        │        │ ▪ │     water; lower ▪ = reference rod  │
        │  storm │   │     needles/grit stay outside       │
        │  drain═╧═══╧════════════════════════════════════│
        └──────────────────────────────────────────────┘
                  │ 2–3 signal conductors, ~20 ft
                  ▼
        protected building: UNO R4 WiFi (USB power) → WiFi
```

- **Stilling well:** cap the top; drill several **¼" holes around the base** so water inside
  tracks the corner while pine needles stay out. Stand it vertically in the corner, anchored so
  it can't float or tip. Drill a small vent hole high up so the pipe doesn't air-lock.
- **Set the trip height on site:** fix the sense rod (or float) at **~2–3"** — low enough to trip
  as soon as water backs up, high enough to ignore a passing splash/puddle, and well below the 6"
  overflow lip. Put the reference rod an inch or so below the sense rod. Mount via bulkhead ports
  or a bracket. (Optional redundancy electrode: a second sense rod near the lip — see §1.)
- **Field junction:** the electrode/float leads join the run cable in **one sealed IP67 junction**
  (gel/potted) at the drain — the only wet connection. Everything downstream is dry.

---

## 5. Wiring

One detection level → one signal to the node, plus GPIO protection.

**Float variant (dry contact — simplest):**
```
  Stilling-well float (dry contact, no polarity)
     float lead 1 ─── conductor 1 ──[~1kΩ]──▶ D2   (INPUT_PULLUP — idles HIGH, LOW when tripped)
     float lead 2 ─── conductor 2 ───────────▶ GND

  Per input at the node: TVS/clamp diode from the GPIO to 3V3, series ~1kΩ as above.
  UNO R4 WiFi power ◀── 5 V USB-C supply (in the building)
```
- **`INPUT_PULLUP`**: the pin idles HIGH; a submerged (tripped) float closes to GND → reads LOW.
  Debounce/sustain is in firmware (§6), so ripple and a passing splash don't alert.

**Electrode variant (recommended — no moving parts):**
```
  Stilling-well electrodes
     drive rod  ─── conductor 1 ──▶ D4 (drive: pulsed HIGH briefly to sample)
     sense rod  ─── conductor 2 ──[~1kΩ]──▶ D2 (INPUT_PULLDOWN; reads HIGH only when water bridges)
     (share the run cable's GND if using a detector board instead)
```
- The firmware **pulses D4 and reads D2** for a few ms, then idles both — so no sustained DC sits
  on the electrodes (electrolysis/corrosion guard). Water bridging the rods pulls D2 to the drive
  level during the pulse. Or drop in a cheap **liquid-level/contact detector board** (its digital
  out → D2, `INPUT`), which handles excitation for you.

**Both variants:**
- **Surge protection matters here.** A ~20 ft outdoor cable entering a building is a transient/
  static path. Put a **series ~1 kΩ + a clamp diode (TVS to 3V3)** on the sense line. pivac has
  already lost one GPIO (pin 26) to a power-event transient — don't repeat it on an exposed line.
- **Optical-sensor variant:** add conductors for **5 V** + **sensor GND**; its digital output
  goes to D2 (`INPUT`, match the sensor's active level). Cat5e's spare pairs cover any of these.

---

## 6. Arduino firmware

Reuse the WiFi/HTTP/watchdog scaffolding from the existing `ArduinoPSI_*` / `DomesticWater`
sketches in `~/github/Arduino` (WiFiS3, `WiFiServer` on port 80, RA4M1 watchdog, escalating
reconnect with `NVIC_SystemReset()` fallback, `uptime_ms`). The node adds only: read the one
wet-at-level input, **debounce + require the state sustained** before latching, and serve the
status dict.

**Output format — critical:** `pivac.ArduinoSensor` parses the response with `ast.literal_eval`
on the first line matching `.*\{.*\}`, so the dict must use **single quotes** (a Python literal,
*not* JSON) — matches every existing sketch.

```cpp
// storm-drain-clog-node.ino — UNO R4 WiFi
// One wet-at-level sensor in a stilling well: water standing in the corner = clogged.
#include <WiFiS3.h>

const uint8_t PIN_SENSE = 2;   // wet-at-level input (float via INPUT_PULLUP, or electrode/board out)
const unsigned long SUSTAIN_MS = 45000UL;   // must hold ~45 s before it counts (real clog holds; splash doesn't)
const unsigned long CLEAR_MS   = 15000UL;   // must be dry ~15 s before clearing (hysteresis)

bool clogged = false;
unsigned long wetSince = 0, drySince = 0, cloggedStartMs = 0;

// Read the sensor. Float: tripped = pin LOW. Electrode: pulse the drive pin, sample, idle it
// (no sustained DC → no electrolysis). Return true when water is bridging at the trip level.
bool readWet() {
  // Float variant:  return digitalRead(PIN_SENSE) == LOW;
  // Electrode variant (drive on D4, sense on D2 INPUT_PULLDOWN):
  digitalWrite(4, HIGH); delayMicroseconds(200);
  bool wet = digitalRead(PIN_SENSE) == HIGH;
  digitalWrite(4, LOW);
  return wet;
}

// Debounced, sustained latch with hysteresis.
bool sustainedLatch(bool raw) {
  unsigned long now = millis();
  if (raw) { drySince = 0; if (!wetSince) wetSince = now; if (!clogged && now - wetSince >= SUSTAIN_MS) clogged = true; }
  else     { wetSince = 0; if (!drySince) drySince = now; if (clogged && now - drySince >= CLEAR_MS)   clogged = false; }
  return clogged;
}

void setup() {
  pinMode(PIN_SENSE, INPUT_PULLUP);   // electrode variant: INPUT_PULLDOWN + pinMode(4, OUTPUT)
  // ... WiFi connect + watchdog (copy from ArduinoPSI sketch) ...
}

void loop() {
  bool was = clogged;
  sustainedLatch(readWet());
  if (clogged && !was) cloggedStartMs = millis();
  if (!clogged) cloggedStartMs = 0;

  // HTTP: GET / → status dict. Single-quoted literal, e.g.:
  //   {'clogged' : 0, 'clogged_s' : 0, 'uptime_ms' : 123456}
  //   clogged_s = clogged ? (millis()-cloggedStartMs)/1000 : 0
  // server.handle();  // see scaffolding
}
```

### 6.1 HTTP endpoints
| Method / path | Purpose | Called by |
|---------------|---------|-----------|
| `GET /` | status dict (below) | **pivac** (read-only) |

### 6.2 Status dict (single-quoted)
```
{'clogged' : 0, 'clogged_s' : 0, 'uptime_ms' : 123456}
```
- `clogged` — `1` when water has stood at the trip level for ≥ `SUSTAIN_MS` (drain is backed up)
- `clogged_s` — seconds since `clogged` first latched (0 while clear) — shows how long it's been
  backed up (and, in Grafana history, how long each episode lasted)
- `uptime_ms` — ms since boot; distinguishes a WiFi self-reconnect (keeps climbing) from a
  reboot (resets to ~0), same as the other sketches

### 6.3 Notes
- **The sustained-latch (`SUSTAIN_MS`) is the anti-false-alarm.** A real clog holds water for
  many minutes; wind chop, a splash, or a brief heavy-rain surge that the drain then clears
  should not email you. Tune `SUSTAIN_MS`/`CLEAR_MS` after watching a few real rain events.
- **Watchdog + reconnect:** keep the RA4M1 watchdog and escalating WiFi reconnect from the
  pressure sketches so a hung node self-heals.
- **WiFi creds** are hardcoded in the existing sketches (known issue — see the Arduino repo
  CLAUDE.md); match that pattern, don't commit creds.

---

## 7. pivac integration

No derived Pi-side value is needed (the node emits everything), so this node can use the generic
`pivac.ArduinoSensor` directly via a `module:` override — like the two pressure boards, and
unlike `pivac.DomesticWater` which needed a wrapper for `runVolume`. Add to
`/etc/pivac/config.yml`:

```yaml
pivac.StormDrain:
    module: pivac.ArduinoSensor
    description: Driveway storm-drain clog sensor via Arduino
    enabled: true
    ipaddr: 10.0.0.XXX          # UniFi-reserve by the new board's WiFi MAC, then set here
    daemon_sleep: 15            # slow-moving signal; 15 s is plenty
    inputs:
        clogged:
            sk_path: environment.water.stormdrain
            outname: clogged            # → environment.water.stormdrain.clogged (0/1)
        clogged_s:
            sk_path: environment.water.stormdrain
            outname: cloggedFor         # → environment.water.stormdrain.cloggedFor (s)
```

Then a dedicated systemd unit `pivac-stormdrain.service` (clone an existing
`pivac-arduino-*.service`, set the module arg to `pivac.StormDrain`), install, enable, and add it
to the restart/stop lists in CLAUDE.md's deployment + SD-maintenance sections.

### 7.1 Signal K paths
| Path | Type | Notes |
|------|------|-------|
| `environment.water.stormdrain.clogged` | 0/1 | water standing at the trip level, sustained — drain backed up |
| `environment.water.stormdrain.cloggedFor` | s | seconds since `clogged` latched (0 while clear) |

Booleans are emitted as integer 0/1 (not Python bool) so InfluxDB stores them as float and
Grafana can plot/aggregate them — same convention as the Sentry LED paths.

---

## 8. Alerting (Grafana → graph-bridge → email)

Add `grafana/provisioning/alerting/storm-drain.yaml` (group `storm-drain`), routing to the
existing `graph-bridge` contact point — same mechanics as `domestic-water.yaml`. Two rules:

- **`storm-drain-clogged`** (warning) — fires when `environment.water.stormdrain.clogged == 1`
  (the firmware already sustained it, so `for:` can be short, e.g. 1m). "Storm drain backed up —
  clear it before it overflows." `noDataState: OK` (the freshness rule covers no-data).
- **`storm-drain-stale`** (warning) — 30 m freshness on `environment.water.stormdrain.clogged`,
  never-true sentinel `value < -1` + `noDataState: Alerting` (same pattern as
  `domestic-water-stale` / the Arduino PSI freshness rules). Catches a dead node so a clog can't
  go undetected silently.

Deploy the YAML the same way as the others (copy to `/etc/grafana/provisioning/alerting/`,
`chown root:grafana`, `chmod 640`, `systemctl restart grafana-server` — see CLAUDE.md's
"Grafana Alerting" deployment block).

A Grafana panel on `clogged` + `cloggedFor` gives an at-a-glance history of how often and how
long the drain backs up — useful for deciding whether to address the pine-needle source (a screen
or guard over the grate). *(If you add the optional overflow-lip redundancy electrode from §1,
give it its own `clogged`-style path + rule as an "actually overflowing now" escalation.)*

---

## 9. Failure modes

| Event | Behaviour |
|-------|-----------|
| Splash / wind chop / brief rain surge | `SUSTAIN_MS` latch (~45 s) suppresses it — no alert |
| Real clog | water stands at the trip level → `clogged` latches → email |
| Sensor fouled by debris | Stilling well prevents most of it; electrodes (§3.1) have no moving part to stick — a float can swap to electrodes/optical with only a pin-mode change |
| Electrode corrosion | Pulsed excitation (§5/§6) avoids sustained DC; stainless/graphite rods |
| Deep-winter freeze / ice-lock | **Out of scope** — drain not needed when freezing (§1) |
| WiFi down | Board keeps sensing locally; pivac shows stale → `storm-drain-stale` email |
| Node hung | RA4M1 watchdog resets it; `uptime_ms` reveals the reset |
| Pi/pivac down | Node unaffected; just not published |
| Power-event transient on the outdoor line | Series R + TVS clamp on each input protects the GPIO (the dead-GPIO-26 lesson) |

pivac never actuates anything — this node is monitor-only by construction.

---

## 10. Deployment & test checklist

1. Acquire a **UNO R4 WiFi** + the sensor (electrodes or one float) + stilling-well PVC + burial cable.
2. Build the stilling well; measure the overflow lip; fix the sensor at the ~2–3" trip height (§4).
3. Wire per §5 (sense → D2, electrode drive → D4 if used, series R + clamp, sealed field
   junction); USB-power the node.
4. Flash the sketch; confirm WiFi join + `GET /` returns the single-quoted dict; bench-test by
   dipping the sensor in water and watching `clogged` latch after `SUSTAIN_MS`.
5. DHCP-reserve the board IP in UniFi by its WiFi MAC; set it in the config `ipaddr`.
6. Add the config block + `pivac-stormdrain.service`; `daemon-reload`; enable; start.
7. Confirm `environment.water.stormdrain.*` flowing into Signal K, then InfluxDB/Grafana.
8. Add `storm-drain.yaml` alert rules; test with the `graph-bridge` curl (CLAUDE.md) and by
   tripping the sensor until it latches → confirm the email arrives.
9. Update CLAUDE.md: Active Services table, Current Modules, deployment restart/stop lists,
   Known Operational Behaviours (stilling-well + sustained-latch rationale, freeze out-of-scope).
10. Field-tune `SUSTAIN_MS`/`CLEAR_MS` and the trip height after the first few real rain events.

---

## 11. References

- pivac `ArduinoSensor` contract: `pivac/ArduinoSensor.py`; config example:
  `config/config.yml.sample` (`pivac.ArduinoPSI`)
- Companion node this mirrors (reed-to-GPIO pattern, firmware scaffolding):
  `docs/domestic-water-node-build-spec.md`
- Grafana alert wiring to email: `grafana/provisioning/alerting/domestic-water.yaml` +
  CLAUDE.md "Grafana Alerting → Microsoft Graph email bridge"
- Arduino firmware scaffolding (WiFiS3, watchdog, bounded HTTP): `~/github/Arduino`
  (`ArduinoPSI_*`, `DomesticWater`)
