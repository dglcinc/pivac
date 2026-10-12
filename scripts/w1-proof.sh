#!/bin/sh
# 1-wire proof for the EXT board on the bench Pi: bring up the DS2482 at 0x18 on i2c-1,
# wait for the bus search, then read every DS18B20 N times and count clean (CRC YES) reads.
#   sudo sh w1-proof.sh [reads-per-probe]     (default 40)
# A chip that logs "DS2482 reset failed" has VCC or GND open (or the Pi's SDA is held low:
# check `i2cdetect -y 1` shows 0x18 alone, not every address).
N=${1:-40}
M=/sys/bus/w1/devices/w1_bus_master1
ls /sys/firmware/devicetree/base | grep -q onewire && echo "WARN: w1-gpio overlay is active; delete it from config.txt"
modprobe ds2482 2>/dev/null || true
if [ ! -e $M ]; then
  echo ds2482 0x18 > /sys/bus/i2c/devices/i2c-1/new_device 2>/dev/null || true
  sleep 2
fi
dmesg | grep -i 'ds2482' | tail -3
if [ ! -e $M ]; then
  echo "FAIL: no w1_bus_master1 (chip not instantiated; check 3.3 V at J2 VCC-GND, then U1's VCC and GND joints)"; exit 1
fi
echo 1 > $M/w1_master_search 2>/dev/null   # ask for a search now; the kernel's own runs every 10 s
sleep 8
echo "master present; slave count: $(cat $M/w1_master_slave_count)"
PROBES=$(ls -d /sys/bus/w1/devices/28-* 2>/dev/null)
[ -z "$PROBES" ] && { echo "FAIL: master up, no 28-* probes enumerated (probe plug V-D-G order, probe leads)"; exit 2; }
echo "probes: $(echo $PROBES | sed 's#/sys/bus/w1/devices/##g')"
ok=0; bad=0
for p in $PROBES; do
  i=0; while [ $i -lt $N ]; do
    if cat "$p/w1_slave" 2>/dev/null | head -1 | grep -q 'YES'; then ok=$((ok+1)); else bad=$((bad+1)); fi
    i=$((i+1))
  done
  echo "$(basename $p): last read $(cat $p/temperature 2>/dev/null) m°C"
done
echo "clean reads: $ok   CRC/read failures: $bad   (target: all clean)"
[ $bad -eq 0 ]
