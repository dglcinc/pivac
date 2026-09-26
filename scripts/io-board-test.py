#!/usr/bin/env python3
"""Channel-by-channel bench test for the Raspberry Pi I/O board.

Run this on the bench Pi with the board seated on the header and the sense supply
powered (24 VAC on J4.1/J4.2 for the rev A PCB, the 14 V wall wart for the
perfboard). It sets every channel's GPIO to input with pull-up, checks that all
of them idle high, then walks the channels in plug order: short the named plug
position to its COM, and the script reports PASS when that channel's pin goes
low. It also reports any *other* pin that dropped at the same time, which is the
signature of a solder bridge on the LED row, and it refuses to move on until the
short is released, so each channel is proven both ways.

No pivac install needed. Uses `pinctrl` (Trixie, Pi 4 and Pi 5) or falls back to
`raspi-gpio`. Stdlib only.

    sudo python3 io-board-test.py            # guided walk-through, rev A PCB map
    sudo python3 io-board-test.py --monitor  # live table of all channels
    sudo python3 io-board-test.py --only 5   # guided, one channel (by # column)
    sudo python3 io-board-test.py --perfboard  # the original perfboard's map
    sudo python3 io-board-test.py --led      # mirror the walk on the Pi's ACT LED

With --led the green ACT LED shows the walk from the bench, so no terminal has to
be watched: it lights while a short is being read and goes out on release, it
flickers if another channel dropped with it (a bridge), two blinks close the idle
check, three slow blinks end a clean walk and five fast ones a walk with a
failure. The LED's mmc0 trigger is restored on exit.

The rev A map is docs/rpi-io-boards-assembly.md (SP-C and SP-E have no plug: short
the J8 pad to the J8 COM pad). The perfboard map is §2.1 of
docs/rpi-io-board-design.md.
"""
import argparse
import select
import shutil
import subprocess
import sys
import time

# (#, name, chip·ch, plug position, BCM) for the rev A PCB
CHANNELS_REVA = [
    (1,  "ZV",     "U1", "J1.1", 17),
    (2,  "DHW",    "U1", "J1.2", 27),
    (3,  "BLR",    "U1", "J1.3", 22),
    (4,  "CHIL",   "U1", "J2.1", 25),
    (5,  "BOS1",   "U2", "J2.2", 6),
    (6,  "BOS2",   "U2", "J2.3", 5),
    (7,  "DEHUM",  "U2", "J3.1", 12),
    (8,  "SCALA",  "U2", "J3.2", 23),
    (9,  "HPHEAT", "U3", "J3.3", 24),
    (10, "SP-D",   "U3", "J4.3", 19),
    (11, "SP-C",   "U3", "J8",   13),
    (12, "SP-E",   "U3", "J8",   16),
]

# (#, name, IC·ch, plug position, BCM) for the original perfboard
CHANNELS_PERF = [
    (1,  "ZV",    "A·4", "J1.1", 17),
    (2,  "DHW",   "A·3", "J1.2", 27),
    (3,  "BLR",   "A·2", "J1.3", 22),
    (4,  "CHIL",  "A·1", "J2.1", 25),
    (5,  "BOS1",  "B·3", "J2.2", 6),
    (6,  "BOS2",  "B·2", "J2.3", 5),
    (7,  "DEHUM", "B·1", "J3.1", 12),
    (8,  "SCALA", "C·1", "J3.2", 23),
    (9,  "SP-B",  "C·2", "J3.3", 24),
    (10, "SP-C",  "C·4", "J4.2", 13),
    (11, "SP-D",  "C·3", "J4.3", 19),
]
CHANNELS = CHANNELS_REVA
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


class Led:
    """The Pi's green ACT LED as a bench indicator (no-op without --led)."""
    PATH = "/sys/class/leds/ACT"

    def __init__(self, enabled):
        self.enabled = enabled
        self.old = None
        if not enabled:
            return
        try:
            with open(f"{self.PATH}/trigger") as f:
                self.old = f.read().split("[", 1)[1].split("]", 1)[0]
            self._write("trigger", "none")
            self.off()
        except OSError as e:
            print(f"--led: cannot drive {self.PATH} ({e}); continuing without it")
            self.enabled = False

    def _write(self, name, value):
        with open(f"{self.PATH}/{name}", "w") as f:
            f.write(value)

    def on(self):
        if self.enabled:
            self._write("brightness", "1")

    def off(self):
        if self.enabled:
            self._write("brightness", "0")

    def blink(self, n, on_s, off_s=None):
        if not self.enabled:
            return
        for _ in range(n):
            self.on()
            time.sleep(on_s)
            self.off()
            time.sleep(off_s if off_s is not None else on_s)

    def restore(self):
        if self.enabled and self.old:
            self.off()
            self._write("trigger", self.old)


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


def guided(be, only, led):
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
        led.blink(2, 0.15)

    print("For each channel, short the plug position to that plug's COM (position 4;\n"
          "J8 channels: the J8 pad to the J8 COM pad).\n"
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
            led.blink(8, 0.06)
        else:
            print("ACTIVE -> PASS", end="", flush=True)
            results[n] = "pass"
        led.on()
        print("   release ... ", end="", flush=True)
        levels, key = stable_read(be, bcm, 1)
        led.off()
        if key == "q":
            break
        print("idle")

    print("\nsummary")
    for ch in chans:
        print("  " + fmt_row(ch, 1 if results.get(ch[0]) != "pass" else 0,
                             results.get(ch[0], "not tested")))
    print("\nA channel whose IR LED lights but never goes ACTIVE is chip seating or\n"
          "orientation. One that does neither is on the field side: resistor, plug\n"
          "link, or the sense-supply feed (VS) to that chip.")
    ok = all(v == "pass" for v in results.values())
    led.blink(3, 0.5) if ok else led.blink(5, 0.1)
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--monitor", action="store_true", help="live table instead of guided walk")
    ap.add_argument("--only", type=int, help="guided test of one channel (# column)")
    ap.add_argument("--perfboard", action="store_true",
                    help="use the original perfboard's channel map instead of rev A")
    ap.add_argument("--led", action="store_true",
                    help="mirror the walk on the Pi's green ACT LED (see the module doc)")
    args = ap.parse_args()
    global CHANNELS, BCMS
    if args.perfboard:
        CHANNELS = CHANNELS_PERF
        BCMS = [c[4] for c in CHANNELS]
    be = Backend()
    be.set_pullups()
    print(f"using {be.tool}; pull-ups set on BCM {BCMS}")
    if args.monitor:
        monitor(be)
        return 0
    led = Led(args.led)
    try:
        return guided(be, args.only, led)
    finally:
        led.restore()


if __name__ == "__main__":
    sys.exit(main())
