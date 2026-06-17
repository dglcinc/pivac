"""
pivac.Sprinkler — OpenSprinkler irrigation flow via the local HTTP API.

Polls the OpenSprinkler controller's `/jc` (controller variables) endpoint and
publishes the irrigation flow rate to Signal K, so it can be overlaid on the
domestic-water flow graph (a parallel `environment.water.irrigation.*` path —
no collision with the iPerl's `environment.water.domestic.*`).

Flow math (per the OpenSprinkler 2.2.1 API):
    flcrt = flow-sensor clicks counted during the last `flwrt` window
    flwrt = flow count window (firmware-dependent units)
    fpr   = volume per click = ((fpr1<<8) + fpr0) / 100   (from /jo; cached)
    flow rate = (flcrt / flwrt) * fpr * 60 * flow_scale   [volume/min]

`flow_scale` (default 1.0) is a one-time calibration multiplier: the `flwrt`
window units are firmware-dependent, so the absolute scale should be checked
once against a live irrigation run (compare to the OS app's reported flow) and
`flow_scale` tuned in config — no code change needed.

Required config keys:
    host            OpenSprinkler IP (e.g. 10.0.0.17)
    password_md5    MD5 hash of the OS *device* password (Pi config only — never
                    in the repo). The OS local API authenticates with md5(pw).

Optional config keys:
    port            HTTP port (default 5000)
    flow_scale      calibration multiplier on the computed rate (default 1.0)
    fpr             volume-per-click override (default: read from /jo and cache)
    timeout         HTTP timeout seconds (default 8)
    daemon_sleep    seconds between cycles (framework key; recommend 15)

Signal K paths emitted:
    environment.water.irrigation.flowRate  number, gallons/min (assumes OS imperial units)
    environment.water.irrigation.active    number 0/1 (any station currently running)
"""

import logging

logger = logging.getLogger(__name__)

_cache = {"fpr": None}

FLOWRATE_PATH = "environment.water.irrigation.flowRate"
ACTIVE_PATH = "environment.water.irrigation.active"


def _require_requests():
    try:
        import requests
        return requests
    except ImportError:
        raise ImportError("Sprinkler module requires requests "
                          "(pip install requests --break-system-packages)")


def _base(config):
    host = config.get("host")
    if not host:
        raise ValueError("Sprinkler: 'host' required in config")
    return "http://%s:%s" % (host, config.get("port", 5000))


def _get_json(config, endpoint):
    requests = _require_requests()
    pw = config.get("password_md5")
    if not pw:
        raise ValueError("Sprinkler: 'password_md5' required in config")
    r = requests.get("%s/%s" % (_base(config), endpoint),
                     params={"pw": pw}, timeout=config.get("timeout", 8))
    r.raise_for_status()
    data = r.json()
    # An OS error response is {"result": <code>} (2 = unauthorized); a successful
    # /jc or /jo returns the data object with no top-level "result".
    if isinstance(data, dict) and data.get("result") not in (None, 1):
        raise RuntimeError("OpenSprinkler %s returned result=%s (2=unauthorized)"
                           % (endpoint, data["result"]))
    return data


def _flow_per_click(config):
    """volume per flow-sensor click; from config override or cached /jo read."""
    if config.get("fpr") is not None:
        return float(config["fpr"])
    if _cache["fpr"] is None:
        jo = _get_json(config, "jo")
        _cache["fpr"] = ((jo.get("fpr1", 0) << 8) + jo.get("fpr0", 0)) / 100.0
        logger.info("Sprinkler: flow pulse rate fpr=%s vol/click (sn1t=%s)",
                    _cache["fpr"], jo.get("sn1t"))
    return _cache["fpr"]


def _any_station_active(jc) -> int:
    """ps = per-station [program_id, remaining_sec, start_time]; remaining>0 = running."""
    for st in jc.get("ps", []):
        if isinstance(st, list) and len(st) >= 2 and st[1] > 0:
            return 1
    return 0


def status(config={}, output="default"):
    jc = _get_json(config, "jc")
    flcrt = jc.get("flcrt", 0)
    flwrt = jc.get("flwrt", 0)
    fpr = _flow_per_click(config)
    scale = config.get("flow_scale", 1.0)

    flow_rate = 0.0
    if flwrt and flcrt:
        flow_rate = (flcrt / flwrt) * fpr * 60.0 * scale   # volume/min
    flow_rate = round(flow_rate, 3)
    active = _any_station_active(jc)
    logger.debug("Sprinkler: flcrt=%s flwrt=%s fpr=%s -> flowRate=%s gpm active=%s",
                 flcrt, flwrt, fpr, flow_rate, active)

    if output == "signalk":
        from pivac import sk_init_deltas, sk_add_source, sk_add_value
        deltas = sk_init_deltas()
        src = sk_add_source(deltas)
        sk_add_value(src, FLOWRATE_PATH, flow_rate)
        sk_add_value(src, ACTIVE_PATH, active)
        return deltas

    return {FLOWRATE_PATH: flow_rate, ACTIVE_PATH: active}


if __name__ == "__main__":
    import json
    import sys
    logging.basicConfig(format="%(name)s %(levelname)s: %(message)s", level=logging.DEBUG)
    try:
        import yaml
    except ImportError:
        sys.exit("PyYAML required")
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "/etc/pivac/config.yml"
    with open(cfg_path) as f:
        config = yaml.safe_load(f).get("pivac.Sprinkler", {})
    print(json.dumps(status(config), indent=2))
