# Unico S.M.A.R.T. Control Board serial protocol

This is the protocol between Unico's ECMConfig program and the S.M.A.R.T. Control Board (SCB), carried by the A01470 USB board. `scripts/unico-scb.py` implements it and `docs/unico-scb-live-test.md` is the procedure for proving it against an air handler, with the record of the 2026-10-24 run on the utility zone's M2430 (firmware 3.21), which passed every stage. Statements marked "measured" come from that run; the rest is read from the program.

Every claim cites `File.cs:line` in ILSpy's decompilation of ECMConfig 4.6. Where the decompiled logic is contradictory or only implies a meaning, the text says "inferred" and the point is repeated in section 9. The checksum examples are checked by `tests/test_unico_scb.py`.

To regenerate the source the citations refer to, on a Mac:

```bash
curl -LO https://unicosystem.com/wp-content/uploads/2022/09/ECM-Configuration.zip
unzip ECM-Configuration.zip
brew install sevenzip dotnet && dotnet tool install -g ilspycmd
7zz x -oinst ECMConfig_4.6_Installer.exe          # NSIS installer, unpacked without running it
cp "inst/Application Files/ECMConfig 4.6_4_6_0_0/ECMConfig 4.6.exe.deploy" ecm46.exe
DOTNET_ROOT=/opt/homebrew/opt/dotnet/libexec DOTNET_ROLL_FORWARD=Major ~/.dotnet/tools/ilspycmd -p -o src ecm46.exe
```

The decompiled source is Unico's code and stays out of this repo.

### Wiring (Bulletin 30-039.007, p. 26)

The USB board sits in the data path between the SCB and the motor and is always fitted, so the SCB-to-motor traffic crosses it whether or not a PC is attached.

| Link | Harness | Pin and colour |
|---|---|---|
| SCB header to USB board | A01474-G01 data cable | 1 Blue, 2 Yellow, 3 Orange, 4 Black |
| USB board to motor plug | A01473-G01, data wires | Blue 3, Orange 4, Black 7, Yellow 8 |
| SCB to motor power | A01473-G01 | Red 1, Purple 5, GND 6 |
| Motor plugs | A02624-G01 | power 1 Red, 5 Black, 6 Green; comm 7, 4, 8, 3, all brown |

The USB board's green LED flashes when the SCB sends to the PC and the red LED when the PC sends to the SCB (Bulletin 30-039.007, table 6). The levels on the data wires are not documented; a forum capture of a Regal ECM link measured 0 to 5 V at 4800 8N1.

## 1. Architecture in one paragraph

The SCB is the bus master and the PC only answers. The program never sends a request on its own: it reads whatever bytes have arrived, and when it finds a valid SCB frame it immediately transmits one reply frame (`ECM_Configuration.cs:9692-9721`, `9886-9896`). The help text says the same: "The ECMConfig program follows instructions from the SMART Control Board (SCB)" (`Variable_Speed_Setup.Communication.resx`, `RichTextBox1.Text`). There is exactly one PC message type, a fixed-layout frame that carries every requested setting at once; there are no separate read, write or factory-reset commands. The USB board sits on the SCB-to-motor harness (bulletin 30-039 pp. 26, table 11: "Wiring Harness, SCB/USB to Motor harness … supplies power and communication to the motor"), so the PC's receive line also carries SCB↔motor traffic, which the program recognises and ignores ("motor talk", `ECM_Configuration.cs:14581-14722`).

## 2. Serial settings

| Item | Value | Source |
|---|---|---|
| Driver object | `Comm64.Comm` (MSComm-compatible wrapper, `Comm64.dll`) | `ECM_Configuration.cs:731`, `6340`, `using Comm64` line 15 |
| Settings | `"4800,n,8,1"` (4800 baud, no parity, 8 data, 1 stop) | `ECM_Configuration.cs:9197` |
| Handshaking | `0` (none) | `9187` |
| DTREnable | `true` (DTR asserted while open) | `9184` |
| RTSEnable | `true` (RTS asserted while open, never toggled) | `9195` |
| InputLen | `0` (read everything available) | `9189` |
| rThreshold / sThreshold | `1` / `1`, but no OnComm handler is attached anywhere; reception is polled by a timer | `9194`, `9198`; no `OnComm`/`Comm1_` handlers in the file |
| RxTimeout / TxTimeout | `0` / `0` | `9196`, `9199` |
| In/Out buffer size | 4096 / 4096 | `9188`, `9191` |
| EOFEnable / EOFChar | `false` / 26 | `9185-9186` |
| NullDisgard | `false` (NUL bytes kept) | `9190` |
| ParityReplace | `'?'` (moot, no parity) | `9193` |
| Initial CommPort | 1, then replaced by the port scan | `9183` |

`Comm.readBytes(n)` waits up to `RxTimeout` ms for `n` bytes and returns what is buffered; with `RxTimeout = 0` it returns at once with up to 4096 bytes (Comm64 IL, `Comm.readBytes`). `writeBytes` contains no RTS or DTR manipulation (Comm64 IL, `Comm.writeBytes`).

### 2.1 Port discovery

At load, `VerifyTimer` (enabled, 5000 ms, `ECM_Configuration.cs:6859-6860`) scans COM 0 through 127 and opens the first port whose `getPortName()` contains `"USB"`, then disables itself (`10131-10179`). `InputTimer` repeats the same scan whenever `foundComm` is false (`9428-9499`). A pyserial port of this is "open the USB serial device". The installer ships FTDI VCP drivers (`Drivers/ftdiport.inf`), but the board fitted here enumerates as a Cypress Semiconductor CDC device ("USB ___ Serial Cable", USB serial number `unicousb`), which macOS drives without an installer as `/dev/cu.usbmodemunicousb1`; on Linux expect `/dev/ttyACM0`. The tool looks for `cu.usbmodem*`, `cu.usbserial-*`, `ttyACM*` and `ttyUSB*`.

### 2.2 Timers

