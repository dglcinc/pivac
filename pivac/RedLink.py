"""RedLink — Honeywell thermostat polling via the official mobile API.

Replaces the previous mytotalconnectcomfort.com HTML scraper. The scraper
triggered Honeywell's bot detection on the login endpoint, causing repeated
"Too Many Attempts" lockouts. aiosomecomfort uses the same TCC mobile API the
iOS app uses, with long-lived OAuth-style session cookies.

A single AIOSomeComfort client + aiohttp.ClientSession is kept alive across
status() calls in a background event loop. Re-creating the session every poll
would hit the library's MAX_LOGIN_ATTEMPTS / MIN_LOGIN_TIME rate limit.
"""
import asyncio
import logging
import re
import socket
import threading
import time

import aiohttp
import aiosomecomfort
import pytemperature

logger = logging.getLogger(__name__)

# Warn if a full status() cycle (connect + parallel refresh) exceeds this many
# seconds. Healthy cycles run 5–15s; sustained values above this threshold
# show up as stale-data flicker in WilhelmSK widgets long before the
# `redlink-stale-fast` (10m) freshness alert fires.
CYCLE_WARN_THRESHOLD = 20.0

# Hard per-device deadline for `dev.refresh()`. Independent of the config's
# `request_timeout` (which governs the aiosomecomfort client used for login —
# cold-start login on the Pi takes ~75s and must not be cut short). With
# refreshes parallelised, this is the worst-case cycle time when one device
# stalls: a single slow thermostat can no longer drag the others past it.
REFRESH_DEADLINE = 12.0

_loop = None
_loop_thread = None
_session = None
_client = None
_lock = threading.Lock()

# Health state — exported as SK values every cycle so Grafana can alert on
# sustained errors without waiting for the freshness rule to time out.
# `_last_error_type` is "" on success, otherwise the exception class name
# (AuthError, APIRateLimited, UnexpectedResponse, TimeoutError, ...).
_consecutive_errors = 0
_last_error_type = ""

_STATENUMS = {"heat": 1, "cool": -1, "fan": 0.5, "off": 0}


def _ensure_loop():
    global _loop, _loop_thread
    if _loop is not None and _loop.is_running():
        return
    _loop = asyncio.new_event_loop()
    _loop_thread = threading.Thread(
        target=_loop.run_forever, daemon=True, name="redlink-loop"
    )
    _loop_thread.start()


def _run(coro):
    _ensure_loop()
    return asyncio.run_coroutine_threadsafe(coro, _loop).result()


async def _connect(uid, pwd, timeout):
    global _session, _client
    if _session is None or _session.closed:
        # force_close=True works around an aiohttp+Python 3.13 hang on the
        # second request to mytotalconnectcomfort.com — login() POSTs then
        # GETs /portal, and the GET stalls indefinitely if connection
        # pooling is on. Closing after each request is fine here: we only
        # poll every few seconds and TLS resumption keeps the cost low.
        connector = aiohttp.TCPConnector(force_close=True, family=socket.AF_INET)
        _session = aiohttp.ClientSession(connector=connector)
    if _client is None:
        _client = aiosomecomfort.AIOSomeComfort(
            uid, pwd, timeout=timeout, session=_session
        )
        await _client.login()
        await _client.discover()


async def _refresh_one(dev):
    try:
        await asyncio.wait_for(dev.refresh(), timeout=REFRESH_DEADLINE)
        return dev
    except (asyncio.TimeoutError, aiosomecomfort.ConnectionTimeout,
            aiosomecomfort.ConnectionError) as e:
        logger.warning("RedLink %s refresh failed (%s); skipping this cycle",
                       dev.name, type(e).__name__)
        return None


async def _refresh_all():
    """Refresh every device concurrently. Sequential refreshes serialise five
    HTTPS round-trips to Honeywell per cycle (each ~5–15s on the Pi with
    force_close=True), pushing total cycle time to 30–75s and producing
    visible stale-data flicker in WilhelmSK widgets. asyncio.gather brings
    cycle time down to max(per-device latency). Per-device failures are
    logged and dropped — publishing 4 of 5 thermostats is better than
    dropping the whole poll."""
    devs = [
        dev
        for loc in _client.locations_by_id.values()
        for dev in loc.devices_by_id.values()
    ]
    results = await asyncio.gather(*[_refresh_one(d) for d in devs])
    return [d for d in results if d is not None]


async def _reset():
    global _session, _client
    if _client is not None:
        try:
            await _client.logoff()
        except Exception:
            pass
        _client = None
    if _session is not None and not _session.closed:
        await _session.close()
    _session = None


def _to_kelvin(value, scale):
    if scale == "celsius":
        return pytemperature.c2k(float(value))
    return pytemperature.f2k(float(value))


