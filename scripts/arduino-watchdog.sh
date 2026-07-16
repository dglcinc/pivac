#!/usr/bin/env bash
#
# arduino-watchdog.sh — auto-recover the two UNO R4 WiFi pressure boards.
#
# The DHW (10.0.0.114) and boiler/hydronic (10.0.0.219) pressure Arduinos share the
# "Arduinos" Shelly Plug US Gen4 at 10.0.0.61. After a power event they occasionally fail to
# rejoin WiFi and sit dark until the plug is power-cycled (observed 2026-07-16: a mains blip
# rebooted the Pi + both boards; the .219 board stayed unreachable for 16h with no auto-recovery
# and no alert until manually power-cycled). Their pivac services have Restart=always, but that
# cannot help — the service is not crashing, the board is off the network.
#
# This watchdog closes that gap: run on a 5-minute systemd timer, it pings both boards and, if
# EITHER has been unreachable for a sustained period (DOWN_THRESHOLD_S), power-cycles the Shelly
# once (rate-limited by CYCLE_MIN_INTERVAL_S) to force both boards to reboot and re-associate.
# Cycling the shared plug briefly drops the healthy board too; it recovers in seconds.
#
# State lives in tmpfs (/run) so it resets on reboot — after a reboot the boards get a fresh
# grace period rather than being cycled on stale state. Logs go to journald (systemctl status /
# journalctl -u arduino-watchdog). It NEVER touches the Pi's own power (that is a different
# Shelly, 10.0.0.118) — only the Arduinos' plug.
#
# Tunables (env-overridable for testing):
set -euo pipefail

# Board list is env-overridable (space-separated) for testing; default = the two real boards.
read -ra BOARDS <<< "${BOARDS_STR:-10.0.0.114 10.0.0.219}"  # DHW, boiler/hydronic pressure boards
SHELLY="${SHELLY:-10.0.0.61}"            # "Arduinos" plug, open local RPC (auth disabled)
SHELLY_SWITCH_ID="${SHELLY_SWITCH_ID:-0}"
DOWN_THRESHOLD_S="${DOWN_THRESHOLD_S:-900}"      # board(s) must be down this long before cycling (15m)
CYCLE_MIN_INTERVAL_S="${CYCLE_MIN_INTERVAL_S:-3600}"  # min seconds between power cycles (1h)
OFF_DWELL_S="${OFF_DWELL_S:-8}"          # seconds to hold power off during a cycle
CURL_TIMEOUT_S="${CURL_TIMEOUT_S:-5}"
PROBE_RETRIES="${PROBE_RETRIES:-2}"      # extra probes before declaring a board down (guards a dropped packet)

STATE_DIR="${STATE_DIR:-/run/arduino-watchdog}"
DOWN_FILE="$STATE_DIR/first_down"        # epoch when we first saw any board down (absent = all healthy)
LAST_CYCLE_FILE="$STATE_DIR/last_cycle"  # epoch of the last power cycle

mkdir -p "$STATE_DIR"

log() { echo "$*"; }
now() { date +%s; }

# Return 0 if the board answers HTTP, 1 otherwise. Retries to avoid a single dropped packet.
board_up() {
    local ip="$1" i code
    for ((i = 0; i <= PROBE_RETRIES; i++)); do
        code="$(curl -s -m "$CURL_TIMEOUT_S" -o /dev/null -w '%{http_code}' "http://$ip/" || true)"
        [[ "$code" == "200" ]] && return 0
        ((i < PROBE_RETRIES)) && sleep 3
    done
    return 1
}

# Identify which boards are down.
down_boards=()
for b in "${BOARDS[@]}"; do
    if ! board_up "$b"; then
        down_boards+=("$b")
    fi
done

# All healthy -> clear the down timer and exit quietly (no log spam on the happy path).
if ((${#down_boards[@]} == 0)); then
    rm -f "$DOWN_FILE"
    exit 0
fi

T_NOW="$(now)"

# First time we see a board down: start the timer, don't act yet (let the firmware's own
# reconnect / a transient WiFi blip resolve on its own).
if [[ ! -f "$DOWN_FILE" ]]; then
    echo "$T_NOW" > "$DOWN_FILE"
    log "Board(s) unreachable: ${down_boards[*]} — starting down-timer (will cycle after ${DOWN_THRESHOLD_S}s if not recovered)"
    exit 0
fi

FIRST_DOWN="$(cat "$DOWN_FILE")"
DOWN_FOR=$((T_NOW - FIRST_DOWN))

if ((DOWN_FOR < DOWN_THRESHOLD_S)); then
    log "Board(s) still unreachable: ${down_boards[*]} — down ${DOWN_FOR}s (< ${DOWN_THRESHOLD_S}s threshold), waiting"
    exit 0
fi

# Down long enough to warrant a power cycle. Enforce the rate limit.
if [[ -f "$LAST_CYCLE_FILE" ]]; then
    LAST_CYCLE="$(cat "$LAST_CYCLE_FILE")"
    SINCE_CYCLE=$((T_NOW - LAST_CYCLE))
    if ((SINCE_CYCLE < CYCLE_MIN_INTERVAL_S)); then
        log "Board(s) unreachable ${DOWN_FOR}s: ${down_boards[*]} — but last power-cycle was ${SINCE_CYCLE}s ago (< ${CYCLE_MIN_INTERVAL_S}s); rate-limited, not cycling. Likely a board that reboots but won't rejoin — check it physically."
        exit 0
    fi
fi

log "Board(s) unreachable ${DOWN_FOR}s: ${down_boards[*]} — power-cycling Shelly $SHELLY (id $SHELLY_SWITCH_ID)"
if ! curl -s -m "$CURL_TIMEOUT_S" "http://$SHELLY/rpc/Switch.Set?id=${SHELLY_SWITCH_ID}&on=false" > /dev/null; then
    log "WARNING: failed to reach Shelly $SHELLY to turn OFF — is the plug online? Not clearing state; will retry next tick."
    exit 0
fi
sleep "$OFF_DWELL_S"
if ! curl -s -m "$CURL_TIMEOUT_S" "http://$SHELLY/rpc/Switch.Set?id=${SHELLY_SWITCH_ID}&on=true" > /dev/null; then
    log "WARNING: failed to turn Shelly $SHELLY back ON — retrying once"
    curl -s -m "$CURL_TIMEOUT_S" "http://$SHELLY/rpc/Switch.Set?id=${SHELLY_SWITCH_ID}&on=true" > /dev/null || \
        log "ERROR: Shelly $SHELLY still not reachable to turn ON — the plug itself may be offline; manual intervention needed."
fi

echo "$T_NOW" > "$LAST_CYCLE_FILE"
# Clear the down timer so the boards get a fresh grace period to boot + rejoin before we
# re-evaluate; the rate limit is the real guard against a tight cycle loop.
rm -f "$DOWN_FILE"
log "Power cycle issued; boards rebooting. Cleared down-timer; next cycle not before ${CYCLE_MIN_INTERVAL_S}s from now."
