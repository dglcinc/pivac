#!/usr/bin/env python3
"""Write a KiCad schematic for each board, from the same tables gen-boards.py places.

    python3 hardware/gen-schematics.py          (plain python3 is enough; no pcbnew needed)

The schematic is the human-readable record of the circuit: every part as a library symbol
with a short wire stub and a global label on each connected pin, arranged by function. Nets
are carried by labels, not drawn wires. Symbols come from KiCad's own libraries where they
exist (resistor, diode, capacitor, fuse, varistor, generic connectors, the Pi header, solder
jumpers); the LTV-847 and DS2482-100 are drawn here. The pin-to-net tables are shared with
gen-boards.py by import, so the two cannot drift apart.

Check with:  kicad-cli sch erc hardware/int-board/int-board.kicad_sch
             kicad-cli sch export netlist hardware/int-board/int-board.kicad_sch
"""
import os
import re
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_tables as T  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SYMLIB = os.path.expanduser("~/Applications/KiCad.app/Contents/SharedSupport/symbols")


# ------------------------------------------------------------------ s-expression helpers
def parse(text):
    """Minimal s-expression reader: returns nested lists of str."""
    tokens = re.findall(r'"(?:[^"\\]|\\.)*"|[()]|[^\s()"]+', text)
    stack = [[]]
    for tok in tokens:
        if tok == "(":
            stack.append([])
        elif tok == ")":
            node = stack.pop()
            stack[-1].append(node)
        else:
            stack[-1].append(tok)
    return stack[0]


def dump(node, depth=0):
    if isinstance(node, str):
        return node
    inner = " ".join(dump(n, depth + 1) for n in node)
    return "(" + inner + ")"


def lib_symbol(lib, name):
    """Return the (symbol "lib:name" ...) block from a KiCad library, renamed with its lib prefix."""
    text = open(os.path.join(SYMLIB, lib + ".kicad_sym"), encoding="utf-8").read()
    tree = parse(text)[0]
    for node in tree:
        if isinstance(node, list) and node and node[0] == "symbol" and node[1] == f'"{name}"':
            node = [n for n in node]
            node[1] = f'"{lib}:{name}"'   # sub-units keep their bare "name_0_1" names
            return node
    raise SystemExit(f"symbol {lib}:{name} not found")


def symbol_pins(node):
    """{pin number: (x, y, rotation)} in symbol coordinates (y up)."""
    pins = {}

    def walk(n):
        if isinstance(n, list):
            if n and n[0] == "pin":
                at = next(m for m in n if isinstance(m, list) and m[0] == "at")
                num = next(m for m in n if isinstance(m, list) and m[0] == "number")[1].strip('"')
                pins[num] = (float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0)
            for m in n:
                walk(m)

    walk(node)
    return pins


def box_symbol(name, pins_left, pins_right, width=20.32, ref_prefix="U", desc=""):
    """Draw a rectangular symbol: pins_left/right are lists of (number, name) top to bottom."""
    rows = max(len(pins_left), len(pins_right))
    height = (rows + 1) * 2.54
    top = height / 2
    body = [f'(symbol "pivac:{name}" (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)',
            f'  (property "Reference" "{ref_prefix}" (at 0 {top + 1.27:.2f} 0) (effects (font (size 1.27 1.27))))',
            f'  (property "Value" "{name}" (at 0 {-top - 1.27:.2f} 0) (effects (font (size 1.27 1.27))))',
            f'  (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
            f'  (property "Datasheet" "{desc}" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
            f'  (symbol "{name}_0_1"',
            f'    (rectangle (start {-width/2:.2f} {top:.2f}) (end {width/2:.2f} {-top:.2f}) (stroke (width 0.254) (type default)) (fill (type background))))',
            f'  (symbol "{name}_1_1"']
    pins = {}
    for i, (num, pname) in enumerate(pins_left):
        y = top - (i + 1) * 2.54
        body.append(f'    (pin passive line (at {-width/2 - 2.54:.2f} {y:.2f} 0) (length 2.54) (name "{pname}" (effects (font (size 1.27 1.27)))) (number "{num}" (effects (font (size 1.27 1.27)))))')
        pins[str(num)] = (-width / 2 - 2.54, y, 0)
    for i, (num, pname) in enumerate(pins_right):
        y = top - (i + 1) * 2.54
        body.append(f'    (pin passive line (at {width/2 + 2.54:.2f} {y:.2f} 180) (length 2.54) (name "{pname}" (effects (font (size 1.27 1.27)))) (number "{num}" (effects (font (size 1.27 1.27)))))')
        pins[str(num)] = (width / 2 + 2.54, y, 180)
    body.append("  ))")
    return parse("\n".join(body))[0], pins


