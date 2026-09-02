"""Chiltrix CX75 heat pump over RS-485 Modbus RTU.

The chiller is a Modbus *slave* on terminals A3/B3 (9600 8N1, slave 1,
function 03).  An Arduino UNO R4 with an RS-485 shield sits between it and the
Pi on USB, running the `ChiltrixScan` sketch from ~/github/Arduino.  This
module drives that sketch's `s <from> <to>` range-read command and republishes
every register the unit answers.

READ ONLY.  The sketch only ever issues function 03.  Registers 140-146 are
writable on the chiller and include the on/off switch and the cooling target;
nothing here writes them.

Why one module and one service: a serial port is exclusive.  Two config
sections sharing `module:` works over HTTP because each does its own GET, but
they would fight over /dev/ttyACM0.

Two properties are mandatory for any serial client to this sketch, both learned
the hard way (see CLAUDE.md):

  * Opening the port does NOT reset an UNO R4, so a previous client can leave
    the sketch inside a `watch`.  A running watch consumes exactly one
    character to stop, which eats the first byte of whatever you send next.
    `_quiesce` nudges the board to its prompt before any real command.
  * Every read is bounded.  `chiltrix-logger` once ran `active` for 18 hours
    having written zero rows because its read loop had no timeout.

Registers carrying a confirmed meaning get a named path.  Everything else is
published under `.raw.r<addr>` rather than dropped: several addresses are
suspected to be an operating state, a fault code or a pump speed, and the
moment that identifies them is a live alarm which cannot be recaptured after
the fact.

Raw addresses keep the bare address in the path deliberately.  The
address = parameter-number mapping for the settings block is supported by four
value matches but is not proven, so nothing in the data model asserts it; the
interpretation lives in CLAUDE.md where it can be corrected without orphaning a
measurement.
"""

import logging
import time

logger = logging.getLogger(__name__)

# ---- register map -----------------------------------------------------------
# Confirmed against the unit and against Chiltrix's own Modbus document.  The
# document agrees with gonzojive (CX34) on every address they share and
# contradicts jasipsw (CX50-2) on every one, so no jasipsw address is treated
# as known here — those live in RAW_RANGES and publish under .raw.
#
# kind: "tempK"  raw/10 degC published as Kelvin
#       "wholeK" whole degC published as Kelvin (the setpoints)
#       "div10"  raw/10 in the register's own unit
#       "int"    the bare integer
NAMED = {
    140: ("switchOn",        "int"),
    141: ("operatingMode",   "int"),     # 0 cool 1 heat 2 DHW 3 cool+DHW 4 heat+DHW
    142: ("coolingTarget",   "wholeK"),  # whole degC — the rounding behind the E14 lockout
    143: ("heatingTarget",   "wholeK"),
    144: ("dhwTarget",       "wholeK"),
    145: ("heatingAuMode",   "int"),
    146: ("dhwAuMode",       "int"),
    202: ("ambientTemp",     "tempK"),
    205: ("outletTemp",      "tempK"),   # supply to the house, the cold side in cooling
    213: ("waterFlow",       "div10"),   # L/min — scale measured, not documented
    227: ("compressorHz",    "int"),
    256: ("inputCurrent",    "div10"),   # A — scale measured against Emporia
    281: ("inletTemp",       "tempK"),   # return from the house, the warm side in cooling
}

# ⚠️ ANSWERING PROVES NOTHING ON THIS UNIT.  Every address from 0 to 359 answers
# function 03 with no gaps (scanned 2026-08-29), and it does not stop there —
# that is only where the scan stopped.  So a response is not evidence that an
# address is meaningful, and the count of answering registers is not a discovery
# about the chiller.  Meaning comes only from Chiltrix's document plus value
# cross-checks against things already known.
#
# 0-139 is the settings block, polled because a parameter changed on the panel is
# exactly what later explains a change in behaviour and nothing else in this
# system records one.  Four have confirmed identities at address = parameter
# number: 53=P53 pump min speed 40%, 59=P59 antifreeze 3 degC, 64=P64 flow-meter
# select, 109=P109 target range.  65 reads 14 against a documented P65 of 20,
# which most likely means that setting was changed on this unit.
#
# The upper space is deliberately NOT swept.  Only the addresses below carry a
# documented meaning or a community-map candidate worth catching during a live
# fault; publishing the rest would be hundreds of InfluxDB series of noise.
RAW_RANGES = [(0, 139),
              (140, 146), (202, 214), (225, 227), (243, 248),
              (256, 261), (264, 264), (281, 285)]

