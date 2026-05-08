#!/bin/bash
# Weekly hot-recovery clone of the live Pi filesystem to the USB-attached
# spare microSD. Used for fast card-death recovery: pull live SD, drop spare
# in, reboot. rpi-clone runs on a live system; no service stop needed.
#
# Triggered by sd-clone.timer; can also be run manually as root.
set -u -o pipefail

READER_MODEL=NS-DCR30A2
RPI_CLONE=/usr/local/sbin/rpi-clone

log() { echo "[$(date -Is)] $*"; }

if [[ $EUID -ne 0 ]]; then
    log "ERROR: must run as root"
    exit 1
fi

if [[ ! -x $RPI_CLONE ]]; then
    log "ERROR: $RPI_CLONE not installed (clone repo at ~/github/rpi-clone, copy to /usr/local/sbin)"
    exit 1
fi

# The Insignia NS-DCR30A2 is a 4-LUN reader; only the slot with media has size > 0.
TARGETS=()
for blk in /sys/block/sd?; do
    [[ -e $blk ]] || continue
    name=$(basename "$blk")
    model=$(cat "$blk/device/model" 2>/dev/null | tr -d ' ')
    size=$(cat "$blk/size" 2>/dev/null || echo 0)
    [[ $model == "$READER_MODEL" ]] || continue
    [[ $size -gt 0 ]] || continue
    TARGETS+=("$name")
done

if [[ ${#TARGETS[@]} -eq 0 ]]; then
    log "ERROR: no populated $READER_MODEL slot found — is the spare card inserted?"
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

exit $RC
