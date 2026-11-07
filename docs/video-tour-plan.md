# Video tour of the monitoring setup, for Unico

Unico's customer service team asked on 2026-11-06 for a video of the monitoring setup, so their staff can review it. The contact already knows the owner, so the video can name the owner; this plan, which sits in a public repo, uses placeholders for names and contacts. This plan covers the shot list, the narration script, how to capture the Mac and iPad screens, and how to cut the video together in iMovie. The target length is 12 to 14 minutes.

## Approach

Shoot after the first Rev B AirMaster is built and installed on the great room air handler. That unit has both a hydronic module and a DX coil, so it shows the dual configuration with the AirMaster running live; the utility air handler then shows a pure hydronic unit with the Pi's USB tap and the sensor node.

Shoot the equipment on the iPhone as silent B-roll, record every screen directly with the built-in screen recorders, and narrate afterwards as one voice-over read from the script below. Narrating live while holding a phone in the utility room yields uneven audio and long takes. A voice-over recorded in a quiet room is even in level, can be re-read line by line, and sets the pace for the cut, so the pictures are trimmed to fit the words.

Record the screens rather than filming them with the phone. A phone filming a monitor picks up moiré, glare and a tilted frame, and small text becomes unreadable. Native screen recordings stay sharp at any zoom. The one exception is a short shot of a hand holding the iPad running WilhelmSK, which shows the app in use. Film that one with the phone.

All the software is already on hand: the iPhone camera, Screenshot (Cmd-Shift-5) and QuickTime on the Mac, Screen Recording on the iPad, Keynote for the diagram and title cards, GarageBand for cleaning up the voice-over, and iMovie for the edit.

## Outline

| Seg | Topic | Time |
|-----|-------|------|
| 0 | Open | 0:30 |
| 1 | Water and control diagrams | 1:45 |
| 2 | Air handlers | 2:00 |
| 3 | Utility room plumbing | 1:30 |
| 4 | Integration panel | 2:30 |
| 5 | Power, thermostats, boiler | 1:00 |
| 6 | Collectors and storage | 1:30 |
| 7 | WilhelmSK | 1:00 |
| 8 | Grafana examples | 1:00 |
| 9 | Custom boards | 1:30 |
| 10 | GitHub | 1:00 |
| 11 | Close | 0:30 |

## iPhone settings

1. Set the camera to 1080p at 30 fps (Settings → Camera → Record Video). Use 4K only if a shot will be cropped hard in the edit, such as terminal labels on the panel.
2. Hold the phone landscape for every shot.
3. Wipe the lens before each session.
4. Press and hold on the subject until "AE/AF LOCK" appears, so exposure does not pump when the frame crosses a light.
5. Light the utility room. Overhead light alone leaves the panel in shadow, so add a work lamp or a second phone's flashlight held off to one side.
6. Move slowly, or hold still for 8 to 10 seconds. A phone clamp on a small tripod helps with the panel close-ups.
7. Start each shot 3 seconds early and run it 5 seconds long, to leave handles for the cut.
8. Record 20 seconds of each room in silence, as room tone to lay under any cut that needs it.

## Shot list

