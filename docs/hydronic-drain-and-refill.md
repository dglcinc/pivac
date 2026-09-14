# Hydronic loop — drain and refill procedure

The shared four-pipe loop (Ti-200 boiler, CX75 chiller with its VCT37C buffer tank, two
secondary PEX loops, six Unico air-handler coils) holds about 86 gallons of 25 % propylene
glycol. This is the procedure for emptying it as completely as a house system allows, and
refilling it from a drum of pre-mixed fluid with a portable pump instead of the autofill.
System facts are from `docs/unico-cooling-assessment-and-tuning.md` §2 and §3.5; the
glycol and pressure rules are in `CLAUDE.md` under Chiltrix CX75.

## 1. Numbers the procedure rests on

| Item | Value | Source |
|---|---|---|
| Loop volume | about 86 gal | David's estimate, 2026-09-03 top-up |
| Buffer tank | 37 gal (Chiltrix VCT37C) | assessment §3 |
| Each secondary loop | about 9 gal in 200 ft of 1¼" PEX | assessment §2.2 |
| System high point | attic coil, about 25 ft above the boiler gauge | assessment §3.5 |
| Static head to the attic coil | 10.8 psi | 25 ft ÷ 2.31 |
| Cold fill pressure | 21–23 psi at the boiler gauge | `CLAUDE.md`, glycol top-up rule |
| Head the fill pump must make at zero flow | 53 ft (23 psi × 2.31) | |
| Boiler relief valve | 30 psi (confirm on the valve tag) | Ti-200 standard fitting |
| Glycol target | 30 % PG (freezes about −13 °C) | assessment §7.1; 25 % sits on the −10 °C line P109 = 1 is conditioned on |
| Concentrate for 30 % of 86 gal | about 26 gal, or the equivalent premixed | |

## 2. The fill pump

Pacific Hydrostar 65836 (Harbor Freight): 1/2 HP, 115 V, 8.4 A, 1,500 GPH (25 gpm) maximum,
120 ft maximum head, 1" × 11.5 TPI ports, cast iron, clean liquids only. At the 53 ft the full
system presents it delivers roughly 10–15 gpm, which is above the 4–6 gpm that gives 2 ft/s
scouring velocity in 1" and 1¼" PEX, so it fills to the attic and purges every loop with margin.

Dead-headed it makes about 52 psi, above the boiler's relief setting, so the discharge carries a
ball valve throttled against the boiler gauge, and that valve is closed before the pump is
switched off. A running centrifugal pump against a closed valve is harmless for a minute.

Set it up as a closed purge cart:

- Reservoir: a clean 32–55 gal drum. Jugs are too small; the pump empties 5 gal in about 20 s
  and gulps air when a jug runs dry, and that air goes straight into the loop.
- Suction: short hose, submerged, with the pump below the drum's water line.
- Discharge: ball valve, then hose to a boiler-drain fitting downstream of the autofill's
  pressure-reducing valve, with the autofill isolated. A 1" to ¾" GHT adapter is needed at the
  pump.
- Purge return: hose from the purge cock in use back into the drum, so purged fluid is not lost.

Propylene glycol is fine through the pump. Rinse it afterwards; the old fluid carries the 8-Way
treatment's caustic and nitrite.

## 3. Draining

Gravity alone leaves about a quarter of the fluid behind, in the coil circuits, the sags of the
PEX runs, the plate exchanger and the boiler. The order below gets most of that out.

1. Breaker off at the chiller; boiler off; both secondary circulators off. Close the autofill's
   isolation valve so the domestic side cannot refill behind the drains.
2. Open every zone valve so all six coils are in circuit. Use the HZ-432 valves' manual-open
   lever, or power them. A closed zone valve traps its coil full.
3. Open the high points first so air can enter as fluid leaves: the attic coil vent, each
   coil's manual vent, the tank's top vent and the air separator's cap.
4. Open the low points: boiler drain, buffer tank drain, the CX75 hydronic-module drain plugs
   (the IOM's winterising section names them), the purge cocks at the foot of each secondary
   return, and the Y-strainer blowdown. Take the gravity drain; expect 60–75 %.
5. Blow the remainder with compressed air at 15–20 psi through a regulator, into each coil's
   vent port with its zone valve open and out that loop's low drain, one zone at a time, master
   bedroom last. Blow in the direction of normal flow: the Taco's integral check valve and any
   flow checks block the reverse. Do the tank and the boiler through their own drains and vents.
6. For a chemistry reset, refill with tap water, circulate briefly, and drain again. What stays
   after the second drain is under a fifth of a fill, a few tens of ppm of hardness, less than a
   single autofill top-up used to add.
7. Disposal: the old charge goes to the sanitary sewer only if the MUA accepts glycol. The
   nitrite treatment rules out a storm drain.

With the system at zero pressure, two checks that are only possible now:

- Expansion tank air charge, with a tyre gauge at the Schrader valve. Set it to the intended
  cold fill pressure, about 20 psi for the 25 ft rise. Water at the valve means the bladder has
  failed; replace the tank.
- The attic auto-vent. A vent stuck shut is the one failure that air-binds that coil, so replace
  it while the loop is open.

## 4. Refilling

Pre-mix the whole charge in the drum before any of it enters the system. Adding concentrate to
a filled loop leaves the refractometer reading one concentration at the gauge and another at
the attic. Premixed inhibited glycol already comes in demineralised water, so purified water is
only needed for the balance; RO or distilled from a grocery or water store is good enough.
Inhibited concentrate carries its own inhibitor, so no 8-Way.

1. Fill with every vent open, pump throttled, closing each vent as it spits solid fluid, attic
   vent last.
2. Purge one loop and one zone at a time. Isolate the fill point from the return so the flow
   must travel out the supply, through the open coil and back to that loop's purge cock, run
   the purge hose into the drum, and continue until the stream is bubble-free for a full minute.
   Master bedroom gets the longest purge.
3. Purge the boiler circuit and the tank the same way.
4. Fill the chiller side, restore its breaker, and let its internal pump's idle trickle and its
   own auto-vent finish. `hvac.chiller.chiltrix.startupFlow` back at 51.7 L/min in the next
   pump-only window proves the exchanger and pump are free of air.
5. Throttle the discharge to bring the boiler gauge to 21–23 psi cold, close the fill valve,
   stop the pump, and cap the fill fitting.

## 5. After the first day

- Bleed every vent once more and re-check the pressure; add fluid through the same fitting if
  it has fallen.
- Measure the glycol with the refractometer at two points and record the date and reading
  here and in `CLAUDE.md`, because a glycol change moves the `startupFlow` baseline.
- Check pH within a week: NTI allows 7.5–9.5 and Alfa Laval's exchanger 9.0 at most.
- Read the loop probes on Signal K. A coil still holding air shows as one zone reading wrong
  while the others hold; `pivac.LoopDelta` shows it as a loop whose ΔT stays near zero on a
  call.

## 6. Not covered

Winterising the chiller alone (breaker off, no drain) is a separate, simpler matter and is in
`CLAUDE.md`. The domestic side of the autofill and the DHW system are untouched. The CX75 IOM
governs its drain plugs and any refrigerant-side steps; nothing here opens that side.
