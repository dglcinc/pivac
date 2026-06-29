# Domestic Water Node — Build Spec

**Status:** Draft / not yet built — supersedes the retired camera-CV `pivac.WaterMeter`
(Tapo-RTSP + OpenCV) as the domestic main-meter path.
**Goal:** Give `environment.water.domestic.*` a reliable, fully-local live source —
consumption + flow rate + (optional) automatic leak shutoff — feeding Signal K →
InfluxDB → Grafana → WilhelmSK like every other pivac sensor.

This is the **domestic** node. The companion irrigation change (a DAE meter straight
into OpenSprinkler) is summarized in [§9](#9-companion-irrigation-change) but is not part
of this build.

---

## 1. Decisions & open items

**Decided:**
- **Meter:** DAE **MJ-75a** — ¾", multi-jet, **0.1 gal/pulse**, NSF61 lead-free potable,
  2-wire dry-contact reed. (Finest DAE resolution; best for leak detection.)
- **Controller:** the spare **Arduino UNO R4 WiFi** (the third board), reusing the
  existing `pivac.ArduinoSensor` HTTP-JSON pattern.
- **Power:** a single **12 V DC, 1–2 A** adapter feeds both the board (VIN) and the
  valve (via the relay). No second supply.
- **pivac stays read-only.** It only *reads* the node's JSON. All valve control and any
  autonomous shutoff logic live **on the Arduino**, never in pivac.

**Resolved (2026-06-28):**
1. **Valve variant = A — 2-wire reverse-polarity bistable** (David has it in hand). Holds
   position with **zero** holding power, so a commanded shut-off survives a power blink; no
   electronic feedback; needs a **DPDT** relay. Wiring detail in §4.3. *(B = "Normally
   Open" 5-wire and "Normally Closed"/"Auto Return" are documented in §4.4 for reference
   only — not used.)*
2. **Auto-shutoff = monitor-first.** The sketch ships with autonomous shutoff **disabled**;
   the valve moves only on a manual `GET /valve/*`. Enable later once a Grafana baseline
   exists.
3. **Board confirmed = UNO R4 WiFi** (the spare third board; WiFiS3 HTTP). Sketch reuses
   the `ArduinoPSI_*` WiFi/watchdog scaffolding.

---

## 2. Bill of materials

| # | Item | Spec / model | Notes |
|---|------|--------------|-------|
| 1 | Domestic meter | **DAE MJ-75a**, ¾" multi-jet, 0.1 gal/pulse, NSF61 | Reed, 2-wire, no power |
| 2 | Shutoff valve | **U.S. Solid ¾" SS304 full-port, 9–24 V DC**, *2-wire reverse polarity* (`B06XWG6ZLS`) | Variant B: "Normally Open" 5-wire instead |
| 3 | Controller | **Arduino UNO R4 WiFi** (the repurposed spare) | WiFiS3, HTTP server |
| 4 | Relay | **DPDT relay module**, coil 5 V, contacts ≥ 2 A @ 12 V, opto-isolated | Variant B: 1-channel SPST |
| 5 | Power | **12 V DC adapter, 1–2 A** (≈12–24 W) | Powers board + valve |
| 6 | Plumbing | 2× ¾" unions, lead-free fittings, PTFE/thread sealant | Serviceable install |
| 7 | Manual valve | ¾" manual ball valve **upstream** | Likely the existing main shutoff — keep it |
| 8 | Enclosure | IP-rated box near the meter | Damp location |
| 9 | Misc | 2-conductor cable (meter), hookup wire, RC snubber, resistors | See wiring |

Potable note: MJ-75a is NSF61; U.S. Solid SS304 is NSF/ANSI 61; use **lead-free** fittings.

---

## 3. Architecture & data flow

```
                ┌───────────────────── domestic node (at the water main) ─────────────────────┐
  city → iPerl → DAE MJ-75a (0.1 gal/pulse) ─reed─▶ UNO R4 WiFi ──relay──▶ U.S. Solid valve ─▶ house
  utility meter      consumption metering         (pulse count,           (whole-house shutoff)
  (untouched)                                       flow calc,
                                                     valve ctrl,
                                                     HTTP/JSON)
                └──────────────────────────────────────┬───────────────────────────────────────┘
                                                        │  WiFi, HTTP GET /  (single-quoted dict)
                                                        ▼
                              Pi: pivac.ArduinoSensor poll → Signal K deltas
                                                        ▼
                              InfluxDB → Grafana (Domestic Water row) → WilhelmSK
                                                        ▼
                              Grafana alerting → graph-bridge → email (leak/anomaly)
```

Plumbing order: **existing manual valve → DAE meter → motorized valve → house**, so the
meter records all house flow and the motorized valve cuts the whole house downstream.
Install the meter with its arrow in flow direction and a few pipe-diameters of straight
run up/downstream (AWWA), with unions for service.

---

## 4. Wiring

### 4.1 Power — how 12 V reaches the board *and* the valve (single rail, two branches)

One 12 V DC adapter (1–2 A, center-positive barrel is typical) feeds everything. Cut the
barrel off (or use a screw-terminal barrel-jack adapter) to expose **+12 V** and **GND**,
then split each into a small bus:

```
                      ┌─────────────────── +12 V bus ───────────────────┐
                      │                                                  │
 12 V DC adapter (+) ─┤                                                  │
                      ├─▶ UNO R4 WiFi  VIN  pin   (board's onboard reg makes 5 V/3.3 V;
                      │                            R4 VIN spec = 6–24 V, so raw 12 V is fine)
                      └─▶ relay contact side (the cross-wired +12 V / GND that the
                          DPDT relay swaps onto the two valve motor leads — see §4.3)

                      ┌─────────────────── GND bus (common) ────────────┐
 12 V DC adapter (−) ─┼─▶ UNO R4 WiFi  GND pin                          │  ← ALL grounds
                      ├─▶ relay module GND                              │     must be common
                      └─▶ relay contact side (the GND half of the cross-wire)
```

**The 12 V never touches an Arduino signal pin.** The board takes 12 V only on **VIN**
(it regulates its own logic rails). The valve's motor current (a few hundred mA for the
~3–5 s of travel, then ~0 once it hits its limit switch) flows **only** through the relay
**contacts** from the +12 V/GND bus to the motor leads — never through a GPIO or the 5 V
regulator. The relay **coil/opto** is the only thing the Arduino drives, and it's powered
from the board's **5 V** pin (see §4.3), not from the 12 V rail.