| # | Seg | Shot | Source |
|---|-----|------|--------|
| 1 | 0 | Owner at the panel, wide | iPhone |
| 2 | 0 | Title card | Keynote |
| 3 | 1 | Water and control diagrams | Keynote |
| 4 | 2 | Great room air handler, wide | iPhone |
| 5 | 2 | Hydronic module and DX coil | iPhone |
| 6 | 2 | AirMaster on the SCB | iPhone |
| 7 | 2 | AirMaster page on the phone | iPhone |
| 8 | 2 | Utility air handler, wide | iPhone |
| 9 | 2 | Utility SCB USB and node | iPhone |
| 10 | 3 | Chiltrix CX75 outdoors | iPhone |
| 11 | 3 | CX75 panel display | iPhone |
| 12 | 3 | Buffer tank, UBT/LBT probes | iPhone |
| 13 | 3 | Primary pump, tees | iPhone |
| 14 | 3 | Loop A and B pumps | iPhone |
| 15 | 3 | Probe at a tee, close | iPhone |
| 16 | 3 | Y-strainer, gauges | iPhone |
| 17 | 4 | Integration panel, wide | iPhone |
| 18 | 4 | HZ-432, zone lights | iPhone |
| 19 | 4 | Quattro blocks | iPhone |
| 20 | 4 | Relays | iPhone |
| 21 | 4 | Pi with INT and EXT | iPhone |
| 22 | 4 | Modbus UNO R4, RS-485 | iPhone |
| 23 | 4 | 1-wire trunk, H plugs | iPhone |
| 24 | 5 | Emporia in the panel | iPhone |
| 25 | 5 | Thermostat on the wall | iPhone |
| 26 | 5 | Sentry camera on boiler | iPhone |
| 27 | 6 | Data-flow diagram | Keynote |
| 28 | 6 | pivac services in terminal | Mac |
| 29 | 6 | Signal K data browser | Mac |
| 30 | 6 | Chiltrix raw registers | Mac |
| 31 | 7 | Hand holding iPad | iPhone |
| 32 | 7 | WilhelmSK pages | iPad |
| 33 | 8 | Grafana PivacR dashboard | Mac |
| 34 | 8 | Utility fan per call | Mac |
| 35 | 8 | A P1 lockout | Mac |
| 36 | 9 | INT and EXT boards, bench | iPhone |
| 37 | 9 | KiCad 3D of INT and EXT | Mac |
| 38 | 9 | AirMaster renders | Mac |
| 39 | 9 | AirMaster board in hand | iPhone |
| 40 | 10 | GitHub pivac repo | Mac |
| 41 | 10 | GitHub Arduino repo | Mac |
| 42 | 11 | Closing card | Keynote |

### Shot direction

Each entry gives the framing, what must be in the frame, the camera position, and where to lock focus. "Lock" means press and hold on that point until AE/AF LOCK shows. A close-up should hold the subject for 8 to 10 seconds with no movement. A move should be one slow pan or push lasting 6 to 8 seconds, then a 3-second hold at the end.