| Timer | Interval | Role | Source |
|---|---|---|---|
| `InputTimer` | 5000 ms at start; 100 ms once any SCB frame is seen; 200 ms after 10 empty reads or 29 short reads | Poll, parse, reply | `6450-6451`, `9646`, `9891`, `9941`, `9959`, `9966`, `10020` |
| `VerifyTimer` | 5000 ms, one-shot | Initial port scan; later re-validates an out-of-range user entry | `6859-6860`, `10123-10317`, `14395` |
| `ServiceLoggerTimer` | 5000 ms, aligned to a 5-s wall-clock boundary | Writes UI values to a CSV; no serial I/O | `Service_Logger_Window.cs:331`, `421` |
| `LoggingTimer` | 1000 ms | Blinks the logger indicator | `Service_Logger_Window.cs:356` |

### 2.3 One InputTimer tick

1. `readBytes(4096)` then `InBufferCount = 0`, which discards anything that arrived during the read (`ECM_Configuration.cs:9540-9541`).
2. If a previous tick left a partial buffer in `oldInput`, the new bytes are appended to it and the joined buffer is parsed (`9560-9578`).
3. Fewer than 5 bytes: `TooShort` keeps them in `oldInput` for the next tick (`9590`, `9955`, `14845-14864`).
4. Otherwise `Watch.getRxCRC` parses (section 4) and returns a code `b4` (`9596-9601`):
   * `255`: no `01 83`/`01 84` header, i.e. SCB↔motor traffic. `MotorTalk` keeps the buffer for re-assembly and the tick returns with no reply (`9611-9623`).
   * `254`: header found and byte 2 = `0xFF`. The SCB reports it cannot talk to the motor; the UI shows "SCB can not communicate with the motor" and the tick returns **without replying** (`9625-9633`, `Dashboard.cs:1822-1825`).
   * `>0` with `01 83` at the frame start: decode with `rx1`, refresh the UI, and send the reply frame with `makeOutput()` (`9641-9721`).
   * `>0` with `01 84`: decode with `rx2` (four-hour log), then `makeOutput()` (`9886-9896`).
   * `>0` with any other header: `wrongComm++`; after 7 in a row the port is closed and rescanned (`9898-9903`).
   * `0`: `BadChecksum` retries the parse one byte further on if more than 50 bytes remain, otherwise stashes the buffer (`9934-9942`, `14724-14802`).
5. Nothing received: `ReceivedNothing`; after 10 consecutive empty ticks (about 1 s at 100 ms) the UI declares "No communication with SCB Board" (`9996-10036`, `10385`).

`AcceptNewData` counts failed ticks; at 26 it clears every decoded value (`Watch.clear`) and sets `timeOut = 5` so that the next good frame reloads the requested values from the stored ones (`11786-11817`, `9738-9753`).

### 2.4 Echo of the PC's own transmission

The program contains no explicit echo suppression. `makeOutput` empties the receive buffer immediately before writing (`ECM_Configuration.cs:11845-11850`) and writes the frame (`11855`); nothing discards bytes after the write. If the PC's own frame comes back on the shared line, the parser treats it as follows: it starts `01 83` like an SCB frame, but byte 3 is 28 (`Watch.cs:80`), which is not 20 or 23, so the parser checks it as a 9-byte frame (`Dashboard.cs:1836-1839`, `1864-1866`). The Fletcher sums at byte 8 are non-zero, the code returns 0, and `BadChecksum` re-parses from the next byte when more than 50 bytes remain (`ECM_Configuration.cs:14728-14757`). A reimplementation should discard its own transmitted bytes explicitly: after `write()`, read and drop `len(frame)` bytes if they match, or reject any `01 83` frame whose byte 3 is `0x1C`. Measured: the Cypress board does not loop the PC's bytes back; no `01 83 … 1c` frame appeared after any of the five transmissions of 2026-10-24.

## 3. Frame format

All frames start with a two-byte header and end with two Fletcher check bytes. Multi-byte values are big-endian (high byte first) throughout (`Watch.cs:102-103`, `Dashboard.cs:2404`).

| Byte | SCB → PC status | SCB → PC log | PC → SCB reply |
|---|---|---|---|
| 0 | `0x01` | `0x01` | `0x01` |
| 1 | `0x83` (131) | `0x84` (132) | `0x83` (131) |

The same `01 83` header is used in both directions; direction is distinguished by byte 3 (section 3.3). Whether `0x01` is an address is not stated in the code; the motor-bus traffic the program ignores begins with `0x0A` (`ECM_Configuration.cs:14612`), which suggests a node-address byte (inferred).

There is no preamble, break or inter-frame marker; `set_Break` exists in Comm64 but is never called.

### 3.1 Checksum (Fletcher-16 check bytes)

Transmit (`Message.cs:99-108`, `Dashboard.cs:1712-1733`): with `s1 = s2 = 0`, for every byte from index 0 (the `0x01`) through index `N-3` (the last payload byte):

```
s1 = (s1 + b) % 255
s2 = (s2 + s1) % 255
```

then

```
c0 = 255 - ((s1 + s2) % 255)
c1 = 255 - ((s1 + c0) % 255)
frame[N-2] = c0 ; frame[N-1] = c1
```

The checksum covers the header too. Receive (`Message.cs:117-133`): run the same two sums over the whole frame including `c0, c1`; the frame is valid when `s1 == 0 and s2 == 0`. `c0` and `c1` always fall in 1..255 and are never 0 (checked on 200,000 random frames), which is why the parser rejects any candidate whose last two bytes contain a 0 (`Dashboard.cs:2041-2064`). Because the arithmetic is modulo 255, a byte `0xFF` contributes like `0x00`.

Verified example, the PC's idle 43-byte frame (all requests empty, flags `0xFE`, override byte `0x01`):

```
01 83 fe 1c 01 00×36 7f df
```

Example with settings (from `fletcher_check.py`):

