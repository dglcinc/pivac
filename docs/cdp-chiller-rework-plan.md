# CDP Relay + RPi Label Rework — single-chiller conversion

**Status:** partially executed.
**Date:** 2026-07-23, revised 2026-08-10 to match what actually shipped.

> **⚠️ The naming scheme in the original plan was superseded before it was built.** This plan
> specified `RCHL→CHIL` and `LCHL→BOS2`. What actually shipped on 2026-08-02 was
> **`RCHL→BOS2`** and **`LCHL→BOS1`**, with the old `BOS1` on BCM 24 dropped in favour of the
> reclaimed relay. Sections 2–6 have been rewritten to the shipped scheme; the original is
> recoverable from this file's git history.
>
> **`CHIL` arrived later, on a different pin (2026-08-11).** The CHIL *relay* always existed in the
> panel — the 2026-08-02 change simply landed no Pi input on it. On 2026-08-11 the `SCALA`
> booster-pump-leak-pan input on **BCM 25 / phys 22** was renamed to **`CHIL`** and now senses the
> chiller call, so the chiller **is** monitored. Earlier revisions of this document said the chiller
> gives no call contact and is deliberately unmonitored — **both statements are wrong** and are
> corrected throughout. The leak-pan signal is no longer published.

**What is done:** the chiller conversion itself (two UniChillers → one Chiltrix CX75, 2026-08),
and the `pivac.GPIO` software side — live on the Pi and verified, with the repo-side changes
(`config.yml.sample`, README, both Grafana dashboards, CLAUDE.md) carried by **PR #96**.

**What is outstanding:** the CDP panel wiring detail behind the reclaimed relays, the label
reprint (§4) — including the override relay, still unlabeled — and the new-Pi build (§6), which
has not been started. **The panel-side coil wiring state is
not recorded anywhere** — §3 and §6 describe what the wiring must be, not what has been verified.
Confirm at the panel before treating any of it as done.
**Scope:** Control Distribution Panel (CDP) relay bank, the Raspberry Pi enclosure label, the
Pi's GPIO wiring harness, `pivac.GPIO` config, and the Grafana panels that reference the
retired relays. Also covers the new-Pi build, which reuses the existing harness.

**Driver:** both original UniChiller outdoor units are decommissioned and replaced by **one new
chiller**. That removes the need for chiller alternation (YALT), two-stage cooling staging
(Y2ON / Y2FAN), and a second chiller call (LCHL). Separately, **BOS2** gains a monitoring
relay so its compressor call is sensed the same way BOS1 already is.

**Out of scope (explicitly not touched by this plan):** the boiler / Sentry camera path, DHW,
the domestic-water and irrigation nodes, the Arduino pressure boards, 1-Wire sensors, and
anything in the `hvac.boiler.*` or `environment.water.*` Signal K trees. No InfluxDB data is
deleted.

---

## 1. Pre-conversion baseline

*This table is the state **before** the conversion, retained as the historical record of what the
panel and label looked like. For the current roster see §2.*

The label rows map to `(BCM, physical)` pin pairs — verified consistent for all 12 rows against
the Pi 40-pin header. The **live** `pivac.GPIO` config (OneDrive copy of `config.yml`, 2026-03-10)
is one revision ahead of the repo's `config/config.yml.sample`, which is missing BOS1 and SCALA.

| Row | Label (printed) | BCM | Phys | In live config? | Notes |
|----:|-----------------|----:|-----:|-----------------|-------|
| 1 | ZV | 17 | 11 | yes | Zone valves |
| 2 | DHW | 27 | 13 | yes | Domestic hot water call |
| 3 | BLR | 22 | 15 | yes | Boiler call |
| 4 | RCHL | 5 | 29 | yes | Right chiller — **in service today** |
| 5 | LCHL | 6 | 31 | yes | Left chiller — decommissioned 2025 |
| 6 | Y2ON | 13 | 33 | yes | A/C high call, 4-min timer relay |
| 7 | **Y2OFF** | 26 | 37 | as `YOFF` | **Label typo** — config says `YOFF`. Currently commented out (dead pad on old Pi) |
| 8 | Y2FAN | 16 | 36 | yes | |
| 9 | DEHUM | 12 | 32 | yes | |
| 10 | SCALA | 25 | 22 | yes | Booster-pump leak pan. *Blank on the repo's docx — the printed label is newer* |
| 11 | BOS1 | 24 | 18 | yes | Kitchen compressor. *Blank on the repo's docx* |
| 12 | UNUSED | 23 | 16 | no | The only free input *in the current state* — and, having never been used, the only one with **no wire run to the header** |

> The `docs/PhoenixContact-BC-RPI-label.docx` in this repo (md5 `e9217d7c…`, from `dglcinc/HVAC-pi`
> commit `8062fd0`) shows rows 10–12 all as `UNUSED` and row 7 as `Y2OFF`. It is **one revision
> behind the printed label**. Rows 10/11 must be filled in from live config as part of this edit,
> not just the chiller changes.

