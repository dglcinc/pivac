# CDP Relay + RPi Label Rework — single-chiller conversion

**Status:** plan only, nothing built or rewired.
**Date:** 2026-07-23
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

## 1. Current state

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

**Decisions taken (2026-07-23):** CHIL keeps **RCHL's** pin so the in-service chiller call wire
never moves. YOFF stays on **BCM 26 / pin 37** — the dead pad was the old Pi's silicon, and the
new board starts clean.

| Row | New label | BCM | Phys | Action |
|----:|-----------|----:|-----:|--------|
| 1 | ZV | 17 | 11 | unchanged |
| 2 | DHW | 27 | 13 | unchanged |
| 3 | BLR | 22 | 15 | unchanged |
| 4 | **CHIL** | 5 | 29 | **rename only — no wire move** |
| 5 | **BOS2** | 6 | 31 | **rename only** — relay reclaimed in place, existing contact wire reused |
| 6 | UNUSED | 13 | 33 | **freed** — pull wire at header + relay |
| 7 | **YOFF** | 26 | 37 | **rename only** (typo fix) — no wire move; re-enable in config |
| 8 | UNUSED | 16 | 36 | **freed** — pull wire at header + relay |
| 9 | DEHUM | 12 | 32 | unchanged |
| 10 | SCALA | 25 | 22 | unchanged (fill in on the docx) |
| 11 | BOS1 | 24 | 18 | unchanged (fill in on the docx) |
| 12 | UNUSED | 23 | 16 | unchanged — remains a true spare, still unwired |

**Net effect:** 9 active inputs, 3 spare (BCM 13/33, 16/36, 23/16).
**Wire movement at the header: zero.** Two pulls (Y2ON, Y2FAN), no new header runs, no relocations.

> **Why BOS2 lands in LCHL's slot rather than the never-used pin 16.** The LCHL relay is being
> reclaimed for BOS2 anyway (§3), and its dry contact **already has a wire run to header pin 31**.
> Leaving both the relay and that wire in place means the only new conductor in the whole job is the
> BOS2 call signal into the relay coil — which is needed no matter which pin is chosen. Pin 16 has
> never been wired, so siting BOS2 there would add a contact-to-header run for nothing. Cost of this
> choice: BOS1 (row 11) and BOS2 (row 5) are non-adjacent on the label. That is cosmetic, and it
> loses to saving a wire run.

---

## 3. Relay hardware

### Removed / reclaimed

| Relay | Disposition | Reason |
|-------|-------------|--------|
| **LCHL** | **Reclaim in place → BOS2 sensing** | Plain N/O relay, same type as RCHL/BOS1 — and its contact wire to pin 31 is reused as-is |
| **Y2ON** | Remove or spare | 4-min **timer** relay; not suitable as plain sensing unless set instantaneous |
| **Y2FAN** | Remove or spare | Staging no longer needed |
| **YALT** | **Remove entirely** | Alternation is meaningless with one chiller |

Reclaiming the **LCHL** relay for BOS2 means no new relay hardware is needed. Leaving it in its
existing rail position — rather than moving it — is what lets its contact-to-header wire stay
untouched, and keeps the DIN layout dense with no shuffling.

### Control-logic consequences — **verify at the panel before cutting**

These follow from the v1.7 manual's CDP Relays Walkthrough. They are inferences from documentation,
not from tracing live wiring, so confirm each one physically (ideally with your HVAC contractor):

1. **YALT removal breaks the chiller call path.** The manual states YALT "uses lead and lag calls
   from the zone controller, CWRA, and Y2 relays to energize the chiller relays." With YALT gone,
   whatever fed YALT must now drive **CHIL** directly.
2. **YOFF's interrupt point moves.** Today YOFF "opens a N/C contact to disable power to YALT and
   the CWRA." With YALT removed, YOFF must interrupt the **new direct chiller call path** instead,
   or the seasonal cutoff silently stops working. This is the single highest-risk item in the
   rework — a YOFF that no longer cuts the call will let the chiller run in winter.
