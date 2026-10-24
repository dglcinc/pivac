# Unico SCB live test

This is the procedure for proving `scripts/unico-scb.py` against the master bedroom air handler's S.M.A.R.T. Control Board, from a Mac on the USB port of the control box. The protocol is `docs/unico-scb-protocol.md`. The outcome decides the serial interface on the air-handler node's rev B board, which taps the same line on the UNO R4's `Serial1` (the rev A board is `hardware/ah-board`, PR #242).

The SCB is the bus master. It sends status frames on its own, and every frame the PC sends back is a write request, so the test runs in three stages and the later ones wait for the earlier ones to pass.

| Stage | Transmits | Risk |
|---|---|---|
| 1. Listen | Nothing | None |
| 2. Mirror | The stored values, unchanged | Low |
| 3. Set | One changed value, then the original | Changes a stored airflow |

## Setup

1. On the M2: `git fetch && git checkout feat/unico-scb-serial`, then `python3 tests/test_unico_scb.py`, which must print `all 14 checks passed`.
2. Connect a USB A-to-B cable from the Mac to the port on the side of the control box. macOS has an FTDI driver built in, and the board appears as `/dev/cu.usbserial-*` (`ls /dev/cu.usbserial-*`).
3. Run the tool from the repo with `uv run --no-project --with pyserial python scripts/unico-scb.py …`. The `--no-project` keeps uv from building the Pi-only `RPi.GPIO` dependency.

## Stage 1: listen

```bash
uv run --no-project --with pyserial python scripts/unico-scb.py listen \
    --raw scb-raw.txt --csv scb.csv -v --seconds 600
```

Pass when all of these hold:

1. The board's green LED flashes and status lines print within a few seconds.
2. The model reads as this air handler's model, which matches the MOD and AUX switch positions on the SCB.
3. The stored airflows match Bulletin 30-039 table 10 for the model and the CFM switch, or a value set earlier with ECMConfig.
4. The calls follow the thermostat: on a master bedroom call `Y1` appears, and `Y2` when the high fan runs. The node's `environment.inside.hvac.ah.mbr.y2` must agree.
5. Actual airflow and RPM rise and fall with the calls, and read near zero with no call.
6. The frame length is 51. A 9-, 36- or 37-byte frame means older firmware, so stop before stage 2 and update the doc.

Record the motor-bus bytes (`bus` lines under `-v`, frames starting `0a`) in the raw file; they are the SCB-to-motor protocol, which ECMConfig ignores and the node may want later.

Measure the line for the rev B interface while it is live, with the meter's common on the data cable's black wire, then on the SCB's `C` terminal:

1. DC volts on each of blue, yellow and orange at idle.
2. The same during traffic, and on an oscilloscope if one is to hand.
3. Whether any wire sits at 24 VAC, which would make it the supply and not data.

## Stage 2: mirror

```bash
uv run --no-project --with pyserial python scripts/unico-scb.py mirror            # prints the frame only
uv run --no-project --with pyserial python scripts/unico-scb.py mirror --transmit
```

The mirror answer requests exactly what the SCB reports as stored, which is what ECMConfig sends on every tick after its first. The tool refuses when the SCB's byte 2 bit 7 is clear, because the Air Cycle byte then cannot be mirrored safely (protocol §9 item 1).

Pass when all of these hold:

1. The red LED flashes once on the send.
2. The tool reports the echo: `matched, dropped` means the USB board loops our transmission back (protocol §9 item 11), and `none` means it does not. Record which.
3. Every stored value is unchanged in the status frames that follow.
4. The SCB's flags byte drops bit 5 (`0x20`, "timed out waiting for the PC") on the next frame.

## Stage 3: set

Change one value by a small amount, confirm it, and put it back. Fan-only airflow (`G`) is the least consequential:

```bash
uv run --no-project --with pyserial python scripts/unico-scb.py set cfm.G=<stored+25>              # dry run
uv run --no-project --with pyserial python scripts/unico-scb.py set cfm.G=<stored+25> --transmit
uv run --no-project --with pyserial python scripts/unico-scb.py set cfm.G=<stored> --transmit
```

Pass when the stored `G` airflow reads the new value within about 20 s and the original after the restore. ECMConfig's help warns not to cut the SCB's power until a change shows as stored, since the board is then writing its memory.

The tool never sends the thermostat override (PC byte 4 bits 2–7), which runs the blower and can close the SCB's hot-water, chilled-water and condenser relays, or the test flow and test pressure bytes, whose effect is unknown.

## Afterwards

1. Commit `scb-raw.txt` from stage 1 under `docs/data/` if it shows anything the protocol doc does not already describe, and update the protocol doc's §9.
2. Record the line measurements in `docs/air-handler-shield-pcb-plan.md` as the input to the rev B serial interface.
