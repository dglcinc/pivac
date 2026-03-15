import requests
import logging
import re
import ast

logger = logging.getLogger(__name__)

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
        logger.debug("Parsing pressure response...")
        r = requests.get("http://%s" % config["ipaddr"], timeout=2)
        logger.debug("Got request: %s" % r.text)
        # The Arduino returns single-quoted pseudo-JSON (e.g. {'psi' : 18.4}) wrapped in
        # HTML boilerplate. We extract the dict-like line with a regex, then parse it with
        # ast.literal_eval (not json.loads) because single-quoted keys are valid Python
        # literals but not valid JSON. Do not change to json.loads without also updating
        # the Arduino sketches to emit double-quoted keys.
        psi = ast.literal_eval(re.findall(r'.*\{.*\}',r.text)[0])['psi']

        if output == "signalk":
            sk_add_value(sk_source,"%s.%s" % (sensors["psi"]["sk_path"], sensors["psi"]["outname"]), psi)
        else:
            result[sensors["psi"]["outname"]] = psi
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