---

## 2. Target state

**Decisions as shipped (2026-08-02, amended 2026-08-11):** both old chiller relays were reclaimed
**in place** as Bosch compressor monitoring inputs — no header wire moved. The chiller call is
sensed too, but on a **different pin than this plan originally proposed**: `SCALA` on **BCM 25 /
phys 22** was renamed **`CHIL`** on 2026-08-11 and now watches the chiller call relay. Note what
`CHIL` actually reports — it is the *zone-demand* side, not the compressor (§3).

**YOFF is retired — it is no longer in use.** BCM 26 / phys 37 becomes a spare, and the dead-pad
question is moot: there is **no rewire to BCM 19**, on either the current Pi or the new one. The
seasonal-cutoff function it performed no longer exists as a CDP interlock (§3, item 2).

| Row | New label | BCM | Phys | Action |
|----:|-----------|----:|-----:|--------|
| 1 | ZV | 17 | 11 | unchanged |
| 2 | DHW | 27 | 13 | unchanged |
| 3 | BLR | 22 | 15 | unchanged |
| 4 | **BOS2** | 5 | 29 | **rename only** (was RCHL) — relay reclaimed in place, contact wire reused |
| 5 | **BOS1** | 6 | 31 | **rename only** (was LCHL) — relay reclaimed in place, contact wire reused |
| 6 | UNUSED | 13 | 33 | **freed** — pull wire at header + relay |
| 7 | UNUSED | 26 | 37 | **retired** — YOFF no longer in use; the dead pad on the current Pi is now irrelevant |
| 8 | UNUSED | 16 | 36 | **freed** — pull wire at header + relay |
| 9 | DEHUM | 12 | 32 | unchanged |
| 10 | **CHIL** | 25 | 22 | **rename only** (was SCALA, 2026-08-11) — now senses the chiller call; leak-pan signal dropped |
| 11 | UNUSED | 24 | 18 | **freed** — the old BOS1 input, superseded by row 5 |
| 12 | UNUSED | 23 | 16 | unchanged — remains a true spare, still unwired |

**Net effect:** 7 active inputs (ZV, DHW, BLR, BOS2, BOS1, DEHUM, **CHIL**). Spares: BCM 13/33,
16/36, 24/18, 26/37, 23/16 — **five**, against the original plan's three, because retiring YOFF and
the old BOS1 input frees extra slots while `CHIL` reused an existing input rather than a spare. All
but 23/16 already have wire runs to the header, so most are cheap to press into service (§8).

> **Spare caveat while the current Pi is still in service** (the new Pi is not built yet):
> **BCM 26 / phys 37 is not usable** — that pad is electrically dead on this board, which is why
> YOFF was disabled in the first place. It only becomes a real spare on the new Pi. Treat the
> usable spares today as **BCM 13/33, 16/36, 24/18** (all wired) and **23/16** (unwired).

**Wire movement at the header: zero.** Two pulls (Y2ON, Y2FAN) plus the retired old-BOS1 run on
pin 18, no new header runs, no relocations.

> **Why the two Bosch inputs land in the old chiller slots.** Both chiller relays are plain N/O
> relays whose dry contacts **already have wire runs to header pins 29 and 31**. Reclaiming them in
> place means the only new conductors in the whole job are the two Bosch compressor calls into the
> relay coils. Pin 16 has never been wired, so siting anything there would add a contact-to-header
> run for nothing, and the old BOS1 relay on pin 18 is freed rather than kept so that BOS1 and BOS2
> sit adjacent on the label (rows 4/5) instead of being split across the strip.

---

## 3. Relay hardware

### Removed / reclaimed

| Relay | Disposition | Reason |
|-------|-------------|--------|
| **RCHL** | **Reclaim in place → BOS2 sensing** | Plain N/O relay; its contact wire to pin 29 is reused as-is. The chiller it called no longer exists |
| **LCHL** | **Reclaim in place → BOS1 sensing** | Same, contact wire to pin 31 reused |
| **old BOS1** (BCM 24) | **Free** | Superseded by the reclaimed LCHL relay; its pin-18 run is retired |
| **Y2ON** | Remove or spare | 4-min **timer** relay; not suitable as plain sensing unless set instantaneous |
| **Y2FAN** | Remove or spare | Staging no longer needed |
| **YALT** | **Remove entirely** | Alternation is meaningless with one chiller |

Reclaiming both chiller relays means **no new relay hardware is needed**. Leaving them in their
existing rail positions — rather than moving them — is what lets both contact-to-header wires stay
untouched, and keeps the DIN layout dense with no shuffling.

### The chiller call path and the override

> **⚠️ `CHIL` is the DEMAND side, not the chiller's run command.** The single most important thing
> to understand about this plant: **the CHIL relay operates independently of whether the chiller
> is running.** Do not read `CHIL` asserted as "the chiller is on".

