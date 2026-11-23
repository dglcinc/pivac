<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
<!-- Copyright David Lewis -->

# Chiltrix CX75 — Modbus link, register map and operating notes

Evidence and history behind the Chiltrix rules in `CLAUDE.md`. Parameter tuning is in `chiltrix-cycling-tuning-plan.md`; the alert rules and the evidence behind the retired ones are in `grafana-alerting-notes.md`.

## Chiltrix CX75 Modbus is LIVE — `A3`/`B3`, and the whole register map is confirmed against the unit (2026-08-26)

the connection is **`A3` and `B3`, A/B only, with no ground, no bias resistors and no terminator at the Arduino**, per Chiltrix's own `cx34-123&cx50-2&cx35-1 Modbus User Document.docx` (in `~/OneDrive - DGLC/Claude/HVAC Manuals/`), whose figures show the Modbus port on the right-hand side of the board with **green = A and white = B**. Serial settings are **Modbus RTU, 9600 / none / 8 / 1, slave ID `1`, function 03**; the chiller is a **slave**, so an external master may poll on demand. **The chiller biases the pair itself — 3.18 V measured across `A3`/`B3` with nothing connected — so external fail-safe bias is not merely unnecessary, it would fight the chiller's own network.** The `DA1`/`DA2` pair on `P6` is not the route: it never returned a byte at any baud or slave ID, and its 0.44 V idle solves to a ~130 Ω terminator at the far end, which is what distinguishes it electrically from the live pair. The right-hand terminal block is four separate connectors, top to bottom:

| Connector | Terminals (top→bottom) | Use |
|---|---|---|
| `P7` | `A1a` `A1b` `GND` | parallel tap of the A1 controller bus — empty here |
| `P6` | `DA1` `DA2` `GND` | dead end; never answered |
| **`P5`** | **`B3` `A3`** | **the working Modbus port** |
| `P4` | `B2` `A2` `B1` `A1` `GND` `+12V` | wired controller + sensor buses |

On the sibling CX35-1/CX50-2 board these are one 8-position connector reading `+12V GND A1 B1 A2 B2 A3 B3`, plus a separate `0V DA2 DA1`. **A `GND` terminal sits two positions from `A3`/`B3`** — that is the isolated-ground landing point if an isolated transceiver is ever fitted.

**⚠️ A FLOATING CABLE SHIELD costs two thirds of your frames, and only while the compressor runs.** Measured on the same cable in one evening: with the drain ungrounded at both ends, **0.0% loss at idle and 65.3% at 55 Hz**; grounding the drain **at the Arduino end alone**, **0.0% across 635 reads at up to 55 Hz**. A shield does nothing unless it is grounded at one end, and 50 ft of pair sharing a tray with an inverter has no defence without it. One end only — bonding both ends puts the chiller-to-Pi ground difference onto the shield running alongside the signal pair. **The lesson generalises: link quality measured at idle is meaningless, because nothing radiates with the drive off.**

**⚠️ Diagnose with the failure code, not the symptom.** `ChiltrixScan`'s `watch` prints **`TMO`** (timeout — nothing arrived), **`CRC`**, or the exception code, because a timeout and a corrupted reply point at opposite causes. In the broken configuration 83% of failures were `TMO` but **17% were `CRC`/`E0`/`E1`, which is what proved bytes were arriving corrupted** rather than the chiller being silent. ModbusMaster validates slave id and function *before* CRC, so corruption surfaces as any of the three.

**⚠️ `SW1` on the main board is the COMPRESSOR MODEL ENCODE — do not touch it looking for Modbus settings.** CX65 IOM p61: `C38 Compressor model Encode (By Main board dialing SW1`. It has nothing to do with the BMS port, address, or termination, and changing it tells the controller it has different hardware. Read **`C38`** on the panel to see the encoded value. (`P88` "Model selection" and `P99` "Compressor manufacturer" are related software-side settings; also leave alone.) As found: **1 off, 2 on, 3 off, 4 on.**

**There is NO Modbus parameter on the CX** — the full `P00`–`P119` table was read and contains no address, baud, Node-ID, or comms-enable setting. The port cannot be "switched off", and the Node-ID is not settable from the panel.

**⚠️ Use Chiltrix's register map, never the community ones.** It **agrees with gonzojive (CX34) on all six addresses they share and contradicts jasipsw (CX50-2) on all seven**, so a jasipsw address is a guess. Every row below is confirmed against the physical unit:

| Reg | Meaning | Scale | Access |
|---|---|---|---|
| 140 | Switch on/off | 0 off, 1 on | R/W |
| 141 | Operating mode | 0 cool, 1 heat, 2 DHW, 3 cool+DHW, 4 heat+DHW | R/W |
| 142 | AC cooling target | **whole °C** | R/W |
| 143 | AC heating target | whole °C | R/W |
| 144 | Hot water target | whole °C | R/W |
| 145 / 146 | AC heating / hot water AU mode | 0 disable, 1 enable | R/W |
| 202 | Ambient air temp | ÷10 → °C | read |
| 205 | Outlet water temp — **water returning FROM the chiller** to the house | ÷10 → °C | read |
| 281 | Inlet water temp — **water going TO the chiller**, the return from the house | ÷10 → °C | read |
| 213 | Water flow | **÷10 → L/min** | read |
| 227 | Compressor frequency | Hz, 0–80 (raw) | read |
| 256 | Input AC current | **÷10 → A** | read |

**Both scales the document leaves unstated are `÷10`, and both were measured rather than inferred.** Flow: register 213 read raw **69** while the panel showed **1.8 gpm** → 6.9 L/min = 1.82 gpm. Current: register 256 read **109** at 55 Hz while `electrical.emporia.house.chiltrix` read **2660.5 W** → 10.9 A × 240 V = 2616 W, within 1.7%. **Raw would have published flow 10× high, which silently makes a strainer-fouling alarm unfireable** — 505 clears any threshold set against a 20 L/min `P65` trip.

**How the map was confirmed, and the trap in confirming it.** 142 read 10, matching the 50 °F panel target; 202 read 23.9 °C against RedLink's outdoor sensor at 23.89 °C, which also refutes jasipsw's claim that 202 is inlet water; 281 and 205 tracked the controller's own inlet and outlet displays to within 0.4 °F; and 227 and 256 both fell to 0 together when the compressor stopped while inlet and outlet converged with the pump still running. **⚠️ Compare temperatures at idle, never during a transient** — the outlet moved 4.7 → 9.8 °C in the three minutes after a stop, which made one comparison look like a 3 °F calibration error when it was drift. **Inlet is the return from the house and runs warmer than outlet in cooling**, so `281 − 205` is positive; negative means the addresses are swapped or the unit is heating.

**Use the controller's own words: `inlet` is the water going TO the chiller and `outlet` is the water returning FROM it.** That is what the panel displays, and it matches the register names. Do not relabel these as "return" and "supply" — those are correct from the *house's* point of view and invert the sense, which is how a plotted pair ends up backwards.

**⚠️ The chiller modulates BOTH the pump and the compressor off inlet water temperature (register 281).** So water flow is a *controlled output*, not an independent measurement, and any fouling rule built on flow is measuring a control loop unless something pins the pump. This is the mechanism behind the pump trimming already noted above, and it is why `flow ÷ Hz` failed: both terms are outputs of the same controller responding to the same input.

**The chiller restarts on its own hysteresis, about 2 °C above target** — 12 °C against the 10 °C setpoint — not on a zone call. Inlet climbing past the setpoint without a start means the band has not been reached yet.

**⚠️ Neither raw flow NOR flow ÷ Hz is a usable fouling signal (measured 2026-08-27).** A fixed threshold near 35 L/min false-fires at part load on a clean strainer. The ratio does not rescue it: **at a constant 55 Hz the flow ranged 42.5–52.9 L/min, a 20% spread, giving flow ÷ Hz of 0.773–0.962.** The compressor speed was pinned and the flow moved anyway, so the quantity is not load-independent. Over those 53 samples flow correlates **+0.96 with outlet water temperature and −0.96 with ΔT**: from 20:43:34 to 20:44:00 on 26 Aug, Hz held at 55 while outlet fell 6.7 → 6.1 °C, flow fell 45.9 → 42.5 and ΔT widened 4.6 → 4.9 °C. **The controller trims pump speed to hold an evaporator ΔT** (`P53` sets the floor at 40%), with glycol viscosity rising as the water cools pushing the same way. **The narrow 0.96–1.03 band was an artefact of reading only the ramp-down segment**, where Hz and flow happened to fall together; read the ramp-*up* and the ratio reaches **3.78**, because at 14–35 Hz the pump is already at full 52.9 L/min while the compressor spools.

