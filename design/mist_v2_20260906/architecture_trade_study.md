# Knee-drive frame trade study

The fully carriage-mounted knee drive has a torque penalty at the hip because it controls the absolute tibia angle. Mounting the knee motor on the first 40 mm of the femur changes that reaction path. The motor remains near the hip but moves with the upper leg. This is an architectural alternative allowed by the requested weight/complexity tradeoff; it is not yet a fitted CAD revision.

For the current remote architecture, `sK = rK*(h+k)` and hip motor torque is `(tauH-tauK)/rH` before losses. For a motor mounted to the femur driving a belt referenced to that same femur, `sK = rK*k`; hip motor torque becomes `tauH/rH`. This change comes from where the motor housing reacts torque. It cannot be obtained by changing the software matrix while keeping the old hardware.

This comparison holds total mass and endpoint force constant, moves one existing 55 g servo from the yaw carriage to 40 mm down the femur, and adds its static gravity contribution. The 3.95376 kg case uses the existing assumptions. The 5.2 kg case illustrates the upward mass pressure seen in the first actual leg CAD. Neither value is a measured robot weight.

| Mass | Load | Architecture / ratios | Yaw / hip / knee motor demand | Worst peak utilization at 9.9 V |
|---|---|---|---:|---:|
| 3.954 kg | three_static | carriage-mounted, 2/2/2 | 0.000 / 0.701 / 0.371 N m | 52.5% |
| 3.954 kg | three_static | carriage-mounted, 2/3.5/2 | 0.000 / 0.401 / 0.371 N m | 30.0% |
| 3.954 kg | three_static | proximal-femur-mounted, 2/2/2 | 0.000 / 0.320 / 0.371 N m | 27.8% |
| 3.954 kg | two_dynamic_1p5 | carriage-mounted, 2/2/2 | 0.000 / 1.831 / 0.930 N m | 137.1% |
| 3.954 kg | two_dynamic_1p5 | carriage-mounted, 2/3.5/2 | 0.000 / 1.046 / 0.930 N m | 78.4% |
| 3.954 kg | two_dynamic_1p5 | proximal-femur-mounted, 2/2/2 | 0.000 / 0.890 / 0.930 N m | 69.7% |
| 5.200 kg | three_static | carriage-mounted, 2/2/2 | 0.000 / 0.986 / 0.512 N m | 73.9% |
| 5.200 kg | three_static | carriage-mounted, 2/3.5/2 | 0.000 / 0.563 / 0.512 N m | 42.2% |
| 5.200 kg | three_static | proximal-femur-mounted, 2/2/2 | 0.000 / 0.463 / 0.512 N m | 38.3% |
| 5.200 kg | two_dynamic_1p5 | carriage-mounted, 2/2/2 | 0.000 / 2.472 / 1.247 N m | 185.1% |
| 5.200 kg | two_dynamic_1p5 | carriage-mounted, 2/3.5/2 | 0.000 / 1.412 / 1.247 N m | 105.8% |
| 5.200 kg | two_dynamic_1p5 | proximal-femur-mounted, 2/2/2 | 0.000 / 1.214 / 1.247 N m | 93.4% |

A bare 55 g motor at 40 mm adds at most about 0.022 N m gravity moment about the hip. It also adds approximately 0.000088 kg m2 point-mass inertia, before its own rotational inertia and mount. These costs need comparison with the deleted transmission shafts, supports and frame. A motor at the distal knee would cost considerably more in swing inertia, and is not the same alternative.

The relative-knee row is an ideal kinematic case grounded in a possible motor mounting frame. It does not establish that the servo, output support, reduction and belt fit the femur. Shaft support and belt tension remain necessary, even if the large opposing trunnion arrangement is removed. The body shell, knee pulley size, electrical routing and all moving clearances must be redesigned together.

No gait, thermal duty or stair success is inferred from these nominal-pose torque numbers. The existing simulations remain attached to the carriage-mounted architecture. A new URDF and mass distribution are required before using the alternative as the robot design.

Reproduce with `python architecture_trade_study.py` in an environment with NumPy. The source uses the existing analytically reviewed Jacobian and virtual-work transform.