def status(config={}, output="default"):
    global _consecutive_errors, _last_error_type

    if "uid" not in config or "pwd" not in config:
        logger.error("Credentials not specified in config file.")
        raise ValueError

    uid = config["uid"]
    pwd = config["pwd"]
    timeout = config.get("request_timeout", 30)
    inputs = config.get("inputs", {})

    inside_path = inputs.get("thermostat", {}).get(
        "sk_path", "environment.inside.thermostat"
    )
    outside_path = inputs.get("outdoor_sensor", {}).get(
        "sk_path", "environment.outside.thermostat"
    )

    devices = None
    error = None
    cycle_start = time.monotonic()
    with _lock:
        try:
            _run(_connect(uid, pwd, timeout))
            devices = _run(_refresh_all())
        except aiosomecomfort.AuthError as e:
            logger.exception("Honeywell auth failed")
            error = e
            _run(_reset())
        except aiosomecomfort.APIRateLimited as e:
            logger.warning("Honeywell rate-limited; will retry next cycle")
            error = e
            _run(_reset())
        except (
            aiosomecomfort.ConnectionError,
            aiosomecomfort.ConnectionTimeout,
            aiosomecomfort.SessionTimedOut,
            aiosomecomfort.UnexpectedResponse,
            aiosomecomfort.ServiceUnavailable,
        ) as e:
            logger.warning("RedLink transient error: %s: %s", type(e).__name__, e)
            error = e
            _run(_reset())
        except Exception as e:
            logger.exception("RedLink unexpected error")
            error = e
            _run(_reset())

    cycle_elapsed = time.monotonic() - cycle_start
    if cycle_elapsed > CYCLE_WARN_THRESHOLD:
        logger.warning("RedLink cycle took %.1fs (threshold %.0fs) — expect WilhelmSK widget freshness flicker",
                       cycle_elapsed, CYCLE_WARN_THRESHOLD)

    if error is not None:
        _consecutive_errors += 1
        _last_error_type = type(error).__name__
    elif not devices:
        # connect/login worked but every device refresh failed individually
        _consecutive_errors += 1
        _last_error_type = "AllDevicesFailed"
    else:
        _consecutive_errors = 0
        _last_error_type = ""

    # Surface health metrics every cycle (success or failure) so Grafana can
    # alert on sustained errors without waiting for the data-freshness rule.
    # On error we return a deltas object containing only the health values —
    # the orchestrator pushes them to Signal K, while existing thermostat
    # values age out and the redlink-stale alerts eventually fire too.
    if output == "signalk":
        from pivac import sk_init_deltas, sk_add_source, sk_add_value
        deltas = sk_init_deltas()
        sk_source = sk_add_source(deltas)
        sk_add_value(sk_source, f"{inside_path}.redlink.consecutiveErrors", _consecutive_errors)
        sk_add_value(sk_source, f"{inside_path}.redlink.lastErrorType", _last_error_type)
        if not devices:
            return deltas

    if not devices:
        # default-output callers (manual scripts, tests) still want to see errors.
        raise IOError(f"RedLink poll failed: {_last_error_type} (consecutive={_consecutive_errors})")

    result = {}
    outdoor_humidity_pct = None

    for dev in devices:
        name = dev.name or str(dev.deviceid)
        fname = re.sub(r"\s+", "_", name)

        scale = "fahrenheit" if dev.temperature_unit == "F" else "celsius"
        if name in inputs and "scale" in inputs[name]:
            scale = inputs[name]["scale"]

        if dev.current_temperature is None:
            logger.warning("Skipping %s — no current_temperature", name)
            continue
        ktemp = _to_kelvin(dev.current_temperature, scale)

        state = dev.equipment_output_status or "off"
        if state not in _STATENUMS:
            state = "off"

        humidity_pct = float(dev.current_humidity) if dev.current_humidity is not None else 0.0
        heatset = int(float(dev.setpoint_heat)) if dev.setpoint_heat is not None else None
        coolset = int(float(dev.setpoint_cool)) if dev.setpoint_cool is not None else None

        if dev.outdoor_humidity is not None and outdoor_humidity_pct is None:
            outdoor_humidity_pct = float(dev.outdoor_humidity)

        if output == "signalk":
            sk_add_value(sk_source, f"{inside_path}.{fname}.temperature", int(ktemp))
            sk_add_value(sk_source, f"{inside_path}.{fname}.scale", scale)
            sk_add_value(sk_source, f"{inside_path}.{fname}.humidity", humidity_pct / 100.0)
            sk_add_value(sk_source, f"{inside_path}.{fname}.redlinkid", str(dev.deviceid))
            sk_add_value(sk_source, f"{inside_path}.{fname}.state", state)
            sk_add_value(sk_source, f"{inside_path}.{fname}.statenum", _STATENUMS[state])
            if heatset is not None:
                sk_add_value(sk_source, f"{inside_path}.{fname}.heatset", heatset)
            if coolset is not None:
                sk_add_value(sk_source, f"{inside_path}.{fname}.coolset", coolset)
        else:
            result[str(dev.deviceid)] = {
                "name": name,
                "temp": dev.current_temperature,
                "scale": scale,
                "hum": humidity_pct,
                "status": state,
                "heatset": heatset,
                "coolset": coolset,
            }

    if output == "signalk":
        if outdoor_humidity_pct is not None:
            sk_add_value(sk_source, f"{outside_path}.humidity", outdoor_humidity_pct / 100.0)
        return deltas

    if outdoor_humidity_pct is not None:
        result["outhum"] = outdoor_humidity_pct
    return result