The system is **decoupled across the buffer tank**, with the tank acting as the thermal buffer
between two independent controls:

```
DEMAND SIDE                                  SUPPLY SIDE
water-cooled zone calls (HZ432 "Y")          Chiltrix's own controller
        │                                            │
        ▼                                            ▼
   CHIL relay ──→ pulls chilled water          runs the compressor when buffer-tank
   (+ closes the chiller's Y contacts,         RETURN WATER hits setpoint
    enabling it)                               (50, with a 2 °C hysteresis)
        │                                            │
        └──────────────→ BUFFER TANK ←───────────────┘
                       (37 gal, UBT/LBT)
```

- **The CHIL relay** is triggered by a **Y call from the Honeywell HZ432** when one of the three
  water-cooled zones calls for cool. What it does is **draw chilled water out of the buffer tank**
  to that zone. It also closes the chiller's Y dry contacts, but that is an **enable**, not a run
  command — the chiller still decides for itself whether to fire.
- **The chiller runs as needed**, on its own return-water thermostat: it starts when return water
  from the buffer tank reaches setpoint (**50, plus a 2 °C hysteresis**) and stops when satisfied.
  *(Recorded as David stated it — note the mixed units; 50 is presumably °F with a 2 °C band.
  Confirm against the Chiltrix controller before relying on the exact figures.)*
- **The override relay** is a second N.O. relay bridging the same Y dry contacts. It holds the
  chiller **enabled** continuously, independent of the HZ432, so the unit keeps the tank at
  setpoint even with no zone calling. It is **manual, currently unlabeled, and has no signal wired
  to energize it**.

> **Consequences for monitoring — three different questions, three different signals:**
>
> | Question | Signal | Notes |
> |---|---|---|
> | Is a water zone calling? | `CHIL` relay | demand only; says nothing about the compressor |
> | Is the chiller actually running? | **`electrical.emporia.house.chiltrix`** (power draw) | the only direct run signal we have |
> | Is the loop keeping up? | `UBT` / `LBT` | the outcome; what actually matters |
>
> This is why a `CHIL` freshness rule was the wrong shape for chiller-failure detection (§5.5).
> `CHIL` can be asserted for a long stretch with the compressor cycling on and off underneath it,
> and the override makes the chiller run with `CHIL` idle. **Emporia's `chiltrix` circuit is the
> run signal**; UBT/LBT show whether the run is achieving anything.
>
> Note UBT/LBT observe the *result*, not the chiller's control input — the Chiltrix regulates on
> its own internal return-water sensor, so our tank probes are a downstream proxy, not the same
> measurement.

### Control-logic consequences — **SETTLED 2026-08-12**

These started as inferences from the v1.7 manual's CDP Relays Walkthrough, flagged for physical
verification. **David has since confirmed the end state, so they are now statements of fact rather
than things to check.** The v1.7 manual describes the *old* plant and is superseded on every point
below — do not re-derive control logic from it.

**The whole intermediate control layer is gone.** `CRWA`/`CWRA` (the chilled-water return
aquastat), the **alternating relay** (`YALT`) and the **low-ambient cutoff** (`YOFF`) are all
decommissioned. **The Chiltrix controller and the CHIL relay together perform every function for
the water-cooled zones** — there is no external aquastat gating it, no alternation to arbitrate
(one unit), and no external staging.

See the decoupled demand/supply diagram above for what remains; it is not repeated here, because
two drawings of the same plant is exactly how the old architecture diagrams came to disagree with
reality. **The one-line version: `CHIL` moves water out of the tank, the Chiltrix decides on its
own when to refill it with cold.**

1. **YALT is decommissioned.** The manual's description — YALT "uses lead and lag calls from the
   zone controller, CWRA, and Y2 relays to energize the chiller relays" — describes plant that no
   longer exists. Alternation is meaningless with one chiller. The HZ432 Y call now drives the
   CHIL relay directly.
2. **YOFF is retired. The seasonal cutoff is now powering the chiller down at the breaker.** The
   old YOFF opened a N/C contact to disable power to YALT and the CWRA; with YALT gone and YOFF
   out of service, **no CDP interlock inhibits cooling seasonally, by design**. Winter shutdown is
   a manual breaker-off at the panel.

   This is simpler than the old interlock and it is also *stronger*: killing power is upstream of
   both call paths, so it defeats the override as well as the HZ432. The tradeoff is that it is
   **entirely procedural** — nothing enforces or records it. Two follow-ons worth noting:

   - **The override cannot cause a winter run once the breaker is off**, which removes what would
     otherwise be the main hazard of leaving it engaged (§3). Before the breaker is thrown, an
     engaged override does hold the chiller calling regardless of season.
   - **The loop must survive winter unpowered and static** — no circulation, no chiller freeze
     protection, outdoor unit included. That is what the glycol concentration is protecting, and
     it is the reason the concentration matters more now than it did under the old always-powered
     arrangement. See §7.
