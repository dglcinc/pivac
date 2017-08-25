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

def init_pins(input_pins={}, pullmode=GPIO.PUD_UP, pinmode = GPIO.BCM):
    logger.debug("Initializing pins")

    try:
        GPIO.setmode(pinmode)
        pm = pinmode
    except:
        logger.exception("unknown board mode")
        raise ValueError

    chan_list = []
    logger.debug("pin list is %s" % input_pins)
    for r in input_pins.keys():
        logger.debug("pin is %s(%d)" % (r,input_pins[r]["pin"]))
        chan_list.append(input_pins[r]["pin"])
    logger.debug("Chan list is: %s" % chan_list)
    GPIO.setup(chan_list, GPIO.IN, pull_up_down=pullmode)
    pins_initted = True

    return

def status(config={},output_type="default"):
    result = {}
    if "input_pins" in config:
        if not pins_initted:
            if "numbering" in config:
                pinmode = GPIO.BCM
                if config["numbering"] == "board":
                    pinmode = GPIO.BOARD
            pullmode = GPIO.PUD_UP
            if "pullmode" in config:
                if config["pullmode"] == "pulldown":
                    pullmode = GPIO.PUD_DOWN
            init_pins(config["input_pins"],pullmode,pinmode)

        for pin in config["input_pins"].keys():
            result[pin] = GPIO.input(config["input_pins"][pin]["pin"]) == 0
    else:
        logger.exception("No input pins specified for GPIO")
        raise KeyError

    if output_type == "signalk":
        logger.debug("formatting signalk output...")
        from pivac import sk_init_deltas, sk_add_delta
        deltas = sk_init_deltas()

        for p in config["input_pins"]:
            logger.debug("p = %s" % p)

        if "sk_formatted" in config:
            logger.debug("formatted output")
            for r in result.keys():
                sk_add_delta(deltas, "%s.state" % (config["sk_formatted"] % r), result[r])
                sk_add_delta(deltas, "%s.statenum" % (config["sk_formatted"] % r), int(result[r]))
        elif "sk_literal" in config:
            logger.debug("literal output")
            for r in result.keys():
                sk_add_delta(deltas, "%s.name" % config["sk_literal"], r)
                sk_add_delta(deltas, "%s.state" % config["sk_literal"], result[r])
                sk_add_delta(deltas, "%s.statenum" % config["sk_literal"], int(result[r]))
        return deltas
    else:
        return result