```
01 83 00 1c 02 01 2c 01 c2 02 58 01 f4 02 58 02 58 07 08 07 08 07 08 07 08 07 08 07 08 14 02 58 00 07 d0 04 0a 08 83 00 00 84 a8
```

### 3.2 How the receiver finds a frame and its length

`Dashboard.NewRx` guesses a length from the buffer size: 37→36, 36→35, 101→101, >49→50, 9→8, else 50 (`Dashboard.cs:3405-3430`). `Message`'s constructor then scans from index 1 for `01 83` or `01 84`, forces the length to 101 for `01 84`, copies the bytes from the header on, and returns the header's offset (`Message.cs:141-240`). The length variables hold the index of the last byte, so "length 50" means a 51-byte frame.

`Dashboard.getRxCRC` (`Dashboard.cs:1762-2126`) then decides the real length by running the Fletcher sums from the header and seeing where they hit zero:

* Short status frame: if byte 3 is not 20 or 23, the frame is 9 bytes and must validate at index 8 (`1836-1839`, `1864-1866`). A 9-byte buffer goes straight to this test (`1873-1904`).
* Otherwise the sums are run to index 35. Valid there gives a 36-byte frame (`1776-1859`).
* If not, index 36 is tried, giving a 37-byte frame (`1921-1927`), and then 37 onward until the first zero, which gives the 51-byte status frame or the 102-byte log frame (`1929-1949`).
* A candidate whose last byte is 0 is treated as trailing zeros, and the code falls back to the 37-byte length (`CheckRestZeroes`, `1745-1760`, `1951-1990`).
* No header in the buffer returns 255; header with byte 2 = `0xFF` returns 254; valid returns 1; invalid returns 0 (`1822-1825`, `1853`, `1860-1863`, `2084-2087`).

`Message.decreaseLengthNow(n)` simply sets the last-byte index to `n-1`. Its special cases 35, 36, 37, 51 and ≤9 are all no-ops (`lengthNow = lengthNow`), left from debugging (`Message.cs:54-92`). `decreaseLengthNext(51)` sets `lengthNext = 50`, which is how a short SCB frame tells the PC to answer in the long format (section 3.4).

The robust equivalent for Python: find `01 83` or `01 84`; for `01 83` with byte 3 not in {20, 23} test length 9; otherwise test lengths 36, 37 and 51 (`01 83`) or 102 (`01 84`) in that order; accept the first whose Fletcher sums are zero and whose last two bytes are non-zero.

### 3.3 Byte 3

| Value | Meaning | Source |
|---|---|---|
| 20 (`0x14`) | SCB long-status frame from older firmware; PC answers with the 31-byte reply | `Dashboard.cs:1836`, `3224-3227`, `Watch.cs:1867-1879` |
| 23 (`0x17`) | SCB long-status frame from firmware that accepts the 43-byte reply (any value > 20 triggers `decreaseLengthNext(51)`); firmware 3.21 sends it (measured) | `Dashboard.cs:3224-3227`, `3275-3278` |
| other | 9-byte SCB frame, where byte 3 is the firmware version | `Dashboard.cs:2173-2210` |
| 28 (`0x1C`) | Always sent by the PC | `Watch.cs:80` |

### 3.4 Reply length

`Watch.getLength` returns 12 for every `lengthNext` except 35 and 36, where it returns 0 (`Watch.cs:1867-1879`), and `makeOutput` allocates `30 + that + 1` bytes (`ECM_Configuration.cs:11822-11825`). The PC therefore sends 43 bytes after a 9-, 51- or 102-byte SCB frame, and after a 36/37-byte frame whose byte 3 is greater than 20. It sends 31 bytes after a 36/37-byte frame whose byte 3 is 20.

## 4. SCB → PC messages and their decoding

`ECMotorError`, `model`, `switches` and the rest are fields of `Dashboard` (`Dashboard.cs:11-101`). "Unset" sentinels are erased-EEPROM values the code maps to "unknown".

### 4.1 Status frame, 51 bytes (`01 83`, byte 3 = 23)

Decoded by `Dashboard.rx1` with offset `b = 0` (`Dashboard.cs:2128-3283`).

| Bytes | Field | Decoding | Source |
|---|---|---|---|
| 2 | `ECMotorError` (status flags, section 4.5) | raw | `2144-2150` |
| 3 | 23 | protocol level | §3.3 |
| 4 | `model` (section 6.2) | bits 0-1 chassis, bits 2-7 thermostat inputs, active-low | `2157-2163` |
| 5 | `powerLevel` (motor size: 6 or 12) | raw byte | `2276-2306` |
| 6-17 | Stored airflow, CFM, for G, Y1, Y2, W1, W2, E | six u16 BE; skipped (old value kept) if high byte ≥ 63 (`0x3Fxx` = unset), if both bytes are 0, or if below `speedMin[0]` | `2352-2419` |
| 18-29 | Stored speed limit, RPM, same order | six u16 BE; same skip rules against `speedMin[1]` | `2485-2541` |
| 30-31 | Actual airflow, CFM | u16 BE; ignored if `3F FF` | `2542-2581` |
| 32-33 | Actual speed, RPM | u16 BE | `2583-2629` |
| 34 | Stored fresh-air percentage, % | `0xFF` → 0 | `2634-2671` |
| 35-36 | Stored needed airflow | u16 BE; if percentage > 0, `round(raw / 100 × percentage)` gives fresh-air CFM, so raw is total blower CFM; `3F FF` or more → 0 | `2672-2730` |
| 37 | DC bus | volts = value × 4, shown when version > 9; `0xFF` → 0 | `2731-2768`, `1575` |
| 38-39 | `switches` (section 6.3) | u16 BE; `FF FF` → 0, `00 00` → `0xFFFF` (unknown); also `storedConfiguration = byte38 & 0x40`, `storedPerformance = byte38 & 0x20` | `2769-2822` |
| 40-41 | Stored square feet | u16 BE; `FF FF` → 0 | `2874-2921` |
| 42 | Occupants (bits 0-6) and EAC relay (bit 7: `0x80` = "Open", `0x00` = "Closed") | `0xFF` → occupants 0, relay unknown | `2922-2961`, `1587-1600` |
| 43 | Fixed-mode run time, minutes (1-60) | `0xFF` → 0 | `2962-3003` |
| 44 | Fixed-mode interval, hours (1-24) | `0xFF` → 0 | `3004-3041` |
| 45 | Bedrooms (bits 0-5), EAC enable (bit 6, `0x40`), Auto mode (bit 7, `0x80`; 0 = Fixed) | bits 6-7 are read only when `ECMotorError & 0x80`; `0xFF` → all unknown | `3042-3090` |
| 46 | Firmware version | shown as `"3." + n`, or `"2.0"` when 0; `0xFF` → 0 | `3091-3128`, `Watch.cs:613-621` |
| 47-48 | Motor control status (section 4.6) | u16 BE; `FF FF` → 0 | `3129-3176` |
| 49-50 | Fletcher check bytes | | §3.1 |