A 12 V / 1–2 A adapter covers the board (~0.1–0.2 A) plus valve travel comfortably. Use
≥ 20 AWG for the 12 V motor run; keep it short. **Common ground is mandatory** — the
Arduino, the relay module, and the 12 V adapter's negative must all tie together, or the
relay opto won't switch reliably.

### 4.2 Meter (reed pulse)

| Meter wire | To | Notes |
|------------|----|-------|
| Reed lead 1 | **D2** (interrupt) | `pinMode(INPUT_PULLUP)` |
| Reed lead 2 | **GND** | — |

Dry contact, no polarity. With `INPUT_PULLUP` the pin idles HIGH and pulses LOW on each
0.1-gal reed closure (~0.16 mA through the reed — well under its 10 mA / 24 V limit).
Software debounce (§5) handles contact bounce.

### 4.3 Valve — Variant A (reverse-polarity bistable, DPDT) — **chosen**

The valve has **two** motor leads and changes position by **polarity**: +/− on the leads
drives it one way (OPEN), −/+ drives it the other (CLOSE). It self-stops at an internal
limit switch at each end (current drops to ~0), and being **bistable it holds position
with zero power** — so a power loss leaves it wherever it was. A **DPDT** relay is what
flips that polarity from a single GPIO.

**Why DPDT:** to reverse polarity you must swap *both* leads at once. A DPDT relay is two
SPDT switches that throw together — one pole handles each motor lead. Wire the contacts
**crossed**:

| Motor lead | Relay pole | Contact at REST (de-energized) | Contact when ENERGIZED |
|------------|-----------|-------------------------------|------------------------|
| Motor **A** → **COM1** | pole 1 | **NC1 = GND**  → A sees **−** | **NO1 = +12 V** → A sees **+** |
| Motor **B** → **COM2** | pole 2 | **NC2 = +12 V** → B sees **+** | **NO2 = GND**  → B sees **−** |
| Result | | **A=−, B=+ → OPEN polarity** | **A=+, B=− → CLOSE polarity** |

