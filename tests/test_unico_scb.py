"""Checks for scripts/unico-scb.py: framing, decoding and the mirror answer.

The two PC frames are the ones verified in docs/unico-scb-protocol.md §3.1. The
status frame is synthetic, laid out per §4.1. Run: python tests/test_unico_scb.py
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("unico_scb", os.path.join(HERE, "..", "scripts", "unico-scb.py"))
scb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scb)

IDLE = bytes.fromhex("0183fe1c01" + "00" * 36 + "7fdf")
EXAMPLE = bytes.fromhex(
    "0183001c02012c01c2025801f40258025807080708070807080708070814025800"
    "07d0040a0883000084a8")


def status_frame():
    """A 3642 in Auto mode with EAC, calling Y2, motor running at 900 CFM."""
    body = [0x01, 0x83, 0x80, 23]
    calls = 0b111111 & ~(1 << 3)                      # Y2 active (active-low)
    body.append((calls << 2) | 2)                     # chassis 2 = 3642
    body.append(12)                                   # full-size motor
    for cfm in (437, 656, 875, 656, 875, 875):
        body += [cfm >> 8, cfm & 0xFF]
    for rpm in (1800,) * 6:
        body += [rpm >> 8, rpm & 0xFF]
    body += [900 >> 8, 900 & 0xFF, 1100 >> 8, 1100 & 0xFF]   # actual CFM, RPM
    body += [20, 0x01, 0x2C]                          # fresh 20 %, needed 300
    body += [85]                                      # DC bus 340 V
    body += [0x00, 0x10]                              # Air Cycle switch on
    body += [0x13, 0x88, 4, 10, 8]                    # 5000 sqft, 4 occ, 10 min / 8 h
    body += [0x80 | 0x40 | 3]                         # Auto, EAC, 3 bedrooms
    body += [19, 0x00, 0x04]                          # fw 3.19, running
    return scb.with_check(body)


def check(label, ok):
    print("[%s] %s" % ("PASS" if ok else "FAIL", label))
    return ok


def main():
    results = [
        check("idle PC frame validates", scb.fletcher_ok(IDLE)),
        check("example PC frame validates", scb.fletcher_ok(EXAMPLE)),
        check("with_check rebuilds the idle frame", scb.with_check(IDLE[:-2]) == IDLE),
        check("with_check rebuilds the example frame", scb.with_check(EXAMPLE[:-2]) == EXAMPLE),
    ]
    f = status_frame()
    noise = bytes.fromhex("0a0300030466")
    frames, tail = scb.split_frames(noise + f + IDLE + f[:20])
    kinds = [k for k, _ in frames]
    results.append(check("split: bus, status, pc, and a partial tail", kinds == ["bus", "status", "pc"] and tail == f[:20]))
    d = scb.decode_status(f)
    results += [
        check("model 3642", d["model"] == "3642"),
        check("calls Y2", d["calls"] == ["Y2"]),
        check("stored and actual airflow", d["cfm"]["Y2"] == 875 and d["actual_cfm"] == 900 and d["actual_rpm"] == 1100),
        check("DC bus and motor running", d["dc_bus_v"] == 340 and scb.motor_text(d["motor_status"]) == "Running"),
    ]
    m = scb.mirror_frame(f)
    results += [
        check("mirror is 43 bytes and validates", len(m) == 43 and scb.fletcher_ok(m)),
        check("mirror requests the stored airflows", [scb.u16(m, 5 + 2 * k) for k in range(6)] == list(d["cfm"].values())),
        check("mirror keeps Auto, EAC and bedrooms", m[38] == 0xC3 and m[4] == 0x03),
        check("mirror sends no override or test bytes", m[4] & 0xFC == 0 and m[39] == 0 and m[40] == 0),
    ]
    s = scb.mirror_frame(f, cfm={"Y2": 850})
    results.append(check("set changes only Y2", scb.u16(s, 9) == 850 and s[5:9] == m[5:9] and s[11:41] == m[11:41]))
    if not all(results):
        sys.exit(1)
    print("all %d checks passed" % len(results))


if __name__ == "__main__":
    main()
