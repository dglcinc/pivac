# pivac
Python package to vacuum data from Raspberry-Pi(RPi)-based monitoring and control solutions (like HVAC and home automation)


# Overview
This module has the modest aspiration of making it easier to solve a certain class of monitoring (and eventually control) use cases for Raspberry Pi based projects, by providing pre-built recipes for common situations in HVAC and home automation projects. It has no aspirations to replace more general modules like GPIO and w1Therm (in fact it is built on top of them.)

## Standard call interface, Diverse inputs, JSON output
The core concept of this package is simple - go get some data from somewhere related to your use case (a piece of HVAC equipment or a home automation product website) and return it as a JSON-formatted data collection. You can then reformat it and deliver it in a number of different ways.

## Why Python?
What can I say, I like Python. It's easy and fun to write some pretty fancy stuff. And supposedly that's [where the Pi in Raspberry Pi comes from](https://www.techspot.com/article/531-eben-upton-interview/) (Pi-thon, get it?).

## Why RPi and not Arduino
I actually started this project on Arduino, using a packaged Arduino-based PLC from [Digital Loggers](http://www.digital-loggers.com). There are some advantages to using the Arduino in terms of analog inputs, PWM handling, performance, etc. and the DL PLC is pretty cool, with optical input isolators, open collector outputs, LCD screen, etc. I didn't really need the benefits of the Arduino and the programming model was not fun (e.g. coding in Lua on NodeMCU to do your Wi-Fi comms., serial-loading sketches constantly, etc.) Great if you need it, a pain if you don't. I abandoned this because the RPi is way simpler - I can SSH in headless, use a standard UNIX programming model and tools (which I know very well) code in fun languages like Python -- what's not to like?

Ambitious contributors/forkers who have more need for Arduino could follow the suggestion in this [excellent Maker article](http://makezine.com/projects/tutorial-raspberry-pi-gpio-pins-and-python/) to piggy-back an Arduino to your RPi's serial port, and add a module supply JSON as output.

# Some serving suggestions
My original project assembled it all into a pretty simple web page delivered on the RPi via an Apache-based Python CGI, then by setting up the RPi as a thing on Amazon's IOT service and using a Lambda to re-generate an S3-based static page whenever the thing shadow is updated by my RPi, about once every few seconds. I know kinda sloppy but it works... That is where you could optimize your updating to minimize charges for Lambda, etc., but at the volume I consume (low and cheap) it's not a priority. The github repository for that version is at [HVAC-pi]().

## Signal-K!
I serendipitously stumbled on a project targeted at the boating community, [Signal K](http://www.signalk.org). It's goal is strikingly similar to mine (gather data from a variety of disparate sources and protocols and rationalize them into a JSON-based data stream). They have more and better developers, and a pretty highly evolved ecosystem. So I've converted to outputting my JSON to a Signal K server, and then using the tools in that ecosystem (such as the excellent IOS app [WilhelmSK](http://www.wilhelmsk.com)) to store and render my data. It's very cool. Check it out.

# Example Project
My example RPi project is to create a one-page app that allows me to monitor my HVAC system. It pulls (vacuums) data from four sources:
* Several Dallas one-wire temperature sensors connected to the one-wire bus on the RPi, to monitor key control points in my hydronic heating and cooling system.
* Several mechanical (4PDT) relays connected to GPIO pins, to monitor the operational status of the HVAC equipment (what is off or on, heating or cooling, making hot water, etc.)
* A TED5000 power panel monitor, to show energy consumption related to the HVAC operation (mainly two five-ton chillers, that each consume about 8Kwh, and whose operation understandably I would like to optimize)
* Several Honeywell RedLink IAQ 2.0 thermostats, so I can keep track of the conditions in each zone in my HVAC system by seeing current temperature and humidity, equipment status (heating, cooling, etc.), and eventually setpoints.

### Why polling of the GPIO pins, rather than events?
* It's simpler
* I want to store time series data without interpolating
* It makes it easy to dis-connect and reconnect to your aggregator and see the complete picture
I suppose you could do some work to optimize by only generating output when state changes, but that gets a lot more complicated and I don't really see the benefit for my use case, so I didn't do it.
### Why not control too, not just monitoring?

## Example 1: TED 5000 (The Energy Detective)
The TED5000 is a power panel monitor that allows you to monitor energy consumption in your home by placing CTs (current transformers) on your main feed or subcircuits in your home's power panel. A small gateway attached to the CTs runs a web server that publishes a website accessible on your local network, and also publishes XML-based data via HTTP GET.

What I wanted to do f
