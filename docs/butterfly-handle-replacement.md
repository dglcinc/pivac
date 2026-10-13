# Replacement butterfly handle for the red-handled drain valves

The hose-end drain ball valves on the chilled-water piping carry a red cast butterfly handle held by an M6×1 nut. One handle's wings broke off at the base. No catalog handle publishes a matching hole, so this part copies the broken base and adds longer wings that rise clear of the pipe insulation. `hardware/butterfly-handle/` holds the generator (`make_handle.py`, needs `cadquery`), the STEP and STL to order from (PA12 and 316L versions), and a 1:1 SVG to check against the old base.

## The valve

The bonnet ends in a ring 19 mm in outside diameter with a 2 mm wall, 7 mm tall outside. Inside it a white PTFE packing washer sits 2 mm below the rim. The stem rises out of the washer as a 5 × 8 mm double-D drive, and the M6×1 thread starts 2.5 mm above the rim. The flats run on up through the thread, so the handle slides down over it onto the drive, and the nut clamps it. The handle's boss drops inside the ring and bears on the washer, so the ring stands 2 mm into an annular groove in the handle's underside and the skirt hangs 2 mm down the outside of the ring, clear of the bonnet body. The ring has a lowered sector 2.2 mm deep, visible on the left of IMG_1881 and IMG_1884, and a lug filling the groove stops the handle at each end of it.

## The part

| Feature | Value | Source |
|---|---|---|
| Base | 26.42 mm OD, 8.20 mm tall | Old base |
| Stem hole | Double-D, 4.90 mm across the flats, 8.00 mm across the round, filed to fit | Stem 5 × 8; overlay on IMG_1891; printed under for SLM's ±0.2 mm |
| Groove | 13.74 mm ID, 19.51 mm OD, 4.0 mm deep | Old base 3.8 mm; 2 mm clear above the rim |
| Boss | Flush with the skirt face | Old base |
| Stop lug | Radial spoke from boss to skirt, its sides in line with the hole's flats, on the hole's long axis, ending 0.3 mm short of the skirt face | Old base, flush; shortened to clear the cutaway floor by 0.5 mm |
| Nut seat | 5.5 mm above the boss face, in an 18 mm recess | Old base 5.5 mm; 1.0 mm above the thread start |
| Wings | 85 mm span, 10 mm thick blades, rising at 20° to 24.8 mm overall height | New; the original spanned 63 mm |
| Socket clearance | Nothing inside 9 mm radius above the nut face | Fits a 10 mm socket |
| Volume | 10.1 cm³, about 81 g in 316L | Model |

The underside drawing is seen from the valve. The lug and both wings lie on the double-D's long axis, the axis through its round ends. That placement is read from the old base, where the lug and the two wing fractures sit on that axis. The wings rise so the grip clears the insulation over most of the quarter turn. Where a wing meets the insulation, the foam compresses.

The nut seat is the one depth that must not be printed thin. Below 4.5 mm above the boss face the nut lands on the shoulder of the flats and leaves the handle loose.

The wider span gives 35 % more leverage than the 63 mm original. The blade root carries the same bending moment for a given valve torque whatever the span, because a longer wing needs less hand force.

## Material

The handle is ordered in 316L stainless, SLM, from JLC3DP, from `butterfly-handle.step`. It quoted $18, against $29 for PA12 MJF and $178 for 316L DMLS at Xometry. 316L does not rust on a sweating pipe, and at 10 N·m, the most a stiff ¾" ball valve should need, the blade root sees about 50 MPa against roughly 500 MPa yield. SLM holds about ±0.2 mm, so the drive prints at 4.90 × 8.00 mm, to be filed open to fit the 5 × 8 stem; play there would cost leverage. The lug is 5.05 mm wide, the stem's width. 316L files more easily than 17-4, which is also less resistant to a sweating pipe.

`butterfly-handle-pa12.step` is the nylon version. MJF holds about ±0.3 mm, so it prints the drive at 4.80 × 7.90 mm and opens the groove to 19.90 mm so the 19 mm ring cannot bind. PA12 is near its strength at the wing root at 10 N·m and creeps at the flats, so it needs a stainless washer under the nut and eventual replacement.

## Before ordering

1. Print `butterfly-handle-1to1.svg` at 100 % and check the 10 mm scale bar with the caliper.
2. Lay the old base face down on the underside view. The groove, the lug and the double-D should line up with the base's. In particular, the lug should sit on the hole's long axis. If the lug sits on the flats' axis instead, rotate the lug in `make_handle.py` onto the y axis, rebuild, and order from the regenerated STEP.
3. In the order notes, ask for the hole and the groove to be left clean of support material, the hole held to size or undersize, and the boss face and nut seat flat.
4. When it arrives, file the flats of the hole a few strokes at a time until the handle slides onto the stem with no play.
