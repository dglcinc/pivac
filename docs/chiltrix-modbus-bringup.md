# Chiltrix CX75 Modbus Bring-Up — Runbook

**Status:** The Arduino end is proven good and the chiller has never answered. The open question is
whether the `P6` BMS port is populated at all on a CX75 with no Remote Gateway fitted. · **Owner:**
David · **Machine: the M2** (the UNO R4 and the sketches live there)

Self-contained on purpose. A session picking this up needs no prior conversation.

---

## 1. Where this stands

**The goal** is to poll the chiller directly over Modbus RTU from an UNO R4 WiFi, so
`pivac.Chiltrix` can eventually publish inlet/outlet water temperatures, the real part-load
evaporator ΔT and pump speed. Those are the numbers that decide whether `P59` needs touching
before the return-water target can go below 50 °F.

**What is measured, and needs no re-checking:**

- **Terminals.** The CX75's BMS port is connector **`P6`** on the main control PCB: top to bottom
  **`DA1` `DA2` `GND`**. Verified against the board silkscreen, matching the CX65 hi-res diagram.
  Landed as **blue → `DA1` (A/+), white → `DA2` (B/−), cable drain → `GND`**, drain at the chiller
  end only. `P6` is separate from `P4` (the wired controller), so polling cannot disturb it.
- **COM settings.** Chiltrix's Remote Gateway guide fixes them: **Modbus RTU, 9600, parity None,
  8 data, 1 stop**, and describes the chiller as a plain **Modbus RTU slave**. Node-ID for a single
  chiller is "usually 1".
- **Cable.** 50 ft of 22 AWG shielded, and **continuous to the chiller**. Proven by the idle bias
  reading — see §2. At 9600 baud, length is not a factor and no terminator is required.
- **The Arduino transmits.** Driver asserting, differential on the pair, UART saturated at line
  rate. Proven by measurement in §2.
- **The receiver can resolve a bit.** Fail-safe bias is fitted and the idle differential is
  **440 mV** against a **200 mV** receiver threshold.

**What has been ruled out:**

| Suspect | Result |
|---|---|
| A/B polarity | 32 ids at 9600 in **both** polarities, under working bias — silence either way |
| Wrong terminals | verified against the board silkscreen |
| Parity / framing config | vendor doc fixes 8N1; the sketch already uses `SERIAL_8N1` |
| A Modbus parameter on the CX | the **entire `P00`–`P119` table** was read — no address, baud, Node-ID or comms-enable setting exists |
| `SW1` on the main board | it is the **compressor model encode** (`C38`), nothing to do with comms |
| Ground-potential difference | common mode measures 60 mV; a real offset would be volts |
| Wrong serial port on the R4 | sketches already use `Serial1` (`Serial` is USB CDC on the R4) |
| Missing fail-safe bias | fitted, measured, and the silence survives it |
| A mute RS-485 shield | the driver demonstrably takes the line — §2 |
| Slave id | 1–32 swept at 9600, both polarities. Ids are legal to 255, so this is not exhaustive |

> **⚠️ Do not touch `SW1`.** It encodes which compressor is fitted. As found: **1 off, 2 on,
> 3 off, 4 on.** Read `C38` on the panel to see the encoded value.

**The open question.** Not one byte has ever arrived from the far end — no reply, and no CRC error
either, at any baud or address. The wired controller at `P4` polls the chiller continuously and
successfully, so `P4` carries Modbus traffic; none of it is visible at `P6`. Two connectors sharing
one UART would show each other's traffic, so **`P6` is electrically a separate bus and nothing on
it is listening.** Chiltrix's own guide says the Remote Gateway inserts itself as master and
relegates the wired controller to a second port, which suggests the comms design assumes a gateway
is present. **A terminated, permanently silent `P6` on a gateway-less CX75 may be the designed
behaviour rather than a fault.** Settling that is what §5 is for.

