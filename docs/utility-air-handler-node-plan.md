# Utility air-handler node: install plan

The rev A air-handler shield is the utility zone's Unico M2430's coil node, installed 2026-11-01 as a temporary mount until the rev B carrier. The unit's S.M.A.R.T.
Control Board already reaches Signal K over the Pi's USB (`pivac.UnicoSCB_Utility`), so the node adds only
what the SCB cannot give, the coil's water and air temperatures, and together they are the data set rev B
was designed to deliver from one box: calls, airflow and RPM from the SCB, four coil temperatures from the
node, all under `environment.inside.hvac.ah.utility`. The fan-optimization doc (§6) names this unit as the
one that reports airflow and lacks coil temperatures; after this install it is the one air handler with a
complete heat balance, air side and water side at a known CFM.

The board, its bench record and the sensor calibration are in `docs/air-handler-shield-pcb-plan.md`,
`docs/air-handler-shield-assembly.md` and `docs/air-handler-probe-calibration-2026-11-01.md`. The
master bedroom node (`docs/mbr-air-handler-node-plan.md`) is the pattern for everything below that is not
specific to this board or this unit; its §3 mounting rules and §6 commissioning apply unchanged.

## 1. What the node measures

| Signal | Source | Signal K path under `ah.utility` |
|---|---|---|
| Coil water supply | PA9A on TB3 | `water.supply.temperature` |
| Coil water return | PA9B on TB3 | `water.return.temperature` |
| Supply air | SUP 1 on TB2 | `air.supply.temperature` |
| Return air | RET 1 on TB2 | `air.return.temperature` |
| Water ΔT, gated | `pivac.LoopDelta` | `water.deltaT`, `water.flowing` |
| Air ΔT, gated | `pivac.LoopDelta` | `air.deltaT`, `air.flowing` |
| Node uptime | the sketch | `uptimeMs` |
| Calls, airflow, RPM | the SCB on the Pi | `call.*`, `fan.*`, `scb.*` (already live) |

1. The node's Y2 and W2 inputs stay unwired. The SCB publishes `call.y2` and `call.w2` from the control
   board itself, so the optocouplers would duplicate them, and leaving them off keeps the node's wiring to
   R and C at the thermostat terminals.
2. PA9A and PA9B are the batch's closest pair, 0.005 K apart at 55 °F. SUP 1 and RET 1 are the NTC pair
   with the smaller fit residuals.
3. In cooling, loop B carries only this coil (the kitchen and great room cool on their Bosch units), so
   `LOOPB.deltaT` and `ah.utility.water.deltaT` measure the same water and must agree; that is the
   commissioning check for the water pair. In heating loop B carries three coils and the node reads this
   coil's share.

## 2. Board, power and mounting

The board is the rev A shield on the UNO R4 WiFi that ran the bench (USB serial `E8F60AA9FDE82`), U2
fitted, JP1 open, R15 off. It takes 24 VAC on TB1's R and C from the Unico's own transformer and feeds the
R4's 5V header pin from U1 across its isolation barrier, so a laptop on the R4's USB-C while the 24 VAC is
live is safe (shield plan §4.2). The wall adapter and the USB-C converter of the master bedroom node play
no part.

1. **Transformer.** The Unico's transformer is 50 VA (part A00057) and also powers the EIM. The board adds
   about 3 VA. Read the nameplate at the unit before wiring.
2. **Mounting.** The shield has no mounting holes; the R4 carries it. The R4 goes on an Adafruit 4557 DIN
   bracket, as at the master bedroom, on a short length of 35 mm rail beside the control box, with the
   Quattro blocks for the sensor leads on the same rail. Hold the tab behind a header when seating or
   pulling a plug: nothing supports it.
3. **Where.** Beside the control box, where R and C and the SCB's USB board already are, within the probe
   leads' reach of the coil connections. Measure the run from the rail to the coil pipes before cutting
   the 1-wire and NTC leads.