1. **Owner at the panel.** Medium-wide, from your knees to a foot above your head, with the integration panel filling the right two thirds of the frame. Tripod at chest height, 6 to 8 ft back, square to the panel. Stand to the left of the panel, turn to face the lens, then turn and look at the panel. Lock on your face. This is the only on-camera shot; say nothing.
2. **Title card.** In Keynote, use the title "Monitoring a Unico hydronic system", with [owner's name] and "November 2026" below it. Use a plain dark background with white type, and nothing else on the slide.
3. **Water and control diagrams.** Two slides, built in stages, exported as `shot-03-water-a` to `-d` and `shot-03-control-a` to `-c`. The water slide: (a) the two sources, the CX75 and buffer tank through the Taco 0015 and the Ti-200 through its UP26-99F, joined in one supply line into the primary header, and the return line from the header back to the tank and the boiler, with domestic hot water off the boiler; (b) the closely spaced tees below the supply, out to the loop A and loop B pumps, a zone valve for each air handler, the five Unico air handlers, and the loop returns entering the top of the header; (c) the Bosch Bova DX units for kitchen and great room cooling; (d) the temperature probes, with IN on the header between the supply and the tees and OUT between the loop returns and the return to the sources. The control slide: (a) each zone's thermostat, wireless to its EIM, which drives the air handler's S.M.A.R.T. board; (b) the integration panel, where the boards' W, Y and G calls pass through Quattro blocks to the HZ-432 and its outputs pass through a second set of Quattro blocks, with each zone valve taking power from the panel and returning its end switch; (c) the relays, which take each HZ-432 output and switch the Taco, the loop pumps, the boiler and the Chiltrix mode, with a spare pole on each to the Pi, and the AirMaster on the board's USB port. The probes on the water slide are one colour, keyed by the legend at the bottom. Each stage is its own PNG, so the diagram builds as the edit cuts from one to the next.
4. **Great room air handler, wide.** The whole unit with space on each side, so the blower, the hydronic module, the DX coil and the control box read as one assembly, with the refrigerant lineset and the water pipes both visible where they enter. Stand back as far as the space allows, at the unit's mid-height, 30° off the control-box end. Lock on the control box.
5. **Hydronic module and DX coil.** First the M3036 hydronic module with its supply and return pipes and zone valve; then the DX coil section with the insulated suction line and liquid line from the Bosch unit. Shoot each square to the pipes so they run straight across the frame, 18 in away. Lock on the pipe connections. Light from the side so copper and foil insulation do not flare. If one frame can hold both coil sections, hold it 5 seconds; it is the shot that shows the dual configuration.
6. **AirMaster on the SCB.** The installed AirMaster with its status LEDs lit, the USB cable into the S.M.A.R.T. Control Board, and the 24 VAC leads to the Unico's terminal strip, in one frame. Shoot square to the box face, 10 to 12 in away. Lock on the AirMaster's label. Hold 10 seconds, then pull back slowly to the board's USB connector and the board's silkscreen name.
7. **AirMaster page on the phone.** Record the iPhone's own screen (Control Center → Screen Recording, microphone off) while the page shows the calls, airflow and RPM. For the cut, start the recording, then raise the zone's setpoint from its thermostat so a call and the airflow rise appear on the page within the take; airflow reaches its stored value in about 20 s. Hold 30 seconds.
8. **Utility air handler, wide.** Frame as in shot 4. It is the pure hydronic unit, so frame the coil and its water pipes with no lineset in view. Show the M2430 rating plate if it is legible from there; otherwise add a 3-second close-up of the plate.
9. **Utility SCB USB and node.** Open the control box with power on, staying clear of the terminals. Frame the S.M.A.R.T. Control Board with the USB cable running out of the box toward the Pi, square to the board, 10 to 12 in away, lit from one side because the board's coating reflects. Lock on the USB connector and hold 8 seconds. Then cut to the node: the UNO R4 and its shield from 30° above, the terminal legends and the leads to PA9A/PA9B and SUP 1/RET 1 readable. Lock on the shield's terminal block.
10. **CX75 outdoors.** Wide, with the whole unit, the fan grille and the piping into the house wall. Shoot from a corner at 45° and at the unit's mid-height, with the house wall behind it to show scale. In daylight, keep the sun behind you. If the compressor is running, record 10 seconds with the fan turning.
11. **CX75 panel display.** The display filling the frame, with mode, setpoint and water temperature readable. Shoot about 20° off-axis to the side and slightly above, to kill glare and your reflection. Lock on the digits. Hold 10 seconds while the unit is running, so a live temperature shows.
12. **Buffer tank and probes.** Start with the full tank top to bottom, then tilt slowly from the upper probe (UBT) down to the lower (LBT). Shoot from 6 to 8 ft back at mid-height so the tank stays vertical with no keystone. Lock on each probe as you reach it, and hold 3 seconds on each.
13. **Primary pump and tees.** The Taco 0015 primary pump and the run of pipe past both secondary tees, so the eye follows the water from the tank to the tees. Shoot along the pipe at about 30°, so the run recedes across the frame. Lock on the first tee.
14. **Loop A and B pumps.** Both secondary pumps in frame. If their pipe labels or tags are readable, hold on them. Loop B's UP26-99F speed switch should be visible (it sits on HIGH in heating). Shoot square to the pump bodies. Lock on the loop B speed switch.
15. **Probe at a tee, close.** One loop probe on its copper, with the insulation pulled back if it refits easily, so the probe body, the grease and the cable strain relief show. Shoot from 6 in away, square to the pipe. Use 2× zoom rather than moving the phone closer, which keeps focus. Lock on the probe. Light from the side to show texture.
16. **Y-strainer and gauges.** The strainer body, the cap and the gauge or pressure sensor on the same run in one frame. Then cut to the gauge face alone, readable. Shoot the gauge square-on to avoid parallax on the needle. Lock on the needle.
17. **Integration panel, wide walk.** Begin with the whole panel in frame and hold 3 seconds. Then truck slowly left to right at chest height, keeping the phone parallel to the panel face, about 4 ft away. Use the 0.5× lens if the panel will not fit at 1×, and keep its edges straight. Do not pan by turning your wrist.
18. **HZ-432 and zone lights.** The HZ-432 face with its zone and equipment LEDs readable. Film it during a call, so at least one zone light and an equipment light are lit. Shoot square to the panel, slightly below its centre so the LEDs face the lens. Lock on the LED column. Turn exposure down a stop (drag the sun icon after locking) so the LEDs do not bloom.
19. **Quattro blocks.** A row of the pass-through blocks with their wires in, showing the colour-coded leads entering and leaving. Shoot from 30° to one side so the wire entries show along the row. Lock on the middle block. Shoot in 4K if you want to crop to a legible terminal label in the edit.
20. **Relays.** The relay row with each label readable (HPCALL, HPHEAT, HPCOOL, DHWX, BLR, DHW, BOS1, BOS2). Square-on, and close enough that the labels fill the width. If a relay has an indicator LED, film it while that relay is energised. Lock on the HPCALL label.
21. **Pi with INT and EXT.** The Pi with INT on top and EXT hanging below it, solder side out, in one frame. Then a push-in to the 7-way link and the plugs. Shoot square-on to EXT's face, then from 30° above to show INT on the Pi. Lock on the board legends. Keep the Pi's LEDs in frame.
22. **Modbus UNO R4 and RS-485.** The UNO R4, its RS-485 adapter, and the twisted pair leaving toward the Chiltrix. Show the board's TX/RX LEDs flickering, which marks the 1 s sweep. Shoot from 30° above, 8 in away. Lock on the RS-485 terminal block. Hold 10 seconds so the flicker reads.
23. **1-wire trunk and H plugs.** The CAT6 trunk entering EXT and the H plugs with their legend (GND · DATA · VCC). Shoot square-on to the plugs. Lock on the legend. Then tilt along the trunk as far as it stays in view.
24. **Emporia in the panel.** The Vue unit and its CTs on the feeders and branch circuits, with the circuit directory visible if possible. Have someone qualified open the panel and film from outside the opening without reaching in. Shoot from 3 ft back and slightly above. Lock on the Vue's label. If the panel cannot be opened safely, film the closed panel and use an Emporia app screenshot instead.
25. **Thermostat on the wall.** One RedLink thermostat, with the room temperature and setpoint readable. Shoot square-on at the display's height, 12 to 18 in away, about 10° off-axis to avoid reflection. Lock on the digits.
26. **Sentry camera on the boiler.** The Tapo camera and the boiler display it watches, both in one frame, so the angled mount shows. Film from 4 to 6 ft away without touching either one; a knock moves the Sentry calibration (CLAUDE.md, Sentry operating rules). Then a 2× zoom of the boiler display alone, at an angle. Lock on the display digits. Check `decodeMargin` in Signal K afterwards.
27. **Data-flow diagram.** One Keynote slide built in three stages: (a) the sources on the left (relays, 1-wire, Modbus, SCB, nodes, Emporia, RedLink, Sentry); (b) the pivac collectors and Signal K in the middle; (c) InfluxDB, Grafana and WilhelmSK on the right. Use the same colour for each source type as in shot 3.
28. **pivac services.** A Terminal window at 125 % font, cropped tight to the output of `systemctl list-units "pivac-*"`, with every line `active running`. Hold 5 seconds. No scrolling.
29. **Signal K data browser.** A browser window cropped to the data table with no tabs or bookmarks showing. Type `hvac` in the filter, hold 5 seconds, then change it to `environment.inside.hvac` and hold. Leave the pointer still while values update.
30. **Chiltrix raw registers.** The same view filtered on `chiltrix.raw`, with a column of `raw.r2xx` values changing. Hold 10 seconds with no pointer movement, so the eye catches the updates.
31. **Hand holding the iPad.** Over-the-shoulder at 45°, with your hand and the iPad in frame and WilhelmSK page 1 showing. Turn the iPad brightness to full. Tilt it slightly away from overhead lights to avoid glare. Lock on the screen. Tap one room tile. This is the only phone shot of a screen.
32. **WilhelmSK pages.** An iPad screen recording in landscape: hold page 1 for 8 seconds, swipe to page 2, then hold for 8 seconds. Make no taps that open dialogs.
33. **Grafana PivacR, 24 h.** A browser cropped to the dashboard, with the time picker showing "Last 24 hours". Scroll slowly through the panels, pausing 3 seconds on each panel the script names.
34. **Utility fan per call.** Zoom to one utility zone heat call, with the airflow, RPM and call panels stacked. Hover the pointer on the 500 CFM, 1630 RPM point so the tooltip shows. Hold 5 seconds.
35. **A P1 lockout.** Zoom to 03:30–05:00 EST on 2026-11-03, with `raw.r284`, `raw.r210` and compressor Hz on screen. Hover on the r210 jump just before the trip. Hold 5 seconds.
36. **INT and EXT on the bench.** If a spare set is on hand, place both boards side by side on a plain dark surface, component side up, and then flip them to show the copper. Shoot from directly overhead on a tripod, filling the frame, with soft light from two sides so the solder joints do not flare. Lock on the silkscreen titles. If no spare set exists, use shot 37 alone.
37. **KiCad 3D of INT and EXT.** KiCad's 3D viewer, full window. Start top-down, then orbit slowly to 45° over 8 seconds and hold. Hide the toolbar panels.
38. **AirMaster renders.** The rendered images in `docs/air-handler-pico-*.png`, moved with Ken Burns in the edit, in this order: board top, box open, box closed showing the LEDs.
39. **AirMaster board in hand.** A spare Rev B board and its box on a plain dark surface, shot overhead as in shot 36, with the USB-A cable and the 24 VAC terminal in frame. Then lift the board and turn it slowly to show both sides. Lock on the board's silkscreen title.
40. **GitHub pivac.** Follow steps 1 to 3 of the GitHub tour. Use browser zoom at 125 %. Pause 3 seconds on each folder or file the script names, and scroll in short steps.
41. **GitHub Arduino.** Follow steps 4 and 5 of the GitHub tour, at the same zoom and pace.
42. **Closing card.** In Keynote, show [owner's name] and [owner's email], with the two repo URLs below.

## Screen capture

### Mac

1. Before recording, turn on Do Not Disturb, quit Mail, Messages and Teams, hide the Dock, and clear the desktop.
2. Set System Settings → Displays to a scaled "Larger Text" resolution, so text stays readable on a phone-sized playback. Set the browser zoom to 125–150 %.
3. Use a browser window with no bookmarks bar, and close all unrelated tabs.
4. Press Cmd-Shift-5, choose "Record Selected Portion", and draw the frame at about 16:9 around the browser or terminal. Under Options, set the microphone to None and turn on Show Mouse Clicks.
5. Move the pointer slowly and pause 3 seconds on each thing the script names. Scroll in short steps.
6. Recordings save to the Desktop as `.mov` files, which iMovie imports directly.

### iPad

1. Add Screen Recording to Control Center (Settings → Control Center) if it is not already there.
2. Turn on Do Not Disturb, so no banner records.
3. Long-press the record button and set the microphone off. Tap Start Recording, wait for the 3-second countdown, then swipe the control center away.
4. Hold the iPad in landscape so the recording fills a 16:9 frame.
5. AirDrop the recording from Photos to the Mac.

### What to record

1. Shot 28: in Terminal, `ssh pi@10.0.0.82 'systemctl list-units "pivac-*" --no-pager'`, at a large font size (Cmd-+ three times). It shows one service per collector.
2. Shot 29: the Signal K admin → Data Browser, with the address bar cropped out of the recording, filtered on `hvac`, then `environment.inside.hvac`. The values update live, which is the point of the shot.
3. Shot 30: the same browser filtered on `chiltrix.raw`, which shows the registers ticking once a second.
4. Shot 32: WilhelmSK, page 1 (rooms, water temperatures, relays, pressures, Sentry), then a swipe to page 2 (Grafana).
5. Shots 33 to 35: Grafana's PivacR dashboard over the last 24 hours. Then zoom to a utility zone heat call showing airflow and RPM per call (`docs/air-handler-fan-optimization.md` has the times). Then zoom to the 2026-11-03 04:00 EST lockout with `raw.r284` and `raw.r210`.
6. Shots 37 and 38: open the boards in KiCad's 3D viewer and orbit slowly. Pan across the AirMaster renders in `docs/air-handler-pico-*.png` with Ken Burns in iMovie. If the Rev B boards have arrived, film the bare board on the bench instead.
7. Shot 39: the AirMaster's own web page, if a unit is running. Otherwise drop the shot and say the line over the renders.
8. Shots 40 and 41: see the GitHub tour below.

### Keep off screen

1. `/etc/pivac/config.yml`, `/etc/pivac/graph.env` and any file under `~/.config/`. They hold the Signal K, RedLink, Emporia, OpenSprinkler and Grafana credentials and the Shelly cloud key.
2. Browser password prompts and saved-login autofill. Sign in before you start recording.
3. Email, Teams and Messages notifications.
4. The AirMaster label sheet and `~/.config/airmaster/units.csv`, which carry each unit's setup password.
5. The `wilhelm-sk` repo, which is private. Show the layout in the app instead.
6. The house address on equipment labels or delivery boxes, and mail or papers in the utility room, since the video may be passed around inside Unico.

## GitHub tour

Both `pivac` and `Arduino` are public repos. Show them in the browser at github.com, cropped below the browser's tab bar. In 60 seconds:

1. `pivac`: the README and file list, then `pivac/` with one file per collector, opening `ChiltrixModbus.py` and `UnicoSCB.py` briefly.
2. `pivac/docs/`: scroll the list, then open `unico-scb-protocol.md` and scroll its frame tables. This is the doc Unico will care about most.
3. `pivac/hardware/`: the board folders (`int-board`, `ext-board`, `extc-board`, `ahp-board`).
4. `Arduino`: the sketch list, then `AirMaster/README.md`.
5. The Pull Requests tab with closed PRs, to show the change history.

## Narration script

Read at an easy pace, about 140 words a minute. Each block is one voice-over take, labelled with its segment and shots. Pause a beat between paragraphs; the cut uses those pauses.

**Seg 0, shots 1–2.**
I'm [owner's name]. This is the monitoring system I built around my Unico installation. Everything in this video is home-built: the sensors, the software, the dashboards, and the circuit boards. I'll walk through the equipment first, then show how the data is collected and displayed.

