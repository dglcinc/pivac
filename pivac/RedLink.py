import mechanize
import urllib2 
import cookielib
import time
import logging
from bs4 import BeautifulSoup
import json
import re
import pytemperature

logger = logging.getLogger(__name__)

# maintain session after site is loaded as module-level globals
logged_in = False
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
cj = None
br = None

# prevent browser class from saving history
class NoHistory(object):
    def add(self, *a, **k): pass
    def clear(self): pass

def init_site():
    global cj, br
    global logged_in
    logged_in = False

    try:
        logger.debug("Initializing mechanize...")
        cj = cookielib.CookieJar()
        br = mechanize.Browser(history=NoHistory())
        br.set_cookiejar(cj)
        br.set_handle_equiv(True)
        br.set_handle_gzip(True)
        br.set_handle_redirect(True)
        br.set_handle_referer(True)
        br.set_handle_robots(False)
        br.addheaders = [('User-agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8'),
            ('Referer', 'https://www.mytotalconnectcomfort.com/portal/?timeout=True'),
            ('Connection', 'keep-alive'),
            ('Origin', 'https://www.mytotalconnectcomfort.com'),
            ('Accept-Language', 'en-us')]
        br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)
        if logger.getEffectiveLevel() == logging.DEBUG:
            # turn on mechanize debugging
            br.set_debug_http(True)
            br.set_debug_redirects(True)
            br.set_debug_responses(True)

            # disable ssl cert verification (to allow use of charles)
            import ssl
            try:
                _create_unverified_https_context = ssl._create_unverified_context
            except AttributeError:
                # Legacy Python that doesn't verify HTTPS certificates by default
                pass
            else:
                # Handle target environment that doesn't support HTTPS verification
                ssl._create_default_https_context = _create_unverified_https_context

    except:
        logger.exception("Error prepping Redlink scrape")
    return

init_site()