3. **Two-stage staging is gone with Y2ON/Y2FAN, and nothing external replaces it.** The Chiltrix
   modulates internally, so no external stage-2 call is needed. The freed inputs stay freed — the
   earlier caveat about having to bring one back does not apply.
4. **CRWA / CWRA is decommissioned.** The return-water aquastat no longer gates the chiller. The
   Chiltrix regulates on its **own internal return-water sensor** instead, which is the same
   mechanism that lets it hold buffer-tank temperature under the override — the sensing moved
   inside the unit rather than disappearing.

### Zone → equipment map

Which thermostat zone is served by which cooling source. All five RedLink zones are accounted
for, so any zone calling for cool should assert exactly one of `CHIL`, `BOS1` or `BOS2`.

| Cooling source | Relay | RedLink zone(s) | Emporia circuit |
|----------------|-------|-----------------|-----------------|
| **Chiltrix CX75** (hydronic, via buffer tank) | `CHIL` | `MASTER_BR`, `DSTRS_FAM_ROOM`, `KIDS_ROOM` | `electrical.emporia.house.chiltrix` |
| **Bosch BOVA** (kitchen) | `BOS1` | `KITCHEN` | `electrical.emporia.house.bova_kitchen` |
| **Bosch BOVA** (great room) | `BOS2` | `GREAT_ROOM` | on `electrical.emporia.house.utility_sub_panel` |

Notes:

- **The chiller carries three zones; each Bosch carries one.** So `CHIL` should assert far more
  often than either BOS relay, and a quiet `CHIL` on a hot day is more suspicious than a quiet
  `BOS1`.
- **`bova_kitchen` is the Emporia rename that finally disambiguates the two BOVAs** — it is the
  BOS1 unit. The BOS2 unit currently has **no circuit of its own**: it sits inside
  `utility_sub_panel` with the fridge and shop outlets, so its draw cannot be read in isolation.
  **This is temporary — a CT for BOS2 is on order (2026-08-12).** Once fitted, BOS2 gets its own
  Emporia circuit and `utility_sub_panel` drops to the fridge and shop outlets; expect to add the
  new series to Grafana panel 10 then.
- **`CHIL` asserting means a zone is drawing chilled water, NOT that the chiller is running**
  (see the decoupled diagram above). The compressor cycles on its own return-water setpoint
  underneath a long `CHIL` call, and the override runs it with `CHIL` idle. For "is the chiller
  actually running", use `electrical.emporia.house.chiltrix`.

### BOS1 / BOS2 sensing

**The CDP relay is not in the compressor's control path.** When an air handler calls for cooling
it drives its compressor **directly**; that path is untouched by this rework and does not pass
through the CDP. What the CDP relay senses is a *parallel* indication:

```
air handler call for cooling ─┬─→ compressor                      (control path — untouched)
                              └─→ air handler's call relay
                                    └─→ existing run to mechanical room
                                          └─→ CDP relay coil
                                                └─→ dry contact → Pi input   (monitoring only)
```

The air handler already had a relay that sent a call to the mechanical room — that is what used to
drive the chiller. With the chillers gone, that same relay output is repurposed to energize the
reclaimed CDP relay, whose dry contact feeds the Pi input, pulled up internally (`pullmode:
pullup`, matching every other input).

| Signal | Relay reclaimed | Pi input |
|--------|-----------------|----------|
| BOS2 | old **RCHL** | BCM 5 / phys 29 |
| BOS1 | old **LCHL** | BCM 6 / phys 31 |

**There are no new conductors.** The air-handler-to-mechanical-room runs already existed to carry
the old chiller calls, and both CDP relays keep their existing contact wires to the header. The
job is a re-landing of what was already there, not new cable. **Do not feed 24 VAC anywhere near
the header.**

Two consequences worth being explicit about:

- **The monitoring cannot break cooling.** Because the CDP relay is a parallel tap rather than a
  series element, a failed relay, a dropped coil wire, or a dead Pi input loses *visibility* only.
  Cooling continues regardless. This is a strictly better arrangement than putting the sense relay
  in the call path.
- **The series records the air handler's call, not proof the compressor ran.** `BOS1`/`BOS2`
  assert when the air handler calls for cooling. If a compressor is called but fails to start —
  breaker trip, high-pressure lockout, contactor failure — the relay still shows asserted. A
  silent compressor failure therefore looks like normal operation on the dashboard. Cross-check
  against Emporia (`electrical.emporia.house.bosch_bova` and the `utility_sub_panel` circuit) if
  actual running state matters: real compressor draw is the signal that distinguishes them.

---

## 4. Label (`docs/PhoenixContact-BC-RPI-label.docx`)

Seven single-token text swaps against the table in §2, plus the catch-up fill on row 10.
No layout change — the label is already sized to fit under the Phoenix Contact clear cover, and
row count is unchanged.