So: relay **de-energized = OPEN** (fail-safe — the supply line stays open on power/board
loss), relay **energized = CLOSE**.

```
                 DPDT relay (or two ganged SPDT channels, coils both on D7)
   +12 V ───┬──────────────● NO1                ● NC2 ●───────┬─── +12 V
            │               \                  /              │
            │                ●COM1── Motor A ──┤              │
            │                                  COM2── Motor B │
            │                ●NC1               ●NO2          │
   GND ─────┴──────────────────┘                  └──────────┴─── GND
   (NC1=GND, NO1=+12)                         (NC2=+12, NO2=GND)   ← crossed
```

**If you have a 2-channel SPDT relay module** (the common blue boards) instead of a single
8-pin DPDT part: use **both** channels as the two poles and **tie both IN pins to D7** so
they throw together. Wire channel 1 as the COM1/NO1/NC1 row above, channel 2 as the
COM2/NO2/NC2 row. The motor leads go to the two **COM** screw terminals.

**Relay coil power & logic level:** power the module's **VCC/JD-VCC from the Arduino 5 V**
pin, GND common, and drive **IN from D7**. These cheap modules are usually **active-LOW**
(coil energizes when IN is pulled LOW) — the sketch defaults to that
(`#define RELAY_ACTIVE_HIGH 0`), so at boot D7 idles HIGH → coil de-energized → **OPEN**
polarity → fail-open. If your module is active-HIGH, flip that one `#define`. Verify once
with a meter before connecting the valve.

| Signal | Pin | Behaviour (active-LOW module) |
|--------|-----|-------------------------------|
| Relay coil (direction) | **D7** | HIGH = de-energized = OPEN · LOW = energized = CLOSE |

The firmware **persists the commanded position to EEPROM** and re-asserts it in `setup()`,
so a watchdog reset re-drives the valve to its last commanded state rather than blindly
reopening (§5, §10). *(Optional standby-current elimination: add a 2nd relay on **D8** in
series with the 12 V and pulse it only during the ~5 s actuation — not required, since the
valve idles at ~0 power at its limit switch.)*

### 4.4 Valve — Variant B (Normally-Open 5-wire) *(not used — kept for reference)*

| Signal | Pin | Behaviour |
|--------|-----|-----------|
| Relay coil (close power) | **D7** | OFF = valve open (default) · ON = powered → closes |
| Open feedback | **D4** | from valve's "open" indicator wire |
| Closed feedback | **D5** | from valve's "closed" indicator wire |

Feedback wires may sit at 12 V — read them through a **divider** (e.g. 10 k/15 k → ~5 V)
or an optocoupler into the 5 V pins, **not** raw. Share ground.

### 4.5 Protection
- **RC snubber** across the valve motor leads (or the relay contacts) for inductive
  back-EMF — e.g. 0.1 µF film cap in series with ~100 Ω, rated ≥ 100 V.
- Keep meter signal wiring away from the 12 V motor run; twisted pair if long.

---

## 5. Arduino firmware

> **Built:** the full sketch is `~/github/Arduino/DomesticWater/DomesticWater.ino`
> (Arduino repo branch `feat/domestic-water-node`). It compiles clean for
> `arduino:renesas_uno:unor4wifi` (30 % flash, 29 % RAM). The skeleton below is the
> illustrative reference; the shipped sketch differs in three ways worth noting:
> (1) the **relay defaults to active-LOW** (`#define RELAY_ACTIVE_HIGH 0`) so D7 idling
> HIGH at boot = de-energized = **OPEN** (fail-open) — flip the define for an active-HIGH
> module; (2) it **persists the commanded valve state** to EEPROM (with a magic marker)
> and re-asserts it in `setup()`, so a watchdog reset re-drives the last position instead
> of reopening; (3) it adds a `GET /reset?confirm=1` totalizer-reset endpoint. Autonomous
> shutoff is present only as a commented stub (monitor-first).