3. **Two-stage staging disappears with Y2ON/Y2FAN.** Confirm the new chiller either handles its own
   staging internally or genuinely doesn't need it. If it does need an external stage-2 call, stop
   and re-plan — one of the freed inputs would have to come back.
4. **CRWA / CWRA aquastat.** Confirm whether the return-water aquastat still gates the new chiller,
   and if so where it sits in the simplified path.

### BOS2 sensing

BOS2's compressor call currently runs direct to the Bosch unit. Route it through the reclaimed
LCHL relay exactly as BOS1 is done: the call energizes the relay coil, and the relay's **dry
contact** feeds the Pi input — which, because the relay stays put, is the **existing wire to
BCM 6 / physical pin 31**, pulled up internally (`pullmode: pullup`, matching every other input).

The only new conductor is the BOS2 call signal from the Bosch unit into the relay coil, replacing
the old chiller call that drove it. Do not feed 24 VAC anywhere near the header.

---

## 4. Label (`docs/PhoenixContact-BC-RPI-label.docx`)

Twelve single-token text swaps against the table in §2, plus the two catch-up fills (rows 10/11).
No layout change — the label is already sized to fit under the Phoenix Contact clear cover, and
row count is unchanged.

The trailing `6489705080` on the label is, per the manual, the Pi's MAC address. **It will be wrong
on the new Pi** — capture the new board's `eth0` MAC during the build and update it in the same
edit. (For reference the current Pi's `eth0` is `d8:3a:dd:b1:ad:4d`.)

Mechanics: `.docx` is a zip; the edit is a targeted swap in `word/document.xml` then rezip. No
`python-docx` needed for text-only changes.

---

## 5. Software

### 5.1 `pivac.GPIO` config

Live file is `/etc/pivac/config.yml` on the Pi. Under `pivac.GPIO: inputs:`

- `5:` — `outname: RCHL` → **`CHIL`**
- `6:` — `outname: LCHL` → **`BOS2`**
- `13:` — **delete** (Y2ON)
- `16:` — **delete** (Y2FAN)
- `26:` — **uncomment / re-enable**, `outname: YOFF` (disabled while the old pad was dead)
- leave `17 ZV`, `27 DHW`, `22 BLR`, `12 DEHUM`, `25 SCALA`, `24 BOS1` untouched
- `23:` is **not** added — it stays an unconfigured spare

Both chiller-slot changes are pure `outname` renames; no pin numbers move.

Then `sudo systemctl restart pivac-gpio`.

Also bring **`config/config.yml.sample`** in this repo up to date — it currently lacks BOS1 and
SCALA and still lists the retired chiller inputs, so it no longer reflects reality.

### 5.2 Signal K path churn

Paths are `electrical.ac.switch.utility.{NAME}.{state,statenum}`. Retiring Y2ON / Y2FAN and
renaming RCHL → CHIL and LCHL → BOS2 means:

- `…RCHL.state` and `…LCHL.state` **stop updating**; `…CHIL.state` and `…BOS2.state` start fresh
  with no history. Note LCHL → BOS2 is a rename at the *pin*, not a continuation of meaning — the
  new series measures a different piece of equipment, so the break in history is correct here.
- The existing InfluxDB series stay on disk as the historical record of the old chillers. **Nothing
  is deleted** — this is the same naming-vs-history tradeoff as the inverted Arduino module names,
  and here the clarity of `CHIL` is worth the break since the hardware genuinely changed.

### 5.3 Grafana

Two dashboards reference the retired names and will show dead series otherwise:

- **`grafana/dashboards/pivacr.json`** — refs to `Y2ON` ×2, `Y2FAN` ×2, `RCHL` ×2, `LCHL` ×1,
  `BOS1` ×3. Drop the Y2ON/Y2FAN series, repoint RCHL → CHIL and LCHL → BOS2, and group BOS2 with
  BOS1 rather than leaving it where the old chiller series sat.
- **`grafana/dashboards/chiller-time-r.json`** — refs `RCHL`, `LCHL`, `BOS1`. This dashboard's whole
  premise is per-chiller runtime across two units; with one chiller it needs a genuine rework, not
  a rename. Consider recasting it as *cooling* runtime: CHIL + BOS1 + BOS2.

Keep the PivacR panel conventions: `custom.axisWidth: 50`, no per-panel `axisLabel`, and boolean
relay state as a **stepped-line timeseries** rather than a state-timeline (which can't align its
row-label width).

### 5.4 WilhelmSK

`iphone.wlyt` has a SwitchBank on both pages. A plain-text grep for the relay names found no
matches, so the bank likely references SK paths in an encoded form — **check it on-device** after
the config change and re-point or remove the retired switches. Layout file lives at
`~/OneDrive - DGLC/Claude/iphone.wlyt`.

### 5.5 Alerting

No Grafana alert rule references the relay paths (the freshness rules cover temps, pressures, and
water only), so **no alerting changes are required**. Worth considering afterward: a freshness rule
on `CHIL` would catch a failed new-chiller call, which nothing currently watches.

---

## 6. Sequencing

Do the software prep before the panel is opened, so the new Pi boots into a correct config and you
aren't debugging YAML with the panel in pieces.

1. **Bench, before touching the panel**
   a. Update the label docx (§4), leaving the MAC as a placeholder.
   b. Update `config.yml.sample` + the two Grafana dashboards (§5.1, §5.3); commit on a branch.
   c. Build the new Pi: image from the weekly `sd-clone` spare or a fresh install, then restore
      `/etc/pivac/config.yml` and apply the §5.1 edits. Record the new `eth0` MAC.
   d. **DHCP-reserve the new MAC to `10.0.0.82` in UniFi** — the nginx port-forwards and every
      external URL depend on that address.

2. **Panel work, power off**
   a. Photograph the panel and label every wire before removing anything.
   b. **Ohm the YOFF wire (pin 37) to ground with it unplugged** — this is the pre-flight for
      reusing BCM 26. If it reads shorted, the wire killed the old pad, not the power event: stop
      and move YOFF to BCM 19 / pin 35 instead.
   c. Pull the Y2ON and Y2FAN wires from header pins 33 and 36. **Leave pin 31 alone** — that wire
      is being reused for BOS2.
   d. Remove YALT; rewire the chiller call path to drive CHIL directly (§3, item 1).
   e. **Re-establish YOFF's cutoff on the new path** and prove it (§3, item 2).
   f. Reclaim the LCHL relay in place for BOS2: disconnect the old chiller call from its coil and
      land the BOS2 compressor call there instead. Its contact wire to **pin 31** is untouched.
   g. Fit the new Pi and the updated label.

3. **Verify**
   ```bash
   python -c "import pivac.GPIO as m, json; print(json.dumps(m.status(), indent=2))"
   ```
   Expect exactly 9 inputs, no LCHL/Y2ON/Y2FAN, `CHIL` present, `BOS2` present, `YOFF` present.
   Then: force a cooling call and confirm CHIL asserts; run the Kitchen and Living Room zones
   independently and confirm BOS1 and BOS2 assert separately; **throw YOFF and confirm the chiller
   call actually drops**; confirm all nine appear in Grafana and WilhelmSK.

4. **Document** — update `CLAUDE.md` (relay roster, the retired-name/InfluxDB note, the resolved
   GPIO 26 item) and the HVAC System Manual's CDP Relays Walkthrough, which still describes LCHL,
   RCHL, Y2ON, YALT and two chillers.

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
- Confirm the new chiller needs no external stage-2 call before the Y2ON/Y2FAN inputs are freed.
- Decide the fate of the freed Y2ON timer and Y2FAN relays (spares vs. removal) — no impact on
  the Pi side either way.
- The standing **GPIO 26 dead-pad** carryover in `CLAUDE.md` is resolved by the new Pi, contingent
  on step 2b passing.
- Unrelated but adjacent: this is the natural moment to add the **cooling fan** to the Pi enclosure
  that the Sentry thermal work called for.