| Row | From | To |
|----:|------|----|
| 4 | `RCHL` | `BOS2` |
| 5 | `LCHL` | `BOS1` |
| 6 | `Y2ON` | `UNUSED` |
| 7 | `Y2OFF` | `UNUSED` — YOFF retired, no longer in use |
| 8 | `Y2FAN` | `UNUSED` |
| 10 | *(blank on the docx)* | `SCALA` |
| 11 | `BOS1` | `UNUSED` |

Row 11 is the one to watch: the repo's docx shows it blank, the *printed* label shows `BOS1`, and
it now becomes `UNUSED` because that input was retired. Whichever copy you edit, the end state is
`UNUSED`.

> **The override relay still needs a label.** The manual N.O. relay that bridges the chiller's Y
> dry contacts (§3) is unlabeled. It does not occupy a row in the table above — that table maps Pi
> header inputs, and this relay drives nothing on the Pi — but it is the one device in the panel
> whose position is *not* discoverable from anywhere: no energizing signal, no telemetry, no label.
> Whatever it is called, the label should say what closing it does (holds the chiller Y call
> closed → chiller maintains buffer-tank temperature) rather than just naming it.

The trailing `6489705080` on the label is, per the manual, the Pi's MAC address. **It will be wrong
on the new Pi** — capture the new board's `eth0` MAC during the build and update it in the same
edit. (For reference the current Pi's `eth0` is `d8:3a:dd:b1:ad:4d`.)

Mechanics: `.docx` is a zip; the edit is a targeted swap in `word/document.xml` then rezip. No
`python-docx` needed for text-only changes.

---

## 5. Software

### 5.1 `pivac.GPIO` config

**✅ Done 2026-08-02** — live on the Pi and verified; repo-side in PR #96.

Live file is `/etc/pivac/config.yml` on the Pi. Under `pivac.GPIO: inputs:`

- `5:` — `outname: RCHL` → **`BOS2`**
- `6:` — `outname: LCHL` → **`BOS1`**
- `13:` — **delete** (Y2ON)
- `16:` — **delete** (Y2FAN)
- `24:` — **delete** (old BOS1, superseded by pin 6)
- `26:` — **stays commented out permanently.** YOFF is retired (§2); this is no longer a pending
  re-enable and the dead-pad workaround is not needed. It can be deleted outright at the next
  config edit.
- leave `17 ZV`, `27 DHW`, `22 BLR`, `12 DEHUM`, `25 SCALA` untouched
- `23:` is **not** added — it stays an unconfigured spare

Both chiller-slot changes are pure `outname` renames; no pin numbers move.

Then **`sudo systemctl restart pivac-gpio` followed by `sudo systemctl restart signalk`** — see
§5.2 for why the second restart is not optional.

`config/config.yml.sample` in this repo is brought up to date by PR #96 (it previously lacked BOS1
and SCALA and still listed the retired chiller inputs).

### 5.2 Signal K path churn

Paths are `electrical.ac.switch.utility.{NAME}.{state,statenum}`. Retiring Y2ON / Y2FAN / old BOS1
and renaming RCHL → BOS2 and LCHL → BOS1 means:

- `…RCHL.state` and `…LCHL.state` **stop updating**; `…BOS2.state` and `…BOS1.state` start fresh.
  Both are renames at the *pin*, not continuations of meaning — the new series measure different
  equipment, so the break in history is correct.
- `…BOS1` is the awkward case: the name survives but **moves pins**, so its series breaks even
  though the signal it represents did not change. History before 2026-08-02 belongs to the pin-24
  input; after, to the pin-6 input. Same signal, discontinuous series.
- The existing InfluxDB series stay on disk as the historical record of the old chillers.
  **Nothing is deleted** — the same naming-vs-history tradeoff as the inverted Arduino module
  names and the CRW→UBT rename.

> **⚠️ Retiring a path requires a `signalk` restart.** Signal K keeps a retired path in its data
> model, frozen at its last value, until the server restarts — and the WilhelmSK SwitchBank
> enumerates whatever Signal K holds. Verified live 2026-08-02: after `restart pivac-gpio` alone,
> `BOS1`/`BOS2` published fresh while stale `LCHL`/`RCHL`/`Y2ON`/`Y2FAN` still sat in the API and
> still appeared on the dashboards. `restart signalk` cut the list to exactly 7. **Recipe: config
> edit → `restart pivac-gpio` → `restart signalk`.** This is the same behaviour later confirmed
> for the 1-Wire roster change.

### 5.3 Grafana

**✅ Done in PR #96.** Both dashboards referenced the retired names and would otherwise show dead
series:

- **`grafana/dashboards/pivacr.json`** — Y2ON/Y2FAN series dropped, RCHL/LCHL repointed to
  BOS2/BOS1, and the two Bosch series grouped together rather than left where the old chiller
  series sat.
