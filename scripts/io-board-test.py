#!/usr/bin/env python3
"""Channel-by-channel bench test for the Raspberry Pi I/O board.

Run this on the bench Pi with the board seated on the header and the 14 V wall
wart powered. It sets every channel's GPIO to input with pull-up, checks that all
of them idle high, then walks the channels in plug order: short the named plug
position to its COM, and the script reports PASS when that channel's pin goes
low. It also reports any *other* pin that dropped at the same time, which is the
signature of a solder bridge on the LED row, and it refuses to move on until the
short is released, so each channel is proven both ways.

No pivac install needed. Uses `pinctrl` (Trixie, Pi 4 and Pi 5) or falls back to
`raspi-gpio`. Stdlib only.

    sudo python3 io-board-test.py            # guided walk-through
    sudo python3 io-board-test.py --monitor  # live table of all channels
    sudo python3 io-board-test.py --only 5   # guided, one channel (by # column)

Channel map is §2.1 of docs/rpi-io-board-design.md.
"""
import argparse
import select
import shutil
import subprocess
import sys
import time

# (#, name, IC·ch, plug position, BCM)
CHANNELS = [
    (1,  "ZV",    "A·4", "J1.1", 17),
    (2,  "DHW",   "A·3", "J1.2", 27),
    (3,  "BLR",   "A·2", "J1.3", 22),
    (4,  "CHIL",  "A·1", "J2.1", 25),
    (5,  "BOS1",  "B·3", "J2.2", 6),
    (6,  "BOS2",  "B·2", "J2.3", 5),
    (7,  "DEHUM", "B·1", "J3.1", 12),
    (8,  "SP-A",  "C·1", "J3.2", 23),
    (9,  "SP-B",  "C·2", "J3.3", 24),
    (10, "SP-C",  "C·4", "J4.2", 13),
    (11, "SP-D",  "C·3", "J4.3", 19),
]
BCMS = [c[4] for c in CHANNELS]

POLL_S = 0.05        # read interval
DEBOUNCE = 4         # consecutive reads required in a state before it counts


class Backend:
    """Read GPIO levels through whichever CLI the OS ships."""

    def __init__(self):
        if shutil.which("pinctrl"):
            self.tool = "pinctrl"
        elif shutil.which("raspi-gpio"):
            self.tool = "raspi-gpio"
        else:
            sys.exit("need pinctrl or raspi-gpio on PATH (apt install raspi-utils)")

    def set_pullups(self):
        for bcm in BCMS:
            if self.tool == "pinctrl":
                subprocess.run(["pinctrl", "set", str(bcm), "ip", "pu"], check=True)
            else:
                subprocess.run(["raspi-gpio", "set", str(bcm), "ip", "pu"], check=True)

    def read(self):
        """Return {bcm: level} with level 0 or 1."""
        pins = ",".join(str(b) for b in BCMS)
        out = subprocess.run([self.tool, "get", pins], capture_output=True,
                             text=True, check=True).stdout
        levels = {}
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            if self.tool == "pinctrl":
                # " 17: ip    pu | hi // GPIO17 = input"
                bcm = int(line.split(":")[0])
                levels[bcm] = 1 if "| hi" in line else 0
            else:
                # "GPIO 17: level=1 fsel=0 func=INPUT pull=UP"
                bcm = int(line.split(":")[0].split()[1])
                levels[bcm] = int(line.split("level=")[1].split()[0])
        missing = [b for b in BCMS if b not in levels]
        if missing:
            sys.exit(f"could not read BCM {missing}: {out!r}")
        return levels


def key_pressed():
    """Return the pending keystroke, or None (non-blocking, line-buffered)."""
    if not sys.stdin.isatty():
        return None
    r, _, _ = select.select([sys.stdin], [], [], 0)
    if r:
        return sys.stdin.readline().strip().lower()
    return None


