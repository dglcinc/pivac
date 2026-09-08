# Chiltrix shoulder-season heating — plan

**Date:** 2026-09-07.
**Status:** proposed, nothing built. The controls it relies on are read from the CX65 IOM
(pp. 37–38, 67) and the HZ-432 installation guide (69-2198), and the live Chiltrix registers were
read on 7 September; the physical checks in §5 and §8 have not been made.
**Goal:** heat the house from the Chiltrix CX75 when outdoor air is mild, from the NTI Ti-200 boiler
when it is cold, and let the changeover happen on its own with a manual override.

## 1. What the plant already allows

Source selection on the primary is only which pump runs. Each source carries its own circulator
into the header: the boiler's UP26-99F puts the boiler in circuit, and the Taco 0015 puts the
buffer tank in circuit. In cooling the Taco runs and the primary passes through the tank; in
heating today the boiler pump runs and the primary bypasses the tank for the boiler loop. Run the
Taco with the Chiltrix in heating mode and the tank is back in circuit, so the Chiltrix heats the
house through the buffer exactly as it cools it. No valve moves and no pipe changes.

The zone side is unchanged too. The HZ-432 opens each zone's valve and starts its secondary pump
on a call of either kind, and all five zones take hot water in winter, kitchen and great room
through their M3036 hydronic modules. Loop B carries three coils in heating and wants HIGH, which
is already on the seasonal list.

Two consequences follow from the geometry. The tank is a 37 gallon thermal mass at 304 BTU/°F,
so a mode change is not instant: warming it from a 50 °F cooling target to a 110 °F heating target
is about 18,000 BTU, roughly half an hour of Chiltrix output before the first heat call gets hot
water. And in heating the loop-probe offsets belong to the 140 °F column in the `config.yml`
comment rather than the 45 °F values that are live, and every ΔT on the loop panel inverts sign.

## 2. The Chiltrix side

The CX75 is a reversible heat pump rated 72,000 BTU/hr and COP 4.57 at 47 °F ambient, and it has
never heated here: register 141 reads mode 0 and register 143 holds a 50 °C heating target it has
not been asked to reach. Its external-control interface is the `C`-`H`-`COM` dry-contact block on
the main board, `DIN7` for cooling and `DIN6` for heating, enabled by `P111`, which reads 0 today.
With `P111` at 1 the block behaves as a single-stage heat-pump thermostat input in one of two
ways, chosen by relay type:

| Option | Relays | Behaviour |
|---|---|---|
| 1 | normally open | Closing `H` puts the unit in heating and runs it to the heating target; closing `C` does the same for cooling; both open is standby, and the tank drifts between calls. Chiltrix names this as a shoulder-season choice |
| 2 | normally closed | The unit stays in its last commanded mode and maintains the tank at target between calls, so the first call gets hot water at once |

Option 1 is the one that maps onto a zone call, and it is the one this plan wires. The standby
between calls is what makes the mode change safe: nothing runs until a zone asks, and the tank lag
in §1 is paid once per changeover rather than fought continuously.

Three parameters go with it. `P111` must be 1, and the IOM says the relay inputs do not override
the wired controller until it is; `C63` and `C64` on the panel show the two contact states either
way, so the first physical check is what terminal the `CHIL` relay's contact lands on today.
Register 143 sets the heating target, whole °C, and 110 to 120 °F is the range to start in
(43 to 49 °C), because the unit's own `P72` cap reads 50 °C and every degree of water above the
room costs COP. Heating AU mode (register 145, with `P48` capping the curve at 45 °C and `P49` an
offset) floats that target with outdoor air and is worth enabling once a fixed target has run a
few days. `P42`/`P43` auto switch-over cannot be combined with `C`-`H`-`COM` and stays off. `P08`
reads 1, DHW disabled, so a mode change carries no DHW state with it.

