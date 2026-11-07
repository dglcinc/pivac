# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
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
                pconfig["packages"] = yaml.load(fp.read(), Loader=yaml.FullLoader)
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
        raise ValueError
    
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


def offset_at(offsets, kelvin):
    """A probe's calibration offset in Kelvin at the temperature it is reading.

    `offsets` is either a number (one offset for every temperature) or a mapping of
    temperature in degrees F to offset in Kelvin, as the bench records state them:
    `{45: 0.653, 140: 0.346}` for a loop probe, `{55: 3.382, 115: 3.556}` for a coil
    probe. A DS18B20's error is a line in temperature, which is why every multi-point
    calibration gives one offset per operating point, so between two points the
    offset is interpolated on the reading and beyond the last point the end segment
    is extended. One point is a constant. None, "" and 0 mean no correction."""
    if offsets in (None, "", 0, 0.0):
        return 0.0
    if not isinstance(offsets, dict):
        return float(offsets)
    pts = sorted((float(t), float(k)) for t, k in offsets.items())
    if len(pts) == 1:
        return pts[0][1]
    f = (kelvin - 273.15) * 9.0 / 5.0 + 32.0
    if f <= pts[0][0]:
        (t0, k0), (t1, k1) = pts[0], pts[1]
    elif f >= pts[-1][0]:
        (t0, k0), (t1, k1) = pts[-2], pts[-1]
    else:
        i = next(i for i in range(1, len(pts)) if f < pts[i][0])
        (t0, k0), (t1, k1) = pts[i - 1], pts[i]
    return k0 + (k1 - k0) * (f - t0) / (t1 - t0)
