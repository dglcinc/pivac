# Import Libraries
from w1thermsensor import W1ThermSensor
import os
import time
import logging

logger = logging.getLogger(__name__)

# Initialize the GPIO Pins
os.system('modprobe w1-gpio')  # Turns on the GPIO module
os.system('modprobe w1-therm') # Turns on the Temperature module

DEG_FAHRENHEIT = 0
DEG_CELSIUS = 1
DEG_KELVIN = 2

# returns a jSON object containing the current values of all 28* one-wire devices on the bus
# sensors are scanned on module load for performance; if your bus changes frequently you can move into status()
sensors = W1ThermSensor.get_available_sensors()
logger.debug("Available sensors: " + str(sensors))

def available_sensors():
    return sensors

# send -1 for no rounding
def status(config = {}, output="default"):
    logger.debug("generating status")
    result = {}
    dnames = {}

    if "rounding" in config:
        round_digits = config["rounding"]

    # not an error if no sensors specified, you just won't get pretty names
    if "sensors" in config:
        dnames = config["sensors"]

    # prep for signalk output
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

    for sensor in sensors:
        temp = 0
        sname = ""

        # read the sensor and prep for output (both types)
        temp_type = DEG_FAHRENHEIT
        temps = { "fahrenheit": DEG_FAHRENHEIT, "celsius": DEG_CELSIUS, "kelvin": DEG_KELVIN }
        if "scale" in config and config["scale"] in temps:
            temp_type = temps[config["scale"]]

        if temp_type == DEG_CELSIUS:
            thermtemp = sensor.get_temperature(W1ThermSensor.DEGREES_C)
        elif temp_type == DEG_KELVIN:
            thermtemp = sensor.get_temperature(W1ThermSensor.KELVIN)
        else:
            thermtemp = sensor.get_temperature(W1ThermSensor.DEGREES_F)
        logger.debug("Temp for %s is: %f" % (sensor.id, thermtemp))

        if sensor.id in dnames and "name" in dnames[sensor.id]:
            sname = dnames[sensor.id]["name"]
        else:
            # this will add a new member to the dict with the name of the sensor
            sname = sensor.id

        if round_digits == 0:
            result[sname] = int(round(thermtemp,0))
        elif round_digits > 0:
            result[sname] = round(thermtemp,round_digits)
        else:
            result[sname] = thermtemp

        if output == "signalk":
            kpath = ""
            kformatted = False
            
            # if there is config for this sensor, get it
            if sensor.id in dnames:
                if "sk_formatted" in dnames[sensor.id]:
                    kformatted = True
                    kpath = dnames[sensor.id]["sk_formatted"]
                elif "sk_literal" in dnames[sensor.id]:
                    kpath = dnames[sensor.id]["sk_literal"]
            logger.debug("kpath = %s(%d) - sensor %s, name %s" % (kpath, kformatted, sensor.id, sname))

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

            # output delta
            if oformatted:
                sk_add_delta(deltas, opath % sname, result[sname])
            else:
                sk_add_delta(deltas, opath, result[sname])

    if output == "signalk":
        logger.debug(deltas)
        return deltas
    else:
        logger.debug(result)
        return result
