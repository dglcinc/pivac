#!/usr/bin/env bash
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
#
# The one list of pivac units in service, and the commands that act on all of
# them. scripts/nas-image-backup.sh keeps its own copies of this list because
# it must run with no dependencies; tests/test_claude_md_size.py fails if the
# three disagree.
#
#   pivac-services.sh restart      restart every pivac unit
#   pivac-services.sh stop         stop every pivac unit
#   pivac-services.sh start        start every pivac unit
#   pivac-services.sh stop-all     pivac units, then signalk, influxdb, nginx
#                                  (before SD card maintenance or rsync)
#   pivac-services.sh logs [N]     last N journal lines across every unit (50)
#   pivac-services.sh status       one line per unit
#   pivac-services.sh list         print the unit names
set -euo pipefail

PIVAC_SVCS=(pivac-1wire pivac-redlink pivac-gpio pivac-arduino-psi
            pivac-arduino-therm-psi pivac-emporia pivac-sentry
            pivac-sprinkler pivac-domestic-water pivac-chiltrix pivac-loop-delta
            pivac-grafana-alerts pivac-ah-mbr pivac-ah-utility pivac-scb-utility pivac-scb-mbr
            pivac-ah-greatroom pivac-scb-greatroom pivac-ah-kids pivac-scb-kids
            pivac-ah-kitchen pivac-scb-kitchen)

case "${1:-}" in
  restart|stop|start)
    sudo systemctl "$1" "${PIVAC_SVCS[@]}"
    ;;
  stop-all)
    # Order matters: the pivac units push to Signal K, Signal K feeds InfluxDB,
    # and nginx goes last because it carries the external connections.
    sudo systemctl stop "${PIVAC_SVCS[@]}"
    sudo systemctl stop signalk
    sudo systemctl stop influxdb
    sudo systemctl stop nginx
    ;;
  logs)
    args=()
    for s in "${PIVAC_SVCS[@]}"; do args+=(-u "$s"); done
    journalctl "${args[@]}" -n "${2:-50}" --no-pager
    ;;
  status)
    for s in "${PIVAC_SVCS[@]}"; do
      printf '%-26s %s\n' "$s" "$(systemctl is-active "$s" 2>/dev/null || true)"
    done
    ;;
  list)
    printf '%s\n' "${PIVAC_SVCS[@]}"
    ;;
  *)
    sed -n '10,17p' "$0" | sed 's/^# \{0,3\}//'
    exit 2
    ;;
esac
