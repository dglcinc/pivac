import mechanize
import urllib2 
import cookielib
import time
import logging
from bs4 import BeautifulSoup
import json
import re

logger = logging.getLogger(__name__)

# maintain session after site is loaded as module-level globals
site_ready = False
logged_in = False
retrying = 0
retry_count = 5
locationId = ""
locationId_prog = re.compile("GetZoneListData\?locationId=([0-9][0-9]*)&")
statsId_prog = re.compile("data-id=\"([0-9][0-9]*)\"")
statsData_prog = re.compile("Control.Model.set\(Control.Model.Property.([A-Za-z0-9]+), *([A-Za-z0-9.]+)\)")
conciseStatData_prog = re.compile("Control.Model.set\(Control.Model.Property.(outdoorHumidity), *([A-Za-z0-9.]+)\)")
statname_prog = re.compile("ZoneName.*>([A-Za-z0-9 ]+) Control<")
status_prog = re.compile("id=\"eqStatus([A-Za-z]+)\" *class=\"\">")
status_map = {
    "FanOn": "fan",
    "Heating": "heat",
    "Cooling": "cool",
    "off": "off"
}
HOMEPAGE = "https://www.mytotalconnectcomfort.com/portal"

try:
    cj = cookielib.CookieJar()
    br = mechanize.Browser()
    br.set_cookiejar(cj)
    site_ready = True

except:
    logger.exception("Error prepping Redlink scrape")

def status(config={}, output="default"):
    global site_ready, logged_in, retrying, retry_count
    global locationId, locationId_prog
    global statsId_prog, statsData_prog, status_prog
    global cj, br

    result = {}

    if "website" in config:
        homepage = config["website"]
    else:
        homepage = HOMEPAGE

    if not "uid" in config or not "pwd" in config:
        logger.error("Credentials not specified in config file.")
        raise ValueError

    # log in to mytotalconnectcomfort.com
    # NOTE: this code currently only works if you only have one location defined...
    if site_ready:
        stats_page = ""
        try:
            if logged_in == False:
                logger.debug("Not logged in; logging in...")
                response = br.open(homepage)

                # sometimes we get an exception but still logged in...
                stats_page = response.read()
                if locationId_prog.findall(stats_page):
                    logger.debug("Already logged in %s" % locationId)
                    logged_in == True
                else:
                    logger.debug("filling login form...")
                    try:
                        br.select_form(nr=0)
                    except:
                        # try retsetting Mechanize
                        logger.exception("form error on: %s" % hp.read())
                        br = mechanize.Browser()
                        cj = cookielib.CookieJar()
                        br.set_cookiejar(cj)
                        br.open(homepage)
                        br.select_form(nr=0)
                    br.form['UserName'] = config["uid"]
                    br.form['Password'] = config["pwd"]
                    response = br.submit()
                    stats_page = response.read()
                logger.debug("done logging in")
                list = locationId_prog.findall(stats_page)
                logger.debug("loclist= %s" % list)
                locationId = list[0]
                logger.debug("locationId=%s" % locationId)
                logged_in = True
            else:
                refresh_link = homepage
                logger.debug("Refresh link = %s" % refresh_link)
                response = br.open(refresh_link)
                stats_page = response.read()
