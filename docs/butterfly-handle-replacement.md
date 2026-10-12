# Replacement butterfly handle for the red-handled drain valves

The hose-end drain ball valves on the chilled-water piping carry a red cast butterfly handle held by an M6×1 nut. One handle's wings broke off at the base. No catalog handle publishes a matching hole, so this part copies the broken base and adds longer wings that rise clear of the pipe insulation. `hardware/butterfly-handle/` holds the generator (`make_handle.py`, needs `cadquery`), the STEP and STL to order from, and a 1:1 SVG to check against the old base.

## The valve

The bonnet ends in a ring 19 mm in outside diameter with a 2 mm wall, 7 mm tall outside. Inside it a white PTFE packing washer sits 2 mm below the rim. The stem rises out of the washer as a double-D drive stub, with an M6×1 thread above it. The handle slides down over the thread onto the drive, and the nut clamps it. The ring runs in an annular groove in the handle's underside, while the handle's boss drops inside the ring onto the washer. The ring has a lowered sector, visible on the left of IMG_1881 and IMG_1884, and a lug hanging from the groove floor stops the handle at each end of it.

## The part

| Feature | Value | Source |
|---|---|---|
| Base | 26.42 mm OD, 8.20 mm tall | Old base |
| Stem hole | Double-D, 7.30 mm across the flats, 9.20 mm across the round | Old base 7.16 × 9.08 mm, plus clearance |
| Groove | 13.74 mm ID, 19.51 mm OD, 4.3 mm deep | Old base 3.8 mm deep, deepened so the rim cannot bottom |
| Boss | Set back 2.0 mm from the skirt face | Ring 2 mm deep inside; to confirm on the old base |
| Stop lug | 7.93 mm wide across the groove, reaching 1.5 mm down from the groove floor, on the hole's long axis | Width from the old base; depth estimated, must clear the cutaway floor |
| Wings | 85 mm span, 10 mm thick blades, rising at 20° to 24.8 mm overall height | New; the original spanned 63 mm |
| Socket clearance | Nothing inside 9 mm radius above the nut face | Fits a 10 mm socket |
| Volume | 10.4 cm³, about 83 g in 316L | Model |

The underside drawing is seen from the valve. The lug and both wings lie on the double-D's long axis, the axis through its round ends. That placement is read from the old base, where the lug and the two wing fractures sit on that axis. The wings rise so the grip clears the insulation over most of the quarter turn. Where a wing meets the insulation, the foam compresses.

The wider span gives 35 % more leverage than the 63 mm original. The blade root carries the same bending moment for a given valve torque whatever the span, because a longer wing needs less hand force.

## Material

Order it printed in 316L stainless (SLM, from JLC3DP or Xometry). It does not rust, and at 10 N·m, the most a stiff ¾" ball valve should need, the blade root sees about 50 MPa, against roughly 500 MPa yield for printed 316L. The double-D flats are about 5 mm long by 8 mm deep and bear 18–36 MPa at 5–10 N·m, which steel carries indefinitely.

PA12 nylon (MJF) is the cheaper option, and it insulates against condensation. At those bearing stresses it creeps, though, and the hole rounds out over the years. If it is printed in PA12, put a stainless washer under the nut and expect to replace it.

## Before ordering

1. Confirm three depths, which the model takes from photos: on the old base, the skirt face to the boss face (`BOSS_RECESS`) and the groove floor to the lug face (`LUG_H`); on the valve, the rim to the cutaway floor, which `LUG_H` must be less than. Also measure the rim to the top of the drive stub. The hub is 6.2 mm long from the boss face to the nut face, and the stub must not stand much taller than that above the washer, or the nut lands on the stub's shoulder and leaves the handle loose.
2. Print `butterfly-handle-1to1.svg` at 100 % and check the 10 mm scale bar with the caliper.
3. Lay the old base face down on the underside view. The groove, the lug and the double-D should line up with the base's. In particular, the lug should sit on the hole's long axis. If the lug sits on the flats' axis instead, rotate the lug in `make_handle.py` onto the y axis, rebuild, and order from the regenerated STEP.
4. Ask for the hole and the groove to be held to ±0.1 mm. If the printer cannot hold that, order the hole 0.2 mm undersize and file the flats to fit the stem.
