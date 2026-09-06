# Storm-Drain Clog Sensor Node — Build Spec

**Status:** Design/spec. Nothing built or ordered yet.
**Goal:** Detect when the driveway storm drain (bottom-right corner) has clogged — water
backs up ~6" deep in the corner and then overflows into a limited-capacity overflow area.
Give a **push email alert** (via the existing Grafana → `graph-bridge` bridge) as soon as water
starts standing in the corner, with maximum lead time before the 6" overflow. Data lands in
Signal K → InfluxDB → Grafana like every other pivac sensor.

This is a **binary threshold** problem ("has water reached height X?"), not a level
measurement — so the design is deliberately a **single dry-contact float switch**, not an analog
level sensor. The controller is a new **UNO R4 WiFi** node living in the protected building
**~20 ft** from the drain, fed by a passive 2-conductor cable — the same dry-contact-to-GPIO
pattern the [DomesticWater node](domestic-water-node-build-spec.md) uses for its reed meter.

---

## 1. Decisions & scope

**Decided (from the design conversation):**
- **One threshold — clog is binary.** A partial clog just drains slowly; it doesn't back up.
  Water *standing* in the corner is the clog signal, full stop. So a single sensor placed
  **low (~2–3")** — above incidental splash/puddle but well below the 6" overflow — catches a
  clog as soon as water starts pooling, giving the most lead time before overflow. No
  "clog-forming vs. imminent" staging (rejected — severity isn't the signal, standing water is).
  - Set the height **on site**: low enough to trip early on real backup, high enough to ignore a
    passing splash. (A second sensor near the overflow lip is a cheap *optional* redundancy /
    "still not cleared" escalation ping — not part of the core alert.)
- **Sensor = a stainless mini float inside a stilling well (locked in).** The pine needles/grit
  that clog the drain would also foul a bare sensor, so a **stainless vertical M10 reed float**
  rides inside a **1½" PVC stilling well** standing on the drain grate (§4). The well is the key
  reliability element — it damps ripple and keeps needle *mats* off the float, which is what makes
  a simple float (rather than a fussier no-moving-parts sensor) the right call. Alternatives
  (electrodes, clamp-on capacitive, condensate-style float, optical) are documented in §3.
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
4. **Overflow-lip height** measured in the corner, to set the float trip height.
5. **Float outer diameter** on the chosen listing (~19–20 mm on the 45 mm mini) — the 1½" well ID
   (~40 mm) must clear it by several mm all around so the float slides freely.

---

## 2. Bill of materials

| # | Item | Suggested part | Notes |
|---|------|----------------|-------|
| 1 | Level sensor | **Stainless M10 vertical mini float switch** (45 mm, reed) — [YXQ B08HWRMRQR](https://www.amazon.com/YXQ-Switch-Stainless-Monitor-Vertical/dp/B08HWRMRQR) or [DEVMO B07T18PGJ4](https://www.amazon.com/DEVMO-Indicator-Vertical-Sensor-Stainless/dp/B07T18PGJ4) | Dry contact; mounts through the well cap on its M10 nut. Alternatives in §3. |
| 2 | Controller | **Arduino UNO R4 WiFi** (new — all spares are deployed) | WiFiS3 HTTP server; reuses existing scaffolding |
| 3 | Stilling well | **1½" schedule-40 PVC** (~6" long) + top cap (drilled M10) + a flat foot (bottom cap / slip-flange) | ID ~40 mm clears the ~20 mm float; ¼" inlet holes at the base. See §4. |
| 4 | Grate mount | **2–4× stainless #8 machine screws + washers/nuts** through the grate slots — *or* stainless zip ties/lockwire (no-drill) | Foot fastens to the 10×10" PVC grate's 3/16" slots. See §4. |
| 5 | Cable | **~25 ft direct-burial multiconductor** — 18/4 sprinkler wire, *or* **Cat5e in conduit** (8 conductors, cheap, plenty spare) | Only 2 conductors needed (float dry contact); spares cover any alternate sensor. |
| 6 | Field junction | Small **IP67** potted/gel-filled junction, mounted **above the 6" flood line** | The only splice; float leads run up to it. |
| 7 | Node power | **5 V USB-C supply** | Board runs on USB in the protected building — no field power |
| 8 | Surge protection | ~1 kΩ series resistor + **TVS/clamp diode to 3V3** (or an RC + Schottky clamp) at the GPIO | Outdoor line entering a building is a transient path — see the dead-GPIO-26 lesson in CLAUDE.md |
| 9 | Enclosure | Small project box for the node inside the building | Not weather-rated (indoors) |
| 10 | Misc | PVC primer + cement, O-ring/silicone for the cap pass-through, optional SS mesh over inlet holes | — |

### 2.1 Rough cost (USD, approximate)

Ballpark retail as of the build; buy-what-you-have knocks it down (hookup wire, resistors, a
spare USB brick, leftover PVC are all likely on hand).

| # | Item | Est. price | Notes |
|---|------|-----------:|-------|
| 1 | **Stainless M10 mini float** | **$8–10** | Alternatives (§3) land within ~$5 either way |
| 2 | **Arduino UNO R4 WiFi** (new board) | **$27–35** | Official ~$27.50; the one genuinely fixed cost |
| 3 | Stilling well — 1½" PVC (~6") + two caps + flat foot | **$6–12** | Hardware-store PVC |
| 4 | Grate mount — SS #8 screws/nuts + washers *or* SS zip ties | **$3–6** | Uses the grate's 3/16" slots |
| 5 | Cable — ~25 ft 18/4 direct-burial *or* outdoor Cat5e (+ conduit if used) | **$12–25** | Conduit adds ~$8–15 if you run it |
| 6 | IP67 field junction (gel/potted) | **$8–12** | The one splice |
| 7 | 5 V USB-C supply | **$8–10** | Often already on hand → $0 |
| 8 | Surge protection — 1 kΩ resistor + TVS/clamp diode | **$3–6** | Buy a small assortment pack |
| 9 | Indoor project box | **$8–12** | Or reuse |
| — | Misc — PVC cement/primer, O-ring, SS mesh, hookup wire | **$8–15** | |
| | **Total** | **≈ $90–140** | Reuse of USB brick / wire / PVC lands nearer the low end |

The sensor choice barely moves the total. The **UNO R4 WiFi is the dominant line item**; an ESP32
dev board (~$6–10) would cut it if you're willing to port the firmware off the WiFiS3/RA4M1
scaffolding (not recommended — the savings aren't worth losing the drop-in reuse). Practically,
this is a **~$100 build**, less if the odds and ends are already in your parts bin.

---

## 3. Sensor options & recommendation

All options detect one thing: *water standing at the trip height inside the stilling well.*
Freezing is a non-issue (§1), which widens the field. **The stilling well is the key enabler:**
because the water inside it is debris-free, the sensor doesn't have to survive pine needles and
grit — so the simplest robust detector, a **stainless reed float riding directly in the well**,
is the pick. The rest are documented alternatives if a float ever disappoints.

### 3.1 Stainless vertical mini float (reed) — **locked in**
A stainless magnetic float rides a short M10 stem; a sealed reed closes/opens as the float lifts.
It mounts **through the well's top cap** on its M10 nut, float hanging into the well, and is a
**plain dry contact → `INPUT_PULLUP` GPIO, identical to the DomesticWater meter reed** — zero
firmware porting, no excitation circuit, no power run out to the drain. The one moving part now
rides *clean* water in the well, so the usual fouling knock is gone. The 45 mm mini size suits a
shallow pit; trip height is set by the cap height (§4).
- **NO vs NC is reversible** by flipping the float on the stem. Mount it **NC (closed dry, opens on
  rising water)** so *wet = pin HIGH* — then a cut/disconnected cable also reads HIGH and
  **self-alarms**, rather than failing silent (a genuine safety property for a rarely-triggered
  sensor). Mount NO if you'd rather; firmware handles either (§6).
- Parts: [YXQ 45 mm](https://www.amazon.com/YXQ-Switch-Stainless-Monitor-Vertical/dp/B08HWRMRQR),
  [DEVMO 45 mm](https://www.amazon.com/DEVMO-Indicator-Vertical-Sensor-Stainless/dp/B07T18PGJ4).

### 3.2 Alternatives (documented, not chosen)
All present the same "clean digital wet-at-level signal" the rest of this spec (§5–§10) assumes,
so any of them is a drop-in swap — differing mainly in whether they need power out to the drain.

- **Contact / conductivity electrodes** — a sense rod + reference rod at the trip height; water
  bridging them reads "wet." No moving part; cheapest. Needs pulsed/alternating excitation (or a
  cheap "liquid-level/contact detector" board) to avoid electrode electrolysis. Good, but a bare
  float is simpler to buy and wire.
- **Clamp-on capacitive (through-wall)** — e.g. Gikfun **XKC-Y25-NPN**
  ([B086QX726M](https://www.amazon.com/Gikfun-Non-Contact-Liquid-XKC-Y25-NPN-Arduino/dp/B086QX726M)),
  straps to the *outside* of the well pipe and senses water through the wall. Truly non-contact
  (no corrosion, no fouling), native 5 V logic out. Caveat: needs a **thin** non-metallic wall —
  bench-test it triggers through the actual 1½" pipe before committing; needs 5 V out on the cable.
- **HVAC condensate float switch (inline SS2 type)** — a mechanical float in a clear ¾"-threaded
  housing ([GAGALOR SS2](https://www.amazon.com/GAGALOR-Condensate-Switch-Overflow-Adaptor/dp/B0CNZ3N7ZS));
  threads into a PVC standpipe instead of a condensate line. Dry contact, see-through, has its own
  cleanout. Essentially the §3.1 float with its own chamber — redundant once you have a stilling
  well, but a clean packaged option. *(The solid-state AG-1250E-style condensate sensor is a
  24 VAC switch, not a dry contact — it needs a transformer + opto stage to read from a GPIO, so
  it's a poor fit here despite excellent sensing.)*
- **Optical (infrared prism)** — IR prism tip, dry = reflect / wet = light escapes. No moving
  part, clean digital out, but pricier and a film on the prism can bias it (the well helps).

**Recommendation:** **stainless mini float (§3.1)**, mounted **NC** for the self-alarm property.
If it ever fouls or sticks, the electrodes or the clamp-on capacitive are drop-in replacements
with the same downstream wiring/firmware.

---

## 4. Physical install — stilling well on the drain grate

The well is a **1½" schedule-40 PVC pipe (~6" tall)** with the stainless mini float threaded
through its top cap. It stands **on top of the 10×10" PVC drain grate** (water pools above the
grate when it clogs), fastened to the grate's 3/16" slots.

```
   IP67 junction (the splice) ── zip-tied to a short stake, ABOVE the 6" flood line
        │ sealed run cable → building (~20 ft)
   ┌──┴──┐  top cap: M10 float through it, O-ring sealed
   │  ╤  │
   │  │  │  1½" PVC well, ~5–6" tall (ID ~40 mm clears the ~20 mm float)
   │  ○  │  float bead rides the stem — trip height ≈ (cap height − 45 mm) ≈ 3"
   │~~~~~│  ← trip level ~3"  (well below the 6" overflow lip)
   │ ○○○ │  ¼" inlet holes around the base, as low as possible
   ╞═╤═╤═╡  flat foot (bottom cap / slip-flange) cemented to the well
─────┼─┼──────────  10×10" PVC grate (3/16" slots)
     █ █   ← SS #8 screws through two slots, washer + nut underneath (or SS zip ties)
```

**Pipe & float:**
- **1½" sch-40** (ID ~40 mm) gives the ~20 mm float free travel. Verify the float's OD first (§1).
- Drill a **10 mm hole in the top cap**, thread the float through, snug the M10 nut with an
  **O-ring/silicone** so the wire pass-through stays dry. Mount **NC** (§3.1) for the self-alarm.
- Drill **4–6 ¼" inlet holes around the base**, as low as possible so shallow pooling enters
  immediately. Optional stainless-mesh band over them as a needle guard.
- **Trip height = cap height − ~45 mm.** Cut the well so the float bead lands ~2–4" above the grate
  (well below the 6" overflow). Dry-fit and bucket-test before final assembly — the one dimension
  that matters.

**Grate mount (uses the slots — no drilling the grate):**
- Cement a **flat foot** (a bottom cap or a 1½" slip-flange) to the well so it can't rock.
- **Bolted:** 2–4 **stainless #8 machine screws** (≈4.2 mm, pass a 3/16" slot) through the foot and
  a slot, **washer + nut underneath**. Two hold it; four for dead-rigid.
- **No-drill:** loop 2–3 **stainless zip ties / lockwire** from the foot through adjacent slots and
  cinch — fully removable for cleaning.
- Place the well in the grate corner toward where water actually pools; its ~1.9" footprint on a
  10×10" grate barely affects normal drainage.

**Wire routing / the one height detail:** the stainless float and its O-ring-sealed pass-through
are submersible, so brief shallow flooding (up to 6") doesn't hurt them. The only connection that
must stay dry is the **splice to the run cable** — put it in the **IP67 junction mounted above the
6" flood line** (on a short stake or the adjacent wall). So: float low, splice high — no geometry
fight. Everything downstream of the junction is dry.

---

## 5. Wiring

One detection level → one dry-contact signal to the node, plus GPIO protection. Just **2
conductors** from the float.

```
  Stilling-well float (reed, dry contact, mounted NC — opens on rising water)
     float lead 1 ─── conductor 1 ──[~1kΩ]──▶ D2   (INPUT_PULLUP)
     float lead 2 ─── conductor 2 ───────────▶ GND

  Per input at the node: TVS/clamp diode from D2 to 3V3, series ~1kΩ as above.
  UNO R4 WiFi power ◀── 5 V USB-C supply (in the building)
```
- **`INPUT_PULLUP` + NC float:** the pin idles HIGH via the pull-up. Dry → contact **closed** →
  pin pulled to GND → **LOW**. Water up → contact **opens** → pin floats to pull-up → **HIGH = wet**.
  A cut/disconnected cable also reads HIGH → **self-alarms** instead of failing silent. (Mount NO
  and invert if you prefer; firmware handles either — §6.) Debounce/sustain lives in firmware, so
  ripple and a passing splash don't alert.
- **Surge protection matters here.** A ~20 ft outdoor cable entering a building is a transient/
  static path. Put a **series ~1 kΩ + a clamp diode (TVS to 3V3)** on the sense line. pivac has
  already lost one GPIO (pin 26) to a power-event transient — don't repeat it on an exposed line.
- **Alternate sensors (§3.2):** electrodes add a pulsed drive pin (D4) + `INPUT_PULLDOWN` on D2;
  clamp-on capacitive / optical add **5 V + GND** conductors and drive D2 (`INPUT`) directly. The
  Cat5e spare pairs cover any of these without re-pulling cable.

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

const uint8_t PIN_SENSE = 2;   // reed float, NC + INPUT_PULLUP: dry=LOW (closed), wet=HIGH (open)
const unsigned long SUSTAIN_MS = 45000UL;   // must hold ~45 s before it counts (real clog holds; splash doesn't)
const unsigned long CLEAR_MS   = 15000UL;   // must be dry ~15 s before clearing (hysteresis)

bool clogged = false;
unsigned long wetSince = 0, drySince = 0, cloggedStartMs = 0;

// Return true when water is standing at the trip level.
// NC float (recommended): opens on water → pin HIGH.  (NO float: wet = LOW — flip the compare.)
// Alt sensors (§3.2): electrode = pulse D4 HIGH, read D2 (INPUT_PULLDOWN), idle D4; capacitive/
// optical = a direct digital line on D2 — swap this one line to match the part.
bool readWet() {
  return digitalRead(PIN_SENSE) == HIGH;   // NC float + INPUT_PULLUP
}

// Debounced, sustained latch with hysteresis.
bool sustainedLatch(bool raw) {
  unsigned long now = millis();
  if (raw) { drySince = 0; if (!wetSince) wetSince = now; if (!clogged && now - wetSince >= SUSTAIN_MS) clogged = true; }
  else     { wetSince = 0; if (!drySince) drySince = now; if (clogged && now - drySince >= CLEAR_MS)   clogged = false; }
  return clogged;
}

void setup() {
  pinMode(PIN_SENSE, INPUT_PULLUP);   // alt: electrode → INPUT_PULLDOWN + pinMode(4, OUTPUT)
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
or guard over the grate). *(If you add the optional overflow-lip redundancy sensor from §1, give
it its own `clogged`-style path + rule as an "actually overflowing now" escalation.)*

---

## 9. Failure modes

| Event | Behaviour |
|-------|-----------|
| Splash / wind chop / brief rain surge | `SUSTAIN_MS` latch (~45 s) suppresses it — no alert |
| Real clog | water stands at the trip level → float opens → `clogged` latches → email |
| Cut / disconnected sensor cable | NC float → reads HIGH → **self-alarms** (`clogged`) rather than failing silent |
| Float fouled/stuck by debris | Stilling well keeps needle mats off it; if it ever sticks, swap to electrodes or clamp-on capacitive (§3.2) — one firmware line |
| Deep-winter freeze / ice-lock | **Out of scope** — drain not needed when freezing (§1) |
| WiFi down | Board keeps sensing locally; pivac shows stale → `storm-drain-stale` email |
| Node hung | RA4M1 watchdog resets it; `uptime_ms` reveals the reset |
| Pi/pivac down | Node unaffected; just not published |
| Power-event transient on the outdoor line | Series R + TVS clamp on each input protects the GPIO (the dead-GPIO-26 lesson) |

pivac never actuates anything — this node is monitor-only by construction.

---

## 10. Deployment & test checklist

1. Acquire a **UNO R4 WiFi** + the **stainless M10 mini float** + 1½" PVC (well/caps/foot) +
   grate-mount hardware + burial cable. Verify the float OD fits the 1½" ID (§1).
2. Build the well (§4): drill the cap M10 hole + base inlet holes, cement the foot, mount the
   float **NC**; measure the overflow lip; cut the well so the float trips at ~2–3".
3. Fasten the foot to the grate through the slots (SS screws or zip ties); mount the IP67 junction
   above the 6" line. Wire per §5 (float → D2 + GND, series R + clamp); USB-power the node.
4. Flash the sketch; confirm WiFi join + `GET /` returns the single-quoted dict; bench-test by
   raising the water in the well and watching `clogged` latch after `SUSTAIN_MS`.
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
