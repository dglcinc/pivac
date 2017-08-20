import lxml.html
import lxml.etree
import requests
import logging

MTU1 = "MTU1"
MTU2 = "MTU2"
MTU3 = "MTU3"
MTU4 = "MTU4"

logger = logging.getLogger(__name__)

def status():
    result = {
        MTU1:0,
        MTU2:0,
        MTU3:0,
        MTU4:0
    }
    try:
        page = requests.get("http://192.168.1.124/stats.htm")
        tree = lxml.html.fromstring(page.content)
        table = tree.xpath("/html/body/center/table[1]/*[text()]")
        for element in table:
            el = element.findall("*")
            for item in el:
                logger.debug(item.text)
                if item.text == "Power:":
                    result[MTU1] = int(el[1].text)
                    result[MTU2] = int(el[2].text)
                    result[MTU3] = int(el[3].text)
                    result[MTU4] = int(el[4].text)
                    return result
    except:
        logger.exception("Exception collecting data from TED5000")

    return result
