#!/usr/bin/env python3
"""Generate the KiCad boards that replace the two Phoenix RPI-BC perfboards.

Run with KiCad's own Python so that ``pcbnew`` imports:

    ~/Applications/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
        hardware/gen-boards.py

Writes ``hardware/int-board/int-board.kicad_pcb`` and ``hardware/ext-board/ext-board.kicad_pcb``
with the outline, the housing's restricted areas as rule areas, every footprint placed and
every pad on its net. Routing is done afterwards by ``hardware/route.sh`` (Freerouting), and the
plan is ``docs/rpi-io-boards-pcb-plan.md``.

Frame: the build docs' frame (Appendix A of the plan) — column 1 left, row 1 top, component
side toward the viewer, origin at the board's top-left corner, y down. All positions in mm.
"""
import os
import sys

import pcbnew
from pcbnew import VECTOR2I, FromMM

HERE = os.path.dirname(os.path.abspath(__file__))
KICAD = os.path.expanduser("~/Applications/KiCad.app/Contents/SharedSupport")
FPLIB = os.path.join(KICAD, "footprints")
PIVAC_PRETTY = os.path.join(HERE, "pivac.pretty")

PITCH = 2.54
LAYERS = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu, "F.SilkS": pcbnew.F_SilkS, "B.SilkS": pcbnew.B_SilkS,
          "F.Fab": pcbnew.F_Fab, "B.Fab": pcbnew.B_Fab, "F.CrtYd": pcbnew.F_CrtYd, "B.CrtYd": pcbnew.B_CrtYd,
          "Edge.Cuts": pcbnew.Edge_Cuts, "User.1": pcbnew.User_1}
BANDS_Y = [(18.11, 22.31), (61.29, 65.49)]  # housing ribs, both boards, solder side


def mm(x, y):
    return VECTOR2I(FromMM(x), FromMM(y))


