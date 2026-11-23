<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
<!-- Copyright David Lewis -->

# Pi backup runbook

The Pi backs up to LookoutNas (DS225+ at `10.0.0.3`) with RonR's `image-utils`, which rsyncs the live system into a bootable `.img`. This runbook covers the manual procedures: building a new image from scratch, running an incremental by hand, verifying an image and restoring one. The scheduled backups and their rules are in `.claude/rules/platform-ops.md` under Backup Automation; the NAS share, the NFS mount and the ACL are in `claude-contexts/pi-CLAUDE.md` under Backup.

## Connection

A Mac with its key on the Pi logs in as `pi` (`ssh pi@10.0.0.82`). The Pi has passwordless SSH as root to the NAS (`ssh root@10.0.0.3`). Run every long command inside `tmux`, because a dropped SSH or xrdp session sends SIGHUP to a foreground rsync:

```bash
ssh pi@10.0.0.82
tmux new -s backup        # detach with Ctrl-b d, reattach with tmux attach -t backup
```

## Scheduled backups

| Timer | When | Does |
|---|---|---|
| `nas-image-backup.timer` | 1st of the month, 03:00 | Incremental into `pivac.img` on the NAS |
| `sd-clone.timer` | Sunday, 02:00 | `rpi-clone` to the spare card |

1. `nas-image-backup.timer` runs `scripts/nas-image-backup.sh`, which mounts the share, stops the disk-writing services, runs `image-backup` and restarts the services on exit.
2. `sd-clone.timer` runs `scripts/sd-clone.sh` against the card in the USB SD reader.

## Run an incremental by hand

```bash
sudo systemctl start nas-image-backup.service
journalctl -u nas-image-backup -f
```

The service does the same work as the monthly run, including the Grafana silence and the service restart. Afterwards check that every unit returned:

```bash
~/github/pivac/scripts/pivac-services.sh status
```

## Build a new image from scratch

`image-backup -i` creates a new image and refuses to overwrite an existing file. Use this procedure only when `pivac.img` must be rebuilt, for example after the NAS copy is lost. Building on a local disk and shipping the result is faster than building over NFS.

**Preconditions:**

- A scratch disk with at least 120 GB free is mounted on the Pi, for example at `/mnt/tempssd`. Check with `df -h /mnt/tempssd`.
- `image-utils` is at `/home/pi/github/RonR-RPi-image-utils/`.
- The target file does not exist.

**Phase 1: build the image on the scratch disk (about 15 minutes).**

```bash
~/github/pivac/scripts/pivac-services.sh stop-all
sudo /home/pi/github/RonR-RPi-image-utils/image-backup -i /mnt/tempssd/pivac.img
sudo systemctl start nginx influxdb signalk
~/github/pivac/scripts/pivac-services.sh start
```

`image-backup` creates the partitions inside the image file, formats them and rsyncs the live system into the loop-mounted partitions. Success shows as:

- a final line reporting that `image-backup` completed;
- `ls -la /mnt/tempssd/pivac.img` showing a sparse file near the card's size;
- `~/github/pivac/scripts/pivac-services.sh status` showing every unit active, with signalk, influxdb and nginx running;
- Grafana dashboards updating again.

Size the image to the full card before the first incremental. `image-backup` never resizes an existing image, and the image's MBR disk identifier must equal the live card's; the commands are in the Backup section of `docs/operational-notes.md`.

**Phase 2: ship the image to the NAS (10 to 20 minutes on gigabit).**

```bash
sudo mount /mnt/nas-pi-backups   # uses the noauto fstab entry
sudo rsync -avS --progress /mnt/tempssd/pivac.img /mnt/nas-pi-backups/
sudo umount /mnt/nas-pi-backups
```

`-S` keeps the file sparse, so rsync sends no empty blocks. If the NFS mount fails, send it over SSH with the root key:

```bash
sudo rsync -avS --progress /mnt/tempssd/pivac.img root@10.0.0.3:/volume1/pi-backups/
```

**Phase 3: verify.**

```bash
sudo mount /mnt/nas-pi-backups
sudo /home/pi/github/RonR-RPi-image-utils/image-info /mnt/nas-pi-backups/pivac.img
ls -la /mnt/nas-pi-backups/pivac.img
sudo umount /mnt/nas-pi-backups
```

`image-info` shows two valid partitions, boot (vfat) and root (ext4), and the size matches the scratch copy.

**Phase 4: detach the scratch disk.**

```bash
sudo umount /mnt/tempssd
sudo eject /dev/sda
```

Confirm the device name with `lsblk` before the eject, then unplug the disk.

## Restore

1. Mount the `pi-backups` share on a Mac, or on any machine with Raspberry Pi Imager.
2. In Pi Imager choose "Use Custom", select `pivac.img` and write it to an SD card of 128 GB or more.
3. Put the card in the Pi and boot. The first boot expands the root filesystem to the full card.
4. For an older version, mount the matching DSM snapshot of the `pi-backups` share and read the image from there.

## Known problems

- All access to the mounted share needs `sudo`. The share's ACL grants only `user:root` and `group:administrators`, so the `pi` user gets permission denied even though the Unix mode bits look open.
- If `image-backup` reports a missing `parted`, `losetup`, `kpartx` or `rsync`, install them with `sudo apt install -y parted kpartx rsync`.
- `stop-all` stops nginx, and nothing restarts it. Start it by hand with `sudo systemctl start nginx`.