**Seg 1, shot 3.**
The house has five Unico air handlers, installed in 2009, all on hydronic coils. A Chiltrix CX75 heat pump makes chilled and hot water into a buffer tank. Two sources feed the primary header, each through its own pump: the Taco puts the tank in circuit, and the NTI Ti-200 boiler's pump puts the boiler in circuit, for heat below 30 degrees outside. The boiler also makes the domestic hot water. The two supplies join in one line into the header. Just below it, two closely spaced tees feed the secondary loops, each with its own pump, and each zone takes water through a valve at its air handler. The loops return into the top of the header, and a return line carries the water back to the tank and the boiler. The kitchen and great room also have Bosch units for cooling; in winter all five zones heat from the water.

Each room's Honeywell thermostat talks wirelessly to an interface module at its air handler, which signals the Unico S.M.A.R.T. Control Board. The board's heat, cool and fan outputs are that zone's call at the HZ-432 zone panel. The calls come into the integration panel through Quattro terminal blocks. The panel opens the zone's valve and waits for the valve's end switch, then chooses the heat pump or the boiler and sets the Chiltrix to heating or cooling. Its outputs leave through a second set of Quattro blocks to relays, which switch the primary pump, the loop pumps, the boiler and the Chiltrix's mode. A spare contact on each relay goes to the Pi.