What the coils will deliver is the constraint that makes this shoulder-season only. Unico's
hydronic ratings assume 140 to 180 °F water, and a heating coil's output scales roughly with the
water-to-air temperature difference, so 120 °F water into a 70 °F room delivers about 70 % of the
140 °F rating and 110 °F water about 55 %. The Chiltrix's own capacity also falls with outdoor
temperature. The balance point in §3 is where those two curves cross the house's load, and it will
find itself by observation.

## 3. The decision point: HZ-432 dual fuel

The HZ-432 already contains the changeover logic, and this plan uses it rather than building one.
Configured as a heat pump system with dual-fuel operation, the panel calls the heat pump on `Y1`
with the changeover on `O/B` for heating above an outdoor balance temperature, and calls the fossil
stage on `W1/E` below it. The relevant settings, from the installation guide:

| Setting | Range and default | Use here |
|---|---|---|
| System type | CONV / HEATPUMP | HEATPUMP |
| Compressor stages | 1 / 2 | 1 |
| Dual fuel operation | NO / YES | YES; requires the C7089U1006 wired outdoor sensor |
| Dual-fuel heat stages | 1 / 2 | 1, the boiler |
| Zone thermostat type, per zone | HTPUMP-O, HTPUMP-B, CONVENTIONAL | CONVENTIONAL: the Prestige IAQ zones are wired as heat/cool thermostats and the panel does the changeover |
| Dual fuel changeover | OT / OT+MULTISTG | OT+MULTISTG: by outdoor temperature, and a second-stage heat call also switches to the boiler for at least an hour |
| OT balance temperature | 0 to 50 °F, default 30 | Start at 40 °F and move it on evidence |
| Changeover delay | 15 to 180 min, default 30 | 30 |
| Auto changeover delay | 15 / 20 / 30 min | 30, the arbitration when one zone calls heat and another cool in the same hour |
| Emergency Heat | button on the panel | Forces the boiler regardless of outdoor temperature |

Winter conversion is then a number or a button: raise the balance temperature to 50 °F, or press
Emergency Heat, and the boiler carries the house. Spring is the reverse. Nothing is rewired
between seasons.

The alternative, kept for the record, is a selector relay in the CDP where `W1` leaves the panel:
de-energised it passes the call to the boiler as today, energised it passes it to a relay that
closes the Chiltrix `H` contact and runs the Taco, with the coil driven by a manual switch or a
Shelly 1 Mini that pivac commands from the RedLink outdoor temperature. It fails to the boiler and
it needs no panel reconfiguration, but the balance point, the cannot-keep-up fallback and the
override would all have to be built, and the automated version puts software on the heating path.
The panel does all three already.

## 4. Wiring

Today the HZ-432's `Y1` drives the `CHIL` relay, whose poles run the Taco, close a contact on the
chiller, and feed the Pi input on BCM 25; its `W1` drives the boiler call and the `BLR` input. The
change adds one relay and moves one wire.

| Signal | Source | Does |
|---|---|---|
| `Y1` | HZ-432 equipment terminal | Energises the `CHIL` coil, as today: Taco runs on any heat-pump call, heating or cooling |
| `O/B` | HZ-432 equipment terminal, configured to energise in heating (B) | Energises a new SPDT relay `K_OB` |
| `CHIL` dry contact, common | existing pole | Goes to `K_OB` common instead of straight to the chiller |
| `K_OB` normally closed | | To the chiller's `C` terminal: a `Y1` call with `O/B` off is a cooling call |
| `K_OB` normally open | | To the chiller's `H` terminal: a `Y1` call with `O/B` on is a heating call |
| `COM` | chiller | Return for both contacts, dry, no voltage applied |
| `W1/E` | HZ-432 | Unchanged: boiler call and `BLR` |
| `K_OB` spare pole | | To a free Pi input on BCM 13, 16 or 24 as `HPHEAT`, so the dashboards know which source is heating |

The freed `Y2FAN` relay in the CDP is a plain 24 VAC relay and can serve as `K_OB`. `Y2ON` is a
timer relay and cannot. The `C`-`H`-`COM` block takes dry contacts only; the IOM warns against
applying voltage to it, and the `CHIL` contact already meets that. The jumpers Chiltrix ships on
the block come off when the relay contacts land.

