import requests
import logging
import re
import ast
import pytemperature

logger = logging.getLogger(__name__)

# Decimal places kept on a Kelvin temperature when the config says nothing.
# 2 dp is 0.018 degF, finer than any sensor feeding this module. Whole Kelvin
# is 1.8 degF, which is coarser than the hardware and destroys small deltas.
DEFAULT_ROUNDING = 2


def _to_kelvin(value, scale):
    """Convert a raw temperature reading to Kelvin. Default scale is fahrenheit
    (what the Arduino emits); celsius and kelvin are also accepted."""
    if scale == "kelvin":
        return float(value)
    if scale == "celsius":
        return pytemperature.c2k(float(value))
    return pytemperature.f2k(float(value))


def _round_temp(kelvin, digits):
    """Apply the OneWireTherm rounding convention to a Kelvin reading: 0 rounds
    to whole Kelvin, a positive value keeps that many decimals, and a negative
    value leaves the reading alone."""
    if digits == 0:
        return int(round(kelvin, 0))
    if digits > 0:
        return round(kelvin, digits)
    return kelvin

def status(config = {}, output = "default"):
    result = {}
    sensors = {}

    if "ipaddr" not in config:
        logger.error("No IP address specified in config file.")
        raise ValueError
    if "inputs" not in config:
        logger.error("No inputs specified in config file.")
        raise ValueError
    else:
        sensors = config["inputs"]

    if output == "signalk":
        logger.debug("prepping sk output...")
        from pivac import sk_init_deltas, sk_add_source, sk_add_value
        deltas = sk_init_deltas()
        sk_source = sk_add_source(deltas)

    try:
        logger.debug("Parsing Arduino response...")
        r = requests.get("http://%s" % config["ipaddr"], timeout=2)
        logger.debug("Got request: %s" % r.text)
        # The Arduino returns single-quoted pseudo-JSON (e.g. {'psi' : 18.4, 'temp' : 120.5})
        # wrapped in HTML boilerplate. We extract the dict-like line with a regex, then parse
        # it with ast.literal_eval (not json.loads) because single-quoted keys are valid
        # Python literals but not valid JSON. Do not change to json.loads without also
        # updating the Arduino sketches to emit double-quoted keys.
        parsed = ast.literal_eval(re.findall(r'.*\{.*\}',r.text)[0])

        # Each config input is keyed by the field name in the Arduino's response dict.
        # Inputs with `type: temperature` are converted to Kelvin and emitted at
        # {sk_path}.{outname}.temperature (matching the OneWireTherm convention); every
        # other field passes through unchanged at {sk_path}.{outname}. This keeps the two
        # existing pressure services byte-for-byte identical — their `psi` input has no
        # `type`, so it takes the pass-through branch exactly as before.
        #
        # `rounding` follows OneWireTherm's semantics and is read per-input first, then
        # from the module block, then DEFAULT_ROUNDING. Checking the module block directly
        # means it works whether or not the operator remembered to list it in `propagate`.
        # It applies only to the temperature branch; pass-through values are never rounded.
        for field, scfg in sensors.items():
            if field not in parsed:
                logger.warning("Arduino at %s: field '%s' missing from response %s"
                               % (config["ipaddr"], field, parsed))
                continue
            raw = parsed[field]
            outname = scfg["outname"]
            sk_path = scfg["sk_path"]

            if scfg.get("type") == "temperature":
                digits = scfg.get("rounding", config.get("rounding", DEFAULT_ROUNDING))
                kelvin = _round_temp(_to_kelvin(raw, scfg.get("scale", "fahrenheit")), digits)
                if output == "signalk":
                    sk_add_value(sk_source, "%s.%s.temperature" % (sk_path, outname), kelvin)
                else:
                    result[outname] = raw
            else:
                if output == "signalk":
                    sk_add_value(sk_source, "%s.%s" % (sk_path, outname), raw)
                else:
                    result[outname] = raw
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        logger.warning("Arduino at %s unreachable (timeout)" % config["ipaddr"])
    except Exception as e:
        logger.warning("Arduino at %s: failed to parse response: %s" % (config["ipaddr"], e))

    if output == "signalk":
        logger.debug("deltas = %s" % deltas)
        return deltas
    else:
        logger.debug("result = %s" % result)
        return result

if __name__ == "__main__":
    logging.basicConfig(format='%(name)s %(levelname)s:%(asctime)s %(message)s',datefmt='%m/%d/%Y %I:%M:%S',level="DEBUG")

    status()
