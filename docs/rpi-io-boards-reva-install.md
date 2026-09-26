# Rev A boards and the new Pi into the housing — cutover

**Status:** run 2026-09-26, 13:53 to 15:10 EDT. The new Pi is the production Pi on the rev A
boards; the old production Pi and the perfboards are the bench set, held as the rollback until
2026-10-10. Kept as the record of the day and the pattern for the next swap. **Owner:** David at
the panel, Claude at the Mac over ssh; each step says who.

**As run.** The clone took 2 m 44 s. First boot was clean on every count. Ten relays read
live at once; `HPCOOL` did not, and the fault was a loose connector on the pigtail's SP-C
wire between the plug and J8 pad 1, found by bridging the plug's slots: 1 to 3 left BCM 13
high, 2 to 3 pulled BCM 16 low, so COM and SP-E were good and slot 1 was open. Reseated and
read 1 on the next boot. The 1-wire proof passed twice, 320 clean reads each. RedLink stalled
in its Signal K reconnect backoff after boot and needed one restart. A pin watch (Monitor
tailing `pinctrl` for the twelve channels) relayed each contact to the terminal as David
shorted the plugs, which is the bench walk done in the housing. One false lead: BCM 16
read low before any wire was moved because pivac sets pull-ups only on its configured pins
and SP-E is unused, so it sits at the Pi's boot pull-down; set `pinctrl set 16 ip pu` before
reading the spare. The extra card went into the SD reader as the clone target, so the weekly
clone continues.

| | Production today | After the cutover |
|---|---|---|
| Pi | Pi 4 B Rev 1.5, `eth0` `2c:cf:67:80:55:00`, `wlan0` `2c:cf:67:80:55:01` | Pi 4 B Rev 1.5, `eth0` `88:a2:9e:3c:c3:73` (`wlan0` expected `…:74`, read it at first boot) |
| UCG client `_id` | `6a9e09b277a1135d842469bd` (fixed `10.0.0.82`); wlan0 `6a9e0b1677a1135d84246a04` (fixed `10.0.0.130`) | `6ab8005daaa25ebc609be30b` (today `pibench`, lease `10.0.0.220`) |
| Card | live card, disk id `0x059be283` | the spare from the USB reader, `/dev/sdb` today, disk id `0xf8c4a716`, last cloned Sun 2026-09-20 02:10 |
| I/O boards | perfboard pair | rev A pair |
| Sense supply | 12 V wall wart (14.7 V DC) on J4.1 (+) and J4.4 (−) | 24 VAC transformer on J4.1 and J4.2, rectified on the board |
| `HPCOOL` (BCM 13) | J4.2 | J8 pigtail position 1 (SP-C) |
| Bench set | new Pi on the bench card (`pibench`) | old production Pi with its own card for two weeks, then the bench card, plus the perfboards |

Every channel keeps its BCM pin and Signal K path; the hostname and Signal K source label
(`rpi:pivac`) are the card's. Budget half a day; the house is unmonitored from step 2 to step
8, and the freshness alerts fire at 30 minutes and clear on their own.

## 0. Before the panel is opened

1. **Claude:** merge PR #210 and pull it on the production Pi, so the clone carries the label,
   this document and the walk script:
   ```bash
   ssh pi@10.0.0.82 'git -C ~/github/pivac pull --ff-only && git -C ~/github/pivac log --oneline -1'
   ```
