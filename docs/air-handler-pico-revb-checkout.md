<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
<!-- Copyright David Lewis -->

# AirMaster carrier Rev B: checkout

Run this on a built board (`docs/air-handler-pico-assembly.md`). Never connect a computer to the Pico's micro-USB
while 24 VAC is on J1: U1 and the micro-USB both feed U4 pin 40, and Rev B has no lockout.

## 1. Unpowered, micro-USB empty

| Between | Expect |
|---|---|
| TP2 and TP3 | open |
| TP1 and TP2 | no short |
| J1 R and C | no short |
| U4 pin 40 and GND | no short |
| U4 pin 36 and GND | no short |

1. TP2 to TP3 is the isolation across U1: TP2 is the high side's COM, TP3 the low side's GND.
2. Check C1's stripe faces its minus pad before going on.

## 2. Bench 24 VAC on J1, micro-USB empty

| Between | Expect |
|---|---|
| TP1 and TP2 | about 35 V DC |
| U4 pin 40 and GND | 5.1 V |
| U4 pin 36 and GND | 3.3 V |
| J4 pin 1 and GND | 5.1 V |
| LED1 | lit |

## 3. Flash, J1 unplugged

1. Copy `~/github/Arduino/arduino_secrets.h.example` to `AirHandlerPico_Bench/arduino_secrets.h` and enter the
   `redux` credentials.
2. `arduino-cli compile -b rp2040:rp2040:rpipicow:usbstack=tinyusb_host,flash=2097152_1048576 AirHandlerPico_Bench`
3. Hold BOOTSEL, plug the micro-USB into the Mac, and copy the `.uf2` to the `RPI-RP2` drive.
4. Unplug the micro-USB, then plug in J1.

## 4. Run on 24 VAC alone

Start `nc -ul 5515` on the Mac Mini (`10.0.0.84`) before plugging in J1. The bench build sends its log there.

| Check | Expect |
|---|---|
| Log | `join redux: ok` |
| Log | `DS2482 found` |
| J2, two probes | two `probe 28 …` lines |
| `curl <ip>/data` | JSON line |
| Water pair | room temperature |
| Air pair on J3 | room ±1 °F |
| `rssi`, lid open | record |
| `rssi`, lid closed | record |

1. Log: the join line carries the IP address and RSSI. Without `DS2482 found`, the log asks for 3.3 V at U2 pins 1
   and 3; measure that first.
2. Probes: use two calibrated probes. The bench build reads the first two on the bus in search order and logs every ROM.
3. Water and air pairs: a probe from the 2026-11 batch reads 6.2 to 7.0 °F low until its offset is applied, so
   judge a batch pair against each other. The NTCs need their own calibration on this ADC.
4. RSSI: close the lid and fit all three screws before the second reading. The Rev C order waits on the difference.
5. LEDs 2–6 follow the SCB's calls and stay dark with no SCB connected.

## 5. On an SCB (optional)

At the utility air handler, unplug the Unico USB board from the Pi, plug it into J4, and power J1. The log shows
`USB device mounted`, and `/data` carries the calls, airflow and RPM within a few seconds. Plug the Unico board back
into the Pi afterwards, because `pivac-scb-utility` reads the utility zone from it.
