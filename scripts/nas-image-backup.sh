#!/bin/bash
# Monthly incremental image-backup of the live Pi filesystem into the
# NFS-mounted .img on LookoutNas. Stops the documented set of disk-writing
# services for a clean rsync, then restarts them — even on failure.
#
# Triggered by nas-image-backup.timer; can also be run manually as root.
set -u -o pipefail

NAS_MOUNT=/mnt/nas-pi-backups
NAS_IMG=$NAS_MOUNT/pivac.img
IMG_BACKUP=/home/pi/github/RonR-RPi-image-utils/image-backup

# nginx is intentionally NOT stopped: it holds no database, so quiescing it
# adds nothing to image consistency, but stopping it blacks out the mlb.dglc.com
# bowling proxy (whose DB lives on the Mac Mini, unaffected by Pi service stops)
# and trips the Grafana mlb-availability alert every month. Leave it running.
STOP_SVCS=(pivac-1wire pivac-redlink pivac-gpio pivac-arduino-psi
           pivac-arduino-therm-psi pivac-emporia pivac-sentry
           signalk influxdb)
START_SVCS=(signalk influxdb pivac-1wire pivac-redlink pivac-gpio
            pivac-arduino-psi pivac-arduino-therm-psi pivac-emporia pivac-sentry)

log() { echo "[$(date -Is)] $*"; }

if [[ $EUID -ne 0 ]]; then
    log "ERROR: must run as root"
    exit 1
fi

if ! mountpoint -q "$NAS_MOUNT"; then
    log "mounting $NAS_MOUNT"
    mount "$NAS_MOUNT" || { log "ERROR: mount failed"; exit 1; }
fi

if [[ ! -f $NAS_IMG ]]; then
    log "ERROR: $NAS_IMG missing — refusing to bootstrap from a timer"
    exit 1
fi

trap 'log "restarting services"; systemctl start "${START_SVCS[@]}" || true' EXIT

log "stopping services: ${STOP_SVCS[*]}"
systemctl stop "${STOP_SVCS[@]}"

log "starting incremental against $NAS_IMG"
T0=$(date +%s)
# Exclude /home/pi/thinclient_drives: an xrdp-chansrv FUSE mount created by an
# active RDP session. root cannot traverse the FUSE mount, so rsync returns
# exit 23 and image-backup aborts — even though all real data transferred. It
# holds remote drive-redirection data that has no place in a Pi image anyway.
"$IMG_BACKUP" -o '--exclude=/home/pi/thinclient_drives' "$NAS_IMG"
RC=$?
T1=$(date +%s)
ELAPSED=$((T1 - T0))
log "incremental finished — exit $RC — elapsed ${ELAPSED}s ($((ELAPSED/60))m $((ELAPSED%60))s)"

exit $RC
