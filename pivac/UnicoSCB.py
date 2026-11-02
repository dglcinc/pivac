"""pivac.UnicoSCB — a Unico air handler's S.M.A.R.T. Control Board (SCB), read from
its serial line and published as Signal K deltas.

The SCB is the bus master: it sends a 36-byte status frame every 0.85 s whether or
not anything answers (docs/unico-scb-protocol.md), carrying the six thermostat
inputs, the actual airflow and RPM, the stored airflow per mode and its flags. One
config section serves one air handler and names the transport:

    port: /dev/serial/by-id/*unicousb*    the control box's USB board on the Pi (a glob is fine)
    node: http://10.0.0.180/              the air-handler node's HTTP line (the rev B shield)

Either way the paths are the same, so a unit moves from the Pi's USB to its own node
by changing that one line. `answer: true` makes the serial reader answer every frame
with the protocol's no-change frame, which brings the 51-byte frame and its extra
fields (motor state, DC bus, switch word, firmware); by default it transmits nothing.

Paths under `sk_path` (default environment.inside.hvac.ah.utility):

    call.g call.y1 call.y2 call.w1 call.w2 call.e   0/1, the inputs as the SCB sees them
    fan.airflow  fan.rpm                            actual, CFM and RPM
    fan.stored.g .. fan.stored.e                    the stored airflow per mode, CFM
    scb.flags                                       status byte (bit 5 = nobody answering)
    scb.age                                         seconds since the last valid frame
    fan.state scb.dcBus scb.switches scb.firmware   only from the 51-byte frame

A gap (nothing published) means no frame within `stale_s` (10 s), the port missing
or the node unreachable; no sentinel is ever sent.
"""
import glob
import logging
import time

from pivac import unico_scb_protocol as proto

logger = logging.getLogger(__name__)

_ser = None
_ser_name = None
_buf = b""
_last = None            # last decoded status frame
_last_t = 0.0
_warned_t = 0.0

NODE_FIELDS = (("g", "call.g"), ("y1", "call.y1"), ("y2", "call.y2"), ("w1", "call.w1"),
               ("w2", "call.w2"), ("e", "call.e"), ("cfm", "fan.airflow"), ("rpm", "fan.rpm"),
               ("cfm_g", "fan.stored.g"), ("cfm_y1", "fan.stored.y1"), ("cfm_y2", "fan.stored.y2"),
               ("cfm_w1", "fan.stored.w1"), ("cfm_w2", "fan.stored.w2"), ("cfm_e", "fan.stored.e"),
               ("flags", "scb.flags"), ("scb_age", "scb.age"))


def values_from_frame(d, age):
    """The published values for a decoded status frame `d` (proto.decode_status) that
    arrived `age` seconds ago, keyed by the path under sk_path."""
    out = {}
    for m in proto.MODES:
        out["call.%s" % m.lower()] = 1 if m in d["calls"] else 0
    if "actual_cfm" in d:
        out["fan.airflow"] = d["actual_cfm"]
        out["fan.rpm"] = d["actual_rpm"]
        for m in proto.MODES:
            out["fan.stored.%s" % m.lower()] = d["cfm"][m]
    out["scb.flags"] = d["flags"]
    out["scb.age"] = round(age, 1)
    if d["len"] == 51:
        out["fan.state"] = proto.motor_text(d["motor_status"])
        out["scb.dcBus"] = d["dc_bus_v"]
        out["scb.switches"] = d["switches"]
        out["scb.firmware"] = "3.%d" % d["firmware"]
    return out


def values_from_node(j):
    """The same values from a rev B node's JSON line, whose field names are the
    shield plan's (docs/air-handler-shield-pcb-plan.md section 7)."""
    out = {}
    for field, path in NODE_FIELDS:
        if field in j:
            out[path] = j[field]
    return out


def _warn(msg):
    global _warned_t
    if time.time() - _warned_t > 60:
        logger.warning(msg)
        _warned_t = time.time()


def _open(pattern, baud):
    global _ser, _ser_name
    import serial
    found = sorted(glob.glob(pattern))
    if not found:
        _warn("no serial port matches %s; is the control box's USB cable in?" % pattern)
        return None
    _ser = serial.Serial(found[0], baud, timeout=0.05)
    _ser_name = found[0]
    logger.info("opened %s at %d 8N1" % (found[0], baud))
    return _ser


def _poll_serial(config):
    """Drain the port, keep the newest status frame, answer it if asked to."""
    global _ser, _buf, _last, _last_t
    if _ser is None and _open(config.get("port", "/dev/serial/by-id/*unicousb*"), int(config.get("baud", proto.BAUD))) is None:
        return
    try:
        _buf += _ser.read(max(4096, _ser.in_waiting))
    except Exception as e:
        _warn("serial read failed on %s (%s); reopening" % (_ser_name, e))
        try:
            _ser.close()
        except Exception:
            pass
        _ser, _buf = None, b""
        return
    frames, _buf = proto.split_frames(_buf)
    if len(_buf) > 1024:            # garbage with no frame in it; start over
        _buf = b""
    for kind, f in frames:
        if kind != "status":
            continue
        _last, _last_t = proto.decode_status(f), time.time()
        if config.get("answer"):
            try:
                _ser.write(proto.answer_frame(f, proto.stored_settings(f)) if len(f) == 51 else proto.idle_frame(f))
            except Exception as e:
                _warn("answer failed: %s" % e)


def _poll_node(config):
    import requests
    try:
        r = requests.get(config["node"], timeout=float(config.get("timeout", 2)))
        r.raise_for_status()
        return r.json()
    except Exception as e:
        _warn("node %s: %s" % (config["node"], e))
        return None


def status(config={}, output="default"):
    sk_path = config.get("sk_path", "environment.inside.hvac.ah.utility")
    stale_s = float(config.get("stale_s", 10))
    if config.get("node"):
        j = _poll_node(config)
        vals = values_from_node(j) if j else {}
    else:
        _poll_serial(config)
        age = time.time() - _last_t
        vals = values_from_frame(_last, age) if _last is not None and age <= stale_s else {}
        if _last is not None and age > stale_s:
            _warn("no SCB frame for %.0f s on %s" % (age, _ser_name))
    if output == "signalk":
        from pivac import sk_init_deltas, sk_add_source, sk_add_value
        deltas = sk_init_deltas()
        if vals:
            src = sk_add_source(deltas)
            for k, v in vals.items():
                sk_add_value(src, "%s.%s" % (sk_path, k), v)
        return deltas
    return vals


if __name__ == "__main__":
    logging.basicConfig(format='%(name)s %(levelname)s:%(asctime)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S', level="DEBUG")
    import json
    import sys
    cfg = {"port": sys.argv[1]} if len(sys.argv) > 1 else {}
    time.sleep(1.5)
    status(cfg)
    time.sleep(1.5)
    print(json.dumps(status(cfg), indent=2))