Reuse the WiFi/HTTP scaffolding from the existing `ArduinoPSI_*` sketches in
`~/github/Arduino` (WiFiS3, `WiFiServer` on port 80, RA4M1 watchdog, escalating reconnect
with `NVIC_SystemReset()` fallback). The node adds: pulse counting, an EEPROM totalizer,
flow calc, valve control, and the JSON endpoint.

**Output format — critical:** `pivac.ArduinoSensor` parses the response with
`ast.literal_eval` on the first line matching `.*\{.*\}`, so the dict must use
**single quotes** (Python literal, *not* JSON). Matches the existing pressure sketches.

```cpp
// domestic-water-node.ino — UNO R4 WiFi
// Meter: DAE MJ-75a, 0.1 gal/pulse (reed on D2). Valve: U.S. Solid (relay on D7).
#include <WiFiS3.h>
#include <EEPROM.h>

const float K_GAL_PER_PULSE = 0.1f;     // DAE MJ-75a (factory; multi-jet ±1.5%)
const uint8_t PIN_PULSE = 2;            // reed, INPUT_PULLUP, FALLING
const uint8_t PIN_VALVE = 7;            // DPDT direction (A) / close-power (B)
const unsigned long DEBOUNCE_US = 3000; // reed bounce guard (max rate ~2 Hz)
const unsigned long EEPROM_SAVE_MS = 300000UL; // persist totalizer every 5 min
const int EEPROM_ADDR = 0;

volatile uint32_t pulseCount = 0;       // since boot (ISR)
volatile unsigned long lastPulseUs = 0;
uint32_t totalPulses = 0;               // persisted lifetime total
uint32_t lastSavedTotal = 0;
unsigned long lastSaveMs = 0;

// flow window
uint32_t windowStartPulses = 0;
unsigned long windowStartMs = 0;
float flowRateGpm = 0.0f;

int valveCommanded = 1;                 // 1 = open (default), 0 = closed

void onPulse() {
  unsigned long now = micros();
  if (now - lastPulseUs < DEBOUNCE_US) return;   // debounce
  lastPulseUs = now;
  pulseCount++;
}

void saveTotal() {
  EEPROM.put(EEPROM_ADDR, totalPulses);
  lastSavedTotal = totalPulses;
  lastSaveMs = millis();
}

void valveOpen()  { /* A: */ digitalWrite(PIN_VALVE, LOW);  /* B: LOW=open(default) */ valveCommanded = 1; }
void valveClose() { /* A: */ digitalWrite(PIN_VALVE, HIGH); /* B: HIGH=powered closed */ valveCommanded = 0; }

void setup() {
  pinMode(PIN_PULSE, INPUT_PULLUP);
  pinMode(PIN_VALVE, OUTPUT);
  EEPROM.get(EEPROM_ADDR, totalPulses);          // restore lifetime total
  if (totalPulses == 0xFFFFFFFF) totalPulses = 0; // fresh EEPROM
  valveOpen();
  attachInterrupt(digitalPinToInterrupt(PIN_PULSE), onPulse, FALLING);
  // ... WiFi connect + watchdog (copy from ArduinoPSI sketch) ...
  windowStartMs = millis();
}

void loop() {
  // --- fold ISR count into lifetime total ---
  noInterrupts();
  uint32_t pc = pulseCount; pulseCount = 0;
  interrupts();
  totalPulses += pc;

  // --- flow rate over a rolling ~10 s window ---
  unsigned long nowMs = millis();
  if (nowMs - windowStartMs >= 10000UL) {
    uint32_t dp = totalPulses - windowStartPulses;
    float minutes = (nowMs - windowStartMs) / 60000.0f;
    flowRateGpm = (dp * K_GAL_PER_PULSE) / minutes;
    windowStartPulses = totalPulses;
    windowStartMs = nowMs;
  }

  // --- persist totalizer on a timer (EEPROM wear: ~5 min, not per-pulse) ---
  if (totalPulses != lastSavedTotal && nowMs - lastSaveMs >= EEPROM_SAVE_MS) saveTotal();

  // --- OPTIONAL autonomous leak shutoff (disabled until monitor-first phase done) ---
  // if (AUTOSHUTOFF && flowRateGpm > HIGH_GPM for > N min) valveClose();

  // --- HTTP: GET / → status dict; GET /valve/open|/valve/close → manual control ---
  // server.handle();  // see scaffolding. Status line MUST be single-quoted:
  //   {'flow' : 2.50, 'volume' : 12345.6, 'flowing' : 1, 'valve' : 1}
  // where volume = totalPulses * K_GAL_PER_PULSE, flowing = (flowRateGpm > 0.0)
}
```