**Seg 2, shots 4–9.**
This is the great room air handler. It has two coils: a hydronic module on the water loop for heat, and a DX coil from a Bosch heat pump for cooling. The box on the S.M.A.R.T. Control Board's USB port is the AirMaster, a board I designed. It reads the control board's serial line and serves a web page. Here it is on my phone: the thermostat calls, the airflow and the motor RPM, live. When I raise the setpoint, the call comes in and the airflow climbs to its stored value.

The utility air handler is pure hydronic. Its sensor node, on an Arduino, reads the coil's water in and out and the supply and return air, and runs on the air handler's own 24 volts. This USB cable takes the same control board data straight to the Pi. I worked out the board's serial protocol, so neither connection changes anything on the board.

**Seg 3, shots 10–16.**
The CX75 sits outside. In the utility room, its water goes into this buffer tank, with temperature probes at the top and bottom. The primary pump carries tank water past these tees, where the two secondary loops draw from it. Loop A serves the kids room and master bedroom; loop B serves the family room, kitchen and great room. Each loop has a probe on its supply and its return, mounted on the copper and insulated, so I can measure the temperature difference every loop delivers. The Y-strainer protects the Chiltrix's heat exchanger, and the pressure readings catch a fouling screen before it trips the low-flow alarm.

**Seg 4, shots 17–23.**
This is the integration panel, where every signal comes together. The HZ-432 zone panel takes the five thermostat calls and decides between the heat pump and the boiler. The Quattro terminal blocks distribute the 24-volt calls from the air handlers and the equipment. Each relay here repeats one of those signals as a dry contact: heat pump call, heating and cooling mode, boiler, domestic hot water, and the Bosch units. The Raspberry Pi reads all ten contacts through the two boards I designed, called INT and EXT. This Arduino is the Modbus interface to the Chiltrix. It reads two hundred and thirty-four registers once a second over RS-485: temperatures, pressures, compressor speed, flow and fault codes. And this cable is the 1-wire trunk for the eight temperature probes on the tank and the loops.