**⚠️ `281` against `142` ALSO fails, and so does end-of-cycle inlet (measured 2026-08-28).** The 6 h rolling mean of inlet sat at **48.6–49.9 °F across both a clean period and a live flow decline** — a 1.3 °F spread with no separation — because the idle rise between cycles dominates it and the restart hysteresis bounds that regardless of restriction. End-of-cycle inlet fails for a related reason: through a 354-minute run the unit still reached its **44.6 °F stop point**, the same value as every clean cycle. It took 354 minutes instead of 11, so **run duration separates where inlet temperature does not**.

**The one flow measurement that IS comparable is the startup plateau.** Across eight clean starts the flow holds a flat **52.9 L/min from ~70 s before the compressor engages until ~140 s into the run**, spanning the whole power ramp, then trims down. That window is ~3.5 minutes wide and is bracketed by an obvious cue — from when power starts climbing until a little after it levels off. **Deep idle is a 2–5 L/min sensing trickle and useless as a reference**; the pump is barely turning to keep water past the sensor. `pivac.ChiltrixModbus` publishes this as `.startupFlow`.

**⚠️ But the plateau does NOT prove a fixed pump speed, and that question is open.** The CX pump is under controller command at all times, and **the controller modulates both the pump and the compressor off inlet water temperature (`281`)** — so flow is a *controlled output*, not an independent measurement, and any fouling rule built on it may be measuring the control loop. **Two attempts to break the tie both failed on instrument resolution and should not be repeated:** register `256` quantizes to 0.1 A (24 W) against a 22–200 W pump-alone draw, and Emporia's 60 s poll cannot isolate a ~70 s window inside a longer compressor-off period. Registers **248** (pinned at 100) and **260** (tracks flow, sits near the `P53` 40% floor) are the candidate pump speeds — read them, or clean the strainer and watch whether flow recovers.

**The chiller was commissioned 2026-08-04, which sets the fouling clock.** The loop temperature history is the record: `environment.inside.hvac.OUT.temperature` ran 38.9–44.3 °F to 13 July, sat at **82–84 °F from 14 July to 3 August** with no cooling source at all during the changeover, then came down on 4 August. So the **first strainer blockage took 18 days** (to 2026-08-22). Any claimed re-fouling much faster than that is suspect, because a freshly commissioned loop carries the most mobile debris and should foul *fastest*.

**⚠️ Drop `TMO` rows before any state-machine analysis of the log.** Parsing a timeout as `0` makes `hz or 0` read as compressor-off, which split one 354-minute run into three and manufactured three fake "degraded cycles". The register value is absent, not zero.

**Register `284` is the controller's fault/lockout register, caught with a known cause on 2026-09-03.** It read **32** for sixteen consecutive minutes (16:19–16:34 EDT) and **0 for every other sample of the surrounding eight days**, ~8,400 of them. The cause is known rather than inferred: David left an isolation valve closed for a couple of minutes during a glycol top-up. The sequence reads cleanly — inlet reached the 54.7 °F restart band, the controller commanded the pump to 100 % (`248` 10 → 100), flow read 54.0 for one cycle and **0.0** the next, `284` went to 32, the controller commanded the pump to 0, and the unit sat locked for sixteen minutes while the loop coasted to 62.2 °F before releasing itself and restarting to 60 Hz and 14.6 A. `243` and `244` stayed 0 and 2 throughout, so neither is the fault word. **`284` = 2 is P1 high pressure protection**, matched against the panel's error log on 2026-10-20 (see P1 in heating below). Treat any value other than 2 and 32 as new information. The register shows a fault only while it is active, and a P1 that clears inside one poll never reaches it: the full scan every ~70 s missed 6 of the 18 P1s logged to 2026-10-26. Since 2026-10-26 17:49 EDT the module reads 227 and 284 every ~6 s between full scans (now every ~76 s), and publishes `faultCode`, which holds a non-zero 284 for 60 s so a fault seen by one read still fills a minute bucket; count P1s as rises of `faultCode` to 2 and check the count against the panel log.

**⚠️ The `P5` reading rests on the mechanism alone and was never confirmed against a panel code.** The controller's error log read empty when checked on 2026-09-06; it had been cleared. What supports `P5` is the sequence itself plus the CX65 IOM p70, which names insufficient flow **and air in the lines** as the two `P5` triggers — and a glycol fill introduces air, so an open valve does not rule out an air lock. **The next occurrence is the chance to confirm it**: touch **ERROR** on the controller home screen (IOM p55), find the row by timestamp (the log lists TIME / DATE / ERROR), and record it before pressing anything. **"Error Reset" clears the fault; "Clear" wipes the history.** Codes worth recognising (IOM p63): `P5` indoor unit water flow error, `P1` high pressure, `P2` low pressure, `E14` system anti freeze twice, `E17` **AC** system anti freeze twice.

**The consequence generalises: the Modbus record is the only durable evidence of a chiller fault here.** No register latches a code, the panel log is a few rows deep, and a Clear erases it. **That is a stronger argument for publishing unidentified registers under raw paths** than the original one — not merely that the identifying moment cannot be recaptured, but that the panel's own record cannot be relied on to still be there.

**Sketches live in `~/github/Arduino`** (`ChiltrixModbus`, `ChiltrixScan`, `RS485Blast`), on branch `feat/chiltrix-modbus`, PR dglcinc/Arduino#10. All are **read-only — function 03, never 6 or 16** — even though 140–146 are writable and include the cooling target and the on/off switch. Modbus RTU needs **≥3.5 character times of silence between frames** (~4 ms at 9600); `readOne()` owns that gap, and without it roughly 40% of back-to-back transactions time out.

**The Arduino runs on the Pi's USB**, `/dev/ttyACM0`, serial `E8F60AA93AA8`, vendor 2341. `vcgencmd get_throttled` stays `0x0` with it attached, so the Pi's USB budget carries an UNO R4 plus RS-485 shield comfortably. **⚠️ A charge-only USB cable is the failure to check first** — the board powers up and its LEDs light, but `cdc_acm` never loads and nothing appears on the bus. **`chiltrix-logger.service` is RETIRED — stopped and disabled 2026-08-28, superseded by `pivac.ChiltrixModbus`.** Its TSV at `~/chiltrix/chiltrix_log.tsv` stays on disk as history (26–28 Aug, 6 columns) and `python3 ~/chiltrix/tally_log.py [since]` still reads it. **The serial port is exclusive**, so the two cannot both run — `pivac-chiltrix.service` declares `Conflicts=chiltrix-logger.service`. Everything the logger captured now lands in InfluxDB under `hvac.chiller.chiltrix.*` at full width. **⚠️ ANSWERING PROVES NOTHING ON THIS UNIT — every address 0–359 answers function 03 with no gaps** (scanned 2026-08-29, and 359 is only where the scan stopped). So a response is not evidence an address is meaningful, and an earlier note reading "45 registers answered" as a finding about the chiller was wrong: 45 was simply what the module asked for. **`registerCount` is a link-health signal, not a property of the device.** Meaning comes only from Chiltrix's document plus value cross-checks.

**184 addresses are published: the confirmed set plus the whole `P00`–`P139` settings block, and since 2026-09-16 addresses 215–217 as the `C16` defrost and `C17` freeze-protection candidates (Chiltrix support named both readouts; `C13` sits at 213, so 200 + n is the hypothesis the first defrost tests).** A setting changed on the panel is exactly what later explains a behaviour change, and nothing else records one. The CX65 IOM's table runs to **`P119`**, so 0–139 covers it with margin. **Raw paths keep the bare address (`raw.r<addr>`) deliberately** — the data model does not assert the parameter mapping, though it is now verified (below).