DEFAULT_PORT = "/dev/ttyACM0"
SK_ROOT = "hvac.chiller.chiltrix"

# ---- persistent state (this module owns one serial port, so one daemon) -----
_ser = None
_state = {
    "run_started": None,     # wall clock of the current compressor run
    "run_duration": 0.0,     # seconds; holds the last run's length while stopped
    "startup_flow": None,    # max flow seen across the current start window
    "startup_flow_last": None,
    "prev_hz": None,
    "stopped_at": None,      # wall clock of the last compressor stop edge
}

# Idle-side flow samples this soon after a stop edge are the pump spinning
# down and are excluded from the plateau.  See _derive.
STOP_SETTLE_S = 180


def _open(port, baud):
    import serial                       # imported late so the rest is testable
    global _ser
    if _ser is not None:
        try:
            _ser.close()
        except Exception:
            pass
    _ser = serial.Serial(port, baud, timeout=0.2)
    time.sleep(2.5)                      # the sketch prints its menu on connect
    if not _quiesce(_ser):
        raise RuntimeError("board would not return to its prompt")
    return _ser


def _quiesce(s, tries=6):
    """Leave the sketch silent at its command prompt.

    A watch left running by a previous client would otherwise swallow the first
    character of our command and discard the rest.
    """
    for _ in range(tries):
        s.write(b"\n")
        s.flush()
        t0 = last = time.time()
        got = b""
        while time.time() - t0 < 4.0:
            n = s.in_waiting
            if n:
                got += s.read(n)
                last = time.time()
            elif time.time() - last > 1.2:
                break
            time.sleep(0.05)
        s.reset_input_buffer()
        if time.time() - last > 1.2 and not got.strip().split(b"\n")[-1][:1].isdigit():
            return True
    return False


def _read_range(s, lo, hi, quiet=0.4, deadline=15.0):
    """Issue `s <lo> <hi>` and return {addr: int16}.

    The sketch prints one tab-separated row per address that answers:
        addr \t raw \t 0xHEX \t int16 \t <temp> \t ...
    Field 3 is the signed value, which is the one that matters for a negative
    temperature.  Non-data lines (the banner, the header, the "N of M" trailer)
    have no tab-delimited integer in field 3 and are skipped.
    """
    s.reset_input_buffer()
    s.write(("s %d %d" % (lo, hi)).encode() + b"\n")
    s.flush()
    t0 = last = time.time()
    buf = ""
    while time.time() - t0 < deadline:
        n = s.in_waiting
        if n:
            buf += s.read(n).decode("utf-8", "replace")
            last = time.time()
        elif time.time() - last > quiet:
            break
        time.sleep(0.02)
    else:
        raise RuntimeError("no reply to 's %d %d' within %.0fs" % (lo, hi, deadline))
    out = {}
    for line in buf.splitlines():
        p = line.rstrip("\r").split("\t")
        if len(p) >= 4 and p[0].strip().isdigit():
            try:
                out[int(p[0])] = int(p[3])
            except ValueError:
                continue
    return out


def _convert(kind, raw):
    if kind == "tempK":
        return round(raw / 10.0 + 273.15, 2)
    if kind == "wholeK":
        return round(float(raw) + 273.15, 2)
    if kind == "div10":
        return round(raw / 10.0, 1)
    return int(raw)


