"""The Unico S.M.A.R.T. Control Board (SCB) serial protocol: framing, decoding and the
PC's answer frames. `docs/unico-scb-protocol.md` is the specification, with every claim
cited to the decompiled ECMConfig 4.6 and the facts measured on 2026-10-24.
`scripts/unico-scb.py` is the command-line tool and `pivac.UnicoSCB` the provider
module; both import from here. Nothing here touches hardware or pivac's config."""
import json

BAUD = 4800
MODES = ("G", "Y1", "Y2", "W1", "W2", "E")
STATUS, LOG = 0x83, 0x84
PC_TAG = 0x1C            # byte 3 of every PC frame
CFM_MAX = {"1218": 500, "2430": 750, "3036": 1200, "3642": 1200, "4860": 1500}
RPM_MIN = {"3036": 600}  # 400 for every other model
RPM_MAX = 1800
OVERRIDE_BIT = {"G": 0x80, "Y1": 0x40, "Y2": 0x20, "W1": 0x10, "W2": 0x08, "E": 0x04}
OVERRIDE_MAX_S = 300
MENU_BIT = {"freshair": 0x01, "motor": 0x02}    # PC byte 32, protocol §5.3
AIR_LIMITS = {"percent": 255, "blower": None, "sqft": 30000, "occupants": 51,
              "runmin": 60, "interval": 24, "bedrooms": 50}


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

def stored_settings(f):
    """Every writable setting the 51-byte status frame `f` reports as stored, in the
    vocabulary `set` uses (protocol §4.1, §5.1)."""
    if len(f) != 51 or f[3] != 23:
        raise ValueError("needs a 51-byte status frame with byte 3 = 23")
    if not f[2] & 0x80:
        raise ValueError("SCB byte 2 bit 7 is clear: Air Cycle mode unknown, refusing to guess byte 38")
    d = decode_status(f)
    sw = d["switches"]
    return {
        "model": d["model"], "firmware": "3.%d" % d["firmware"], "switches": "0x%04X" % sw,
        "cfm": dict(d["cfm"]), "rpm": dict(d["rpm_limit"]),
        "air": {"percent": f[34], "blower": u16(f, 35), "sqft": u16(f, 40),
                "occupants": f[42] & 0x7F, "runmin": f[43], "interval": f[44],
                "bedrooms": f[45] & 0x3F, "eac": bool(f[45] & 0x40),
                "mode": "auto" if f[45] & 0x80 else "fixed"},
        "auto": {"style": "energysaver" if sw & 0x2000 else "maxcomfort"},
        "damper": "poweropen" if sw & 0x4000 else "powerclose",
    }


def answer_frame(f, want, menus=0, test=None):
    """The 43-byte answer that requests the settings in `want` (the shape of
    stored_settings) from the SCB whose status frame is `f`. With want equal to the
    stored settings this is ECMConfig's no-change frame; `menus` is byte 32 and `test`
    the two test bytes."""
    if len(f) != 51 or f[3] != 23:
        raise ValueError("needs a 51-byte status frame with byte 3 = 23")
    air, cfm, rpm = want["air"], want["cfm"], want["rpm"]
    auto, eac = air["mode"] == "auto", bool(air["eac"])
    b2 = (f[2] & 1) | (2 if want["auto"]["style"] == "energysaver" else 0) \
        | (4 if want["damper"] == "poweropen" else 0)
    b4 = (2 if auto else 0) | (1 if eac else 0)
    b38 = (air["bedrooms"] & 0x3F) | (0x40 if eac else 0) | (0x80 if auto else 0)
    body = [0x01, STATUS, b2, PC_TAG, b4]
    for m in MODES:
        body += [cfm[m] >> 8, cfm[m] & 0xFF]
    for m in MODES:
        body += [rpm[m] >> 8, rpm[m] & 0xFF]
    flow, pressure = test or (0, 0)
    body += [air["percent"], air["blower"] >> 8, air["blower"] & 0xFF, menus & 0xFF,
             air["sqft"] >> 8, air["sqft"] & 0xFF, air["occupants"], air["runmin"],
             air["interval"], b38, flow, pressure]
    assert len(body) == 41
    return with_check(body)


def merge(stored, changes):
    """`stored` with the `set` changes applied: {"cfm": {...}, "rpm": {...}, "air": {...},
    "auto": {...}, "damper": str}."""
    want = json.loads(json.dumps(stored))
    for group, vals in changes.items():
        if group in ("cfm", "rpm", "air", "auto"):
            want[group].update(vals)
        elif group == "damper":
            want["damper"] = vals
    return want


def mirror_frame(f, cfm=None, rpm=None):
    """ECMConfig's no-change frame: requests exactly what `f` reports as stored,
    optionally with replacement airflows or RPM limits."""
    return answer_frame(f, merge(stored_settings(f), {"cfm": cfm or {}, "rpm": rpm or {}}))


def override_frame(f, mode):
    """The mirror answer with one Thermostat Override bit set in byte 4 (protocol §5.3):
    the SCB then runs as if the thermostat called `mode`. Live only; the SCB keeps it
    for as long as the answers keep coming, so the caller must send plain mirror
    frames to release it."""
    body = bytearray(mirror_frame(f)[:-2])
    body[4] |= OVERRIDE_BIT[mode]
    return with_check(body)


def idle_frame(f):
    """The 43-byte answer that requests nothing: what ECMConfig sends on its first tick
    after connecting, before it has copied stored to requested (protocol §5.4). Byte 2
    carries the SCB's own bit 0, the two "no request" sentinels and 0xF8 (no Air Cycle
    mode selected); byte 4 is 0x01 (the EAC box indeterminate); bytes 5-40 are zero.
    Verified example in protocol §3.1: 01 83 fe 1c 01 00x36 7f df."""
    body = [0x01, STATUS, (f[2] & 1) | 0xFE, PC_TAG, 0x01] + [0] * 36
    assert len(body) == 41
    return with_check(body)