**The address = parameter-number mapping is VERIFIED (2026-08-30), checked value-by-value against the full `P00`–`P119` table in `cx65-1-iom.pdf` pp. 56–60.** Of the 105 parameters the manual lists, **85 registers read exactly the manual's default** (counting the known deliberate change `109`=1). The clincher is the gap alignment: **the 15 addresses in 0–119 with no manual entry are exactly the P-numbers the manual skips** (13, 14, 16, 20–22, 29, 44, 46, 70, 89–93) — the register space has values everywhere, and the manual's numbering holes line up one-for-one. The 20 mismatches are all in-range and read as CX75 factory tuning against a CX65 manual: `88`=6 vs default 4 (`P88` is model selection — a different model *should* differ), the EEV block (`76`/`77`/`96`/`102`), max-temp caps (`72`=50, `73`=49), pressure trims (`87`, `106`, `107`), defrost trims (`37`, `45`). **Two caveats.** Enum-coded parameters can use a different internal encoding than the panel shows — `2` reads 1 against `P02`'s documented 5/6 for 50/60 Hz, and `104` reads 0 (°C) while the panel displays °F — so trust numeric matches, not raw enum values. And **`65` still reads 14 against the manual's cx65/cx75 `P65` of 20**; it fits the factory-tuning pattern but confirm on the panel before treating any flow number as near or far from the `P5` trip. **The `52`=0 "contradiction" is resolved: it was a conflation.** `P52` governs the *pump*, and register 0 = "not stop" is consistent with what the unit does — the pump never stops, it idles down to the 2–7 L/min sensing trickle. What stops at target is the *compressor*, governed by the `P12` hysteresis band (register `12`=2 °C, matching the observed restarts at 54.0/54.2 °F against the 50 °F target), not by `P52`.

**The `P114`–`P119` DHC tail is inert here.** `P114` max humidity 50, `P115` max temp 27, `P116` default target water temp 12, `P117` max allowed target return water 20, `P118` min allowed target 10, `P119` DHC enable **0**. The manual states that with DHC disabled none of `P114`–`P118` apply — worth knowing because `P118` = 10 °C read carelessly says the minimum settable target is 50 °F, which would contradict `P109`'s range and mislead anyone re-reading the E14 lockout history.

**⚠️ Opening the port does NOT reset an UNO R4, and that breaks the naive logger sequence.** The board's uptime counter survives repeated host connects (measured across 19.7 h), so a previous session can leave the sketch still in `watch`. A running watch consumes **exactly one character** to stop, so a client that opens and immediately writes `w 281 205 …` has its leading `w` eaten as the stop character and the remainder discarded as junk — the board then sits silent at its prompt. `chiltrix-logger` did this and **ran `active` for 18 hours having written zero rows**, with nothing in its journal, because its read loop had no timeout. `logger.py` now **quiesces the board to its prompt first** (nudge with a newline, wait for the stream to go quiet, drain, then send the command) and **raises if no row arrives in 60 s** so the outer loop reopens. Backup at `~/chiltrix/logger.py.bak-20260827`. Any future serial client to this sketch needs the same two properties.

**An isolated transceiver is optional, not required.** `EVAL-ADM2587EARDZ` (~$62, Arduino-shield form factor) would give 25 kV/µs common-mode immunity and a floating bus-side ground (`GND2`, pins 16/20) to land on the chiller's `GND` — worth it only if losses ever return under heavier load than the 55 Hz tested. The ADM2587E's receiver is also fail-safe by design (inputs open → `RxD` high), which is a second reason no external bias belongs on this bus.

## Chiltrix CX75 antifreeze lockout (E14) — keep the return-water target at 50 °F / 10 °C (2026-08-21)

dropping the target to 46 °F locked the chiller out overnight with **E14 "System anti freeze level one twice"**, and **the controller's "Error reset" button did NOT clear it — recovery needed a breaker power cycle** (off ~1 min; expect a few minutes before the compressor restarts on its own minimum-off timer; "Clear" only wipes the error log, which is worth keeping as evidence). Two causes compound. **`P59` "AC anti-freezing temperature" defaults to 3 °C = 37.4 °F and watches *leaving* water**, while the unit runs roughly a 9 °F evaporator ΔT *below* its *return* target — so the lowest safe return target is about **49 °F**. And **the controller stores the target in whole °C**, so a Fahrenheit entry lands lower than typed: 50 °F = 10 °C exactly (leaving 41.0 °F, 3.6 °F margin), **48 °F = 8 °C = 46.4 °F (leaving 37.4 °F — exactly on the trip)**, 46 °F = 7 °C = 44.6 °F (leaving 35.6 °F — below it). **Set it in whole °C and read the stored value back.** To run colder the order is **glycol → `P59` (with margin above the fluid's freeze point) → target**; **`P109` only opens the range** (now set to `1`, allowing 41–77 °F) and is *not* the limit. `P53` (internal pump minimum speed, 40 %) is the other lever — it lets the evaporator ΔT widen at low demand, which is exactly when this tripped. **⚠️ Measured 2026-08-29→09-06, the margin at the 50 °F target is zero, not 2.2 °F:** forty running minutes came in at or below 38.5 °F leaving water and the minimum reached **exactly 37.40 °F** on 09-02 15:36, with 37.58 on three other occasions. All sit at the end of a run at full flow (49–52 L/min), and since `P95` = 3 (2026-08-30) every one is a surge-terminated run: the compressor jumps from its 25 Hz floor to 47–60 Hz in the last one to three minutes and stops (18 of 358 runs through 09-13, outlet minima 37.2–39.0 °F, against 40.4 °F for the rest). The steady floor at 25 Hz is 40.3–40.6 °F, 3 °F above the trip; the `P95` change raised it from 36.7–38.2 °F. A level-one trip needs to happen twice for E14, so these are near misses — but **widening `P12` at this target would push them under, which is why the target raise has to come first** (`docs/chiltrix-cycling-tuning-plan.md` §2). **Adding glycol does not help here**: `P59` trips on a fixed 3 °C leaving-water temperature and knows nothing about concentration, so the 2026-09-03 top-up lowered the real freeze point and left the E14 exposure unchanged. **If E14 ever recurs at a 50 °F target the setpoint is no longer the explanation** — check water flow, charge, and the leaving-water sensor. **Flow is the first thing to check, because it was already a factor once**: the Y-strainer was clogged during this trial (see the strainer note below), and low flow widens the evaporator ΔT onto the `P59` trip, so the restriction likely contributed to the lockout rather than the 46 °F target accounting for it alone. Full analysis, the CX parameter table and the measured one-day trial are in `docs/unico-cooling-assessment-and-tuning.md`.

## Chiltrix CX75 P5 "indoor unit water flow error" is the LOW-FLOW alarm, and the Y-strainer is the first suspect (root-caused + fixed 2026-08-22)

repeated P5 alarms that reset and re-tripped within the hour. **`P5` fires when measured water flow falls below `P65` "AC minimum water flow" = 20 L/min on cx65/cx75**; `P64` sets the sensing type (factory `1` = flow meter) and **`C13` on the panel is the live flow readout**. "Indoor unit" is a misnomer inherited from split-system firmware — on a monobloc it is the water side of the plate exchanger, the circuit the CX's own pump drives. The same manual calls the identical quantity "usage side water flow volume" (`C13`) and "AC minimum water flow" (`P65`). **Cause was a heavily clogged Y-strainer**, loaded with calcium-looking scale that migrates from the boiler side of the shared four-pipe loop. **After cleaning, `C13` read over 54 L/min against the 20 L/min trip.** **Signature in the data:** chiller runtime collapsed to **169 min against 626–1,012 min on each of the previous ten days** (mean run 15.4 min vs 22–72), the loop warmed from ~45 °F to **77 °F**, and only the chiller's zones drifted — MASTER_BR went 76 → 79 °F while KITCHEN and GREAT_ROOM held, because those two are DX in cooling. **What rules out the alternatives:** loop pressure stayed **21–23 psi** (no water lost), and the unit still made cold water when it ran, pulling the tank down 8.1 °F in five minutes (~29,500 BTU/hr net) — capacity was normal and the *protection* was stopping it. **Why the margin is thin here:** removing ~30,000 BTU/hr at Chiltrix's 9 °F design ΔT needs ~25 L/min against a 20 L/min trip, so losing a fifth of the flow crosses it at full output while part load keeps running. An isolated early P5 followed later by a cluster is a **fouling curve** — that history is what points at the strainer rather than at air. **⚠️ `C13` reads 0 at idle and that is normal** — the CX's pump does not run continuously (standby is 9–11 W, controls only). Every start goes **9 W → 22–200 W for 1–2 min (pump alone) → 1,000–2,600 W (compressor)**, and that pump-only window is when to read `C13`. Setting **`P52 = 0`** ("not stop", the factory value; this unit is stopping at target) would make `C13` continuously readable and keep debris in suspension between cycles. **Follow-ups:** re-check the screen in days, not months; the right permanent filtration is a **hydronic dirt separator** with a blowdown valve (a *finer* in-line filter clogs faster than the Y did) — dirt-only, since the loop already has an air separator. **And do NOT raise the autofill to recover pressure: on a glycol system keep the feed valve closed.** An autofill feeds plain water, carrying the dissolved calcium and oxygen that caused this, diluting the glycol silently, and masking leaks. Top up **manually with premixed glycol** to **20 psi cold** on the 18 psi precharge (it has touched 27.1 psi, so headroom to a 30 psi relief is thin), then vent.

