import logging
logger = logging.getLogger(__name__)
import sys
import argparse
import json
import socket
import time
import pytemperature as pt
import re
import pkgutil
from pydoc import safeimport
import os

# set logging temporarily before args parsing
loglevel = os.getenv("LOG_CFG", "ERROR")
logger = logging.getLogger(__name__)
logging.basicConfig(level=loglevel)

# load pivac; it may be installed globally or running from a github clone...
try:
    spath = os.path.abspath(os.path.dirname(__file__))
    sys.path.append("%s/.." % spath)
    logger.debug("curdir: %s, path: %s" % (spath, sys.path))
    import pivac
except:
    logger.exception("pivac package not in python path; trying safeimport.")

#load config from config file
cfgfile = os.getenv("PIVAC_CFG", "")
config = pivac.set_config(cfgfile)
packages = config["packages"]

# get list of modules in pivac that implement status()
pkglist = []
for k in packages.keys():
    if "enabled" not in packages[k] or packages[k]["enabled"]:
        pkglist.append(k)
logger.debug("Pivac Packagelist = %s" % pkglist)
logger.debug("config = %s" % config)

# handle arguments
argdesc=""
for i in pkglist:
    desc = "[no description]"
    if "description" in packages[i]:
        desc = packages[i]["description"]
    argdesc = argdesc + "%s: %s\n" % (i, desc)

parser = argparse.ArgumentParser(description=argdesc, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("stype", nargs="+", choices=pkglist, help="Specify source module(s) for JSON data (from %s); recommend one per invocation due to differing module processing times" % config["sourcefile"])
parser.add_argument("--loglevel", choices=["DEBUG", "WARNING", "INFO", "ERROR", "CRITICAL"], default="ERROR", help="set logger debug level; default is ERROR")
parser.add_argument("--output", choices=["default","signalk"], default="default", help="specify format of JSON written to stdout; default is 'default'")
parser.add_argument("--format", choices=["compact","pretty"], default="compact", help="specify whether output should be pretty-printed; default is 'compact'")
parser.add_argument("--daemon", action="store_true", default=False,  help="run forever in a while loop; sleeptime is set in %s; if more than one input module default is used" % config["sourcefile"])
args = parser.parse_args()
logging.debug("Arguments = %s" % args)
 
# Remove all handlers associated with the root logger object, to set final format and log level
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(format='%(name)s %(levelname)s:%(asctime)s %(message)s',datefmt='%m/%d/%Y %I:%M:%S',level=args.loglevel)

logging.debug("Arguments = %s" % args)

# load referenced packages (loading here since below is in while loop)
modfuncs = {}
for p in args.stype:
    try:
        logger.debug("Loading module %s" % p)
        statmod = safeimport(p)
        statfn = getattr(statmod, "status")
        modfuncs[p] = statfn
    except:
        logger.exception("Package %s in configfile %s not found or doesn't have status() function" % (p, config["sourcefile"]))
        sys.exit(1)

sleepytime = -1
packages = config["packages"]

while 1:
    data = ""
    for p in args.stype:
        try:
            logger.debug("calling status for %s (%s)" % (p, packages[p]))
            data = modfuncs[p](packages[p], args.output)
            logger.debug("%s returned %s" % (p, data))
        except:
            logger.exception("Error getting data from module %s" % p)
    
        if args.format == "pretty":
            print(json.dumps(data,indent=2))
            sys.stdout.flush()
        else:
            print(json.dumps(data))
            sys.stdout.flush()

    if args.daemon == True:
        if sleepytime < 0:
            sleepytime = 0.5
            if len(args.stype) == 1:
                if "daemon_sleep" in packages[args.stype[0]]:
                    sleepytime = packages[args.stype[0]]["daemon_sleep"]
        logger.debug("sleepytime = %f" % sleepytime)
        time.sleep(sleepytime)
    else:
        sys.exit()