> The wired controller at `P4` is the **standard CX wired controller**. It is **not** a
> Psychrologix — that is a separate Chiltrix controller, needed only for indoor Chiltrix zone
> units, which this house does not have (the indoor side is Unico air handlers on chilled-water
> coils). There is also **no Remote Gateway / ProtoAir on the network**: the UniFi client list
> carries no FieldServer, MSA or Sierra Monitor device, and no unidentified client listens on 502,
> 80, 443 or 22.

## 2. What the bench measurements establish

Fail-safe bias is fitted **at the Arduino end only**, and is required — without it the pair floats
at ~10 mV, far under the 200 mV receiver threshold, and the receiver free-runs on noise. The
DFR0259 has no bias network of its own and its AUTO mode tri-states the driver between frames.

```
   +5 V ──[ 680 Ω ]── A   (DA1, blue)
    GND ──[ 680 Ω ]── B   (DA2, white)
```

560 Ω–1 kΩ all work. **Polarity matters**: pull-up on A, pull-down on B. Reversed inverts the idle
state and is worse. **Fit no terminator** — 120 Ω across a pair you are biasing fights the
resistors, and Chiltrix's guide says termination "would override the effect of any bias resistors".

**Idle reads 0.44 V DC across A/B, and that number proves the cable.** The divider is
`V_AB = 5 × R / (1360 + R)`, so 0.44 V solves to **R ≈ 130 Ω**. The transceiver's own input
impedance is ~12 kΩ and would have left the pair above 4 V. Only a **120 Ω terminator at the far
end** loads it to 130 Ω, so the cable is continuous and lands on a terminated bus. Anything near
4 V means a conductor is not landing.

**Transmit is proven with a saturation sketch, not with an AC reading.** `RS485Blast` writes `0x55`
continuously to `Serial1` at 9600 — alternating bits, no Modbus framing, no valid CRC, so a
listening slave cannot act on any of it. Against that, the pair moves from **0.44 V to 1.085 V DC**.
A fixed resistor divider cannot produce 1.085 V; only an active driver can. The reading sits above
the bias rather than near zero because the AUTO direction circuit holds the driver asserted through
the idle gaps between bytes, adding mark time to an otherwise balanced stream.

> **⚠️ The `ON/OFF` switch and the L LED read identically to a dead shield.** The L LED is driven by
> the sketch, so it flashes whether the shield is connected to D0/D1 or not, and with the switch OFF
> the pair sits at exactly the 0.44 V bias. **LED activity is not evidence the shield is in
> circuit.** Confirm the switch position explicitly before believing any transmit measurement.
>
> The flash rate is itself a throughput check: 256 bytes per toggle at 9600 baud is 267 ms, so
> **~2 Hz means `write()` is blocking on a full TX buffer** and bytes are leaving at line rate.
> Much faster means the writes are going nowhere.

> **⚠️ Do not use an AC-volts reading to test for transmit.** A `P` sweep transmits an 8-byte frame
> then waits ~8 s for a timeout — roughly **0.1 % duty**. `w` polls five registers against ~2 s
> timeouts plus `delay(2000)`, roughly **0.3 %**. A meter averages either to nothing, so a zero
> reading would not distinguish a working shield from a dead one. Saturate the link instead.
> Note also that **autoranging selects the range, not the function**: on a combined-V meter the
> auto-sense reports the dominant DC bias and hides the signal entirely.

## 3. Flash and run

Sketches: `~/OneDrive - DGLC/Claude/chiltrix-sketches/` — `ChiltrixScan` (interactive scanner),
`ChiltrixModbus` (the eventual HTTP bridge) and `RS485Blast` (the §2 transmit-saturation
diagnostic). `arduino-cli` is at `/opt/homebrew/bin` with the `renesas_uno` core.

**Shield: DFR0259, both DIP switches AUTO and ON.** Set the ON/OFF switch to **OFF while
uploading** — with it ON the shield sits on D0/D1 and blocks the upload. Flip back to **ON** to run,
and confirm it.

```bash
cd ~/OneDrive\ -\ DGLC/Claude/chiltrix-sketches/ChiltrixScan
arduino-cli board list                      # find the port
arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi .
arduino-cli upload -p <PORT> --fqbn arduino:renesas_uno:unor4wifi .
arduino-cli monitor -p <PORT> -c baudrate=115200
```

