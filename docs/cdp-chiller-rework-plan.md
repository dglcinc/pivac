# CDP Relay + RPi Label Rework — single-chiller conversion

**Status:** partially executed.
**Date:** 2026-07-23, revised 2026-08-10 to match what actually shipped.

> **⚠️ The naming scheme in the original plan was superseded before it was built.** This plan
> specified `RCHL→CHIL` and `LCHL→BOS2`. What actually shipped on 2026-08-02 was
> **`RCHL→BOS2`** and **`LCHL→BOS1`**, with **no `CHIL` relay at all** — the new chiller does not
> work in a way that gives it a call relay, so its call state is deliberately unmonitored. The old
> `BOS1` on BCM 24 was dropped in favour of the reclaimed relay. Sections 2–6 below have been
> rewritten to the shipped scheme; the original is recoverable from this file's git history.

**What is done:** the chiller conversion itself (two UniChillers → one Chiltrix CX75, 2026-08),
and the `pivac.GPIO` software side — live on the Pi and verified, with the repo-side changes
(`config.yml.sample`, README, both Grafana dashboards, CLAUDE.md) carried by **PR #96**.

**What is outstanding:** the CDP panel wiring detail behind the reclaimed relays, the label
reprint (§4), the new-Pi build (§6), and the YOFF re-enable. **The panel-side coil wiring state is
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

**Decisions as shipped (2026-08-02):** both old chiller relays were reclaimed **in place** as Bosch
compressor monitoring inputs — no header wire moved. **There is no `CHIL` relay**: the new chiller
provides no call contact to sense, so the chiller's own call state is not monitored at all. That is
a deliberate accepted loss, not an oversight, and is the single biggest functional difference from
the original plan — see §3.

YOFF: this plan assumes the **new Pi**, whose silicon is clean, so YOFF can stay on **BCM 26 /
pin 37**. Note this differs from the *current* Pi's pending fix, which is to move YOFF to
**BCM 19 / phys 35** because BCM 26's pad is dead (see `CLAUDE.md`). Whichever Pi is in service
when the rewire happens decides which applies.

| Row | New label | BCM | Phys | Action |
|----:|-----------|----:|-----:|--------|
| 1 | ZV | 17 | 11 | unchanged |
| 2 | DHW | 27 | 13 | unchanged |
| 3 | BLR | 22 | 15 | unchanged |
| 4 | **BOS2** | 5 | 29 | **rename only** (was RCHL) — relay reclaimed in place, contact wire reused |
| 5 | **BOS1** | 6 | 31 | **rename only** (was LCHL) — relay reclaimed in place, contact wire reused |
| 6 | UNUSED | 13 | 33 | **freed** — pull wire at header + relay |
| 7 | **YOFF** | 26 | 37 | **rename only** (typo fix) — no wire move; re-enable in config |
| 8 | UNUSED | 16 | 36 | **freed** — pull wire at header + relay |
| 9 | DEHUM | 12 | 32 | unchanged |
| 10 | SCALA | 25 | 22 | unchanged (fill in on the docx) |
| 11 | UNUSED | 24 | 18 | **freed** — the old BOS1 input, superseded by row 5 |
| 12 | UNUSED | 23 | 16 | unchanged — remains a true spare, still unwired |

**Net effect:** 7 active inputs today (ZV, DHW, BLR, BOS2, BOS1, DEHUM, SCALA), 8 once YOFF is
re-enabled. Spares: BCM 13/33, 16/36, 24/18, 23/16 — one more than the original plan produced,
because dropping CHIL frees a slot.

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

> **No relay senses the chiller.** With CHIL dropped, nothing in the CDP observes whether the
> chiller is being called. Everything the Pi reports about cooling is now inferred from the two
> Bosch compressor calls and the buffer-tank temperatures (UBT/LBT), not from the chiller itself.
> Revisit if the CX75 turns out to expose a usable dry contact.

### Control-logic consequences — **verify at the panel before cutting**

These follow from the v1.7 manual's CDP Relays Walkthrough. They are inferences from documentation,
not from tracing live wiring, so confirm each one physically (ideally with your HVAC contractor):

1. **YALT removal breaks the chiller call path.** The manual states YALT "uses lead and lag calls
   from the zone controller, CWRA, and Y2 relays to energize the chiller relays." With YALT gone,
   whatever fed YALT must now drive the **new chiller** directly.