# --------------------------------------------------------------------------- board helpers
class Board:
    def __init__(self, path, width, length):
        self.path = path
        self.width, self.length = width, length
        self.board = pcbnew.NewBoard(path)
        self.nets = {}
        self.refs = {}
        self._setup()

    def _setup(self):
        b = self.board
        ds = b.GetDesignSettings()
        ds.SetCopperLayerCount(2)
        ds.SetBoardThickness(FromMM(1.6))
        ds.m_TrackMinWidth = FromMM(0.2)
        ds.m_ViasMinSize = FromMM(0.6)
        ds.m_MinThroughDrill = FromMM(0.3)
        ds.m_MinClearance = FromMM(0.2)
        ds.m_CopperEdgeClearance = FromMM(0.3)
        ns = ds.m_NetSettings
        default = ns.GetDefaultNetclass()
        default.SetClearance(FromMM(0.2))
        default.SetTrackWidth(FromMM(0.25))
        default.SetViaDiameter(FromMM(0.8))
        default.SetViaDrill(FromMM(0.4))
        power = pcbnew.NETCLASS("Power")
        power.SetClearance(FromMM(0.25))
        power.SetTrackWidth(FromMM(0.5))
        power.SetViaDiameter(FromMM(1.0))
        power.SetViaDrill(FromMM(0.5))
        ns.SetNetclass("Power", power)
        for pat in ("VS", "COM", "AC*", "+5V", "GND", "VCC"):
            ns.SetNetclassPatternAssignment(pat, "Power")
        # outline
        rect = pcbnew.PCB_SHAPE(b)
        rect.SetShape(pcbnew.SHAPE_T_RECT)
        rect.SetStart(mm(0, 0))
        rect.SetEnd(mm(self.width, self.length))
        rect.SetLayer(pcbnew.Edge_Cuts)
        rect.SetWidth(FromMM(0.1))
        b.Add(rect)

    # nets
    def net(self, name):
        if name not in self.nets:
            n = pcbnew.NETINFO_ITEM(self.board, name)
            self.board.Add(n)
            self.nets[name] = n
        return self.nets[name]

    # rule areas
    def keepout(self, pts, layers=("B.Cu",), name="", pads=True, footprints=True, tracks=False,
                vias=False, pour=True):
        z = pcbnew.ZONE(self.board)
        z.SetIsRuleArea(True)
        z.SetZoneName(name)
        z.SetDoNotAllowPads(pads)
        z.SetDoNotAllowFootprints(footprints)
        z.SetDoNotAllowTracks(tracks)
        z.SetDoNotAllowVias(vias)
        try:
            z.SetDoNotAllowZoneFills(pour)
        except AttributeError:
            z.SetDoNotAllowCopperPour(pour)
        ls = pcbnew.LSET()
        for l in layers:
            ls.addLayer(LAYERS[l])
        z.SetLayerSet(ls)
        chain = pcbnew.SHAPE_LINE_CHAIN()
        for x, y in pts:
            chain.Append(mm(x, y))
        chain.SetClosed(True)
        z.Outline().AddOutline(chain)
        self.board.Add(z)
        return z

    def zone(self, netname, pts, layer="B.Cu", clearance=0.25, width=0.25):
        z = pcbnew.ZONE(self.board)
        z.SetNet(self.net(netname))
        z.SetLayer(LAYERS[layer])
        z.SetLocalClearance(FromMM(clearance))
        z.SetMinThickness(FromMM(width))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        chain = pcbnew.SHAPE_LINE_CHAIN()
        for x, y in pts:
            chain.Append(mm(x, y))
        chain.SetClosed(True)
        z.Outline().AddOutline(chain)
        self.board.Add(z)
        return z

    def track(self, netname, x0, y0, x1, y1, layer="F.Cu", width=0.4):
        t = pcbnew.PCB_TRACK(self.board)
        t.SetStart(mm(x0, y0))
        t.SetEnd(mm(x1, y1))
        t.SetWidth(FromMM(width))
        t.SetLayer(LAYERS[layer])
        t.SetNet(self.net(netname))
        self.board.Add(t)
        return t

    def fill(self):
        pcbnew.ZONE_FILLER(self.board).Fill(self.board.Zones())

    def rect_keepout(self, x0, y0, x1, y1, **kw):
        return self.keepout([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], **kw)

    # graphics
    def line(self, x0, y0, x1, y1, layer="F.SilkS", width=0.15):
        s = pcbnew.PCB_SHAPE(self.board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(mm(x0, y0))
        s.SetEnd(mm(x1, y1))
        s.SetLayer(LAYERS[layer])
        s.SetWidth(FromMM(width))
        self.board.Add(s)

    def text(self, s, x, y, layer="F.SilkS", size=1.0, rot=0, bold=False):
        t = pcbnew.PCB_TEXT(self.board)
        t.SetText(s)
        t.SetPosition(mm(x, y))
        t.SetLayer(LAYERS[layer])
        t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size)))
        t.SetTextThickness(FromMM(size * 0.15))
        t.SetTextAngleDegrees(rot)
        if bold:
            t.SetBold(True)
        if layer.startswith("B."):
            t.SetMirrored(True)
        self.board.Add(t)
        return t

    # footprints
    def place(self, ref, fp, x, y, rot=0, back=False, value="", dnp=False):
        """Add a FOOTPRINT (already built or loaded) at (x, y) with rotation in degrees.

        ``back`` flips it onto the solder side. Pad positions are checked by the caller.
        """
        fp.SetReference(ref)
        fp.SetValue(value)
        self.board.Add(fp)
        if back:
            fp.SetLayerAndFlip(pcbnew.B_Cu)
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(mm(x, y))
        if dnp:
            fp.SetDNP(True)
            fp.SetExcludedFromBOM(True)
        fp.Reference().SetTextSize(VECTOR2I(FromMM(0.8), FromMM(0.8)))
        fp.Reference().SetTextThickness(FromMM(0.12))
        fp.Value().SetVisible(False)
        self.refs[ref] = fp
        return fp

    def lib(self, ref, libname, fpname, x, y, rot=0, **kw):
        fp = pcbnew.FootprintLoad(os.path.join(FPLIB, libname + ".pretty"), fpname)
        if fp is None:
            raise SystemExit(f"footprint {libname}:{fpname} not found")
        return self.place(ref, fp, x, y, rot, **kw)

    def connect(self, ref, pad, netname):
        fp = self.refs[ref]
        p = fp.FindPadByNumber(str(pad))
        if p is None:
            raise SystemExit(f"{ref} has no pad {pad}")
        p.SetNet(self.net(netname))

    def pad_xy(self, ref, pad):
        p = self.refs[ref].FindPadByNumber(str(pad)).GetPosition()
        return pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)

    def save(self):
        self.board.Save(self.path)


