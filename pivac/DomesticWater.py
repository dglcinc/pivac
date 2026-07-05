"""pivac.DomesticWater — the DAE MJ-75a domestic water-meter node.

A thin wrapper over pivac.ArduinoSensor that adds one value the node does not
emit: the gallons consumed during the *current* flow session
(`environment.water.domestic.runVolume`, 0 while idle).

The node already publishes the lifetime totalizer (`consumption`) and the
`flowing` flag, which is everything needed — so this is computed here on the Pi
(no firmware change): snapshot the totalizer when flow starts, report the delta
while flowing. State persists across polls in the long-running provider daemon.
`consumption` (lifetime) and `runDuration`/`runningFor` (this draw's duration)
come straight through from ArduinoSensor unchanged.
"""
import logging
import pivac.ArduinoSensor as ArduinoSensor

logger = logging.getLogger(__name__)

# --- per-flow-session state (persists across status() calls in the daemon) ---
_run_start_volume = None   # totalizer (gal) captured when the current flow began
_was_flowing = False
_last_run_volume = 0.0      # gallons of the current/most-recent draw (HELD while idle)


def _session_gallons(volume, flowing):
    """Update session state and return gallons for the current draw. The value
    is held after flow stops (shows the last draw's total until the next draw
    starts, then resets to 0 and counts up again). Returns None when data is
    missing (node unreachable) so a dropped poll neither disturbs the session
    nor emits a bogus value."""
    global _run_start_volume, _was_flowing, _last_run_volume
    if volume is None or flowing is None:
        return None
    flowing = bool(flowing)
    if flowing:
        if not _was_flowing or _run_start_volume is None:
            _run_start_volume = volume        # new draw (or mid-flow start): snapshot totalizer
        _last_run_volume = round(volume - _run_start_volume, 1)
    _was_flowing = flowing
    return _last_run_volume                    # while idle this holds the last draw's total


def status(config={}, output="default"):
    sk_path = config.get("sk_path", "environment.water.domestic")
    data = ArduinoSensor.status(config, output)

    if output == "signalk":
        vals = {v["path"]: v["value"]
                for upd in data.get("updates", []) for v in upd.get("values", [])}
        gal = _session_gallons(vals.get("%s.consumption" % sk_path),
                               vals.get("%s.flowing" % sk_path))
        if gal is not None and data.get("updates"):
            data["updates"][0]["values"].append(
                {"path": "%s.runVolume" % sk_path, "value": gal})
    else:
        gal = _session_gallons(data.get("consumption"), data.get("flowing"))
        if gal is not None:
            data["runVolume"] = gal
    return data


if __name__ == "__main__":
    logging.basicConfig(format='%(name)s %(levelname)s:%(asctime)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S', level="DEBUG")
    import json
    print(json.dumps(status(), indent=2))
