#!/bin/bash
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
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
# Every pivac unit has Requires=signalk.service, so stopping signalk stops them
# all regardless of this list — but any service missing from START_SVCS stays
# dead after the backup. Keep both lists in sync with the Active Services table
# in CLAUDE.md (learned 2026-09-01: loop-delta, sprinkler, domestic-water and
# chiltrix were down 4.5h+ after the monthly run).
STOP_SVCS=(pivac-1wire pivac-redlink pivac-gpio pivac-arduino-psi
           pivac-arduino-therm-psi pivac-emporia pivac-sentry
           pivac-sprinkler pivac-domestic-water pivac-chiltrix pivac-loop-delta
           pivac-grafana-alerts pivac-ah-mbr pivac-ah-utility pivac-scb-utility signalk influxdb)
START_SVCS=(signalk influxdb pivac-1wire pivac-redlink pivac-gpio
            pivac-arduino-psi pivac-arduino-therm-psi pivac-emporia pivac-sentry
            pivac-sprinkler pivac-domestic-water pivac-chiltrix pivac-loop-delta
            pivac-grafana-alerts pivac-ah-mbr pivac-ah-utility pivac-scb-utility)

log() { echo "[$(date -Is)] $*"; }

# Stopping InfluxDB makes every Grafana rule's query fail, and each rule alerts
# on a query error after a minute, so the stop would email and push about 18
# stale alerts at 3 am. A silence covers both paths: the email bridge never
# hears of a silenced alert and pivac.GrafanaAlerts publishes it as normal. The
# silence expires by itself, so a backup that hangs or dies still alerts, and
# an alert still firing when it ends is notified then. Failure to set it never
# stops the backup. Grafana stays up throughout, since it is not in STOP_SVCS.
SILENCE_API=http://127.0.0.1:4000/grafana/api/alertmanager/grafana/api/v2/silences
SILENCE_KEY=/home/pi/.config/grafana-claude-agent.key
SILENCE_MATCH='.+'      # every rule: all of them query InfluxDB
SILENCE_LIMIT_MIN=60    # set before the stop; a run past this alerts
SILENCE_TAIL_MIN=15     # after the restart, while the sources republish
SILENCE_ID=""

# set_silence MINUTES: create the silence, or move its end if it exists.
set_silence() {
    local body resp id
    body=$(python3 -c '
import datetime as dt, json, sys
now = dt.datetime.now(dt.timezone.utc)
stamp = lambda t: t.strftime("%Y-%m-%dT%H:%M:%SZ")
out = {"matchers": [{"name": "alertname", "value": sys.argv[1], "isRegex": True, "isEqual": True}],
       "startsAt": stamp(now), "endsAt": stamp(now + dt.timedelta(minutes=int(sys.argv[2]))),
       "createdBy": "nas-image-backup", "comment": "Monthly image backup stops InfluxDB"}
if sys.argv[3]:
    out["id"] = sys.argv[3]
print(json.dumps(out))' "$SILENCE_MATCH" "$1" "$SILENCE_ID") || return 1
    # The token goes through a file descriptor to stay out of the process list.
    resp=$(curl -sS --max-time 10 --fail-with-body \
        --config <(printf 'header = "Authorization: Bearer %s"\n' "$(cat "$SILENCE_KEY")") \
        -H 'Content-Type: application/json' -d "$body" "$SILENCE_API") \
        || { log "WARNING: could not set Grafana silence: $resp"; return 1; }
    id=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["silenceID"])' "$resp") \
        || { log "WARNING: unexpected Grafana silence reply: $resp"; return 1; }
    SILENCE_ID=$id
    log "Grafana silence $id ends in $1 min"
}

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

set_silence "$SILENCE_LIMIT_MIN"

on_exit() {
    log "restarting services"
    systemctl start "${START_SVCS[@]}" || true
    [[ -n $SILENCE_ID ]] && set_silence "$SILENCE_TAIL_MIN"
}
trap on_exit EXIT

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
