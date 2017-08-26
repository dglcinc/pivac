import xml.etree.ElementTree as ET
import requests
import logging
import re

logger = logging.getLogger(__name__)

def status(config = {}, output = "default"):
    result = {}
    xmlpaths = {}

    if "ipaddr" not in config:
        logger.exception("No IP address specified in config file.")
        raise ValueError
    if "inputs" not in config:
        logger.exception("No inputs specified in config file.")
        raise ValueError
    else:
        xmlpaths = config["inputs"]

    if output == "signalk":
        logger.debug("prepping sk output...")
        from pivac import sk_init_deltas, sk_add_source, sk_add_value
        deltas = sk_init_deltas()
        sk_source = sk_add_source(deltas)

    try:
        logger.debug("Parsing TED data...")
        page = requests.get("http://%s/api/LiveData.xml" % config["ipaddr"], timeout=2)
        
        logger.debug("Got request...")
        e = ET.fromstring(page.text)
#        logger.debug("E = %s" % e.__dict__)

        for i in xmlpaths.keys():
#            logger.debug("i = %s" % i)
            a = e.find(".//%s" % i)
#            logger.debug("a = %s" % a.__dict__)

#                logger.debug("xmlpaths = %s, i = %s, xmlpaths[i] = %s, name = %s" % (xmlpaths, i, xmlpaths[i], xmlpaths[i]["outname"]))
            if output == "signalk":
                sk_add_value(sk_source,"%s.%s.power" % (xmlpaths[i]["sk_path"], xmlpaths[i]["outname"]), int(a.text))
            else:
                result[xmlpaths[i]["outname"]] = int(a.text)
    except:
        logger.exception("Exception collecting data from TED5000")

    if output == "signalk":
        logger.debug("deltas = %s" % deltas)
        return deltas
    else:
        logger.debug("result = %s" % result)
        return result

if __name__ == "__main__":
    logging.basicConfig(format='%(name)s %(levelname)s:%(asctime)s %(message)s',datefmt='%m/%d/%Y %I:%M:%S',level="DEBUG")

    status()
