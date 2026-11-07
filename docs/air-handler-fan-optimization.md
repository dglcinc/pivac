<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
<!-- Copyright David Lewis -->

# Air handler fan optimization

This is the control approach for a Unico air handler's fan speed, and what the data from two M2430s says to do now. The master bedroom data is `pivac.UnicoAH_MBR` at one-minute means from the evening of 2026-10-20 to 2026-11-01, 11.5 days. The downstairs family and utility data is `pivac.UnicoSCB_Utility` from 2026-10-24 to 2026-11-01, 7.7 days. `docs/data/ah-mbr-node/fan-analysis/` holds the scripts.

## 1. Recommendations for the master bedroom

The first gain is a thermostat setting. Fan changes come after it.

| # | Action | When | Expected result |
|---|---|---|---|
| 1 | Put the thermostat on Heat | Now | 10 of 15 changeovers and all the high fan time go |
| 2 | Read the stored airflows | Next visit | Replaces the inferred 300 and 500 CFM |
| 3 | Raise W1 from 300 to 400 CFM | After 2, for a week | Supply air about 101 °F; 25 % more capacity |
| 4 | Raise Y1 from 300 to 400 CFM | Spring | Brings it onto the coil tables |
| 5 | Try Y2 at 600 CFM | June, if the room loses ground | About 11 % more capacity |

1. **Thermostat.** The rule in `CLAUDE.md` is Heat for the winter, never Auto, and this thermostat is still calling cool. Sun takes the room to 75 °F most mornings, and the heat-to-cool changeover then sends the tank's hot water through the coil first. Each round trip costs about 3.9 kWh of tank swing, about 3.4 kWh a day at this rate. On Heat the room can drift above 75 °F on a sunny morning, which the room record will show.
2. **Stored airflows.** Run `scripts/unico-scb.py listen` on the master bedroom's USB port, or fit its AirMaster. Every airflow in this document rests on the inference in §3 until then.
3. **W1.** This is a test, since the room holds 72 °F now. Watch the supply temperature and listen at the outlets, and stop at 450 CFM or a 95 °F supply, whichever comes first. A saving appears only when the plant's water temperature can come down, and the coldest-weather zone decides that, so check the other coils before moving the Chiltrix target.
4. **Y1.** The Unico coil tables start at 400 CFM, and the air handler manual asks for 200 to 250 CFM per nominal ton. Absolute dehumidification does not suffer: at 50 °F water and 4 GPM the table gives 4.5 MBH of latent at 400 CFM, 4.9 at 500 and 5.0 at 600. Swap the water probes to their cooling offsets first.
5. **Y2.** The table gives 17.4 MBH at 500 CFM and 19.3 at 600, at 50 °F and 4 GPM. There is no fall evidence for or against it, because the fall's high fan time was caused by the hot water in §2. The utility unit's ducts reach the motor's 1800 RPM limit at about 495 CFM (§6), so 600 CFM may be out of reach here too. Read the master bedroom's RPM at 500 CFM before trying it.

The aquastat interlock in `docs/chiltrix-shoulder-season-heating-plan.md` §7.1 was deferred until changeovers became daily. At this rate they nearly are, about 1.3 a day, so it comes back into question if the thermostat change does not end them.

## 2. What the data shows

**Heating never needs the high fan, and the coil is starved for air.** There were 240 heat calls, 21.8 a day, median 12 minutes and 90th percentile 15, with no Y2. In steady running the coil heats the air almost to the water temperature, so more water temperature than the air can carry is being supplied.

| Steady, 8 minutes or more into a call | Heat, low | Cool, low | Cool, high |
|---|---|---|---|
| Minutes | 980 | 612 | 703 |
| Water in, °F | 113.6 | 52.6 | 51.8 |
| Water out, °F | 108.7 | 55.9 | 56.2 |
| Air in, °F | 73.3 | 75.1 | 73.9 |
| Air out, °F | 110.5 | 55.9 | 57.4 |
| Air ΔT, °F | 37.5 | 19.0 | 16.6 |
| Water ΔT, °F | 5.0 | 3.2 | 4.4 |
| Effectiveness | 0.93 | 0.86 | 0.75 |