2. **David:** print the label from `docs/PhoenixContact-BC-RPI-label.docx` (rows J1.1 to J8.3,
   H1 to H3, then the new Pi's MAC `88:a2:9e:3c:c3:73`).
3. **David:** parts at the panel: the 24 VAC transformer with bare wire ends; the four PTSM
   4-way plugs (reuse the perfboard's, they are the same part); the PTSM-3 plug for the J8
   pigtail; ferrules for stranded conductors; 22 AWG solid; the link cable; the bench Pi
   powered off (done 2026-09-26) with its bench card pulled and kept for the old Pi.
4. **David:** confirm the transformer's outlet is the `PivacPower` Shelly's, so the sense supply
   and the Pi come and go together.

## 1. Freeze the production Pi and take a fresh clone (Claude)

The weekly clone is six days old and taken live. Re-clone with the writers stopped so the card
carries InfluxDB, the Grafana database and the config as of this minute. In `tmux` on the Pi:

```bash
ssh pi@10.0.0.82
tmux new -s cutover
sudo systemctl stop pivac-1wire pivac-redlink pivac-gpio pivac-arduino-psi pivac-arduino-therm-psi pivac-emporia pivac-sentry pivac-watermeter pivac-sprinkler pivac-domestic-water pivac-chiltrix pivac-loop-delta pivac-grafana-alerts signalk influxdb grafana-server nginx
lsblk -o NAME,SIZE | grep -E '^sd'                    # the spare is the 119.2G one (sdb on 2026-09-26; sda is the empty slot)
sudo /home/pi/github/pivac/scripts/sd-clone.sh          # ~5 min incremental; ends "rpi-clone finished — exit 0"
```

Then the one check the kernel cannot survive without. The spare's boot partition is
auto-mounted under `/media/pi/`; `sd-clone.sh` rewrites this and exits 2 if it cannot:

```bash
sudo blkid -s PTUUID -o value /dev/sdb; grep -o 'root=PARTUUID=[^ ]*' /media/pi/*/cmdline.txt
```

Expect the same eight hex digits (`f8c4a716`) in both. Nothing else needs editing: the clone of
the live card already has `dtparam=i2c_arm=on`, no `w1-gpio` overlay, `ds2482-init` enabled
and `ds2482` in `modules-load.d` (checked on the spare 2026-09-26). Then:

```bash
sudo poweroff
```

Do not restart anything on the production Pi. It stays down; if step 7 fails it goes back in
with its own card, untouched.

**David:** when the lights stop, pull the spare card from the USB reader. Leave the Pi's own
card in it.

## 2. Move the `10.0.0.82` reservation to the new MAC (Claude)

Before the new Pi is powered. The port forwards and every external URL point at `.82`.

```bash
KEY=$(cat ~/.config/unifi/claude-agent.key); B=https://10.0.0.1/proxy/network/api/s/default
curl -sk -X PUT  -H "X-API-KEY: $KEY" -H 'Content-Type: application/json' "$B/rest/user/6a9e09b277a1135d842469bd" -d '{"use_fixedip":false,"fixed_ip":""}'
curl -sk -X POST -H "X-API-KEY: $KEY" -H 'Content-Type: application/json' "$B/cmd/stamgr" -d '{"cmd":"kick-sta","mac":"2c:cf:67:80:55:00"}'
curl -sk -X POST -H "X-API-KEY: $KEY" -H 'Content-Type: application/json' "$B/cmd/stamgr" -d '{"cmd":"kick-sta","mac":"88:a2:9e:3c:c3:73"}'
curl -sk -X PUT  -H "X-API-KEY: $KEY" -H 'Content-Type: application/json' "$B/rest/user/6ab8005daaa25ebc609be30b" -d '{"name":"pivac","use_fixedip":true,"fixed_ip":"10.0.0.82","network_id":"63ab8c9d277b3e032baaa609"}'
curl -sk -H "X-API-KEY: $KEY" "$B/stat/user/88:a2:9e:3c:c3:73" | python3 -c 'import sys,json; d=json.load(sys.stdin)["data"][0]; print(d["use_fixedip"], d["fixed_ip"])'
```

All return `"rc":"ok"` (`api.err.UnknownStation` on a kick is fine) and the last line reads
`True 10.0.0.82`. The old record is renamed afterwards in step 10.

## 3. Panel: power down, photograph, pull (David)

1. CDP control-power breaker off (relay coils and the panel's 24 VAC), then the `PivacPower`
   Shelly off: `curl "http://10.0.0.118/rpc/Switch.Set?id=0&on=false"`. Confirm the Pi is dark
   and 0 V on the wall wart leads.
2. Photograph the four plugs and the H1 plug against the label before touching a wire.
3. Pull J1 to J4 and H1 from the perfboards, unplug the link cable, lift the Pi with its INT
   perfboard out of the housing, lift the EXT perfboard from its slot. The Pi's USB devices
   come with it: the Chiltrix UNO R4 bridge (`/dev/ttyACM0`) and the USB SD reader.
4. Keep the Pi, its card and the perfboards together, labelled "pivac, old, card intact,
   rollback until 2026-10-10".

## 4. Rewire the plugs

Plugs J1 to J3 replug position for position. J4 changes, and one relay moves to the pigtail.
Positions are counted left to right on the footprint in the board's top view, whatever the plug
body prints. Silkscreen names that differ from the config name are in brackets.

| Position | Wire tagged | BCM | Phys | Action |
|---|---|---|---|---|
| J1.1 | ZV | 17 | 11 | replug |
| J1.2 | DHW | 27 | 13 | replug |
| J1.3 | BLR | 22 | 15 | replug |
| J1.4 | COM | | | replug |
| J2.1 | HPCALL (CHIL) | 25 | 22 | replug |
| J2.2 | BOS1 | 6 | 31 | replug |
| J2.3 | BOS2 | 5 | 29 | replug |
| J2.4 | COM | | | replug |
| J3.1 | DEHUM | 12 | 32 | replug |
| J3.2 | SCALA | 23 | 16 | replug |
| J3.3 | HPHEAT | 24 | 18 | replug |
| J3.4 | COM | | | replug |
| J4.1 | 24 VAC (24VAC) | | | **new**: transformer wire 1; the wall wart + comes out |
| J4.2 | 24 VAC (unlabelled) | | | **new**: transformer wire 2; `HPCOOL` comes out |
| J4.3 | DHWX (SP-D) | 19 | 35 | replug |
| J4.4 | COM | | | **empty** unless a common is grouped here; the wall wart − comes out |

J8 pigtail (PTSM-3 header in the EXT proto field, wired to the INT board's J8 pads):

| Position | Wire tagged | BCM | Phys | Action |
|---|---|---|---|---|
| 1 | HPCOOL (SP-C) | 13 | 33 | **move** from the perfboard's J4.2 |
| 2 | SP-E | 16 | 36 | spare, empty |
| 3 | COM | | | the `HPCOOL` relay's common, if it is not already on a J1–J3 COM |

The transformer's two wires are the AC pair into the bridge; **neither is COM**. A return on
J4.4 shorts the transformer through one diode and the PTC on every negative half-cycle (the PTC
took that for several minutes on 2026-09-25 and recovered). Every COM is one net, the bridge's
negative, so one common may serve all the relays on any position 4 or pigtail 3, and it never
meets Pi ground. Strain-relieve the pigtail and every cable at the housing entry. Ferrules on
stranded conductors; 22 AWG solid goes in bare. A wire with no row above is a retired run:
coil and tag it. Land the transformer **last**, after the checks in step 6.

## 5. Fit the new Pi and the boards (David)

1. Spare card into the new Pi. Seat the Pi on the rev A INT board's socket, all 40 pins.
2. The pair into the housing, EXT board in its slot with H1 to H3 at the short-end opening,
   link cable J6 to the EXT link header (3V3 · SDA · SCL · GPIO4 · GND straight through), the
   J8 pigtail plugged into the PTSM-3 header in the EXT proto field.
3. Plugs J1 to J4 and the pigtail per step 4. H1 takes the trunk plug, VCC · DATA · GND left
   to right in the plug, which reads GND · DATA · VCC from the front with the board solder side
   out. H2 and H3 stay empty.
4. The Chiltrix UNO R4 bridge and the USB SD reader onto the new Pi's USB, the extra card in
   the reader as the clone target. Ethernet, then the Pi's USB-C lead. The label under the
   clear cover. Both USB leads were left off on 2026-09-26 and had to be reconnected after
   the first-boot checks: `lsusb` showing only the hubs is the sign.

## 6. Meter checks, then power (David)

Plugs in, everything unpowered, transformer not landed:

1. Each channel position to its plug's COM: open, or the relay's contact resistance if that
   relay is closed; never a dead short from a relay that should be open.
2. Any COM to Pi ground (a header ground pad or a USB shell): **open**. A beep is a common
   still on Pi ground; find it before powering.
3. J4.1 to J4.2 open; J4.1 and J4.2 to J4.4 open.

Land the transformer, `PivacPower` on (`…on=true`), and read about 35 V DC between TP1 (VS)
and TP2 (COM): zero is a reversed diode or an open PTC, 37 V unloaded is normal. Then the CDP
control breaker on.

## 7. First boot (Claude)

The clone boots as `pivac`, DHCP gives it `.82` and every service starts. After two minutes:

```bash
ssh pi@10.0.0.82 'hostname; cat /sys/class/net/eth0/address /sys/class/net/wlan0/address; uptime -p; ls /sys/firmware/devicetree/base | grep -c onewire; systemctl is-active ds2482-init signalk influxdb grafana-server nginx; systemctl list-units "pivac-*" --no-pager | grep -c running; ls -l /dev/ttyACM0'
```

Expect `pivac`, `88:a2:9e:3c:c3:73`, the wlan0 MAC (note it for step 10), `0` onewire nodes,
everything `active`, 12 running pivac units and the Chiltrix bridge present. If ssh answers at
`.220` and not `.82`, the reservation in step 2 did not take: fix it, then
`sudo systemctl restart NetworkManager`. The Mac's `known_hosts` entry for `.82` is the card's
own host key, so ssh raises no warning.

**Relays.** All eleven paths publish within a cycle:

```bash
ssh pi@10.0.0.82 'curl -s http://127.0.0.1:3000/signalk/v1/api/vessels/self/electrical/ac/switch/utility | python3 -c "import sys,json; print({k:v[\"statenum\"][\"value\"] for k,v in json.load(sys.stdin).items()})"'
```

Expect ZV, DHW, BLR, HPCALL, BOS1, BOS2, DEHUM, SCALA, HPHEAT, HPCOOL and DHWX, with `HPHEAT`
or `HPCOOL` at 1 for whichever mode the HZ-432 holds and the rest as the panel stands. Then
the proofs that need a call: `HPCALL` at 1 on the first hydronic call (raise a setpoint on
MASTER_BR, DSTRS_FAM_ROOM or KIDS_ROOM), `DHW` then `DHWX` on the next DHW draw while a zone
calls, `BOS1` on a KITCHEN cool call and `BOS2` on GREAT_ROOM. A path that moves with another
when one relay closed is a common on the wrong plug. For a pin-level view, stop `pivac-gpio`
and run `sudo python3 ~/github/pivac/scripts/io-board-test.py --monitor`, then start it again.

## 8. 1-wire (Claude)

```bash
ssh pi@10.0.0.82 'readlink /sys/bus/i2c/devices/1-0018/driver; cat /sys/bus/w1/devices/w1_bus_master1/w1_master_slave_count; ls /sys/bus/w1/devices/ | grep ^28-'
```

Expect the driver link ending `ds2482`, a count of **8**, and the eight ROMs of the CLAUDE.md
roster. Then the forty-sweep proof from `docs/ds18b20-bus-topology.md` §7.3 (`crc_fail=0
sweeps_not_8=0`, `ext_power` 1 on all eight). `DS2482 reset failed` in the journal with the
chip answering at `0x18` is VCC or ground open on the link cable. `pivac-1wire` rescans every
cycle and needs no restart.

## 9. From outside (David and Claude)

- `https://68lookout.dglc.com/admin/` loads and the Data Browser shows
  `electrical.ac.switch.utility.*` and `environment.inside.hvac.*` under a minute old.
- WilhelmSK reconnects, the SwitchBank shows all eleven relays in order, `notifications.pivac.*`
  return to `normal` within a cycle.
- Grafana shows the gap and data resuming; Sentry `decodeMargin` still 40–60 and
  `registrationScore` above 0.6, since work in the boiler room bumps the camera.
- `journalctl -u pivac-1wire -u pivac-gpio -u pivac-chiltrix -u pivac-redlink -n 30 --no-pager`
  clean after the first cycle; RedLink logs in about 75 s after boot.

Close the panel. The old Pi stays on the shelf, powered off, card in, until 2026-10-10.

## 10. Afterwards (Claude, same day)

1. **wlan0 reservation.** Read the new wlan0 MAC from step 7, find its UCG record
   (`GET $B/stat/user/<mac>`; it appears once the `redux` profile has associated, and
   `sudo nmcli connection up redux` forces that), release `10.0.0.130` from
   `6a9e0b1677a1135d84246a04` with `{"use_fixedip":false,"fixed_ip":""}`, kick
   `2c:cf:67:80:55:01`, pin `.130` on the new record with name `pivac-wlan0`, then
   `sudo nmcli connection up redux` again to re-lease.
2. **Old records.** Rename `6a9e09b277a1135d842469bd` to `pibench` (it becomes the bench Pi)
   and leave `dc:a6:32:19:12:ee`'s record alone.
3. **Backup image.** `nas-image-backup.timer` runs 2026-10-01 03:00 and the image's disk
   identifier must equal the live card's, now `0xf8c4a716`:
   ```bash
   ssh pi@10.0.0.82 'sudo mount /mnt/nas-pi-backups && sudo sfdisk --disk-id /mnt/nas-pi-backups/pivac.img 0xf8c4a716 && sudo umount /mnt/nas-pi-backups'
   ```
4. **Weekly clone.** `sd-clone.timer` fires Sunday 02:00 against the extra card in the
   reader. On 2026-10-10 the old Pi boots the bench card as `pibench`; its own card
   (`0x059be283`) is then free.
5. **Docs.** CLAUDE.md: the Pi network interfaces paragraph (both MACs), the bench-Pi
   sentence in Known Operational Behaviours (the bench Pi is now `2c:cf:67:80:55:00` with the
   perfboards), the label's MAC line in `cdp-chiller-rework-plan.md` §4;
   `rpi-io-boards-assembly.md` "Bench Pi"; the Backup Automation disk-id note; global memory
   `user.md`. `docs/new-pi-cutover.md` retires to the history it records.

## 11. Rollback

At any point up to step 9: `PivacPower` off, the old Pi with its own card and the perfboards
back on the plugs per the photographs (wall wart on J4.1 and J4.4, `HPCOOL` on J4.2), and the
reservation back:

```bash
KEY=$(cat ~/.config/unifi/claude-agent.key); B=https://10.0.0.1/proxy/network/api/s/default
curl -sk -X PUT  -H "X-API-KEY: $KEY" -H 'Content-Type: application/json' "$B/rest/user/6ab8005daaa25ebc609be30b" -d '{"use_fixedip":false,"fixed_ip":""}'
curl -sk -X POST -H "X-API-KEY: $KEY" -H 'Content-Type: application/json' "$B/cmd/stamgr" -d '{"cmd":"kick-sta","mac":"88:a2:9e:3c:c3:73"}'
curl -sk -X PUT  -H "X-API-KEY: $KEY" -H 'Content-Type: application/json' "$B/rest/user/6a9e09b277a1135d842469bd" -d '{"name":"pivac","use_fixedip":true,"fixed_ip":"10.0.0.82","network_id":"63ab8c9d277b3e032baaa609"}'
```

The old card is untouched by this procedure, so it boots as it did before step 1; only the
data written to the new card in between is lost.
