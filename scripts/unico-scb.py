#!/usr/bin/env python3
"""Talk to a Unico S.M.A.R.T. Control Board (SCB) through its A01470 USB board.

The SCB is the bus master. It sends a status frame to the PC on its own and the PC
answers each one; there are no query commands. Every answer is a write request:
the SCB stores any requested value that differs from what it holds. The protocol
is in docs/unico-scb-protocol.md and the test procedure in
docs/unico-scb-live-test.md.

    listen   decode what the SCB sends; never transmits (the default and the safe one)
    decode   decode a hex dump written by `listen --raw`
    mirror   build the answer that requests exactly what the SCB reports as stored,
             and with --transmit send it (the protocol's "no change" frame)
    set      mirror with one airflow or RPM limit changed; needs --transmit to send

On a Mac the FTDI board appears as /dev/cu.usbserial-*; on Linux as /dev/ttyUSB0.
Run from the repo without installing anything:

    uv run --no-project --with pyserial python scripts/unico-scb.py listen

Writes go to the SCB's memory immediately. `set` refuses values outside the
program's limits, and nothing here sends the thermostat override, the test flow or
the test pressure bytes.
"""
import argparse
import csv
import glob
import sys
import time

BAUD = 4800
MODES = ("G", "Y1", "Y2", "W1", "W2", "E")
STATUS, LOG = 0x83, 0x84
PC_TAG = 0x1C            # byte 3 of every PC frame
CFM_MAX = {"1218": 500, "2430": 750, "3036": 1200, "3642": 1200, "4860": 1500}
RPM_MIN = {"3036": 600}  # 400 for every other model
RPM_MAX = 1800


# --- framing -------------------------------------------------------------------

def fletcher_ok(frame):
    """True when the running sums over the whole frame, check bytes included, are zero."""
    s1 = s2 = 0
    for b in frame:
        s1 = (s1 + b) % 255
        s2 = (s2 + s1) % 255
    return s1 == 0 and s2 == 0 and frame[-1] != 0 and frame[-2] != 0


def with_check(body):
    """Append the two Fletcher check bytes the SCB expects."""
    s1 = s2 = 0
    for b in body:
        s1 = (s1 + b) % 255
        s2 = (s2 + s1) % 255
    c0 = 255 - ((s1 + s2) % 255)
    c1 = 255 - ((s1 + c0) % 255)
    return bytes(body) + bytes((c0, c1))


def split_frames(buf):
    """Yield (kind, frame) from a byte buffer and return the unconsumed tail.

    kind is "status", "log", "pc" (our own or ECMConfig's answer) or "bus" (bytes
    between frames: SCB-to-motor traffic, kept as raw hex)."""
    out, i, junk = [], 0, bytearray()
    while i < len(buf) - 1:
        if buf[i] == 0x01 and buf[i + 1] in (STATUS, LOG):
            if buf[i + 1] == LOG:
                lengths = (102,)
            elif i + 3 < len(buf) and buf[i + 3] not in (20, 23, PC_TAG):
                lengths = (9,)
            elif i + 3 < len(buf) and buf[i + 3] == PC_TAG:
                lengths = (43, 31)
            else:
                lengths = (36, 37, 51)
            if i + max(lengths) > len(buf) and not any(
                    i + n <= len(buf) and fletcher_ok(buf[i:i + n]) for n in lengths):
                break                                   # wait for more bytes
            for n in lengths:
                if i + n <= len(buf) and fletcher_ok(buf[i:i + n]):
                    if junk:
                        out.append(("bus", bytes(junk)))
                        junk = bytearray()
                    kind = "log" if buf[i + 1] == LOG else ("pc" if buf[i + 3] == PC_TAG else "status")
                    out.append((kind, bytes(buf[i:i + n])))
                    i += n
                    break
            else:
                junk.append(buf[i])
                i += 1
        else:
            junk.append(buf[i])
            i += 1
    if junk:
        out.append(("bus", bytes(junk)))
    return out, bytes(buf[i:])


# --- decoding ------------------------------------------------------------------

def u16(f, i):
    return (f[i] << 8) | f[i + 1]


def model_name(model_byte, switches, power_level):
    chassis = ("1218", "2430", "3642", "4860")[model_byte & 3]
    if power_level == 12 and switches is not None and switches & 0x0400:
        return "3036"
    return chassis


