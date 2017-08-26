============
Pivac
============

Python package to pull data from Raspberry-Pi(RPi)-based inputs, and output JSON data. Supports the assembly and delivery of RPi-based monitoring and control solutions, like HVAC and home automation. Could also be used for other  monitoring projects like home brewing and sous vide. These inputs include both RPi hardware inputs (like GPIO pins and GPIO-supported protocols like 1-Wire), as well as external sources useful for assembling a complete solution, such as HTTP-based data feeds and web sites (a.k.a. screen scraping.) This package is "input-only" - no provision is (currently) made to process updates.

Currently supported inputs include:

* **1-WireTherm**: 1-Wire-based Dallas temperature sensors (thermometers)
* **GPIO**: Generic reads of RPi GPIO pins, pulled high or low using internal pullup resistors
* **RedLink**: Screen scraping of Honeywell's website for RedLink thermostats, mytotalconnectcomfort.com (requires an account and installed RedLink equipment)
* **TED5000**: Parsing of the live XML feed from the TED5000 home energy monitoring solution.
* **FlirFX**: Collect temperature and humidity from a FLIR camera

The package is extensible, so if the supported inputs don't meet your needs, you can add your own.

The package provides each input individually, so you can pick and choose which ones you want.