- **`grafana/dashboards/chiller-time-r.json`** — its whole premise was per-chiller runtime across
  two units, which is meaningless now. Recast as **"Relay Run Time (hours/day)"** over BOS1 + BOS2.
  With CHIL dropped there is no chiller series to include, so despite the filename and dashboard
  uid this panel no longer reports chiller runtime at all. **Renaming the file and uid is deferred**
  — the uid `adjb9zorra8e8c` is referenced by provisioning and the title now carries the meaning.

Keep the PivacR panel conventions: `custom.axisWidth: 50`, no per-panel `axisLabel`, and boolean
relay state as a **stepped-line timeseries** rather than a state-timeline (which can't align its
row-label width).

### 5.4 WilhelmSK

**✅ Settled 2026-08-02 — no `.wlyt` change is ever needed for a relay change.** The original
worry was that the SwitchBank encoded SK paths in some non-greppable form. It does not: both
widgets carry only the parent path `"path": "electrical.ac.switch.utility"` and **enumerate
children dynamically** from whatever Signal K holds. That is precisely why the `signalk` restart
in §5.2 matters — the bank is a live view of the server's data model, so a retired path keeps
showing until the server forgets it. Adding, dropping, or renaming a relay needs no layout edit on
either the iPad or iPhone.

### 5.5 Alerting

No Grafana alert rule references the relay paths (the freshness rules cover temps, pressures, and
water only), so **no alerting changes were required**.

The original plan proposed a freshness rule on `CHIL` to catch a failed chiller call. The relay
still exists and could be landed on a freed input, but **a call-based rule is the wrong shape for
this chiller**: the override bypasses the CHIL relay, and the Chiltrix runs to buffer-tank setpoint
rather than to zone demand (§3). A CHIL rule would therefore alarm on a chiller that is running
fine under override, and stay quiet on one that has failed while the tank drifts.

`CHIL` is also the *demand* signal rather than the run signal — the compressor cycles
independently underneath it (§3) — so even a perfectly fresh `CHIL` says nothing about whether
the chiller fired. Chiller-failure detection belongs on the **process side**: `environment.inside.hvac.{UBT,LBT}.
temperature` failing to fall — or drifting up — over a sustained window is the signal that the
chiller is not doing its job, regardless of which path called it. That is the right shape but
genuinely harder to get right than a freshness check (it needs a window long enough to survive
normal off cycles), and it has not been designed. **UBT/LBT stratification is also still
unverified** — both read 46.1 °F on install — so the tank-based rule should wait until there is a
call to stratify against.

> If an alert rule is ever removed from these YAMLs, note that Grafana alert provisioning is
> **additive** — deleting a rule from `groups:` does not delete it from Grafana. See the
> `deleteRules:` requirement in `CLAUDE.md`.

---

## 6. Sequencing

Do the software prep before the panel is opened, so the new Pi boots into a correct config and you
aren't debugging YAML with the panel in pieces. **Step 1b is already done** (PR #96); the config on
the live Pi is already at the target state, so a clone-based build inherits it.

1. **Bench, before touching the panel**
   a. Update the label docx (§4), leaving the MAC as a placeholder.
   b. ~~Update `config.yml.sample` + the two Grafana dashboards~~ — **done, PR #96.**
   c. Build the new Pi: image from the weekly `sd-clone` spare or a fresh install, then restore
      `/etc/pivac/config.yml`. Record the new `eth0` MAC. If the image is a clone taken after
      2026-08-02 the §5.1 edits are already present — verify rather than reapply.
   d. **DHCP-reserve the new MAC to `10.0.0.82` in UniFi** — the nginx port-forwards and every
      external URL depend on that address.

2. **Panel work, power off**
   a. Photograph the panel and label every wire before removing anything.
   b. Pull the YOFF wire from pin 37 — the input is retired (§2), so there is no pad test to run
      and no move to BCM 19. If the wire is left landed it must stay commented out in config, or
      the dead pad will fabricate data (this is exactly what produced the bogus Jun–Jul 2026 YOFF
      plateau in InfluxDB).
   c. Pull the Y2ON and Y2FAN wires from header pins 33 and 36, and the retired old-BOS1 run from
      pin 18. **Leave pins 29 and 31 alone** — those wires are being reused for BOS2 and BOS1.
   d. Remove YALT; the chiller call path is now HZ432 Y → CHIL relay → chiller Y dry contacts,
      with the override relay in parallel (§3). No Pi input senses either.
   e. ~~Re-establish YOFF's cutoff~~ — **not applicable.** Seasonal shutdown is a manual breaker-off
      at the chiller (§3, item 2). Nothing to wire or prove here.
   f. Reclaim both chiller relays in place: land each air handler's call-relay output onto the
      corresponding CDP relay coil, in place of the old chiller call it used to drive. Contact
      wires to **pins 29 and 31** are untouched, and the air-handler-to-mechanical-room runs are
      reused as-is (§3). BOS1's indication moves off the old pin-24 relay, which is then retired.
      Nothing here touches either compressor's control path.
   g. Fit the new Pi and the updated label.

