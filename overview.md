# pivac — Overview

Python library and daemon for monitoring a custom HVAC system via Raspberry Pi.

## Repo

`dglcinc/pivac` — [github.com/dglcinc/pivac](https://github.com/dglcinc/pivac)

Local clone: `~/github/pivac` (Mac), `~/github/pivac` (Pi)

## What it does

Reads HVAC sensor data (Emporia energy monitor, Sentry boiler controller) and publishes to SignalK, which feeds Grafana dashboards.

## Key services (on Pi)

| Service | Description |
|---------|-------------|
| `pivac-emporia.service` | PyEmVue API poller for Emporia energy monitor |
| `pivac-sentry.service` | Sentry boiler controller reader |

## Grafana dashboards

- Apartment Power panel — air_cond, furnace, garage/entry/basement circuits
- House Power panel — wall oven, Bosch BOVA
- Sentry Boiler Values / Sentry Boiler Status

## Load context for Claude

"set context pivac" — reads this file + `~/github/pivac/CLAUDE.md`

## Current state (2026-04-26)

All services running. No open PRs. SD card upgraded to 128GB (2026-04-19).