def stable_read(be, want_bcm=None, want_level=None):
    """Poll until the required pin sits at want_level for DEBOUNCE reads, or a
    key is pressed. Returns (levels, key)."""
    run = 0
    while True:
        levels = be.read()
        key = key_pressed()
        if key is not None:
            return levels, key
        if want_bcm is None:
            return levels, None
        run = run + 1 if levels[want_bcm] == want_level else 0
        if run >= DEBOUNCE:
            return levels, None
        time.sleep(POLL_S)


def fmt_row(ch, level, mark=""):
    n, name, ic, plug, bcm = ch
    state = "ACTIVE" if level == 0 else "idle  "
    return f"{n:>2}  {name:<6} {ic:<4} {plug:<5} BCM{bcm:<3} {state} {mark}"


def monitor(be):
    print("live view; Ctrl-C to stop\n")
    seen = set()
    try:
        while True:
            levels = be.read()
            rows = []
            for ch in CHANNELS:
                if levels[ch[4]] == 0:
                    seen.add(ch[0])
                rows.append(fmt_row(ch, levels[ch[4]], "*" if ch[0] in seen else ""))
            active = [c[1] for c in CHANNELS if levels[c[4]] == 0]
            print("\033[2J\033[H", end="")
            print(" #  name   IC   plug  pin    state  (* = seen active)")
            print("\n".join(rows))
            print(f"\nactive now: {active or 'none'}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print()


def guided(be, only):
    chans = [c for c in CHANNELS if only is None or c[0] == only]
    results = {}

    print("idle check: nothing shorted, wart powered ...")
    levels, _ = stable_read(be)
    stuck = [c for c in chans if levels[c[4]] == 0]
    if stuck:
        for c in stuck:
            print("  " + fmt_row(c, 0, "<- LOW AT IDLE"))
        print("A channel low with nothing shorted is a field conductor shorted to COM,\n"
              "a bridge on the LED row, or a chip in backwards. Fix before continuing.")
        if input("continue anyway? [y/N] ").strip().lower() != "y":
            return 1
    else:
        print(f"  all {len(chans)} channels idle high\n")

    print("For each channel, short the plug position to that plug's COM (position 4).\n"
          "Type s<Enter> to skip a channel, q<Enter> to quit.\n")
    for ch in chans:
        n, name, ic, plug, bcm = ch
        print(f"[{n:>2}/{len(CHANNELS)}] short {plug} to COM   ({name}, {ic}, BCM{bcm}) ... ",
              end="", flush=True)
        levels, key = stable_read(be, bcm, 0)
        if key == "q":
            break
        if key == "s":
            print("skipped")
            results[n] = "skip"
            continue
        others = [c[1] for c in CHANNELS if c[4] != bcm and levels[c[4]] == 0]
        if others:
            print(f"ACTIVE, but so is {others} -> BRIDGE or crossed wire")
            results[n] = f"fail (also {others})"
        else:
            print("ACTIVE -> PASS", end="", flush=True)
            results[n] = "pass"
        print("   release ... ", end="", flush=True)
        levels, key = stable_read(be, bcm, 1)
        if key == "q":
            break
        print("idle")

    print("\nsummary")
    for ch in chans:
        print("  " + fmt_row(ch, 1 if results.get(ch[0]) != "pass" else 0,
                             results.get(ch[0], "not tested")))
    print("\nA channel whose IR LED lights but never goes ACTIVE is chip seating or\n"
          "orientation (IC-C is rotated). One that does neither is on the field side:\n"
          "resistor, plug link, or the +14 V feeder to that chip.")
    return 0 if all(v == "pass" for v in results.values()) else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--monitor", action="store_true", help="live table instead of guided walk")
    ap.add_argument("--only", type=int, help="guided test of one channel (# column)")
    args = ap.parse_args()
    be = Backend()
    be.set_pullups()
    print(f"using {be.tool}; pull-ups set on BCM {BCMS}")
    if args.monitor:
        monitor(be)
        return 0
    return guided(be, args.only)


if __name__ == "__main__":
    sys.exit(main())
