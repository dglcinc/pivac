# Pivac Project — Claude Code Instructions

## What This Project Is
Pivac is a Python application running on a Raspberry Pi (hostname: `pivac`) that reads data from
various sensors and devices and pushes it to a SignalK v2 server via WebSocket. SignalK stores
data in InfluxDB and it is visualized in Grafana and the WilhelmSK mobile app.

## Architecture
- **pivac-provider.py**: Main daemon. Loads a sensor module, calls its `status()` function in a
  loop, and sends SignalK delta JSON over WebSocket to the local SignalK server.
- **pivac/ modules**: One Python module per device type. Each implements `status(config, output)`
  and returns a SignalK delta dict.
- **config**: `/etc/pivac/config.yml` — one section per module plus a `signalk:` section with
  connection credentials.
- **SignalK**: Runs as `signalk` systemd service on localhost:3000.

## Active Sensor Modules and Services
| systemd service         | Module                  | Device                          | IP           |
|-------------------------|-------------------------|---------------------------------|--------------|
| pivac-1wire             | pivac.OneWireTherm      | 1-wire temperature sensors      | GPIO         |
| pivac-redlink           | pivac.RedLink           | Honeywell thermostat (web)      | internet     |
| pivac-gpio              | pivac.GPIO              | GPIO input pins (relays/switches)| GPIO        |
| pivac-arduino-psi       | pivac.ArduinoPSI        | Hydronic pressure (Fusch 100PSI)| 10.0.0.114   |
| pivac-arduino-therm-psi | pivac.ArduinoThermPSI   | DHW pressure (Fusch 200PSI)     | 10.0.0.219   |

## Key File Locations
- Pivac code: `~/github/pivac/`
- Config: `/etc/pivac/config.yml`
- Systemd services: `/etc/systemd/system/pivac-*.service`
- SignalK config: `~/.signalk/`
- Python venv: `~/pivac-venv/`

## Standard Deployment Procedure
After a `git pull`, run the following to deploy changes:
```bash
sudo systemctl restart pivac-1wire pivac-redlink pivac-gpio pivac-arduino-psi pivac-arduino-therm-psi
sudo systemctl status pivac-1wire pivac-redlink pivac-gpio pivac-arduino-psi pivac-arduino-therm-psi
journalctl -u pivac-1wire -u pivac-redlink -u pivac-gpio -u pivac-arduino-psi -u pivac-arduino-therm-psi -n 50
```

If systemd service files were changed:
```bash
sudo cp ~/github/pivac/scripts/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
```

## Checking Logs
```bash
# All pivac services together
journalctl -u pivac-1wire -u pivac-redlink -u pivac-gpio -u pivac-arduino-psi -u pivac-arduino-therm-psi -n 50

# Single service
journalctl -u pivac-redlink -n 50

# SignalK server
journalctl -u signalk -n 50
```

## Known Operational Behaviours (Not Bugs)
- **Arduino timeouts**: Both Arduinos (10.0.0.114 and 10.0.0.219) occasionally go unresponsive.
  Logged as a single WARNING line. Self-recover; occasional power cycle needed.
- **RedLink ConnectionResetError**: Honeywell's server occasionally drops HTTPS connections.
  Self-recovering. Logged as ERROR but normal.
- **OneWireTherm SensorNotReadyError**: 1-wire sensors occasionally not ready mid-conversion.
  Transient, self-recovering.

## SignalK Upgrade (if needed)
The admin console upgrade fails with ENOTEMPTY. Use the manual procedure:
```bash
sudo systemctl stop signalk
sudo rm -rf /usr/lib/node_modules/.signalk-server-*
sudo npm install -g signalk-server@latest
sudo systemctl start signalk
```

## Python Environment
Always use the pivac venv:
```bash
source ~/pivac-venv/bin/activate
pip install <package> --break-system-packages
```
