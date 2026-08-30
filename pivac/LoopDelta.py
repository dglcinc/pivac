"""pivac.LoopDelta — gated supply/return delta-T for the chilled-water loops.

A loop's delta-T only means something while that loop is pumping.  With the
pump off the probes sit in stagnant water in a short dead leg off the header,
and they do not converge: the supply leg hangs off the cold half of the header
and the return leg off the warm half, so the pair keeps a plausible positive
delta-T for as long as the loop is idle.  Measured on this system, loop A holds
+3.6 K while only loop B is running, against a genuine +5.0 K of its own — 72%
of the real value, with nothing in the trace to mark it false.  So the gate is
not polish; an ungated series is mostly fiction between calls.

The first minutes of a run are no better.  Cold water reaches the supply probe
before the return responds, so delta-T overshoots — +6.2 K against a settled
+4.0 K at one minute in — and only lands by minute three.  `settle_s` discards
that window.

What survives is one number per run.  After trimming the transient off a 7-13
minute call there is not enough continuous data to draw an honest line, so this
publishes the run's mean once, when the run ends, and says nothing in between.
`.flowing` is emitted every cycle instead, which is what carries liveness and
explains the gaps.

This is a derived module: it reads what other pivac modules have already
published to Signal K rather than touching hardware.  That keeps it off the
1-wire bus and the GPIO pins their owners have already claimed, and away from
the Honeywell session, which tolerates exactly one client.

Delta-T is published in KELVIN, matching `hvac.chiller.chiltrix.evaporatorDelta`
and every other temperature in this repo.  A difference in kelvin equals one in
degrees Celsius, so Fahrenheit is `* 9/5` with NO offset — a panel that applies
the absolute conversion `* 9/5 - 459.67` to these paths is wrong by 459.67.
"""
import json
import logging
import time
import urllib.request
from datetime import datetime

logger = logging.getLogger(__name__)

_DEFAULT_URL = "http://localhost:3000/signalk/v1/api/vessels/self"

# Per-loop run state, persisting across status() calls in the daemon.
_runs = {}


def _new_state():
    return {"running": False, "start": 0.0, "sum": 0.0, "n": 0}


def _fetch(url, timeout):
    """GET a Signal K subtree.  Returns None on any failure — a module that
    cannot read its inputs must publish nothing rather than guess."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        logger.warning("LoopDelta could not read %s (%s)", url, exc)
        return None


def _age(stamp, now):
    """Seconds since an ISO8601 Signal K timestamp, or None if unparseable."""
    if not stamp:
        return None
    try:
        return now - datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _value(tree, *path, **kw):
    """Pluck value from a Signal K subtree, rejecting anything staler than
    max_age_s.  Stale is treated as missing: a probe that stopped reporting an
    hour ago must not keep contributing to a delta-T."""
    max_age_s = kw.get("max_age_s")
    now = kw.get("now")
    node = tree
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    if not isinstance(node, dict) or "value" not in node:
        return None
    if max_age_s is not None:
        age = _age(node.get("timestamp"), now)
        if age is not None and age > max_age_s:
            logger.warning("LoopDelta ignoring %s, %.0fs stale", ".".join(path), age)
            return None
    return node["value"]


def _gate_open(relay_state, zone_states):
    """True when this loop is pumping.

    `relay_state` is the loop's own pump relay once one is wired, or the shared
    CHIL relay until then.  CHIL alone is not sufficient for a secondary,
    because it asserts when ANY chiller zone calls — including one on the other
    loop, which is exactly the case that fabricates a delta-T.  `zone_states`
    narrows it to this loop's zones.  A zone counts as calling on any non-zero
    equipment state, so the gate works in heating as well as cooling.

    Returns False if the relay is unreadable: no evidence of flow is not
    evidence of flow.
    """
    if not relay_state:
        return False
    if zone_states is None:
        return True                       # no zone narrowing configured
    return any(z is not None and z != 0 for z in zone_states)


def _advance(state, gated, delta, now, settle_s):
    """Advance one loop's run state machine.

    Returns (completed, flowing).  `completed` is the mean delta-T of a run that
    has just ended, and is None on every other cycle — including at the end of a
    run shorter than settle_s, which yields no value at all.  That is correct:
    such a run is entirely startup transient and never held a measurement.
    """
    completed = None
    if gated:
        if not state["running"]:
            state.update(running=True, start=now, sum=0.0, n=0)
        elif delta is not None and now - state["start"] >= settle_s:
            state["sum"] += delta
            state["n"] += 1
    elif state["running"]:
        state["running"] = False
        if state["n"]:
            completed = round(state["sum"] / state["n"], 3)
        else:
            logger.info("LoopDelta run ended with no settled samples; nothing published")
    return completed, gated


def status(config={}, output="default"):
    sk_path = config.get("sk_path", "environment.inside.hvac")
    base = config.get("sk_url", _DEFAULT_URL).rstrip("/")
    timeout = config.get("request_timeout", 5)
    max_age_s = config.get("max_age_s", 120)
    settle_s = config.get("settle_s", 180)
    loops = config.get("loops", {})
    rounding = config.get("rounding", 3)

    now = time.time()
    hvac = _fetch("%s/%s" % (base, sk_path.replace(".", "/")), timeout)
    relays = _fetch("%s/electrical/ac/switch/utility" % base, timeout)
    want_zones = any(loop.get("zones") for loop in loops.values())
    zones = _fetch("%s/environment/inside/thermostat" % base, timeout) if want_zones else {}

    result = {}
    if hvac is None or relays is None or (want_zones and zones is None):
        return _emit(result, sk_path, output)

    for name, loop in loops.items():
        state = _runs.setdefault(name, _new_state())

        sup = _value(hvac, loop["supply"], "temperature", max_age_s=max_age_s, now=now)
        ret = _value(hvac, loop["return"], "temperature", max_age_s=max_age_s, now=now)
        delta = None if sup is None or ret is None else ret - sup

        relay = _value(relays, loop["relay"], "state", max_age_s=max_age_s, now=now)
        zone_states = None
        if loop.get("zones"):
            zone_states = [_value(zones, z, "statenum", max_age_s=max_age_s, now=now)
                           for z in loop["zones"]]

        completed, flowing = _advance(state, _gate_open(relay, zone_states),
                                      delta, now, settle_s)
        result["%s.flowing" % name] = 1 if flowing else 0
        if completed is not None:
            result["%s.deltaT" % name] = round(completed, rounding)
            logger.info("LoopDelta %s run finished: %.3f K over %d samples",
                        name, completed, state["n"])

    return _emit(result, sk_path, output)


def _emit(result, sk_path, output):
    if output != "signalk":
        return result
    from pivac import sk_init_deltas, sk_add_source, sk_add_value
    deltas = sk_init_deltas()
    source = sk_add_source(deltas)
    for key, value in result.items():
        sk_add_value(source, "%s.%s" % (sk_path, key), value)
    return deltas