def _derive(regs, result, stop_settle_s=STOP_SETTLE_S):
    """Compressor run duration, and the flow plateau around a start.

    Flow is NOT a fixed reference at an arbitrary moment: the pump nearly stops
    in deep idle (2-5 L/min, enough to keep water moving past the sensor) and
    the controller trims it while running.  Measured across eight clean starts,
    though, it holds a flat plateau from roughly 70 s before the compressor
    engages until about 140 s into the run, spanning the whole power ramp.
    That plateau is the comparable number, so it is captured as the maximum
    flow seen from the last stop through the first 150 s of the run, and held
    until the next start replaces it.

    The idle side of the window opens `stop_settle_s` after the stop edge.
    The pump spins down over the next sample or two, and a sample that lands
    mid-ramp reads a plausible 30-40 L/min with the compressor already at 0 Hz.
    Without the guard that sample became the plateau, the idle trickle could
    not displace it, and it stood until the next start: 36 minutes on
    2026-09-02, longer than the alert's 30-minute window, so
    chiltrix-pump-only-flow-low fired on a strainer that read the same
    52.9 L/min before and after cleaning.  The pump-only window before a start
    is unaffected, since the compressor's minimum-off timer keeps restarts
    well past the settle period, and the run side of the window captures the
    plateau regardless.

    Note this does not establish that the plateau is a FIXED commanded speed —
    an adaptive re-trim by the controller would move it too.  See the header of
    grafana/provisioning/alerting/chiltrix.yaml.
    """
    hz = regs.get(227)
    flow = regs.get(213)
    if hz is None:
        return
    now = time.time()
    prev = _state["prev_hz"]

    if prev is None:
        # First cycle of this daemon. The prior compressor state is unknown, so
        # a run already in progress must NOT be treated as starting now — that
        # would under-report runDuration (silently disarming an alert that fires
        # on a LONG run) and record a mid-run flow as the startup plateau.
        # Publish neither until a genuine 0 -> >0 edge is seen.
        _state["prev_hz"] = hz
        return
    if hz > 0 and prev == 0:
        _state["run_started"] = now
    elif hz == 0 and prev is not None and prev > 0:
        if _state["run_started"] is not None:
            _state["run_duration"] = now - _state["run_started"]
        _state["run_started"] = None
        _state["stopped_at"] = now
        if _state["startup_flow"] is not None:
            _state["startup_flow_last"] = _state["startup_flow"]
        _state["startup_flow"] = None

    if flow is not None:
        lpm = flow / 10.0
        settling = (_state["stopped_at"] is not None
                    and now - _state["stopped_at"] < stop_settle_s)
        in_window = ((hz == 0 and not settling)
                     or (_state["run_started"] is not None
                         and now - _state["run_started"] <= 150))
        if in_window and lpm > 15.0:     # excludes the deep-idle sensing trickle
            if _state["startup_flow"] is None or lpm > _state["startup_flow"]:
                _state["startup_flow"] = lpm

    _state["prev_hz"] = hz

    if _state["run_started"] is not None:
        result["runDuration"] = round(now - _state["run_started"], 1)
    elif _state["run_duration"]:
        result["runDuration"] = round(_state["run_duration"], 1)

    plateau = _state["startup_flow"] or _state["startup_flow_last"]
    if plateau is not None:
        result["startupFlow"] = round(plateau, 1)


def status(config={}, output="default"):
    port = config.get("port", DEFAULT_PORT)
    baud = int(config.get("baud", 115200))
    ranges = config.get("ranges") or RAW_RANGES

    global _ser
    regs = {}
    try:
        if _ser is None or not _ser.is_open:
            logger.warning("ChiltrixModbus opening %s", port)
            _open(port, baud)
        for lo, hi in ranges:
            regs.update(_read_range(_ser, lo, hi))
    except Exception as e:
        logger.warning("ChiltrixModbus read failed (%s); reopening next cycle", e)
        try:
            _ser.close()
        except Exception:
            pass
        _ser = None
        if not regs:
            raise

    if not regs:
        raise RuntimeError("no registers answered")

    result = {}
    for addr, raw in sorted(regs.items()):
        if addr in NAMED:
            name, kind = NAMED[addr]
            result[name] = _convert(kind, raw)
        else:
            result["raw.r%d" % addr] = int(raw)

    if 281 in regs and 205 in regs:
        result["evaporatorDelta"] = round((regs[281] - regs[205]) / 10.0, 2)

    _derive(regs, result, float(config.get("stop_settle_s", STOP_SETTLE_S)))
    # How many of the addresses WE ASKED FOR answered.  Not a property of the
    # chiller — it answers everything — but a useful link-health signal, since a
    # degrading bus drops responses.
    result["registerCount"] = len(regs)

    if output != "signalk":
        return result

    from pivac import sk_init_deltas, sk_add_source, sk_add_value
    deltas = sk_init_deltas()
    src = sk_add_source(deltas)
    for key, value in result.items():
        sk_add_value(src, "%s.%s" % (SK_ROOT, key), value)
    return deltas
