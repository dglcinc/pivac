# Import Libraries
from w1thermsensor import W1ThermSensor, Unit
import os
import time
import logging

logger = logging.getLogger(__name__)

# Initialize the GPIO Pins
#os.system('modprobe w1-gpio')  # Turns on the GPIO module
#os.system('modprobe w1-therm') # Turns on the Temperature module

DEG_FAHRENHEIT = 0
DEG_CELSIUS = 1
DEG_KELVIN = 2

# returns a jSON object containing the current values of all 28* one-wire devices on the bus
#
# The bus is re-scanned at the top of every status() cycle rather than only at import.
# The kernel's w1 bus takes a few seconds to enumerate the DS18B20s after a (cold) boot,
# but the systemd service starts immediately — so an import-time-only scan caught an empty
# (or partial) bus and cached it forever, leaving the service "active" but silently
# publishing nothing until a manual restart. This recurred on essentially every power
# cycle. Re-scanning each cycle makes the module self-healing: a bus that isn't ready at
# boot — or a sensor that drops off and returns mid-run — recovers on its own within one
# daemon cycle, no restart needed. The scan is just a /sys/bus/w1/devices/ directory read,
# so it's cheap at the daemon cadence.
sensors = []
_last_sensor_count = -1

def _scan_sensors():
    global sensors, _last_sensor_count
    try:
        found = W1ThermSensor.get_available_sensors()
    except Exception as e:
        # Keep the last-known list if a scan blips (e.g. bus flaky mid-read); next
        # cycle re-scans. Better to retry against known sensors than to zero the list.
        logger.warning("OneWireTherm bus scan failed (%s); keeping %d known sensor(s)"
                       % (type(e).__name__, len(sensors)))
        return sensors
    sensors = found
    if len(sensors) != _last_sensor_count:
        logger.warning("OneWireTherm bus now has %d sensor(s)" % len(sensors))
        _last_sensor_count = len(sensors)
    return sensors

# initial scan at import (may legitimately be empty right after a cold boot; status()
# re-scans each cycle and picks the sensors up as soon as the bus enumerates them)
_scan_sensors()
logger.debug("Available sensors: " + str(sensors))

def available_sensors():
    return sensors

# Per-sensor calibration offset, added to the raw reading.
#
# The offset is expressed in KELVIN, which as a *difference* is identical to degrees
# Celsius, so one config value stays correct whatever `scale` says: Signal K output is
# always read in Kelvin, and a Fahrenheit read scales the same offset by 1.8. Bench
# ice-point values for the PA1-PA5 loop probes are in docs/ds18b20-PA1-5-calibration.md.
#
# This exists because the secondary-loop measurement is a *difference* of a few degrees.
# A DS18B20's absolute spec is +/-0.5 C, and the ten bench-calibrated probes spread 1.4 F
# — larger than the loop delta-T being measured, so an uncalibrated pair reports the
# sensor spread rather than the loop.
def _apply_offset(temp, offset_k, read_fahrenheit=False):
    if not offset_k:
        return temp
    return temp + (offset_k * 1.8 if read_fahrenheit else offset_k)

# send -1 for no rounding
def status(config = {}, output="default"):
    logger.debug("generating status")
    # Re-scan the bus each cycle so a boot-race empty enumeration (or a mid-run
    # sensor dropout/recovery) self-heals without a manual service restart.
    _scan_sensors()
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

        # Isolate each sensor: a transient SensorNotReadyError (or any per-sensor
        # failure) must not suppress the healthy sensors. Without this, one bad
        # DS18B20 takes down all temperatures for the whole cycle (the exception
        # bubbles to pivac-provider.py's module-level catch). Same isolation
        # pattern as RedLink._refresh_one.
        try:
            # read the sensor and prep for output (both types)
            temp_type = DEG_FAHRENHEIT
            temps = { "fahrenheit": DEG_FAHRENHEIT, "celsius": DEG_CELSIUS, "kelvin": DEG_KELVIN }
            if "scale" in dnames[sensor.id] and config["scale"] in temps:
                temp_type = temps[dnames[sensor.id]["scale"]]

            if output == "signalk" or temp_type == DEG_KELVIN:
                thermtemp = sensor.get_temperature(Unit.KELVIN)
            elif temp_type == DEG_CELSIUS:
                thermtemp = sensor.get_temperature(Unit.DEGREES_C)
            else:
                thermtemp = sensor.get_temperature(Unit.DEGREES_F)
            logger.debug("Temp for %s is: %f" % (sensor.id, thermtemp))

            offset_k = dnames[sensor.id].get("offset", 0)
            if offset_k:
                read_fahrenheit = (output != "signalk" and temp_type == DEG_FAHRENHEIT)
                thermtemp = _apply_offset(thermtemp, offset_k, read_fahrenheit)
                logger.debug("Offset %+.3f K applied to %s" % (offset_k, sensor.id))

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
        except Exception as e:
            logger.warning("OneWireTherm sensor %s read failed (%s); skipping this cycle"
                           % (sensor.id, type(e).__name__))
            continue

    if output == "signalk":
        logger.debug(deltas)
        return deltas
    else:
        logger.debug(result)
        return result