The units come from the UI: values are shown as CFM and converted to L/s with `× 0.47195` (`ECM_Configuration.cs:10500`); minutes and hours for bytes 43 and 44 come from the Fixed Mode help ("Run ___ minutes every ___ hours … minutes between 1 and 60 … hours between 1 and 24", `Variable_Speed_Setup.Fixed_Mode.resx`).

### 4.2 Status frames, 36 and 37 bytes (`01 83`, byte 3 = 20 or 23)

These carry bytes 0-33 of the 51-byte layout and nothing more. Measured: the 36-byte frame with byte 3 = 23 is what the SCB sends while nothing answers it, one every 0.85 s. The frame after a 43-byte reply is 51 bytes, and the SCB keeps sending 51-byte frames for about ten frames (9 s) after the last reply, then returns to 36 bytes. A client that wants the long frame answers every frame; the idle frame of §8 does it without writing anything. The 37-byte variant is identical except that `powerLevel` occupies bytes 5-6 (u16 BE) and every later field moves up one byte (`b = 1`, `Dashboard.cs:2279-2299`). Checksum is at bytes 34-35 or 35-36. After decoding, the code sets the speed limits from `model % 4` (section 6.1), clears bit 7 of `ECMotorError`, sets stored EAC and Auto mode to "unknown", forces the thermostat-override word to "inactive" (`manual |= 0xFF00`), and if byte 3 is greater than 20 sets `lengthNext = 50` (`Dashboard.cs:3178-3279`).

Section 9 notes a parser quirk that, in a buffer of exactly 37 bytes, decodes a 37-byte frame with the 36-byte offsets.

### 4.3 Short status frame, 9 bytes (`01 83`, byte 3 not 20/23)

| Bytes | Field | Source |
|---|---|---|
| 2 | `ECMotorError` | `Dashboard.cs:2144-2150` |
| 3 | Firmware version (`0xFF` → 0) | `2177-2210` |
| 4 | `model` | `2157-2163` |
| 5-6 | `switches`, u16 BE (same sentinels and bit extraction as §4.1) | `2212-2263` |
| 7-8 | Fletcher | |

The same post-processing as §4.2 follows (`3229-3279`).

### 4.4 Four-hour log frame, 102 bytes (`01 84`)

Decoded by `Dashboard.rx2` (`Dashboard.cs:3285-3309`).

| Bytes | Field |
|---|---|
| 2-3 | `CFMnow`, u16 BE |
| 4-99 | `fourHour[0..47]`, 48 × u16 BE |
| 100-101 | Fletcher |

The Fresh Air Monitor sums the 48 entries and compares them with `storedNeededAirflow × 60 × 4` (`Dashboard.cs:1623-1645`), and the SI display multiplies every entry by 0.0283168 (ft³ → m³, `ECM_Configuration.cs:12237-12306`). Each entry is therefore the fresh air delivered in one 5-minute slot of a rolling four-hour window, in cubic feet (inferred from those two formulas). The display lists them as four columns of 12 (`Dashboard.cs:1606-1622`). The SCB presumably sends this frame only while the Fresh Air Monitor is open, which the PC signals in byte 32 of its reply (inferred, section 5.3).

### 4.5 `ECMotorError` (SCB byte 2)

| Bit | Mask | Meaning in the program | Source |
|---|---|---|---|
| 0 | `0x01` | Echoed back in PC byte 2 bit 0; while set, user edits are not accepted and fields are refreshed from the requested values; speed limits are recomputed. Meaning inferred: "settings changed / refresh". | `Dashboard.cs:3378`, `2825`, `Watch.cs:343-347` |
| 2 | `0x04` | SCB received a frame from the PC that was not `0x83` ("didn't get 131"; USB/cable fault message) | `Dashboard.cs:3367-3370`, `ECM_Configuration.cs:11950-11958` |
| 3 | `0x08` | SCB↔motor: timed out before told to run → "No communication with motor" | `3367-3370`, `11895-11907` |
| 4 | `0x10` | SCB↔motor: timed out telling it to run → also "No communication with motor" | `3363-3366`, `11895-11907` |
| 5 | `0x20` | SCB timed out waiting for the PC ("timed out waiting for vb", "No message"). Measured: clear in the frame after a reply and set again in the next, so it reports the previous interval only | `3353-3360`, `11936-11948` |
| 6 | `0x40` | Enables the Auto-mode airflow check: with G active, Air Cycle switch on and Auto mode stored, the PC flags orange when actual airflow ≤ required blower airflow | `3316-3343`, `11965-11977` |
| 7 | `0x80` | SCB frame carries valid EAC and Auto-mode bits in byte 45 | `3067-3075`, `3211` |
| all | `0xFF` | SCB cannot communicate with the motor; the PC does not reply | `1822-1825`, `ECM_Configuration.cs:9625-9633` |

