# OpenSprinkler "Gallons" UI Fork — Scoping

**Status:** scoping only (no code written). Optional/cosmetic — see "Do we even need this?".
**Date:** 2026-06-21
**Device:** OpenSprinkler 3.2 (`hwv=32`, ESP8266, MAC `B4:E6:2D:6A:03:7B`), firmware **2.2.1(3)** (`fwv=221, fwm=3`), at `10.0.0.17:5000`.
**Meter:** DAE AS200U-75P, **1 gal/pulse**, on SN1. Device `fpr` kept at **1.00** (`fpr0=100, fpr1=0`).

---

## Goal

Make a **self-hosted OpenSprinkler web UI** display irrigation flow in **gallons** (correct numbers *and* a "gal" label), instead of the upstream UI's hard-coded liters — without touching device firmware or our pivac/Grafana pipeline.

## Do we even need this? (read first)

Probably not, strictly:

- **pivac / Grafana / WilhelmSK already show real gallons** and are firmware-confirmed independent of any OS unit setting (the proxy pivac reads, `flcrt`, is a raw pulse frequency computed before `fpr` is applied).
- With device `fpr=1.00` and the meter at 1 gal/pulse, **every number the OS app shows is already a gallon value** — it's only *labeled* "L". The working "read L as gal" convention gives correct gallon magnitudes today.

So this fork buys **only a cosmetically-correct label** in the *browser* UI. It does **not** change the mobile app (which bundles its own UI — see caveats). Worth doing only if the "L" label genuinely bothers you. The better long-term play is the **upstream PR** in "Maintenance" below.

---

## Root cause (why the OS app shows liters)

