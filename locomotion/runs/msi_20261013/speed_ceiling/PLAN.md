The current 0.025 m/s limit is a chosen simulation preview cap. It does not
establish the highest speed of this robot, this gait, or the assembled hardware.

The inherited toe stride is limited to 0.035 m. With stance fraction 0.8 and
translation gain 1.15, its uncapped requested-speed limit is
`0.035 / (0.8 * cycle_s * 1.15)`. That is 0.03170 m/s at 1.2 seconds,
0.03804 m/s at 1.0 seconds, and 0.04755 m/s at 0.8 seconds. Above this
value, a larger request produces the same capped toe stride.

Ranked predictions recorded before execution:

1. The UI/API limit may exclude useful additional stride. A 1.2 s cycle with
   a 0.04 m/s request should move faster than the saved 0.025 m/s reference,
   although the geometric stride will cap at 35 mm.
2. Faster cadence may increase actual progress. Compare 1.0 s and 0.8 s cycles
   with the same 0.025 and 0.04 m/s requests; body shift continues to scale
   with cycle length under the existing rule.
3. Servo target slew and contact slip may eventually consume the geometric
   gain. A 0.8 s cycle with a 0.06 m/s request should plateau or regress if
   its greater target demand only increases lag and slip.

Exactly eight forward cases are authorized, each 480 control steps on nominal
flat ground. The phone payload is 0.155 kg for six `(cycle_s, request_m_s)`
cases: `(1.2, .04)`, `(1.0, .025)`, `(1.0, .04)`, `(.8, .025)`,
`(.8, .04)`, `(.8, .06)`. The bare payload runs `(1.0, .04)` and
`(.8, .04)`. At most three workers run together. Seeds match the saved
selected 1.2 s / 0.025 m/s reference for each payload.

Torque, gains, no-load speed, target slew, latency, lift, recovery and physics
sources remain exact. No longer acceptance suite, training, final-policy
selection, hardware calibration or serial actuation is part of this screen.
Requested command and scored command stay identical; unchanged strict
tracking failures remain failures.
