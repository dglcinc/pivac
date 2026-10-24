# Unico SCB live test

This is the procedure for proving `scripts/unico-scb.py` against an air handler's S.M.A.R.T. Control Board, from a Mac on the USB port of the control box. The protocol is `docs/unico-scb-protocol.md`. The outcome decides the serial interface on the master bedroom air-handler node's rev B board, which taps the same line on the UNO R4's `Serial1` (the rev A board is `hardware/ah-board`, PR #242). The protocol is the same on every SCB, so any zone's control box serves; the record of the 2026-10-24 run on the utility zone's unit is at the end.

The SCB is the bus master. It sends status frames on its own, and every frame the PC sends back is a write request, so the test runs in three stages and the later ones wait for the earlier ones to pass.

| Stage | Transmits | Risk |
|---|---|---|
| 1. Listen | Nothing | None |
| 2. Mirror | The stored values, unchanged | Low |
| 3. Set | One changed value, then the original | Changes a stored airflow |

## Setup

1. On the M2: `git fetch && git checkout feat/unico-scb-serial`, then `python3 tests/test_unico_scb.py`, which must print `all 18 checks passed`.
2. Connect a USB A-to-B cable from the Mac to the port on the side of the control box. The board fitted here is a Cypress CDC device that macOS drives without an installer, `/dev/cu.usbmodemunicousb1`; an FTDI board would appear as `/dev/cu.usbserial-*`. Check with `ls /dev/cu.usbmodem* /dev/cu.usbserial-*`. The tool opens the first port of either kind; pass `--port` when there is more than one.
3. Run the tool from the repo with `python3 scripts/unico-scb.py …` when pyserial is installed (`python3 -c 'import serial'`), otherwise with `uv run --no-project --with pyserial python scripts/unico-scb.py …`. The `--no-project` keeps uv from building the Pi-only `RPi.GPIO` dependency.

## Stage 1: listen

```bash
python3 scripts/unico-scb.py listen --raw scb-raw.txt --csv scb.csv -v --seconds 600
```

Pass when all of these hold:

1. The board's green LED flashes and status lines print within a few seconds.
2. The model reads as the air handler under test, which matches the MOD and AUX switch positions on the SCB.
3. The stored airflows match Bulletin 30-039 table 10 for the model and the CFM switch, or a value set earlier with ECMConfig.
4. The calls follow the zone's thermostat: on a call `Y1` appears, and `Y2` when the high fan runs. On the master bedroom unit the node's `environment.inside.hvac.ah.mbr.y2` must agree.
5. Actual airflow and RPM rise and fall with the calls, and read near zero with no call.
6. The frames are 36 bytes with byte 3 = 23. That is the SCB's unanswered state; it sends the 51-byte frame only in reply to a PC frame, and stage 2 brings it. A 9-byte frame, or byte 3 = 20, means older firmware, so stop before stage 2 and update the doc.

Record the motor-bus bytes (`bus` lines under `-v`, frames starting `0a`) in the raw file; they are the SCB-to-motor protocol, which ECMConfig ignores and the node may want later.

Measure the line for the rev B interface while it is live, with the meter's common on the data cable's black wire, then on the SCB's `C` terminal:

1. DC volts on each of blue, yellow and orange at idle.
2. The same during traffic, and on an oscilloscope if one is to hand.
3. Whether any wire sits at 24 VAC, which would make it the supply and not data.

## Stage 2: mirror

```bash
python3 scripts/unico-scb.py mirror            # prints the frame only
python3 scripts/unico-scb.py mirror --transmit
```

`mirror` and `set` first send the idle frame, which is ECMConfig's own first reply after a connect and requests nothing (protocol §8), because the SCB reports its Air Cycle values only in the 51-byte frame it sends after being answered. The dry run sends it too. The mirror answer then requests exactly what the SCB reports as stored, which is what ECMConfig sends on every tick after its first. The tool refuses when the SCB's byte 2 bit 7 is clear, because the Air Cycle byte then cannot be mirrored safely (protocol §9 item 1).

Pass when all of these hold:

1. The red LED flashes once on the send.
2. The tool reports the echo: `matched, dropped` means the USB board loops our transmission back (protocol §9 item 11), and `none` means it does not. Record which.
3. Every stored value is unchanged in the status frames that follow.
4. The SCB's flags byte drops bit 5 (`0x20`, "timed out waiting for the PC") on the next frame, and raises it again on the one after, since nothing answers that one.

