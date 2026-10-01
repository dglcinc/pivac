# Circuit simulation

`run.sh` runs the EXT board's power section in ngspice (`brew install ngspice`) over a table of cases and prints one line per case. The circuit is in `ext-supply.cir.in`: the 24 VAC source with the transformer's resistance, F1, the D1 to D4 bridge, C3 with its ESR, U3 as a constant-power load above its 16.4 V lockout, and the sense channels as 35 mA.

| Column | Meaning |
|---|---|
| valley, peak, mean | VS against COM in steady state, V |
| Irms | current through F1, A RMS |
| I_f1pk | peak of the charging pulses through F1, A |
| inrush | peak current at switch-on at the crest of the line with C3 empty, A |

Assumed, to be replaced by measurement: transformer resistance 1.0 Ω, F1 0.25 Ω, C3 ESR 0.1 Ω, U3 efficiency 89 %. The transformer's leakage inductance is left out, so the inrush figure is an upper bound.
