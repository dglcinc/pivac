# pivac
Python package to pull data from Raspberry-Pi(RPi)-based inputs, and output JSON data. Supports the assembly and delivery of RPi-based monitoring and control solutions, like HVAC and home automation. Could also be used for other  monitoring projects like home brewing and sous vide. These inputs include both RPi hardware inputs (like GPIO pins and GPIO-supported protocols like 1-Wire), as well as external sources useful for assembling a complete solution, such as HTTP-based data feeds and web sites (a.k.a. screen scraping.) This package is "input-only" - no provision is (currently) made to process updates.

Currently supported inputs include:

* **1-WireTherm**: 1-Wire-based Dallas temperature sensors (thermometers)
* **GPIO**: Generic reads of RPi GPIO pins, pulled high or low using internal pullup resistors
* **RedLink**: Screen scraping of Honeywell's website for RedLink thermostats, mytotalconnectcomfort.com (requires an account and installed RedLink equipment)
* **TED5000**: Parsing of the live XML feed from the TED5000 home energy monitoring solution.
* **FlirFX**: Temperature and humidity from a FLIR camera

The package is extensible, so if the supported inputs don't meet your needs, you can add your own.

The package provides each input individually, so you can pick and choose which ones you want. Customization is possible via a configuration file.

# Overview
This package has the modest aspiration of simplifying a certain class of monitoring (and eventually control) use cases for Raspberry Pi based projects, by providing pre-built recipes for acquiring data, and emitting the data in JSON format. It has no aspirations to replace more general RPi packages like GPIO and w1Therm (in fact it is built on top of them). Examples cases using JSON data:

* Delivering a status website on your RPi, available on your local network
* Modeling your RPi as an Amazon Web Services (AWS) IOT "thing", uploading your data as thing shadow "updates", and using AWS Lambdas to do stuff (store data, render static websites, etc.)
* Inputting data to a [Signal K](http:/www.signalk.org) server running on your RPi, and leveraging the Signal K ecosystem to process and display your data
* Capturing a time series collection of the data in a database such as InfluxDB, and analyzing in a charting tool such as Grafana

## Standard call interface, Diverse inputs, JSON output
The core concept of this package is simple - go get some data from somewhere related to your use case (a piece of HVAC equipment or a home automation product website) and return it as a JSON-formatted data collection. You can then reformat it and deliver it in a number of different ways. A standard call interface and configuration file format makes it easy to add new modules for new input types.

