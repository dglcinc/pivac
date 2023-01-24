# Import Libraries
import os
import errno
import time
import logging
import string

logger = logging.getLogger(__name__)

try:
    import RPi.GPIO as GPIO
except:
    logger.exception("Error importing RPi.GPIO! Try again using sudo.")
    raise OSError

# Initialize the GPIO Pins
os.system('modprobe w1-gpio')  # Turns on the GPIO module

# set up pins - index to pin numbering in relays lists
pins_initted = False

def init_pins(input_pins={}, pinmode = GPIO.BCM):
    logger.debug("Initializing pins")

    try:
        GPIO.setmode(pinmode)
        pm = pinmode
        logger.debug("Pin mode is %d" % pinmode)
    except:
        logger.exception("unknown board mode")
        raise ValueError

    chan_list = []
    logger.debug("pin list is %s" % input_pins)

    chan_list = input_pins.keys()
    logger.debug("Chan list is: %s" % chan_list)

    for i in chan_list:
        pullmode = GPIO.PUD_DOWN
        if input_pins[i]["pullmode"] == "pullup":
            pullmode = GPIO.PUD_UP
        GPIO.setup(i, GPIO.IN, pullmode)
    pins_initted = True

    return

def status(config={},output="default"):
    result = {}
    deltas = {}
    if "inputs" in config:
        if not pins_initted:
            pinmode = GPIO.BCM
            if "numbering" in config and config["numbering"] == "board":
                    pinmode = GPIO.BOARD
            init_pins(config["inputs"],pinmode)

        if output == "signalk":
            logger.debug("formatting signalk output...")
            from pivac import sk_init_deltas, sk_add_value, sk_add_source
            deltas = sk_init_deltas()
            sk_source = sk_add_source(deltas)

        for pinnum, pindict in config["inputs"].iteritems():
            logger.debug("pin = %s, pindict = %s" % (pinnum, pindict))
            presult = GPIO.input(pinnum) == (pindict["pullmode"] == "pulldown")
            if output == "signalk":
                if pindict["sk_literal"] == False:
                    sk_add_value(sk_source, "%s.%s.state" % (pindict["sk_path"], pindict["outname"]), presult)
                    sk_add_value(sk_source, "%s.%s.statenum" % (pindict["sk_path"], pindict["outname"]), int(presult))
                else:
                    sk_add_value(sk_source, "%s.name" % config["sk_path"], pindict["outname"])
                    sk_add_value(sk_source, "%s.state" % config["sk_path"], presult)
                    sk_add_value(sk_source, "%s.statenum" % config["sk_path"], int(presult))
            else:
                result[pindict["outname"]] = presult
    else:
        logger.exception("No input pins specified for GPIO")
        raise KeyError

    if output == "signalk":
        return deltas
    else:
        return result