**Seg 5, shots 24–26.**
Two Emporia monitors in the electrical panels measure every major circuit, including the Chiltrix. The five Honeywell RedLink thermostats report room temperature, humidity, setpoints and call state from Honeywell's cloud. And this camera reads the boiler's controller display, so the Pi knows the boiler's water temperature, gas input, and whether the burner is lit.

**Seg 6, shots 27–30.**
The software is called pivac. Each data source has its own small collector program running on the Pi. Every collector sends its readings to Signal K, an open-source data server, which stores everything in an InfluxDB database for more than a year. Here are the collectors running. Here is the live data in Signal K, organized by path: room temperatures, loop temperatures, relays, the Chiltrix, and the air handlers. These are the Chiltrix's raw registers, updating every second.

**Seg 7, shots 31–32.**
On the iPad and the phone, an app called WilhelmSK shows the live picture: each room's temperature and call, the water temperatures around the loop, the relays, the system pressures and the boiler. It also receives the alerts. When something goes wrong, such as a stale sensor, a low flow or a Chiltrix lockout, I get a push notification and an email.

**Seg 8, shots 33–35.**
Grafana draws the history. Here is a day of the whole system. This is the utility zone's fan during a heat call: the stored airflow and the actual airflow and RPM, read from the control board. I use this to tune airflow per call. And this is a Chiltrix high-pressure lockout, with the compressor's high-side pressure jumping in the last minute before the trip. I've shared this data with Chiltrix.

