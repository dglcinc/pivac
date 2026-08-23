# Chiltrix CX75 Modbus Bring-Up — Runbook

**Status:** In progress. The link does not communicate yet; the cause is identified and the fix
is untested. · **Owner:** David · **Machine: the M2** (the UNO R4 and the sketches live there)

Self-contained on purpose. A session picking this up needs no prior conversation.

---

## 1. Where this stands

**The goal** is to poll the chiller directly over Modbus RTU from an UNO R4 WiFi, so
`pivac.Chiltrix` can eventually publish inlet/outlet water temperatures, the real part-load
evaporator ΔT and pump speed. Those are the numbers that decide whether `P59` needs touching
before the return-water target can go below 50 °F.

**What is confirmed, and needs no re-checking:**

- **Terminals.** The CX75's BMS port is connector **`P6`** on the main control PCB: top to bottom
  **`DA1` `DA2` `GND`**. Verified against the board silkscreen 2026-08-23, matching the CX65
  hi-res diagram. Landed as **blue → `DA1` (A/+), white → `DA2` (B/−), cable drain → `GND`**,
  drain at the chiller end only. `P6` is separate from `P4` (the wired controller), so polling
  cannot disturb the controller.
- **COM settings.** Chiltrix's ProtoAir guide fixes them: **Modbus RTU, 9600, parity None, 8 data,
  1 stop**, and confirms the chiller is a plain **Modbus RTU slave** — a direct master is
  legitimate, no gateway needed. Node-ID for a single chiller is "usually 1".
- **Cable.** 50 ft of 22 AWG shielded. At 9600 baud that is nothing; RS-485 runs 4000 ft at that
  rate. Length is not a factor and **no terminator is required**.

**What has been ruled out:**

| Suspect | Result |
|---|---|
| A/B polarity | swapped at the Arduino end, no change |
| Wrong terminals | verified against the board silkscreen |
| Parity / framing config | vendor doc fixes 8N1; the sketch already uses `SERIAL_8N1` |
| A Modbus parameter on the CX | the **entire `P00`–`P119` table** was read — no address, baud, Node-ID or comms-enable setting exists |
| `SW1` on the main board | it is the **compressor model encode** (`C38`), nothing to do with comms |
| Ground-potential difference | common mode measures 60 mV; a real offset would be volts |
| Wrong serial port on the R4 | sketches already use `Serial1` (`Serial` is USB CDC on the R4) |

> **⚠️ Do not touch `SW1`.** It encodes which compressor is fitted. As found: **1 off, 2 on,
> 3 off, 4 on.** Read `C38` on the panel to see the encoded value.

## 2. The cause, and the fix to test

**The RS-485 pair has no fail-safe bias, from either end.** Measured at the Arduino end:
**A−B ≈ 10 mV**, with **A and B each ≈60 mV to the drain**. Both conductors sitting *together* at
the same small potential is a floating, undriven line — a biasing transceiver would put A and B
**volts** apart from ground, typically A ≈3 V and B ≈2 V.

10 mV is far below the **200 mV RS-485 receiver threshold**, so the receiver's output is undefined
and free-runs on noise, inventing start bits that destroy the framing of any reply. Slaves do not
bias a bus; the master is supposed to, and the **DFR0259 shield has no bias network**. Its AUTO
mode tri-states the driver between frames, which the 10 mV confirms.

**Fit two resistors at the Arduino end:**

```
   +5 V ──[ 680 Ω ]── A   (DA1, blue)
    GND ──[ 680 Ω ]── B   (DA2, white)
```

560 Ω–1 kΩ all work. **Polarity matters**: pull-up on A, pull-down on B. Reversed damages nothing
but inverts the idle state, so every frame reads as a break condition — worse than now, while
measuring a healthy differential.

**No chiller-panel work is needed**, which keeps the 240 V side shut. There is no risk to the
chiller: 5 V through 680 Ω sources at most 7.4 mA into a dead short, against receiver inputs rated
−7 V to +12 V common mode.

**Still fit no terminator.** 120 Ω across a pair you are trying to bias fights the resistors —
Chiltrix's own gateway guide says the termination resistor "would override the effect of any bias
resistors if connected."

### Verify before running anything

