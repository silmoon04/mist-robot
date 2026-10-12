# CAD inertial reconciliation and checks

The complete 657-part candidate accounts for 7.108160 kg, including 450 g supplemental electronics, harness and hardware once. This is based on solid-print volumes, manufacturer motor/phone/battery values and simplified hardware envelopes; it is not a scale or slicer measurement.

`parameters_cad_inertials.json` replaces all 17 URDF link inertials with the exported CAD mass, COM and full COM inertia tensors. Internal transmission rotors remain lumped into their hosting links. Collision shapes remain simple primitive links. The older scalar allowances in the parameter file are retained for compatibility only; `link_mass_properties` is authoritative for this run.

Standing and rolling pass the recorded model criteria. Rolling advances 5.063 m in 8 seconds. The supported 23.244 N single-leg fixture gives 6.59 mm foot error, with hip/knee RMS 0.5296/0.727899 N m. The knee is only 0.000245 N m below the assumed 0.728144 limit. That nominal pass provides no useful engineering headroom given the unmeasured motor, thermal, material and mass assumptions.

The separate matched gait study reports a failed 80 mm/3-second setting and a slower 60 mm/4-second case that passes aggregate criteria while retaining transient support loss. See `../proximal_gait_20260907/MATCHED_CAD_REPORT.md`. No dynamic stair success, full CAD collision sweep or physical print/load release follows from these results.

The report hash, source path and limitations are in `reconciliation.json`. `validation_summary.json` records the bounded stance/rolling/fixture evaluation. `runtime_snapshot` preserves the exact source bytes, and each case has its own parameter snapshot and trajectory.

Reproduce from `simulation` with `.venv/Scripts/python.exe run_proximal_cad_validation.py`. The integration source is `reconcile_proximal_cad.py`; it rejects a partial leg inventory or invalid inertia tensors rather than silently filling missing links.
