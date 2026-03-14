# Thin wrapper for backward compatibility.
# All implementation is in pivac.ArduinoSensor.
# New configs should use: module: pivac.ArduinoSensor
from pivac.ArduinoSensor import status  # noqa: F401

if __name__ == "__main__":
    import logging
    logging.basicConfig(format='%(name)s %(levelname)s:%(asctime)s %(message)s',datefmt='%m/%d/%Y %I:%M:%S',level="DEBUG")
    status()
