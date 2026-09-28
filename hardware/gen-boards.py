#!/usr/bin/env python3
"""Generate the KiCad boards that replace the two Phoenix RPI-BC perfboards.

Run with KiCad's own Python so that ``pcbnew`` imports:

    ~/Applications/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
        hardware/gen-boards.py

Writes ``hardware/int-board/int-board.kicad_pcb`` and ``hardware/ext-board/ext-board.kicad_pcb``
(rev B), and with the argument ``extc`` the rev C EXT board in ``hardware/extc-board``, each
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
    def __init__(self, path, width, length, power_clearance=0.25):
        self.path = path
        self.width, self.length = width, length
        self.power_clearance = power_clearance
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
        power.SetClearance(FromMM(self.power_clearance))
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
        t.SetLocked(True)   # exported to the router as fixed wiring, never re-routed or trimmed
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

    def text(self, s, x, y, layer="F.SilkS", size=1.0, rot=0, bold=False, left=False):
        t = pcbnew.PCB_TEXT(self.board)
        t.SetText(s)
        t.SetPosition(mm(x, y))
        if left:
            t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
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


def _smd(fp, number, x, y, w, h):
    p = pcbnew.PAD(fp)
    p.SetNumber(str(number))
    p.SetShape(pcbnew.PAD_SHAPE_RECT)
    p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    p.SetSize(VECTOR2I(FromMM(w), FromMM(h)))
    p.SetLayerSet(pcbnew.PAD.SMDMask())
    p.SetPosition(mm(x, y))
    fp.Add(p)
    return p


def _peg(fp, x, y, drill):
    p = pcbnew.PAD(fp)
    p.SetNumber("")
    p.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
    p.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    p.SetSize(VECTOR2I(FromMM(drill), FromMM(drill)))
    p.SetDrillSize(VECTOR2I(FromMM(drill), FromMM(drill)))
    p.SetLayerSet(pcbnew.PAD.UnplatedHoleMask())
    p.SetPosition(mm(x, y))
    fp.Add(p)
    return p


def ptsm_hh_smd(board, n):
    """Phoenix PTSM 0,5/n-HH-2,5-SMD: horizontal surface-mount header, entry toward -y.

    Origin at the middle of the pin row on the entry face, which the caller puts on the board
    edge. Body (a + 4.2) wide, 7.5 deep and 5.0 tall, a = (n-1)*2.5. Pad pattern from Phoenix's
    drawing for 1778780 and its STEP model: signal pads 1.2 x 3.2 behind the body (y 6.6 to
    9.8), two anchor pads 2.2 x 5.6 whose inner edge is 1.55 from the outer signal pad's edge
    (y 1.2 to 6.8, centred on the anchor's foot at y 1.5 to 6.5), two 1.1 mm unplated holes for the pegs, 1.1 outside the outer pins at
    y 2.85. The side walls carry the window a latching -PL- plug's tooth enters."""
    fp = pcbnew.FOOTPRINT(board.board)
    fp.SetFPID(pcbnew.LIB_ID("pivac", f"PTSM_0.5_{n}-HH-2.5-SMD"))
    fp.SetLibDescription(f"Phoenix Contact PTSM 0,5/{n}-HH-2,5-SMD horizontal header, surface mount")
    fp.SetAttributes(pcbnew.FP_SMD)
    a = (n - 1) * 2.5
    for i in range(n):
        _smd(fp, i + 1, -a / 2 + i * 2.5, 8.2, 1.2, 3.2)
    for sgn in (-1, 1):
        _smd(fp, "MP", sgn * (a / 2 + 3.25), 4.0, 2.2, 5.6)
        _peg(fp, sgn * (a / 2 + 1.1), 2.85, 1.1)
    hw = a / 2 + 2.1
    _fp_rect(fp, -hw, 0, hw, 7.5, pcbnew.F_Fab, 0.1)
    _fp_rect(fp, -hw, 0.15, hw, 7.5, pcbnew.F_SilkS, 0.12)
    _fp_rect(fp, -a / 2 - 4.5, 0.05, a / 2 + 4.5, 9.95, pcbnew.F_CrtYd, 0.05)
    fp.Reference().SetPosition(mm(0, 11.0))
    fp.Value().SetPosition(mm(0, 12.2))
    return fp


def ptsm_hv_smd(board, n):
    """Phoenix PTSM 0,5/n-HV-2,5-SMD: vertical surface-mount header, entry upward.

    Origin at the middle of the pin row on the long side the leads leave by; the body runs
    5.0 toward +y and the leads 2.1 toward -y. Body (a + 4.2) wide and 7.5 tall. From the
    STEP model of 1778696: lead feet y -2.1 to 1.85, anchor feet 2.4 to 4.05 outside the outer
    pins over the body's whole depth, pegs 1.4 outside the outer pins at y 0.4. The peg holes
    are 1.0 mm and the anchor pads 2.1 wide so the two stay 0.35 mm apart."""
    fp = pcbnew.FOOTPRINT(board.board)
    fp.SetFPID(pcbnew.LIB_ID("pivac", f"PTSM_0.5_{n}-HV-2.5-SMD"))
    fp.SetLibDescription(f"Phoenix Contact PTSM 0,5/{n}-HV-2,5-SMD vertical header, surface mount")
    fp.SetAttributes(pcbnew.FP_SMD)
    a = (n - 1) * 2.5
    for i in range(n):
        _smd(fp, i + 1, -a / 2 + i * 2.5, -0.2, 1.2, 4.4)
    for sgn in (-1, 1):
        _smd(fp, "MP", sgn * (a / 2 + 3.35), 2.5, 2.1, 5.6)
        _peg(fp, sgn * (a / 2 + 1.4), 0.4, 1.0)
    hw = a / 2 + 2.1
    _fp_rect(fp, -hw, 0, hw, 5.0, pcbnew.F_Fab, 0.1)
    _fp_rect(fp, -hw, 0, hw, 5.0, pcbnew.F_SilkS, 0.12)
    _fp_rect(fp, -a / 2 - 4.55, -2.55, a / 2 + 4.55, 5.45, pcbnew.F_CrtYd, 0.05)
    fp.Reference().SetPosition(mm(0, 6.6))
    fp.Value().SetPosition(mm(0, 7.8))
    return fp


def pad_array(board, name, cols, rows, pitch=PITCH, size=1.6, drill=1.0, square_first=True, margin=None):
    """A plated-hole prototyping field or breakout row, pads numbered row-major from 1."""
    fp = pcbnew.FOOTPRINT(board.board)
    fp.SetFPID(pcbnew.LIB_ID("pivac", name))
    n = 1
    for j in range(rows):
        for i in range(cols):
            _pad(fp, n, i * pitch, j * pitch, size, drill,
                 pcbnew.PAD_SHAPE_ROUNDRECT if (n == 1 and square_first) else pcbnew.PAD_SHAPE_CIRCLE)
            n += 1
    m = pitch / 2 if margin is None else margin
    _fp_rect(fp, -m, -m, (cols - 1) * pitch + m, (rows - 1) * pitch + m, pcbnew.F_CrtYd, 0.05)
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


def radial_flat(board, name, pitch, dia, thick, drill=1.0, size=1.8):
    """A radial disc (PTC, MOV) laid flat on the board with its leads bent 90 degrees: pads
    at the pitch, the disc extending toward -y from a 1 mm lead bend. Height on the board is
    the disc thickness plus the bend, about thick + 1.5 mm, against the 8 mm cover limit."""
    fp = pcbnew.FOOTPRINT(board.board)
    fp.SetFPID(pcbnew.LIB_ID("pivac", name))
    _pad(fp, 1, -pitch / 2, 0, size, drill, pcbnew.PAD_SHAPE_ROUNDRECT)
    _pad(fp, 2, pitch / 2, 0, size, drill)
    _fp_rect(fp, -dia / 2, -dia - 1.0, dia / 2, -1.0, pcbnew.F_SilkS)
    _fp_rect(fp, -dia / 2, -dia - 1.0, dia / 2, -1.0, pcbnew.F_Fab, 0.1)
    _fp_rect(fp, -dia / 2 - 0.25, -dia - 1.25, dia / 2 + 0.25, 1.2, pcbnew.F_CrtYd, 0.05)
    _fp_text(fp, "flat, %.0f mm high" % (thick + 1.5), 0, -dia / 2 - 1.0, pcbnew.F_Fab, 0.6)
    fp.Reference().SetPosition(mm(0, -dia - 2.2))
    fp.Value().SetPosition(mm(0, 2.4))
    return fp


def sip8_converter(board):
    """Traco TMR 12WI SIP-8: pins 1, 2, 3, 6, 7, 8 at 2.54 mm (pins 4 and 5 do not exist on the
    single-output part), 0.5 x 0.4 mm posts in 1.0 mm holes. Body 22.0 x 9.6 with the pin row
    3.54 mm from one long face and 6.06 from the other; 12.0 mm tall. Origin at pin 1. Pins 9
    and 12 (case) and 10 and 11 (stand-offs) sit on the long faces at 3.59 and 14.19 mm from pin
    1 and get no holes (Traco: not connected to any circuit); the shanks are clipped."""
    fp = pcbnew.FOOTPRINT(board.board)
    fp.SetFPID(pcbnew.LIB_ID("pivac", "TMR12WI_SIP-8"))
    fp.SetLibDescription("Traco TMR 12WI isolated DC/DC converter, SIP-8, 22 x 9.6 x 12 mm")
    for n in (1, 2, 3, 6, 7, 8):
        _pad(fp, n, (n - 1) * PITCH, 0, 1.8, 1.0, pcbnew.PAD_SHAPE_ROUNDRECT if n == 1 else pcbnew.PAD_SHAPE_CIRCLE)
    x0, x1 = -2.11, 7 * PITCH + 2.11
    _fp_rect(fp, x0, -3.54, x1, 6.06, pcbnew.F_Fab, 0.1)
    _fp_rect(fp, x0 - 0.1, -3.64, x1 + 0.1, 6.16, pcbnew.F_SilkS, 0.12)
    _fp_rect(fp, x0 - 0.25, -3.79, x1 + 0.25, 6.31, pcbnew.F_CrtYd, 0.05)
    for n, name in ((1, "-Vin"), (2, "+Vin"), (3, "Rmt"), (6, "+Vo"), (7, "-Vo"), (8, "NC")):
        _fp_text(fp, name, (n - 1) * PITCH, -1.7, pcbnew.F_SilkS, 0.6)
        _fp_text(fp, str(n), (n - 1) * PITCH, 1.7, pcbnew.F_SilkS, 0.6)
    _fp_text(fp, "TMR 12-4811WI  12 mm tall", 7 * PITCH / 2, 3.2, pcbnew.F_Fab, 0.7)
    fp.Reference().SetPosition(mm(7 * PITCH / 2, 4.6))
    fp.Value().SetPosition(mm(7 * PITCH / 2, 7.4))
    return fp


def radial_disc(board, name, pitch, dia, thick, drill=1.0, size=1.8):
    """A radial disc (PTC) standing on its leads: pads at the pitch, the disc's edge on the board,
    dia wide and thick deep, dia tall."""
    fp = pcbnew.FOOTPRINT(board.board)
    fp.SetFPID(pcbnew.LIB_ID("pivac", name))
    _pad(fp, 1, -pitch / 2, 0, size, drill, pcbnew.PAD_SHAPE_ROUNDRECT)
    _pad(fp, 2, pitch / 2, 0, size, drill)
    _fp_rect(fp, -dia / 2, -thick / 2, dia / 2, thick / 2, pcbnew.F_SilkS)
    _fp_rect(fp, -dia / 2, -thick / 2, dia / 2, thick / 2, pcbnew.F_Fab, 0.1)
    _fp_rect(fp, -dia / 2 - 0.25, -thick / 2 - 0.25, dia / 2 + 0.25, thick / 2 + 0.25, pcbnew.F_CrtYd, 0.05)
    _fp_text(fp, "standing, %.0f mm tall" % dia, 0, -thick / 2 - 1.0, pcbnew.F_Fab, 0.6)
    fp.Reference().SetPosition(mm(0, thick / 2 + 1.2))
    fp.Value().SetPosition(mm(0, thick / 2 + 2.4))
    return fp


def slot_pair(board, gap=3.8, w=1.2, l=2.4):
    """Two unplated slots for a cable tie, l long along y, gap apart along x."""
    fp = pcbnew.FOOTPRINT(board.board)
    fp.SetFPID(pcbnew.LIB_ID("pivac", "TieSlots_2x"))
    for i, x in enumerate((-gap / 2, gap / 2), start=1):
        p = pcbnew.PAD(fp)
        p.SetNumber("")
        p.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
        p.SetShape(pcbnew.PAD_SHAPE_OVAL)
        p.SetDrillShape(pcbnew.PAD_DRILL_SHAPE_OBLONG)
        p.SetSize(VECTOR2I(FromMM(w), FromMM(l)))
        p.SetDrillSize(VECTOR2I(FromMM(w), FromMM(l)))
        p.SetLayerSet(pcbnew.PAD.UnplatedHoleMask())
        p.SetPosition(mm(x, 0))
        fp.Add(p)
    _fp_rect(fp, -gap / 2 - w, -l / 2 - 0.5, gap / 2 + w, l / 2 + 0.5, pcbnew.F_CrtYd, 0.05)
    _fp_text(fp, "tie", 0, l / 2 + 1.2, pcbnew.F_SilkS, 0.6)
    fp.Reference().SetPosition(mm(0, -l / 2 - 1.2))
    fp.Value().SetPosition(mm(0, l / 2 + 2.4))
    return fp


def title_block(B, cx, cy, scale, board_name, stacked=False, rev="B"):
    """DL monogram in a ring, name and version on F.SilkS. Geometry from hardware/dl-monogram.svg
    (units mm, ring at the origin): the letters are 0.8 mm strokes drawn here as silkscreen
    segments with round ends, so the mark is a footprint-free set of board graphics."""
    import math
    s = scale
    ring = pcbnew.PCB_SHAPE(B.board)
    ring.SetShape(pcbnew.SHAPE_T_CIRCLE)
    ring.SetCenter(mm(cx, cy))
    ring.SetEnd(mm(cx + 4.425 * s, cy))
    ring.SetLayer(pcbnew.F_SilkS)
    ring.SetWidth(FromMM(0.35 * s))
    ring.SetFilled(False)
    B.board.Add(ring)
    w = 0.8 * s
    def seg(x0, y0, x1, y1):
        B.line(cx + x0 * s, cy + y0 * s, cx + x1 * s, cy + y1 * s, "F.SilkS", w)
    # D: stem, top and bottom bars, bowl of radius 1.6 about (-1.55, -0.75)
    seg(-1.95, -2.35, -1.95, 0.85)
    seg(-1.95, -2.35, -1.55, -2.35)
    seg(-1.95, 0.85, -1.55, 0.85)
    pts = [(-1.55 + 1.6 * math.cos(a), -0.75 + 1.6 * math.sin(a)) for a in
           [math.radians(-90 + k * 15) for k in range(13)]]
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        seg(xa, ya, xb, yb)
    # L: stem and foot
    seg(1.2, -1.07, 1.2, 2.13)
    seg(1.2, 2.13, 2.63, 2.13)
    if stacked:
        # ring above two centred lines, for the EXT board's narrow field
        B.text("PIVAC MONITORING", cx, cy + 4.425 * s + 1.6, size=0.85, bold=True)
        B.text("BOARD  v1.0", cx, cy + 4.425 * s + 3.1, size=0.8)
        B.text("Rev " + rev + "  " + board_name, cx, cy + 4.425 * s + 4.6, size=0.8)
        return
    # KiCad's stroke font runs about 1.25 mm per character at size 1.45, so the name is 27 mm
    # long: the block is ring (8.85) + gap (1.6) + 27 wide and the caller centres it
    tx = cx + (4.425 + 1.6) * s
    B.text("PIVAC MONITORING BOARD", tx, cy - 0.8 * s, size=1.45 * s, bold=True, left=True)
    B.line(tx, cy + 0.15 * s, tx + 27.0 * s, cy + 0.15 * s, "F.SilkS", 0.15)
    B.text("v1.0  Rev " + rev + "  " + board_name, tx, cy + 2.0 * s, size=1.05 * s, left=True)


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
from gen_tables import CHANNELS, PI_GND, PI_5V, PI_3V3, BREAKOUT, BREAKOUT_X, PLUG_X, PLUG_Y, GND_BUS_X  # noqa: E402


def build_int():
    out = os.path.join(HERE, "int-board")
    os.makedirs(out, exist_ok=True)
    B = Board(os.path.join(out, "int-board.kicad_pcb"), 59.0, 85.0)
    custom = []

    # restricted areas (solder side): the two bands, the column-20 strip and its bulges
    B.rect_keepout(12.99, BANDS_Y[0][0], 59.0, BANDS_Y[0][1], name="housing rib upper")
    B.rect_keepout(6.64, BANDS_Y[1][0], 59.0, BANDS_Y[1][1], name="housing rib lower")
    B.rect_keepout(48.85, 22.31, 50.75, 61.29, name="housing strip col 20")
    # no vias within 0.8 mm of the outline on either layer: the DSN carries no edge clearance,
    # and the router put a COM via 0.28 mm from the edge against the 0.3 mm rule
    for x0, y0, x1, y1 in ((0, 0, 0.8, 85), (58.2, 0, 59, 85), (0, 0, 59, 0.8), (0, 84.2, 59, 85)):
        B.rect_keepout(x0, y0, x1, y1, layers=("F.Cu", "B.Cu"), name="edge via keepout",
                       pads=False, footprints=False, tracks=False, vias=True, pour=False)
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
    j5 = B.place("J5", pi_header(B), 4.77, 8.37, 0, back=True, value="Pi 40-pin socket")
    custom.append(j5)
    j5.Reference().SetVisible(False)   # the socket body covers it; the pin numbers on the front say what it is
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
            ic.SetPosition(mm(14.0 - pcbnew.ToMM(p1.x), yc + 3.81 - pcbnew.ToMM(p1.y)))
            x8, y8 = B.pad_xy(f"U{k}", 8)
            x16, y16 = B.pad_xy(f"U{k}", 16)
            if x8 > 20 and abs(y8 - (yc + 3.81)) < 0.01 and abs(y16 - (yc - 3.81)) < 0.01:
                break
        else:
            raise SystemExit("could not orient the DIP")
    # --- LED resistors, vertical, five columns right of the ICs, three rows
    # 4.0 mm pitch (rev A's 3.3 was tight to populate); the last column's pads stop at x 48.0,
    # short of the housing bulges' rule areas that begin at 48.17
    res_x = [35.2, 39.2, 43.2, 47.2]
    n = 0
    for k, yc in ic_y.items():
        for i in range(4):
            n += 1
            r = B.lib(f"R{n}", "Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
                      res_x[i], yc - 5.08, 270, value="12k 1/4W")
            # reference on the body, along it: the columns sit 3.3 mm apart and leave no room beside
            r.Reference().SetPosition(mm(res_x[i], yc - 5.08)); r.Reference().SetTextAngleDegrees(90)
            r.Reference().SetTextSize(VECTOR2I(FromMM(0.7), FromMM(0.7)))
    # --- link header: JST GH SM07B-GHS-TB, side entry, inside the housing's slot on the right
    # edge (y 26-59, measured on the housing), entry facing +x with its face 0.6 mm inside the
    # edge like rev A's PTSM J6. Seven ways: the I2C link plus VS and COM, which now arrive from
    # the EXT board's rectifier. Placed by trying the four rotations until the pad row is inboard
    # of the mounting tabs (entry toward +x), then slid so the courtyard's right edge is at 58.4.
    j6 = B.lib("J6", "Connector_JST", "JST_GH_SM07B-GHS-TB_1x07-1MP_P1.25mm_Horizontal", 50, 34.5, 0,
               value="GH SM07B link to EXT")
    for rot in (0, 90, 180, 270):
        j6.SetOrientationDegrees(rot)
        j6.SetPosition(mm(50, 34.5))
        p1 = j6.FindPadByNumber("1").GetPosition(); p7 = j6.FindPadByNumber("7").GetPosition()
        mx = max(pcbnew.ToMM(p.GetPosition().x) for p in j6.Pads() if p.GetNumber() == "MP")
        if abs(pcbnew.ToMM(p1.x) - pcbnew.ToMM(p7.x)) < 0.01 and pcbnew.ToMM(p1.x) < mx:
            break   # pins along y, pad row inboard of the tabs: the entry faces +x; pin 1 lands at the bottom
    else:
        raise SystemExit("could not orient J6")
    bb = j6.GetCourtyard(pcbnew.F_CrtYd).BBox()
    j6.SetPosition(mm(50 + (58.4 - pcbnew.ToMM(bb.GetRight())), 34.5))
    bb = j6.GetCourtyard(pcbnew.F_CrtYd).BBox()
    if pcbnew.ToMM(bb.GetTop()) < 26.0 or pcbnew.ToMM(bb.GetBottom()) > 59.0 or pcbnew.ToMM(bb.GetLeft()) < 49.5:
        raise SystemExit("J6 outside the housing slot")
    j6.Reference().SetPosition(mm(55.2, pcbnew.ToMM(bb.GetBottom()) + 1.3))   # below the header, clear of the legend
    # --- test points
    for ref, x, val in (("TP1", 40.0, "VS"), ("TP2", 43.0, "COM"), ("TP3", 46.0, "GND")):
        custom.append(B.place(ref, pad_array(B, "TestPad", 1, 1, size=1.8, drill=1.0, square_first=False), x, 81.0, 0, value=val))
    # --- GPIO breakout (2 x 6 under the header) and prototyping field, bottom right
    j9 = B.place("J9", shadow_column(B, BREAKOUT), BREAKOUT_X, 8.37, 0, value="GPIO breakout")
    custom.append(j9)
    j9.Reference().SetPosition(mm(BREAKOUT_X, 11.7))   # above the column's first pad (row 3)

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
    B.connect("TP1", 1, "VS")
    B.connect("TP2", 1, "COM")
    B.connect("TP3", 1, "GND")
    # links
    for pos, net in enumerate(("3V3", "SDA", "SCL", "GPIO4", "GND", "VS", "COM"), start=1):
        B.connect("J6", pos, net)
    # breakout
    for i, entry in enumerate(BREAKOUT, start=1):
        if entry is None:
            continue
        label, pin, netname = entry
        B.connect("J9", i, netname)
        B.connect("J5", pin, netname)
        B.text(label, BREAKOUT_X + 1.35, 8.37 + (i - 1) * PITCH, size=0.8, rot=90)
    # GPIO8, header pin 24 in the outer column to its breakout pad on row 14, must thread the
    # column twice through 0.84 mm gaps; the router manages it only sometimes, so it is laid
    # by hand: down between the columns, across between pins 25 and 27, then onto the pad.
    x24, y24 = B.pad_xy("J5", 24); x14, y14 = B.pad_xy("J9", 14)
    B.track("GPIO8", x24, y24, 3.5, y24 + 1.27, width=0.25)
    B.track("GPIO8", 3.5, y24 + 1.27, 3.5, y14 - 1.27, width=0.25)
    B.track("GPIO8", 3.5, y14 - 1.27, x14, y14 - 1.27, width=0.25)
    B.track("GPIO8", x14, y14 - 1.27, x14, y14, width=0.25)
    # GPIO6 and GPIO24 were the two connections Freerouting left open with the sockets at x 14:
    # GPIO6 runs straight out of pin 31 along row 16 of the shadow column, which has no pad,
    # then up the strip left of the socket pins; GPIO24 escapes the outer column between pins
    # 17 and 19 and crosses the shadow column between rows 9 and 10.
    # GPIO6 on the front copper, GPIO24 on the back: their verticals overlap in y and any two
    # horizontals from the header would cross on one layer. Every end is a through-hole pad.
    x31, y31 = B.pad_xy("J5", 31); xu2, yu2 = B.pad_xy("U2", 16)
    B.track("GPIO6", x31, y31, 12.3, y31, width=0.25)
    B.track("GPIO6", 12.3, y31, 12.3, yu2, width=0.25)
    B.track("GPIO6", 12.3, yu2, xu2, yu2, width=0.25)
    x18, y18 = B.pad_xy("J5", 18); xu3, yu3 = B.pad_xy("U3", 16)
    ym = y18 + 1.27
    B.track("GPIO24", x18, y18, 3.5, ym, width=0.25, layer="B.Cu")
    B.track("GPIO24", 3.5, ym, 12.3, ym, width=0.25, layer="B.Cu")
    B.track("GPIO24", 12.3, ym, 12.3, yu3, width=0.25, layer="B.Cu")
    B.track("GPIO24", 12.3, yu3, xu3, yu3, width=0.25, layer="B.Cu")
    # GND to the link header: Freerouting left J6.5 open on most runs, so it is laid from the
    # pad west out of the header, down the strip inside the right edge and across to TP3 (GND)
    x5, y5 = B.pad_xy("J6", 5); xt, yt = B.pad_xy("TP3", 1)
    B.track("GND", x5, y5, 51.0, y5)
    B.track("GND", 51.0, y5, 51.0, 78.0)
    B.track("GND", 51.0, 78.0, xt, 78.0)
    B.track("GND", xt, 78.0, xt, yt)

    # ---------------------------------------------------------------- silkscreen
    for j, xc in PLUG_X.items():
        B.text(j, xc, 15.7, size=0.8, bold=True)
    for name, plug, pos, bcm, pin in CHANNELS:
        if plug:
            B.text(name, PLUG_X[plug] + (pos - 2.5) * 2.5, 12.2, size=0.8, rot=90)
    for j, xc in PLUG_X.items():
        B.text("COM", xc + 1.5 * 2.5, 12.2, size=0.8, rot=90)
    B.text("pivac INT rev B -- VS/COM in on J6.6/J6.7 -- COM never meets Pi GND", 31.0, 63.4, size=0.8)
    B.text("Pi GND", 7.6, 59.5, size=0.8, rot=90)
    B.text("no parts here: the Pi's USB stacks sit under this field", 29.5, 68.5, size=0.8)
    # J6 is surface-mount, so its pin legend goes on the front beside the pads, not on the back
    B.text("J6 LINK 1=3V3 2=SDA 3=SCL 4=G4 5=GND 6=VS 7=COM", 50.4, 34.5, size=0.7, rot=90)
    title_block(B, 15.2, 75.4, 1.0, "INT")     # 37.5 mm wide, centred on the 59 mm board
    B.text("1", 4.77, 6.3, size=0.8)
    B.text("2", 2.23, 6.3, size=0.8)
    B.text("39", 4.77, 58.7, size=0.8)
    B.text("40", 2.23, 58.7, size=0.8)

    B.fill()
    B.save()
    save_pretty(custom)
    return B


# --------------------------------------------------------------------------- EXT board
def build_ext():
    out = os.path.join(HERE, "ext-board")
    os.makedirs(out, exist_ok=True)
    # the mains side (VS, COM, 24 VAC) keeps 0.5 mm from everything else on this board; the
    # GH and XH pads at 1.25 and 2.5 mm pitch are the limit, and both sides are SELV
    B = Board(os.path.join(out, "ext-board.kicad_pcb"), 38.5, 85.0, power_clearance=0.5)
    custom = []
    for (y0, y1) in BANDS_Y:
        B.rect_keepout(0, y0, 38.5, y1, name="housing rib")
        B.line(0, y0, 38.5, y0, "B.SilkS", 0.1)
        B.line(0, y1, 38.5, y1, "B.SilkS", 0.1)
    # no vias within 0.8 mm of the outline (see the INT board)
    for x0, y0, x1, y1 in ((0, 0, 0.8, 85), (37.7, 0, 38.5, 85), (0, 0, 38.5, 0.8), (0, 84.2, 38.5, 85)):
        B.rect_keepout(x0, y0, x1, y1, layers=("F.Cu", "B.Cu"), name="edge via keepout",
                       pads=False, footprints=False, tracks=False, vias=True, pour=False)
    # probe sockets H1..H3 at row 2, entry toward the row-1 edge (face 1.7 mm outside it)
    for ref, xc in (("H1", 7.57), ("H2", 20.27), ("H3", 32.97)):
        custom.append(B.place(ref, ptsm_hh(B, 3), xc, 3.7, 0, value="PTSM 0,5/3-HH-2,5-THR"))
    # I2C and 1-wire parts in one row between the sockets and the upper rib: U1 with C1 and
    # JP1 under H1, R1 and JP2 in the middle, C2 and U2 under H3
    u1 = B.lib("U1", "Package_SO", "SOIC-8_3.9x4.9mm_P1.27mm", 4.5, 12.5, 0, value="DS2482-100")
    u1.Reference().SetPosition(mm(4.5, 16.3))
    ec1 = B.lib("C1", "Capacitor_THT", "C_Rect_L7.0mm_W2.5mm_P5.00mm", 9.7, 11.0, 0, value="100n")
    ec1.Reference().SetPosition(mm(12.2, 8.9))
    B.lib("JP1", "Jumper", "SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm", 11.3, 14.7, 90, value="GPIO4->DATA")
    r1 = B.lib("R1", "Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 17.82, 10.8, 0,
               value="2k2 rollback", dnp=True)
    r1.Reference().SetPosition(mm(18.6, 13.3))   # under R1's left end, clear of JP2's reference
    B.lib("JP2", "Jumper", "SolderJumper-3_P1.3mm_Open_RoundedPad1.0x1.5mm", 23.0, 15.2, 0, value="H3: bus/U2")
    ec2 = B.lib("C2", "Capacitor_THT", "C_Rect_L7.0mm_W2.5mm_P5.00mm", 30.8, 10.4, 0, value="100n", dnp=True)
    ec2.Reference().SetPosition(mm(28.0, 13.0))
    u2 = B.lib("U2", "Package_SO", "SOIC-8_3.9x4.9mm_P1.27mm", 33.5, 15.05, 0, value="DS2482-100 (0x19)", dnp=True)
    u2.Reference().SetPosition(mm(28.6, 15.0))   # left of the part; above it sits C2

    # --- link header J1: JST GH BM07B-GHS-TBT, top entry, at the left edge beside the opening to
    # the INT board and low against the lower rib so it does not face INT's J6; pins along y,
    # pin 1 at the bottom like J6's. The room x 0-9.5, y 41-61 stays free of tall parts for the plug and a finger.
    j1 = B.lib("J1", "Connector_JST", "JST_GH_BM07B-GHS-TBT_1x07-1MP_P1.25mm_Vertical", 4.3, 52.5, 0,
               value="GH BM07B link to INT")
    for rot in (0, 90, 180, 270):
        j1.SetOrientationDegrees(rot)
        j1.SetPosition(mm(4.3, 52.5))
        p1 = j1.FindPadByNumber("1").GetPosition(); p7 = j1.FindPadByNumber("7").GetPosition()
        if abs(pcbnew.ToMM(p1.x) - pcbnew.ToMM(p7.x)) < 0.01 and pcbnew.ToMM(p1.y) > pcbnew.ToMM(p7.y):
            break   # pins along y with pin 1 at the bottom, the same end as INT's J6, so the leads run straight
    else:
        raise SystemExit("could not orient J1")
    bb = j1.GetCourtyard(pcbnew.F_CrtYd).BBox()
    if pcbnew.ToMM(bb.GetLeft()) < 0.8 or pcbnew.ToMM(bb.GetBottom()) > 61.0:
        raise SystemExit("J1 outside its room: x %.1f y %.1f" % (pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetBottom())))
    j1.Reference().SetPosition(mm(4.3, pcbnew.ToMM(bb.GetTop()) - 1.0))

    # --- power section, mid field: bridge column, PTC standing, reservoir standing, converter
    # along the lower rib. D_DO-41 footprint: origin at pad 1 (cathode), pad 2 10.16 along +x.
    for ref, y in (("D1", 24.95), ("D2", 28.45), ("D3", 31.95), ("D4", 35.45)):
        d = B.lib(ref, "Diode_THT", "D_DO-41_SOD81_P10.16mm_Horizontal", 10.0, y, 0, value="1N4007")
        d.Reference().SetPosition(mm(22.0, y)); d.Reference().SetTextSize(VECTOR2I(FromMM(0.7), FromMM(0.7)))
    f1 = radial_disc(B, "PTC_Radial_P5.08_Standing", 5.08, 13.0, 3.1)
    custom.append(B.place("F1", f1, 18.04, 44.5, 0, value="PTC 1.1A 60V"))
    f1.Reference().SetPosition(mm(9.7, 44.5))   # left of the disc, so the link legend below it stays clear
    c3 = B.lib("C3", "Capacitor_THT", "CP_Radial_D12.5mm_P5.00mm", 29.0, 30.0, 0, value="470u 63V")
    c3.Reference().SetPosition(mm(31.5, 22.9))
    u3 = sip8_converter(B)
    custom.append(B.place("U3", u3, 13.11, 54.04, 0, value="TMR 12-4811WI"))
    # --- lower field: 5.1 V out on J4 (JST XH, pin 1 at 28.0), C4 beside it, tie slots under it,
    # 24 VAC in on J3 at the bottom edge with the probe sockets' 1.7 mm overhang, proto 10 x 4
    j4 = B.lib("J4", "Connector_JST", "JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical", 28.0, 69.2, 0, value="5V OUT to Pi USB-C")
    j4.Reference().SetPosition(mm(26.3, 65.4))
    c4 = B.lib("C4", "Capacitor_THT", "C_Rect_L7.0mm_W2.5mm_P5.00mm", 23.3, 67.0, 270, value="1u")
    x2, y2 = B.pad_xy("C4", 2)
    if abs(x2 - 23.3) > 0.01 or abs(y2 - 72.0) > 0.01:
        raise SystemExit(f"C4 pad 2 at {x2:.2f},{y2:.2f}, wanted 23.3,72.0")
    c4.Reference().SetPosition(mm(21.2, 69.5)); c4.Reference().SetTextAngleDegrees(90)
    # tie slots under J4 to the right of the proto field, which is 6 x 4 to leave them room
    custom.append(B.place("TS1", slot_pair(B), 30.6, 75.6, 0, value="tie slots"))
    B.rect_keepout(27.3, 73.7, 33.9, 77.5, layers=("F.Cu", "B.Cu"), name="tie slots",
                   pads=False, footprints=False, tracks=True, vias=True, pour=True)
    custom.append(B.place("J3", ptsm_hh(B, 2), 7.25, 81.3, 180, value="PTSM 0,5/2-HH-2,5-THR 24 VAC"))
    custom.append(B.place("PF1", pad_array(B, "Proto_6x4", 6, 4, square_first=False), 13.0, 75.6, 0, value="proto"))
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
    # U2's pin 8 (AD0 high) is the VCC pad Freerouting leaves open; pin 1 is VCC too, so tie them
    # straight across the package, clear of pins 2 and 7 by 0.7 mm
    x1, y1 = B.pad_xy("U2", 1); x8, y8 = B.pad_xy("U2", 8)
    B.track("VCC", x1, y1, x8, y8, width=0.4)
    B.connect("C1", 1, "VCC"); B.connect("C1", 2, "GND")
    B.connect("C2", 1, "VCC"); B.connect("C2", 2, "GND")
    for ref in ("H1", "H2"):
        B.connect(ref, 1, "VCC"); B.connect(ref, 2, "DATA"); B.connect(ref, 3, "GND")
    B.connect("H3", 1, "VCC"); B.connect("H3", 2, "H3_DATA"); B.connect("H3", 3, "GND")
    B.connect("JP2", 1, "DATA"); B.connect("JP2", 2, "H3_DATA"); B.connect("JP2", 3, "DATA_H3")
    B.connect("R1", 1, "VCC"); B.connect("R1", 2, "DATA")
    B.connect("JP1", 1, "GPIO4"); B.connect("JP1", 2, "DATA")
    for pos, net in enumerate(("VCC", "SDA", "SCL", "GPIO4", "GND", "VS", "COM"), start=1):
        B.connect("J1", pos, net)
    B.connect("J2", 1, "VCC"); B.connect("J2", 2, "DATA"); B.connect("J2", 3, "GND")
    # 24 VAC in on J3.1 (R) and J3.2 (C), PTC in the R leg, full-wave bridge, reservoir, converter
    B.connect("J3", 1, "ACR")
    B.connect("J3", 2, "ACC")
    B.connect("F1", 1, "ACR")
    B.connect("F1", 2, "ACF")
    # D_DO-41 footprint: pad 1 = cathode, pad 2 = anode
    B.connect("D1", 2, "ACF"); B.connect("D1", 1, "VS")
    B.connect("D2", 2, "ACC"); B.connect("D2", 1, "VS")
    B.connect("D3", 2, "COM"); B.connect("D3", 1, "ACF")
    B.connect("D4", 2, "COM"); B.connect("D4", 1, "ACC")
    B.connect("C3", 1, "VS"); B.connect("C3", 2, "COM")     # CP_Radial: pad 1 positive
    # Freerouting left C3's VS pad open; lay it: up from the pad, along y 22.9 above the diode
    # column (0.85 mm off the anode pads, clear of the rib rule area at 22.31), down to D1's cathode
    xc, yc = B.pad_xy("C3", 1); xd, yd = B.pad_xy("D1", 1)
    B.track("VS", xc, yc, xc, 22.9, width=0.5)
    B.track("VS", xc, 22.9, xd, 22.9, width=0.5)
    B.track("VS", xd, 22.9, xd, yd, width=0.5)
    B.connect("U3", 1, "COM"); B.connect("U3", 2, "VS")     # pin 3 Remote open = on
    B.connect("U3", 6, "+5V"); B.connect("U3", 7, "GND")
    B.connect("C4", 1, "+5V"); B.connect("C4", 2, "GND")
    B.connect("J4", 1, "+5V"); B.connect("J4", 2, "GND")

    for x, s in ((2.6, "trunk"), (5.07, "V"), (7.57, "D"), (10.07, "G")):
        B.text(s, x, 8.4, size=0.8 if len(s) == 1 else 0.7)
    B.text("H2 spare", 20.27, 8.4, size=0.8)
    B.text("H3 spare/0x19", 32.97, 8.4, size=0.8)
    B.text("pivac EXT rev B: 24 VAC in J3, VS/COM out J1.6/7, 5.1 V out J4", 19.25, 63.4, size=0.65)
    for i, s in enumerate(("J1 LINK 1=3V3 2=SDA", "3=SCL 4=GPIO4 5=GND", "6=VS 7=COM")):
        B.text(s, 9.0, 47.2 + 1.15 * i, size=0.65, left=True)   # between F1 and U3, beside J1
    B.text("24 VAC", 7.25, 77.6, size=0.8)
    B.text("5V OUT", 31.6, 65.4, size=0.7)
    title_block(B, 31.2, 40.3, 0.7, "EXT", stacked=True)   # below C3, right of F1, above U3
    B.save()
    save_pretty(custom)
    return B


