# Replacement lever for the chilled-water ball valves

Two A.Y. McDonald brass ball valves on the chilled-water side (600 WOG / 150 WSP, yellow vinyl grip) have plated steel levers rusted through at the hub. The stems sweat at loop temperature, and the vinyl grip holds the condensate against the steel. The replacement is a 316 stainless lever cut flat and bent by hand. It is not urgent; the old levers still turn the valves.

The files are in `hardware/valve-lever/`. `make_lever.py` writes both outputs beside itself and needs `ezdxf`; every dimension below is a constant at the top of the script.

| File | Use |
|------|-----|
| `valve-lever-316.dxf` | Cut file: outline and hole only, mm |
| `valve-lever-1to1.svg` | Full-size print with bend lines; check the 50 mm bar after printing |
| `old-lever-bench.jpg` | The old lever's head from the valve side, the source of the lug geometry |
| `old-lever-side.jpg` | The old lever installed, side view, showing the jog |

## The valve

The stem is a double-D, 5 mm across the flats and 8 mm across the round, with the flats parallel to the lever. It takes an M8×1.25 nut. Two stop lugs on the lever's head bear on a boss on the valve neck at open and closed. A.Y. McDonald sells a stainless handle, 72032SSH, only for its Model 72032 valves. Watts ILHK-SS 1/4 to 1/2 is the nearest catalog stainless kit, but it is made for Watts FBV valves and is hard to find in stock.

## The part

| Feature | Dimension |
|---------|-----------|
| Material | 316 stainless, 0.120" (3.05 mm) |
| Reach | 100 mm, hole centre to tip, parallel to the valve face |
| Head | 20 mm wide, back edge 10 mm behind the hole centre, first bend 15 mm ahead of it |
| Hole | Double-D, 8.1 mm across the round, 5.1 mm across the flats, flats parallel to the lever |
| Jog | 60° ramp 17.3 mm long, grip 15 mm off the face |
| Grip | 16 mm wide, round tip |
| Lug A | 5 × 7 mm on the back edge, centred 4.8 mm right of the hole centre |
| Lug B | 5 × 7 mm on the left edge, centred 3.9 mm toward the grip |
| Bend reliefs | 1.6 × 1.5 mm at each lug root |
| Flat length | 125.7 mm |

The face is the head plate that sits against the valve body. Lug positions are stated in the outside view, the side facing you on the valve, with the grip pointing down. They were measured off `old-lever-bench.jpg` with the 8 mm hole as the scale and are good to about ±1 mm. The part is chiral: bending the lugs toward the outside face puts lug B on the wrong side.

## Before ordering

1. Print the SVG at 100 % and lay the old lever on it, outside face up and grip down. Check the hole, both lugs and the ramp angle; change `RAMP_DEG` if the old ramp is nearer 45°.
2. Upload the DXF to SendCutSend and Xometry for quotes. SendCutSend's order minimum is $39, which sets the price at two levers, so quote four or five for spares.
3. Order the parts flat. The lugs are likely shorter than SendCutSend's minimum flange for 3 mm stainless.

## Bending

1. Bend both lugs 90° toward the valve, away from you with the outside face up.
2. Try the lever on the valve and file a lug if the valve closes short of its stop.
3. Bend the jog: 60° at the first line so the grip side comes toward you, then 60° back at the second so the grip runs parallel to the head.

Fit with an A4 stainless M8×1.25 nylon-insert lock nut (13 mm). Leave the grip bare or keep any sleeve short, so no condensate is held against the hub.