Measured on the utility zone's board: byte 2 reads `0xA1` unanswered and `0x80` in the frame after a reply, so bits 0 and 7 are set at rest and bit 0 does not depend on the PC.

`getError(1)` ORs a 1 in unconditionally after its tests (verified in IL at `0x1b0b3c`), so it yields 3 when bit 3 or 4 is set and 1 otherwise. The "unrecognized response" and "2" branches of `setCommunication` cannot be reached (`ECM_Configuration.cs:11885-11921`).

### 4.6 Motor control status (bytes 47-48)

From `Dashboard.getControlStatus` (`Dashboard.cs:1510-1580`):

| Condition | Text |
|---|---|
| `& 0x6000` non-zero | "Unknown" (or "?" if also `& 0x8A55`) |
| bit 2 (`0x04`) clear, bit 0 (`0x01`) set | "Control in Starting Routine" |
| bit 2 clear, bit 0 clear | "Stopped" |
| bit 2 clear and `0x0020` | + "Lost Rotor Trip" (red) |
| bit 2 clear and `0x0100` | + "Under Voltage Detected" (red) |
| bit 2 clear and `0x0400` | + "Incomplete Parameters" |
| bit 2 clear and `& 0x1ADA` | text replaced by "?" |
| bit 2 set | "Running" |
| bit 2 set and `0x0800` | + "Blocked Inlet Detected" (red) |
| bit 2 set and `& 0x17FB` | text replaced by "?" |
| `0x8000` | tested, no effect |

When the firmware version exceeds 9 the text is prefixed "Internal DC Voltage: (byte 37 × 4)" (`1575`).

## 5. PC → SCB reply

Built by `ECM_Configuration.makeOutput` (`ECM_Configuration.cs:11819-11857`) and `Watch.getTxCRC` (`Watch.cs:75-185`), then checksummed by `Dashboard.getTxCRC` (`Dashboard.cs:1712-1733`).

### 5.1 Layout

| Bytes | Field | Encoding | Source |
|---|---|---|---|
| 0-1 | `01 83` | | `ECM_Configuration.cs:11826-11827` |
| 2 | Flags (§5.2) | `Dashboard.getError(0)` | `Watch.cs:79`, `Dashboard.cs:3377-3385` |
| 3 | `0x1C` (28) | constant | `Watch.cs:80` |
| 4 | Thermostat override / mode byte (§5.3) | `manual & 0xFF` | `Watch.cs:81`, `246-275`, `Dashboard.cs:176-191` |
| 5-16 | Requested airflow, CFM, G, Y1, Y2, W1, W2, E | six u16 BE; `00 00` if the requested value is 0 or outside `[speedMin[0], speedMax[0]]` | `Watch.cs:86-115`, `Dashboard.cs:257-290` |
| 17-28 | Requested speed limit, RPM, same order | six u16 BE; `00 00` if 0 or outside `[speedMin[1], speedMax[1]]` | same |
| 29 | Fresh-air percentage | byte, 0-255 | `Watch.cs:132-133`, `Dashboard.cs:1270-1287` |
| 30-31 | Blower flow rate for ventilation, CFM | u16 BE = `round(blowerFlowRate × 100 / percentage)`, capped at `speedMax[0]`; 0 if percentage is 0 | `Watch.cs:134-140`, `Dashboard.cs:1167-1178` |
| 32 | Open-windows bitmap (§5.3) | `menusOpen` | `Watch.cs:141-142`, `Dashboard.cs:1346-1365` |
| 33-34 | Square feet | u16 BE, max 30000 | `Watch.cs:143-145`, `Dashboard.cs:967-988`, `1122-1125` |
| 35 | Occupants | byte, max 51 (see §9: overflow bug) | `Watch.cs:146-150`, `Dashboard.cs:802-819` |
| 36 | Fixed-mode run time, minutes | byte, max 60 | `Watch.cs:151-152`, `Dashboard.cs:1392-1414` |
| 37 | Fixed-mode interval, hours | byte, max 24 | `Watch.cs:153-154`, `Dashboard.cs:1431-1453` |
| 38 | Bedrooms (bits 0-5, max 50) OR EAC (`0x40`) OR Auto mode (`0x80`) | if EAC is "unknown" the whole byte is 0; if Auto mode is "unknown" it ORs `0xFF` | `Watch.cs:155-176`, `Dashboard.cs:491-505`, `557-579` |
| 39 | Test flow | always 0 (no caller sets it) | `Watch.cs:177-178`, `Dashboard.cs:1460-1483` |
| 40 | Test pressure | always 0 (no caller sets it) | `Watch.cs:179-180`, `Dashboard.cs:1485-1508` |
| 41-42 | Fletcher | | §3.1 |

The 31-byte reply is bytes 0-28 with the check bytes at 29-30 (`Watch.cs:126-129`).

`makeOutput1` (`ECM_Configuration.cs:11859-11867`, `Watch.cs:187-198`) builds a 37-byte frame: `01 83 02`, byte 3 copied from the received buffer at `Length - 34`, the actual airflow at bytes 29-30, check bytes at 35-36. It is called only from the `default:` branch of `switch (b4)` (`9722-9728`), which cannot be reached because `getRxCRC` returns only 0, 1, 254 or 255. The `case 2` branch (`9694-9699`) cannot be reached either.

### 5.2 PC byte 2

`b = (ECMotorError & 1) | requestedPerformance | requestedConfiguration`, then `| 0xF8` if the override word is above 255 (`Dashboard.cs:3377-3385`).

| Bit | Source value | Meaning |
|---|---|---|
| 0 | SCB byte 2 bit 0 | Acknowledge/echo |
| 1 | `requestedPerformance` = 2 | Auto mode style EnergySaver (0 = MaxComfort) — `Watch.cs:682-728`, `ECM_Configuration.cs:12434-12469` |
| 2 | `requestedConfiguration` = 4 | Damper "Power Open / Spring Close" (0 = "Power Close / Spring Open") — `Watch.cs:628-675`, `ECM_Configuration.cs:12426-12433` |
| 3 | sentinel | Set by the "no request" sentinels `requestedPerformance = 10` (`0b1010`) and `requestedConfiguration = 12` (`0b1100`) (`Dashboard.cs:358-361`, `414-417`, `3447-3449`) |
| 3-7 | `0xF8` | Neither Fixed nor Auto mode is selected (override word ≥ 256) |

