import logging
import sys
import argparse
import json
import socket
import time
import pytemperature as pt
import re

# handle arguments
parser = argparse.ArgumentParser(description="Emit SignalK deltas for sensors and specialized data sources connected to a Raspberry Pi\n  1Wire: uses GPIO pin 4 (board pin 7) for data, with 4.7k ohm pullup to 3.3V\n  GPIO-IN: configures designated pins as INPUT_PULLUP\n  TED5000: scrapes real-time KWh usage from TED5000 MTUs\n  RedLink: scrapes thermostat info from designated mytotalconnectcomfort.com website and location", formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("stype", choices=["1Wire","GPIO", "TED5000", "RedLink"], help="Specify source of sensors to emit from")
parser.add_argument("lmode", nargs="?", choices=["DEBUG", "WARNING", "INFO", "ERROR", "CRITICAL"], default="WARNING", help="set logger debug level")
parser.add_argument("--daemon", action="store_true", default=False,  help="run forever in a while loop")
args = parser.parse_args()

logging.basicConfig(format='%(name)s %(levelname)s:%(asctime)s %(message)s',datefmt='%m/%d/%Y %I:%M:%S',level=args.lmode)

logger = logging.getLogger(__name__)

logging.debug(args)

while 1:
    deltas = {
        "updates": [
            {
                "source": {
                    "label": "rpi:%s" % socket.gethostname()
                },
                "values": []
            }
        ]
    }

    try:
        if args.stype == "1Wire":
            import pivac.OneWireTherm
            data = pivac.OneWireTherm.status(pivac.OneWireTherm.DEG_KELVIN)
            logger.debug(str(data))
    
            for d in data:
                logger.debug("value = %s" % str(d))
                if d == "AMB":
                    deltas["updates"][0]["values"].append({
                        "path":  "environment.outside.thermostat.temperature",
                        "value": data[d]
                    })
                else:
                    deltas["updates"][0]["values"].append({
                        "path":  "environment.inside.hvac.temperature.%s" % d,
                        "value": data[d]
                    })
    
        elif args.stype == "GPIO":
            import pivac.GPIO
            data = pivac.GPIO.status()
            logger.debug(str(data))
    
            for d in data:
                logger.debug("value = %s" % str(d))
                deltas["updates"][0]["values"].append({
                    "path": "electrical.ac.switch.utility.%s.state" % d,
                    "value": data[d]
                })
                deltas["updates"][0]["values"].append({
                    "path": "electrical.ac.switch.utility.%s.statenum" % d,
                    "value": int(data[d])

                })
    
        elif args.stype == "TED5000":
            import pivac.TED5000
            data = pivac.TED5000.status()
            logger.debug(str(data))
    
            for d in data:
                deltas["updates"][0]["values"].append({
                    "path": "electrical.ac.ted5000.%s.power" % d,
                    "value": data[d]
                })
    
        elif args.stype == "RedLink":
            import pivac.RedLink
            data = pivac.RedLink.status()
    #        logger.debug(str(data))
    
            if "outhum" in data:
                deltas["updates"][0]["values"].append({
                    "path": "environment.outside.thermostat.humidity",
                    "value": data["outhum"]
                })
            for d in data:
                if d == "outhum":
                    continue
                fname = re.sub(r"[\s+]", '_', data[d]["name"])
#                logger.debug("fname = %s" % fname)
                deltas["updates"][0]["values"].append({
                    "path": "environment.inside.thermostat.%s.temperature" % fname,
                    "value": pt.f2k(int(data[d]["temp"]))
                })
                deltas["updates"][0]["values"].append({
                    "path": "environment.inside.thermostat.%s.humidity" % fname,
                    "value": int(data[d]["hum"])
                })
                deltas["updates"][0]["values"].append({
                    "path": "environment.inside.thermostat.%s.redlinkid" % fname,
                    "value": d
                })
                deltas["updates"][0]["values"].append({
                    "path": "environment.inside.thermostat.%s.state" % fname,
                    "value": data[d]["status"]
                })
                statenums = {
                    "heat": 1,
                    "cool": -1,
                    "fan": 0.5,
                    "off": 0
                }
                deltas["updates"][0]["values"].append({
                    "path": "environment.inside.thermostat.%s.statenum" % fname,
                    "value": statenums[data[d]["status"]]
                })
    except:
        logger.exception("Unable to complete a deltas run due to exception.")

    # output deltas and decide whether to continue looping
    #logger.debug("Daemon mode = %i" % args.daemon)
    if args.daemon == True:
        print(json.dumps(deltas))
        sys.stdout.flush()
        sleepytime = 0.5
        if args.stype == "RedLink":
            sleepytime = 2.0
        time.sleep(sleepytime)
    else:
        print(json.dumps(deltas,indent=2))
        sys.exit()
