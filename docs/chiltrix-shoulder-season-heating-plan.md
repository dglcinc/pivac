# Chiltrix shoulder-season heating — plan

**Date:** 2026-09-07.
**Status:** the HZ-432 is configured (heat pump, dual fuel, conventional thermostats) and the
`HPHEAT` relay is wired, proven in the panel's test mode and monitored on the Pi under the same
name, all on 8 September
2026. Still to do: the factory outdoor sensor, the override relay's position, the heating target
confirmed at 50 °C, and the live-call proof in §5. The controls are
read from the CX65 IOM (pp. 37–38, 67) and the HZ-432 installation guide (69-2198).
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
so a mode change is not instant: moving it between the 50 °F cooling target and the 122 °F heating
target is about 24,000 BTU, 25 to 45 minutes of Chiltrix output before the first heat call gets hot
water; §7 prices it. And in heating the loop-probe offsets belong to the 140 °F column in the `config.yml`
comment rather than the 45 °F values that are live, and every ΔT on the loop panel inverts sign.

## 2. The Chiltrix side

The CX75 is a reversible heat pump rated 72,000 BTU/hr and COP 4.57 at 47 °F ambient, and it has
never heated here: register 141 reads mode 0 and register 143 holds a 50 °C heating target it has
not been asked to reach. Its external-control interface is the `C`-`H`-`COM` dry-contact block on
the main board, `DIN7` for cooling and `DIN6` for heating, enabled by `P111`. The panel shows
`P111` enabled, and register 111 does not track it: it read 0 before, during and after a three-minute
disabled window on 8 September 2026 with three polls inside it, so the panel is the only reference
for this setting. With the block enabled it behaves as a single-stage heat-pump thermostat input
in one of two ways, chosen by relay type:

| Option | Relays | Behaviour |
|---|---|---|
| 1 | normally open | Closing `H` puts the unit in heating and runs it to the heating target; closing `C` does the same for cooling; both open is standby, and the tank drifts between calls. Chiltrix names this as a shoulder-season choice |
| 2 | normally closed | The unit stays in its last commanded mode and maintains the tank at target between calls, so the first call gets hot water at once |

Option 1 is the one that maps onto a zone call, and it is the one this plan wires. The standby
between calls is what makes the mode change safe: nothing runs until a zone asks, and the tank lag
in §1 is paid once per changeover rather than fought continuously. §7 gives the price.

