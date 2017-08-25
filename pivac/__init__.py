import time
import logging
import os
import yaml
import socket
import copy

CONFIG_FILE = "/etc/pivac/config.yml"
pconfig = {
}

deltas_template = {
    "updates": [
        {
            "source": {
                "label": "rpi:%s" % socket.gethostname()
            },
            "values": []
        }
    ]
}

def config(file=""):
    global pconfig
    logger = logging.getLogger(__name__)

    if pconfig:
        return pconfig
    path = ""
    try:
        logger.debug("loading config file...")
        # look in /etc/pivac
        if len(file):
            path = file

        elif os.access(CONFIG_FILE, os.R_OK):
            path = CONFIG_FILE

        # look in the parent of the module directory (in case user just cloned the git repository
        else:
            tpath = os.path.dirname(__file__)
            tpath = tpath + "/../config/config.yml"
            logger.debug("Checking tpath %s..." % tpath)
            if os.access(tpath,os.R_OK):
                logger.debug("setting path...")
                path = tpath
        
        logger.debug("loading config file...%s" % path)
        if len(path):
            with open(path,"r") as fp:
                pconfig["packages"] = yaml.load(fp.read())
                pconfig["sourcefile"] = path
                fp.close()
        else:
                # else print error
                logger.exception("Config file not specified or not accessible. You must call pivac.config(file) or edit /etc/pivac/config.yml.")
    except:
        logger.exception("Unable to load config file (%s)" % path )
    
    return pconfig

def sk_init_deltas():
    return copy.deepcopy(deltas_template)

def sk_add_delta(deltas, path, value):
    deltas["updates"][0]["values"].append({
        "path":  path,
        "value": value
    })