## Why Python?
What can I say, I like Python. It's easy and fun to write some pretty fancy stuff. And supposedly it's [where the Pi in Raspberry Pi comes from](https://www.techspot.com/article/531-eben-upton-interview/) (Pi-thon, get it?).

## Why RPi and not Arduino
I actually started this project on Arduino, using a packaged Arduino-based PLC from [Digital Loggers](https://dlidirect.com/products/diy-programmable-controller). There are some advantages to using the Arduino in terms of analog inputs, PWM handling, performance, etc. and the DL PLC is pretty cool, with optical input isolators, open collector outputs, LCD screen, etc. I didn't really need these features, and the programming model was not fun (e.g. coding Lua on NodeMCU to do your Wi-Fi comms., serial-loading sketches constantly, etc.) Great if you need it, a pain if you don't. I abandoned this because the RPi is way simpler - I can SSH in headless, use a standard UNIX programming model and tools (which I know very well) code in fun languages like Python -- what's not to like? The code for the (archived) Arduino version is at [HVAC-plc](https://github.com/dglcinc/HVAC-plc).

Ambitious contributors/forkers who like the RPi model and also have more need for Arduino features could follow the suggestion in this [excellent Maker article](http://makezine.com/projects/tutorial-raspberry-pi-gpio-pins-and-python/) to piggy-back an Arduino to your RPi's serial port, and add a module that reads the Arduino and supplies JSON as output.

## Why polling of the GPIO pins, rather than events?
* It's simpler
* I want to store time series data without interpolating
* It makes it easy to disconnect and reconnect to your aggregator and still see the complete picture of current state

I suppose you could do some work to optimize by only generating output when state changes, but that gets a lot more complicated and I don't really see the benefit for my use case, so I didn't do it.

## Why not control too, not just monitoring?
Eventually. For the HVAC use case specifically, I have shied away from making the correct operation of the HVAC system dependent on the RPi:

* It means you can't condition your space if you have a problem with the RPi
* It's very hard to find HVAC technicians that can or will work on RPi-based controls

I'm pondering a design that allows some control or automation by the RPi, but fallback to full mechanical behavior if the RPi is down. When I have a good plan for that I'll reconsider having the RPi control the system.


## Suggestions for Processing the Output
My original project delivered the JSON from my data sources into a python script that dynamically generated a simple web page on the RPi as an Apache-based Python CGI. I then internet-enabled my project (to avoid doing port forwarding to my RPi, and to learn AWS IOT...) by setting up the RPi as a thing on Amazon's IOT service, and using a Lambda to generate an S3-based static page whenever the thing shadow is updated by my RPi, once every few seconds. I know kinda sloppy but it works... You could optimize your updating to minimize charges for Lambda, etc., but at the volume I consume (low and cheap) it's not a priority. The github repository for my current version is at [HVAC-pi](https://github.com/dglcinc/HVAC-pi), including the python cgi in the /local subdirectory, and the AWS thing code in /hvac-pi-aws.

## Signal K!
I serendipitously stumbled on a project targeted at the boating community, [Signal K](http://www.signalk.org). some features of that project are strikingly similar to mine (gather data from a variety of disparate sources and protocols and rationalize them into a JSON-based data stream). They have more and better developers, and a pretty highly evolved ecosystem. So I've converted to outputting my JSON to a Signal K server, and then using the tools in that ecosystem (such as the excellent IOS app [WilhelmSK](http://www.wilhelmsk.com)) to store and render my data. It's very cool. Check it out. The current version of [HVAC-pi](https://github.com/dglcinc/HVAC-pi) includes a [script](https://github.com/dglcinc/HVAC-pi/blob/master/sk-sensor-emit.py) that outputs Signal K deltas, for use with an execute provider. A separate repository will be launched shortly to generify this mechanism.

# Installing the Package
The package is published to PyPi, so you can install it with the following:

```
sudo pip install pivac

```
If you prefer not to run the install as sudo (which puts scripts in /usr/local/bin, config in /etc/pivac, and a python module in your default Python install directory), then clone the [github repository](https://github.com/dglcinc/pivac). The scripts and config will work properly using the local repository directory as the launch point.

## Configuring the Package
The only required configuration is to edit the /etc/pivac/config.yml file to reflect the modules and configuration you want to use. A complete, commented sample is provided as /etc/pivac/config.yml.sample.

Each top level key in the config file is an actual Python package name, so if you create your own Python packages and name them in the config file, they will be used by the package and the scripts.

# Using the Package

Once the configuration file is set up, the easiest way to use the package is to use the scripts, which will be installed in /usr/local/bin unless you opt to clone the git repository:

## The Scripts

* **`pivac-provider.py`** - provides a variety of options for input, output, and formatting. --help option arguments and script behavior are dynamically configured using the contents of the configuration file. The --help option provides detailed documentation on how to use the script.
* **`pivac-provider.sh`** - a wrapper for the .py script, that restarts it if it fails (e.g. when running with --daemon option) (this script execs to provider.sh and inherits its behavior).
* **`provider.sh`** - a generic wrapper script that restarts a script if it fails, and catches the SIGHUP signal (kill -1) to restart the script. A standard kill (SIGINT) will stop the wrapper and the script.

## The Modules
The pivac package currently contains the following modules:

* GPIO
* OneWireTherm
* TED5000
* RedLink
* FlirFX

## Initialization
* **`pivac.set_config(configfile="")`**: This method must be called before using any of the modules. It locates and reads the config file, first in `/etc/pivac/config.yml` then in `config/config.yml` relative to the parent directory of the scripts, if you do not specify it. Returns the `config` dictionary. This currently can only be set once, because the data read from the config file is used to load modules by the `pivac-provider.py` script. If you attempt to set again it will return the current config dict.

* **`pivac.get_config()`**: Returns the config dictionary read from the config file.

* **`[module].status(config={}, output="default")`**: Each module implements (at least) this method, and can be used individually in your project. Each module supports one interface method, status(). Status takes two arguments - a dictionary containing the configuration for the module read from the configuration file, and a string indicating the output type. outputs a JSON object containing JSON state specific to the target being reported on, as follows:

## GPIO
* **`GPIO.status(config={}, output="default")`**: each pin included in the configuration file will be reported as "true" if on and "false" if off.
	* For pins configured with pull-down resistors, "on" or "true" means the pin is attached to voltage.
	* The module configuration file provides options for specifying pull-up or pull-down, as well as names to map pins to in the JSON output.
	* For pins configured with pull-up resistors, "on" or "true" means the pin is attached to ground. 

Example output using the sample yml file with `python pivac-provider.py pivac.GPIO --format "pretty"`:

```
{
    "Y2ON": false, 
    "DEHUM": false, 
    "RCHL": false, 
    "BLR": true, 
    "DHW": false, 
    "Y2FAN": false, 
    "ZV": true, 
    "YOFF": false, 
    "LCHL": false
}
```	

##OneWireTherm

* **`OneWireTherm.status(config={}, output="default")`**: the module will return the current temperature reported by every sensor on the 1-wire bus. Options in the config file allow you to assign names, and specify a temperature scale and rounding. Example output using the sample yml file with `python pivac-provider.py pivac.OneWireTherm --format "pretty"`:

```
{
    "CRW": 45, 
    "OUT": 47, 
    "AMB": 73, 
    "IN": 40
}
```
##TED5000

* **`TED5000.status()`**: Returns JSON for the current PowerNow values of MTUs 1-4 from the URL `<my_ted_gateway_ip_or_hostname>/LiveData.xml`. All TED data is available; The configuration file allows you to specify any path from the `LiveData.xml` url using an XPath-style path, and the "friendly" name it should be mapped to. Example output using the sample yml file with `python pivac-provider.py pivac.TED5000 --format "pretty"`:

```
{
    "MainPanel": 1161, 
    "SubPanel": 398, 
    "HVAC": 30
}
```
##RedLink

* **`Redlink.status(verbose=False)`**: Returns the current temperature, humidity, status, and name (as set on the thermostat) for every thermostat associated with the location defined on mytotalconnectcomfort.com. Temperature will be defined as on the thermostat. Humidity will be a whole number. Status will be one of "cool", "heat", "fanOn", or "off". Outdoor humidity is returned as "outhum". The key for each object is the thermostat identifier used in the RedLink registry. `verbose = True` causes the scraper to navigate to the sub-page for each thermostat, collect all available detailed data like setpoints, and return it as a nested JSON object for each thermostat; this option is slower, so don't use it unless you need it. Example output using the sample yml file with `python pivac-provider.py pivac.RedLink --format "pretty"`:

```
{
    "2834229": {
      "status": "fan", 
      "hum": 51, 
      "name": "KIDS ROOM", 
      "temp": 74
    }, 
    "outhum": 100.0, 
    "2528432": {
      "status": "off", 
      "hum": 47, 
      "name": "KITCHEN", 
      "temp": 75
    }, 
    "2842218": {
      "status": "off", 
      "hum": 50, 
      "name": "MASTER BR", 
      "temp": 74
    }, 
    "2417403": {
      "status": "off", 
      "hum": 51, 
      "name": "DSTRS FAM ROOM", 
      "temp": 74
    }, 
    "2834247": {
      "status": "off", 
      "hum": 49, 
      "name": "GREAT ROOM", 
      "temp": 75
    }
}
```
##FlirFX
The FLirFX module lets you collect temperature and humidity data from a FLIR camera. The config file format allows you to specify multiple cameras (inputs) and your login credentials. Example output using the sample yml file with `python pivac-provider.py pivac.FlirFX --format "pretty"`:

```
{
  "192.168.2.79": {
    "temperature": 67.98, 
    "humidity": 49
  }
}

```
# Example Project
The goal of my RPi project was to create a simple app (single responsive HTML dashboard) that allows me to monitor my HVAC system. It pulls data from four sources:

* Several Dallas [DS18B20](https://www.amazon.com/gp/product/B00CHEZ250/ref=oh_aui_detailpage_o07_s00?ie=UTF8&psc=1) waterproof one-wire temperature sensors connected to the one-wire bus on the RPi, to monitor key control points in my hydronic heating and cooling system.
* Several mechanical (4PDT) relays connected to GPIO pins, to monitor the operational status of the HVAC equipment (what is off or on, heating or cooling, making hot water, etc.)
* A TED5000 power panel monitor, to show energy consumption related to the HVAC operation (mainly two five-ton chillers, that each consume about 8Kwh, and whose operation understandably I would like to optimize)
* Several Honeywell RedLink IAQ 2.0 thermostats, so I can keep track of the conditions in each zone in my HVAC system by seeing current temperature and humidity, equipment status (heating, cooling, etc.), and eventually setpoints.

## Example 1: 1-Wire DS18B20 Temperature Sensors
These are pretty commonly used sensors, because they are cheap and easy to use. There are plenty of tutorials on how to wire these (e.g. [this one](https://www.modmypi.com/blog/ds18b20-one-wire-digital-temperature-sensor-and-the-raspberry-pi)), so I'm not going to cover here. The best Python library I found for these is [w1thermsensor](https://github.com/timofurrer/w1thermsensor), so that's the one I use. Note that without some hacking the data line for the 1-wire bus must be GPIO pin 4. I prefer to power the sensors rather than use "parasitic" mode (which has some limitations), but that's just me.

### Other RPi protocols
The RPi supports several protocols out of the box, such as I2C and SPI. 1-Wire suited my needs, so that's the only one pivac currently supports. The module framework can be easily extended for these by following the 1-Wire Therm example.

## Example 2: GPIO pin inputs
The GPIO pins on the RPi are a good way to collect data. A good way to know which pins you can/should use for inputs is to use a pin mapping chart, like [this one](http://www.raspberrypi-spy.co.uk/2012/06/simple-guide-to-the-rpi-gpio-header-and-pins/). Make sure to use the one appropriate for your Pi.

When reading from a digital pin, in order to get a consistent reading you need to pull it up to a known voltage (e.g. VCC, 3.3V on the board), or pull it down to ground. If you pull up, then you can signal a change by grounding the pin to board ground. If you pull it to ground, then you need to send it a voltage. The ground and the voltage need to be from the same source, so best to reference board ground and board 3.3v for these pins.

The RPi provides both pull-up and pull-down resistors for the pins (if you don't know what these are, [see here](http://raspi.tv/2013/rpi-gpio-basics-6-using-inputs-and-outputs-together-with-rpi-gpio-pull-ups-and-pull-downs)). I use pull-ups, so my circuits are normally connected only to board ground unless my relays close. You may have your own purposes. My library lets you configure a pin as either pull-up or pull-down. Technically you can set them all individually but it's easier to remember if you do one or the other.

## Example 3: TED 5000 (The Energy Detective)
The TED5000 is a power panel monitor that allows you to monitor energy consumption in your home by placing CTs (current transformers) on your main feed or subcircuits in your home's power panel. A small gateway attached to the CTs runs a web server that publishes a website accessible on your local network, that allows you to view a dashboard for current and historical data, charting, and also publishes XML-based data via HTTP GET.

The gateway can be a little flaky and also it's a closed ecosystem, all about TED. You can't easily integrate it with anything else, except by using a couple of APIs it provides. One is a built in capability to publish historical data in one-minute intervals. Another is the "real time" HTTP URL that allows you to collect the current values of all the system parameters in a structured HTML document.

I opted for using the "real time" interface, since that would allow me to control how often and where the data are reported. So my python script calls the real time interface URL, parses the response using the Python lxml parser, and prints the "PowerNow" values for the four possible MTUs (I have 3) to stdout as a JSON-formatted object.

Others may be interested in more or different values from the real-time XML document. The script can easily be extended as desired.

## Example 4: Honeywell mytotalconnectcomfort.com
This is a website targeted specifically at owners of Honeywell WiFi thermostats, or RedLink thermostats connected to a RedLink gateway. Honeywell does not make the data APIs for this site publicly available. There are APIs called by the site, but more header spoofing would be required to get the server to generate a valid request. The same information can be retrieved by screen-scraping the site, so I didn't bother to decode the API headers.

This code makes a number of assumptions, so if your personal use is different, you'll have to tweak the scraping code, which uses [Mechanize](https://github.com/python-mechanize/mechanize). Some points to keep in mind:

* You must have a login account on the site.
* You must have at least one supported thermostat configuration.
* Not all thermostats support all options; for example, older thermostats do not support query of their state (are they cooling, heating, etc.)
* The code maintains an active login session to improve performance and minimize booting due to "too many logins"
* The code supports only one location. If you have multiple locations you will need to modify the scraping code.
* The thermostats will report additional properties such as setpoint. These are output in the JSON as a nested JSON object.
* The website supports the ability to change thermostat settings (setpoint, mode, etc.) This library does not currently implement that feature. You will need to change the scraping code.
* Mechanize has its History object set to NoHistory in the code. Keep in mind if you change this, the history will cause the process to grow and eventually crash your RPi. If you do this, make sure you periodically call Browser's clear_history() method.

There is a site that provides an undocumented way to access Honeywell's REST API interface, [here](http://dirkgroenen.nl/projects/2016-01-15/honeywell-API-endpoints-documentation/).