4. **TB1.** The plug is the 4-way MC 1,5 (1803594); R to position 1 and C to position 2 in 18 AWG
   thermostat cable, Y2 and W2 positions empty. Land the screws with the plug off the board.

## 3. Sensors and wiring

The probes and NTCs mount by the master bedroom plan's §3.1 and §3.2: water probes on copper at the coil
connections, axial and greased, two to three inches of thermal lead-in, insulation each side, supply probe
after the zone pump, both probes of a pair mounted the same way so their mounting error is common-mode;
air sensors in the supply plenum downstream of the coil and in the return ahead of it, out of radiant
sight of the coil. Strain relief an inch or two behind each probe and each bead.

As installed on 2026-11-01: PA9A and PA9B are strapped to the coil's supply and return pipes with cable
ties and insulated over; the supply-air bead sits about 18 inches above the coil in the supply plenum; the
return-air bead sits near the coil at the end of the return duct, after its last turn, so it reads mixed
return air. On the first heat call the coil water read about 3 °F below the loop B probes in the boiler
room on both legs with the pair's ΔT within 0.3 °F of loop B's, so the mounting carries no visible bias.

| Plug | Positions | Lead |
|---|---|---|
| TB3 | V · D · G | PA9A and PA9B through a Quattro set |
| TB2 | SUP · GND · RET · GND | SUP 1 and RET 1, each on its own GND |
| TB1 | R · C · Y2 · W2 | R and C only |

1. **Leads.** The PTSM plugs hold 20 to 26 AWG and hold solid wire best; the probes' fine stranded leads
   worked loose and broke inside their connectors on the bench. Terminate the probes and beads in Quattro
   blocks on the rail and run 22 AWG solid from the blocks to the plugs. For the 1-wire run use
   three-conductor; in a twisted-pair cable pair DATA with one ground and VCC with the other
   (`docs/ds18b20-bus-topology.md` rule 4).
2. **Polarity at TB3.** With the probe's VDD and GND reversed, TB3.V to G reads millivolts: F2 trips and
   resets itself once the probe is out. Check V to G reads 5 V with the probes on before closing up.
3. **NTC leads.** Any twisted pair; thermostat cable serves. Each bead's second lead goes to its own GND
   position on TB2.

## 4. Sketch