3. **Verify**
   ```bash
   python -c "import pivac.GPIO as m, json; print(json.dumps(m.status(), indent=2))"
   ```
   Expect exactly **7 inputs** (ZV, DHW, BLR, BOS2, BOS1, DEHUM, CHIL) — no LCHL, RCHL, Y2ON,
   Y2FAN, YOFF or SCALA. If any retired name is still present in the **Signal K API** rather than the
   module output, that is the missing `restart signalk` (§5.2), not a config fault.

   Then: **call the `KITCHEN` zone and confirm `BOS1` asserts, then the `GREAT_ROOM` zone and
   confirm `BOS2` asserts** — one at a time (see the zone map in §3). This proves each air
   handler's call relay landed on the right CDP relay rather than the two being swapped, which is
   the failure mode a config-only rename cannot distinguish: crossed relays look perfectly healthy
   until you check which zone drives which. It is the only physical check left in this plan; the
   YOFF cutoff test is gone with YOFF.

   Optionally also call one of `MASTER_BR` / `DSTRS_FAM_ROOM` / `KIDS_ROOM` and confirm `CHIL`
   asserts — weaker evidence, since the Chiltrix runs to tank setpoint and may already be calling
   for reasons unrelated to the zone.

4. **Document** — `CLAUDE.md` is already updated for the relay roster and the retired-name/InfluxDB
   note (PR #96); the GPIO 26 item resolves when the new Pi is fitted. Still outstanding: the
   **HVAC System Manual's CDP Relays Walkthrough**, which continues to describe LCHL, RCHL, Y2ON,
   YALT and two chillers, and is the document a contractor is most likely to read.

---

## 7. Loop water volume after the conversion

Recorded 2026-08-10, after the hardware change was made. The conversion shrank the hydronic
loop three ways: the chiller moved closer to the house, the buffer tank was downsized, and two
outdoor units became one.

| Component | Change | Δ volume |
|-----------|--------|---------:|
| Thermal buffer tank | 40 gal → 37 gal | **−3.0 gal** |
| 1¼" PEX | ~40 ft removed @ 0.0453 gal/ft | **−1.8 gal** |
| Outdoor units | 2 × UniChiller → 1 × Chiltrix CX75 | **≈ −1 gal** (assumed) |
| | | |
| **Total** | **92 gal → ≈ 86 gal** | **≈ −6 gal** |

The tank downsizing dominates; everything else is small. Net reduction is roughly 6–7 %.

**Derivation notes, so the figure can be rechecked rather than trusted:**

- The **92 gal** starting figure is David's pre-conversion calculation. It is not derived
  anywhere in this repo, and its component breakdown — in particular whether it included the
  chillers' internal volume — is not recorded. Everything above is a delta applied to it.
- **1¼" PEX holds 0.0453 gal/ft** (ID ≈ 1.054", SDR-9). The result is insensitive to the exact
  ID spec: computing the wall from SDR-9 instead gives ID 1.069" and 0.0466 gal/ft, moving the
  40 ft term by 0.05 gal.
- **The 40 ft is read as 40 linear feet of tubing removed.** If it instead describes the *run*
  shortening by 40 ft, both supply and return shortened — 80 ft of tubing, −3.6 gal, and the
  total becomes **≈ 84 gal**. Worth pinning down if the number is ever used for anything
  load-bearing.
- **The chiller term is an assumption, not a measurement.** Two units were removed and one
  installed, so even with identical internal volumes the net is *minus one unit's worth* — not
  a wash. For a brazed-plate heat exchanger plus internal piping at this capacity, ~1 gal is a
  reasonable placeholder. Replace it with the CX75's published internal volume when convenient.

### Glycol

Inhibited **propylene** glycol, refractometer-measured at **25 %** by volume (2026-08-10). To
reach **30 %** by draining mixture and replacing it with 100 % glycol at constant system volume:

```
X = V × (C_target − C_now) / (1 − C_now)
X = 86 × (0.30 − 0.25) / (1 − 0.25) = 5.7 gal
```

**Drain ≈ 5.7 gal, add ≈ 5.7 gal of 100 % glycol.** Insensitive to the volume uncertainty above —
at 84 gal it is 5.6. Circulate before drawing the sample and before re-measuring, so the fluid
removed is actually at loop concentration rather than a stratified pocket.

**Why the concentration matters more than it used to:** the winter shutdown is now a breaker-off
(§3, item 2), so the loop sits **unpowered and static all winter, outdoor unit included** — no
circulation, no chiller freeze protection. Freeze protection is the fluid alone. Note the standard
distinction: 30 % PG puts the *freeze* point near 8 °F but the *burst* point far lower, and for a
static loop burst protection is the relevant figure since PG forms slush rather than expanding
sharply. Check the intended figure against the CX75's own glycol guidance, which may specify a
minimum for the unit rather than for the climate.