## The Y-strainer fouls from the boiler side, and low flow presents as `P5` — check `C13`, not the chiller (2026-08-22)

repeated **`P5` "indoor unit water flow error"** traced to the shared four-pipe loop's Y-strainer, **heavily clogged with calcium-looking scale migrating from the boiler side**. `P65` sets the low-flow trip at **20 L/min** on a CX65/CX75, `P64` selects the flow meter, and **`C13` is the live readout** — over **54 L/min** after cleaning. **`C13` reads 0 at idle and that is normal**; the pump only runs during a call, so read it in the **1–2 minute pump-only window at the start of a run**. That check costs nothing and catches the next restriction long before `P5` does, which matters because the scale keeps arriving from a shared loop. **The failure signature in InfluxDB** on 22 Aug: the chiller ran 5, 10, 0 and 6 minutes across 10:00–14:00 EDT while `IN` climbed 58.6 → 76.0 °F. **The quieter signature is more useful** — a restricted chiller sits *above* its own return-water target all afternoon, which is what happened for at least the ten days before cleaning (return water 52.4–54.4 °F against a 50 °F target, running power averaging 1593 W; post-clean 51.9 °F on 1423 W at a *warmer* outdoor average). **Consequence: any capacity or comfort analysis using data before 2026-08-22 is measuring a flow-restricted plant**, including the "loop runs 6–8 °F warmer than the UniChillers" finding — see `docs/unico-cooling-assessment-and-tuning.md` §6.4. **Do not raise the autofill to recover pressure** on a glycol system: it carries in the calcium and oxygen that caused this, dilutes the glycol silently, and hides leaks. Top up manually with premixed glycol to 20 psi cold.


## The Y-strainer screen is 60 mesh and re-fouls slowly (measured 2026-09-12)

The CX65 and CX50-2 IOMs require a 60 mesh or finer screen (0.25 mm opening) ahead of the plate exchanger, and the ACOL DN32 strainer's stock screen meets it. Measured from two macro photos of the basket against a millimetre tape (`IMG_1784.HEIC` and `IMG_1785.HEIC`, 2026-09-12 21:14, in `~/Downloads` on the Mac Mini), with the tape wrapped around the basket so that the tape's ticks and the mesh sit at the same radius and share the same foreshortening. On the second photo the millimetre ticks are 76–91 px apart across the curve; in the same rows the wire cloth's circumferential pitch is 31–33 px and its axial pitch 35.9 px, so the pitch is 0.38–0.44 mm, 23–26 wires per cm, 58–65 per inch. A peak count gave two or three wire rows in every 1 mm tick interval, and the wire occupies about 40 % of the pitch, so the wire is about 0.16 mm and the opening about 0.24 mm. Standard 60 mesh stainless cloth is 0.16–0.19 mm wire on a 0.42 mm pitch with a 0.23–0.26 mm opening. The screen is a plain-weave stainless cloth backed on the outside by an expanded-metal sleeve; the basket is 43.44 mm OD, 39 mm ID and 72.14 mm long.

The re-fouling rate has collapsed. Inspected at about 21:00 on 2026-09-12, 21 days after the 2026-08-22 cleaning, the screen was no more than about 5 % covered, against a heavy blockage that took `C13` under the 20 L/min trip inside the first 18 days after commissioning. The first fill carried the mobile scale from the boiler side of the shared loop; a strainer that catches 5 % in three weeks after catching a full load in the first three is clearing the loop's residue with no new material arriving. `.startupFlow` held a daily mean of 51.9–52.9 L/min on every day from 2026-08-31 to 2026-09-12, which is the flow-side confirmation. The dirt separator remains the right permanent answer if the rate ever climbs again, but nothing in this inspection calls for it now.

## Measured cooling performance, 2026-08-29 → 09-12

Water-side, from the chiller's own inlet, outlet and flow registers with glycol taken at 0.98 of
water's heat capacity, and electricity from `electrical.emporia.house.chiltrix`; treat every figure
as ±10 %. Over the fifteen days the unit drew 271 kWh and delivered 379 ton-hours, a COP of 4.9
including standby. Running only, by ambient:

| Ambient | Running COP | Capacity | Input |
|---|---|---|---|
| below 60 °F | 7.4 | 35 kBTU/h | 1.39 kW |
| 65–70 °F | 6.7 | 33 | 1.43 |
| 75–80 °F | 6.0 | 31 | 1.50 |
| above 80 °F | 5.5 | 30 | 1.62 |

Peak output is 51 kBTU/h at 55–60 Hz from 2.7 kW. Daily electricity fits 0.82 kWh per °F of mean
outdoor temperature above 48 °F (r = 0.70), so a 70 °F day costs 18 kWh, about $3.25 at 18 ¢, and a
75 °F day 22 kWh. Idle draw is 10 W with the pump trickling at 5.7–6.9 L/min.

The first heating run, 2026-09-08 20:49, gives one datapoint for the other direction: 14 minutes at
55–60 Hz and 0.45 kWh took the tank from 51 to 77.5 °F return and 86 °F supply, about 85 kBTU/h from
3.2 kW (COP near 7.5) at 70 °F ambient with a 60–74 °F return, the easiest conditions it will see.
Cooling back from 77.7 to 44.6 °F took 36 minutes and 1.13 kWh with zones calling throughout.

A mains interruption produces a heating blip: on 2026-09-13 three brief outages each showed as
under a minute of `operatingMode` = 1 with `HPHEAT` energised and the outlet jumping to 56–61 °F, and
the pair at 13:02 and 13:09 cost a 52-minute cool-back run starting from 57.7 °F. No thermostat
carried a heat state, so read a sub-minute mode flip against the Pi's `journalctl --list-boots`
before suspecting the HZ-432's `B` terminal.

## Measured heating performance, 2026-09-15 → 09-27

Same method as the cooling figures: water side from registers 213, 281 and 205 with glycol at 0.98
of water's heat capacity, electricity from `electrical.emporia.house.chiltrix`, every figure ±10 %.
The heating target over this period was 50 °C, so steady running held a 120 °F return and a 128 °F supply. Steady
means heating mode, compressor running and return above 110 °F: 568 minutes in all.

| Chiller ambient | Minutes | Input | Output | COP |
|---|---|---|---|---|
| 45–50 °F | 98 | 4.55 kW | 53 kBTU/h | 3.4 |
| 50–55 °F | 344 | 4.41 kW | 55 kBTU/h | 3.7 |
| 55–60 °F | 171 | 3.89 kW | 54 kBTU/h | 4.1 |

Across all 568 minutes the COP is 3.6 at a median 50 Hz. The three bands differ by less than the
error of the method, so read them as one figure near 3.6 that improves with ambient. Warming a
cold tank runs far better: with the return under 95 °F the unit delivers 68 kBTU/h from 3.0 kW, a
COP of 6.8. Over the six days from 09-22 the unit drew 70.4 kWh in heating mode, idle included, and
delivered 1,010 kBTU, a COP of 4.2; that figure is lifted by the warm-up minutes of 35 changeovers
and a plant that holds one mode will sit nearer 3.6.

Peak draw in heating is 6.9 kW and 26.9 A from register 256, reached at 65–68 Hz with the return
above 116 °F, against 3.7 kW in cooling. The Emporia reading and the register agree at 254 V.
Idle draw in heating mode is 10 W with the pump at 8.0 L/min. Heat runs are short at this load:
55 runs in the six days, median 13 minutes, about 10 starts a day. No defrost occurred; the lowest
ambient in the record is 48 °F, so the COP below 45 °F is unmeasured.

## P1 high pressure trips at the end of heating runs (panel log 09-27 → 10-20)

The panel's error log on 2026-10-20 held 13 × P1 high pressure protection and one P4 over current
protection. The panel clock runs 2–3 minutes behind EDT; every entry was matched against the
Modbus record.

