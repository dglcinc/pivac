#!/usr/bin/env python3
"""Regenerate the rows of PhoenixContact-BC-RPI-label.docx (in this script's directory).

The docx is its own template: the script opens it, keeps every style, the page setup and the
empty side shape, and replaces the rows of the single table with the ROWS list below; the last
row carries the Pi's eth0 MAC. Run it after any change to the channel map (docs/rpi-io-board-design.md
§2.1 and §4.3) or the 1-wire sockets (docs/ds18b20-bus-topology.md §5.1 and §5.5).

Each row is "left text" and an optional right-aligned "(BCM,phys)"; a row of None is a spacer.
"""
import os, re, shutil, tempfile, zipfile

MAC = "2c:cf:67:80:55:00"          # new Pi eth0, read on the bench 2026-09-06

ROWS = [
    ("J1.1  ZV",        "(17,11)"),
    ("J1.2  DHW",       "(27,13)"),
    ("J1.3  BLR",       "(22,15)"),
    ("J1.4  24V COM",   None),
    ("J2.1  CHIL",      "(25,22)"),
    ("J2.2  BOS1",      "(6,31)"),
    ("J2.3  BOS2",      "(5,29)"),
    ("J2.4  24V COM",   None),
    ("J3.1  DEHUM",     "(12,32)"),
    ("J3.2  SP-A",      "(23,16)"),
    ("J3.3  SP-B",      "(24,18)"),
    ("J3.4  24V COM",   None),
    ("J4.1  +14V IN",   None),
    ("J4.2  SP-C",      "(13,33)"),
    ("J4.3  SP-D",      "(19,35)"),
    ("J4.4  24V COM",   None),
    None,
    ("H1  VCC·DATA·GND  trunk", None),
    ("H2  VCC·DATA·GND  spare", None),
    ("H3  VCC·DATA·GND  spare", None),
    ("LINK  3V3·SDA·SCL·sp·GND", None),
    None,
    (f"eth0  {MAC}", None),
]

HERE = os.path.dirname(os.path.abspath(__file__))
DOCX = os.path.join(HERE, "PhoenixContact-BC-RPI-label.docx")

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

with zipfile.ZipFile(DOCX) as z:
    names = z.namelist()
    parts = {n: z.read(n) for n in names}
xml = parts["word/document.xml"].decode("utf8")

rows = re.findall(r"<w:tr[ >].*?</w:tr>", xml, flags=re.S)
tmpl = next(r for r in rows if "<w:tab/>" in r)          # a "name <tab> (bcm,phys)" row
runs = re.findall(r"<w:r>.*?</w:r>|<w:r [^>]*>.*?</w:r>", tmpl, flags=re.S)
run_text = next(r for r in runs if "<w:t" in r)           # a text run to clone
run_tab = next(r for r in runs if "<w:tab/>" in r)
para_open = tmpl[: tmpl.index(runs[0])]                   # <w:tr …><w:tc>…<w:p …><w:pPr>…</w:pPr>
para_close = tmpl[tmpl.index(runs[-1]) + len(runs[-1]):]  # </w:p></w:tc></w:tr>

def text_run(s):
    return re.sub(r"<w:t[^>]*>[^<]*</w:t>", f'<w:t xml:space="preserve">{esc(s)}</w:t>', run_text, count=1)

def row(left, right):
    body = text_run(left)
    if right:
        body += run_tab + text_run(right)
    return para_open + body + para_close

new_rows = [row(" ", None) if r is None else row(*r) for r in ROWS]
tbl = re.search(r"<w:tbl>.*?</w:tbl>", xml, flags=re.S).group(0)
first = tbl.index(rows[0]); last = tbl.index(rows[-1]) + len(rows[-1])
new_tbl = tbl[:first] + "".join(new_rows) + tbl[last:]
xml = xml.replace(tbl, new_tbl)

parts["word/document.xml"] = xml.encode("utf8")
tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx", dir=HERE).name
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
    for n in names:
        z.writestr(n, parts[n])
shutil.move(tmp, DOCX)
print(f"wrote {os.path.basename(DOCX)}: {len(ROWS)} rows, MAC {MAC}")