A new zone folder `AirHandler_Utility` in `~/github/Arduino`, on the `feat/airhandler-ds2482` line (Arduino
PR #14), which carries `OneWireBus.h` and the DS2482 reads. It differs from `AirHandler_MBR` in the zone
constants only:

```c
#define ZONE_TAG       "UTIL"
#define HOSTNAME       "airhandler-utility"
#define SHIELD_PCB                         // return air on A0, supply on A1
#define ROM_WSUP       { 0x28, 0x08, 0x7F, 0xD4, 0x00, 0x00, 0x00, 0xB2 }   // PA9A 28-000000D47F08
#define ROM_WRET       { 0x28, 0x67, 0x85, 0xD4, 0x00, 0x00, 0x00, 0x4E }   // PA9B 28-000000D48567
#define NTC_R0_OHM     9877.0f     // pair 1's mean R25 from the 2026-11-01 baths
#define NTC_BETA       4001.0f     // pair 1's mean beta
#define NTC_RREF_OHM   10000.0f    // R1 and R2
#include "AirHandler_impl.h"
```

1. The ROM bytes are the bus order the sketch prints; the w1 names reverse the six serial bytes.
2. The NTC constants are the pair's means. With them, RET 1 reads +0.0 to +0.5 °F and SUP 1 −0.1 to
   −0.3 °F across the three baths, so the per-input offsets in pivac config are −0.15 K for the return
   bead and +0.10 K for the supply bead, each within 0.07 K of constant from 55 to 110 °F. The master
   bedroom node carries its residuals the same way.
3. The sketch's Y2 code stays; D8 reads high with nothing on TB1's Y2, so the node reports `y2` 0, and
   pivac does not map it (§6).
4. `arduino_secrets.h` with the WiFi credentials goes in the folder, gitignored. Build and flash from the
   M2 over USB: `arduino-cli compile -b arduino:renesas_uno:unor4wifi AirHandler_Utility`, then `upload`
   to the board's port. The bring-up mode prints the 1-wire master, both ROMs, the raw counts and the
   WiFi hostname at boot, and the R4 prints them before a monitor can open, so watch the port from a
   script that is open across the reset.

## 5. Network

The node joins SSID `redux` as `airhandler-utility`. Its WiFi MAC is unknown until it first joins; read it
from the UCG client list by hostname, then give it a fixed IP by the recipe in the UniFi tool memory:
`GET /proxy/network/api/s/default/stat/user/<mac>` for the user `_id`, `PUT .../rest/user/<_id>` with
`use_fixedip`, `fixed_ip` and the LAN `network_id`. **10.0.0.181** is free (checked 2026-11-01; .180 is the
master bedroom node), name `AirHandler-Utility`. The reservation follows the MAC, so the board keeps the
address wherever it is plugged in.

## 6. pivac

### 6.1 Config section

A `pivac.UnicoAH_Utility` section in `/etc/pivac/config.yml` and `config/config.yml.sample`, a copy of
`pivac.UnicoAH_MBR` with these differences:

```yaml
pivac.UnicoAH_Utility:
    description: Utility zone Unico M2430, coil water and air temperatures
    module: pivac.ArduinoSensor
    enabled: true
    ipaddr: 10.0.0.181
    rounding: 2
    daemon_sleep: 5
    inputs:
        wsup:  { sk_path: environment.inside.hvac.ah.utility.water, outname: supply, type: temperature, offsets: {55: 3.382, 115: 3.556} }
        wret:  { sk_path: environment.inside.hvac.ah.utility.water, outname: return, type: temperature, offsets: {55: 3.387, 115: 3.595} }
        aret:  { sk_path: environment.inside.hvac.ah.utility.air,   outname: return, type: temperature, offset: -0.15 }
        asup:  { sk_path: environment.inside.hvac.ah.utility.air,   outname: supply, type: temperature, offset: 0.10 }
        uptime_ms: { sk_path: environment.inside.hvac.ah.utility, outname: uptimeMs }
```

1. The water offsets carry both bath columns, 55 °F for cooling water and 115 °F for heating, and the
   module interpolates on the reading, so there is no seasonal swap.
2. `y2` and `y2_s` are not mapped: the input is unwired and the SCB's `call.y2` is the truth.
3. The SCB section stays as it is, `port:` on the Pi's USB. Its comment about replacing `port:` with
   `node:` applies to a rev B node with the serial tap; this node has none.

### 6.2 Service

`scripts/systemd/pivac-ah-utility.service`, a copy of `pivac-ah-mbr.service` with the section name
changed, installed and enabled on the Pi, and added to the restart list in CLAUDE.md's Standard
Deployment Procedure, the SD-maintenance stop list, and `STOP_SVCS` and `START_SVCS` in
`scripts/nas-image-backup.sh`, which is where a missing unit stays dead after the monthly backup.

### 6.3 LoopDelta gate on the SCB's calls

`pivac.LoopDelta` gates a loop on a relay narrowed by RedLink zone states, which lags the equipment by
24 to 48 s. The utility unit has a better gate on the bus: the SCB's own call bits, published every 5 s.
The module gains a `gate:` key, a list of paths under `sk_path` whose value of 1 opens the gate, in place
of `relay:` and `zones:` for that loop; everything else, the settle time, the three meanings of the
published value and the gap on a stale source, is unchanged.

```yaml
        ah.utility.water:
            supply: ah.utility.water.supply
            return: ah.utility.water.return
            gate: [ah.utility.call.y1, ah.utility.call.w1]
        ah.utility.air:
            supply: ah.utility.air.supply
            return: ah.utility.air.return
            gate: [ah.utility.call.g]
```

1. Water moves through the coil on a Y1 or W1 call, when the zone's pump runs; the fan alone (G without a
   call) moves air over still water, so the water pair gates on the calls and the air pair on the fan.
