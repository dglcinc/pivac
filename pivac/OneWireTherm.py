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

    # not an error if no sensors specified, you just won't get pretty names
    if "inputs" in config:
        dnames = config["inputs"]
    for s in sensors:
        if s.id not in dnames:
            dnames[s.id] = {}
    from pivac import propagate_defaults
    logger.debug("before prop: %s" % dnames)
    propagate_defaults(config, dnames, config["propagate"])
    logger.debug("after prop: %s" % dnames)

    # prep for signalk output
    if output == "signalk":
        logger.debug("prepping sk output...")
        from pivac import sk_init_deltas, sk_add_source, sk_add_value
        deltas = sk_init_deltas()
        sk_source = sk_add_source(deltas)

    logger.debug("sensors = %s" % sensors)
    for sensor in sensors:
        temp = 0
        sname = ""

        # read the sensor and prep for output (both types)
        temp_type = DEG_FAHRENHEIT
        temps = { "fahrenheit": DEG_FAHRENHEIT, "celsius": DEG_CELSIUS, "kelvin": DEG_KELVIN }
        if "scale" in dnames[sensor.id] and config["scale"] in temps:
            temp_type = temps[dnames[sensor.id]["scale"]]

        if output == "signalk" or temp_type == DEG_KELVIN:
            thermtemp = sensor.get_temperature(W1ThermSensor.KELVIN)
        elif temp_type == DEG_CELSIUS:
            thermtemp = sensor.get_temperature(W1ThermSensor.DEGREES_C)
        else:
            thermtemp = sensor.get_temperature(W1ThermSensor.DEGREES_F)
        logger.debug("Temp for %s is: %f" % (sensor.id, thermtemp))

        if sensor.id in dnames and "outname" in dnames[sensor.id]:
            sname = dnames[sensor.id]["outname"]
        else:
            # this will add a new member to the dict with the name of the sensor
            sname = sensor.id

        round_digits = dnames[sensor.id]["rounding"]
        if round_digits == 0:
            result[sname] = int(round(thermtemp,0))
        elif round_digits > 0:
            result[sname] = round(thermtemp,round_digits)
        else:
            result[sname] = thermtemp
        if output == "signalk":
            # output delta
            if not dnames[sensor.id]["sk_literal"]:
                sk_add_value(sk_source, "%s.%s.temperature" % (dnames[sensor.id]["sk_path"], sname), result[sname])
            else:
                sk_add_value(sk_source, "%s.temperature" % dnames[sensor.id]["sk_path"], result[sname])

    if output == "signalk":
        logger.debug(deltas)
        return deltas
    else:
        logger.debug(result)
        return result
