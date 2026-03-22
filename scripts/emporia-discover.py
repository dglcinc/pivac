#!/usr/bin/env python3
"""
emporia-discover.py — List all Emporia devices and circuits on your account.

Run this once to find your device GIDs and circuit names so you can populate
the pivac.Emporia section in /etc/pivac/config.yml.

Usage:
    source ~/pivac-venv/bin/activate
    python scripts/emporia-discover.py --username YOUR_EMAIL --password YOUR_PASSWORD

Or, if PIVAC_CFG (or /etc/pivac/config.yml) already has a pivac.Emporia section
with username/password filled in:
    python scripts/emporia-discover.py
"""

import argparse
import sys
import os


def load_credentials_from_config():
    """Try to pull username/password from the pivac config file."""
    try:
        import yaml
        cfg_file = os.environ.get('PIVAC_CFG', '/etc/pivac/config.yml')
        with open(cfg_file, 'r') as f:
            cfg = yaml.load(f.read(), Loader=yaml.FullLoader)
        emporia_cfg = cfg.get('pivac.Emporia', {})
        return emporia_cfg.get('username'), emporia_cfg.get('password')
    except Exception:
        return None, None


def main():
    parser = argparse.ArgumentParser(description='Discover Emporia devices and circuit names')
    parser.add_argument('--username', help='Emporia account email')
    parser.add_argument('--password', help='Emporia account password')
    args = parser.parse_args()

    username = args.username
    password = args.password

    if not username or not password:
        cfg_user, cfg_pass = load_credentials_from_config()
        username = username or cfg_user
        password = password or cfg_pass

    if not username or not password:
        print("ERROR: username and password are required.")
        print("Provide --username / --password, or add them to pivac.Emporia in your config file.")
        sys.exit(1)

    try:
        import pyemvue
    except ImportError:
        print("ERROR: pyemvue is not installed. Run: pip install pyemvue --break-system-packages")
        sys.exit(1)

    print("Authenticating with Emporia API...")
    vue = pyemvue.PyEmVue()
    try:
        ok = vue.login(username=username, password=password)
    except Exception as e:
        print("ERROR: Authentication failed: %s" % e)
        sys.exit(1)
    if not ok:
        print("ERROR: Authentication failed: incorrect username or password?")
        sys.exit(1)

    print("Fetching devices...\n")
    devices = vue.get_devices()
    for device in devices:
        vue.populate_device_properties(device)

    if not devices:
        print("No devices found on this account.")
        sys.exit(0)

    print("Found %d device(s):\n" % len(devices))
    print("=" * 60)

    for device in devices:
        print("Device: %s" % (device.device_name or "(unnamed)"))
        print("  GID:            %s" % device.device_gid)
        print("  Model:          %s" % (device.model or "unknown"))
        print("  Firmware:       %s" % (device.firmware or "unknown"))
        print("  Location:       %s" % (device.location_name or "unknown"))
        print()

        if device.channels:
            print("  Channels:")
            for ch in sorted(device.channels, key=lambda c: c.channel_num):
                print("    [%2s]  %s" % (ch.channel_num, ch.name or "(unnamed)"))
        else:
            print("  No channels found (try running after a short delay)")
        print()

    print("=" * 60)
    print()
    print("Add the following to your /etc/pivac/config.yml:\n")
    print("pivac.Emporia:")
    print("    description: Reports power consumption from Emporia Vue panels")
    print("    enabled: true")
    print("    daemon_sleep: 60")
    print("    username: %s" % username)
    print("    password: YOUR_PASSWORD")
    print("    token_file: /etc/pivac/emporia-tokens.json")
    print("    sk_path: electrical.emporia")
    print("    panels:")
    for device in devices:
        suggested_name = (device.location_name or device.device_name or 'panel').lower().replace(' ', '_')
        print('        "%s": %s  # %s' % (
            device.device_gid,
            suggested_name,
            device.device_name or "(unnamed)"
        ))


if __name__ == '__main__':
    main()
