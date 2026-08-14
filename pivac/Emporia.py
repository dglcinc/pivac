import logging
import re
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Module-level cache: authenticated PyEmVue instance and device properties.
# Both persist across calls within a single daemon process, avoiding
# re-authentication and re-discovery on every poll cycle.
_vue = None
_device_cache = {}  # gid (int) -> {'name': str, 'channels': {channel_num: channel_name}}
_device_cache_time = 0.0  # monotonic timestamp of the last successful refresh

# Channel names live in the Emporia app, not in our config, so renaming a circuit
# there must eventually reach us. Re-read them periodically rather than caching
# for the life of the daemon -- see the note in _get_device_cache().
NAME_REFRESH_S = 3600


# Characters that read as word separators become underscores; everything else that
# is not [a-z0-9_] is dropped. Anything surviving here ends up in a Signal K path
# AND an InfluxDB measurement name, so it has to be quoting-safe and dot-free --
# a '.' would silently split the path into an extra level of nesting.
_SEPARATORS = re.compile(r'[\s/\-+&,]+')
_ILLEGAL = re.compile(r'[^a-z0-9_]')


def _sanitize(name):
    """Convert a human-readable circuit name into a Signal K path component.

    Emporia app labels are free text ("Don't know", "Microwave + Refrigerator"),
    but the result is used as both a Signal K path component and an InfluxDB
    measurement name. Punctuation that needs quoting in InfluxQL -- apostrophes
    especially -- is stripped rather than escaped, and '.' is removed because it
    would otherwise create an unintended nested path.
    """
    s = _SEPARATORS.sub('_', name.lower())
    s = _ILLEGAL.sub('', s)
    s = re.sub(r'_+', '_', s).strip('_')
    return s or 'unnamed'


def _get_vue(config):
    """Return (or create) an authenticated PyEmVue instance."""
    global _vue
    if _vue is not None:
        return _vue
    try:
        import pyemvue
        _vue = pyemvue.PyEmVue()
        token_file = config.get('token_file', '/etc/pivac/emporia-tokens.json')
        _vue.login(
            username=config['username'],
            password=config['password'],
            token_storage_file=token_file
        )
        logger.info("Authenticated with Emporia API (token cached at %s)" % token_file)
    except Exception as e:
        logger.error("Failed to authenticate with Emporia: %s" % e)
        _vue = None
        raise
    return _vue


def _get_device_cache(vue, config):
    """
    Build (or return cached) a mapping of device GID to panel name and channel names.

    Config 'panels' maps GID strings to friendly panel names, e.g.:
        panels:
            "123456789": house
            "987654321": apartment

    Channel names come from the Emporia app via populate_device_properties().

    The cache is refreshed every `name_refresh_s` seconds (default 3600) rather
    than held for the life of the daemon. Renaming a circuit in the Emporia app
    otherwise has no effect until the service is restarted by hand: the module
    keeps emitting the old Signal K path, which looks like a stale sensor rather
    than a stale label. Refreshing is not free -- populate_device_properties() is
    an extra cloud call per device -- so it is done on a timer, not every cycle.

    A refresh that raises keeps the previous cache, so a transient Emporia API
    failure degrades to slightly stale names rather than losing all of them.
    """
    global _device_cache, _device_cache_time

    ttl = config.get('name_refresh_s', NAME_REFRESH_S)
    if _device_cache and (time.monotonic() - _device_cache_time) < ttl:
        return _device_cache

    panels = config.get('panels', {})
    try:
        devices = vue.get_devices()
        for device in devices:
            vue.populate_device_properties(device)
    except Exception as e:
        if _device_cache:
            logger.warning("Emporia channel-name refresh failed (%s: %s); "
                           "keeping the previous names" % (type(e).__name__, e))
            return _device_cache
        raise

    fresh = {}
    for device in devices:
        gid = device.device_gid
        panel_name = panels.get(str(gid), 'panel_%s' % gid)
        channel_names = {}
        if device.channels:
            for ch in device.channels:
                channel_names[ch.channel_num] = ch.name or ('channel_%s' % ch.channel_num)
        fresh[gid] = {
            'name': panel_name,
            'channel_names': channel_names,
        }

    # A rename changes the Signal K path and the InfluxDB measurement, and leaves
    # the old path frozen in Signal K until the server restarts -- worth a WARNING
    # so the cause is obvious in the journal rather than looking like a dead sensor.
    for gid, entry in fresh.items():
        old = (_device_cache.get(gid) or {}).get('channel_names', {})
        new = entry['channel_names']
        if old and old != new:
            changed = sorted('%s: %r -> %r' % (n, old.get(n), new.get(n))
                             for n in set(old) | set(new) if old.get(n) != new.get(n))
            logger.warning("Emporia channel names changed on GID %s (%s). New Signal K "
                           "paths start fresh; restart signalk to drop the old ones."
                           % (gid, '; '.join(changed)))
        elif not old:
            logger.info("Discovered Emporia device GID %s -> panel '%s' with %d channels" % (
                gid, entry['name'], len(new)))

    _device_cache = fresh
    _device_cache_time = time.monotonic()
    return _device_cache