| Panel time | Code | Condition |
|---|---|---|
| 09-27 10:13 | P1 | End of run |
| 10-06 23:32 | P1 | End of run |
| 10-10 04:58 | P1 | End of run |
| 10-10 06:26 | P1 | End of run |
| 10-11 09:38 | P1 | End of run |
| 10-11 11:21 | P1 | End of run |
| 10-12 00:28 | P1 | End of run |
| 10-12 07:07 | P1 | End of run |
| 10-17 06:02 | P1 | End of run |
| 10-17 23:51 | P1 | Defrost, 39 °F |
| 10-18 05:58 | P4 | Defrost entry, 36 °F |
| 10-18 22:08 | P1 | End of run |
| 10-20 07:58 | P1 | End of run |
| 10-20 08:28 | P1 | End of run, latched |

1. End of run: the tank at or past the 50 °C target, return 122–127 °F, leaving 129–134 °F, the
   compressor at 33–41 Hz and the pump trimmed to 63–74 %, 37–42 L/min. The compressor stops, the
   pump drops to 10 %, and the unit restarts normally on its next call.
2. Defrost, 10-17 23:51: the compressor surged to 72 Hz at 22 A, then leaving water fell below
   return (104 against 111 °F), the reverse cycle of a defrost. 10-18 05:58: 46 to 68 Hz at
   24.8 A at the same transition. These were the first defrosts on record.
3. 10-20 08:28 latched: the only pair of P1s within 30 minutes. `284` held 2 from 08:30 to 09:42,
   the compressor never restarted while the return fell from 126 to 98 °F, and the pump ran at its
   `P53` minimum of 40 % (`248` = 40, 23–24 L/min). A breaker power cycle cleared it. Chiltrix
   support (2026-10-20): after a P1 the unit restarts on its own shortly after, a couple of P1s
   in a row put it in full lockout, and a power cycle is usually needed to clear it. Support gave
   no window; the pairs 88 and 103 minutes apart cleared on their own.

**Water temperature alone does not predict a P1.** Over the 329 heating stops since 09-27, the 12
matched P1 stops ended at a median 125 °F return and 132 °F leaving; the 317 ordinary stops ended
at 127 °F and 134 °F. About 4 % of heating runs end in P1 under the same water conditions, so at
the 50 °C target every run ends near the high-pressure cutout. Startup flow held 54–55 L/min
throughout, the loop held 22–25 psi, and the trips follow the number of heating runs, so nothing
points at a worsening fault.

**Settings since 2026-10-20 12:23 EDT, on Chiltrix support's advice (Devon Powell, Hotspot
Energy, 10-20):** P1 comes when return water nears 130 °F, and P1 and P4 can come in pairs at
defrost; one or two on a cold night are no concern.

| Setting | Meaning | Before | Now |
|---|---|---|---|
| Heating target | Register 143 | 50 °C | 46 °C |
| P38 | Coil temperature that ends defrost | 30 °C | 15 °C |
| P39 | Air-to-coil difference that starts defrost | 8 °C | 12 °C |
| P53 | Pump minimum speed | 40 % | 50 % |

1. Heating target: 48 °C from 10-20 12:22 EDT, entered as 119 °F (the controller truncates a °F
   entry to whole °C, so 118 °F would store as 47 °C), and 46 °C since 10-29 12:58 EDT, entered in
   °C and read back from register 143 (319.15 K). The second step followed the 10-29 lockout below.
2. P38 and P39: later and shorter defrosts. Inspect the outdoor coil after the first freezing
   rain or snowy night for frost left behind.
3. P53: the pump floor in every mode. A lockout now idles the pump at about 30 L/min, and in
   cooling the higher floor narrows the evaporator ΔT at low load, which adds margin to `P59`.
4. Judge the change by the P1 count in the panel log and by `chiltrix-fault-latched`; go back up a
   degree if a room falls 1 °F below setpoint overnight.

**Panel log since the change** (cleared 2026-10-20, last read 2026-10-26; the panel clock runs 2–3
minutes behind EDT):

| Panel time | Code | Condition |
|---|---|---|
| 10-21 01:12 | P1 | End of run, 50 °F: 37 Hz, return 120 °F, leaving 127 °F |
| 10-21 23:41 | P1 | End of run, 49 °F: 37 Hz, return 120 °F, leaving 127 °F |
| 10-24 07:27 | P4 | End of a 25 min run, 38 °F: 43–53 Hz at 15–18.7 A on the minute samples; compressor off two minutes, restarted 07:32, 75 Hz at 26 A at 07:37 (the highest frequency on record), stopped at target 07:39 with the return at 125 °F |
| 10-24 22:37 | P1 | End of run, 44 °F: 40 Hz, return 122 °F, leaving 129 °F; `284` read 2 |
| 10-26 04:50 | P1 | End of run, 43 °F: 40 Hz, return 120 °F, leaving 127 °F; `284` read 2 |
| 10-26 06:38 | P1 | End of run, 43 °F: 40 Hz, return 122 °F, leaving 129 °F; `284` missed it; restarted 06:46 |

Five P1s in 144 heating starts from 10-20 12:23 to 10-26 08:10 EDT (3.5 %), against 12 in 329
heating stops at 50 °C (3.6 %), so the 48 °C target moved the trip water down with it and left the
rate unchanged. Every one came at the end of a run at 37–40 Hz, with the return at 120–122 °F and the
leaving water at 127–129 °F: the P1 belongs to the end of a run, whatever the target. The 10-26
04:50 and 06:38 pair, 108 minutes apart, cleared on its own like the pairs 88 and 103 minutes apart
at 50 °C; only the 30-minute pair of 10-20 latched. `284` caught three of the five at its 70 s
cadence, so the panel log is the count. The P4 stood alone, cleared itself in two minutes, and
never showed in `284`, so `chiltrix-fault-latched` had nothing to see and the panel log is the only
record of a P4. Both P4s on record came on a defrost-range morning (36 °F on 10-18, 38 °F on 10-24, the
coldest hour since the change).

**The 2026-10-29 lockout and the high-side pressure.** Two P1s on consecutive heating runs, at 07:15:02
and 07:36:41 EDT, latched `284` at 2 until a breaker cycle at 07:58; the unit restarted at 07:59. Both
ended a run at 36 Hz with flow trimmed to 39–41 L/min, return 121–123 °F and leaving 129–131 °F, at
50 °F outdoors. Over all heating stops since 09-27, counted from the panel log to 10-26 and from
`284` at its 6 s cadence after:

| Period | Heating stops | P1 | Rate |
|---|---|---|---|
| 50 °C, 09-27 to 10-20 | 334 | 14 | 4.2 % |
| 48 °C, 10-20 to 10-26 17:49 | 146 | 5 | 3.4 % |
| 48 °C, 10-26 17:49 to 10-29 | 50 | 7 | 14 % |

The rise began within hours of the fast fault poll going live (10-26 17:49), in similar weather and
with no setting changed; whether the poll has any part in it is untested.

Registers 210 and 215 behave as the high-side pressure in kPa and its saturation temperature in
tenths of a °C: both correlate 0.89 with leaving water and barely with compressor Hz, 210 runs a
median 3,339 kPa while heating, peaks at 4,244 kPa at a P1, and rises 44.5 kPa per °F of leaving
water. Neither identity is confirmed against a panel readout. Read that way:

1. The plate exchanger is not fouling. At 125–130 °F leaving water and 33–42 Hz the daily median of
   210 held 3,350–3,470 kPa on every day from 09-27 to 10-29.
2. A P1 is a sudden rise, not the end of a slow one. In 12 of 15 cleanly sampled P1 stops, 210
   jumped 350–650 kPa in the last minute (medians 3,682 to 3,984 kPa) while the compressor held
   36–38 Hz, flow held 38–42 L/min with the pump at 67–73 %, and leaving water was flat or falling.
   One of 297 ordinary stops shows such a jump; those stop while still ramping down from 55 Hz, with
   210 rising gradually to a median 3,608 kPa and leaving water higher than at the P1s (133 against
   128.5 °F).
3. The jump points at the refrigerant side, likely the expansion valve on the low-Hz plateau near
   target. Water-side settings only lower the baseline it starts from: 46 °C takes about 160 kPa
   off it, which keeps a median jump under the trip; `P53` at 75 % would hold about 3 L/min more
   at the end of a run and take about 30 kPa, so it stays at 50 %.