# --------------------------------------------------------------------------- custom footprints
def _pad(fp, number, x, y, size, drill, shape=pcbnew.PAD_SHAPE_CIRCLE):
    p = pcbnew.PAD(fp)
    p.SetNumber(str(number))
    p.SetShape(shape)
    p.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
    p.SetSize(VECTOR2I(FromMM(size), FromMM(size)))
    p.SetDrillSize(VECTOR2I(FromMM(drill), FromMM(drill)))
    p.SetLayerSet(pcbnew.PAD.PTHMask())
    p.SetPosition(mm(x, y))
    fp.Add(p)
    return p


def _fp_rect(fp, x0, y0, x1, y1, layer, width=0.12):
    s = pcbnew.PCB_SHAPE(fp)
    s.SetShape(pcbnew.SHAPE_T_RECT)
    s.SetStart(mm(x0, y0))
    s.SetEnd(mm(x1, y1))
    s.SetLayer(layer)
    s.SetWidth(FromMM(width))
    fp.Add(s)


def _fp_text(fp, s, x, y, layer, size=0.8):
    t = pcbnew.PCB_TEXT(fp)
    t.SetText(s)
    t.SetPosition(mm(x, y))
    t.SetLayer(layer)
    t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size)))
    t.SetTextThickness(FromMM(size * 0.15))
    fp.Add(t)


def ptsm_hh(board, n):
    """Phoenix PTSM 0,5/n-HH-2,5-THR: one row of n pins at 2.5 mm, holes 1.1 mm, entry toward -y.

    Body (a + 4.2) wide and 7.5 deep, a = (n-1)*2.5; the pin row sits 5.4 mm behind the entry
    face and 2.1 mm ahead of the rear face (Phoenix drawing 1814867; the 5.4 is what makes the
    EXT board's sockets overhang the row-1 edge by 1.7 mm as the build doc observed).
    """
    fp = pcbnew.FOOTPRINT(board.board)
    fp.SetFPID(pcbnew.LIB_ID("pivac", f"PTSM_0.5_{n}-HH-2.5-THR"))
    fp.SetLibDescription(f"Phoenix Contact PTSM 0,5/{n}-HH-2,5-THR horizontal print header")
    a = (n - 1) * 2.5
    for i in range(n):
        _pad(fp, i + 1, -a / 2 + i * 2.5, 0, 1.95, 1.1,
             pcbnew.PAD_SHAPE_ROUNDRECT if i == 0 else pcbnew.PAD_SHAPE_CIRCLE)
    hw = (a + 4.2) / 2
    _fp_rect(fp, -hw, -5.4, hw, 2.1, pcbnew.F_Fab, 0.1)
    _fp_rect(fp, -hw - 0.1, -5.5, hw + 0.1, 2.2, pcbnew.F_SilkS, 0.12)
    _fp_rect(fp, -hw + 0.02, -5.65, hw - 0.02, 2.35, pcbnew.F_CrtYd, 0.05)
    _fp_text(fp, "1", -a / 2, 3.2, pcbnew.F_SilkS, 0.7)
    fp.Reference().SetPosition(mm(0, -1.6))
    fp.Value().SetPosition(mm(0, 3.5))
    return fp


def pad_array(board, name, cols, rows, pitch=PITCH, size=1.6, drill=1.0, square_first=True):
    """A plated-hole prototyping field or breakout row, pads numbered row-major from 1."""
    fp = pcbnew.FOOTPRINT(board.board)
    fp.SetFPID(pcbnew.LIB_ID("pivac", name))
    n = 1
    for j in range(rows):
        for i in range(cols):
            _pad(fp, n, i * pitch, j * pitch, size, drill,
                 pcbnew.PAD_SHAPE_ROUNDRECT if (n == 1 and square_first) else pcbnew.PAD_SHAPE_CIRCLE)
            n += 1
    _fp_rect(fp, -pitch / 2, -pitch / 2, (cols - 0.5) * pitch, (rows - 0.5) * pitch, pcbnew.F_CrtYd, 0.05)
    fp.Reference().SetPosition(mm((cols - 1) * pitch / 2, -pitch))
    fp.Value().SetPosition(mm(0, rows * pitch))
    return fp