def decode_status(f):
    """Decode an SCB status frame (9, 36, 37 or 51 bytes) into a dict."""
    d = {"len": len(f), "flags": f[2], "level": f[3]}
    calls = f[4] >> 2                       # active-low G Y1 Y2 W1 W2 E, bit 5..0
    d["calls"] = [m for k, m in enumerate(MODES) if not (calls >> (5 - k)) & 1]
    if len(f) == 9:
        d["firmware"] = f[3]
        d["switches"] = u16(f, 5)
        d["model"] = model_name(f[4], d["switches"], 0)
        return d
    b = 1 if len(f) == 37 else 0
    d["power_level"] = u16(f, 5) if b else f[5]
    p = 6 + b
    d["cfm"] = dict(zip(MODES, (u16(f, p + 2 * k) for k in range(6))))
    d["rpm_limit"] = dict(zip(MODES, (u16(f, p + 12 + 2 * k) for k in range(6))))
    d["actual_cfm"] = u16(f, p + 24)
    d["actual_rpm"] = u16(f, p + 26)
    if len(f) == 51:
        d["fresh_pct"] = f[34]
        d["needed_cfm_raw"] = u16(f, 35)
        d["dc_bus_v"] = f[37] * 4
        d["switches"] = u16(f, 38)
        d["sqft"] = u16(f, 40)
        d["occupants"] = f[42] & 0x7F
        d["eac_relay"] = "open" if f[42] & 0x80 else "closed"
        d["run_min"] = f[43]
        d["interval_h"] = f[44]
        d["byte45"] = f[45]
        d["firmware"] = f[46]
        d["motor_status"] = u16(f, 47)
    d["model"] = model_name(f[4], d.get("switches"), d["power_level"])
    return d


SWITCH_BITS = ((15, "low-static"), (14, "damper-power-open"), (13, "energysaver"),
               (12, "cap-latched"), (11, "high-static"), (10, "aux-latched"),
               (9, "defrost"), (8, "chiller-leader"), (7, "cap-hi"), (6, "aux-on"),
               (5, "boiler-emergency"), (4, "air-cycle"), (3, "potable"),
               (2, "hum-hi"), (1, "revvalve-O"), (0, "mod-live"))


def motor_text(s):
    if s & 0x04:
        t = "Running" + (" +BlockedInlet" if s & 0x0800 else "")
    else:
        t = "Starting" if s & 0x01 else "Stopped"
        t += "".join(n for m, n in ((0x20, " +LostRotor"), (0x100, " +UnderVolt"),
                                    (0x400, " +IncompleteParams")) if s & m)
    return t


def describe(d):
    line = "%s len=%d flags=0x%02X calls=%s" % (d["model"], d["len"], d["flags"], ",".join(d["calls"]) or "-")
    if "actual_cfm" in d:
        line += " actual=%d CFM %d RPM" % (d["actual_cfm"], d["actual_rpm"])
    if "motor_status" in d:
        line += " motor=%s bus=%dV fw=3.%d" % (motor_text(d["motor_status"]), d["dc_bus_v"], d["firmware"])
    if "cfm" in d:
        line += "\n    stored CFM " + " ".join("%s=%d" % kv for kv in d["cfm"].items())
        line += "\n    RPM limit  " + " ".join("%s=%d" % kv for kv in d["rpm_limit"].items())
    if d.get("switches") is not None:
        line += "\n    switches 0x%04X %s" % (d["switches"], " ".join(
            n for bit, n in SWITCH_BITS if d["switches"] >> bit & 1))
    return line


# --- the answer frame ----------------------------------------------------------

def mirror_frame(f, cfm=None, rpm=None):
    """The 43-byte answer that requests what the 51-byte status frame `f` reports as
    stored, optionally with replacement airflow or RPM limits. This is the frame
    ECMConfig sends on every tick after its first, when requested = stored."""
    if len(f) != 51 or f[3] != 23:
        raise ValueError("mirror needs a 51-byte status frame with byte 3 = 23")
    d = decode_status(f)
    cfm = dict(d["cfm"], **(cfm or {}))
    rpm = dict(d["rpm_limit"], **(rpm or {}))
    sw = d["switches"]
    b2 = (f[2] & 1) | (2 if sw & 0x2000 else 0) | (4 if sw & 0x4000 else 0)
    if f[2] & 0x80:                                   # byte 45's EAC/Auto bits are valid
        auto, eac = bool(f[45] & 0x80), bool(f[45] & 0x40)
        b38 = (f[45] & 0x3F) | (0x40 if eac else 0) | (0x80 if auto else 0)
        b4 = (2 if auto else 0) | (1 if eac else 0)
    else:
        raise ValueError("SCB byte 2 bit 7 is clear: Air Cycle mode unknown, refusing to guess byte 38")
    body = [0x01, STATUS, b2, PC_TAG, b4]
    for m in MODES:
        body += [cfm[m] >> 8, cfm[m] & 0xFF]
    for m in MODES:
        body += [rpm[m] >> 8, rpm[m] & 0xFF]
    body += [f[34], f[35], f[36], 0x00, f[40], f[41], f[42] & 0x7F, f[43], f[44], b38, 0x00, 0x00]
    assert len(body) == 41
    return with_check(body)


# --- serial --------------------------------------------------------------------

