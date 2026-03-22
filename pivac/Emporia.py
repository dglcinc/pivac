import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Module-level cache: authenticated PyEmVue instance and device properties.
# Both persist across calls within a single daemon process, avoiding
# re-authentication and re-discovery on every poll cycle.
_vue = None
_device_cache = {}  # gid (int) -> {'name': str, 'channels': {channel_num: channel_name}}


def _sanitize(name):
    """Convert a human-readable circuit name into a Signal K path component."""
    return name.lower().replace(' ', '_').replace('/', '_').replace('-', '_').replace('(', '').replace(')', '')


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
    """
    global _device_cache
    if _device_cache:
        return _device_cache

    panels = config.get('panels', {})
    devices = vue.get_devices()
    for device in devices:
        vue.populate_device_properties(device)

    for device in devices:
        gid = device.device_gid
        panel_name = panels.get(str(gid), 'panel_%s' % gid)
        channel_names = {}
        if device.channels:
            for ch in device.channels:
                channel_names[ch.channel_num] = ch.name or ('channel_%s' % ch.channel_num)
        _device_cache[gid] = {
            'name': panel_name,
            'channel_names': channel_names,
        }
        logger.info("Discovered Emporia device GID %s -> panel '%s' with %d channels" % (
            gid, panel_name, len(channel_names)))

    return _device_cache


def status(config={}, output="default"):
    """
    Poll all configured Emporia panels and return current power readings in Watts.

    Each channel (main feed legs + individual circuit clamps) becomes a separate
    Signal K value at path:  <sk_path>.<panel_name>.<circuit_name>

    Config keys:
        username       Emporia account email
        password       Emporia account password
        token_file     Path for token cache (default: /etc/pivac/emporia-tokens.json)
        sk_path        Signal K base path (default: electrical.emporia)
        panels         Dict mapping GID strings to panel names
                         e.g. {"123456789": "house", "987654321": "apartment"}
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

            for channel_num, channel in usage_device.channels.items():
                if channel is None or channel.usage is None:
                    continue

                # API returns kWh over the scale interval (1 minute); convert to watts.
                # kWh/min * 60 min/hr * 1000 W/kW = W
                watts = round(channel.usage * 60 * 1000, 1)

                # Use the cached channel name from populate_device_properties; fall back
                # to the name on the usage object, then a generic label.
                raw_name = (channel_names.get(channel_num)
                            or getattr(channel, 'name', None)
                            or 'channel_%s' % channel_num)
                cname = _sanitize(raw_name)
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