# ------------------------------------------------------------------ schematic writer
class Sheet:
    def __init__(self, path, title):
        self.path = path
        self.title = title
        self.uuid = str(uuid.uuid4())
        self.libs = {}       # lib_id -> (node, pins)
        self.items = []

    def lib(self, lib_id, node=None, pins=None):
        if lib_id not in self.libs:
            if node is None:
                lib, name = lib_id.split(":")
                node = lib_symbol(lib, name)
                pins = symbol_pins(node)
            self.libs[lib_id] = (node, pins)
        return self.libs[lib_id][1]

    def place(self, lib_id, ref, value, x, y, nets, footprint="", dnp=False, hide_value=False):
        """Place a symbol at (x, y) in sheet mm (y down) and label the pins listed in nets {pin: net}.

        Positions snap to the 2.54 mm grid so every pin end sits on the connection grid; pins
        not in ``nets`` get a no-connect flag.
        """
        x, y = round(x / 2.54) * 2.54, round(y / 2.54) * 2.54
        pins = self.lib(lib_id)
        u = str(uuid.uuid4())
        props = [f'(property "Reference" "{ref}" (at {x:.2f} {y - 3.5:.2f} 0) (effects (font (size 1.27 1.27))))',
                 f'(property "Value" "{value}" (at {x + 5:.2f} {y + 3.5:.2f} 0) (effects (font (size 1.0 1.0)) (justify left){" (hide yes)" if hide_value else ""}))',
                 f'(property "Footprint" "{footprint}" (at {x:.2f} {y:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes)))']
        pin_items = " ".join(f'(pin "{p}" (uuid "{uuid.uuid4()}"))' for p in pins)
        self.items.append(
            f'(symbol (lib_id "{lib_id}") (at {x:.2f} {y:.2f} 0) (unit 1) (exclude_from_sim no) (in_bom {"no" if dnp else "yes"}) '
            f'(on_board yes) (dnp {"yes" if dnp else "no"}) (uuid "{u}") {" ".join(props)} {pin_items} '
            f'(instances (project "{self.title}" (path "/{self.uuid}" (reference "{ref}") (unit 1)))))')
        for p, (px, py, rot) in pins.items():
            if p not in {str(k) for k in nets}:
                self.items.append(f'(no_connect (at {x + px:.4f} {y - py:.4f}) (uuid "{uuid.uuid4()}"))')
        for p, net in nets.items():
            px, py, rot = pins[str(p)]
            ex, ey = x + px, y - py             # pin end, sheet coordinates
            # the pin points inward; the label goes a little further out along the pin direction
            dx, dy = {0: (-2.54, 0), 180: (2.54, 0), 90: (0, 2.54), 270: (0, -2.54)}[int(rot) % 360]
            lx, ly = ex + dx, ey + dy
            self.items.append(f'(wire (pts (xy {ex:.4f} {ey:.4f}) (xy {lx:.4f} {ly:.4f})) (stroke (width 0) (type default)) (uuid "{uuid.uuid4()}"))')
            lrot = {0: 180, 180: 0, 90: 270, 270: 90}[int(rot) % 360]
            self.items.append(f'(global_label "{net}" (shape passive) (at {lx:.4f} {ly:.4f} {lrot}) (fields_autoplaced yes) '
                              f'(effects (font (size 1.0 1.0)) (justify {"right" if lrot == 180 else "left"})) (uuid "{uuid.uuid4()}") '
                              f'(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes))))')

    def pwr_flags(self, nets, x, y):
        """One PWR_FLAG per net so ERC accepts the Pi's power-input pins as driven."""
        for i, net in enumerate(nets):
            self.place("power:PWR_FLAG", f"#FLG{i + 1}", "PWR_FLAG", x + i * 15.24, y, {1: net}, hide_value=True)

    def text(self, s, x, y, size=2.0):
        self.items.append(f'(text "{s}" (exclude_from_sim no) (at {x:.2f} {y:.2f} 0) (effects (font (size {size} {size}) bold) (justify left)) (uuid "{uuid.uuid4()}"))')

    def save(self):
        libs = "\n".join(dump(node) for node, _ in self.libs.values())
        body = "\n".join(self.items)
        out = (f'(kicad_sch (version 20250114) (generator "pivac") (generator_version "10.0") (uuid "{self.uuid}") (paper "A3")\n'
               f'(title_block (title "{self.title}") (company "pivac") (rev "A"))\n'
               f'(lib_symbols\n{libs}\n)\n{body}\n(sheet_instances (path "/" (page "1")))\n)\n')
        open(self.path, "w", encoding="utf-8").write(out)
        # project-local library tables so the pivac symbols and footprints resolve in the GUI
        d = os.path.dirname(self.path)
        open(os.path.join(d, "sym-lib-table"), "w").write(
            '(sym_lib_table (version 7)\n  (lib (name "pivac")(type "KiCad")(uri "${KIPRJMOD}/../pivac.kicad_sym")(options "")(descr "pivac symbols"))\n)\n')
        open(os.path.join(d, "fp-lib-table"), "w").write(
            '(fp_lib_table (version 7)\n  (lib (name "pivac")(type "KiCad")(uri "${KIPRJMOD}/../pivac.pretty")(options "")(descr "pivac footprints"))\n)\n')
        custom = [dump(node) for lib_id, (node, _) in self.libs.items() if lib_id.startswith("pivac:")]
        libpath = os.path.join(HERE, "pivac.kicad_sym")
        existing = open(libpath).read() if os.path.exists(libpath) else ""
        for c in custom:
            name = c.split('"')[1]
            if f'"{name}"' not in existing:
                existing = existing.rstrip().rstrip(")") + "\n" + c + "\n)\n" if existing else \
                    '(kicad_symbol_lib (version 20251024) (generator "pivac")\n' + c + "\n)\n"
        open(libpath, "w").write(existing)


