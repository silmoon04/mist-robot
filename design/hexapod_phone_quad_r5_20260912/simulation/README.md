# R5 quadruped dynamics checks

This is the R5 simulation workspace. It uses NumPy and PyBullet; dependency pins are in `requirements.txt`. Final results, frame checks and commands are documented in `R5_DYNAMICS.md`. The nominal, half-stiffness and full-solid tests pass; both feedback-dead-zone walking tests fail. Copied older scripts and notes are reference material. The R4 baseline remains in its separate design directory.

`export_urdf.py` uses the selected R5 assembly manifest. The toolpath model is `cad/output/assembly_manifest_as_printed.json`; the separate full-solid comparison is `cad/output/assembly_manifest.json`. Each rigid link needs a mass in kg, a COM in mm, a full inertia tensor about that COM in kg m², and an STL in the link's local frame. Missing meshes, incomplete links, implausible inertia tensors and inconsistent physical frames stop export. In particular, the configured coxa length must agree with the hip origin declared by CAD. The URDF references meshes by relative path, so preserve the directory structure when copying the package.

`kinematics.py` reads the common settings file. It uses X forward, Y left and Z up. Three servo joints drive each leg directly. Positive hip and knee angles rotate the leg downward. The phone has a separate continuous yaw joint, operated with WiFi and its internal battery. The phone is in landscape orientation, with its screen plane vertical. Its collision box comes from the actual bare-phone envelope in the CAD manifest. Disconnect USB before rotation.

`statics.py` computes the whole assembly COM from every link, shifts the torso to place that COM inside the support triangle, solves vertical ground reactions and includes descendant-link gravity in each joint torque. It refuses unreachable poses or a COM correction that does not converge. This is a level-ground quasi-static load calculation, with no acceleration or cable load.

`run_simulation_r5.py` exports the URDF, runs a free base with gravity and floor contact, holds a stance, sweeps the phone through one full turn and attempts one slow crawl cycle. It uses no base constraint. Stance feet have fixed world targets while the body shifts and the swing foot advances. A pass requires real swing-foot clearance, loss of swing-foot contact, three supporting feet, positive support margin, bounded stance error and forward body displacement. Shank contact cannot count as toe support. The tested pose is hip 30°, knee 81°, with a 22 mm stride, 10 mm COM shift and 15 mm lift. Final coxa length is 70 mm and operating yaw is ±19°.

The nominal controller represents finite servo stiffness and damping plus gravity compensation. Its proportional gains for yaw, hip, knee and phone are 3, 8, 6 and 0.8 N·m/rad. Derivative gains are 0.025, 0.04, 0.015 and 0.003 N·m·s/rad. Torque is capped at 0.588 N·m, and commanded joint travel is limited to 1 rad/s. Backdriving can exceed the commanded rate. These are simulation assumptions requiring hardware calibration. The simulator sends no commands to physical servos. R5 also tests half position stiffness and feedback dead-zone sensitivity; these proxies do not model anisotropic material or mechanical backlash.

This PD and gravity-compensation model is not a bench-calibrated model of the STS3215 internal firmware. Mapping its torques and position targets to real servo commands remains unvalidated. No controller has been deployed to the robot. Treat this as a CAD and URDF physics candidate, followed by coupon measurements, physical load checks and servo-control calibration.

The baseline torque cap is 0.588 N·m, derived from the manufacturer's one-fifth-stall cyclic test condition. A separately requested 0.8 N·m experiment remains below the 0.981 N·m rated load but exceeds that sustained screen. It receives a distinct experimental status. Neither torque value establishes safe continuous temperature in this robot.

Run from this directory with Python 3.12:

```text
python -m pip install -r requirements.txt
python -m unittest -v test_kinematics.py test_control_uncertainty.py test_frame_contract_r5.py
python run_simulation_r5.py --manifest ../cad/output/assembly_manifest_as_printed.json --output output_r5_printed_nominal --hip 30 --knee 81 --shift 10 --stride 22 --lift 15
```

The report records settings, URDF, source and manifest hashes, masses, contact metrics, joint loads and limitations. Changing the manifest, settings or CAD meshes during a run invalidates that run. The trajectory contains measured simulation poses, rather than a prescribed animation. The screenshot is a visual aid. Read the report's gate results before using either as evidence.

Dynamics and the torque cap run at 240 Hz. Reported trajectory, contact and torque metrics are sampled at 20 Hz, so peak values refer to those samples. `render_simulation.py` reconstructs the final measured pose for the preview without changing the physics report.

CAD visuals are retained, with mass properties supplied by the selected model. Floor contact uses simple collision boxes and 14 mm wide rocker cylinders with a 5 mm radius. The CAD foot's small neutral flat changes contact depth by at most 0.2 mm. These proxies do not replace the separate CAD interference checks. Friction, motor gains, backlash, bus timing, thermal behavior, flexible parts, printed strength and real wiring are unmeasured. A bounded simulation pass cannot certify fit, printing quality or hardware walking.