**The coil has spare heating capacity in all the weather so far.** Heat duty was 45 % at 30 to 40 °F outdoors with 120 °F in the primary, 39 % at 40 to 45 °F, 27 % at 45 to 50 °F and 17 % from 50 to 60 °F. The room held 72 °F throughout. The coldest hour was 38 °F, so this says nothing about design weather.

**The morning cool call is the plant's main changeover.** Ten of the 15 changes to cooling came within 6 minutes of a master bedroom cool call, between 10:17 and 12:45 EDT, with the room at 75 °F and 54 to 66 °F outdoors. The other five came in the evening, including the kids room episode.

**That call blows hot air into a room asking for cooling, and this is what raises the high fan.** Cold water reached the coil 15 to 19 minutes into each long call, and until then the supply air peaked at 102 to 111 °F. In six of the ten long calls the room rose from 75 to 77 °F, and Y2 came on 15 to 19 minutes in, as the water turned cold. It then ran for up to 205 minutes. In the other four the room stayed at 75 °F and Y2 ran for 0 to 11 minutes. Fan speed cannot fix this, since the fan runs on the call whatever the water temperature.

**The fall's coil was dry.** Return air averaged 74.6 °F at 38 % RH, a 47 °F dew point, against 52 °F water. All the cooling here was sensible, so these numbers say nothing about dehumidification.

## 3. The coil model and how far to trust it

Three operating points agree on one water flow if the stored airflows are the same as the utility zone's M2430, which reads G 200, Y1 300, Y2 500, W1 300, W2 500, E 500. The air-side and water-side heat balance then gives 5.06 GPM in heating, 4.67 in cooling low and 4.62 in cooling high. `docs/unico-cooling-assessment-and-tuning.md` calculated 3.9 to 4.7 GPM for this coil. The cooling water ΔT here has 0.45 °F taken off, because the config holds the 115 °F offsets for these probes. That is an inference, and the stored values have not been read.

The utility unit's stored values, read directly, are these same numbers (§6). The heat balance fits a UA of about 920 BTU/h·°F at 300 CFM in heating. Scaling UA with airflow to the 0.35 to 0.5 power gives this, with entering air at 73.3 °F:

| W1, CFM | At 113.6 °F water: MBH | Same 12.15 MBH: water in, °F | Supply air, °F | Water out, °F |
|---|---|---|---|---|
| 300 | 12.1 | 114 | 111 | 109 |
| 350 | 13.8 | 109 | 105 | 104 |
| 400 | 15.4 | 105 | 101 | 100 |
| 450 | 17.0 | 103 | 98 | 97 |
| 500 | 18.4 | 100 | 96 | 95 |

This is a fit to one coil over 11.5 days. The W1 test in §1 is what checks it.

Three things are not measured: water flow, blower power and outlet noise. Fan power rises steeply with airflow and is the cost of every step up. Blower heat counts toward the room in heating, so the net can be judged only with the Chiltrix's power at the lower water temperature.

## 4. The general control approach

**The controller adjusts stored airflow slowly, and does not run a live fan loop.** The SCB has no live speed command, so the only control is its stored airflow per call, and each change is a write to memory of unknown endurance. It settles on a value per call for each season, and the thermostat keeps doing minute-by-minute control.

Each call produces one record, once these gates pass: 8 minutes into the call, water on the right side of the air, all sensors fresh, water flowing, and the fan at its stored airflow. A record holds water and air in and out, ΔT, effectiveness, actual CFM and RPM, the stage, the room's distance from setpoint and RH. Calls with wrong-side water are counted separately and never used for tuning.

| Call | Raise it when | Lower it when | Limits |
|---|---|---|---|
| W1 | Supply air is above 100 °F and the room holds | Supply air is under 95 °F | Model range, RPM limit, noise |
| W2, E | The room loses ground on W1 | Never on its own | As above |
| Y1 | Most calls upstage with the room over 1 °F | Room RH is over 55 % with Y1 above 400 CFM | 200 to 250 CFM per ton where the coil is wet |
| Y2 | The room still loses ground on high | The owner's noise limit | RPM limit |
| G | Never | Never | Owner's choice |

The 100, 95 and 55 values are starting points to tune against the first test.

The ducts set the real ceiling, and each unit measures its own. RPM divided by actual CFM is close to constant for a duct system, so one call gives the airflow at which the motor reaches its stored RPM limit, and the controller never asks for more.

