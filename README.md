# pivac
Python package to vacuum data from Raspberry-Pi(RPi)-based inputs, to support the assembly and delivery of RPi-based monitoring and control solutions (like HVAC and home automation, but could also be used for other  monitoring projects like home brewing and sous vide). These inputs include both RPi hardware inputs (like GPIO pins and GPIO-supported protocols like 1-Wire), as well as external sources useful for assembling a complete solution, such as HTTP-based data feeds and web sites (a.k.a. screen scraping.) This package is "input-only" - no provision is (currently) made to process updates.

Currently supported inputs include:
* 1-WireTherm: 1-Wire-based Dallas temperature sensors (thermometers)
* GPIORead: Generic reads of RPi GPIO pins, pulled high using internal pullup resistors
* RedLink: Screen scraping of Honeywell's website for RedLink thermostats, mytotalconnectcomfort.com (requires an account and installed RedLink equipment)
* TED5000: Parsing of the live XML feed from the TED5000 home energy monitoring solution.

The package is designed to be extensible, so if the supported inputs don't meet your needs, you can add your own.

# Overview
This module has the modest aspiration of making it easier to solve a certain class of monitoring (and eventually control) use cases for Raspberry Pi based projects, by providing pre-built recipes for acquiring data for common HVAC and home automation use cases, and a framework for emitting readings in JSON format. It has no aspirations to replace more general RPi packages like GPIO and w1Therm (in fact it is built on top of them). Examples of upstream use:
* Delivering a status website on your RPi, available for use on your local network
* Modeling your RPi as an AWS IOT "thing", uploading your data as thing shadow "updates", and using AWS Lambdas to do stuff (store data, render static websites, etc.)
* Inputting data to a [Signal K](http:/www.signalk.org) server running on your RPi, and leveraging the Signal K ecosystem to process and display your data

## Standard call interface, Diverse inputs, JSON output
The core concept of this package is simple - go get some data from somewhere related to your use case (a piece of HVAC equipment or a home automation product website) and return it as a JSON-formatted data collection. You can then reformat it and deliver it in a number of different ways.

## Why Python?
What can I say, I like Python. It's easy and fun to write some pretty fancy stuff. And supposedly that's [where the Pi in Raspberry Pi comes from](https://www.techspot.com/article/531-eben-upton-interview/) (Pi-thon, get it?).

## Why RPi and not Arduino
I actually started this project on Arduino, using a packaged Arduino-based PLC from [Digital Loggers](http://www.digital-loggers.com). There are some advantages to using the Arduino in terms of analog inputs, PWM handling, performance, etc. and the DL PLC is pretty cool, with optical input isolators, open collector outputs, LCD screen, etc. I didn't really need the benefits of the Arduino and the programming model was not fun (e.g. coding in Lua on NodeMCU to do your Wi-Fi comms., serial-loading sketches constantly, etc.) Great if you need it, a pain if you don't. I abandoned this because the RPi is way simpler - I can SSH in headless, use a standard UNIX programming model and tools (which I know very well) code in fun languages like Python -- what's not to like? The code for the Arduino version is at [HVAC-plc](https://github.com/dglcinc/HVAC-plc).

Ambitious contributors/forkers who have more need for Arduino could follow the suggestion in this [excellent Maker article](http://makezine.com/projects/tutorial-raspberry-pi-gpio-pins-and-python/) to piggy-back an Arduino to your RPi's serial port, and add a module to supply JSON as output.

# Some Serving Suggestions
My original project delivered the JSON from my data sources into a simple web page delivered on the RPi via an Apache-based Python CGI. I then internet-enabled it by setting up the RPi as a thing on Amazon's IOT service and using a Lambda to re-generate an S3-based static page whenever the thing shadow is updated by my RPi, about once every few seconds. I know kinda sloppy but it works... You could optimize your updating to minimize charges for Lambda, etc., but at the volume I consume (low and cheap) it's not a priority. The github repository for my current version is at [HVAC-pi](https://github.com/dglcinc/HVAC-pi), including the python cgi in the /local subdirectory, and the AWS thing code in /hvac-pi-aws.

## Signal K!
I serendipitously stumbled on a project targeted at the boating community, [Signal K](http://www.signalk.org). some features of that project are strikingly similar to mine (gather data from a variety of disparate sources and protocols and rationalize them into a JSON-based data stream). They have more and better developers, and a pretty highly evolved ecosystem. So I've converted to outputting my JSON to a Signal K server, and then using the tools in that ecosystem (such as the excellent IOS app [WilhelmSK](http://www.wilhelmsk.com)) to store and render my data. It's very cool. Check it out.

# Example Project
The goal of my RPi project is to create a simple app (single responsive HTML dashboard) that allows me to monitor my HVAC system. It pulls data from four sources:
* Several Dallas [DS18B20](https://www.amazon.com/gp/product/B00CHEZ250/ref=oh_aui_detailpage_o07_s00?ie=UTF8&psc=1) waterproof one-wire temperature sensors connected to the one-wire bus on the RPi, to monitor key control points in my hydronic heating and cooling system.
* Several mechanical (4PDT) relays connected to GPIO pins, to monitor the operational status of the HVAC equipment (what is off or on, heating or cooling, making hot water, etc.)
* A TED5000 power panel monitor, to show energy consumption related to the HVAC operation (mainly two five-ton chillers, that each consume about 8Kwh, and whose operation understandably I would like to optimize)
* Several Honeywell RedLink IAQ 2.0 thermostats, so I can keep track of the conditions in each zone in my HVAC system by seeing current temperature and humidity, equipment status (heating, cooling, etc.), and eventually setpoints.

### Why polling of the GPIO pins, rather than events?
* It's simpler
* I want to store time series data without interpolating
* It makes it easy to dis-connect and reconnect to your aggregator and still see the complete picture of current state
I suppose you could do some work to optimize by only generating output when state changes, but that gets a lot more complicated and I don't really see the benefit for my use case, so I didn't do it.

### Why not control too, not just monitoring?
Eventually. For the HVAC use case specifically, I have shied away from making the correct operation of the HVAC system dependent on the RPi:
* It means you can't condition your space if you have a problem with the RPi
* It's very hard to find HVAC technicians that can or will work on RPi-based controls

I'm pondering a design that allows some control or automation by the RPi, but fallback to full mechanical behavior if the RPi is down. When I have a good plan for that I'll reconsider having the RPi control the system.

## Example 1: 1-Wire Dallas Temperature Sensors, DS18B20
These are pretty commonly used sensors, because they are cheap and easy to use. There are plenty of tutorials on how to wire these (e.g. [this one](https://www.modmypi.com/blog/ds18b20-one-wire-digital-temperature-sensor-and-the-raspberry-pi), so I'm not going to cover. The best Python library I found for these is [w1thermsensor](https://github.com/timofurrer/w1thermsensor), so that's the one I use. Note that without some hacking the data line for the 1-wire bus must be GPIO pin 4. I prefer to power the sensors rather than use "parasitic" mode (which has some limitations), but that's just me.

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