---

## 8. Open items

- **Label the override relay** (§4). It is the only device in the panel whose state is discoverable
  from nowhere — manual, no energizing signal, no telemetry, no label. Optionally land a spare pole
  on one of the wired free inputs (BCM 13/33, 16/36 or 24/18) so its position shows up in Signal K;
  that is the cheapest way to stop it being forgotten in either position.
- **Winter shutdown is now purely procedural** — breaker off at the chiller, nothing enforces or
  records it (§3, item 2). Worth a calendar reminder rather than a wiring change.
- **Check ≈86 gal against the CX75's minimum loop volume.** The buffer tank exists to stop the
  compressor short-cycling, and the loop just lost ~6 gal while consolidating two compressors
  into one. The Chiltrix is inverter-driven and modulates, so it tolerates a small loop far
  better than a fixed-speed unit would — this is expected to pass, but it is a one-line check
  against the manual and has not been done.
- **Confirm BOS1/BOS2 are not swapped** — the zone-by-zone test in §6.3. The wiring arrangement is
  recorded in §3, but nothing yet confirms which air handler landed on which CDP relay, and a
  crossed pair is indistinguishable from a correct one in the config.
- **Decide whether call-only monitoring is enough.** `BOS1`/`BOS2` record the air handler's call,
  so a compressor that fails to start still reads as asserted (§3). Pairing them with Emporia
  circuit draw would turn "was it called" into "did it actually run" — not designed.
- ~~Decide whether to land CHIL on a freed input~~ — **done 2026-08-11**, though on BCM 25 by
  renaming `SCALA` rather than on a spare. Remember what it does and does not tell you: it reports
  the HZ432 zone call, not the override and not the compressor (§3).
- **Buffer-tank alerting is the real chiller-failure detector** (§5.5) — undesigned, and blocked
  on confirming UBT/LBT actually stratify.
- ~~Confirm the new chiller needs no external stage-2 call~~ — **settled**: the Chiltrix modulates
  internally, no external staging (§3, item 3). The freed inputs stay freed.
- **Add the BOS2 series to Grafana panel 10 once its CT is fitted** (on order 2026-08-12). Until
  then BOS2's draw is only visible mixed into `utility_sub_panel`.
- Decide the fate of the freed Y2ON timer and Y2FAN relays (spares vs. removal) — no impact on
  the Pi side either way.
- **HVAC System Manual — v1.8 drafted 2026-08-12, needs David's review then structural work.**
  `~/OneDrive - DGLC/Claude/HVAC System Manual - 68 Lookout Road v1.8.docx` (v1.7 untouched).
  **23 paragraphs rewritten, text-only** — paragraph count, styles, bookmarks and all 38 embedded
  images preserved; no figures, tables or sections were added or removed. Covers the CDP Relays
  Walkthrough (LCHL/RCHL → BOS1/BOS2, Y2ON/YOFF/YALT marked DECOMMISSIONED, SCALA → CHIL), the
  glossary, and the spring/fall seasonal checklists.
  **Deliberately left for David — these need new photos and layout judgement, which is why they
  were not attempted:**
  - The **Chillers** hardware section (Figure 10 "The 5-ton UniChillers", ~p421–428): still
    describes two 5-ton units in the chiller shack, activated via LCHL/RCHL dry contacts.
  - **Chiller Tuning Settings + aquastat tables** (~p429–472, Figure 11): Left Chiller / Right
    Chiller / CWRA columns, all obsolete — the Chiltrix regulates internally.
  - **Figure 12 "Chiller Return Water Thermal Mass Tank"** (~p477) — this is now the 37 gal buffer
    tank with the UBT/LBT probes on it.
  - **CRWA section and Figures 13/14** (~p483–531): the aquastat is decommissioned; the whole
    section can go once its figures are dealt with.
  - **"Alternative approach to winterize chillers"** (~p768–770) and the emergency-shutdown and
    zone-controller paragraphs (p173, p286, p289) — all still written for two chillers.
  - **p473** still carries the 2025 "left chiller decommissioned" note, now superseded.
  **Also worth knowing:** the v1.7 glossary entry for SCALA was already wrong before this pass —
  it described SCALA as "chiller sequencing" when the walkthrough correctly had it as the booster
  pump leak pan. And **the leak pan is now genuinely unmonitored**, since that input became CHIL;
  v1.8 states this explicitly in the CHIL entry.
- The standing **GPIO 26 dead-pad** carryover in `CLAUDE.md` is now **moot rather than pending** —
  it only mattered because YOFF needed that pin, and YOFF is retired. The pad is still dead on the
  current Pi; it simply no longer blocks anything. `CLAUDE.md` and the session-state notes still
  carry it as a "rewire before heating season" action item and should be corrected.
- Unrelated but adjacent: this is the natural moment to add the **cooling fan** to the Pi enclosure
  that the Sentry thermal work called for.