The sentinels are replaced by the stored value on first use: `setRequested…` divides the stored bit (`0x40` or `0x20` from SCB byte 38) by 16 (`Dashboard.cs:388-412`, `444-468`).

### 5.3 PC byte 4 and byte 32

Byte 4 comes from `Watch.setManual` (`Watch.cs:246-275`), called with the six "Thermostat Override" check boxes, the two Air Cycle radio buttons and the EAC box (`ECM_Configuration.cs:11842`):

| Bit | Mask | Meaning |
|---|---|---|
| 7 | `0x80` | Override G (fan) |
| 6 | `0x40` | Override Y1 (low cool) |
| 5 | `0x20` | Override Y2 (high cool) |
| 4 | `0x10` | Override W1 (low heat) |
| 3 | `0x08` | Override W2 (high heat) |
| 2 | `0x04` | Override E (emergency) |
| 1 | `0x02` | Auto (ASHRAE) mode selected and Fixed not selected |
| 0 | `0x01` | EAC box checked (also true when the box is indeterminate) |

When neither Fixed nor Auto is selected, `0xFF00` is added to the 16-bit word; only the low byte is sent, but the excess sets bits 3-7 of byte 2 (`Watch.cs:257`, `Dashboard.cs:176-191`, `3384`). Short SCB frames force this state (`Dashboard.cs:3214`, `3265`).

Byte 32 (`menusOpen`): bit 0 is set while the Fresh Air Monitor window is open, bit 1 while the Motor Status window is open (`ECM_Configuration.cs:12196-12217`, `15824-15836`). `setRequestedMenusOpen(v)` ORs `v` when `v < 128` and ANDs it otherwise, so 253 clears bit 1 and 254 clears bit 0 (`Dashboard.cs:1346-1365`).

### 5.4 Requested values and when they change

Each requested field starts at 0, or at the sentinel for performance, configuration, EAC (2 → "unknown") and Auto mode (2 → "unknown") (`Dashboard.cs:3432-3473`). The first time a valid SCB frame arrives after connecting, the program copies stored → requested for every field (`ECM_Configuration.cs:9738-9753`; `Dashboard.cs:206-237`, `600-603`, `776-779`, `932-939`, `1205-1208`, `1247-1250`, `1376-1379`, `1416-1419`, `470-485`, `529-544`). In that first tick the reply is built before the copy (`makeOutput` at `9696`/`9709`, copy at `9741-9753`), so the first reply after every connect carries zeros and sentinels. The SCB therefore treats 0 as "no request"; otherwise ECMConfig would erase the board on every connect. Measured: five idle frames (zeros in bytes 5-40, byte 38 included) left every stored airflow, RPM limit, Air Cycle value and the bedroom count unchanged, and a reply with one airflow changed was reported as stored in the next frame, under a second later.

User edits go through `Watch.getRequested…/setRequested…`, which clamp to the limits in §7 and return 4 when requested ≠ stored or 2 when cleared (e.g. `Dashboard.cs:292-326`, `623-640`). Any 2 or 4 shows the wait cursor until the SCB's later status frames report the new value as stored (`ECM_Configuration.cs:13752-13783`). The help describes this as "waiting for acknowledgment that changes have been saved in memory. Data corruption can occur at this time, and you should wait to power off the SCB until the hourglass has disappeared" (`Communication.resx`).

## 6. Models, limits and switches

### 6.1 Airflow and speed limits set by the program

`speedMin[0]`/`speedMax[0]` bound requested CFM; `speedMin[1]`/`speedMax[1]` bound requested RPM. Defaults are 0/1800 CFM and 400/1800 RPM (`Dashboard.cs:3474-3479`). They are recomputed when `ECMotorError` bit 0 is set or on the first frame:

From a 51-byte frame, by `powerLevel` and model (`Dashboard.cs:2823-2873`):

| powerLevel | Condition | Model | CFM max | RPM min |
|---|---|---|---|---|
| 6 | `model % 2 == 0` | 1218 | 500 | 400 |
| 6 | `model % 2 == 1` | 2430 | 750 | 400 |
| 12 | `switches & 0x400` | 3036 (Aux) | 1200 | 600 |
| 12 | `model % 2 == 0` | 3642 | 1200 | 400 |
| 12 | `model % 2 == 1` | 4860 | 1500 | 400 |

From a 9-, 36- or 37-byte frame, by `model % 4` (`Dashboard.cs:3184-3207`, `3235-3258`): 0 → 500, 1 → 750, 2 → 1200, 3 → 1500 CFM max, RPM min 400. CFM min is always 0 and RPM max always 1800.

### 6.2 Model byte (SCB byte 4)

| Bits | Meaning | Source |
|---|---|---|
| 0-1 | Chassis: 0 = 1218, 1 = 2430, 2 = 3642, 3 = 4860; with Aux = 1, 2 or 3 shows 3036 (not for firmware "2.0"/"3.1") | `ECM_Configuration.cs:11981-12093`, `15639-15668` |
| 2-7 | Thermostat inputs, active-low: bit 7 G, 6 Y1, 5 Y2, 4 W1, 3 W2, 2 E; a row is highlighted when its bit is 0 | `ECM_Configuration.cs:12109-12130`, `Dashboard.cs:3318` |

`getModel` returns `0xFFFF` while `powerLevel` is 0 or the initial 18 (`Dashboard.cs:123-138`).

Factory table from the help (`Factory_Defaults.cs`, TableLayoutPanel cells reconstructed by position; `Model_Number.cs` agrees on the switch columns):

