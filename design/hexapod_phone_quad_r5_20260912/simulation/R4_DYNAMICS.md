# R4 inward-knee dynamics

R4 uses the corrected C018 case geometry and inward knee-case arrangement. Its mass, inertia and source audits must bind to the frozen R4 export. R3 reports and recordings remain historical results for their own geometry.

The test matrix preserves the previous controller, 0.588 N·m effort cap and contact gates. The loaded starting pose is hip 30°, knee 81°, with a 10 mm COM shift, 22 mm stride and 15 mm commanded foot lift. The CAD rest pose remains 30°/75°. The operating yaw range is ±22°.

Each run contains 64 simulated seconds: standing, one phone rotation and one crawl cycle. The robot has a free base. A pass requires actual swing-foot clearance and loss of contact, the other three feet supporting it, positive support margin, bounded stance error and forward movement. Printed strength, actual backlash, controller calibration and hardware walking remain separate unvalidated properties.

Run from this directory with Python 3.12. The requirements match the tested NumPy and PyBullet versions:

```text
python -m pip install -r requirements.txt
python -m unittest -v test_kinematics.py test_control_uncertainty.py
```

After the R4 manifests are frozen, reproduce the five cases with:

```text
python run_simulation_r4.py --manifest ../cad/output/assembly_manifest_as_printed.json --output output_r4_printed_nominal --hip 30 --knee 81 --shift 10 --stride 22 --lift 15
python run_simulation_r4.py --manifest ../cad/output/assembly_manifest_as_printed.json --output output_r4_printed_half_stiffness --hip 30 --knee 81 --shift 10 --stride 22 --lift 15 --torque-gain-scale 0.5
python run_simulation_r4.py --manifest ../cad/output/assembly_manifest_as_printed.json --output output_r4_printed_feedback_05 --hip 30 --knee 81 --shift 10 --stride 22 --lift 15 --torque-gain-scale 0.5 --feedback-deadband-deg 0.5
python run_simulation_r4.py --manifest ../cad/output/assembly_manifest_as_printed.json --output output_r4_printed_feedback_10 --hip 30 --knee 81 --shift 10 --stride 22 --lift 15 --torque-gain-scale 0.5 --feedback-deadband-deg 1.0
python run_simulation_r4.py --manifest ../cad/output/assembly_manifest.json --output output_r4_solid_nominal --hip 30 --knee 81 --shift 10 --stride 22 --lift 15
```

Half stiffness means half the proportional control gains, with the same derivative setting. The 0.5° and 1° values are feedback-dead-zone half widths. Gravity compensation remains active. These are uncertainty proxies with rigid links; they do not simulate mechanical backlash flanks, printed material anisotropy, creep or fracture. The 1 rad/s limit applies to commanded motion, not a hard bound on backdriven velocity.

The part-only extrusion model excludes support and adhesion material. The full-solid model is a separate conservative mass comparison. Both use the hardware and wire scenarios explicitly declared in their manifests; the simulator does not add another allowance.

The frozen R4 comparison is in `output_r4_comparison/case_comparison.json` with a text companion. All cases completed 64 simulated seconds with unchanged input hashes.

| Case | Model mass | Forward advance | Bounded result |
|---|---:|---:|---|
| Printed nominal | 2.748544 kg | 22.238 mm | Pass |
| Half position stiffness | 2.748544 kg | 22.813 mm | Pass |
| Half stiffness, 0.5° feedback half width | 2.748544 kg | 24.400 mm | Pass |
| Half stiffness, 1° feedback half width | 2.748544 kg | -1.636 mm | Walking failed |
| Full-solid nominal | 2.911449 kg | 24.292 mm | Pass |

The nominal run's maximum sampled stance error was 2.496 mm, minimum mid-swing support margin 6.711 mm and maximum sampled roll or pitch 0.038°. Its largest quasi-static load was 0.548382 N·m. The full-solid case reached 0.580414 N·m. All cases retained the 0.588 N·m cap; no higher-torque experiment was used.

The 1° feedback-half-width case could stand and rotate the phone, but failed the stepping and stance-error gates. Preserve this result as a sensitivity limitation. It is not a measured physical backlash threshold. The inward arrangement does not establish reliable hardware walking or safe printed strength.

Independent checks passed for 2,205 deposition-source assertions, 873 printed-assembly assertions and 320 full-solid mass/frame assertions. The calculated printed mass includes 1.047638 kg of model PLA, 0.390991 kg of high-scenario fasteners and a 0.150 kg wiring allowance. These remain estimates rather than weighed hardware.

Render the saved measured poses after the R4 nominal run without stepping dynamics again:

```text
python render_simulation.py --output output_r4_printed_nominal
python render_recorded_motion.py --output output_r4_printed_nominal
```

The video command additionally requires FFmpeg on PATH. It uses exact recorded poses, sampled at 4 Hz and played at 24 fps, giving approximately 10.67 seconds at 6× speed for a complete test. No new robot poses are synthesized.
