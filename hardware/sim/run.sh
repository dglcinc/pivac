#!/bin/sh
# Runs the EXT supply model over a table of cases and prints one line per case.
# usage: hardware/sim/run.sh     (needs ngspice: brew install ngspice)
cd "$(dirname "$0")"
printf "%-34s %6s %6s %6s %7s %7s %8s\n" case valley peak mean Irms I_f1pk inrush
run() { # name vrms pload rsrc phase isense
  sed -e "s/@VRMS@/$2/" -e "s/@PLOAD@/$3/" -e "s/@RSRC@/$4/" -e "s/@PHASE@/$5/" -e "s/@ISENSE@/$6/" ext-supply.cir.in > /tmp/ext-supply-$$.cir
  ngspice -b /tmp/ext-supply-$$.cir 2>/dev/null | awk -v n="$1" '
    /^v_valley/{a=$3} /^v_peak/{b=$3} /^v_mean/{c=$3} /^i_rms/{d=$3} /^i_f1pk/{e=$3} /^i_inrush/{f=$3} /^i_inrmin/{g=$3}
    END{ if (-g>f) f=-g; printf "%-34s %6.2f %6.2f %6.2f %7.3f %7.2f %8.1f\n", n,a,b,c,d,e,f }'
  rm -f /tmp/ext-supply-$$.cir
}
run "idle Pi 0.6 A, 25.9 V"           25.9  3.4 1.0 90 0.035
run "typical Pi 1.0 A, 25.9 V"        25.9  5.7 1.0 90 0.035
run "Pi peak 1.5 A, 25.9 V"           25.9  8.6 1.0 90 0.035
run "U3 full 2.4 A, 25.9 V"           25.9 13.8 1.0 90 0.035
run "Pi peak, 24.0 V"                 24.0  8.6 1.0 90 0.035
run "Pi peak, low line 21.6 V"        21.6  8.6 1.0 90 0.035
run "U3 full, low line 21.6 V"        21.6 13.8 1.0 90 0.035
run "U3 full, low line, 2 ohm xfmr"   21.6 13.8 2.0 90 0.035
run "Pi peak, stiff xfmr 0.3 ohm"     25.9  8.6 0.3 90 0.035