2. A stale `call.*` path (the SCB reader down) closes the gate, so a dead tap reads as the loop not
   measuring, with `flowing` 0, and the sensor-freshness rule on the SCB path is what reports it.
3. `tests/` gets a case for the `gate:` key beside the relay cases.

### 6.4 Alerts

`ah-utility-air-return-stale` in `grafana/provisioning/alerting/sensor-freshness.yaml`, a copy of the
master bedroom rule on `environment.inside.hvac.ah.utility.air.return.temperature`, 30 min, warning,
shipped `isPaused: true` and unpaused once the path publishes, verified against the `alert_rule` table.

### 6.5 CLAUDE.md

A row in Active Services, a `UnicoAH_Utility` entry in Current Modules, the service in the three lists of
§6.2, the LoopDelta entry's description of the `gate:` key, and the 1-wire section's note that PA9A and
PA9B are in service.

## 7. Order of work

1. **Bench, before the board leaves.** The 24 VAC run of the assembly doc's check table: TB1 on the bench
   transformer, R4 off USB, `AirHandler_Utility` flashed, console showing the DS2482, both ROMs with
   `CRC ok`, the two NTCs, WiFi joined and the hostname. Read the WiFi MAC from the UCG and set the
   .181 reservation. This is also the first run of the zone sketch on the DS2482.
2. **Pivac side, before the install.** Config section, service, the LoopDelta `gate:` key with its test,
   the paused alert rule, CLAUDE.md; one PR, merged and pulled on the Pi, the service enabled. With the
   node on the bench at .181 the whole path can be proved from Signal K before anything is mounted.
3. **At the unit.** Transformer nameplate; power off; rail, bracket and Quattro blocks; probes on the coil
   connections and beads in the plenums; leads to the blocks and 22 AWG to the plugs; TB1 R and C; power
   on; TB3 V to G at 5 V; the node's LED matrix and `uptimeMs` climbing in Signal K.
4. **Commissioning, first day.** The four temperatures live; on the first cool or heat call, `flowing` 1
   on both pairs within the settle time; `ah.utility.water.deltaT` against `LOOPB.deltaT` on a cooling
   call, which must agree to the pair corrections; the air ΔT against the SCB's airflow and the water ΔT
   in a heat balance; unpause the alert; camera check on the Sentry, since the boiler room will have been
   visited.

## 8. Boundaries

The SCB stays on the Pi's USB; TB5 is not wired and the node carries no serial tap. The node's Y2 and W2
inputs stay unwired. `pivac.UnicoSCB` and `pivac.ArduinoSensor` are not changed; `pivac.LoopDelta` gains
the `gate:` key and nothing else. The master bedroom node is untouched. No Grafana panels are in this
plan; the first week's data is pulled the way the fan-optimization doc pulled the master bedroom's, and
panels follow if they earn a place. The rev B carrier and the AirMaster firmware are not affected: this
node is the utility unit's for as long as rev A serves, and a carrier replaces it only if the serial tap
is wanted off the Pi.

## 9. Parts

Everything is on hand except the bracket, if the master bedroom's was the only one.

| Part | Maker number | Digi-Key | Amazon |
|---|---|---|---|
| DIN bracket for the R4 | Adafruit 4557 | [search](https://www.digikey.com/en/products/result?keywords=adafruit+4557) | [search](https://www.amazon.com/s?k=adafruit+4557+din+rail) |
| Feed-through blocks | Phoenix PT 2,5-QUATTRO, 3209578 | [search](https://www.digikey.com/en/products/result?keywords=3209578) | [search](https://www.amazon.com/s?k=phoenix+3209578) |
| TB1 plug | Phoenix MC 1,5/4-ST-3,81, 1803594 | on hand | |
| TB2, TB3 plugs | Phoenix PTSM 0,5/4-P and 0,5/3-P | on hand | |

Stock and price were not checked on the vendor pages for this plan; confirm before ordering.