Devon Powell had this data on 10-29 with five questions: the identities of 210 and 215 and the P1
cutout pressure, the cause of the jump and any EEV setting to change (`P76`, `P77`, `P96` and `P102`
differ from the CX65 defaults), a better fix than the target, whether reading two registers every
6 s could affect the controller, and a setting that recovers from a P1 lockout without a power cycle. He agreed to 46 °C as a stopgap and is
checking the Modbus analysis with Chiltrix.
At 46 °C the rate was 8.1 % (10 P1s in 123 heating stops to 2026-11-03), with lockouts on 11-02 and
11-03. With the poll slowed to a full scan every ~72 s from 2026-11-03 04:54 to 2026-11-06 14:37 EST,
the panel logged no P1 in 50 heating stops; those days ran 50 °F minimum and 63 °F mean outdoors,
against 40 and 55 °F in the 46 °C week before, so the weather confounds the test.

Matt Dail, Chiltrix's engineer, answered on 2026-11-06 that polling cannot disturb the controller (he
reads all 286 registers within 2 s on his own units and still sees faults he induces) and that the
controller answers a read of every register at once, though he uses blocks of 50. He asked for the
raw registers 0–146 and 200–286 at 1 s. Since 2026-11-06 14:39 EST the module sweeps all 234 in five
block reads of up to 50 about once a second, sending a value to Signal K only when it changes and
every value every 30 s. For the next lockout, export every `raw.r*` and named register from an
hour before the first P1 to the restart, reverse the named conversions to raw integers (tempK:
`(K − 273.15) × 10`; whole-°C targets: `K − 273.15`; flow and current: × 10), and forward-fill to the
sweeps that `registerCount` marks. Before 2026-11-06 the logger never read 200, 201, 218–224,
228–242, 249–255, 262, 263, 265–280 or 286. The raw export of the four earlier lockouts sent to him
is OneDrive `Claude/cx75-p1-raw-registers.zip`.

The 2026-10-20 lockout fired only `chiltrix-pump-only-flow-low`, because the module took the
40 % pump of the lockout as a start plateau (50 % since P53 changed). The module now takes an idle-side plateau only at a
pump command of 90 % or more, and `chiltrix-fault-latched` fires when `284` holds non-zero for six
minutes.

## The pump-start pressure step needs 21.5 psi cold (measured 2026-09-19 → 09-27)
## The pump-start pressure step needs the loop above the tank's precharge (measured 2026-09-19 → 09-27)

The step in `electrical.ac.arduinoThermPSI.psi` at pump start depends on the pressure the loop
holds before the start, at the same 52–54 L/min startup flow:

| Pressure before the start | Starts | Median step | Range |
|---|---|---|---|
| 21.5–26 psi | 52 | −0.9 psi | −0.0 to −1.9 |
| 21.0–21.5 psi | 28 | −2.9 psi | −0.3 to −6.3 |
| under 21.0 psi | 40 | −5.2 psi | −2.7 to −7.5 |

The change is abrupt. Every start up to 20:48 on 2026-09-21 stepped −0.6 to −1.9 psi from 21.3 to
21.7 psi; the start at 21:13, from 20.7 psi, stepped −4.4 psi, and every cold start since has
stepped −4.4 to −7.5 psi, taking the gauge to 12.5–14 psi. A start from a hot tank at 24.9 psi on
2026-09-22 stepped −0.9 psi between two cold starts that stepped −5.3 and −4.6 psi, and
`.startupFlow` held 52.2–54.4 L/min throughout, so the strainer and exchanger are clear and the
step is a property of the loop's pressure. The behaviour fits an expansion tank precharged near
21 psi: below the precharge the tank holds no water, the loop has no compliance, and the pump's
suction pulls the gauge down by the whole friction loss. A gauge on the tank's air valve, with the
loop side at zero, confirms or refutes it.

Cold idle pressure (compressor off, tank under 60 °F) was 23.5–23.7 psi until 2026-09-18, 21.5–21.7
psi after the demineralisation filter went in on 09-19, and 20.1–20.7 psi from 09-22.

Heating raises the loop 5 to 6.6 psi above its cold pressure: from 23.6 psi cold the gauge reached
30.2 psi on 2026-09-15 and 29.1 psi on 09-16 with the tank at 129 °F, at the 30 psi relief, and
from 20.5 psi cold it reaches 25.0–25.7 psi. The cold fill must therefore sit about 1.5 psi above
the precharge and low enough that a 129 °F tank stays under the relief, and the pump-step fouling
sentinel is valid only for starts from 1.5 psi above the precharge.

## The expansion tank is let down to 18 psi and the loop holds 20 psi cold (2026-10-12)

After the 2026-10-10 refill on a 21 psi precharge, six heat-to-cool changeovers on 10-11 raised the
hot pressure to 25–27.5 psi, and on 10-12 the loop sat at 23.0–23.6 psi cold with the tank at 49 °F,
0.36–0.46 gal in the bladder. With the 0.9 gal of expansion a cold-to-hot season swing brings, that
fluid would heat to about 30 psi. At 18:20 EDT, with the tank at 49 °F and the pump idle, the tank's
air valve read 22.7 psi against the loop's 23.0 psi, so the bladder was taking water. Air was let out
with the tank open to the loop until the gauge read 20 psi, and the autofill regulator was turned
down until it no longer fed at 20 psi. No fluid moved, so the bladder still holds about 0.36 gal cold
and the gas charge corresponds to a precharge of about 18.2 psi.

| | 21 psi precharge, 23 psi cold | 18 psi precharge, 20 psi cold |
|---|---|---|
| Room in the tank, cold to 27 psi | 0.5 gal | 1.1 gal |
| Hot peak with 0.9 gal of expansion | about 30 psi | about 25.8 psi |

The equipment sets the band. The Trinity Ti-200 needs at least 15 psi at the boiler outlet, and its pressure switch inhibits firing below 10 psi (Trinity Ti100-200 Installation and Operation Manual, version 2015-05-12, in `HVAC Documentation/Equipment Manuals` on OneDrive; the 30 psi relief and 60 psi gauge are its standard trim). The CX65-1 IOM, the nearest manual to the CX75, gives 14.5 psi minimum, 43.5 psi maximum and 20–30 psi ideal. The relief opens at 30 psi. A 20 psi cold fill rising to 26 psi hot keeps 5 psi above both minimums at a cold pump start and 4 psi under the relief when hot, so there is no gain in going lower. The first heating night held 24.5–26.3 psi with the tank at 124–132 °F, and the pump-start dips were 1.5–2 psi.

The pump-step sentinel's floor moves with the precharge to 19.5 psi. The pump-start dips through the
cold afternoon of 10-12 reached 17.5–18.5 psi from 23.5 psi; they were dips, not the regulator's
setting, which is unknown on its own gauge. `docs/hydronic-pressure-reset-checklist.md` is the
procedure.

## Operating rules in full

`.claude/rules/chiltrix.md` carries the short form of each rule below; this is the full text with its measurements.