# ------------------------------------------------------------------ INT board
def build_int():
    S = Sheet(os.path.join(HERE, "int-board", "int-board.kicad_sch"), "int-board")
    ltv, ltv_pins = box_symbol("LTV-847", [(1, "A1"), (2, "K1"), (3, "A2"), (4, "K2"), (5, "A3"), (6, "K3"), (7, "A4"), (8, "K4")],
                               [(16, "C1"), (15, "E1"), (14, "C2"), (13, "E2"), (12, "C3"), (11, "E3"), (10, "C4"), (9, "E4")],
                               desc="Lite-On LTV-847 quad optocoupler, DIP-16")
    S.lib("pivac:LTV-847", ltv, ltv_pins)
    S.text("pivac INT board rev B: relay-sense inputs on LTV-847 optocouplers; VS/COM arrive from the EXT board", 20, 15, 3)
    S.text("Field side (VS / COM / plugs) and Pi side (GND / GPIO) meet only inside the optocouplers.", 20, 21, 1.6)

    # channels: one row per IC, resistor + plug label per channel
    for k in (1, 2, 3):
        x, y = 60, 45 + (k - 1) * 60
        nets = {}
        for c in range(1, 5):
            n = (k - 1) * 4 + c
            name, plug, pos, bcm, pin = T.CHANNELS[n - 1]
            nets[2 * c - 1] = "VS"
            nets[2 * c] = f"K{n}"
            nets[17 - 2 * c] = "GND"
            nets[18 - 2 * c] = f"GPIO{bcm}"
            S.place("Device:R", f"R{n}", "12k 1/4W", x + 60 + (c - 1) * 30, y - 6, {1: f"K{n}", 2: f"S_{name}"},
                    footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal")
            S.text(f"ch{n} {name}", x + 52 + (c - 1) * 30, y + 10, 1.2)
            S.text(f"{plug}.{pos} > G{bcm} (p{pin})", x + 52 + (c - 1) * 30, y + 13, 1.0)
        S.place("pivac:LTV-847", f"U{k}", "LTV-847", x, y, nets, footprint="Package_DIP:DIP-16_W7.62mm_Socket")

    # plugs
    S.text("Field plugs, PTSM 0,5/4-HH-2,5-THR; position 4 is COM on every plug; twelve channels on twelve positions", 20, 225, 1.6)
    for i, (j, xc) in enumerate(T.PLUG_X.items()):
        nets = {4: "COM"}
        for name, plug, pos, bcm, pin in T.CHANNELS:
            if plug == j:
                nets[pos] = f"S_{name}"
        S.place("Connector_Generic:Conn_01x04", j, "PTSM 0,5/4-HH", 40 + i * 45, 240, nets, footprint="pivac:PTSM_0.5_4-HH-2.5-THR")
    S.text("The sense supply (VS about 35 V DC, COM its return) is made on the EXT board and arrives on J6.6/J6.7.", 250, 225, 1.6)

    # Pi header
    S.text("Pi 40-pin socket J5 (solder side), odd pins left, even pins right. Pins 9, 25, 39 (GND), 8/10 (console), 27/28 (ID EEPROM) unconnected.", 250, 30, 1.6)
    hdr = {}
    for p in T.PI_GND:
        hdr[p] = "GND"
    for p in T.PI_5V:
        hdr[p] = "+5V"
    for p in T.PI_3V3:
        hdr[p] = "3V3"
    hdr.update({3: "SDA", 5: "SCL", 7: "GPIO4"})
    for name, plug, pos, bcm, pin in T.CHANNELS:
        hdr[pin] = f"GPIO{bcm}"
    for entry in T.BREAKOUT:
        if entry:
            hdr[entry[1]] = entry[2]
    # a plain 2x20 symbol rather than the library's Raspberry Pi symbol, whose ground pins are
    # stacked and would show pins 9, 25 and 39 as connected when the board leaves them open
    S.place("Connector_Generic:Conn_02x20_Odd_Even", "J5", "Pi 40-pin socket", 330, 110, hdr, footprint="pivac:PiHeader_2x20_Socket_Bottom", hide_value=True)

    # breakout, link, power link, test points
    S.text("Shadow column J9: one pad per header row (rows 1, 2, 16, 18 empty); pins 2 and 4 (5 V) carry nothing, the Pi is fed by USB-C", 250, 185, 1.6)
    S.place("Connector_Generic:Conn_01x20", "J9", "breakout", 290, 210, {i: e[2] for i, e in enumerate(T.BREAKOUT, start=1) if e},
            footprint="pivac:Shadow_1x20", hide_value=True)
    S.place("Connector_Generic:Conn_01x07", "J6", "GH link to EXT", 400, 120, dict(enumerate(("3V3", "SDA", "SCL", "GPIO4", "GND", "VS", "COM"), start=1)), footprint="Connector_JST:JST_GH_SM07B-GHS-TB_1x07-1MP_P1.25mm_Horizontal")
    for ref, net, y in (("TP1", "VS", 190), ("TP2", "COM", 200), ("TP3", "GND", 210)):
        S.place("Connector_Generic:Conn_01x01", ref, net, 400, y, {1: net}, footprint="pivac:TestPad", hide_value=True)
    S.pwr_flags(("3V3", "+5V", "GND", "VS", "COM"), 250, 270)
    S.save()
    return S


# ------------------------------------------------------------------ EXT board
def build_ext():
    S = Sheet(os.path.join(HERE, "ext-board", "ext-board.kicad_sch"), "ext-board")
    ds, ds_pins = box_symbol("DS2482-100", [(1, "VCC"), (2, "IO"), (3, "GND"), (4, "SCL")], [(8, "AD0"), (7, "AD1"), (6, "PCTLZ"), (5, "SDA")],
                             desc="Analog Devices DS2482-100 I2C to 1-Wire bridge, SO-8")
    S.lib("pivac:DS2482-100", ds, ds_pins)
    S.text("pivac EXT board rev B: DS2482-100 1-wire master, three probe sockets, 24 VAC sense supply and the Pi's 5.1 V supply, link to the INT board", 20, 15, 3)
    tmr, tmr_pins = box_symbol("TMR12WI", [(1, "-Vin"), (2, "+Vin"), (3, "Remote")], [(6, "+Vout"), (7, "-Vout"), (8, "NC")],
                               desc="Traco TMR 12-4811WI isolated DC/DC, 18-75 V in, 5.1 V 2.4 A out, SIP-8")
    S.lib("pivac:TMR12WI", tmr, tmr_pins)
    S.place("pivac:DS2482-100", "U1", "DS2482-100 (0x18)", 80, 60, {1: "VCC", 2: "DATA", 3: "GND", 4: "SCL", 5: "SDA", 7: "GND", 8: "GND"}, footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm")
    S.place("Device:C", "C1", "100n", 130, 60, {1: "VCC", 2: "GND"}, footprint="Capacitor_THT:C_Rect_L7.0mm_W2.5mm_P5.00mm")
    S.place("pivac:DS2482-100", "U2", "DS2482-100 (0x19, not fitted)", 80, 120, {1: "VCC", 2: "DATA_H3", 3: "GND", 4: "SCL", 5: "SDA", 7: "GND", 8: "VCC"}, footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", dnp=True)
    S.place("Device:C", "C2", "100n", 130, 120, {1: "VCC", 2: "GND"}, footprint="Capacitor_THT:C_Rect_L7.0mm_W2.5mm_P5.00mm", dnp=True)
    S.text("Probe sockets PTSM 0,5/3-HH-2,5-THR: 1 VCC, 2 DATA, 3 GND. JP2 sends H3's DATA to the bus (1-2) or to U2 (2-3).", 20, 160, 1.6)
    for i, (ref, io) in enumerate((("H1", "DATA"), ("H2", "DATA"), ("H3", "H3_DATA"))):
        S.place("Connector_Generic:Conn_01x03", ref, "PTSM 0,5/3-HH", 50 + i * 45, 180, {1: "VCC", 2: io, 3: "GND"}, footprint="pivac:PTSM_0.5_3-HH-2.5-THR")
    S.place("Jumper:SolderJumper_3_Open", "JP2", "H3: bus / U2", 200, 180, {1: "DATA", 2: "H3_DATA", 3: "DATA_H3"}, footprint="Jumper:SolderJumper-3_P1.3mm_Open_RoundedPad1.0x1.5mm")
    S.text("Rollback to w1-gpio: fit R1 and bridge JP1, and GPIO4 becomes the bus data line.", 20, 215, 1.6)
    S.place("Device:R", "R1", "2k2 (not fitted)", 50, 235, {1: "VCC", 2: "DATA"}, footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", dnp=True)
    S.place("Jumper:SolderJumper_2_Open", "JP1", "GPIO4 -> DATA", 90, 235, {1: "GPIO4", 2: "DATA"}, footprint="Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm")
    S.place("Connector_Generic:Conn_01x07", "J1", "GH link to INT", 250, 60, dict(enumerate(("VCC", "SDA", "SCL", "GPIO4", "GND", "VS", "COM"), start=1)), footprint="Connector_JST:JST_GH_BM07B-GHS-TBT_1x07-1MP_P1.25mm_Vertical")
    S.place("Connector_Generic:Conn_01x03", "J2", "bus pads", 250, 110, {1: "VCC", 2: "DATA", 3: "GND"}, footprint="pivac:Pads_1x3")
    # power section
    S.text("24 VAC in on J3, PTC F1, bridge D1-D4, C3 470 uF: VS about 35 V DC against COM, out to INT on J1.6/J1.7 and into U3.", 20, 270, 1.6)
    S.text("U3 makes 5.1 V isolated for the Pi: C4 at its output, J4 to a USB-C pigtail. Remote (pin 3) open = on. COM never meets GND.", 20, 276, 1.6)
    S.place("Connector_Generic:Conn_01x02", "J3", "PTSM 0,5/2-HH 24 VAC", 40, 300, {1: "ACR", 2: "ACC"}, footprint="pivac:PTSM_0.5_2-HH-2.5-THR")
    S.place("Device:Fuse", "F1", "PTC 1.1A 60V", 80, 300, {1: "ACR", 2: "ACF"}, footprint="pivac:PTC_Radial_P5.08_Standing")
    for ref, a, kk, x in (("D1", "ACF", "VS", 120), ("D2", "ACC", "VS", 140), ("D3", "COM", "ACF", 160), ("D4", "COM", "ACC", 180)):
        S.place("Device:D", ref, "1N4007", x, 300, {2: a, 1: kk}, footprint="Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal")
    S.place("Device:C_Polarized", "C3", "470u 63V", 210, 300, {1: "VS", 2: "COM"}, footprint="Capacitor_THT:CP_Radial_D12.5mm_P5.00mm")
    S.place("pivac:TMR12WI", "U3", "TMR 12-4811WI", 260, 300, {1: "COM", 2: "VS", 6: "+5V", 7: "GND"}, footprint="pivac:TMR12WI_SIP-8")
    S.place("Device:C", "C4", "1u", 310, 300, {1: "+5V", 2: "GND"}, footprint="Capacitor_THT:C_Rect_L7.0mm_W2.5mm_P5.00mm")
    S.place("Connector_Generic:Conn_01x02", "J4", "XH 5V OUT to Pi USB-C", 340, 300, {1: "+5V", 2: "GND"}, footprint="Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical")
    S.pwr_flags(("VCC", "GND", "VS", "COM", "+5V"), 200, 240)
    S.save()
    return S


# ------------------------------------------------------------------ EXT board, rev C
def build_extc():
    S = Sheet(os.path.join(HERE, "extc-board", "extc-board.kicad_sch"), "extc-board")
    ds, ds_pins = box_symbol("DS2482-100", [(1, "VCC"), (2, "IO"), (3, "GND"), (4, "SCL")], [(8, "AD0"), (7, "AD1"), (6, "PCTLZ"), (5, "SDA")],
                             desc="Analog Devices DS2482-100 I2C to 1-Wire bridge, SO-8")
    S.lib("pivac:DS2482-100", ds, ds_pins)
    S.text("pivac EXT board rev C: DS2482-100 1-wire master, two probe sockets, 24 VAC sense supply and the Pi's 5.1 V supply, link to the INT board", 20, 15, 3)
    S.text("Every connector at an edge is the surface-mount PTSM header with its entry face on the edge; J4 is the vertical header of the same family.", 20, 21, 1.6)
    tmr, tmr_pins = box_symbol("TMR12WI", [(1, "-Vin"), (2, "+Vin"), (3, "Remote")], [(6, "+Vout"), (7, "-Vout"), (8, "NC")],
                               desc="Traco TMR 12-4811WI isolated DC/DC, 18-75 V in, 5.1 V 2.4 A out, SIP-8")
    S.lib("pivac:TMR12WI", tmr, tmr_pins)
    S.place("pivac:DS2482-100", "U1", "DS2482-100 (0x18)", 80, 60, {1: "VCC", 2: "DATA", 3: "GND", 4: "SCL", 5: "SDA", 7: "GND", 8: "GND"}, footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm")
    S.place("Device:C", "C1", "100n", 130, 60, {1: "VCC", 2: "GND"}, footprint="Capacitor_THT:C_Rect_L7.0mm_W2.5mm_P5.00mm")
    S.text("Probe sockets PTSM 0,5/3-HH-2,5-SMD: 1 VCC, 2 DATA, 3 GND. H1 is the trunk, H2 a spare on the same bus.", 20, 160, 1.6)
    for i, ref in enumerate(("H1", "H2")):
        S.place("Connector_Generic:Conn_01x03", ref, "PTSM 0,5/3-HH-SMD", 50 + i * 45, 180, {1: "VCC", 2: "DATA", 3: "GND"}, footprint="pivac:PTSM_0.5_3-HH-2.5-SMD")
    S.text("Rollback to w1-gpio: fit R1 and bridge JP1, and GPIO4 becomes the bus data line.", 20, 215, 1.6)
    S.place("Device:R", "R1", "2k2 (not fitted)", 50, 235, {1: "VCC", 2: "DATA"}, footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", dnp=True)
    S.place("Jumper:SolderJumper_2_Open", "JP1", "GPIO4 -> DATA", 90, 235, {1: "GPIO4", 2: "DATA"}, footprint="Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm")
    S.place("Connector_Generic:Conn_01x07", "J1", "GH link to INT", 250, 60, dict(enumerate(("VCC", "SDA", "SCL", "GPIO4", "GND", "VS", "COM"), start=1)), footprint="Connector_JST:JST_GH_BM07B-GHS-TBT_1x07-1MP_P1.25mm_Vertical")
    S.place("Connector_Generic:Conn_01x03", "J2", "bus pads", 250, 110, {1: "VCC", 2: "DATA", 3: "GND"}, footprint="pivac:Pads_1x3")
    S.text("24VAC input on J3 (1 = R, 2 = C), PTC F1 in the R leg, bridge D1-D4, C3 470 uF: VS about 35 V DC against COM, out to INT on J1.6/J1.7 and into U3.", 20, 270, 1.6)
    S.text("U3 makes 5.1 V isolated for the Pi: C4 at its output, J4 (1 = +5 V, 2 = GND) to a USB-C pigtail. J3 is black and J4 white: they take the same plug.", 20, 276, 1.6)
    S.place("Connector_Generic:Conn_01x02", "J3", "PTSM 0,5/2-HH-SMD 24VAC input", 40, 300, {1: "ACR", 2: "ACC"}, footprint="pivac:PTSM_0.5_2-HH-2.5-SMD")
    S.place("Device:Fuse", "F1", "PTC 1.1A 60V", 80, 300, {1: "ACR", 2: "ACF"}, footprint="pivac:PTC_Radial_P5.08_Standing")
    for ref, a, kk, x in (("D1", "ACF", "VS", 120), ("D2", "ACC", "VS", 140), ("D3", "COM", "ACF", 160), ("D4", "COM", "ACC", 180)):
        S.place("Device:D", ref, "1N4007", x, 300, {2: a, 1: kk}, footprint="Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal")
    S.place("Device:C_Polarized", "C3", "470u 63V", 210, 300, {1: "VS", 2: "COM"}, footprint="Capacitor_THT:CP_Radial_D12.5mm_P5.00mm")
    S.place("pivac:TMR12WI", "U3", "TMR 12-4811WI", 260, 300, {1: "COM", 2: "VS", 6: "+5V", 7: "GND"}, footprint="pivac:TMR12WI_SIP-8")
    S.place("Device:C", "C4", "1u", 310, 300, {1: "+5V", 2: "GND"}, footprint="Capacitor_THT:C_Rect_L7.0mm_W2.5mm_P5.00mm")
    S.place("Connector_Generic:Conn_01x02", "J4", "PTSM 0,5/2-HV-SMD 5VDC output to Pi", 340, 300, {1: "+5V", 2: "GND"}, footprint="pivac:PTSM_0.5_2-HV-2.5-SMD")
    S.pwr_flags(("VCC", "GND", "VS", "COM", "+5V"), 200, 240)
    S.save()
    return S


# ------------------------------------------------------------------ air-handler shield
def build_ah():
    S = Sheet(os.path.join(HERE, "ah-board", "ah-board.kicad_sch"), "ah-board")
    ds, ds_pins = box_symbol("DS2482-100", [(1, "VCC"), (2, "IO"), (3, "GND"), (4, "SCL")], [(8, "AD0"), (7, "AD1"), (6, "PCTLZ"), (5, "SDA")],
                             desc="Analog Devices DS2482S-100+ I2C to 1-Wire bridge, SO-8")
    S.lib("pivac:DS2482-100", ds, ds_pins)
    tmr, tmr_pins = box_symbol("TMR3WI", [(1, "-Vin"), (2, "+Vin"), (3, "Remote")], [(6, "+Vout"), (7, "-Vout"), (5, "NC"), (8, "NC")],
                               desc="Traco TMR 3-4811WI isolated DC/DC, 18-75 V in, 5 V 0.6 A out, SIP-8")
    S.lib("pivac:TMR3WI", tmr, tmr_pins)
    opto, opto_pins = box_symbol("LTV-814S", [(1, "A/K"), (2, "K/A")], [(4, "C"), (3, "E")], width=12.7,
                                 desc="Lite-On LTV-814S AC-input optocoupler, SMD-4")
    S.lib("pivac:LTV-814S", opto, opto_pins)
    S.text("pivac air-handler node shield for the UNO R4 WiFi (docs/air-handler-shield-pcb-plan.md)", 20, 15, 3)
    S.text("24 VAC on TB1 (R, C, Y2, W2). F1, D2 TVS, D1 half-wave into C1: VS about 35 V against C (net COM). U1 isolates and feeds the R4's 5V pin.", 20, 21, 1.6)
    S.place("Connector_Generic:Conn_01x04", "TB1", "MC 1,5/4-G-3,81 24VAC", 30, 50, {4: "ACR", 3: "COM", 2: "Y2", 1: "W2"}, footprint="Connector_Phoenix_MC:PhoenixContact_MC_1,5_4-G-3.81_1x04_P3.81mm_Horizontal")
    S.place("Device:Fuse", "F1", "1812L020/60DR", 60, 50, {2: "ACR", 1: "ACF"}, footprint="Fuse:Fuse_1812_4532Metric_Pad1.30x3.40mm_HandSolder")
    S.place("Device:D_TVS", "D2", "SMAJ43CA", 85, 50, {1: "ACF", 2: "COM"}, footprint="Diode_SMD:D_SMA")
    S.place("Device:D", "D1", "S1M", 110, 50, {2: "ACF", 1: "VS"}, footprint="Diode_SMD:D_SMA")
    S.place("Device:C_Polarized", "C1", "100u 63V", 135, 50, {1: "VS", 2: "COM"}, footprint="Capacitor_SMD:CP_Elec_10x10.5")
    S.place("pivac:TMR3WI", "U1", "TMR 3-4811WI", 175, 50, {1: "COM", 2: "VS", 6: "+5V", 7: "GND"}, footprint="pivac:TMR3WI_TMR12WI_SIP-8")
    S.place("Device:C", "C2", "10u", 215, 50, {1: "+5V", 2: "GND"}, footprint="Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder")
    S.place("Device:C", "C3", "22u", 235, 50, {1: "+5V", 2: "GND"}, footprint="Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder")
    S.place("Device:R", "R16", "1k", 255, 50, {2: "+5V", 1: "PWRLED"}, footprint="Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder")
    S.place("Device:LED", "LED1", "green PWR", 275, 50, {2: "PWRLED", 1: "GND"}, footprint="LED_SMD:LED_0805_2012Metric_Pad1.15x1.40mm_HandSolder")
    S.text("Y2 and W2: 2 x 2.2k in series, LED and anti-parallel diode, 1k across the optocoupler's input, to C. Output pulled up 10k, 1 uF to GND.", 20, 90, 1.6)
    for i, (call, pin, ra, rb, rsh, led, dap, opt, rpu, cf, col) in enumerate((
            ("Y2", "D8", "R5", "R6", "R9", "LED2", "D3", "U3", "R11", "C7", "blue"),
            ("W2", "D9", "R7", "R8", "R10", "LED3", "D4", "U4", "R12", "C8", "red"))):
        y = 110 + i * 40
        a, b, c = call + "A", call + "B", call + "C"
        S.place("Device:R", ra, "2k2", 30, y, {1: call, 2: a}, footprint="Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder")
        S.place("Device:R", rb, "2k2", 55, y, {1: a, 2: b}, footprint="Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder")
        S.place("Device:LED", led, col, 80, y, {2: b, 1: c}, footprint="LED_SMD:LED_0805_2012Metric_Pad1.15x1.40mm_HandSolder")
        S.place("Device:D", dap, "1N4148W", 105, y, {1: b, 2: c}, footprint="Diode_SMD:D_SOD-123")
        S.place("Device:R", rsh, "1k", 130, y, {1: c, 2: "COM"}, footprint="Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder")
        S.place("pivac:LTV-814S", opt, "LTV-814S", 165, y, {1: c, 2: "COM", 3: "GND", 4: pin}, footprint="Package_DIP:SMDIP-4_W9.53mm")
        S.place("Device:R", rpu, "10k", 200, y, {1: pin, 2: "+5V"}, footprint="Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder")
        S.place("Device:C", cf, "1u", 220, y, {1: pin, 2: "GND"}, footprint="Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder")
    S.text("Air temperatures: 10.0k 0.1% from 5 V to each NTC on TB2, 1k to A0 and A1, 100n at the pins.", 20, 200, 1.6)
    S.place("Connector_Generic:Conn_01x04", "TB2", "PTSM 0,5/4-HH-2,5-SMD air", 30, 220, {1: "AIRS", 2: "GND", 3: "AIRR", 4: "GND"}, footprint="pivac:PTSM_0.5_4-HH-2.5-SMD")
    for j, (rd, rs, cc, node, pin) in enumerate((("R1", "R3", "C5", "AIRR", "A0"), ("R2", "R4", "C6", "AIRS", "A1"))):
        x = 70 + j * 70
        S.place("Device:R", rd, "10k0 0.1%", x, 220, {1: "+5V", 2: node}, footprint="Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder")
        S.place("Device:R", rs, "1k", x + 20, 220, {1: node, 2: pin}, footprint="Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder")
        S.place("Device:C", cc, "100n", x + 40, 220, {1: pin, 2: "GND"}, footprint="Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder")
    S.text("1-wire: DS2482 at 0x18 on SDA/SCL, bus on TB3 with VCC through F2. JP1 and R15 (not fitted) are the rollback to D2 with U2 removed.", 20, 255, 1.6)
    S.place("pivac:DS2482-100", "U2", "DS2482S-100+ (0x18)", 60, 280, {1: "+5V", 2: "OWD", 3: "GND", 4: "SCL", 5: "SDA", 7: "GND", 8: "GND"}, footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm")
    S.place("Device:C", "C4", "100n", 100, 280, {1: "+5V", 2: "GND"}, footprint="Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder")
    S.place("Device:R", "R13", "4k7", 120, 280, {1: "+5V", 2: "SDA"}, footprint="Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder")
    S.place("Device:R", "R14", "4k7", 140, 280, {1: "+5V", 2: "SCL"}, footprint="Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder")
    S.place("Device:Fuse", "F2", "1812L020/60DR", 160, 280, {1: "+5V", 2: "OWV"}, footprint="Fuse:Fuse_1812_4532Metric_Pad1.30x3.40mm_HandSolder")
    S.place("Connector_Generic:Conn_01x03", "TB3", "PTSM 0,5/3-HH-2,5-SMD 1-wire", 190, 280, {1: "OWV", 2: "OWD", 3: "GND"}, footprint="pivac:PTSM_0.5_3-HH-2.5-SMD")
    S.place("Device:R", "R15", "4k7 (not fitted)", 220, 280, {1: "OWV", 2: "OWD"}, footprint="Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder", dnp=True)
    S.place("Jumper:SolderJumper_2_Open", "JP1", "DATA -> D2", 245, 280, {1: "OWD", 2: "D2"}, footprint="Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm")
    S.text("Water meter, optional and not fitted: TB4 (+5, FLOW, GND), R17 10k pull-up, R18 100R and C9 1n into A3.", 20, 310, 1.6)
    S.place("Connector_Generic:Conn_01x03", "TB4", "PTSM 0,5/3-HH-2,5-SMD flow (not fitted)", 30, 330, {1: "+5V", 2: "FLOW", 3: "GND"}, footprint="pivac:PTSM_0.5_3-HH-2.5-SMD", dnp=True)
    S.place("Device:R", "R17", "10k (not fitted)", 70, 330, {1: "+5V", 2: "FLOW"}, footprint="Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder", dnp=True)
    S.place("Device:R", "R18", "100R (not fitted)", 95, 330, {1: "FLOW", 2: "A3"}, footprint="Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder", dnp=True)
    S.place("Device:C", "C9", "1n C0G (not fitted)", 120, 330, {1: "A3", 2: "GND"}, footprint="Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder", dnp=True)
    S.text("Arduino headers (5V, GND, A0, A1, A3, SDA, SCL, D2, D8, D9 used) and J1, the 12-pad test row.", 20, 355, 1.6)
    S.place("Connector_Generic:Conn_01x10", "J10", "SCL..D8", 30, 380, {1: "SCL", 2: "SDA", 4: "GND", 9: "D9", 10: "D8"}, footprint="pivac:ArduinoHeader_1x10")
    S.place("Connector_Generic:Conn_01x08", "J11", "D7..D0", 70, 380, {6: "D2"}, footprint="pivac:ArduinoHeader_1x8")
    S.place("Connector_Generic:Conn_01x08", "J12", "NC..VIN", 110, 380, {5: "+5V", 6: "GND", 7: "GND"}, footprint="pivac:ArduinoHeader_1x8")
    S.place("Connector_Generic:Conn_01x06", "J13", "A0..A5", 150, 380, {1: "A0", 2: "A1", 4: "A3"}, footprint="pivac:ArduinoHeader_1x6")
    S.place("Connector_Generic:Conn_01x12", "J1", "test row", 200, 380, dict(enumerate(("GND", "+5V", "D8", "D9", "A3", "A0", "A1", "OWV", "OWD", "SDA", "SCL", "GND"), start=1)), footprint="pivac:TestRow_1x12")
    for ref, x, net in (("TP1", 240, "VS"), ("TP2", 255, "COM"), ("TP3", 270, "ACF")):
        S.place("Connector:TestPoint", ref, net, x, 380, {1: net}, footprint="pivac:TestLoop")
    S.pwr_flags(("GND", "VS", "COM", "+5V", "ACR"), 300, 240)
    S.save()
    return S


if __name__ == "__main__":
    import sys
    which = sys.argv[1:] or ["int", "ext"]
    if "int" in which:
        build_int()
    if "ext" in which:
        build_ext()
    if "extc" in which:
        build_extc()
    if "ah" in which:
        build_ah()
    print("wrote", ", ".join(w + "-board.kicad_sch" for w in which))