**Seg 9, shots 36–39.**
These are the custom boards. INT sits on the Pi and carries the relay inputs. EXT holds the 24-volt power supply that runs the Pi, and the 1-wire interface. And this is the AirMaster you saw on the great room air handler. It plugs into the S.M.A.R.T. Control Board's USB port, runs on the air handler's 24 volts, and puts the board on Wi-Fi. A homeowner or technician can see the calls, airflow and RPM from its own page, with no other software, and it can also report to a home system like mine.

**Seg 10, shots 40–41.**
All of the code and the hardware designs are on GitHub. The pivac repository has the collectors, the dashboards and the documentation, including the full write-up of the control board protocol. The Arduino repository has the firmware for the nodes and the AirMaster.

**Seg 11, shot 42.**
That's the system. I'd be glad to walk your team through any part of it on a call. Thanks for watching.

## Recording the voice-over

1. Record in a small, furnished room with the heat pump and fans quiet. A closet full of clothes is ideal.
2. Use AirPods or the iPhone itself 8 to 12 inches from your mouth, slightly off to one side to avoid popping on P and B.
3. Record each segment as its own take in GarageBand on the Mac (Voice track, "Narration Vocal" preset), or in Voice Memos on the iPhone. Re-read any line you stumble on; cut the bad take later.
4. In GarageBand, trim the takes, then export each with Share → Export Song to Disk as AAC.

## Editing in iMovie

1. Create a new Movie project. In Settings, leave the theme off.
2. Import the B-roll, screen recordings, Keynote PNGs and voice-over files into one event.
3. Lay the voice-over takes on the audio track in segment order. They set the timing.
4. Drop the B-roll above each take in shot-list order and trim each clip to its sentence. Cut on the pauses between paragraphs.
5. Put a lower-third title (Titles → Lower Third) on the first close-up of each component: "Unico S.M.A.R.T. Control Board", "HZ-432 zone panel", "Chiltrix Modbus interface", "INT and EXT boards", "AirMaster".
6. Use Ken Burns on the Keynote stills and the board renders. Keep transitions to plain cuts, with a cross-dissolve only between segments.
7. Set the B-roll clip volume to zero, so only the voice-over plays. Lay room tone under any silent gap.
8. Share → File, 1080p, quality High. A 13-minute video comes to about 1 to 2 GB.

## Delivery

The file is too large to attach to email. Upload it to OneDrive and send a view-only link, or upload it to YouTube as Unlisted and send that link. YouTube plays better on a phone and lets Unico share it internally. Send the link as a reply on the existing email thread with Unico customer service, so the context travels with it.
