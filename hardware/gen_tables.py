"""Pin and net tables shared by gen-boards.py (placement, nets) and gen-schematics.py."""
PITCH = 2.54

# Channel table: name, plug.position, LTV-847 IC/channel, Pi header pin, BCM
CHANNELS = [
    ("ZV", "J1", 1, 17, 11), ("DHW", "J1", 2, 27, 13), ("BLR", "J1", 3, 22, 15),
    ("CHIL", "J2", 1, 25, 22), ("BOS1", "J2", 2, 6, 31), ("BOS2", "J2", 3, 5, 29),
    ("DEHUM", "J3", 1, 12, 32), ("SCALA", "J3", 2, 23, 16), ("HPHEAT", "J3", 3, 24, 18),
    ("SP-D", "J4", 3, 19, 35), ("SP-C", None, None, 13, 33), ("SP-E", None, None, 16, 36),
]
# LTV-847: channel c (1-4) has A = 2c-1, K = 2c, E = 17-2c, C = 18-2c
PI_GND = (6, 14, 20, 30, 34)       # the outer-column grounds; 9, 25 and 39 stay unconnected
GND_BUS_X = 0.75                   # pre-routed ground bus along the board edge, F.Cu
PI_5V = (2, 4)
PI_3V3 = (1, 17)
# Shadow column: one breakout pad per header row, 2.54 mm right of the inner column, carrying
# that row's odd pin where it is free, otherwise a nearby even pin. (label, Pi pin) per row 1-20;
# None leaves the row without a pad.
BREAKOUT = [None, None, ("SCL", 5, "SCL"), ("G4", 7, "GPIO4"), ("GND", 9, "GND"), ("G18", 12, "GPIO18"),
            ("SDA", 3, "SDA"), ("5V", 4, "+5V"), ("3V3", 17, "3V3"), ("G10", 19, "GPIO10"),
            ("G9", 21, "GPIO9"), ("G11", 23, "GPIO11"), ("G7", 26, "GPIO7"), ("G8", 24, "GPIO8"),
            ("GND", 30, "GND"), None, ("GND", 34, "GND"), None, ("G20", 38, "GPIO20"), ("G21", 40, "GPIO21")]
BREAKOUT_X = 4.77 + PITCH
PLUG_X = {"J1": 13.1, "J2": 24.8, "J3": 36.5, "J4": 48.2}   # pin-row centres, from the STEP
PLUG_Y = 6.95