The console is **115200**; the Modbus link is on `Serial1` at the swept baud, independent of it.
Boot output is lost until a host asserts DTR, so the sketch must be driven rather than passively
read. `chat.py` (asserts DTR, does not reset the R4) is the helper.

> **⚠️ Only one process may hold the port.** A second reader produces interleaved garbage and a
> `device reports readiness to read but returned no data` exception. That is port contention, not a
> bus fault.

> **⚠️ Closing the serial port does not stop the sketch.** A `P` sweep continues on the board after
> the host detaches, which is useful for meter work and confusing otherwise.

### Run capital `P`, not lowercase `p`

> **⚠️ Lowercase `p` probes slave id 1 ONLY** (across all seven bauds). **Capital `P` sweeps ids
> 1–32.** Node-IDs are legal to 255, so even 1–32 is not exhaustive.

`P` takes minutes; each attempt is ~8.5 s and the **9600 block comes first**, which is the only one
that matters since the vendor doc fixes the baud. **Capture the whole transcript** — the result
codes are the diagnosis.

## 4. Reading the outcome

The sketch prints a result code per attempt. Three branches:

**It responds.** Note the baud and id it reports, then run **`k`** — the known-value checks in §6.

**`0xE3` / "CRC errors" appear where there were none.** Real progress: bytes are arriving, so
something on the bus is transmitting, and it is now a baud or framing problem. Let the sweep finish;
it tests seven bauds.

**A flat "no" across all 32 ids.** This is the current state, and the Arduino end is already
eliminated as the cause (§2). Nothing further at `P6` will change it. Go to §5.

## 5. Questions for the Chiltrix rep

In order of value:

1. **What is the supported way to attach a monitoring device that logs everything the wired
   controller sees?** Ask it this way round. It is the actual goal, it does not presuppose that
   `P6` is the route, and it leaves the rep free to answer "you need the Remote Gateway", "share
   the `P4` bus", or "`P6` needs something enabled" — any of which ends the investigation. In
   Modbus terms the device being attached is a **master**; the chiller is the slave and the wired
   controller is what polls it today. Follow up with the specific: **does `P6` respond on a stock
   CX75 with no Remote Gateway fitted?** If the answer is no, every null result here is explained
   and the `P6` path is closed.
2. **Will Chiltrix supply the CX75 point map on its own?** The only maps in circulation are
   community reverse-engineering — jasipsw (CX50-2) and gonzojive (CX34) — they contradict each
   other on nearly every address and neither covers a CX75. A vendor map removes the guesswork
   whatever the transport turns out to be.
3. **What does the Remote Gateway cost, and can a demo unit be lent?** If `P6` is inert without one,
   buying the gateway and pointing pivac at its Modbus TCP side is a shorter path than
   reverse-engineering an undocumented map through a port that will never answer.
4. **Which indoor sensor does Dynamic Humidity Control take, and is it part of the Psychrologix
   product or a standalone accessory?** `P114`/`P115` are the feedback loop Appendix K.4 of
   `docs/unico-cooling-assessment-and-tuning.md` (PR #117) recommends in place of a Y2 wire. If the
   sensor only comes with a Psychrologix controller, that recommendation costs a controller rather
   than a sensor and needs rethinking.
5. **If `P6` is live, what is the Node-ID and is it settable?** No `P00`–`P119` parameter exposes
   it, and the CX34 map puts "Own 485 Address" in a register, so it may only be reachable over the
   very link being brought up.

## 6. Once it answers — verify registers before trusting any of them

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

## 7. After it works

1. Commit both sketches to `~/github/Arduino` — they exist only on the M2 and in OneDrive.
2. **Re-capture the `.114` DHW recirc sketch** while on that machine; it is uncommitted and exists
   nowhere else, and flashing the repo's psi-only sketch onto that board would silently drop
   `environment.inside.hvac.dhw.recirc.temperature`.
3. Record the verified register map in `docs/unico-cooling-assessment-and-tuning.md` §4.2 (PR #117).
4. Then `pivac.Chiltrix` becomes writable against a map that is known rather than guessed.