- **The return-water target is 12 °C / 53.6 °F, set 2026-09-14 17:00 EDT as change 2 of `docs/chiltrix-cycling-tuning-plan.md` (10 °C before; `P12` widens to 3 next).** `P59` antifreeze trips at 3 °C on *leaving* water and the evaporator ΔT runs ~9 °F below the *return* target, so 49 °F is the floor. The controller stores whole °C, so set it in °C and read it back (48 °F becomes 8 °C, leaving water on the trip). E14 needs a breaker power cycle; the panel's Error reset does not clear it. To run colder: glycol → `P59` → target; `P109` only opens the range. If E14 recurs at 50 °F, check flow, charge and the leaving-water sensor, flow first. **The margin at 10 °C is zero at the end of a run and 3 °F in steady running**: every near miss since `P95` = 3 is a surge-terminated run (25 Hz to 47–60 Hz in the last one to three minutes, then stop; 5 % of runs, outlet 37.2–39.0 °F, 37.22 °F on 2026-09-08 with register 284 unmoved), while the 25 Hz floor holds 40.3–40.6 °F, so raising the target must precede any widening of `P12`. The start ramp is also fixed at 50–52 Hz by minute 3 whatever the load, which is why night runs are 11 min with 36 min gaps. Measured cooling COP is 4.9 all-in and 5.5–7.4 running (`docs/chiltrix-modbus.md`). Adding glycol does not help: `P59` trips on a fixed temperature and knows nothing about concentration. A full drain and refill follows `docs/hydronic-drain-and-refill.md`: pre-mix the whole charge in a drum (25 gal of 75 % premix gives 25 % in the loop's 75 gal; the checklist is `docs/hydronic-drain-and-refill-checklist.md`), fill and purge with a portable pump throttled against the boiler gauge (a dead-headed 65836 makes 52 psi against the 30 psi relief), and record the new glycol reading because it moves the `startupFlow` baseline. **Last drained and refilled 2026-10-10, finished 21:30 EDT**: 25 % PG by refractometer on 2026-10-11 (it read just over 25 % while still mixing) and again on 2026-10-13, pH 8–9 by test paper on 2026-10-13 (NTI allows 7.5–9.5, Alfa Laval's exchanger 9.0 at most), from 25 gal of 75 % premix, expansion tank precharged to 21 psi at the refill and let down to about 18 psi on 2026-10-12, `.startupFlow` 54–55 L/min on the following starts (52.9–56.3 in the week before). The glycol balance puts the loop at about 75 gal (`docs/hydronic-drain-and-refill.md` §1); 55 gal came out by draining.
- **`P5` is the low-flow alarm (`P65` trip, 20 L/min) and the Y-strainer is the first suspect**, fouled by scale from the boiler side of the shared loop. `C13` is the live flow readout; it reads 0 at idle because the pump only runs on a call, so read it in the 1–2 min pump-only window at the start of a run (54 L/min after cleaning). The failure signature is a chiller that runs a few minutes at a time while the loop warms, and, more quietly, sits above its own return target all afternoon. **The loop is filled to 20 psi cold on an expansion tank precharged to about 18 psi (since 2026-10-12)**: the tank's air was let down with the tank open to the loop until the gauge read 20 psi at a 49 °F tank, from 23 psi on a 21 psi precharge, so the bladder holds about 0.36 gal cold and the tank has about 1.1 gal of room before 27 psi, against 0.5 gal before. At the old 21 psi precharge heating added 5 to 6.6 psi and took the loop from 23.6 psi cold to the relief at 30.2 psi on 2026-09-15. Keep the cold pressure 1.5–2 psi above the precharge: below the precharge the bladder is empty, the pump-start step triples and the gauge falls 5–7 psi at every start. The autofill regulator sits below 20 psi (its own gauge is uncalibrated; it did not feed at 20 psi), so it feeds only on a leak; it must never be set at or above the cold fill, or it feeds water at every pump-start dip. Never raise it on this glycol loop; top up manually with premixed glycol. `docs/hydronic-pressure-reset-checklist.md` lowers the pressure without moving any fluid. A Caleffi demineralisation filter has been on the fill side since 2026-09-19; makeup through it is water, so top-ups still use premixed glycol. For any fill larger than a top-up, remove the filter temporarily and fill through the bypass valve behind the autofill's pressure regulator, so the fill cannot over-pressurise the loop. The install dropped the hydronic pressure from 23.3 to 21.0 psi at the same tank temperature and left `.startupFlow` at 52.9 L/min.
- **Flow while running is a controlled output**, trimmed off inlet temperature (register 281) with the compressor, so raw flow, flow ÷ Hz, inlet against target, end-of-cycle inlet and run duration all fail as fouling signals. The **startup plateau** (`.startupFlow`, clean 51.7 L/min since the 2026-09-03 glycol top-up, 50.5–54 before it) is the one comparable measurement, and under 40 L/min is the alarm. **A glycol addition moves this baseline, so record the date of any top-up.** It is also blind to a *total* loss of flow — its 15 L/min floor discards a genuine zero, so `chiltrix-zero-flow` covers that. **The hydronic pressure step at pump start is a second fouling sentinel.** The tank separates flow, never pressure: the `.219` gauge sits on the suction side of the Chiltrix pump's path from the expansion tank connection, so `electrical.ac.arduinoThermPSI.psi` drops by the friction loss of the strainer, exchanger, tank tappings and piping between those points whenever the pump runs. Measured 2026-09-18 over 23 runs: −1.23 psi (−1.00 to −1.56) in the first minute or two at the 52.9 L/min plateau, climbing back about 0.5 psi as the chiller trims flow to 25–35 L/min, and the rest back at the stop; the drop follows flow squared (63 % of the day's pressure variance) and has no relationship to `IN`, `LBT` or the chiller inlet, so thermal contraction of the chilled glycol is at the noise level (−0.19 psi net per run). Read the step at the same startup flow; a growing step at a fixed flow is a filling screen. Baseline 1.0–1.6 psi with the screen about 5 % covered. **The sentinel is valid only for starts from 19.5 psi or more** (1.5 psi above the 18 psi precharge; it was 21.5 psi on the 21 psi precharge): below the precharge the step is −4.4 to −7.5 psi at the same startup flow (every cold start since 2026-09-21 21:13, cold idle pressure 20.1–20.7 psi), which fit the tank's 21 psi precharge at the time and its empty bladder below it; on 2026-10-12 the tank's air valve read 22.7 psi against the loop's 23.0 psi, so the bladder was working. **Register `284` is the fault/lockout word**: 2 is P1 high pressure protection, 32 was the closed-valve lockout of 2026-09-03, and it shows a fault only while active; the ~70 s full scan missed 6 of 18 logged P1s, so the module reads it every sweep (about 1 s since 2026-11-06) and `.faultCode` holds it for 60 s (count P1s as rises of `.faultCode` to 2, checked against the panel's ERROR log); **`284` = 16 is P4 over-current** (matched to the panel's ERROR log on 2026-11-13, panel clock 41–42 s behind the Pi), seen only since the 1 s poll; the 2026-10-24 P4 at the 70 s cadence is only in the panel log. Two P4s 18 minutes apart latched on 2026-11-13 (17:01 and 17:19 EST, cleared by a breaker power cycle), every P4 at the top of a fast ramp to 71–74 Hz at 28.0–28.5 A on `r256` against 24.7–27.1 A on the day's clean runs. **P1 ends about 4 % of heating runs at the 50 °C target** (13 logged 09-27 to 10-20, return 122–127 °F and leaving 129–134 °F at the trip, the same as ordinary stops), and clears itself; two within 30 minutes latched until a breaker power cycle on 2026-10-20 (72 minutes), 2026-10-29 (07:15 and 07:37 EDT, 21 minutes apart), 2026-11-02 and 2026-11-03 (Chiltrix support: a couple of P1s in a row put the unit in full lockout, usually cleared only by a power cycle; no window given), and `chiltrix-fault-latched` now emails when `284` holds non-zero for six minutes; at the 48 °C target the panel log holds 5 P1s in 144 heating starts from 2026-10-20 12:23 to 10-26 08:10 EDT (10-21 01:12, 10-21 23:41, 10-24 22:37, 10-26 04:50, 10-26 06:38, panel clock), 3.5 % against 3.6 % at 50 °C, each at the end of a run and clearing itself (the 10-26 pair 108 minutes apart included), and `284` caught only three of them at its 70 s cadence (`docs/chiltrix-modbus.md`, P1 in heating). During a lockout the pump runs at its `P53` minimum, about 30 L/min at 50 %, which is not a fouled strainer. **Heating target 46 °C since 2026-10-29 12:58 EDT (entered in °C; register 143 reads 319.15 K), after the second lockout; 48 °C from 2026-10-20 12:23, when on Chiltrix support's advice `P38` defrost exit 15 °C (30 before), `P39` defrost start difference 12 °C (8 before), `P53` pump minimum 50 % (40 before).** P1 comes when return water nears 130 °F; a P1 and P4 pair at a cold-night defrost is no concern. Registers `210` and `215` read as high-side pressure (kPa) and its saturation temperature (0.1 °C), unconfirmed against the panel: a P1 is a 350–650 kPa jump in the last minute of a 36–40 Hz plateau with flow and water steady, one ordinary stop in 297 shows it, and steady `210` at 125–130 °F leaving has held 3,350–3,470 kPa since 09-27, so the exchanger is not fouling. The P1 rate went from 3.4–4.2 % of heating stops to 14 % after the fast poll went live (2026-10-26 17:49), and at 46 °C it is 8.1 % (10 in 123 to 2026-11-03), with lockouts on 2026-11-02 (06:13 and 06:39 EST) and 2026-11-03 (04:01 and 04:25 EST), With the poll at ~72 s from 2026-11-03 04:54 EST to 2026-11-06 14:37 EST the panel logged no P1 in 50 heating stops, on days 10 °F warmer than the week before; Chiltrix's engineer (Matt Dail, 2026-11-06) says polling cannot disturb the controller (he reads all 286 registers within 2 s on his own units) and asked for registers 0–146 and 200–286 at 1 s around the next lockout, which the module has sent since 2026-11-06 14:39 EST (`docs/chiltrix-modbus.md`). To give him a lockout, export the raw registers from an hour before the first P1 to the restart, forward-filled to 1 s. `scripts/chiltrix-raw-fetch.sh` (on the Pi) and `scripts/chiltrix-raw-build.py` do it. **The 1 s record of 2026-11-12 to 11-14 gives the mechanisms (`docs/chiltrix-heating-control-analysis.md`): a P1 is a mild-weather fault of a long low-speed period**, 8 to 10 minutes at 36–38 Hz short of the stop (49.2 °C inlet, 3 °C above the target) with zero superheat, the main expansion valve (register 240) closed to 66–76 steps and the pump slowed to 65–73 %, after which high-side pressure rises 900 kPa in two minutes with the water unchanged; cold nights have no such periods and no P1s, and the target does not matter. **A P4 is an overshoot on a mid-run jump of the commanded frequency (register 228) from 44–47 to 73–77 Hz**, input current passing 28.0 A while still accelerating; the drive normally holds 27 A. Proposed and not made, pending Chiltrix's review: `P53` 50 → 80, `P96` 54 → 90, `P27` 100 → 90. The chiller restarts on its own 2 °C hysteresis (`P12`). **`P52` = 2 since 2026-09-16 18:10 EDT**: the pump stops at target and runs one minute after each fifteen-minute stop, so zero idle flow becomes normal if the meter reads the stop, but it does not: the meter read 6.9 L/min through all 588 idle minutes of 2026-09-18 and never 0, the same trickle mode 0 held, so 6.9 L/min is the idle baseline the pressure step is measured against and a genuine zero is still a fault; `chiltrix-zero-flow` reads 7 minutes of zero flow as a fault and then needs a window that spans the restarts, and `.startupFlow` sees the restarts, so compare its baseline across the change. Any capacity analysis using data before 2026-08-22 is measuring a flow-restricted plant. Commissioned 2026-08-04; the first blockage took 18 days.
- **Shoulder-season heating (`docs/chiltrix-shoulder-season-heating-plan.md` §7–8):** a heat↔cool changeover moves the tank about 74 °F and costs 25–45 min of compressor time, 2.3 kWh to heat and 1.6 kWh to cool; the one measured so far (2026-09-08, partial swing) heated at 85 kBTU/h from 3.2 kW and cooled back at 0.034 kWh/°F with zones calling. A mains interruption shows as a sub-minute `operatingMode` = 1 blip with `HPHEAT` energised and a warm outlet; check `journalctl --list-boots` before suspecting the `B` terminal. **Winter (§9): the chiller stays on in heat mode all winter (decided 2026-09-15); the HZ-432 balance point (35 °F since 2026-11-13, the measured setting; 30 °F from 2026-10-18, 35 °F from 2026-10-11, 40 °F before; the panel does not offer 32 °F) sends calls below it to the boiler, the `DHWX` bridge feeds the zones from the tank whenever the boiler refuses a call for DHW, and the five hydronic thermostats sit on Heat, never Auto. Loop B's UP26-99F runs on HIGH in heating since 2026-10-19 and returns to LOW for cooling, because it carries three coils in winter and the great room, its far coil, gets 67 % of design flow on LOW (assessment §5.6); on LOW in the week before, the great room ran 65 % duty on a 38 °F night and held 72 °F, with loop B's ΔT 7.8 °F calling alone and its supply 0.45 °F under `IN`. On HIGH (2026-10-19 to 10-25) loop B's heating ΔT is 6.0 °F calling alone and 5.2 °F with both loops, against 8.4 and 7.2 °F on LOW, and its supply sits 0.45 °F under `IN` (90th percentile 0.76 °F) with both loops calling, so HIGH stays; a loop B supply 2 °F or more under `IN` with both loops calling means the primary is short, so drop to MEDIUM. Taking the unit out of service is HMI off with the breaker on, `DHWX` inhibit open, HZ-432 boiler-only (balance 50 °F or Emergency Heat).** Left on in heat mode it holds the tank at 122 °F for about 1,700 BTU/h at 60 °F ambient (measured 2026-09-15 with the primary off: 130.4 to 125.3 °F in 56 min, the pump idling at 8 L/min through the outdoor exchanger), about 16 reheat starts a day at 30 °F plus defrost, $100 for the winter, accepted; §9 prices it and the first cold week's record replaces the estimate. Chiltrix support (2026-09-16) concurs with `P52` = 2 for the winter (set 2026-09-16 18:10 EDT, `raw.r52` reads 2), expects no slush at 30 %, says `C17` freeze protection runs the pump at full speed and `C16` reports defrost, confirms register 143 is writable, regards cycle count and oil return as no concern, and advises a heating target as low as the rooms allow (the target is 46 °C since 2026-10-29). In off the unit stays powered for its standby protections, ignores the `C`/`H` contacts (the IOM's own instruction for relay-control wiring), keeps the off state through a mains outage (`P00` = 1), and still answers Modbus, so register 140 reads 0 and the freshness alerts stay quiet. Left enabled in cool mode it re-chills the tank at 0 °F ambient and courts E14; `chiltrix-cooling-cold` emails and raises `notifications.pivac.chiltrix_cooling_cold` when the unit is enabled in cooling mode with its own ambient reading under 40 °F for 30 min, which under option 2 means a stale cool call (thermostats on Auto). The HZ-432 has no cooling lockout by outdoor temperature (its `OT LOCKOUT` is a heating-stage lockout for non-dual-fuel panels) and the Chiltrix's outdoor-temperature standby (`P112`, `P42`/`P43`) cannot be used with `C`-`H`-`COM` control, which is why the thermostats must sit on Heat. 30 % glycol covers the outdoor exchanger for burst. The tank cannot cover a long DHW call, and the Ti-200's DHW priority time limit is the setting for that. At $1.93/therm and 18 ¢/kWh the chiller heats for less than the Ti-200 on every day down to about 35 °F (about $2/day saved through 40–55 °F), so the HZ-432 balance temperature is a capacity setting. Through 2026-10-11 the coldest heating hour was 41 °F, no defrost had been seen (`r216` 0), and at 40–45 °F the unit made 64 kBTU/h above 60 Hz at COP 3.1 with 130 °F leaving water (max 71 Hz ever); on the night of 2026-10-17 (38 °F low) it ran 75–87 % of each hour from 01:00 to 08:00 at 49–61 kBTU/h, COP 2.94 overall at 33–36 °F ambient, with the first defrosts on record (`r216` stayed 0, so it is not the defrost register); the November record (plan §8.1, 272 chiller-only hours to 2026-11-14) gives COP 3.0 at 34–36 °F RedLink and 3.4 at 38–44 °F all-in, full duty at 37 °F with every room held, the load meeting capacity near 32–34 °F and price holding the chiller cheaper to about 27 °F, and the panel's own outdoor sensor reads about 1 °F above RedLink at night (41 °F against 39 °F at 09:30 on 2026-11-14; shown only by Checkout step 1, `OT SENSOR VAL`, which drops every relay; the Chiltrix's register 202 with the compressor off 20 min or more matches it and is the logged stand-in, while running it reads about 3 °F below RedLink), so 35 °F on the panel is the measured setting and 30 °F hands over below capacity; judge it by the rooms and the tank, never duty: raise it to 40 °F if a room falls 1 °F below setpoint overnight or the upper tank stays under 105 °F outside a defrost, the dual fuel changeover is `OT` alone, and a latched lockout above the balance point stops all heat because the panel raised no second-stage boiler call during the 2026-11-07 lockout; measured boiler input is `1884 − 28.9 × T(°F)` kBTU/day from `scripts/boiler-heat-by-outdoor.py`, and the chiller's heating COP is measured at 3.4 to 4.1 between 45 and 60 °F ambient with a 120 °F return (3.6 over 568 steady minutes, 6.8 while the return is under 95 °F, peak draw 6.9 kW and 26.9 A) and is an estimate below 45 °F. **Changeovers decide the saving**: 35 in the six days from 2026-09-22 with the thermostats on 71 °F heat and 74–76 °F cool cost 26 kWh of tank swings and brought the chiller from 40 % cheaper than gas to between a tie and a third cheaper.
