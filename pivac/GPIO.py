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
MODE_BCM = 0
MODE_BOARD = 1
pm = MODE_BCM # gets initialized below

# Relay names/numbering [ name, bcm, board ]
R = {
    "ZV" : [17, 11],
    "DHW" : [27, 13],
    "BLR" : [22, 15],
    "RCHL" :[5, 29],
    "LCHL" : [6, 31],
    "Y2ON" : [13, 33],
    "YOFF" : [26, 37],
    "Y2FAN" : [16, 36],
    "DEHUM" : [12, 32]
}

def init_pins(pinmode = GPIO.BCM):
    logger.debug("Initializing pins")
    GPIO.setmode(pinmode)
    if pinmode == GPIO.BCM:
        pm = MODE_BCM
    elif pinmode == GPIO.BOARD:
        pm = MODE_BOARD
    else:
        logger.exception("unknown board mode")
        raise ValueError

    chan_list = []
    logger.debug("R is " + str(R))
    for r in R.keys():
        logger.debug("r is " + str(r))
        logger.debug("R[r][pm] is " + str(R[r][pm]))
        chan_list.append(R[r][pm])
    logger.debug("Chan list is: " + str(chan_list))
    GPIO.setup(chan_list, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    return

# initialize the pins
init_pins()

def status():
    result = {}
    for r in R.keys():
        result[r] = GPIO.input(R[r][pm]) == 0

    return result
