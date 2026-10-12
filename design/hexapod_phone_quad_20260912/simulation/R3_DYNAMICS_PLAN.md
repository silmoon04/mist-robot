# R3 manufacturing and dynamics checks

R2 results stay in `output` as a historical baseline. The R2 mass model used the earlier fastener allowance. The corrected hardware count and revised printed geometry require new R3 results before carrying forward a walking conclusion.

Use `run_simulation_r3.py` with an explicit manufacturing manifest and a separate output directory. `--manifest` is mandatory, and the file must contain `mass_model.kind` metadata. The runner reads each link's complete mass, center of mass and inertia tensor. It does not independently add fasteners, wiring or an infill percentage. The manifest producer must replace the old allowance once, distribute the actual fastener estimate by link and retain the separately declared wire allowance.

Run the measured-toolpath mass model first when available. Its PLA properties must come from part-only extrusion, excluding skirt, support and other material removed after printing. Keep the full-solid CAD case separate as a conservative mass comparison. Neither model is a weighing result.

The rigid-body test retains the existing contact and motion gates. A body moving forward is insufficient: each foot must lift, lose contact while the other three feet support the robot, preserve support margin and keep stance-position error bounded. Use the 0.588 N·m primary torque cap. A separately named 0.8 N·m experiment remains below the published rated load but exceeds the sustained screen and cannot receive the primary pass status.

The following uncertainty cases are available without changing geometry or pass gates:

| Case | Position gain scale | Derivative gain scale | Feedback dead-zone half width |
|---|---:|---:|---:|
| Nominal assumed controller | 1.0 | 0.1 | 0° |
| Half effective position stiffness | 0.5 | 0.1 | 0° |
| Half stiffness with feedback uncertainty | 0.5 | 0.1 | 0.5° |
| Twice the feedback uncertainty | 0.5 | 0.1 | 1.0° |

The gain scales multiply the same base gains used in R2. The 0.1 derivative scale is the R2 numerical setting. A 0.5 position scale halves the effective rotational control stiffness. The dead-zone half width means feedback correction begins outside that angle; the full width is twice the value. Gravity feedforward remains active.

These cases are uncertainty proxies. All links remain rigid. They do not model printed anisotropic elasticity, separate motor/output shafts, mechanical backlash flank contact, creep, stress, fatigue, fracture or loss of a bolted joint. Printed material strength and joint retention require their own load tests or a suitably characterized structural model. A dynamics pass cannot qualify them.

The runner also records sampled world-coordinate foot forces. These can describe the tested motion's loading for later fixture work, but do not qualify impacts or material strength. A 1 rad/s limit applies to commanded angle changes; actual joint velocity can exceed it under backdriving and is separately reported. Source files, URDF, settings, mesh and manifest hashes must remain unchanged for a run to receive a pass.

Run from the `simulation` directory with Python 3.12. The dependency pins match the tested Python 3.12.7 environment. Use a virtual environment if desired, then install the requirements:

```text
python -m pip install -r requirements.txt
```

The final R3 runs use a 30° hip / 81° knee starting posture, 10 mm COM shift, 22 mm stride and 15 mm foot lift. This is a loaded test pose; the CAD assembly's rest pose remains 30°/75°. Reproduce each frozen case with:

```text
python run_simulation_r3.py --manifest ../cad/output/assembly_manifest_as_printed.json --output output_r3_printed_nominal --hip 30 --knee 81 --shift 10 --stride 22 --lift 15
python run_simulation_r3.py --manifest ../cad/output/assembly_manifest_as_printed.json --output output_r3_printed_half_stiffness --hip 30 --knee 81 --shift 10 --stride 22 --lift 15 --torque-gain-scale 0.5
python run_simulation_r3.py --manifest ../cad/output/assembly_manifest_as_printed.json --output output_r3_printed_feedback_05 --hip 30 --knee 81 --shift 10 --stride 22 --lift 15 --torque-gain-scale 0.5 --feedback-deadband-deg 0.5
python run_simulation_r3.py --manifest ../cad/output/assembly_manifest_as_printed.json --output output_r3_printed_feedback_10 --hip 30 --knee 81 --shift 10 --stride 22 --lift 15 --torque-gain-scale 0.5 --feedback-deadband-deg 1.0
python run_simulation_r3.py --manifest ../cad/output/assembly_manifest.json --output output_r3_solid_nominal --hip 30 --knee 81 --shift 10 --stride 22 --lift 15
```

The printed nominal, half-stiffness, 0.5° feedback-dead-zone and full-solid cases passed their bounded tests. The half-stiffness case with a 1° feedback half width failed walking: the feet did not complete the required steps, stance error grew and net advance was approximately zero. Standing and phone rotation still passed. Preserve that failure as the observed control-sensitivity result. It is not a measured mechanical-backlash threshold.

All cases retain the 0.588 N·m cap and unchanged physical-contact gates. No 0.8 N·m experiment was needed. The full-solid case is a separate conservative mass scenario. The former 30 mm outward-toe buffer is not a hardware specification; final geometry checks govern clearance.

`output_r3_comparison/case_comparison.json` and its text companion collect the exact case outcomes and report hashes. Render a saved measured pose without changing its simulation report using:

```text
python render_simulation.py --output output_r3_printed_nominal
```
