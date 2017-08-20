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

dnames = {
    "0516a36332ff" : "IN",
    "0516a365d8ff" : "OUT",
    "0316a00f04ff" : "CRW",
    "0516a36816ff" : "AMB",
    "0316a015e7ff" : "Unassigned"
}

# returns a JSON object containing the current values of all 28* one-wire devices on the bus
sensors = W1ThermSensor.get_available_sensors()
logger.debug("Available sensors: " + str(sensors))

def available_sensors():
    return sensors

# send -1 for no rounding
def status(temp_type=DEG_FAHRENHEIT, round_digits=0):
    logger.debug("generating status")
    result = {}
    for sensor in sensors:
        temp = 0
        name = ""
        if temp_type == DEG_CELSIUS:
            thermtemp = sensor.get_temperature(W1ThermSensor.DEGREES_C)
        elif temp_type == DEG_KELVIN:
            thermtemp = sensor.get_temperature(W1ThermSensor.KELVIN)
        else:
            thermtemp = sensor.get_temperature(W1ThermSensor.DEGREES_F)
        logger.debug("Temp for: " + sensor.id + " is: " + str(thermtemp))
        try:
            name = dnames[sensor.id]
        except KeyError:
            name = sensor.id
        # this will add a new member to the dict with the name of the sensor
        if (round_digits >= 0):
            result[name] = int(round(thermtemp,round_digits))
        else:
            result[name] = thermtemp
    logger.debug(result)
    return result
