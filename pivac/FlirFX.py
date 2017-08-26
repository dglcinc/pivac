import requests
import logging
import time
import json
import pytemperature

logger = logging.getLogger(__name__)

Cams = {}

def status(config={}, output="default"):
    result = {}

    if output == "signalk":
        logger.debug("prepping sk output...")
        from pivac import sk_init_deltas, sk_add_source, sk_add_value
        deltas = sk_init_deltas()

    cams = config["inputs"]
    for cam, camdict in cams.iteritems():
        logger.debug("iterating camera %s", cam)
        if output == "signalk":
            sk_source = sk_add_source(deltas,"flirfx:%s" % cam)

        try:
            # no session yet
            if "fake" in camdict and camdict["fake"] == True:
                temp_units = "F"
                temp_value = 68
                humidity_value = 49
            else:
                if cam not in Cams:
                    logger.debug("logging into camera...")
                    Cams[cam] = {}
                    r = requests.post('http://%s/API/1.0/ChiconyCameraLogin' % cam, data = '{ "password" : "%s" }' % camdict["pwd"] )
                    session = r.cookies['Session']
                    Cams[cam]["cookies"] = dict(Session=session)

                req = requests.post('http://%s/API/1.1/CameraStatus' % cam, cookies=cookies, data = '{ "getCameraStatus" : [ "humidity", "temperature"] }' )
                res = req.json()
                temp_units = res['temperature']['tempUnits']
                temp_value = res['temperature']['tempValue']
                humidity_value = res['humidity']['humidityLevel']

            if temp_units == 'F':
                temp_value = pytemperature.f2k(temp_value)
            elif temp_units == 'C':
                temp_value = pytemperature.c2k(temp_value)

            if output == "signalk":
                sk_add_value(sk_source, "%s.temperature" % camdict["sk_path"], temp_value)
                sk_add_value(sk_source, "%s.humidity" % camdict["sk_path"], humidity_value)
            else:
                if camdict["scale"] == "fahrenheit":
                    temp_value = pytemperature.k2f(temp_value)
                if camdict["scale"] == "celcius":
                    temp_value = pytemperature.k2c(temp_value)
                result[cam] = {}
                result[cam]["temperature"] = temp_value
                result[cam]["humidity"] = humidity_value
        except:
            logger.exception("error getting data from FLIR camera %s" % cam)

    if output == "signalk":
        return deltas
    else:
        return result
