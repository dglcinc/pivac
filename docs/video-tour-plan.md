# Video tour of the monitoring setup, for Unico

Brian Intagliata (Unico customer service) asked on 2026-11-06 for a video of the monitoring setup so his team can review it. This plan covers the shot list, the narration script, how to capture the Mac and iPad screens, and how to cut the video together in iMovie. The target length is 12 to 14 minutes.

## Approach

Shoot the equipment on the iPhone as silent B-roll, record every screen directly with the built-in screen recorders, and narrate afterwards as one voice-over read from the script below. Narrating live while holding a phone in the utility room yields uneven audio and long takes. A voice-over recorded in a quiet room is even in level, can be re-read line by line, and sets the pace for the cut, so the pictures are trimmed to fit the words.

Record the screens rather than filming them with the phone. A phone filming a monitor picks up moiré, glare and a tilted frame, and small text becomes unreadable. Native screen recordings stay sharp at any zoom. The one exception is a short shot of a hand holding the iPad running WilhelmSK, which shows the app in use. Film that one with the phone.

All the software is already on hand: the iPhone camera, Screenshot (Cmd-Shift-5) and QuickTime on the Mac, Screen Recording on the iPad, Keynote for the diagram and title cards, GarageBand for cleaning up the voice-over, and iMovie for the edit.

## Outline

| Seg | Topic | Time |
|-----|-------|------|
| 0 | Open | 0:30 |
| 1 | System diagram | 1:00 |
| 2 | Air handlers | 1:30 |
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
| 1 | 0 | David at the panel, wide | iPhone |
| 2 | 0 | Title card | Keynote |
| 3 | 1 | System diagram | Keynote |
| 4 | 2 | MBR air handler, wide | iPhone |
| 5 | 2 | MBR node on DIN rail | iPhone |
| 6 | 2 | MBR coil probes | iPhone |
| 7 | 2 | Utility air handler, wide | iPhone |
| 8 | 2 | SCB, USB cable | iPhone |
| 9 | 2 | Utility node, rev A shield | iPhone |
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
| 38 | 9 | AirMaster renders, board | Mac/iPhone |
| 39 | 9 | AirMaster web page | Mac |
| 40 | 10 | GitHub pivac repo | Mac |
| 41 | 10 | GitHub Arduino repo | Mac |
| 42 | 11 | Closing card | Keynote |

Notes by shot number:

1. Shot 1 is the one on-camera shot. Prop the phone on a tripod at chest height with the panel behind you. Say nothing; the voice-over covers it.
2. Shots 2, 27 and 42: build them in one Keynote deck, 1920 × 1080, plain dark background. Export with File → Export To → Images (PNG) and drop the stills into iMovie.
3. Shot 3 is one Keynote slide drawn as boxes and arrows. Outdoors sits the CX75. In the utility room are the buffer tank, the primary loop and loops A and B to the five Unico air handlers, with the Ti-200 boiler on the same loop and the two Bosch units for kitchen and great room cooling. Reveal one group per click, then export each build stage as its own PNG so the diagram assembles in step with the words.
4. Shots 5, 6 and 9: show the node's label, the coil supply and return probes, and the duct air sensors. Shot 8 is a close-up of the USB cable at the SCB. It matters most to Unico, so hold it 10 seconds.
5. Shot 11: film the CX75 display at an angle to avoid glare.
6. Shot 15: one probe close up, with the insulation pulled back if it can be refitted easily. This shows how the probe is mounted.
7. Shots 17 to 23 are a slow walk across the panel from left to right. Then repeat each part as a held close-up, in 4K if the terminal labels must be legible.
8. Shot 24: film the Emporia CTs with the panel's dead front on, or with the panel safely open by someone qualified. Never reach into a live panel holding a phone.
9. Shot 26: the camera and the boiler display it reads. Avoid bumping the camera: any knock moves the Sentry calibration (CLAUDE.md, Sentry operating rules), so film from a distance and check `decodeMargin` afterwards.
10. Shots 28 to 41 follow the screen capture section below.

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
2. Shot 29: the Signal K admin at `https://68lookout.dglc.com/admin/` → Data Browser, filtered on `hvac`, then `environment.inside.hvac`. The values update live, which is the point of the shot.
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

## GitHub tour

Both `dglcinc/pivac` and `dglcinc/Arduino` are public, so show them in the browser at github.com, signed in so the private repos list is not needed. In 60 seconds:

1. `pivac`: the README and file list, then `pivac/` with one file per collector, opening `ChiltrixModbus.py` and `UnicoSCB.py` briefly.
2. `pivac/docs/`: scroll the list, then open `unico-scb-protocol.md` and scroll its frame tables. This is the doc Unico will care about most.
3. `pivac/hardware/`: the board folders (`int-board`, `ext-board`, `extc-board`, `ahp-board`).
4. `Arduino`: the sketch list, then `AirMaster/README.md`.
5. The Pull Requests tab with closed PRs, to show the change history.

## Narration script

Read at an easy pace, about 140 words a minute. Each block is one voice-over take, labelled with its segment and shots. Pause a beat between paragraphs; the cut uses those pauses.

**Seg 0, shots 1–2.**
I'm David Lewis. This is the monitoring system I built around my Unico installation in northern New Jersey. Everything in this video is home-built: the sensors, the software, the dashboards, and the circuit boards. I'll walk through the equipment first, then show how the data is collected and displayed.

**Seg 1, shot 3.**
The house has five Unico air handlers, installed in 2009, all on hydronic coils. A Chiltrix CX75 heat pump makes chilled and hot water into a buffer tank. A primary loop carries water from the tank to two secondary loops, which feed the coils. An NTI Ti-200 boiler shares the same loop for heat below 30 degrees outside, and for domestic hot water. The kitchen and great room have Bosch units for cooling; in winter all five zones heat from the water loop.

**Seg 2, shots 4–9.**
This is the master bedroom air handler. The box on the DIN rail is a sensor node I built on an Arduino. It reads the coil's water in and out, the supply and return air, and the high-fan call, and it runs on the air handler's own 24 volts. The utility zone has the same node, plus one more connection. This USB cable goes into the S.M.A.R.T. Control Board. I worked out the board's serial protocol, so the Pi reads all six thermostat inputs, the actual airflow and the motor RPM every few seconds, without changing anything on the board.

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
These are the custom boards. INT sits on the Pi and carries the relay inputs. EXT holds the 24-volt power supply that runs the Pi, and the 1-wire interface. This is the AirMaster, the newest board. It plugs into the S.M.A.R.T. Control Board's USB port, runs on the air handler's 24 volts, and puts the board on Wi-Fi. It serves its own web page, so a homeowner or technician can see the calls, airflow and RPM without any other software, and it can also report to a home system like mine. The second revision is being made now.

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

The file is too large to attach to email. Upload it to OneDrive and send Brian a view-only link, or upload it to YouTube as Unlisted and send that link. YouTube plays better on a phone and lets his team share it internally. Reply on the "Intro to David Lewis" thread so the context travels with it.