| Model | Default Hi, CFM (L/s) | Default Lo, CFM (L/s) | Range min, CFM | Range max, CFM | Mod | Aux |
|---|---|---|---|---|---|---|
| 1218 | 400 (189) | 300 (142) | 100 | 500 | 1 | 0 |
| 2430 | 625 (294) | 500 (236) | 200 | 750 | 0 | 0 |
| 3036 | 750 (354) | 625 (294) | 300 | 1000 | 1 | 1 |
| 3642 | 875 (413) | 750 (353) | 300 | 1200 | 1 | 0 |
| 4860 | 1250 (590) | 1000 (472) | 400 | 1500 | 0 | 0 |

The Requested Speed Limit help gives an RPM range of 150-1800 (`Requested_Speed_Limit.resx`); the code enforces 400 (600 on the 3036) to 1800 (§9). Air Cycle factory default: Fixed Mode, 10 minutes every 8 hours (`Factory_Defaults.cs:2173`). The Lock-to-Hi-Cool boxes set G = Y2/2, Y1 = 3·Y2/4, W1 = 3·Y2/4, W2 = Y2, E = Y2 (`ECM_Configuration.cs:10483-10751`).

### 6.3 Switch word (SCB bytes 38-39, or 5-6 in the 9-byte frame)

From `Watch.getSwitches` (`Watch.cs:437-611`), `Dashboard.getModel` (`Dashboard.cs:103-140`) and the switch help (`Switches.cs` table):

| Bit | Mask | Meaning |
|---|---|---|
| 15 | `0x8000` | Low static pressure warning ("disconnected ducts, too many ducts") |
| 14 | `0x4000` | Stored damper type: Power Open/Spring Close (`storedConfiguration`) |
| 13 | `0x2000` | Stored Auto style: EnergySaver (`storedPerformance`) |
| 12 | `0x1000` | Capacity switch as latched at power-up |
| 11 | `0x0800` | High static pressure warning ("blocked or closed ducts") |
| 10 | `0x0400` | Aux switch as latched at power-up |
| 9 | `0x0200` | Defrost active |
| 8 | `0x0100` | Chiller switch = Leader (0 = Follower) |
| 7 | `0x0080` | Capacity switch, live (Hi) |
| 6 | `0x0040` | Aux switch, live (ON) |
| 5 | `0x0020` | Boiler switch = Emergency (0 = Primary) |
| 4 | `0x0010` | Air Cycle switch ON |
| 3 | `0x0008` | Potable Water switch ON |
| 2 | `0x0004` | Hum Spd switch = High |
| 1 | `0x0002` | Rev Valve switch = O (0 = B) |
| 0 | `0x0001` | Mod switch, live: 1 = 2430/4860 (Mod = 0), 0 = 1218/3642 (Mod = 1) |

A live bit (0, 6, 7) that disagrees with the latched value (model bit 0, bit 10, bit 12) is drawn red with "Model, Aux, or Capacity switch has changed. ALL data will be reset to new model default value when board power is cycled off, and then on again" (`ECM_Configuration.cs:11992`, `12102-12105`, `13636-13717`). `0xFFFF` means unknown.

## 7. Value ranges and derived quantities

| Field | Range in program | Source |
|---|---|---|
| Requested airflow | `speedMin[0]`..`speedMax[0]` CFM (§6.1) | `Dashboard.cs:292-326`, `ECM_Configuration.cs:13887-13976` |
| Speed limit | `speedMin[1]`..1800 RPM | `ECM_Configuration.cs:13978-14012` |
| Bedrooms | 1-50 in the UI, 50 max in the model | `ECM_Configuration.cs:8032-8033`, `Dashboard.cs:750-753` |
| Occupants | 2-51 in the UI, 51 max | `8019-8020`, `Dashboard.cs:927-930` |
| Square feet | 1-30000 | `7922-7923`, `Dashboard.cs:1122-1125` |
| Fresh-air percentage | 1-255 | `8057`, `Dashboard.cs:1323-1326` |
| Run time | 1-60 min | `8226-8227`, `Dashboard.cs:1411-1414` |
| Interval | 1-24 h | `8192-8193`, `Dashboard.cs:1450-1453` |

Minimum fresh air (ASHRAE 62.2) is `sqft / 100 + 7.5 × (bedrooms + 1)`, or `sqft / 100 + 7.5 × occupants` when occupants is given (`Dashboard.cs:710-748`, `1044-1081`; `ECM_Configuration.cs:14475-14498`). The blower airflow that delivers it is `fresh-air CFM × 100 / percentage`, capped at `speedMax[0]` with the message "Calculated airflow … exceeds blower capacity" (`Dashboard.cs:1185-1203`).

## 8. Which fields write, and what is unsafe

Every reply frame is a write request. The SCB persists any field whose requested value differs from what it reports as stored, and acknowledges by reporting the new value in later status frames (§5.4). Nothing in the protocol is a pure query; a read-only client must still answer the SCB, or the SCB flags "timed out waiting for the PC" (bit 5). A read-only implementation sends the idle frame, which is ECMConfig's own first reply after a connect (§5.4): `01 83`, byte 2 = `(rx[2] & 1) | 0xFE` (the two sentinels and `0xF8` for no mode), byte 3 = `0x1C`, byte 4 = `0x01` (the EAC box indeterminate), zeros in bytes 5-40, check bytes. Measured: it writes nothing (§5.4) and brings the 51-byte status frame (§4.2). `scripts/unico-scb.py idle` sends it.

