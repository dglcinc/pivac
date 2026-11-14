<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
<!-- Copyright David Lewis -->

# Air-handler nodes: rev A to the utility unit, the Rev B AirMaster to the master bedroom

The rev A shield goes back on the utility zone's M2430, with the SCB read again over the Pi's USB. The Rev B
AirMaster, `AM-0001` until step 3 makes it `AM-0014`, replaces the UNO R4 node on the master bedroom's M2430 and
reads that unit's SCB on J4. Both nodes keep their addresses: rev A 10.0.0.181, the AirMaster 10.0.0.182. Never
connect a computer to the Pico's micro-USB while 24 VAC is on J1.

## 1. Utility unit

| Step | From | To |
|---|---|---|
| Power off | AirMaster J1 | unplugged |
| Water pair | J2 plug | rev A TB3 |
| Air pair | J3 plug | rev A TB2 |
| 24 VAC | J1 plug, R and C | TB1 plug, positions 1 and 2 |
| SCB | USB board cable on J4 | the Pi's USB |
| Power on | TB1 | plugged in |

1. TB3 and TB2 take the same PTSM plugs in the same orders, V · D · G and SUP · GND · RET · GND.
2. Land R and C in the TB1 plug with it off the board; Y2 and W2 stay empty.

## 2. Master bedroom unit

| Step | From | To |
|---|---|---|
| Power off | UNO's USB-C | unplugged from the converter |
| 1-wire V · D · G | XT1, XT2, XT3 | J2 plug 1, 2, 3 |
| Supply air | XT4, XT5 | J3 plug 1, 2 |
| Return air | XT7, XT8 | J3 plug 3, 4 |
| 24 VAC | Unico R and C | J1 plug 1 (R), 2 (C) |
| SCB | control box USB board | J4 |
| Power on | J1 | plugged in |

1. Run 22 AWG solid from the blocks to the plugs, as on the utility unit. The NTC shields (XT6, XT9) stay open.
2. R and C come from the converter's input; the converter, K1 and the UNO stay in place, unpowered or idle, as
   the rollback.
3. The PA5 pair ran at 5 V on the UNO; the DS2482 runs it at 3.3 V, which DS18B20s accept.
4. Without a USB board in this control box the temperatures still publish and the calls do not.

## 3. New identity

AM-0001's label is retired, so the board takes the first Rev C label, AM-0014, before it goes up. With J1
unplugged, hold BOOTSEL, plug the micro-USB into the M2 and run, from `~/github/Arduino`:

```bash
arduino-cli compile -b rp2040:rp2040:rpipicow:usbstack=tinyusb_host,flash=2097152_1048576 --output-dir build AirMaster
~/.config/airmaster/venv/bin/python AirMaster/factory/airmaster_factory.py flash --uf2 build/AirMaster.ino.uf2 --new-identity
```

1. The tool names the label, `Use label AM-0014`; stick it on the base. The unit keeps its WiFi, name and
   offsets, and its setup network becomes `AirMaster-A8B6`.
2. A Rev C board later takes the same serial with `flash --serial AM-0014`; this board is then re-flashed with
   `--new-identity` or retired.

## 4. The unit's page

Browse to `http://10.0.0.182/`.

| Setting | Value |
|---|---|
| Name | Master Bedroom |
| Water supply ROM | `28-000000cb6e28` |
| Water return ROM | `28-0000001a8cda` |
| Water supply offset | +0.26 °F |
| Water return offset | +0.53 °F |
| Supply air offset | −0.53 °F |
| Return air offset | +0.17 °F |

1. Name: the host name becomes `master-bedroom.local`.
2. Water offsets: PA5A and PA5B at the 115 °F bath. For cooling they are +0.50 and +0.33 °F.
3. Air offsets: the beads' mean residual from 90 to 130 °F on R0 10000, beta 3995, the curve both the UNO
   sketch and AirMaster use.

## 5. Pi

The config is staged as `/etc/pivac/config.yml.swap`, and the live one is kept as
`/etc/pivac/config.yml.bak-20261114-swap`.

```bash
sudo cp /etc/pivac/config.yml.swap /etc/pivac/config.yml
sudo cp ~/github/pivac/scripts/systemd/pivac-scb-mbr.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now pivac-scb-mbr
sudo systemctl restart pivac-ah-mbr pivac-ah-utility pivac-scb-utility
sudo systemctl restart signalk
```

1. The signalk restart drops `ah.mbr.y2` and `ah.mbr.y2Seconds`, which the AirMaster does not publish; the high-fan
   call is `ah.mbr.call.y2`.

## 6. Checks

| Check | Expect |
|---|---|
| `ah.utility.*` temperatures | as before the swap |
| `ah.utility.call.*`, `.fan.rpm` | fresh every 5 s |
| `ah.mbr.water.*` | within 1 °F of loop A supply on a call |
| `ah.mbr.air.*` | room ±1 °F, fan off |
| `ah.mbr.call.*` | matches MASTER_BR in RedLink |

## 7. Rollback

Copy `/etc/pivac/config.yml.bak-20261114-swap` back over the config, stop and disable `pivac-scb-mbr`, and
restart the three services and signalk. Put each node back on its unit as it was before step 1.