## Stage 3: set

Change one value by a small amount, confirm it, and put it back. Fan-only airflow (`G`) is the least consequential:

```bash
python3 scripts/unico-scb.py set cfm.G=<stored+25>              # dry run
python3 scripts/unico-scb.py set cfm.G=<stored+25> --transmit
python3 scripts/unico-scb.py set cfm.G=<stored> --transmit
```

Pass when the stored `G` airflow reads the new value within about 20 s and the original after the restore. ECMConfig's help warns not to cut the SCB's power until a change shows as stored, since the board is then writing its memory.

The tool never sends the thermostat override (PC byte 4 bits 2–7), which runs the blower and can close the SCB's hot-water, chilled-water and condenser relays, or the test flow and test pressure bytes, whose effect is unknown.

## Override (ECMConfig's Thermostat Override)

`override` holds one of G, Y1, Y2, W1, W2 or E as if the thermostat called it, then releases. In this house the SCB's heat and cool relays are dry contacts that pass 24 VAC to the zone's W and Y inputs at the HZ-432 through the Quattro pass-through terminal blocks, so an override is a real zone call: the panel calls the equipment and its damper output energises the zone valve. It is the way to raise a controlled call for a node or `LoopDelta` check without touching a thermostat.

```bash
python3 scripts/unico-scb.py override Y1 --seconds 60                                   # dry run
python3 scripts/unico-scb.py override Y1 --seconds 60 --transmit --this-calls-the-plant
```

Its controls: it refuses without both `--transmit` and `--this-calls-the-plant`; it refuses while the frame shows a thermostat call, since the override could not be told apart from it; the hold is capped at 300 s; and on the timer, on Ctrl-C or on any error it sends ten plain mirror frames to release, then watches the motor for `--watch` seconds and reports whether it stopped. Watch `HPCALL` or `BLR` in Signal K alongside, because the frame's call bits report the thermostat inputs and may not reflect the override.

## Afterwards

1. Commit `scb-raw.txt` from stage 1 under `docs/data/unico-scb/` if it shows anything the protocol doc does not already describe, and update the protocol doc's §9.
2. Record the line measurements in `docs/air-handler-shield-pcb-plan.md` (PR #242) as the input to the rev B serial interface.

## Record: 2026-10-24, utility zone M2430

Run from the M2 with the USB cable in the utility zone air handler's control box, port `/dev/cu.usbmodemunicousb1`, firmware 3.21 (the SCB's label reads `3_21`). No thermostat call during stages 1 to 3; a cool call for the zone ran from 17:23 EDT through the end of the capture.

| Stage | Result |
|---|---|
| 1. Listen | Pass. Model 2430; stored CFM G 200, Y1 300, Y2 500, W1 300, W2 500, E 500, RPM limits 1800 throughout; 36-byte frames with byte 3 = 23 every 0.85 s, flags `0xA1`, three motor-bus frames per tick. On the cool call `G,Y1` appeared, actual airflow rose from 0 to the stored 300 CFM in 20 s and held it at 1040 to 1070 RPM; no `Y2` in the 11.5 min captured; flags unchanged |
| 2. Mirror | Pass. Echo none; every stored value unchanged over 20 s; flags `0x80` in the frame after the reply and `0xA1` from the next |
| 3. Set | Pass. G 200 to 225 reported stored in the next frame, under 1 s; 200 again on the restore |

1. The 36-byte frame is the SCB's unanswered state. One idle frame brought the 51-byte frame on the next tick, and the SCB returned to 36 bytes about ten frames after the last reply.
2. The 51-byte frame read: switches `0x0107` (Chiller = Leader, humidistat high, reversing valve O, Mod switch live), fresh air 10 %, needed airflow 370 CFM, 1500 sq ft, 3 occupants, Fixed mode 10 min every 8 h, 2 bedrooms, EAC off, DC bus byte 1 (4 V by the program's scaling, with the motor stopped).
3. The stored airflows differ from the 2430 factory defaults (Hi 625, Lo 500), so they were set with ECMConfig; Bulletin 30-039 table 10 was not checked.
4. Still to do: the line measurements for the rev B tap, and a high-fan call to see `Y2`.
5. Captures in `docs/data/unico-scb/`: `2026-10-24-utility-listen-idle.txt` (stage 1 and the idle send, raw hex), `2026-10-24-utility-cool-call.txt` and `.csv` (the call), `2026-10-24-utility-transmit-transcripts.txt` (stages 2 and 3).
