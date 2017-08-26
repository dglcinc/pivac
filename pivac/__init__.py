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
    "updates": []
}
source_template = {
    "source": {
        "label": "rpi:%s" % socket.gethostname()
    },
    "values": []
}

def get_config():
    return pconfig

def set_config(file=""):
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
                for p in pconfig["packages"].values():
                    logger.debug("checking propagations for %s" % p)
                    if "propagate" in p and "inputs" in p:
                        propagate_defaults(p, p["inputs"], p["propagate"])
        else:
                # else print error
                logger.exception("Config file not specified or not accessible. You must call pivac.config(file) or edit /etc/pivac/config.yml.")
    except:
        logger.exception("Unable to load config file (%s)" % path )
    
    return pconfig

def sk_init_deltas():
    return copy.deepcopy(deltas_template)

def sk_add_source(deltas,source=""):
    result = copy.deepcopy(source_template)
    if not len(source):
        source = "rpi:%s" % socket.gethostname()
    result["source"]["label"] = source
    deltas["updates"].append(result)

    return result

def sk_add_value(source, path, value):
    source["values"].append({
        "path":  path,
        "value": value
    })

def propagate_defaults(sourcedict, targetdict, keylist):
    logger = logging.getLogger(__name__)

    for keyname in keylist:
        defaultval = None
        if keyname in sourcedict:
            defaultval = sourcedict[keyname]

        for d in targetdict.keys():
            logger.debug("Propagating %s in %s" % (keyname,d))
            if keyname not in targetdict[d]:
                if defaultval == None:
                    logger.exception("Propagated default %s missing in source or target dicts" % keyname)
                    raise KeyError
                targetdict[d][keyname] = defaultval
        logger.debug("target(propagated)=%s" % targetdict)

    return