def open_port(name):
    import serial
    if not name:
        found = sorted(glob.glob("/dev/cu.usbserial-*") + glob.glob("/dev/ttyUSB*"))
        if not found:
            sys.exit("no FTDI port found; plug the USB cable into the control box")
        name = found[0]
    port = serial.Serial(name, BAUD, bytesize=8, parity="N", stopbits=1, timeout=0.1,
                         xonxoff=False, rtscts=False, dsrdtr=False)
    port.dtr = True                                   # ECMConfig holds both asserted
    port.rts = True
    print("opened %s at %d 8N1" % (name, BAUD), file=sys.stderr)
    return port


def frames_from(port, seconds):
    buf, end = b"", time.time() + seconds
    while time.time() < end:
        buf += port.read(512)
        found, buf = split_frames(buf)
        for item in found:
            yield item


def cmd_listen(a):
    port = open_port(a.port)
    raw = open(a.raw, "a") if a.raw else None
    log = csv.writer(open(a.csv, "a", newline="")) if a.csv else None
    last = None
    for kind, f in frames_from(port, a.seconds):
        stamp = time.strftime("%H:%M:%S")
        if raw:
            raw.write("%s %s %s\n" % (time.time(), kind, f.hex()))
            raw.flush()
        if kind == "status":
            d = decode_status(f)
            text = describe(d)
            if text != last or a.verbose:
                print(stamp, text)
                last = text
            if log and "actual_cfm" in d:
                log.writerow([time.time(), d["model"], d["actual_cfm"], d["actual_rpm"],
                              ",".join(d["calls"]), d.get("dc_bus_v"), d.get("motor_status"), d["flags"]])
        elif kind == "log":
            print(stamp, "four-hour log: now=%d slots=%s" % (u16(f, 2), [u16(f, 4 + 2 * k) for k in range(48)]))
        elif kind == "pc":
            print(stamp, "PC frame seen (ECMConfig running, or our echo):", f.hex())
        elif a.verbose:
            print(stamp, "bus", f.hex())


def cmd_decode(a):
    for line in open(a.file):
        parts = line.split()
        if len(parts) == 3 and parts[1] == "status":
            print(describe(decode_status(bytes.fromhex(parts[2]))))


def parse_changes(items):
    cfm, rpm = {}, {}
    for item in items or ():
        key, value = item.split("=")
        kind, mode = key.split(".")
        (cfm if kind == "cfm" else rpm)[mode.upper()] = int(value)
    return cfm, rpm


def answer_once(a, cfm, rpm):
    port = open_port(a.port)
    for kind, f in frames_from(port, 15):
        if kind != "status" or len(f) != 51:
            continue
        d = decode_status(f)
        cap = CFM_MAX[d["model"]]
        floor = RPM_MIN.get(d["model"], 400)
        for m, v in cfm.items():
            if m not in MODES or not 0 < v <= cap:
                sys.exit("%s airflow %d outside 1..%d CFM for a %s" % (m, v, cap, d["model"]))
        for m, v in rpm.items():
            if m not in MODES or not floor <= v <= RPM_MAX:
                sys.exit("%s RPM limit %d outside %d..%d" % (m, v, floor, RPM_MAX))
        print("SCB now:", describe(d))
        out = mirror_frame(f, cfm, rpm)
        print("answer (%d bytes): %s" % (len(out), out.hex()))
        if not a.transmit:
            print("dry run: add --transmit to send it")
            return
        port.reset_input_buffer()
        port.write(out)
        echo = port.read(len(out))
        print("echo:", "matched, dropped" if echo == out else (echo.hex() or "none"))
        print("watching for the stored values to update...")
        for kind, g in frames_from(port, a.watch):
            if kind == "status":
                print(time.strftime("%H:%M:%S"), describe(decode_status(g)))
        return
    sys.exit("no 51-byte status frame in 15 s; run `listen` first")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", help="serial device; default: the first FTDI port")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("listen")
    p.add_argument("--seconds", type=float, default=float("inf"))
    p.add_argument("--raw", help="append every frame as hex to this file")
    p.add_argument("--csv", help="append actual CFM/RPM rows to this file")
    p.add_argument("-v", "--verbose", action="store_true", help="print every frame and the motor-bus bytes")
    p = sub.add_parser("decode")
    p.add_argument("file")
    for name in ("mirror", "set"):
        p = sub.add_parser(name)
        p.add_argument("--transmit", action="store_true", help="send the frame; without it, print only")
        p.add_argument("--watch", type=float, default=20, help="seconds to watch after sending")
        if name == "set":
            p.add_argument("changes", nargs="+", metavar="cfm.Y2=800 | rpm.G=1200")
    a = ap.parse_args()
    if a.cmd == "listen":
        cmd_listen(a)
    elif a.cmd == "decode":
        cmd_decode(a)
    else:
        answer_once(a, *parse_changes(getattr(a, "changes", None)))


if __name__ == "__main__":
    main()