### 5.1 HTTP endpoints
| Method / path | Purpose | Called by |
|---------------|---------|-----------|
| `GET /` | status dict (below) | **pivac** (read-only) |
| `GET /valve/close` | manual close | human / dashboard only |
| `GET /valve/open` | manual open | human / dashboard only |
| `GET /reset?confirm=1` | reset totalizer | manual only (rare) |

### 5.2 Status dict (single-quoted)
```
{'flow' : 2.50, 'volume' : 12345.6, 'flowing' : 1, 'valve' : 1}
```
- `flow` — gal/min (rolling window)
- `volume` — cumulative gallons (`totalPulses × 0.1`)
- `flowing` — `1` if `flow > 0` else `0`
- `valve` — `1` = open, `0` = closed (commanded; for Variant B, derive from feedback)

### 5.3 Notes
- **EEPROM wear:** ~100 k write endurance — persist on a timer (5 min) / on valve events,
  never per pulse. Consider a small wear-leveling ring if you want sub-minute durability.
- **Watchdog:** keep the RA4M1 watchdog + reconnect logic from the pressure sketches.
- **WiFi creds** are hardcoded in the existing sketches (known issue, see the Arduino repo
  CLAUDE.md) — match that pattern or externalize; don't commit creds.

---

## 6. pivac integration

No module changes needed — the generic `pivac.ArduinoSensor` maps each response field to
`{sk_path}.{outname}`. Add to `/etc/pivac/config.yml`:

```yaml
pivac.DomesticWater:
    description: Domestic main water meter (DAE MJ-75a) + shutoff valve via Arduino
    module: pivac.ArduinoSensor
    enabled: true
    ipaddr: 10.0.0.XX          # DHCP-reserve in UniFi by the board's WiFi MAC
    daemon_sleep: 15
    inputs:
        flow:
            sk_path: environment.water.domestic
            outname: flowRate          # → environment.water.domestic.flowRate (gal/min)
        volume:
            sk_path: environment.water.domestic
            outname: consumption       # → environment.water.domestic.consumption (gal, cumulative)
        flowing:
            sk_path: environment.water.domestic
            outname: flowing           # → environment.water.domestic.flowing (0/1)
        valve:
            sk_path: environment.water.domestic
            outname: shutoffValve      # → environment.water.domestic.shutoffValve (1=open)
```

Then a dedicated systemd unit `pivac-domestic-water.service` (clone an existing
`pivac-arduino-*.service`, set the module/args), install, enable, and add it to the
restart/stop lists in CLAUDE.md's deployment + SD-maintenance sections.

### 6.1 Signal K paths
| Path | Unit | Notes |
|------|------|-------|
| `environment.water.domestic.flowRate` | gal/min | rolling window |
| `environment.water.domestic.consumption` | gal | cumulative totalizer |
| `environment.water.domestic.flowing` | 0/1 | derived |
| `environment.water.domestic.shutoffValve` | 0/1 | 1 = open |

> The old camera-CV domestic data was deleted from InfluxDB; this path has had no live
> source since. First good data from this node re-seeds it. If you ever reset measurements,
> restart Signal K afterward (the influxdb2 plugin caches field types — same gotcha as Sentry).

---

## 7. Calibration

The MJ-75a is a **factory-calibrated multi-jet meter at exactly 0.1 gal/pulse, ±1.5%** —
so unlike the GREDIA, the K-factor is *known* and set in the sketch (`K_GAL_PER_PULSE =
0.1`). No fudge factor. Optional sanity check: read the mechanical register, draw a known
volume (e.g. fill a measured container), confirm `volume` deltas match within ~1–2 %.

---