def status(config={}, output="default"):
    global logged_in
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
    stats_page = ""
    try:
        if logged_in == False:
            logger.debug("Not logged in; logging in...")
            response = br.open(homepage)

            # sometimes we get an exception but still logged in...
            stats_page = response.read()
            if locationId_prog.findall(stats_page):
                logger.debug("Already logged in %s" % locationId)
                logged_in = True
            else:
                logger.debug("filling login form...")
                try:
                    br.select_form(nr=0)
                except:
                    # try retsetting Mechanize
                    logger.exception("form error on: %s" % stats_page)
                    init_site()
                    br.open(homepage)
                    br.select_form(nr=0)
                br.form['UserName'] = config["uid"]
                br.form['Password'] = config["pwd"]
                response = br.submit()
                stats_page = response.read()
            logger.debug("done logging in")
            list = locationId_prog.findall(stats_page)
            logger.debug("loclist= %s" % list)
            if len(list):
                locationId = list[0]
            else:
                raise IOError
            logger.debug("locationId=%s" % locationId)
            logger.debug("Stats page = %s" % stats_page)
            logged_in = True
        else:
            refresh_link = homepage
            logger.debug("Refresh link = %s" % refresh_link)
            response = br.open(refresh_link)
            stats_page = response.read()
            logger.debug("Stats page = %s" % stats_page)
    except:    
        logger.exception("Error scraping MyTotalConnectComfort.com")
        logger.debug("Failed on page: %s" % stats_page)
        init_site()
        raise IOError

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
                br.click_link(link)
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

                if config["scale"] == "fahrenheit":
                    scale = "fahrenheit"
                    ktemp = pytemperature.f2k(float(sdict["dispTemperature"]))
                    if s in config["inputs"] and config["inputs"][s]["scale"] == "celsius":
                        scale = "celsius"
                        ktemp = pytemperature.c2k(float(sdict["dispTemperature"]))
                else:
                    scale = "celsius"
                    ktemp = pytemperature.c2k(sdict["dispTemperature"])
                    if s in config["inputs"] and config["inputs"][s]["scale"] == "fahrenheit":
                        scale = "fahrenheit"
                        ktemp = pytemperature.f2k(sdict["dispTemperature"])

                if output == "signalk":
                    fname = re.sub(r"[\s+]", '_', sname)
                    sk_add_value(sk_source, "%s.%s.temperature" % (config["inputs"]["thermostat"]["sk_path"], fname), int(ktemp))
                    sk_add_value(sk_source, "%s.%s.scale" % (config["inputs"]["thermostat"]["sk_path"], fname), ktemp)
                    sk_add_value(sk_source, "%s.%s.humidity" % (config["inputs"]["thermostat"]["sk_path"], fname), int(float(sdict["indoorHumidity"])))
                    sk_add_value(sk_source, "%s.%s.state" % (config["inputs"]["thermostat"]["sk_path"], fname), status_map[sstat])
                    sk_add_value(sk_source, "%s.%s.statenum" % (config["inputs"]["thermostat"]["sk_path"], fname), statenums[status_map[sstat]])
                    sk_add_value(sk_source, "%s.%s.heatset" % (config["inputs"]["thermostat"]["sk_path"], fname), int(float(sdict["heatSetpoint"])))
                    sk_add_value(sk_source, "%s.%s.coolset" % (config["inputs"]["thermostat"]["sk_path"], fname), int(float(sdict["coolSetpoint"])))
                    sk_add_value(sk_source, "%s.%s.humidity" % (config["inputs"]["outdoor_sensor"]["sk_path"], fname), int(float(sdict["outdoorHumidity"])))
                else:
                    result[s] = {
                        "name": sname,
                        "temp": sdict["dispTemperature"],
                        "scale": scale,
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
            init_site()
            raise IOError
    else:
        logger.debug("concise mode")
        soup = BeautifulSoup(stats_page, "lxml")
        laststat = ""
        for e in soup.find_all("tr", attrs={'class': re.compile(r".*\capsule pointerCursor\b.*")}):
            logger.debug("e = %s" %str(e))
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

            logger.debug("Stat = %s" % stat)
            if config["scale"] == "fahrenheit":
                stat["scale"] = "fahrenheit"
                ktemp = pytemperature.f2k(stat["temp"])
                logger.debug("name = %s, value = %s" % (stat["name"], config["inputs"]))
                if stat["name"] in config["inputs"] and config["inputs"][stat["name"]]["scale"] == "celsius":
                    logger.debug("celcius exception")
                    stat["scale"] = "celsius"
                    ktemp = pytemperature.c2k(stat["temp"])
            else:
                stat["scale"] = "celsius"
                ktemp = pytemperature.c2k(stat["temp"])
                logger.debug("name = %s, value = %s" % (stat["name"], config["inputs"]))
                if stat["name"] in config["inputs"] and config["inputs"][stat["name"]]["scale"] == "fahrenheit":
                    logger.debug("fahrenheit exception")
                    stat["scale"] = "fahrenheit"
                    ktemp = pytemperature.f2k(stat["temp"])
                
            if output == "signalk":
                fname = re.sub(r"[\s+]", '_', stat["name"])
                sk_add_value(sk_source, "%s.%s.temperature" % (config["inputs"]["thermostat"]["sk_path"], fname), ktemp)
                sk_add_value(sk_source, "%s.%s.scale" % (config["inputs"]["thermostat"]["sk_path"], fname), stat["scale"])
                sk_add_value(sk_source, "%s.%s.humidity" % (config["inputs"]["thermostat"]["sk_path"], fname), stat["hum"])
                sk_add_value(sk_source, "%s.%s.redlinkid" % (config["inputs"]["thermostat"]["sk_path"], fname), e["data-id"])
                sk_add_value(sk_source, "%s.%s.state" % (config["inputs"]["thermostat"]["sk_path"], fname), stat["status"])
                sk_add_value(sk_source, "%s.%s.statenum" % (config["inputs"]["thermostat"]["sk_path"], fname), statenums[stat["status"]])
            else:
                result[e["data-id"]] = stat
            laststat = e["data-id"]
            logger.debug("laststat = %s", laststat)
        try:
            if not laststat:
                logger.exception("No stats found")
                raise IOError
            logger.debug("getting outdoor humidity")
            linktext = "/portal/Device/Control/%s?page=1" % laststat
            logger.debug("link text = %s" % linktext)
            link = br.find_link(url=linktext)
            response = br.follow_link(link)
            stattext = response.read()
            statdata = conciseStatData_prog.findall(stattext)
            sdict = dict(statdata)

            if output == "signalk":
                sk_add_value(sk_source, "%s.humidity" % config["inputs"]["outdoor_sensor"]["sk_path"], int(float(sdict["outdoorHumidity"])))
            else:
                result["outhum"] = float(sdict["outdoorHumidity"])
        except:
            # too tricky to handle retries, just come back next time
            logger.exception("Error scraping stat page")
            init_site()
            raise IOError

    if output == "signalk":
        return deltas
    else:
        return result