Confirmed against the source ([OpenSprinkler/OpenSprinkler-App](https://github.com/OpenSprinkler/OpenSprinkler-App), `www/js/modules/`). Three independent facts:

1. **The firmware stores no unit.** It keeps `fpr` (pulse rate) as a bare number and the API always reports flow in SI. Unit handling is 100% in the UI.
2. **The flow displays hard-code "L" and ignore the app's own metric flag.** There *is* a "Use Metric" toggle (`OSApp.currentDevice.isMetric`, persisted to localStorage — `options.js:181-183, 403-404, 1042-1044`), used 9× in `options.js` for temperature/elevation/etc., but it is referenced **zero times** in `status.js` and `logs.js`. The flow strings are literal `" L/min"` / `" L"`.
3. **The pulse-rate dropdown silently converts gal→L on save, and never persists.**
   - `options.js:250-251`: if the unit dropdown is "gallon", `data = data * 3.78541` before storing → entering `1 gal/pulse` writes `fpr ≈ 3.78`. (This is the `1.00 → 3.78` we observed.)
   - `options.js:674`: the `<option value='liter'>` is hard-coded `selected='selected'` on every render → the dropdown **always snaps back to L/pulse** after save (matches the observed behavior). The "gallon" choice is not stored anywhere on the device.

### The conversion linchpin
`OSApp.Utils.flowCountToVolume(count)` (`utils.js:159`):
```js
return parseFloat( ( count * ( ( fpr1 << 8 ) + fpr0 ) / 100 ).toFixed( 2 ) );  // = count × fpr
```
With our `fpr = 1.00`, this is the identity: **volume = pulse count = gallons**. So the numbers are already right; only labels are wrong.

---

## Where the units live (patch surface)

| File:line | What it renders | Current | Notes |
|---|---|---|---|
| `www/js/modules/status.js:72` | Realtime flow on dashboard | `flowCountToVolume(flcrt)/(flwrt/60) + " L/min"` | fpr-aware via `flowCountToVolume`; with fpr=1 → gal/min |
| `www/js/modules/logs.js:427` | Per-run flow rate in log table | `fRate.toFixed(2) + " L/min"` | `fRate` = `/jl` 5th field (already volume/min) |
| `www/js/modules/logs.js:489` | "Total Water Used: N L" | `... + stats.totalVolume + " L"` | `totalVolume` = Σ `flowCountToVolume(count)` (`logs.js:202`) |
| `www/js/modules/logs.js:494` | "(N L saved)" water-level note | `... + "L saved" ...` | same units |
| `www/js/modules/options.js:250-251` | gal→L conversion on save | `data *= 3.78541` | only relevant under Strategy B |
| `www/js/modules/options.js:674` | dropdown default | `liter` hard-selected | only relevant under Strategy B |

`isMetric` toggle plumbing already exists in `options.js` (181-183, 403-404, 1042-1044) — the fix is to *consume* it in the flow displays.

---

## Fix strategies

### Strategy A — relabel only (recommended for this install)
**Premise:** keep device `fpr = 1.00` (value `1`, leave dropdown on L/pulse). Then all computed flow numbers are already gallons; we only fix labels, gated on the existing "Use Metric = off" (imperial).

Changes (≈4 string sites, no arithmetic):
- `status.js:72` — `" L/min"` → `( OSApp.currentDevice.isMetric ? " L/min" : " gal/min" )`
- `logs.js:427` — same conditional
- `logs.js:489` — `" L"` → `( isMetric ? " L" : " gal" )`
- `logs.js:494` — `"L saved"` → conditional

**Pros:** tiny diff (~4–6 lines), no conversion math, matches current device state, lowest risk.
**Cons:** correct *only* because our meter is exactly 1 gal/pulse and `fpr=1`. Not a general fix; don't change `fpr` away from 1.00.

### Strategy B — general, unit-aware (upstream-quality)
Make the UI truly unit-aware so it's correct for any meter:
- Store the *true* metric rate (`fpr=3.785` for a 1 gal/pulse meter) so the API/SI values are physically correct liters.
- In `status.js` / `logs.js`, divide volume by `3.78541` and label "gal" when `!isMetric`.
- Persist the pulse-rate unit dropdown (fix `options.js:674` to select based on a stored preference) and make `options.js:250` round-trip correctly.

**Pros:** correct for any meter; this *is* the real upstream bug fix.
**Cons:** more code + conversion math in several spots; must re-derive our calibration math; more test surface. Overkill for a single 1-gal/pulse install.

> **Recommendation:** Strategy A for our own self-host. If we touch this at all, also open the Strategy-B fix as an upstream PR (see Maintenance) so we can eventually drop the fork.

---

## Hosting approaches

### (a) Standalone hosted app on the Pi — recommended
The OpenSprinkler web UI is plain static files (`www/`, JS is **not** minified/transpiled — served as-is). app.opensprinkler.com is exactly this UI hosted standalone; it connects to a controller you point it at. So:

- Serve the patched `www/` from nginx on the Pi (we already run nginx).
- Browse to e.g. `https://68lookout.dglc.com/os-ui/` (or a LAN path), add controller `10.0.0.17:5000` with the device password.
- **No device-side change needed** — this entirely sidesteps the option-write quirk below.

### (b) `jsp` injection (device-served page) — not recommended here
Firmware ≥2.0.3 serves a bootstrap page that loads the UI from the `jsp` base URL (currently `https://ui.opensprinkler.com/js`). Repointing `jsp` at our copy makes `http://10.0.0.17:5000` itself serve the patched UI.

**Blocker/caveat:** we observed that **option writes via the `/co` API do not persist on this unit** (benign `dim` test returned `result:1` but never changed; only `/dl` log-clear persisted). The `jsp` change uses `/cu?pw=...&jsp=...` and may hit the same wall; the app's own option writes *do* persist, so it'd have to be set through the app if it exposes a JS-path field. Approach (a) avoids all of this.

---

## Build & deploy steps (Strategy A + hosting (a))

```bash
# 1. Fork + clone
gh repo fork OpenSprinkler/OpenSprinkler-App --clone
cd OpenSprinkler-App
git checkout -b gallons-display   # pin to a tag matching fw 2.2.1 if exact parity matters

# 2. (optional) run the dev server to iterate
npm install && npm start          # http://localhost:8080

# 3. Apply Strategy-A label edits in:
#    www/js/modules/status.js, www/js/modules/logs.js

# 4. Deploy static files to the Pi (no build needed for the JS)
rsync -a www/ pi@10.0.0.82:/var/www/os-ui/
```

nginx (`/etc/nginx/sites-available/pivac`), add a location:
```nginx
location /os-ui/ {
    alias /var/www/os-ui/;
    index index.html;
    # auth_basic as desired; this UI talks to the LAN controller, holds no secrets itself
}
```
```bash
sudo nginx -t && sudo systemctl reload nginx
```

Then open `https://68lookout.dglc.com/os-ui/`, add controller `10.0.0.17:5000`, and **uncheck "Use Metric"** in Edit Options so the patched labels render as gal.

> Mixed-content note: an HTTPS-served UI talking to an HTTP controller (`10.0.0.17:5000`) can trip browser blocking. If so, either serve the UI over plain HTTP on the LAN, or front the controller through an HTTPS proxy (we already proxy `/sprinkler/` → `10.0.0.17:5000` in nginx — the UI could target that path).

---

## Testing / validation

1. Load the patched UI, confirm dashboard realtime flow reads "gal/min" (0.00 when idle).
2. Run one zone; confirm the realtime number ≈ pivac's gal/min and the meter (~5.5 gpm on the calibrated zone).
3. After the run, confirm the log table shows "gal/min" and "Total Water Used: N gal", with N ≈ the meter delta and ≈ Grafana's Irrigation "Used".
4. Cross-check against `/jc` `flcrt` and pivac's InfluxDB integral (the known-good 983.9 ≈ 984 baseline).

## Effort & risk

- **Effort:** Strategy A ≈ 1–2 h (edit + host + test). Strategy B ≈ a half-day incl. round-trip math + dropdown persistence.
- **Risk:** low — read-only UI layer; no firmware flash, no device config change under hosting (a). Worst case the UI misrenders; revert by using the stock cloud UI. pivac/Grafana untouched throughout.

## Maintenance & upstream recommendation

- A self-hosted fork **drifts** from upstream; re-apply the patch (or re-fork) on app updates.
- **Best path:** the genuine bug is that `status.js`/`logs.js` ignore the existing `isMetric` flag for flow. A small PR making those four sites unit-aware (Strategy B) is squarely upstreamable and benefits everyone — and lets us **delete the fork** once merged. If we invest at all, invest there.

## Decision

Default: **don't fork** — keep `fpr=1.00`, read the OS app's "L" as gallons, rely on Grafana/WilhelmSK for true gallons. Fork only if the label is a persistent annoyance; if so, do **Strategy A + hosting (a)**, and consider opening the **Strategy-B upstream PR** to retire the fork.
