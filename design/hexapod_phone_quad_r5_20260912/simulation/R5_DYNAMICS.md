# R5 inward hip and straight tibia dynamics

This directory belongs to the new R5 design. Its tests must use the R5 geometry and mass manifests. Earlier R4 results remain in the separate R4 design directory and do not establish an R5 pass.

The hip case faces inward, and the lower leg uses a straight knee-to-toe beam. Final coxa length is **70 mm**, read from `settings.json`. Femur and tibia lengths remain 90 and 105 mm. The operating yaw limit is **±19°**, selected after the fixed-saddle clearance review. The toe center stays at local `(105, 0, 0)` mm with the existing 5 mm radius, 14 mm wide rocker contact. Its small printed flat is approximated within 0.2 mm.

The same configured coxa length drives forward and inverse kinematics, the hip joint origin, gravity-load frames and the coxa collision box. The URDF exporter checks every declared parent, origin, axis, rotation and joint limit against this contract. Regression tests cover both 50 and 70 mm lengths and reject a stale 50 mm hip origin under a 70 mm configuration.

The final R5 matrix is bound to the frozen ±19° manifests. Automated validation supplied `--expected-manifest-sha256` from the release cue, preventing an outdated file from entering the run. The tested loaded posture is 30° hip / 81° knee, with 10 mm COM shift, 22 mm stride and 15 mm lift. CAD assembly neutral is separately 30°/75°.

Run from this directory with Python 3.12:

```text
python -m pip install -r requirements.txt
python -m unittest -v test_kinematics.py test_control_uncertainty.py test_frame_contract_r5.py
```

After the R5 mass cue, reproduce the bounded cases with:

```text
python run_simulation_r5.py --manifest ../cad/output/assembly_manifest_as_printed.json --output output_r5_printed_nominal --hip 30 --knee 81 --shift 10 --stride 22 --lift 15
python run_simulation_r5.py --manifest ../cad/output/assembly_manifest_as_printed.json --output output_r5_printed_half_stiffness --hip 30 --knee 81 --shift 10 --stride 22 --lift 15 --torque-gain-scale 0.5
python run_simulation_r5.py --manifest ../cad/output/assembly_manifest_as_printed.json --output output_r5_printed_feedback_05 --hip 30 --knee 81 --shift 10 --stride 22 --lift 15 --torque-gain-scale 0.5 --feedback-deadband-deg 0.5
python run_simulation_r5.py --manifest ../cad/output/assembly_manifest_as_printed.json --output output_r5_printed_feedback_10 --hip 30 --knee 81 --shift 10 --stride 22 --lift 15 --torque-gain-scale 0.5 --feedback-deadband-deg 1.0
python run_simulation_r5.py --manifest ../cad/output/assembly_manifest.json --output output_r5_solid_nominal --hip 30 --knee 81 --shift 10 --stride 22 --lift 15
```

Each run keeps the 0.588 N·m cap, a free base and the prior contact gates. A pass requires actual swing-foot clearance and contact loss, three supporting feet, positive COM support margin, bounded stance error and forward movement. No base constraint is used. The complete test contains standing, one phone turn and one slow crawl cycle.

The half-stiffness and feedback-dead-zone cases are control uncertainty proxies. Gravity compensation remains active, and all links remain rigid. They do not measure or simulate printed anisotropy, mechanical backlash flanks, creep, fracture, or screw retention. The command-rate limit is 1 rad/s; actual velocity under backdriving is reported separately. Physical fit, printed strength, controller calibration and hardware walking remain unvalidated.

Use the exact part-only extrusion COMs and tensors in the printed mass model. Support and adhesion material are excluded from the robot. The full-solid model is a separate conservative mass comparison. Hardware and wiring are taken from the selected manifest once, with no additional allowance added by the simulator.

The final R5 comparison is under `output_r5_comparison`. All five cases completed 64 simulated seconds using unchanged input hashes and the same 0.588 N·m cap.

| Case | Model mass | Forward advance | Bounded result |
|---|---:|---:|---|
| Printed nominal | 2.756962 kg | 24.553 mm | Pass |
| Half position stiffness | 2.756962 kg | 22.659 mm | Pass |
| Half stiffness, 0.5° feedback half width | 2.756962 kg | 5.185 mm | Walking failed |
| Half stiffness, 1° feedback half width | 2.756962 kg | -0.617 mm | Walking failed |
| Full-solid nominal | 2.936135 kg | 24.641 mm | Pass |

The nominal run recorded a maximum sampled stance error of **7.212 mm**, minimum mid-swing support margin of **13.153 mm**, maximum sampled roll or pitch of **0.053°**, and largest sampled commanded torque of **0.579291 N·m**. Its quasi-static peak was **0.546521 N·m**; the full-solid model's was **0.580616 N·m**. Dynamics run at 240 Hz; these trajectory and load metrics are sampled at 20 Hz.

Both feedback-dead-zone cases could stand and rotate the phone, but failed foot-stepping and stance-error gates. This sensitivity failure remains part of the result. The dead-zone parameters are not measured physical backlash tolerances. A nominal pass does not establish reliable hardware walking.

Independent final audits passed **2,208 deposition-source checks**, **921 printed-assembly checks**, and **370 full-solid mass/frame checks**. The printed model includes **1.056056 kg** of part-only PLA, **0.390991 kg** of high-scenario fasteners, and **0.150 kg** of wiring allowance. Finished hardware has not been weighed.

The superseded ±22° comparison and five report copies remain in `interim_ce504_yaw22`, marked as historical. They are excluded from the current verdict. R4 baseline files in the separate design directory remain untouched.

Render the final measured poses without changing their physics report:

```text
python render_simulation.py --output output_r5_printed_nominal
python render_recorded_motion.py --output output_r5_printed_nominal
```

Video regeneration also requires FFmpeg. The recorder selects exact saved poses at 2.5 Hz and displays them at 15 fps, giving 6× playback. It does not interpolate robot poses or advance dynamics again.