def radial_2pin(board, name, pitch, dia, drill=1.0, size=1.8):
    fp = pcbnew.FOOTPRINT(board.board)
    fp.SetFPID(pcbnew.LIB_ID("pivac", name))
    _pad(fp, 1, -pitch / 2, 0, size, drill, pcbnew.PAD_SHAPE_ROUNDRECT)
    _pad(fp, 2, pitch / 2, 0, size, drill)
    _fp_rect(fp, -dia / 2, -dia / 2, dia / 2, dia / 2, pcbnew.F_SilkS)
    _fp_rect(fp, -dia / 2 - 0.25, -dia / 2 - 0.25, dia / 2 + 0.25, dia / 2 + 0.25, pcbnew.F_CrtYd, 0.05)
    fp.Reference().SetPosition(mm(0, -dia / 2 - 1))
    fp.Value().SetPosition(mm(0, dia / 2 + 1))
    return fp


def pi_header(board):
    """2 x 20 socket pads, 2.54 mm, numbered as the Pi header is seen through the board from the
    component side: odd pins in the inner column (+x), even pins in the outer column (-x), pin 1
    at the top. Built pre-mirrored (y negated, layers swapped) because SetLayerAndFlip mirrors
    the footprint top-to-bottom when the caller moves it to the solder side. Placed at pin 1."""
    fp = pcbnew.FOOTPRINT(board.board)
    fp.SetFPID(pcbnew.LIB_ID("pivac", "PiHeader_2x20_Socket_Bottom"))
    for k in range(20):
        _pad(fp, 2 * k + 1, 0, -k * PITCH, 1.7, 1.0, pcbnew.PAD_SHAPE_ROUNDRECT if k == 0 else pcbnew.PAD_SHAPE_CIRCLE)
        _pad(fp, 2 * k + 2, -PITCH, -k * PITCH, 1.7, 1.0)
    _fp_rect(fp, -PITCH - 1.27, 1.27, 1.27, -19 * PITCH - 1.27, pcbnew.F_Fab, 0.1)
    _fp_rect(fp, -PITCH - 1.52, 1.52, 1.52, -19 * PITCH - 1.52, pcbnew.F_CrtYd, 0.05)
    fp.Reference().SetPosition(mm(-1.27, 2.6))
    fp.Value().SetPosition(mm(-1.27, -20 * PITCH))
    return fp


def shadow_column(board, rows):
    """One pad per header row at 2.54 mm, rows with None omitted; pad number = row number."""
    fp = pcbnew.FOOTPRINT(board.board)
    fp.SetFPID(pcbnew.LIB_ID("pivac", "Shadow_1x20"))
    for k, entry in enumerate(rows, start=1):
        if entry is None:
            continue
        _pad(fp, k, 0, (k - 1) * PITCH, 1.6, 1.0, pcbnew.PAD_SHAPE_ROUNDRECT if k == 1 else pcbnew.PAD_SHAPE_CIRCLE)
    first = next(k for k, e in enumerate(rows) if e is not None)
    _fp_rect(fp, -0.9, (first - 0.5) * PITCH, 0.9, (len(rows) - 0.5) * PITCH, pcbnew.F_CrtYd, 0.05)
    fp.Reference().SetPosition(mm(0, -2.6))
    fp.Value().SetPosition(mm(0, len(rows) * PITCH))
    return fp


def save_pretty(fps):
    """Write the custom footprints into hardware/pivac.pretty so the GUI can find them."""
    os.makedirs(PIVAC_PRETTY, exist_ok=True)
    io = pcbnew.PCB_IO_KICAD_SEXPR()
    seen = set()
    for fp in fps:
        name = fp.GetFPID().GetLibItemName().wx_str()
        if name in seen:
            continue
        seen.add(name)
        try:
            io.FootprintSave(PIVAC_PRETTY, fp)
        except Exception as e:  # pragma: no cover
            print("footprint save failed:", name, e)


# --------------------------------------------------------------------------- INT board
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