Meter on **DC volts** across A/B. **It must jump from 10 mV to volts.** Unterminated, the divider
is lightly loaded, so expect **1–4 V** rather than the textbook 400 mV. Anything well above 200 mV
passes. Still tens of millivolts means a resistor is not landing where you think it is.

## 3. Flash and run

Sketches: `~/OneDrive - DGLC/Claude/chiltrix-sketches/` — `ChiltrixScan` (interactive scanner) and
`ChiltrixModbus` (the eventual HTTP bridge). `arduino-cli` is at `/opt/homebrew/bin` with the
`renesas_uno` core.

**Shield: DFR0259, both DIP switches AUTO and ON.** Set the ON/OFF switch to **OFF while
uploading** — with it ON the shield sits on D0/D1 and blocks the upload. Flip back to **ON** to run.

```bash
cd ~/OneDrive\ -\ DGLC/Claude/chiltrix-sketches/ChiltrixScan
arduino-cli board list                      # find the port
arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi .
arduino-cli upload -p <PORT> --fqbn arduino:renesas_uno:unor4wifi .
arduino-cli monitor -p <PORT> -c baudrate=115200
```

The console is **115200**; the Modbus link is on `Serial1` at the swept baud, independent of it.

### Run capital `P`, not lowercase `p`

> **⚠️ Lowercase `p` probes slave id 1 ONLY** (across all seven bauds). **Capital `P` sweeps ids
> 1–32.** The previously documented `d` → `p` → `k` order therefore never tested another address,
> which makes a present-but-unfound device indistinguishable from a dead bus. Node-IDs are legal to
> 255, so even 1–32 is not exhaustive.

`P` takes minutes. **Capture the whole transcript** — the result codes are the diagnosis.

## 4. Reading the outcome

The sketch prints a result code per attempt. Three branches:

**It responds.** Note the baud and id it reports, then run **`k`** — the known-value checks in §5.

**`0xE3` / "CRC errors" appear where there were none.** Real progress: bytes are arriving, so the
chiller is alive and transmitting, and it is now a baud or framing problem. Let the sweep finish;
it tests seven bauds.

**Still a flat "no" across all 32 ids × 7 bauds.** Nothing is arriving at all, which bias alone
does not explain. Next test, no scope needed: put the meter on **AC volts** across A/B and run `P`
again. While the Arduino transmits, AC should read clearly non-zero. **If it stays at 0 through
the whole sweep, nothing is leaving the DFR0259** — the fault is the shield or its DIP switches,
not the chiller. That cleanly splits "my end is mute" from "its end is mute".

## 5. Once it answers — verify registers before trusting any of them

> **⚠️ The two community register maps contradict each other.** jasipsw (CX50-2) and gonzojive
> (CX34) disagree on nearly every address and **neither covers a CX75**. Every register must be
> checked against the panel before use. The sketch is **read-only, function code 3 exclusively** —
> keep it that way; writing to a misidentified register on a running chiller is how you break it.

`k` runs the checks that settle it. The shortcut worth trying first: in the CX34 map **register 53
is `P53`**, so if parameter numbers are register addresses, **register 53 reads 40** (the pump
minimum speed). If that matches, try 59 (`P59`, expect 30 = 3.0 °C), 65 (`P65`, expect 20 L/min)
and 109 (`P109`, expect 1).

Then cross-check the live values against the panel: **`C13`** is the water-flow readout — compare
it against registers 257 and 213, which the CX50-2 and CX34 maps each claim is flow. **`C13` reads
0 at idle and that is normal**; the pump only runs during a call, and the 1–2 minute pump-only
window at the start of each run is when to read it.

Registers 202/203 are the inlet/outlet water temperatures in the CX50-2 map — the pair the whole
exercise is for, since their difference is the real part-load evaporator ΔT.

## 6. After it works

1. Commit both sketches to `~/github/Arduino` — they exist only on the M2 and in OneDrive.
2. **Re-capture the `.114` DHW recirc sketch** while on that machine; it is uncommitted and exists
   nowhere else, and flashing the repo's psi-only sketch onto that board would silently drop
   `environment.inside.hvac.dhw.recirc.temperature`.
3. Record the verified register map in `docs/unico-cooling-assessment-and-tuning.md` §4.2 (PR #117).
4. Then `pivac.Chiltrix` becomes writable against a map that is known rather than guessed.
