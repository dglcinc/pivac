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
    if "xmlpaths" not in config:
        logger.exception("No xml paths specified in config file.")
        raise ValueError
    else:
        xmlpaths = config["xmlpaths"]

    if output == "signalk":
        logger.debug("prepping sk output...")
        from pivac import sk_init_deltas, sk_add_delta
        dpath = ""
        dformatted = False
        deltas = sk_init_deltas()

        # get signalk default format, if any
        if "sk_formatted" in config:
            dpath = config["sk_formatted"]
            dformatted = True
        elif "sk_literal" in config:
            dpath = config["sk_literal"]
        logger.debug("dpath = %s(%d)" % (dpath, dformatted))

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

            if output == "signalk":
                kpath = ""
                kformatted = False
                
                # if there is config for this sensor, get it
                if "sk_formatted" in xmlpaths[i]:
                    kformatted = True
                    kpath = xmlpaths[i]["sk_formatted"]
                elif "sk_literal" in xmlpaths[i]:
                    kpath = xmlpaths[i]["sk_literal"]
                logger.debug("kpath = %s(%d) - path %s, name %s" % (kpath, kformatted, i, xmlpaths[i]["name"]))
    
                # set output values, favoring sensor-specific if found
                opath = dpath
                oformatted = dformatted
                if len(kpath):
                    opath = kpath
                    oformatted = kformatted
                if len(opath) == 0:
                    logger.exception("No signalk path specified for output")
                    raise ValueError
                logger.debug("opath = %s(%d)" % (opath, oformatted))

                if oformatted:
                    sk_add_delta(deltas,opath % xmlpaths[i]["name"], int(a.text))
                else:
                    sk_add_delta(deltas,opath, int(a.text))
            else:
#                logger.debug("xmlpaths = %s, i = %s, xmlpaths[i] = %s, name = %s" % (xmlpaths, i, xmlpaths[i], xmlpaths[i]["name"]))
                result[xmlpaths[i]["name"]] = int(a.text)
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
