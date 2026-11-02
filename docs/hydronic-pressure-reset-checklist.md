# Hydronic pressure reset: lower the loop to 20 psi cold

This sheet lowers the glycol loop's pressure by letting air out of the Extrol EX-60 expansion tank while the tank stays open to the loop. You add or drain no fluid. The bladder keeps the fluid it holds, so the loop still has a cushion when it is cold.

## Why

At a 21 psi precharge the loop read 23.6 psi cold on 2026-10-12 (buffer tank 49 °F), with 0.46 gal in the bladder. With 0.9 gal of expansion added, it would heat to about 30 psi, which is the relief valve's setting. With the tank's air let down until the loop reads 20 psi cold, the same expansion peaks near 25.8 psi.

| | Before | After |
|---|---|---|
| Loop pressure, cold | 23.6 psi | 20 psi |
| Tank precharge (equivalent) | 21 psi | about 17.6 psi |
| Fluid in the bladder, cold | 0.46 gal | 0.46 gal |
| Room in the tank, cold to 27 psi | 0.53 gal | 1.05 gal |
| Hot peak with 0.9 gal of expansion | about 30 psi | about 25.8 psi |
| Hot, tank at 125–132 °F (the normal heating band) | 25–27.5 psi | 24.5–26.3 psi |

## Bring

- [ ] Tyre pressure gauge (0–60 psi)
- [ ] Phone with WilhelmSK open on the Hydronic PSI tile
- [ ] Pen for the blanks below

## Before you start

Check these on WilhelmSK or the boiler-room gauges. The steps assume all four.

- [ ] Buffer tank (UBT) under 55 °F. Tank temp: ________ °F
- [ ] Chiller compressor off and primary pump idle (`HPCALL` = 0)
- [ ] Loop pressure steady for a minute. Reading: ________ psi
- [ ] Relief valve outlet dry. If it is wet, note it: ________

If the panel has gone back to heat and the tank is above 110 °F, use **22 psi** as the target in step 4 instead of 20 psi. Do nothing while the tank is between 55 and 110 °F, because it is moving too fast to read.

## Steps

1. **Close the auto-fill valve.** This stops the regulator adding water while the pressure is coming down.
   - [ ] Done

2. **Gauge the expansion tank's air valve.** It should read the same as the loop, within about 1 psi.
   - Air valve: ________ psi. Loop: ________ psi.
   - [ ] Within 1 psi, so go on.
   - If the air valve reads more than 2 psi below the loop, **stop**, reopen the auto-fill valve and call me. The bladder is not taking water, and these numbers do not apply.

3. **Let air out in short bursts.** Press the valve core for one or two seconds at a time, then wait about five seconds for the loop gauge to settle.

4. **Stop when the loop reads 20 psi** (22 psi if you are working hot), and leave it for a minute.
   - Final loop reading: ________ psi.
   - [ ] Held for one minute.
   - If you overshoot below 19 psi, leave it there and tell me. Do not add air: the tank is open to the loop, so pumping air in only puts the pressure back.

5. **Read the auto-fill regulator's gauge** on its outlet, behind the demineralisation filter.
   - Regulator setting: ________ psi.

6. **Set the regulator to 17–18 psi.** It must sit under the new 20 psi cold pressure, or it will push water in at every pump start.
   - [ ] Set to ________ psi, then reopen the auto-fill valve.
   - If you cannot adjust it, **leave the auto-fill valve closed** and note it here: ________

7. **Set the five hydronic thermostats to Heat**, not Auto: kids room, master bedroom, family room downstairs, kitchen, great room. The family room on Auto has switched the plant into cooling twice in two days.
   - [ ] Done

## Afterwards

Send me the blanks above. I will watch the overnight trend. Expect these readings:

- 20 psi while the tank is cold, 24.5–26.5 psi once it is back at 125–132 °F in heat mode, with pump-start dips of 1–2 psi.
- Pump-start dips of 1–2 psi. Today's were 5–6 psi.

Tell me if you see either of these:

- The pressure climbs past 25 psi. The regulator is still feeding, or the loop still holds air.
- The pressure drifts back toward 19 psi over a few days. The loop still holds air, or the relief valve is weeping.

The next time the tank is drained, set its precharge with the tank isolated and its water side open at zero pressure. Gauging the air valve with the tank connected measures the loop pressure, not the precharge.
