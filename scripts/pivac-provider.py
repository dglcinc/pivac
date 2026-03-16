#!/home/pi/pivac-venv/bin/python3
import logging
logger = logging.getLogger(__name__)
import sys
import argparse
import json
import time
import importlib
import os
import urllib.request
import websocket

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
# skip the reserved "pivac_config" key which holds framework settings
pkglist = []
for k in packages.keys():
    if k == "pivac_config":
        continue
    if not k.startswith("pivac."):
        logger.warning("Config key '%s' does not start with 'pivac.' — skipping (not a pivac module)" % k)
        continue
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
parser.add_argument("--daemon", nargs="?", default=0, type=int, help="run forever in a while loop; sleeptime is set in %s; if more than one input module default is used" % config["sourcefile"])
args = parser.parse_args()
logging.debug("Arguments = %s" % args)

# Remove all handlers associated with the root logger object, to set final format and log level
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(format='%(name)s %(levelname)s:%(asctime)s %(message)s',datefmt='%m/%d/%Y %I:%M:%S',level=args.loglevel)
logger = logging.getLogger(__name__)
logger.debug("Arguments = %s" % args)

loopcount = args.daemon
if args.daemon == None:
    loopcount = -1
logger.debug("Loopcount = %d", loopcount)

# load referenced packages (loading here since below is in while loop)
# If a config section has a 'module:' key, use that as the import path instead of
# the config key name — allowing multiple config sections to share one implementation.
modfuncs = {}
for p in args.stype:
    try:
        module_name = packages[p].get("module", p)
        logger.debug("Loading module %s (implementation: %s)" % (p, module_name))
        statmod = importlib.import_module(module_name)
        statfn = getattr(statmod, "status")
        modfuncs[p] = statfn
    except ImportError as e:
        logger.error("Module %s not found: %s" % (module_name, e))
        sys.exit(1)
    except AttributeError:
        logger.error("Module %s does not implement a status() function" % module_name)
        sys.exit(1)

# SignalK WebSocket connection helpers
sk_config = packages.get("pivac_config", {}).get("signalk", {})

def get_sk_token(sk_cfg):
    """Fetch a JWT token from the SignalK auth endpoint."""
    url = "http://%s:%d/signalk/v1/auth/login" % (sk_cfg["host"], sk_cfg["port"])
    data = json.dumps({"username": sk_cfg["username"], "password": sk_cfg["password"]}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read())
    return result["token"]

def connect_sk_ws(sk_cfg, token):
    """Open a WebSocket connection to the SignalK stream endpoint."""
    ws_url = "ws://%s:%d/signalk/v1/stream?subscribe=none&token=%s" % (
        sk_cfg["host"], sk_cfg["port"], token)
    ws = websocket.WebSocket()
    ws.connect(ws_url)
    logger.info("Connected to SignalK WebSocket at %s:%d" % (sk_cfg["host"], sk_cfg["port"]))
    return ws

def reconnect_sk_ws(sk_cfg, current_ws):
    """Close existing WebSocket (if any) and reconnect with a fresh token."""
    if current_ws:
        try:
            current_ws.close()
        except:
            pass
    for attempt in range(6):
        wait = min(2 ** attempt, 60)
        logger.warning("SignalK WebSocket reconnect attempt %d (waiting %ds)..." % (attempt + 1, wait))
        time.sleep(wait)
        try:
            token = get_sk_token(sk_cfg)
            ws = connect_sk_ws(sk_cfg, token)
            return ws
        except Exception as e:
            logger.warning("Reconnect attempt %d failed: %s" % (attempt + 1, e))
    logger.error("All SignalK reconnect attempts failed.")
    return None

# Establish initial SignalK WebSocket connection (with retries to handle boot race)
ws = None
if sk_config:
    ws = reconnect_sk_ws(sk_config, None)
else:
    logger.warning("No 'pivac_config.signalk' section in config — falling back to stdout output.")
ws_connected_at = time.time() if ws else 0
last_ping_time = time.time() if ws else 0
PING_INTERVAL = 45      # seconds between keepalive pings
MAX_CONNECTION_AGE = 43200  # 12 hours; force reconnect for token refresh

sleepytime = -1
packages = config["packages"]

while 1:
    if sk_config and ws:
        now = time.time()
        if (now - ws_connected_at) > MAX_CONNECTION_AGE:
            logger.info("Forcing WebSocket reconnect for token refresh (>12h)")
            ws = reconnect_sk_ws(sk_config, ws)
            if ws:
                ws_connected_at = now
                last_ping_time = now
        elif (now - last_ping_time) >= PING_INTERVAL:
            try:
                ws.ping()
                last_ping_time = now
            except Exception as e:
                logger.warning("WebSocket ping failed, reconnecting: %s" % e)
                ws = reconnect_sk_ws(sk_config, ws)
                if ws:
                    ws_connected_at = now
                    last_ping_time = now

    for p in args.stype:
        data = None
        try:
            logger.debug("calling status for %s (%s)" % (p, packages[p]))
            data = modfuncs[p](packages[p], "signalk")
            logger.debug("%s returned %s" % (p, data))
        except:
            logger.exception("Error getting data from module %s" % p)

        if data is not None:
            payload = json.dumps(data)
            if sk_config and (not ws or not ws.connected):
                # SignalK is configured but connection is down — try to reconnect
                logger.warning("SignalK WebSocket is down, attempting to reconnect...")
                ws = reconnect_sk_ws(sk_config, ws)
                if ws:
                    ws_connected_at = time.time()
                    last_ping_time = time.time()
            if ws:
                try:
                    ws.send(payload)
                except Exception as e:
                    logger.warning("WebSocket send failed: %s" % e)
                    ws = reconnect_sk_ws(sk_config, ws)
                    if ws:
                        ws_connected_at = time.time()
                        last_ping_time = time.time()
                        try:
                            ws.send(payload)
                        except Exception as e2:
                            logger.error("Send failed after reconnect: %s" % e2)
                            ws = None
            else:
                # No WebSocket configured or all reconnects failed — fall back to stdout
                print(payload)
                sys.stdout.flush()

    if loopcount != 0:
        if sleepytime < 0:
            sleepytime = 0.5
            if len(args.stype) == 1:
                if "daemon_sleep" in packages[args.stype[0]]:
                    sleepytime = packages[args.stype[0]]["daemon_sleep"]
        logger.debug("sleepytime = %f" % sleepytime)
        time.sleep(sleepytime)
        if loopcount > 0:
            loopcount = loopcount - 1
    if loopcount == 0:
        sys.exit()