2. **YOFF's interrupt point moves — and nothing watches the result.** Today YOFF "opens a N/C
   contact to disable power to YALT and the CWRA." With YALT removed, YOFF must interrupt the
   **new direct chiller call path** instead, or the seasonal cutoff silently stops working. This
   is the single highest-risk item in the rework — a YOFF that no longer cuts the call will let
   the chiller run in winter. **Dropping CHIL made this worse:** with no relay sensing the chiller
   call, there is no dashboard signal that would reveal a failed cutoff. It can only be proven
   physically, at the panel, before the panel is closed. Do not defer this to "we'll see it in
   Grafana" — you will not.
3. **Two-stage staging disappears with Y2ON/Y2FAN.** Confirm the new chiller either handles its own
   staging internally or genuinely doesn't need it. If it does need an external stage-2 call, stop
   and re-plan — one of the freed inputs would have to come back.
4. **CRWA / CWRA aquastat.** Confirm whether the return-water aquastat still gates the new chiller,
   and if so where it sits in the simplified path.

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
| 7 | `Y2OFF` | `YOFF` (typo fix) |
| 8 | `Y2FAN` | `UNUSED` |
| 10 | *(blank on the docx)* | `SCALA` |
| 11 | `BOS1` | `UNUSED` |

Row 11 is the one to watch: the repo's docx shows it blank, the *printed* label shows `BOS1`, and
it now becomes `UNUSED` because that input was retired. Whichever copy you edit, the end state is
`UNUSED`.

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
- `26:` — **still commented out**; re-enable as `outname: YOFF` when the pad question is settled
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

The original plan noted that a freshness rule on `CHIL` would catch a failed new-chiller call.
**That option died with CHIL** — there is no chiller relay to watch. If chiller-failure detection
is wanted, it now has to come from the process side rather than the call side: a rule on the
buffer-tank probes (`environment.inside.hvac.{UBT,LBT}.temperature` failing to fall during a
cooling call) is the natural substitute, but it is genuinely harder to get right than a relay
freshness check and has not been designed.

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
   b. **Ohm the YOFF wire (pin 37) to ground with it unplugged** — this is the pre-flight for
      reusing BCM 26. If it reads shorted, the wire killed the old pad, not the power event: stop
      and move YOFF to BCM 19 / pin 35 instead.
   c. Pull the Y2ON and Y2FAN wires from header pins 33 and 36, and the retired old-BOS1 run from
      pin 18. **Leave pins 29 and 31 alone** — those wires are being reused for BOS2 and BOS1.
   d. Remove YALT; rewire the chiller call path to drive the new chiller directly (§3, item 1).
      No relay senses this path.
   e. **Re-establish YOFF's cutoff on the new path and prove it physically** (§3, item 2). There
      is no telemetry that will confirm this later.
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
   Expect exactly **7 inputs** (ZV, DHW, BLR, BOS2, BOS1, DEHUM, SCALA), or 8 with YOFF re-enabled
   — and no LCHL/RCHL/Y2ON/Y2FAN. If any retired name is still present in the **Signal K API**
   rather than the module output, that is the missing `restart signalk` (§5.2), not a config fault.

   Then: **run the Kitchen and Living Room zones independently and confirm BOS1 and BOS2 assert
   separately.** This proves each air handler's call relay landed on the right CDP relay rather
   than the two being swapped — the failure mode that a config-only rename cannot distinguish.
   Finish by throwing YOFF and confirming the chiller call physically drops at the panel.

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

---

## 8. Open items

- **The YOFF interrupt path is the one that can bite.** Everything else fails visibly; a broken
  seasonal cutoff fails silently until winter. Prove it before closing the panel.
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
- **The chiller is no longer monitored at all.** CHIL was dropped because the CX75 exposes no call
  contact. Revisit if that turns out to be wrong; otherwise decide whether a buffer-tank-based
  substitute (§5.5) is worth building.
- Confirm the new chiller needs no external stage-2 call. The Y2ON/Y2FAN inputs are **already
  freed in software**, so if an external stage-2 call turns out to be needed, one has to come back.
- Decide the fate of the freed Y2ON timer and Y2FAN relays (spares vs. removal) — no impact on
  the Pi side either way.
- Update the **HVAC System Manual's CDP Relays Walkthrough** (§6.4) — still describes two chillers.
- The standing **GPIO 26 dead-pad** carryover in `CLAUDE.md` is resolved by the new Pi, contingent
  on step 2b passing.
- Unrelated but adjacent: this is the natural moment to add the **cooling fan** to the Pi enclosure
  that the Sentry thermal work called for.