Because the block is already enabled, the `CHIL` contact on the cooling pair is live today, and
the compressor still starts with `CHIL` open on 16 % of its starts. Under option 1 a call-driven
unit does not do that, so the override relay that bridges the cooling pair is presumably closed and
holding the `C` call; `C64` on the panel reading 1 with `CHIL` open confirms it. **That relay must
be open before the first heating call**, or `C` and `H` close together when `B` energises. Either
open it for the season or move it to the `HPHEAT` common so it follows the mode.
Register 143 sets the heating target, whole °C. Start at 50 °C (122 °F), which is where the
unit's own `P72` caps it and the most the coils can be given, so the first heating test is
unambiguous: a zone that cannot hold at 50 °C is a balance-point problem. Step down afterward if
the zones hold with runtime to spare; each °C of water is worth about 2 to 3 % of COP, and the
coils give up about 4 % of output per °C on the way down. Heating AU mode (register 145, with `P48` capping the curve at 45 °C and `P49` an
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
with `B` energised for heating above an outdoor balance temperature, and calls the fossil
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

Today the HZ-432's `Y1` drives the `CHIL` relay, whose poles run the Taco, close the chiller's
`C`-`COM` cooling contacts, and feed the Pi input on BCM 25; its `W1` drives the boiler call and
the `BLR` input. A second pair is already run from the CDP to the chiller's `H`-`COM` heating
contacts and is not yet driven, and the jumpers Chiltrix ships on the block are out. The change
adds one relay and moves one wire: the `CHIL` contact's run to the cooling pair goes through the
new relay, which steers it to the cooling pair or the heating pair.

| Signal | Source | Does |
|---|---|---|
| `Y1` | HZ-432 equipment terminal | Energises the `CHIL` coil, as today: Taco runs on any heat-pump call, heating or cooling |
| `B` | HZ-432 equipment terminal. The panel carries separate `O` and `B` equipment terminals: `O` energises in cooling and `B` in heat-pump heating, confirmed 8 September 2026 with a zone cooling call (25.6 VAC on `Y1` and `O`, `B` dark) and the panel's Checkout heat-stage test (`B` energised) | Energises the SPDT relay `HPHEAT` in heating; the relay rests in cooling |
| `CHIL` dry contact, common | existing pole | Goes to `HPHEAT` common instead of straight to the cooling pair |
| `HPHEAT` normally closed, the rest state | | To the existing cooling pair, `C`-`COM`: `Y1` without `B` is a cooling call |
| `HPHEAT` normally open, closed while `B` is energised | | To the existing heating pair, `H`-`COM`: `Y1` with `B` is a heating call. A lost `B` wire reads as cooling, the safer of the two failure modes |
| `COM` | chiller | Return for both contacts, dry, no voltage applied |
| `W1/E` | HZ-432 | Unchanged: boiler call and `BLR` |
| `HPHEAT` spare pole | | To J3.3 on the I/O board, BCM 24, as `HPHEAT`, so the dashboards know which source is heating |

Wired and checked 8 September 2026: the relay follows `B`, and the `CHIL` contact reaches the
cooling pair at rest and the heating pair with `B` energised.

The freed `Y2FAN` relay in the CDP is a plain 24 VAC relay and can serve as `HPHEAT`. `Y2ON` is a
timer relay and cannot. The `C`-`H`-`COM` block takes dry contacts only; the IOM warns against
applying voltage to it, and the `CHIL` contact already meets that.

The override relay that bridges the cooling pair keeps its role in cooling under option 1:
closed, it holds the `C` call and the unit maintains the tank between zone calls, which is what
the plant does now. It must not hold `C` while `B` selects `H`, so leave it open in heating, or
move it to the `HPHEAT` common so it follows the mode; either way label it, which is still
outstanding from the relay rework. `P112`, the on-board auto switch-over, shows disabled for both
heating and cooling on the panel and stays that way, since it cannot be combined with
`C`-`H`-`COM` control.

## 5. Sequence

1. On the Chiltrix panel, read `C63` and `C64` while `CHIL` is closed and open. `C64` should
   follow `CHIL`, since that relay lands on the cooling pair, and `C63` should stay 0 until the
   heating pair is driven; that proves the contacts register. The IOM's own preconditions for
   relay control (p. 38) are met or become so here: DHW is disabled at `P08`, `P112` auto
   switch-over is off, `P111` is enabled, and each mode's target is set from the controller
   before the relays are relied on. Use the Mode button to enter heating, confirm the heating
   target at 50 °C, return to cooling, and read register 143 back through
   `hvac.chiller.chiltrix.heatingTarget`. The IOM adds that the controller's schedule timers are
   unavailable under relay control, which changes nothing here.
2. Fit the C7089U1006 outdoor sensor to the HZ-432 in a shaded north location, and make the two
   changes that need no panel work: Loop B to HIGH, the 140 °F loop-probe offsets swapped in.
3. `HPHEAT` is wired per §4 and proven with the HZ-432's test mode. Its `HPHEAT` pole is on J3.3,
   BCM 24, and publishes as `electrical.ac.switch.utility.HPHEAT` since 8 September.
4. Open the override relay, or move it to the `HPHEAT` common. Confirm on the Chiltrix panel that
   `C64` is 0 with no call, 1 on a `Y1` call with `B` off, and that `C63` is 1 on a `Y1` call with
   `B` on.
5. Reconfigure the HZ-432 per §3 and prove the heating side of the changeover with a real
   call: with the outdoor sensor reading above the balance temperature, a zone heat call should
   put 24 VAC on `Y1` and `B` and none on `W1/E`; with Emergency Heat pressed, 24 VAC on `W1/E`
   and none on `Y1`. Checkout steps 11 to 14 show which terminals each zone thermostat raises.
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

## 7. The cost of a changeover

Every changeover moves the buffer tank between the two targets, and the tank does not drift far
enough between calls to shorten the trip. Its 2" of polyurethane on about 27 ft² of shell gives a
UA near 2 BTU/hr·°F, perhaps 4 with the fittings and primary piping, so the time constant is about
three days and an overnight idle moves it 5 to 8 °F. The full swing is therefore paid at every
changeover.

The mass the chiller has to move is 304 BTU/°F for the tank, about 5 gallons in the exchanger and
primary piping, and the calling secondary loop, which the first call brings into circuit: 200 ft of
1¼" PEX holds about 9 gallons. Call it 350 to 400 BTU/°F. Cooling holds the tank between 43 and
53 °F and heating targets 122 °F at the return.

| Direction | Swing | Chiller output | Compressor time | Electricity | At 18 ¢/kWh |
|---|---|---|---|---|---|
| Cool → heat, 48 → 122 °F | 74 °F | 26,000 to 29,000 BTU | 30 to 45 min | 2.3 kWh (2.0 to 2.8) | 41 ¢ (36 to 50) |
| Heat → cool, 122 → 45 °F | 77 °F | 27,000 to 30,000 BTU | 25 to 40 min | 1.6 kWh (1.4 to 1.9) | 29 ¢ (25 to 34) |

The output rate assumes the inverter runs near its ceiling against a 70 °F error: cooling has
measured 55,400 BTU/hr at p99 and 3,740 W peak, and in heating the 72,000 BTU/hr rating is at
47 °F ambient and cooler water than 122 °F, so 40,000 to 55,000 BTU/hr is the working range,
stretched by defrost below about 45 °F outdoor. Heating at 122 °F loses 2 to 3 % of COP per °C
above the rating point, which puts the COP near 3.0 against the rated 4.57. Cooling is priced at
the measured EER of 16.8 above 2,500 W, and the first part of a pull-down runs better than that
because warm return water raises evaporator capacity.

A shoulder day that heats in the morning and cools in the afternoon pays both, about 3.9 kWh or
70 ¢. The chiller averaged about 17 kWh a day, $3.06, over the clean cooling week (1,492 W mean
running at 47 % duty), so two changeovers a day cost a quarter of a summer day's chiller
electricity on days whose own load is small. The HZ-432's 30 minute changeover delay is the only
thing rationing this. If the record shows changeovers on most shoulder days, widen the deadband or
lengthen the delay on the panel, or hold one mode for the day.

The first call feels the pull-down. Under option 1 the zone fan runs throughout, and a coil's output
scales with the water-to-air difference, so in heating it delivers nothing until the water passes
room temperature, about 10 minutes in, and about half its 122 °F output once the water reaches
100 °F, around 20 minutes in. Going to cooling the coil is useful within a few minutes because the
tank passes 70 °F early on the way down.

Two things would change these numbers. The heating target is assumed to be a return-water target
like register 142; step 1 of §5 reads register 143 back. Pulling 122 °F glycol through the
evaporator on the first cooling call may trip a high-inlet limit in the cooling logic, and neither
the IOM notes here nor the Modbus record shows one, so watch `r284` and `operatingMode` on the
first heat-to-cool changeover. The heating COP and the pull-down rate are estimates until the first
week's energy balance in §6 replaces them.

## 8. What this plan does not touch

The boiler, its pump and the Sentry path. The BOVA condensers, which cool their two zones and take
no part in heating. The buffer tank and the glycol loop, which run at 110 to 120 °F on 25 %
propylene glycol without complaint. The `.wlyt` layouts, since the SwitchBank enumerates the relay
roster on its own.

## 9. Open questions

- Does the boiler's pump start from the boiler's own call input, so that dropping `W1` stops it,
  or from a separate relay that would keep it running against the Taco?
- How far below 50 °C can the heating target go with the zones still holding at 40 °F outdoor?
  The loop probes, zone droop and the Modbus COP against outdoor temperature will say.
- Has the glycol been re-measured since the 3 September top-up? The concentration sets nothing in
  heating, but the record wants it.