1. **Rate.** One step of 50 CFM per call per week, and only after 20 gated records at the current value. A step is compared with the week before, matched by outdoor temperature.
2. **Budget.** A hard limit on writes, such as 50 a year. A season should need only a few.
3. **Safety.** Stay inside the model's table limits. Refuse to run with stale sensors or another PC on the SCB. Save the original settings first, log each change with its reason, and restore the last good value if the room fails to hold setpoint after a step.
4. **Plant link.** Report the lowest water temperature each coil could live with at its current airflow. Only the plant can act on that, and only when every zone agrees.

**Build order.** Start with a read-only advisor in pivac that publishes the record, the coil model and a recommended airflow, and compare its advice with the tests in §1 for a season. Next, let it write, through the AirMaster's limits, after you approve each change. The same logic then moves into the AirMaster's firmware, so a standalone unit runs it and pivac or Home Assistant only set limits and read results.

## 5. What would change these recommendations

1. The master bedroom's stored airflows differ from 300 and 500 CFM, which moves every CFM figure here.
2. Summer data is missing: wet-coil behaviour, humidity and real Y2 need have not been measured on this coil with the node fitted.
3. Colder weather. The fall's coldest hour leaves the winter capacity margin unproven.
4. Each unit's numbers are its own. The approach carries over, and the ducts decide the ceiling.

## 6. The downstairs family and utility M2430

The utility unit reports what the master bedroom cannot, actual airflow and RPM, and lacks what it has, coil temperatures. Its stored airflows are known from the 2026-10-24 read: G 200, Y1 300, Y2 500, W1 300, W2 500, E 500, with every RPM limit at 1800. They were set with ECMConfig, away from the factory defaults, which supports the inference in §3 for the master bedroom.

**It has barely run, so it should not be tuned yet.** In 7.7 days it ran 132 minutes, all on Y1, and 118 of those were on 2026-10-30. It made no heat call at all, with outdoor temperatures down to 38 °F. The room spent only 2.3 hours within a degree of its 72 °F heat setpoint, and its hourly averages ran from 73.6 to 75.7 °F. Neighbouring zones or the mechanical room may be carrying it, which these data cannot separate.

| Action | When | Reason |
|---|---|---|
| Change nothing | Now | Two hours of running decides nothing |
| Force one high fan call | Next visit | Shows whether it reaches 500 CFM |
| Fit an AirMaster with coil probes | With the first carriers | Airflow and coil data on one unit |
| Test Y1 at 400 CFM | Spring | As the master bedroom, about 1450 RPM |
| Test W1 | Only if it ever calls heat | There is no heating data |

1. **The airflow ceiling.** On Y1 it held 300 CFM at 1088 RPM, 3.63 RPM per CFM. By the fan law, 500 CFM needs about 1817 RPM against the 1800 limit, so the ducts cap it at about 495 CFM and the stored 500 is already its maximum. No high fan call has been recorded, so the forced call is the test. Noise also rises with RPM.
2. **Water.** Loop B carries only this coil in cooling, since the kitchen and great room cool on their Bosch units, so its probes read this coil's water on a cool call. Over 90 minutes, from the third minute of each call, the water went in at 53.8 °F and out at 55.9 °F, a ΔT of 2.06 °F with a 10 to 90 % range of 1.7 to 2.7 °F. The room was 76 °F at 41 % RH, a 51 °F dew point, so the coil was close to dry. These calls were 9 to 11 minutes long, and the loop probes sit at the tees, so this ΔT includes the pipe run to the coil and back.
3. **Heat balance.** At 300 CFM and a 22 °F gap, air can carry at most 7.1 MBH. The calculated 7.8 GPM on HIGH would put 7.9 MBH in the water, which is more than the air can give, so the real flow is lower or the ΔT reads high. At LOW's 6.5 GPM the water takes 6.6 MBH and effectiveness is 0.92.
4. **Against the master bedroom.** The coil model fitted to the master bedroom's cooling predicts 6.1 MBH and a 1.9 °F water ΔT for this coil at 300 CFM and 6.5 GPM, close to what the probes read. Two units of the same model agree that at 300 CFM the air leaves near the water temperature.
5. **More airflow.** The same model gives about 7.6 MBH at 400 CFM and about 9 MBH at 500, at this water temperature and with the coil dry. Water is not what limits this coil at 300 CFM, so more pump speed would add almost nothing.
