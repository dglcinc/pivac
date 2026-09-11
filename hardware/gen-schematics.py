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
    S.text("pivac INT board rev A: relay-sense inputs on LTV-847 optocouplers, 24 VAC sense supply", 20, 15, 3)
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
            S.text(f"{plug + '.' + str(pos) if plug else 'J8'} > G{bcm} (p{pin})", x + 52 + (c - 1) * 30, y + 13, 1.0)
        S.place("pivac:LTV-847", f"U{k}", "LTV-847", x, y, nets, footprint="Package_DIP:DIP-16_W7.62mm_Socket")

    # plugs
    S.text("Field plugs, PTSM 0,5/4-HH-2,5-THR; position 4 is COM on every plug; J4.1/J4.2 take the 24 VAC", 20, 225, 1.6)
    for i, (j, xc) in enumerate(T.PLUG_X.items()):
        nets = {4: "COM"}
        for name, plug, pos, bcm, pin in T.CHANNELS:
            if plug == j:
                nets[pos] = f"S_{name}"
        if j == "J4":
            nets[1], nets[2] = "ACR", "ACC"
        S.place("Connector_Generic:Conn_01x04", j, "PTSM 0,5/4-HH", 40 + i * 45, 240, nets, footprint="pivac:PTSM_0.5_4-HH-2.5-THR")
    S.place("Connector_Generic:Conn_01x03", "J8", "spare ch pads", 220, 240, {1: "S_SP-C", 2: "S_SP-E", 3: "COM"}, footprint="pivac:Pads_1x3")

    # supply
    S.text("24 VAC sense supply: PTC, MOV (not fitted), full-wave bridge, 220 uF; VS is about 35 V DC, COM its return", 250, 225, 1.6)
    S.place("Device:Fuse", "F1", "PTC 0.1A", 270, 245, {1: "ACR", 2: "ACF"}, footprint="pivac:PTC_Radial_P5.08")
    S.place("Device:Varistor", "RV1", "MOV 39V", 295, 245, {1: "ACF", 2: "ACC"}, footprint="pivac:MOV_Radial_P5.0", dnp=True)
    for ref, a, kk, x in (("D1", "ACF", "VS", 320), ("D2", "ACC", "VS", 340), ("D3", "COM", "ACF", 360), ("D4", "COM", "ACC", 380)):
        S.place("Device:D", ref, "1N4007", x, 245, {2: a, 1: kk}, footprint="Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal")
    S.place("Device:C_Polarized", "C1", "220u 50V", 400, 245, {1: "VS", 2: "COM"}, footprint="Capacitor_THT:CP_Radial_D10.0mm_P5.00mm")

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
    S.text("Shadow column J9: one pad per header row (rows 1, 2, 16, 18 empty)", 250, 185, 1.6)
    S.place("Connector_Generic:Conn_01x20", "J9", "breakout", 290, 210, {i: e[2] for i, e in enumerate(T.BREAKOUT, start=1) if e},
            footprint="pivac:Shadow_1x20", hide_value=True)
    S.place("Connector_Generic:Conn_01x05", "J6", "LINK to EXT", 400, 120, dict(enumerate(("3V3", "SDA", "SCL", "GPIO4", "GND"), start=1)), footprint="pivac:PTSM_0.5_5-HH-2.5-THR")
    S.place("Connector_Generic:Conn_01x04", "J7", "PWR link (not fitted)", 400, 160, dict(enumerate(("VS", "COM", "+5V", "GND"), start=1)), footprint="pivac:PTSM_0.5_4-HH-2.5-THR", dnp=True)
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
    S.text("pivac EXT board rev A: DS2482-100 1-wire master, three probe sockets, link to the INT board", 20, 15, 3)
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
    S.place("Connector_Generic:Conn_01x05", "J1", "LINK to INT", 250, 60, dict(enumerate(("VCC", "SDA", "SCL", "GPIO4", "GND"), start=1)), footprint="pivac:PTSM_0.5_5-HH-2.5-THR")
    S.place("Connector_Generic:Conn_01x03", "J2", "bus pads", 250, 110, {1: "VCC", 2: "DATA", 3: "GND"}, footprint="pivac:Pads_1x3")
    S.pwr_flags(("VCC", "GND"), 200, 240)
    S.save()
    return S


if __name__ == "__main__":
    build_int()
    build_ext()
    print("wrote int-board.kicad_sch and ext-board.kicad_sch")
