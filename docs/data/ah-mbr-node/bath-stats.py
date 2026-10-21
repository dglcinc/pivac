import re, sys, statistics as s
log, anchor = sys.argv[1], float(sys.argv[2])
rows=[]
for l in open(log):
    m=re.search(r'(\d\d:\d\d:\d\d) ds\[0\] ([\d.]+)F\s+ds\[1\] ([\d.]+)F.*A0 (\d+) cts (\d+) ohm ([\d.]+)F.*A1 (\d+) cts (\d+) ohm ([\d.]+)F',l)
    if m: rows.append((m.group(1),)+tuple(float(x) for x in m.groups()[1:]))
print("rows",len(rows),rows[0][0],"to",rows[-1][0])
# per-minute means to see the plateau
for i in range(0,len(rows),60):
    seg=rows[i:i+60]
    print(f"{seg[0][0]} ds0 {s.mean(r[1] for r in seg):6.2f} ds1 {s.mean(r[2] for r in seg):6.2f} A0 {s.mean(r[5] for r in seg):6.2f} ({s.mean(r[4] for r in seg):6.0f} ohm) A1 {s.mean(r[8] for r in seg):6.2f} ({s.mean(r[7] for r in seg):6.0f} ohm)")
w=rows[-180:]  # last 3 min
print("\nlast 5 min window", w[0][0], "to", w[-1][0])
PA5A_K, PA5B_K = 0.320, 0.089
d0=[r[1] for r in w]; d1=[r[2] for r in w]; a0=[r[5] for r in w]; a1=[r[8] for r in w]; o0=[r[4] for r in w]; o1=[r[7] for r in w]
for n,v in (("PA5A ds0",d0),("PA5B ds1",d1),("A0 sup F",a0),("A1 ret F",a1),("A0 ohm",o0),("A1 ohm",o1)):
    print(f"{n:9s} mean {s.mean(v):9.3f} sd {s.pstdev(v):6.3f} min {min(v):8.2f} max {max(v):8.2f}")
m0,m1=s.mean(d0),s.mean(d1)
print(f"\nPA5A raw-anchor {m0-anchor:+.3f} F  ice offset applied -> {m0+PA5A_K*1.8-anchor:+.3f} F residual")
print(f"PA5B raw-anchor {m1-anchor:+.3f} F  ice offset applied -> {m1+PA5B_K*1.8-anchor:+.3f} F residual")
print(f"pair A-B raw {m0-m1:+.3f} F  (ice pair correction +0.415 -> corrected {m0-m1+0.415:+.3f} F)")
print(f"new offsets at {anchor} F: PA5A {anchor-m0:+.3f} F = {(anchor-m0)/1.8:+.3f} K, PA5B {anchor-m1:+.3f} F = {(anchor-m1)/1.8:+.3f} K")
print(f"\nNTC error vs anchor: A0 {s.mean(a0)-anchor:+.2f} F  A1 {s.mean(a1)-anchor:+.2f} F;  A0-A1 {s.mean(a0)-s.mean(a1):+.2f} F")
