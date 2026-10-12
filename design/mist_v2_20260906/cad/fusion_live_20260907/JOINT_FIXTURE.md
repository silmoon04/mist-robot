# Small native joint fixture

**Native result: passed.** The root agent's run at `joint_fixture_runs/20260907T110854554885Z/` created 17 components and 16 native revolutes, passed all probes and 96 world checks, exported the test F3D, and reactivated the existing body with an unchanged fingerprint. See `../fusion_motion_20260907/NATIVE_VERIFICATION.md` for the exact scope.

The root agent owns the live Fusion connection and can run `joint_fixture.py`'s `run(None)` entry point. This sub-agent has not called the live connection.

The script requires the existing document named **MIST concealed wheel drive - native assembly**. It creates a separate document named **MIST JOINT FIXTURE TEST ONLY …**, containing one chassis and four components per leg. These simple bars and blocks are test geometry, not the printable robot.

The 17-component fixture uses the actual `native_parts.place_occurrence` and `motion.apply_motion_plan` implementations. It checks placement after Compute All before creating the 16 joints. The helper uses standard joint Z from parent-owned sketch-plane normals, measures direction with a 0.1° drive, maps limits from the built physical angles, and verifies restoration. Driven poses are measured after doEvents/viewport refresh; Compute All occurs only after restoring their original values because the live diagnostic showed that it resets transient drives.

After all joints exist, the script drives the front-left yaw, hip and knee by +5°, +4° and -3°. It compares component transforms and joint world origins against independent kinematics, including the downstream wheel. It restores the original coordinates and checks all four legs again. An F3D archive is exported only after these checks succeed.

The body document is reactivated in `finally`, on success or failure. Its timeline count, occurrence transforms and body count are compared before and after. The test document remains open for inspection. Failures are recorded rather than hidden, and partial joint details remain in the helper report.

Reports are saved under `joint_fixture_runs/<UTC timestamp>/`. `last_joint_fixture.json` identifies the latest run. Reports are written after placement, after each helper joint and on exit, so a failure can be diagnosed without rerunning a full assembly.

The offline preparation check separately confirms 17 parts, 16 joint records and a maximum joint-datum discrepancy of 5.55e-17 m against `simulation/model.py`. The native result comes from the actual report above. This small fixture has one root-level component per link, so it does not exercise nested occurrence hierarchies, multi-part rigid groups or internal rotor attachments. It makes no full-range, collision, manufacturing or physical-strength claim.