def build_int():
    out = os.path.join(HERE, "int-board")
    os.makedirs(out, exist_ok=True)
    B = Board(os.path.join(out, "int-board.kicad_pcb"), 59.0, 85.0)
    custom = []

    # restricted areas (solder side): the two bands, the column-20 strip and its bulges
    B.rect_keepout(12.99, BANDS_Y[0][0], 59.0, BANDS_Y[0][1], name="housing rib upper")
    B.rect_keepout(6.64, BANDS_Y[1][0], 59.0, BANDS_Y[1][1], name="housing rib lower")
    B.rect_keepout(48.85, 22.31, 50.75, 61.29, name="housing strip col 20")
    for yb in (26.91, 37.83, 45.77, 56.69):
        B.rect_keepout(49.8 - 1.63, yb - 1.63, 49.8 + 1.63, yb + 1.63, name="housing bulge")
    # the riser/edge region left of x 6.64 below the header is free; the Pi header itself sits
    # between y 8 and 57 at x < 6.
    for (y0, y1) in BANDS_Y:
        B.line(0, y0, 59, y0, "B.SilkS", 0.1)
        B.line(0, y1, 59, y1, "B.SilkS", 0.1)

    # --- field plugs J1..J4
    for j, xc in PLUG_X.items():
        custom.append(B.place(j, ptsm_hh(B, 4), xc, PLUG_Y, 0, value="PTSM 0,5/4-HH-2,5-THR"))
    # --- Pi header socket on the solder side. Pad numbering follows the build doc's verified
    # map (docs/rpi-io-board-design.md §4.2): pin 1 at (4.77, 8.37), pin 2 at (2.23, 8.37),
    # pin 3 at (4.77, 10.91). Built by hand so the numbering is explicit; §7 of the plan asks
    # for the meter check of pin 1 and pin 2 before ordering.
    custom.append(B.place("J5", pi_header(B), 4.77, 8.37, 0, back=True, value="Pi 40-pin socket"))
    for pin, (x, y) in ((1, (4.77, 8.37)), (2, (2.23, 8.37)), (3, (4.77, 10.91)), (40, (2.23, 56.63))):
        px, py = B.pad_xy("J5", pin)
        if abs(px - x) > 0.01 or abs(py - y) > 0.01:
            raise SystemExit(f"header pad {pin} at {px:.2f},{py:.2f}, wanted {x},{y}")

    # --- optocouplers, horizontal, pin 1 at the left of the lower row; rows at y 28.5/41/53.5
    ic_y = {1: 28.5, 2: 41.0, 3: 53.5}
    for k, yc in ic_y.items():
        ic = B.lib(f"U{k}", "Package_DIP", "DIP-16_W7.62mm_Socket", 0, 0, 90, value="LTV-847")
        # rotation 90 puts pins 1-8 along +x? measure and fix so pin 1 is at (7.5, yc+3.81)
        for rot in (90, 270):
            ic.SetOrientationDegrees(rot)
            ic.SetPosition(mm(0, 0))
            p1 = ic.FindPadByNumber("1").GetPosition()
            ic.SetPosition(mm(10.5 - pcbnew.ToMM(p1.x), yc + 3.81 - pcbnew.ToMM(p1.y)))
            x8, y8 = B.pad_xy(f"U{k}", 8)
            x16, y16 = B.pad_xy(f"U{k}", 16)
            if x8 > 20 and abs(y8 - (yc + 3.81)) < 0.01 and abs(y16 - (yc - 3.81)) < 0.01:
                break
        else:
            raise SystemExit("could not orient the DIP")
    # --- LED resistors, vertical, five columns right of the ICs, three rows
    res_x = [32.0, 36.0, 40.0, 44.0]
    n = 0
    for k, yc in ic_y.items():
        for i in range(4):
            n += 1
            B.lib(f"R{n}", "Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
                  res_x[i], yc - 5.08, 270, value="12k 1/4W")
    # --- rectifier: four 1N4007 flat, 2 x 2, bottom field
    for i, (ref, x, y) in enumerate([("D1", 37.58, 67.0), ("D2", 37.58, 70.2), ("D3", 50.58, 67.0), ("D4", 50.58, 70.2)]):
        B.lib(ref, "Diode_THT", "D_DO-41_SOD81_P10.16mm_Horizontal", x - 5.08, y, 0, value="1N4007")
    # --- bulk capacitor, PTC, MOV, test points
    B.lib("C1", "Capacitor_THT", "CP_Radial_D10.0mm_P5.00mm", 19.0, 70.0, 0, value="220u 50V")
    custom.append(B.place("F1", radial_2pin(B, "PTC_Radial_P5.08", 5.08, 7.5), 55.0, 26.0, 90, value="PTC 0.1A"))
    custom.append(B.place("RV1", radial_2pin(B, "MOV_Radial_P5.0", 5.0, 7.0), 55.0, 34.5, 90, value="MOV 39V", dnp=True))
    for ref, y, val in (("TP1", 41.0, "VS"), ("TP2", 44.0, "COM"), ("TP3", 47.0, "GND")):
        custom.append(B.place(ref, pad_array(B, "TestPad", 1, 1, size=1.8, drill=1.0, square_first=False), 55.0, y, 0, value=val))
    # spare channel outputs SP-C, SP-E and COM on a 1x3 pad row
    custom.append(B.place("J8", pad_array(B, "Pads_1x3", 1, 3), 55.0, 52.5, 0, value="SP-C SP-E COM"))
    # --- link headers: signal link (fitted) and power link (not fitted), entry toward the bottom edge
    custom.append(B.place("J6", ptsm_hh(B, 5), 13.0, 78.0, 180, value="PTSM 0,5/5-HH-2,5-THR"))
    custom.append(B.place("J7", ptsm_hh(B, 4), 26.2, 78.0, 180, value="PTSM 0,5/4-HH-2,5-THR", dnp=True))
    # --- GPIO breakout (2 x 6 under the header) and prototyping field, bottom right
    custom.append(B.place("J9", shadow_column(B, BREAKOUT), BREAKOUT_X, 8.37, 0, value="GPIO breakout"))
    custom.append(B.place("PF1", pad_array(B, "Proto_9x4", 9, 4, square_first=False), 34.0, 74.5, 0, value="proto"))

    # ---------------------------------------------------------------- nets
    # header; the five outer-column grounds are tied by a pre-routed bus along the board edge,
    # since the router cannot reach them through the column
    for p in PI_GND:
        B.connect("J5", p, "GND")
    gnd_y = [8.37 + ((p // 2) - 1) * PITCH for p in PI_GND]
    B.track("GND", GND_BUS_X, min(gnd_y), GND_BUS_X, max(gnd_y))
    for y in gnd_y:
        B.track("GND", GND_BUS_X, y, 2.23, y)
    for p in PI_5V:
        B.connect("J5", p, "+5V")
    for p in PI_3V3:
        B.connect("J5", p, "3V3")
    B.connect("J5", 3, "SDA")
    B.connect("J5", 5, "SCL")
    B.connect("J5", 7, "GPIO4")
    # channels
    for n, (name, plug, pos, bcm, pin) in enumerate(CHANNELS, start=1):
        k, c = (n - 1) // 4 + 1, (n - 1) % 4 + 1
        A, K, E, C = 2 * c - 1, 2 * c, 17 - 2 * c, 18 - 2 * c
        B.connect(f"U{k}", A, "VS")
        B.connect(f"U{k}", K, f"K{n}")
        B.connect(f"R{n}", 1, f"K{n}")
        B.connect(f"R{n}", 2, f"S_{name}")
        B.connect(f"U{k}", E, "GND")
        B.connect(f"U{k}", C, f"GPIO{bcm}")
        B.connect("J5", pin, f"GPIO{bcm}")
        if plug:
            B.connect(plug, pos, f"S_{name}")
    for plug in PLUG_X:
        B.connect(plug, 4, "COM")
    B.connect("J8", 1, "S_SP-C")
    B.connect("J8", 2, "S_SP-E")
    B.connect("J8", 3, "COM")
    # 24 VAC in on J4.1 (R) and J4.2 (C), PTC in the R leg, MOV across, full-wave bridge
    B.connect("J4", 1, "ACR")
    B.connect("J4", 2, "ACC")
    B.connect("F1", 1, "ACR")
    B.connect("F1", 2, "ACF")
    B.connect("RV1", 1, "ACF")
    B.connect("RV1", 2, "ACC")
    # D_DO-41 footprint: pad 1 = cathode, pad 2 = anode
    B.connect("D1", 2, "ACF"); B.connect("D1", 1, "VS")
    B.connect("D2", 2, "ACC"); B.connect("D2", 1, "VS")
    B.connect("D3", 2, "COM"); B.connect("D3", 1, "ACF")
    B.connect("D4", 2, "COM"); B.connect("D4", 1, "ACC")
    B.connect("C1", 1, "VS")
    B.connect("C1", 2, "COM")
    B.connect("TP1", 1, "VS")
    B.connect("TP2", 1, "COM")
    B.connect("TP3", 1, "GND")
    # links
    for pos, net in enumerate(("3V3", "SDA", "SCL", "GPIO4", "GND"), start=1):
        B.connect("J6", pos, net)
    for pos, net in enumerate(("VS", "COM", "+5V", "GND"), start=1):
        B.connect("J7", pos, net)
    # breakout
    for i, entry in enumerate(BREAKOUT, start=1):
        if entry is None:
            continue
        label, pin, netname = entry
        B.connect("J9", i, netname)
        B.connect("J5", pin, netname)
        B.text(label, BREAKOUT_X + 1.35, 8.37 + (i - 1) * PITCH, size=0.8, rot=90)

    # ---------------------------------------------------------------- silkscreen
    for j, xc in PLUG_X.items():
        names = [c[0] for c in CHANNELS if c[1] == j]
        B.text(j, xc, 13.2, size=0.8, bold=True)
    for name, plug, pos, bcm, pin in CHANNELS:
        if plug:
            B.text(name, PLUG_X[plug] + (pos - 2.5) * 2.5, 12.2, size=0.8, rot=90)
    for j, xc in PLUG_X.items():
        B.text("COM", xc + 1.5 * 2.5, 12.2, size=0.8, rot=90)
    B.text("24VAC", PLUG_X["J4"] - 1.5 * 2.5, 12.6, size=0.8, rot=90)
    B.text("pivac INT rev A -- 24 VAC in on J4.1/J4.2 -- COM is the sense return, never Pi GND",
           31.0, 63.4, size=0.8)
    B.text("Pi GND", 7.6, 59.5, size=0.8, rot=90)
    B.text("LINK 3V3 SDA SCL G4 GND", 13.0, 79.6, size=0.8, layer="B.SilkS")
    B.text("PWR VS COM 5V GND", 27.5, 79.6, size=0.8, layer="B.SilkS")
    B.text("1", 3.5, 6.5, size=0.8)
    B.text("2", 1.0, 6.5, size=0.8)
    B.text("39", 3.5, 58.5, size=0.8)

    B.fill()
    B.save()
    save_pretty(custom)
    return B


# --------------------------------------------------------------------------- EXT board
def build_ext():
    out = os.path.join(HERE, "ext-board")
    os.makedirs(out, exist_ok=True)
    B = Board(os.path.join(out, "ext-board.kicad_pcb"), 38.5, 85.0)
    custom = []
    for (y0, y1) in BANDS_Y:
        B.rect_keepout(0, y0, 38.5, y1, name="housing rib")
        B.line(0, y0, 38.5, y0, "B.SilkS", 0.1)
        B.line(0, y1, 38.5, y1, "B.SilkS", 0.1)
    # riser field: keep pads out of the power riser's terminal area (cols 1-5, rows 11-23)
    B.rect_keepout(0, 25.0, 13.6, 58.5, layers=("F.Cu", "B.Cu"), name="power riser field")

    # probe sockets H1..H3 at row 2, entry toward the row-1 edge
    for ref, xc in (("H1", 7.57), ("H2", 20.27), ("H3", 32.97)):
        custom.append(B.place(ref, ptsm_hh(B, 3), xc, 3.7, 0, value="PTSM 0,5/3-HH-2,5-THR"))
    # DS2482 x2 (U2 not fitted), decoupling, rollback pull-up (not fitted), solder jumpers
    B.lib("U1", "Package_SO", "SOIC-8_3.9x4.9mm_P1.27mm", 11.0, 12.5, 0, value="DS2482-100")
    B.lib("C1", "Capacitor_THT", "C_Rect_L7.0mm_W2.5mm_P5.00mm", 20.5, 11.0, 0, value="100n")
    B.lib("U2", "Package_SO", "SOIC-8_3.9x4.9mm_P1.27mm", 30.0, 30.0, 0, value="DS2482-100 (0x19)", dnp=True)
    B.lib("C2", "Capacitor_THT", "C_Rect_L7.0mm_W2.5mm_P5.00mm", 30.0, 37.5, 0, value="100n", dnp=True)
    B.lib("R1", "Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 22.0, 16.3, 0,
          value="2k2 rollback", dnp=True)
    B.lib("JP1", "Jumper", "SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm", 34.5, 14.5, 90, value="GPIO4->DATA")
    B.lib("JP2", "Jumper", "SolderJumper-3_P1.3mm_Open_RoundedPad1.0x1.5mm", 22.0, 29.0, 0, value="H3: bus/U2")
    # link header at row 18, entry from the row-19 side (+y), as built
    custom.append(B.place("J1", ptsm_hh(B, 5), 25.35, 44.34, 180, value="PTSM 0,5/5-HH-2,5-THR"))
    # prototyping field, lower field
    custom.append(B.place("PF1", pad_array(B, "Proto_11x6", 11, 6, square_first=False), 5.3, 68.0, 0, value="proto"))
    custom.append(B.place("J2", pad_array(B, "Pads_1x3", 1, 3), 35.5, 68.0, 0, value="VCC DATA GND"))

    # nets: DS2482-100 SO-8: 1 VCC, 2 IO, 3 GND, 4 SCL, 5 SDA, 6 PCTLZ, 7 AD1, 8 AD0
    for ref, io in (("U1", "DATA"), ("U2", "DATA_H3")):
        B.connect(ref, 1, "VCC")
        B.connect(ref, 2, io)
        B.connect(ref, 3, "GND")
        B.connect(ref, 4, "SCL")
        B.connect(ref, 5, "SDA")
        B.connect(ref, 7, "GND")
    B.connect("U1", 8, "GND")      # 0x18
    B.connect("U2", 8, "VCC")      # 0x19
    B.connect("C1", 1, "VCC"); B.connect("C1", 2, "GND")
    B.connect("C2", 1, "VCC"); B.connect("C2", 2, "GND")
    for ref in ("H1", "H2"):
        B.connect(ref, 1, "VCC"); B.connect(ref, 2, "DATA"); B.connect(ref, 3, "GND")
    B.connect("H3", 1, "VCC"); B.connect("H3", 2, "H3_DATA"); B.connect("H3", 3, "GND")
    B.connect("JP2", 1, "DATA"); B.connect("JP2", 2, "H3_DATA"); B.connect("JP2", 3, "DATA_H3")
    B.connect("R1", 1, "VCC"); B.connect("R1", 2, "DATA")
    B.connect("JP1", 1, "GPIO4"); B.connect("JP1", 2, "DATA")
    for pos, net in enumerate(("VCC", "SDA", "SCL", "GPIO4", "GND"), start=1):
        B.connect("J1", pos, net)
    B.connect("J2", 1, "VCC"); B.connect("J2", 2, "DATA"); B.connect("J2", 3, "GND")

    B.text("H1 trunk", 5.5, 8.8, size=0.8)
    B.text("H2 spare", 20.27, 9.0, size=0.8)
    B.text("H3 spare/0x19", 32.97, 9.0, size=0.8)
    B.text("V D G", 7.57, 7.2, size=0.8)
    B.text("pivac EXT rev A", 19.25, 24.0, size=0.8)
    B.text("LINK 1=3V3 2=SDA 3=SCL 4=GPIO4 5=GND", 19.25, 51.0, size=0.8)
    B.text("power riser field - keep clear", 6.8, 41.0, size=0.8, rot=90)
    B.save()
    save_pretty(custom)
    return B


if __name__ == "__main__":
    which = sys.argv[1:] or ["int", "ext"]
    if "int" in which:
        build_int()
        print("wrote int-board")
    if "ext" in which:
        build_ext()
        print("wrote ext-board")
