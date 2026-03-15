# pivac module template
#
# Copy this file to pivac/MyModuleName.py and fill in the TODOs.
# The module name (file name without .py) must match the config section key in config.yml,
# or be referenced via the `module:` key if multiple config sections share one implementation.
#
# Minimum requirement: implement status(config, output) as described below.

import logging

# TODO: import any libraries your module needs, e.g.:
# import requests
# import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional: module-level initialization
# ---------------------------------------------------------------------------
# Put any one-time setup here (e.g. hardware init, sensor discovery).
# Keep it lightweight — this runs on import, before status() is called.
# If initialization can fail, catch exceptions here and log them; don't let
# an import error take down the whole provider process.
#
# Example:
#   sensors = discover_sensors()


# ---------------------------------------------------------------------------
# status(config, output) — REQUIRED
# ---------------------------------------------------------------------------
# Called repeatedly by pivac-provider.py (once per daemon loop iteration).
# config  : dict of config values from config.yml for this module's section
# output  : "default" → return plain dict; "signalk" → return Signal K delta
#
# Rules:
#   - On error: log a warning and return empty dict / empty deltas. Do NOT
#     raise an exception — the service must keep running.
#   - On success: return the result dict or delta as described below.

def status(config={}, output="default"):

    # ------------------------------------------------------------------
    # 1. Validate required config keys
    # ------------------------------------------------------------------
    # TODO: add checks for any required config keys, e.g.:
    #   if "ipaddr" not in config:
    #       logger.error("No ipaddr in config")
    #       raise ValueError
    #
    # Commonly used config keys (see config.yml.sample for examples):
    #   config["ipaddr"]        — IP address of a remote device
    #   config["inputs"]        — dict of named sensor inputs
    #   config["daemon_sleep"]  — seconds between polls (handled by provider)
    #   config["enabled"]       — true/false (handled by provider)

    result = {}

    # ------------------------------------------------------------------
    # 2. Set up Signal K output structures (only needed if output="signalk")
    # ------------------------------------------------------------------
    if output == "signalk":
        from pivac import sk_init_deltas, sk_add_source, sk_add_value
        deltas = sk_init_deltas()
        sk_source = sk_add_source(deltas)

    # ------------------------------------------------------------------
    # 3. Read your sensor / data source
    # ------------------------------------------------------------------
    # TODO: implement your data collection here.
    #
    # Wrap in a try/except and return gracefully on failure:
    #
    # try:
    #     value = read_my_sensor()
    # except Exception as e:
    #     logger.warning("MyModule: failed to read sensor: %s" % e)
    #     return deltas if output == "signalk" else result
    #
    # For modules with multiple named inputs, iterate over config["inputs"]:
    #
    # from pivac import propagate_defaults
    # inputs = config.get("inputs", {})
    # propagate_defaults(config, inputs, config.get("propagate", []))
    # for key, inp in inputs.items():
    #     value = read_sensor(key)
    #     ...

    # ------------------------------------------------------------------
    # 4. Package the result
    # ------------------------------------------------------------------
    # For "default" output, populate result dict with plain Python values:
    #   result["my_reading"] = value
    #
    # For "signalk" output, add values to the delta using sk_add_value:
    #   sk_add_value(sk_source, "%s.%s" % (inp["sk_path"], inp["outname"]), value)
    #
    # Signal K paths follow the format:  domain.context.measurement
    # Examples from this project:
    #   environment.inside.hvac.{name}.temperature
    #   electrical.ac.switch.utility.{name}.state
    #   propulsion.mainEngine.coolant.pressure

    # TODO: replace with real readings
    # result["example_reading"] = 0.0
    # if output == "signalk":
    #     sk_add_value(sk_source, "environment.inside.example.value", 0.0)

    # ------------------------------------------------------------------
    # 5. Return
    # ------------------------------------------------------------------
    if output == "signalk":
        logger.debug("deltas = %s" % deltas)
        return deltas
    else:
        logger.debug("result = %s" % result)
        return result


# ---------------------------------------------------------------------------
# Standalone test entry point
# ---------------------------------------------------------------------------
# Run directly for quick testing without Signal K:
#   source ~/pivac-venv/bin/activate
#   python pivac/ModuleTemplate.py
#
# Or via the provider script:
#   python scripts/pivac-provider.py pivac.MyModuleName --format pretty

if __name__ == "__main__":
    import json
    logging.basicConfig(
        format='%(name)s %(levelname)s:%(asctime)s %(message)s',
        datefmt='%m/%d/%Y %I:%M:%S',
        level="DEBUG"
    )
    # TODO: pass a representative config dict for local testing, e.g.:
    # test_config = {
    #     "ipaddr": "10.0.0.100",
    #     "inputs": { "psi": { "sk_path": "propulsion.mainEngine.coolant", "outname": "pressure" } }
    # }
    print(json.dumps(status(), indent=2))
