"""Checks for pivac.UnicoSCB: the same paths from a frame and from a node line.
Run: python tests/test_unico_scb_module.py"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from pivac import unico_scb_protocol as proto     # noqa: E402
from pivac import UnicoSCB                         # noqa: E402

SHORT = bytes.fromhex("0183a117fd0600c8012c01f4012c01f401f407080708070807080708070800000000253a")
LONG = bytes.fromhex("01838017fd0600c8012c01f4012c01f401f407080708070807080708070800000000"
                     "0a017201010705dc030a0802150000b635")
CALL = bytes.fromhex("0183a1173d06" + "00c8012c01f4012c01f401f4" + "070807080708070807080708"
                     + "012c041c" + "00000000")                  # G,Y1 calling, 300 CFM 1052 RPM
CALL = proto.with_check(CALL[:-2])


def check(label, ok):
    print("[%s] %s" % ("PASS" if ok else "FAIL", label))
    return ok


def main():
    v = UnicoSCB.values_from_frame(proto.decode_status(SHORT), 0.4)
    results = [
        check("short frame: six calls at 0, stored airflows, flags, age",
              [v["call.%s" % m] for m in ("g", "y1", "y2", "w1", "w2", "e")] == [0] * 6
              and v["fan.stored.g"] == 200 and v["fan.stored.y2"] == 500 and v["scb.flags"] == 0xA1 and v["scb.age"] == 0.4),
        check("short frame: no 51-byte fields", "fan.state" not in v and "scb.firmware" not in v),
    ]
    c = UnicoSCB.values_from_frame(proto.decode_status(CALL), 0.0)
    results.append(check("call frame: G and Y1 at 1, actual 300 CFM 1052 RPM",
                         c["call.g"] == 1 and c["call.y1"] == 1 and c["call.y2"] == 0
                         and c["fan.airflow"] == 300 and c["fan.rpm"] == 1052))
    l = UnicoSCB.values_from_frame(proto.decode_status(LONG), 0.0)
    results.append(check("long frame: state, DC bus, switches, firmware",
                         l["fan.state"] == "Stopped" and l["scb.dcBus"] == 4 and l["scb.switches"] == 0x0107 and l["scb.firmware"] == "3.21"))
    node = {"g": 1, "y1": 1, "y2": 0, "w1": 0, "w2": 0, "e": 0, "cfm": 300, "rpm": 1052,
            "cfm_g": 200, "cfm_y1": 300, "cfm_y2": 500, "cfm_w1": 300, "cfm_w2": 500, "cfm_e": 500,
            "flags": 0xA1, "scb_age": 0.0, "wsup": 292.9}
    n = UnicoSCB.values_from_node(node)
    results.append(check("node line gives the same paths and values as the call frame",
                         {k: n[k] for k in c} == c and "wsup" not in n.values()))
    d = UnicoSCB.status({"node": "http://127.0.0.1:9/"}, "signalk")
    results.append(check("unreachable node publishes nothing", d["updates"] == []))
    if not all(results):
        sys.exit(1)
    print("all %d checks passed" % len(results))


if __name__ == "__main__":
    main()