## 8. Leak detection & auto-shutoff

Two independent layers; **start monitor-only**, add shutoff after a baseline:

1. **Alerting (in Grafana, like the rest of the system):** add rules on
   `environment.water.domestic.*` routed to the existing `graph-bridge` → email contact
   point. Candidate signals: continuous `flowing == 1` for > N hours (slow leak / running
   fixture), `flowRate` above a household-peak threshold sustained for > M minutes (burst),
   and a "consumption climbed overnight while nothing should run" check. This directly
   addresses the unexplained ~600–1000 gal overnight swings noted in prior sessions.
2. **Autonomous shutoff (on the Arduino, opt-in):** if enabled, the sketch closes the
   valve on a sustained high-flow/continuous-flow rule. **Keep it off until the Grafana
   baseline is understood** to avoid false shut-offs.

Safety: the valve logic is on the Arduino, not pivac (read-only). The **manual upstream
valve** is the human override (the U.S. Solid valve has no manual lever).

---

## 9. Companion irrigation change

Out of scope for the node build, but part of the same effort: replace the oversized GREDIA
on OpenSprinkler with the **DAE AS200U-75P** (¾", single-jet, **1 gal/pulse**) wired to OS
**SN1 + GND**, then set **`fpr = 1.00`** both on the OpenSprinkler device *and* in
`pivac.Sprinkler` config — and **drop the `fpr: 0.0025` override**. With an exact 1 gal/pulse
meter the OS app and Grafana finally agree and the contaminated-calibration saga ends.

---

## 10. Failure modes & power-loss behaviour

| Event | Variant A (reverse polarity) | Variant B (NO 5-wire) |
|-------|------------------------------|------------------------|
| Power loss, valve open | **stays open** | **stays open** |
| Power loss, valve closed (mid-shutoff) | **stays closed** | **reopens** (no hold power) |
| Arduino hung | watchdog resets; valve unchanged | watchdog resets; valve unchanged |
| WiFi down | board keeps metering + local shutoff; pivac shows stale (Grafana freshness alert) | same |
| Pi/pivac down | node unaffected; just not published | same |

pivac **never** commands the valve. The upstream manual valve is the ultimate override.

---

## 11. Deployment & test checklist

1. Plumb meter + valve (water off), unions + manual valve upstream, meter arrow correct.
2. Wire per §4; verify common ground; snubber in place.
3. Flash sketch; confirm WiFi join + `GET /` returns the single-quoted dict.
4. Bench/known-volume test: pulses → `volume` tracks; `flow` reads during draw.
5. Valve test: `GET /valve/close` then `/valve/open`; confirm physical travel (and feedback
   on Variant B); confirm **power-loss leaves it open** (pull power while open).
6. DHCP-reserve the board IP in UniFi by MAC; set it in config.
7. Add config block + `pivac-domestic-water.service`; `daemon-reload`; enable; start.
8. Confirm `environment.water.domestic.*` flowing into Signal K, then InfluxDB/Grafana.
9. Add Grafana alert rules (monitor-only). Defer autonomous shutoff.
10. Update CLAUDE.md: Active Services table, Current Modules, deployment restart/stop lists,
    Known Operational Behaviours.

---

## 12. References

- DAE MJ-75a (0.1 gal/pulse): <https://daecontrol.com/product/dae-mj-75a-lead-free-potable-water-meter-3-4-npt-couplings-pulse-output-gallon/>
- DAE AS200U-75P (1 gal/pulse, irrigation): <https://daecontrol.com/product/dae-as200u-75p/>
- U.S. Solid ¾" SS reverse-polarity valve (B06XWG6ZLS): <https://www.amazon.com/Motorized-Stainless-Polarity-U-S-Solid/dp/B06XWG6ZLS>
- U.S. Solid — power-loss behaviour ("only auto-return models return to closed; all others hold position")
- pivac `ArduinoSensor` contract: `pivac/ArduinoSensor.py`; config example: `config/config.yml.sample` (`pivac.ArduinoPSI`)
- Retired camera path it replaces: `docs/water-meter-camera-monitoring-plan.md`, `docs/water-meter-camera-hardware-options.md`
</content>
</invoke>
