#!/bin/bash
# Weekly hot-recovery clone of the live Pi filesystem to the USB-attached
# spare microSD. Used for fast card-death recovery: pull live SD, drop spare
# in, reboot. rpi-clone runs on a live system; no service stop needed.
#
# Triggered by sd-clone.timer; can also be run manually as root.
set -u -o pipefail

# Anker USB 3.0 Micro SD Card Reader (Genesys Logic chipset). The reader
# advertises a generic SCSI model string ("MassStorageClass"), so we identify
# it by USB VID:PID instead — that's specific to this exact reader and won't
# false-match other USB storage. Replace these if the reader changes.
READER_VID=05e3
READER_PID=0764
RPI_CLONE=/usr/local/sbin/rpi-clone

log() { echo "[$(date -Is)] $*"; }

# usb_ids_for_block_device <sysfs_block_dir>
# Walks up sysfs from the block device to the USB device descriptor and prints
# "<vid> <pid>" (lowercase hex), or nothing if the device isn't on USB.
usb_ids_for_block_device() {
    local p
    p=$(realpath "$1/device" 2>/dev/null) || return
    while [[ -n $p && $p != / ]]; do
        if [[ -e $p/idVendor && -e $p/idProduct ]]; then
            echo "$(<"$p/idVendor") $(<"$p/idProduct")"
            return
        fi
        p=$(dirname "$p")
    done
}

if [[ $EUID -ne 0 ]]; then
    log "ERROR: must run as root"
    exit 1
fi

if [[ ! -x $RPI_CLONE ]]; then
    log "ERROR: $RPI_CLONE not installed (clone repo at ~/github/rpi-clone, copy to /usr/local/sbin)"
    exit 1
fi

# Multi-LUN readers expose one /dev/sdX per slot; only the slot with media has size > 0.
TARGETS=()
for blk in /sys/block/sd?; do
    [[ -e $blk ]] || continue
    name=$(basename "$blk")
    size=$(cat "$blk/size" 2>/dev/null || echo 0)
    [[ $size -gt 0 ]] || continue
    read -r vid pid < <(usb_ids_for_block_device "$blk")
    [[ $vid == "$READER_VID" && $pid == "$READER_PID" ]] || continue
    TARGETS+=("$name")
done

if [[ ${#TARGETS[@]} -eq 0 ]]; then
    log "ERROR: no populated USB SD reader (VID:PID $READER_VID:$READER_PID) found — is the spare card inserted?"
    exit 1
fi
if [[ ${#TARGETS[@]} -gt 1 ]]; then
    log "ERROR: multiple populated slots found — refusing to guess: ${TARGETS[*]}"
    exit 1
fi

TARGET=${TARGETS[0]}
log "target: /dev/$TARGET"

ROOT_SRC=$(findmnt -no SOURCE /)
if [[ $ROOT_SRC == /dev/${TARGET}* ]]; then
    log "ERROR: target $TARGET is the booted disk — refusing"
    exit 1
fi

T0=$(date +%s)
"$RPI_CLONE" "$TARGET" -U
RC=$?
T1=$(date +%s)
ELAPSED=$((T1 - T0))
log "rpi-clone finished — exit $RC — elapsed ${ELAPSED}s ($((ELAPSED/60))m $((ELAPSED%60))s)"

# rpi-clone rewrites the clone's /etc/fstab to the target's disk identifier but
# looks for cmdline.txt at /boot/cmdline.txt. On Bookworm the file lives at
# /boot/firmware/cmdline.txt, so the edit is skipped silently and the clone
# boots with root=PARTUUID=<live card>-02: the kernel loads, then waits for a
# root partition that is not there (ACT flashes, then stops; no network).
# Rewrite it here to the target's own identifier and refuse to call the clone
# good unless the rewrite is verified.
if [[ $RC -eq 0 ]]; then
    DST_ID=$(blkid -s PTUUID -o value "/dev/$TARGET")
    BOOT_PART=/dev/${TARGET}1
    [[ $TARGET == *[0-9] ]] && BOOT_PART=/dev/${TARGET}p1
    MNT=$(mktemp -d)
    if [[ -n $DST_ID ]] && mount "$BOOT_PART" "$MNT"; then
        if [[ -f $MNT/cmdline.txt ]]; then
            sed -i -E "s/root=PARTUUID=[0-9a-fA-F]{8}-02/root=PARTUUID=${DST_ID}-02/" "$MNT/cmdline.txt"
            if grep -q "root=PARTUUID=${DST_ID}-02" "$MNT/cmdline.txt"; then
                log "cmdline.txt on $BOOT_PART: root=PARTUUID=${DST_ID}-02"
            else
                log "ERROR: cmdline.txt on $BOOT_PART still does not reference PARTUUID=${DST_ID}-02 — the clone will not boot"
                RC=2
            fi
        else
            log "ERROR: no cmdline.txt on $BOOT_PART — the clone will not boot"
            RC=2
        fi
        umount "$MNT"
    else
        log "ERROR: could not read the disk identifier or mount $BOOT_PART — cmdline.txt not fixed, the clone will not boot"
        RC=2
    fi
    rmdir "$MNT"
fi

exit $RC