# --------------------------------------------------------------------------- EXT board, rev C
def build_extc():
    """Rev C of the EXT board (docs/rpi-io-boards-revc-plan.md): every connector at an edge is
    the surface-mount PTSM header with its entry face on the edge, J4 is the vertical header of
    the same family, two probe sockets, no tie slots. The power section and the link are rev B's."""
    out = os.path.join(HERE, "extc-board")
    os.makedirs(out, exist_ok=True)
    B = Board(os.path.join(out, "extc-board.kicad_pcb"), 38.5, 85.0, power_clearance=0.5)
    custom = []
    for (y0, y1) in BANDS_Y:
        B.rect_keepout(0, y0, 38.5, y1, name="housing rib")
        B.line(0, y0, 38.5, y0, "B.SilkS", 0.1)
        B.line(0, y1, 38.5, y1, "B.SilkS", 0.1)
    for x0, y0, x1, y1 in ((0, 0, 0.8, 85), (37.7, 0, 38.5, 85), (0, 0, 38.5, 0.8), (0, 84.2, 38.5, 85)):
        B.rect_keepout(x0, y0, x1, y1, layers=("F.Cu", "B.Cu"), name="edge via keepout",
                       pads=False, footprints=False, tracks=False, vias=True, pour=False)

    # --- probe sockets, centred on the board and 17.5 apart so two latching plugs (16.8 wide)
    # sit side by side; entry face on the top edge
    for ref, xc, what in (("H1", 10.5, "TRUNK"), ("H2", 28.0, "SPARE")):
        h = ptsm_hh_smd(B, 3)
        custom.append(B.place(ref, h, xc, 0.0, 0, value="PTSM 0,5/3-HH-2,5-SMD"))
        for k, (dx, letter) in enumerate(((-2.5, "V"), (0.0, "D"), (2.5, "G")), start=1):
            x, y = B.pad_xy(ref, k)
            if abs(x - (xc + dx)) > 0.01 or abs(y - 8.2) > 0.01:
                raise SystemExit(f"{ref} pad {k} at {x:.2f},{y:.2f}")
            B.text(letter, xc + dx, 10.8, size=1.0, bold=True)
        # the reference and the socket's use stand beside its leads, level with the signal
        # pads and behind the body, so each reads as that connector's and shows when it is fitted
        h.Reference().SetPosition(mm(xc - 5.3, 8.2))
        h.Reference().SetTextSize(VECTOR2I(FromMM(0.9), FromMM(0.9)))
        B.text(what, xc + 5.4, 8.2, size=0.7)

    # --- probe row: four parts on one line, 2.5 apart, references on one baseline
    ROW, REF = 13.9, 17.3
    u1 = B.lib("U1", "Package_SO", "SOIC-8_3.9x4.9mm_P1.27mm", 4.6, ROW, 0, value="DS2482-100")
    u1.Reference().SetPosition(mm(4.6, REF))
    ec1 = B.lib("C1", "Capacitor_THT", "C_Rect_L7.0mm_W2.5mm_P5.00mm", 11.1, ROW, 0, value="100n")
    ec1.Reference().SetPosition(mm(13.6, REF))
    jp1 = B.lib("JP1", "Jumper", "SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm", 21.1, ROW, 0, value="GPIO4->DATA")
    jp1.Reference().SetPosition(mm(21.1, REF))
    r1 = B.lib("R1", "Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 25.7, ROW, 0,
               value="2k2 rollback", dnp=True)
    r1.Reference().SetPosition(mm(30.78, REF))

    # --- link header J1, as rev B
    j1 = B.lib("J1", "Connector_JST", "JST_GH_BM07B-GHS-TBT_1x07-1MP_P1.25mm_Vertical", 4.3, 52.5, 0,
               value="GH BM07B link to INT")
    for rot in (0, 90, 180, 270):
        j1.SetOrientationDegrees(rot)
        j1.SetPosition(mm(4.3, 52.5))
        p1 = j1.FindPadByNumber("1").GetPosition(); p7 = j1.FindPadByNumber("7").GetPosition()
        if abs(pcbnew.ToMM(p1.x) - pcbnew.ToMM(p7.x)) < 0.01 and pcbnew.ToMM(p1.y) > pcbnew.ToMM(p7.y):
            break
    else:
        raise SystemExit("could not orient J1")
    bb = j1.GetCourtyard(pcbnew.F_CrtYd).BBox()
    if pcbnew.ToMM(bb.GetLeft()) < 0.8 or pcbnew.ToMM(bb.GetBottom()) > 61.0:
        raise SystemExit("J1 outside its room")
    # above the header, clear of its upper mounting pad, reading left to right
    j1.Reference().SetPosition(mm(4.3, pcbnew.ToMM(bb.GetTop()) - 1.4)); j1.Reference().SetTextAngleDegrees(0)

    # --- power section as rev B, with U3 2 mm further from J1
    for ref, y in (("D1", 24.95), ("D2", 28.45), ("D3", 31.95), ("D4", 35.45)):
        d = B.lib(ref, "Diode_THT", "D_DO-41_SOD81_P10.16mm_Horizontal", 10.0, y, 0, value="1N4007")
        d.Reference().SetPosition(mm(22.0, y)); d.Reference().SetTextSize(VECTOR2I(FromMM(0.7), FromMM(0.7)))
    f1 = radial_disc(B, "PTC_Radial_P5.08_Standing", 5.08, 13.0, 3.1)
    custom.append(B.place("F1", f1, 18.04, 44.5, 0, value="PTC 1.1A 60V"))
    f1.Reference().SetPosition(mm(9.7, 44.5))
    c3 = B.lib("C3", "Capacitor_THT", "CP_Radial_D12.5mm_P5.00mm", 29.0, 30.0, 0, value="470u 63V")
    c3.Reference().SetPosition(mm(31.5, 22.9))
    u3 = sip8_converter(B)
    custom.append(B.place("U3", u3, 15.11, 54.04, 0, value="TMR 12-4811WI"))
    u3.Reference().SetPosition(mm(24.0, 61.3))     # below the body, where it shows with U3 fitted
    # the pin names again on the solder side, for the meter after soldering: the names on the
    # component side are under the converter once it is fitted
    for n, name in ((1, "-Vin"), (2, "+Vin"), (3, "Rmt"), (6, "+Vo"), (7, "-Vo"), (8, "NC")):
        x = 15.11 + (n - 1) * PITCH
        B.text(name, x, 54.04 + 1.9, layer="B.SilkS", size=0.6)
        B.text(str(n), x, 54.04 + 3.0, layer="B.SilkS", size=0.6)
    B.text("U3", 24.0, 58.6, layer="B.SilkS", size=0.8)
    # Traco: no copper under the converter. Its body covers x 13 to 35, y 50.5 to 60.1 on the
    # component side, so nothing but its own pads may be on F.Cu there; the pins are reached on
    # the solder side.
    B.rect_keepout(12.9, 50.4, 35.1, 60.2, layers=("F.Cu",), name="no copper under U3",
                   pads=False, footprints=False, tracks=True, vias=True, pour=True)
    # On the solder side only the four connected pins' escapes run under it: each pin leaves
    # by a 2 mm channel toward the nearer long edge, 3.5 mm away, and the rest is closed.
    pins = [15.11 + (n - 1) * PITCH for n in (1, 2, 6, 7)]
    edges = [12.9] + [v for x in pins for v in (x - 1.0, x + 1.0)] + [35.1]
    for x0, x1 in zip(edges[0::2], edges[1::2]):
        B.rect_keepout(x0, 50.4, x1, 55.05, layers=("B.Cu",), name="no copper under U3",
                       pads=False, footprints=False, tracks=True, vias=True, pour=True)
    B.rect_keepout(12.9, 55.05, 35.1, 60.2, layers=("B.Cu",), name="no copper under U3",
                   pads=False, footprints=False, tracks=True, vias=True, pour=True)

    # --- 5 V output: J4, the vertical header turned so its pin row runs along y and its leads
    # leave toward the right edge; C4 to its left with the legend between them
    J4X, J4Y = 30.1, 71.3          # the lead-side face, and the middle of the pin row
    j4 = ptsm_hv_smd(B, 2)
    custom.append(B.place("J4", j4, J4X, J4Y, 0, value="PTSM 0,5/2-HV-2,5-SMD 5V OUT"))
    for rot in (0, 90, 180, 270):
        j4.SetOrientationDegrees(rot)
        j4.SetPosition(mm(J4X, J4Y))
        (x1, y1), (x2, y2) = B.pad_xy("J4", 1), B.pad_xy("J4", 2)
        if abs(x1 - x2) < 0.01 and y1 < y2 and x1 > J4X:
            break      # pin 1 (+5 V) above pin 2, pads centred right of the lead-side face
    else:
        raise SystemExit("could not orient J4")
    if abs(x1 - (J4X + 0.2)) > 0.01 or abs(y1 - (J4Y - 1.25)) > 0.01:
        raise SystemExit(f"J4 pad 1 at {x1:.2f},{y1:.2f}")
    j4.Reference().SetPosition(mm(J4X - 2.5, 64.6)); j4.Reference().SetTextAngleDegrees(0)
    c4 = B.lib("C4", "Capacitor_THT", "C_Rect_L7.0mm_W2.5mm_P5.00mm", 20.0, 67.0, 270, value="1u")
    x2, y2 = B.pad_xy("C4", 2)
    if abs(x2 - 20.0) > 0.01 or abs(y2 - 72.0) > 0.01:
        raise SystemExit(f"C4 pad 2 at {x2:.2f},{y2:.2f}, wanted 20.0,72.0")
    c4.Reference().SetPosition(mm(17.9, 69.5)); c4.Reference().SetTextAngleDegrees(90)

    # --- 24 VAC input: J3 on the bottom edge, pin 1 (R) at x 9.25
    j3 = ptsm_hh_smd(B, 2)
    custom.append(B.place("J3", j3, 8.0, 85.0, 180, value="PTSM 0,5/2-HH-2,5-SMD 24 VAC"))
    x1, y1 = B.pad_xy("J3", 1)
    if abs(x1 - 9.25) > 0.01 or abs(y1 - 76.8) > 0.01:
        raise SystemExit(f"J3 pad 1 at {x1:.2f},{y1:.2f}, wanted 9.25,76.8")
    j3.Reference().SetPosition(mm(1.9, 78.0))
    pf1 = pad_array(B, "Proto_8x3", 8, 3, square_first=False, margin=0.95)
    custom.append(B.place("PF1", pf1, 15.54, 78.14, 0, value="proto"))
    pf1.Reference().SetPosition(mm(36.2, 80.68)); pf1.Reference().SetTextAngleDegrees(90)
    # J2 stands 0.9 right of its rev B place, which leaves J4's pin legends whole
    custom.append(B.place("J2", pad_array(B, "Pads_1x3", 1, 3), 36.4, 68.0, 0, value="VCC DATA GND"))

    # --- nets
    B.connect("U1", 1, "VCC"); B.connect("U1", 2, "DATA"); B.connect("U1", 3, "GND")
    B.connect("U1", 4, "SCL"); B.connect("U1", 5, "SDA"); B.connect("U1", 7, "GND")
    B.connect("U1", 8, "GND")      # 0x18
    B.connect("C1", 1, "VCC"); B.connect("C1", 2, "GND")
    for ref in ("H1", "H2"):
        B.connect(ref, 1, "VCC"); B.connect(ref, 2, "DATA"); B.connect(ref, 3, "GND")
    B.connect("R1", 1, "VCC"); B.connect("R1", 2, "DATA")
    B.connect("JP1", 1, "GPIO4"); B.connect("JP1", 2, "DATA")
    for pos, net in enumerate(("VCC", "SDA", "SCL", "GPIO4", "GND", "VS", "COM"), start=1):
        B.connect("J1", pos, net)
    B.connect("J2", 1, "VCC"); B.connect("J2", 2, "DATA"); B.connect("J2", 3, "GND")
    B.connect("J3", 1, "ACR")
    B.connect("J3", 2, "ACC")
    B.connect("F1", 1, "ACR")
    B.connect("F1", 2, "ACF")
    B.connect("D1", 2, "ACF"); B.connect("D1", 1, "VS")
    B.connect("D2", 2, "ACC"); B.connect("D2", 1, "VS")
    B.connect("D3", 2, "COM"); B.connect("D3", 1, "ACF")
    B.connect("D4", 2, "COM"); B.connect("D4", 1, "ACC")
    B.connect("C3", 1, "VS"); B.connect("C3", 2, "COM")
    xc, yc = B.pad_xy("C3", 1); xd, yd = B.pad_xy("D1", 1)
    B.track("VS", xc, yc, xc, 22.9, width=0.5)
    B.track("VS", xc, 22.9, xd, 22.9, width=0.5)
    B.track("VS", xd, 22.9, xd, yd, width=0.5)
    B.connect("U3", 1, "COM"); B.connect("U3", 2, "VS")
    B.connect("U3", 6, "+5V"); B.connect("U3", 7, "GND")
    B.connect("C4", 1, "+5V"); B.connect("C4", 2, "GND")
    B.connect("J4", 1, "+5V"); B.connect("J4", 2, "GND")
    # The Pi's supply from U3 to C4, laid by hand on the solder side at 1.0 mm: each pin leaves
    # U3 by its channel, the pair runs round the converter's right end and back under J4, which
    # has no copper on this side. 47 and 55 mm long, about 25 mohm each, against the 62 mm at
    # 0.5 mm the router took round the left end.
    p6x, p6y = B.pad_xy("U3", 6); p7x, p7y = B.pad_xy("U3", 7)
    (c1x, c1y), (c2x, c2y) = B.pad_xy("C4", 1), B.pad_xy("C4", 2)
    for net, pts in (("+5V", [(p6x, p6y), (p6x, 47.9), (37.35, 47.9), (37.35, 65.0), (36.35, 66.0),
                              (c1x + 1.0, 66.0), (c1x, c1y)]),
                     ("GND", [(p7x, p7y), (p7x, 49.4), (35.85, 49.4), (35.85, 61.3), (34.85, 62.3),
                              (17.5, 62.3), (17.5, c2y - 1.0), (18.5, c2y), (c2x, c2y)])):
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            B.track(net, xa, ya, xb, yb, layer="B.Cu", width=1.0)
    # Freerouting leaves J4's two surface pads open on every attempt; lay them: straight out of
    # each pad under the header body to C4, whose pads the router joins to U3. The two tracks
    # run 2.5 apart between the anchor pads and clear the peg holes by 0.65.
    (x1, y1), (x2, y2) = B.pad_xy("J4", 1), B.pad_xy("J4", 2)
    B.track("+5V", x1, y1, 23.0, y1, width=0.5)
    B.track("+5V", 23.0, y1, 23.0, c1y, width=0.5)
    B.track("+5V", 23.0, c1y, c1x, c1y, width=0.5)
    B.track("GND", x2, y2, c2x + (y2 - c2y), y2, width=0.5)
    B.track("GND", c2x + (y2 - c2y), y2, c2x, c2y, width=0.5)

    # --- legends. No via under a legend: a via's mask opening cuts the letter printed over it.
    for x0, y0, x1, y1 in ((3.0, 10.1, 36.5, 11.5),        # V D G under both sockets
                           (3.4, 7.5, 7.0, 9.0), (13.9, 7.5, 17.6, 9.0),       # H1, TRUNK
                           (20.9, 7.5, 24.5, 9.0), (31.4, 7.5, 35.1, 9.0),     # H2, SPARE
                           (22.4, 60.5, 25.6, 62.1),       # the reference U3
                           (2.5, 16.6, 33.0, 18.0),        # the references U1, C1, JP1, R1
                           (1.0, 72.6, 14.8, 76.6),        # 24VAC input, C, R
                           (21.9, 63.2, 24.9, 77.3),       # 5VDC output only, to Pi
                           (32.9, 69.2, 35.2, 73.4),       # +5, G
                           (8.8, 46.5, 21.0, 49.7),        # link legend
                           (2.8, 43.6, 11.0, 45.4),        # the references J1 and F1
                           (24.8, 37.4, 37.6, 50.2)):      # title block
        B.rect_keepout(x0, y0, x1, y1, layers=("F.Cu", "B.Cu"), name="no via under a legend",
                       pads=False, footprints=False, tracks=False, vias=True, pour=False)
    for i, s in enumerate(("J1 LINK 1=3V3 2=SDA", "3=SCL 4=GPIO4 5=GND", "6=VS 7=COM")):
        B.text(s, 9.0, 47.1 + 1.05 * i, size=0.65, left=True)
    B.text("24VAC input", 8.0, 73.4, size=1.0, bold=True)
    B.text("R", 10.95, 75.9, size=1.0, bold=True)
    B.text("C", 5.05, 75.9, size=1.0, bold=True)
    B.text("5VDC output only", 22.7, 70.4, size=0.95, rot=90, bold=True)
    B.text("to Pi", 24.2, 70.4, size=0.95, rot=90, bold=True)
    B.text("+5", 33.95, J4Y - 1.25, size=1.0, bold=True)
    B.text("G", 33.95, J4Y + 1.25, size=1.0, bold=True)
    # the block's ring top and its last line's foot stand the same distance from C3 and U3
    title_block(B, 31.2, 40.8, 0.7, "EXT", stacked=True, rev="C")
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
    if "extc" in which:
        build_extc()
        print("wrote extc-board")