The override relay that today bridges the chiller's contact keeps its role in cooling under
option 1: closed, it holds the `C` call and the unit maintains the tank between zone calls, which
is what the plant does now with `P111` at 0. Leave it open in heating, or move it to the `K_OB`
common so it follows the mode; either way label it, which is still outstanding from the relay
rework.

## 5. Sequence

1. On the Chiltrix panel, read `C63` and `C64` while `CHIL` is closed and open. That says which
   terminal the relay lands on today and whether the shipped jumpers are still fitted. Set the
   heating target to 45 °C and read register 143 back through `hvac.chiller.chiltrix.heatingTarget`.
2. Fit the C7089U1006 outdoor sensor to the HZ-432 in a shaded north location, and make the two
   changes that need no panel work: Loop B to HIGH, the 140 °F loop-probe offsets swapped in.
3. Wire `K_OB` per §4, land the `HPHEAT` pole on a free input, and add it under `pivac.GPIO`;
   `restart pivac-gpio` is all it needs.
4. Set `P111` to 1. Confirm on the panel that a `Y1` call with `O/B` off reads `C64` = 1, and with
   `O/B` on reads `C63` = 1.
5. Reconfigure the HZ-432 per §3 and run its Checkout, which energises each equipment terminal in
   turn and shows which thermostat terminals each zone raises.
6. Force one heating call on a mild evening and watch four things: register 141 goes to 1, the
   Taco runs on `CHIL`, the boiler stays quiet on `BLR`, and `UBT` climbs toward the target with
   loop supply following it after the tank lag.
7. Leave the balance temperature at 40 °F for a fortnight and read the record: zone droop,
   second-stage calls, and the Chiltrix's runtime and COP against outdoor temperature decide
   whether it moves.

## 6. pivac and the dashboards

The Modbus feed already publishes everything the changeover shows: `operatingMode`,
`heatingTarget`, `inletTemp`, `outletTemp`, `compressorHz` and `startupFlow`, which works in
heating as it does in cooling because the pump-only plateau precedes every start. `HPHEAT` joins
the relay roster and the Relays panel. `pivac.LoopDelta` needs no change to gate, since `CHIL`
closes on either call, but every ΔT it publishes reads negative in heating under the warm-minus-cold
convention; the panel's soft limits already allow it. The `chiltrix-pump-only-flow-low` and
`chiltrix-zero-flow` rules stay armed and mean the same thing. `P59` and the E14 exposure are
cooling-only and do not apply.

A heating COP falls out of the same energy balance the assessment uses in cooling: chiller output
from registers 213, 281 and 205 over the Emporia CT, with the tank term reversed in sign. Log it
against outdoor temperature from the first week, because that curve against gas cost is what sets
the balance point on economics once comfort has set its floor.

## 7. What this plan does not touch

The boiler, its pump and the Sentry path. The BOVA condensers, which cool their two zones and take
no part in heating. The buffer tank and the glycol loop, which run at 110 to 120 °F on 25 %
propylene glycol without complaint. The `.wlyt` layouts, since the SwitchBank enumerates the relay
roster on its own.

## 8. Open questions

- Which Chiltrix terminal does the `CHIL` contact land on today, and are the shipped `C`-`H`-`COM`
  jumpers still in place? `C63`/`C64` on the panel answer both.
- Does the HZ-432's `O/B` terminal energise in heating or cooling as configured here, and does the
  zone side accept CONVENTIONAL thermostat type with the Prestige IAQ wiring as installed? The
  Checkout menu shows both.
- Does the boiler's pump start from the boiler's own call input, so that dropping `W1` stops it,
  or from a separate relay that would keep it running against the Taco?
- What heating target do the Unico coils need to hold the house at 40 °F outdoor? 45 °C is the
  starting guess; the loop probes and zone droop will say.
- Has the glycol been re-measured since the 3 September top-up? The concentration sets nothing in
  heating, but the record wants it.