| PC bytes | Effect | Persistent? |
|---|---|---|
| 5-16 | Stored airflow per mode | Yes (EEPROM, inferred from "saved in memory") |
| 17-28 | Stored RPM limit per mode | Yes |
| 2 bits 1-2 | Auto style and damper type | Yes |
| 29-31, 33-38 | Air Cycle parameters: percentage, ventilation blower CFM, square feet, occupants, run time, interval, bedrooms, EAC, Auto/Fixed | Yes |
| 4 bits 2-7 | **Thermostat override**: forces the SCB to run as if G/Y1/Y2/W1/W2/E were called ("Checking this box will force the SCB to run at the associated flow rate", `Thermostat_Override.cs:156`). Live only; the program never persists it. | No |
| 4 bits 0-1 | Mode and EAC hints | Unknown |
| 32 | Which diagnostic windows are open | No (inferred) |
| 39-40 | Test flow, test pressure; always 0 in this program | Unknown, **do not set** |

**Unsafe items.** The thermostat override runs the blower and, by the switch descriptions, can close the hot-water relay (W1/W2 or E), the chilled-water relay (any call with Chiller = Leader), the condenser and the reversing valve (`Switches.cs` table, rows Boiler, Chiller, Rev Valve). A stuck override bit holds the plant on. In this house those relays are dry contacts that pass 24 VAC to the zone's W and Y inputs at the HZ-432 through the Quattro pass-through terminal blocks, so an override is a zone call: the panel calls the equipment and energises the zone valve. `scripts/unico-scb.py override` sends it behind two flags, a 300 s cap and an explicit release (`docs/unico-scb-live-test.md`). Byte 38 is ambiguous: 0 means "Fixed mode, EAC off, 0 bedrooms" and is also what the program sends while EAC is unknown. Measured on a board in Fixed mode with EAC off and 2 bedrooms stored, a zero byte 38 left the bedroom count at 2; whether it would clear a stored Auto mode or EAC is untested. Test flow and test pressure are untested by the program and their effect is unknown.

**There is no factory-reset command.** Factory defaults are restored only by changing the Model, Aux or Capacity switch and cycling SCB power (`ECM_Configuration.cs:11992`; `Factory_Defaults.cs`, "Restoring the Factory Default Settings"). Save/Load writes and reads a local `settings.txt` of space-separated values: COM port, model, aux, six CFMs, six RPM limits, needed airflow, percentage, run time, interval. Loading only fills the UI fields, and the next replies write them (`ECM_Configuration.cs:15544-15737`).

## 9. Open questions and ambiguities

1. **Byte 38 as "no request" with Auto mode or EAC stored.** Zero is "no request" for the airflow, RPM and Air Cycle fields (§5.4, measured), and a zero byte 38 kept a stored bedroom count, but the board tested was in Fixed mode with EAC off, so whether 0 would clear a stored Auto mode or EAC bit is open. Mirror byte 38 from the status frame when either is set.
2. **Occupants overflow.** In `Watch.getTxCRC` the occupants string is seeded with the square-feet value, and `getRequestedOccupants` overwrites it only when occupants is neither 0 nor 255. With occupants 0 and square feet above 255, the checked byte conversion (`conv.ovf.u1.un`, IL `0x1b1888`) throws, `makeOutput` has no handler, and no reply is sent that tick (`Watch.cs:143-150`). The UI normally fills occupants, so this may be latent.
3. **37-byte frames in a 37-byte buffer.** `getRxCRC` maps a frame valid at index 36 back to 36 (`Dashboard.cs:1993-2006`) when the buffer is 46 bytes or shorter, so `rx1` decodes it with the 36-byte offsets (`b = 0`). With more bytes following, `CheckRestZeroes` keeps the 37-byte length. Whether any firmware sends 37-byte frames is unknown.
4. **Header bytes inside data.** The first loop of `getRxCRC` looks for `01 83` at every index up to 35, not only at 0 (`Dashboard.cs:1812-1840`). A stored value of 387 (`0x0183`) in bytes 6-29 would shorten the check window. A reimplementation should look for the header only at the frame start.
5. **Meaning of `ECMotorError` bit 0** and the exact role of PC byte 2 bit 0 are inferred.
6. **Byte 3 values 20 and 23** are named only by their effect on reply length; their real meaning (protocol version, or a length) is not stated. Firmware 3.21 sends 23.
7. **`powerLevel`** values 6 and 12 select ½-size and full-size motors; their units are not stated. Only 6 and 12 change the limits.
8. **Four-hour log units.** "Cubic feet per 5-minute slot" is inferred from the `× 60 × 4` denominator and the ft³ → m³ factor; `CFMnow` is converted by the same factor and may be a slot total.
9. **When the SCB sends `01 84`**, and whether it depends on byte 32 bit 0, is not visible in the PC code.
10. **Model limits disagree with the help.** The code allows 0 CFM minimum on every model, 1200 CFM on the 3036 (help: 1000) and enforces a 400 RPM floor (help: 150).
11. **Motor-bus frames.** The debug view classifies frames starting `0x0A` by bytes 1, 3, 4/5 and 6 (`ECM_Configuration.cs:14612-14713`: byte 1 = 3 with byte 3 = 3 and byte 5 ∈ {109, 110, 111, 134}, byte 3 = 4 and byte 5 ∈ {108, 114-118}; byte 1 = 29 with byte 3 = 4 and byte 4 ∈ {14, 2}). This is the SCB↔motor protocol, which ECMConfig never decodes. Measured with the motor stopped: three frames in every 0.85 s tick, `0a 03 00 03 00 86 00 f7`, `0a 1d 00 04 02 00 00 01 98` and `0a 03 00 04 00 6c 00 00 c3`, one from each of the program's three classes, each followed by a single byte (`71`, `39`, `be`) that is presumably the motor's answer. Their layout and check bytes are unknown; the capture is `docs/data/unico-scb/2026-10-24-utility-listen-idle.txt`.
12. **`decreaseLengthNow` special cases** (35, 36, 37, 51, ≤9) are all no-ops in the decompiled code; they may have been debugger breakpoints.
13. **MSComm HRESULTs** `0x800A1F55` and `0x800A1F45` on port errors close the port and rescan (`ECM_Configuration.cs:10054-10073`); of the `CommEvent` codes only 1008 (receive overrun) acts, by flushing the input buffer (`11602-11637`).