#            logger.debug("Stats page = %s" % stats_page)
        except:    
            logger.exception("Error scraping MyTotalConnectComfort.com")
            logger.debug("Failed on page: %s" % stats_page)
            logged_in = False
            
            # recurse
            if retrying < retry_count:
                retrying += 1
                result = status(config,output)
            else:
                # reset for next time
                retrying = 0
            return result

    # on first success, reset retry loop
    retrying = 0

    if output == "signalk":
        logger.debug("Composing signalk output...")
        from pivac import sk_init_deltas, sk_add_source, sk_add_value
        deltas = sk_init_deltas()
        sk_source = sk_add_source(deltas)
        statenums = {
            "heat": 1,
            "cool": -1,
            "fan": 0.5,
            "off": 0
        }
    verbose = False
    if "verbose" in config:
        verbose = config["verbose"]

    if verbose == True:
        logger.debug("Verbose mode...")
        # get stat list out of the home page
        stats_list = statsId_prog.findall(stats_page) 
        logger.debug("Stats list = %s" % stats_list)
    
        try:
            for s in stats_list:
                linktext = "/portal/Device/Control/%s?page=1" % s
    #            logger.debug("link text = %s" % linktext)
                link = br.find_link(url=linktext)
                response = br.follow_link(link)
                stattext = response.read()
                statdata = statsData_prog.findall(stattext)
                statname = statname_prog.findall(stattext)
                stat = status_prog.findall(stattext)
                sname = statname[0]
                sstat = "off"
                if stat != []:
                    sstat = stat[0]
                sdict = dict(statdata)
                if output == "signalk":
                    fname = re.sub(r"[\s+]", '_', sname)
                    sk_add_value(sk_source, "%s.%s.temperature" % (config["inputs"]["thermostat"]["sk_path"], fname), int(float(sdict["dispTemperature"])))
                    sk_add_value(sk_source, "%s.%s.humidity" % (config["inputs"]["thermostat"]["sk_path"], fname), int(float(sdict["indoorHumidity"])))
                    sk_add_value(sk_source, "%s.%s.state" % (config["inputs"]["thermostat"]["sk_path"], fname), status_map[sstat])
                    sk_add_value(sk_source, "%s.%s.statenum" % (config["inputs"]["thermostat"]["sk_path"], fname), statenums[status_map[sstat]])
                    sk_add_value(sk_source, "%s.%s.heatset" % (config["inputs"]["thermostat"]["sk_path"], fname), int(float(sdict["heatSetpoint"])))
                    sk_add_value(sk_source, "%s.%s.coolset" % (config["inputs"]["thermostat"]["sk_path"], fname), int(float(sdict["coolSetpoint"])))
                    sk_add_value(sk_source, "%s.%s.humidity" % (config["inputs"]["outdoor_sensor"]["sk_path"], fname), int(float(sdict["outdoorHumidity"])))
                else:
                    result[s] = {
                        "name": sname,
                        "temp": float(sdict["dispTemperature"]),
                        "hum": float(sdict["indoorHumidity"]),
                        "status": status_map[sstat],
                        "heatset": int(float(sdict["heatSetpoint"])),
                        "coolset": int(float(sdict["coolSetpoint"])),
                        "rawdata": sdict
                    }
                    # there is no way to get this from the outdoor sensor so it is set by every stat...
                    result["outhum"] = float(sdict["outdoorHumidity"])
    
    #            logger.debug("stat = %s %s %s" % (sname, sstat, sdict))
                br.open(homepage)
        except:
            # too tricky to handle retries, just come back next time
            logger.exception("Error scraping stat page")
    else:
        logger.debug("concise mode")
        soup = BeautifulSoup(stats_page, "lxml")
        laststat = ""
        for e in soup.find_all("tr", "gray-capsule pointerCursor"):
#            logger.debug(str(e))
            stat = {}
            stat["status"] = "off"

            for f in e.find_all():
                if f.has_attr("class"):
                    if f["class"] == ["location-name"]:
                        stat["name"] = f.string
                    if f["class"] == ["hum-num"]:
                        tstr = re.findall("[0-9]+", f.string)
                        if len(tstr) > 0:
                            stat["hum"] = int(tstr[0])
                        else:
                            stat["hum"] = 0
                    if f["class"] == ["tempValue"]:
                        tstr = re.findall("[0-9]+", f.string)
                        if len(tstr) > 0:
                            stat["temp"] = int(tstr[0])
                        else:
                            stat["temp"] = 0
                    if "coolIcon" in f["class"] and f["style"] == "":
                        stat["status"] = "cool"
                    if "heatIcon" in f["class"] and f["style"] == "":
                        stat["status"] = "heat"
                    if "fanOnIcon" in f["class"] and f["style"] == "":
                        stat["status"] = "fan"
            if output == "signalk":
                fname = re.sub(r"[\s+]", '_', stat["name"])
                sk_add_value(sk_source, "%s.%s.temperature" % (config["inputs"]["thermostat"]["sk_path"], fname), stat["temp"])
                sk_add_value(sk_source, "%s.%s.humidity" % (config["inputs"]["thermostat"]["sk_path"], fname), stat["hum"])
                sk_add_value(sk_source, "%s.%s.redlinkid" % (config["inputs"]["thermostat"]["sk_path"], fname), e["data-id"])
                sk_add_value(sk_source, "%s.%s.state" % (config["inputs"]["thermostat"]["sk_path"], fname), stat["status"])
                sk_add_value(sk_source, "%s.%s.statenum" % (config["inputs"]["thermostat"]["sk_path"], fname), statenums[stat["status"]])
            else:
                result[e["data-id"]] = stat
            laststat = e["data-id"]
        try:
            logger.debug("getting outdoor humidity")
            linktext = "/portal/Device/Control/%s?page=1" % laststat
#            logger.debug("link text = %s" % linktext)
            link = br.find_link(url=linktext)
            response = br.follow_link(link)
            stattext = response.read()
            statdata = conciseStatData_prog.findall(stattext)
            sdict = dict(statdata)

            result["outhum"] = float(sdict["outdoorHumidity"])
        except:
            # too tricky to handle retries, just come back next time
            logger.exception("Error scraping stat page")

    if output == "signalk":
        return deltas
    else:
        return result