def status(config={}, output="default"):
    """
    Poll all configured Emporia panels and return current power readings in Watts.

    Each channel (main feed legs + individual circuit clamps) becomes a separate
    Signal K value at path:  <sk_path>.<panel_name>.<circuit_name>

    Circuit names are taken from the Emporia app labels, sanitized to lowercase
    with spaces and punctuation replaced by underscores.

    Required config keys:
        username       Emporia account email
        password       Emporia account password

    Optional config keys:
        token_file     Path for cached auth token
                         default: /etc/pivac/emporia-tokens.json
        sk_path        Signal K base path for all readings
                         default: electrical.emporia
        panels         Dict mapping device GID strings to friendly panel names.
                         If omitted, all panels are included with auto-generated
                         names (panel_<gid>). Run scripts/emporia-discover.py to
                         find GIDs.
                         e.g. {"194331": "house", "265129": "apartment"}
        daemon_sleep   Seconds between polls (framework-level key, not read by
                         this module directly). Should match the API scale window;
                         60 seconds pairs with the hardcoded Scale.MINUTE query.
                         default: 0 (framework default — set to 60 in config)
    """
    global _vue, _device_cache

    for key in ('username', 'password'):
        if key not in config:
            logger.error("Emporia: '%s' required in config" % key)
            raise ValueError("Emporia: '%s' required in config" % key)

    result = {}

    if output == "signalk":
        from pivac import sk_init_deltas, sk_add_source, sk_add_value
        deltas = sk_init_deltas()
        sk_source = sk_add_source(deltas)

    try:
        from pyemvue.enums import Scale, Unit

        vue = _get_vue(config)
        cache = _get_device_cache(vue, config)
        sk_base = config.get('sk_path', 'electrical.emporia')

        gids = list(cache.keys())
        devices_usage = vue.get_device_list_usage(
            deviceGids=gids,
            instant=datetime.now(timezone.utc),
            scale=Scale.MINUTE.value,
            unit=Unit.KWH.value
        )  # returns dict[int, VueUsageDevice] directly (no timestamp) since pyemvue API update

        for gid, usage_device in devices_usage.items():
            if gid not in cache:
                logger.warning("Emporia: received data for unknown GID %s, skipping" % gid)
                continue
            if usage_device is None:
                logger.warning("Emporia: no usage data returned for panel '%s' (GID %s)" % (
                    cache[gid]['name'], gid))
                continue

            panel_name = cache[gid]['name']
            channel_names = cache[gid]['channel_names']

            # Sum watts per circuit name before emitting: a 240 V circuit
            # monitored with one CT per leg appears as two channels sharing a
            # name (house panel ch 1+2, 3+4, 5+6, 7+8). Emitting per channel
            # sent both legs to the same SK path and the second overwrote the
            # first, halving the reported power for those circuits.
            circuit_watts = {}
            for channel_num, channel in usage_device.channels.items():
                if channel is None or channel.usage is None:
                    continue

                # API returns kWh over the scale interval (1 minute); convert to watts.
                # kWh/min * 60 min/hr * 1000 W/kW = W
                watts = channel.usage * 60 * 1000

                # Use the cached channel name from populate_device_properties; fall back
                # to the name on the usage object, then a generic label.
                raw_name = (channel_names.get(channel_num)
                            or getattr(channel, 'name', None)
                            or 'channel_%s' % channel_num)
                cname = _sanitize(raw_name)
                circuit_watts[cname] = circuit_watts.get(cname, 0.0) + watts

            for cname, watts in circuit_watts.items():
                watts = round(watts, 1)
                sk_path = "%s.%s.%s" % (sk_base, panel_name, cname)

                if output == "signalk":
                    sk_add_value(sk_source, sk_path, watts)
                    logger.debug("Emporia: %s = %s W" % (sk_path, watts))
                else:
                    result["%s.%s" % (panel_name, cname)] = watts

    except Exception as e:
        logger.error("Emporia: failed to get usage data: %s" % e)
        # Reset caches to force re-auth and re-discovery on next poll cycle,
        # in case the session expired or the device list changed.
        _vue = None
        _device_cache = {}

    if output == "signalk":
        logger.debug("deltas = %s" % deltas)
        return deltas
    else:
        logger.debug("result = %s" % result)
        return result


if __name__ == "__main__":
    import json
    logging.basicConfig(
        format='%(name)s %(levelname)s:%(asctime)s %(message)s',
        datefmt='%m/%d/%Y %I:%M:%S',
        level="DEBUG"
    )
    print(json.dumps(status(), indent=2))
