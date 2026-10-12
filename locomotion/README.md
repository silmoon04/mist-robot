# MIST locomotion workspace

This package builds an R7 single-leg test model and a floating quadruped, runs CPU PyBullet simulation, and prepares PPO/SAC residual-policy training. Work was paused on 12 October 2026 for transfer to the MSI laptop. Read [DIRECTIONS.md](DIRECTIONS.md) and [the saved state](handoff/PAUSED_STATE.json) before continuing. Both algorithms have 51,200-step checkpoints; final validation was interrupted. Hardware walking and policy transfer remain unvalidated.

## Start the simulation

Run these commands from the `mist-robot` repository root. Python 3.11 is the supported setup target.

```sh
bash locomotion/scripts/setup_cpu.sh
export MIST_PYTHON="$PWD/.venv-locomotion/bin/python"
bash locomotion/scripts/start_sim.sh
```

Open <http://127.0.0.1:8131>. The server binds to loopback and uses software-rendered CAD visuals, so a desktop OpenGL window is unnecessary. The browser can reset terrain and phone payload, send bounded crawl commands, and preview IK. Command expiry stops commanded travel; simulation falls stop the episode. This remote sends no physical motor commands.

`start_sim.sh` accepts `--port 8132` and uses `MIST_PYTHON` if set, then the repository's `.venv-locomotion`. The development fallback under `work/py311` is outside the portable package; use setup or an explicit interpreter after extraction. Stop the server with Ctrl+C.

The default controller is an IK crawl with estimated support/gravity compensation and bounded residual actions. Select a sensor mode and, for PPO/SAC, enter the checkpoint path. The remote verifies the checkpoint, source/CAD envelope, observation contract and resolved sensor profile before loading. Smoke policies remain unqualified.

## Check the model before learning

```sh
"$MIST_PYTHON" locomotion/model.py
"$MIST_PYTHON" locomotion/design_profile.py audit
"$MIST_PYTHON" -m pytest locomotion/tests -q
"$MIST_PYTHON" -m unittest locomotion.hardware.test_bridge locomotion.hardware.test_sensors -q
"$MIST_PYTHON" locomotion/leg_check.py --output locomotion/runs/leg_check.json
"$MIST_PYTHON" locomotion/evaluate.py --nominal --steps 640 --seeds 1 \
  --terrains flat --output locomotion/runs/current_baseline.json
```

`model.py` regenerates `models/single_leg.urdf`, `models/quadruped.urdf` and `models/model_report.json`. The test leg has a fixed base; the quadruped has a free base. The report records source hashes, mass, inertia, centres of mass and assembly assumptions. The single-leg check examines unloaded and downward toe-load tracking. The evaluation command above screens the current baseline controller across cardinal commands and stop with phone present and absent. It is a fresh diagnostic, not learned-policy qualification.

Physics runs at 1000 Hz with 50 Hz commands. Earlier 240 Hz artifacts were rejected for explicit-PD damping instability. The six-second single-leg tracking comparison at 1000 and 2000 Hz supports that test's timestep convergence; it does not establish electrical or contact fidelity. See [RESEARCH.md](RESEARCH.md).

The test suite covers model transforms/FK, seeded Gym reset and observations, servo bounds, feedforward support, sensor timing, remote behavior and design-profile checks. Infinite observation-space bounds produce Gym warnings. Passing these software checks does not measure printed clearances, loaded torque or hardware reliability.

## Geometry and source files

The working leg is the serial direct-drive R7 yaw/hip/knee chain, 82/90/105 mm. Body axes are +X forward, +Y left and +Z up. Leg +X points outward, yaw rotates about +Z, and hip/knee about +Y. Positive pitch lowers the toe. The 12-joint order is FL, FR, RL, RR, each yaw, hip, knee. Neutral is `[0, 30, 81]` degrees; source limits are yaw -55..55, hip -30..65 and knee 5..115 degrees.

Keep the complete repository tree when copying or archiving. The generated URDF mesh paths are relative, but `locomotion/` alone is insufficient. Required geometry comes from:

- `design/single_leg_r7_wide_joints_20260914/output/Single_Leg_R7.urdf`, its manifest and referenced STL files, including the bench fixture used for mass subtraction.
- `design/main_hub_20260915/output/Main_Hub_4Leg.stl` and the hub source report.
- The source inventory, mass budget and R5 phone pose named in `config.json`, for provenance and review.

The hub was designed against `print_dfm_20260914` legs. The R7 URDF does not include all subsequent DFM changes. The R5 phone assembly is represented as payload assumptions and has not been validated on this hub. Visual meshes with primitive link collisions do not demonstrate assembly clearance, fastener access, cable travel or structural strength. Older `bench/leg_calibration.json` describes a 32/110/70 mm four-bar mechanism; its tick mappings and equations cannot calibrate R7.

The pinned [design profile](profiles/README.md) audits this source family and provides a [measurement template](profiles/r7_measurements.template.json). Profile loading does not switch the simulated robot. A different design requires exporter, mounts, inertials, collisions, gait and actuator changes, fresh tests and new training.

## Estimated servos, payload and sensors

The recorded C018 is the 12 V STS3215 variant. Configuration uses 2.942 Nm stall, 0.981 Nm rated torque and 4.717 rad/s no-load speed as specification-based values. The selected command cap is 0.588 Nm and command slew is 1.8 rad/s. The R7 source URDF's 0.8 Nm and 0.5 rad/s are separate old analysis bounds. Neither specification values nor these selected bounds establish sustained torque on the owned hardware.

The servo approximation includes bounded PD, torque-speed saturation, latency, command quantization, slew, deadband, friction, voltage scaling and an estimated thermal proxy. Loaded response, backlash, latency and temperature behavior need bench identification. Masses also need measurement: the hub is a solid-PLA estimate, electronics/harness is a 540 g allowance, and the removable phone is 155 g. Phone frame, pan servo and horn remain when the phone is removed.

`MistEnv(sensor_mode="mpu6050")` is the default. The simulated MPU profile samples at 50 Hz with 5 ms transport delay; `phone` uses 10 Hz and 60 ms and requires a present phone. These are assumptions. Both expose delayed/noisy gravity direction and angular rate rather than current simulator orientation. `none` is an explicit open-loop sensor mode; it does not provide a working physical balance observation. Simulation profiles omit raw accelerometer transients and estimator drift. Perfect world pose, velocity and contacts are available for scoring, not supplied as actor inputs.

The owned MPU6050 can serve a fixed chassis sensor with the phone absent. Native SensorServer on the Mi 9 SE can supply phone sensing. Mount rotation, bias, clock/transport timing and pan state need measurement. See [hardware/README.md](hardware/README.md) for wiring, optional MPU firmware, source selection and sensor-only monitors. Its examples do not enable learned-policy motor execution. The shipped hardware calibration profile refuses arming until a measured R7 profile is supplied.

## Learning and queued jobs

Use the interpreter installed above. Both direct `locomotion/train.py` execution and `python -m locomotion.train` resolve their environment module, including spawned workers.

```sh
# Explicit output matches the simulation remote's development checkpoint paths.
MIST_PYTHON="$MIST_PYTHON" bash locomotion/scripts/train_smoke.sh locomotion/runs/smoke

# Inspect a queued command without launching training.
"$MIST_PYTHON" locomotion/scripts/run_job.py --job ppo-seed42 --print-command

# Launch one prepared job on the current machine.
MIST_PYTHON="$MIST_PYTHON" bash locomotion/scripts/run_training.sh ppo-seed42
```

Without an output argument, `train_smoke.sh` creates a timestamped `runs/smoke-*` directory. Smoke runs use 2048 requested steps per algorithm. The six queue jobs pair PPO and SAC at seeds 42, 100042 and 200042, with 1,001,472 transitions each. Worker overrides must preserve divisibility by `ppo_n_steps * n_envs` for both algorithms. The queue reserves no provider and starts only when invoked. The shared provenance envelope includes controller, sensors, configuration, source CAD and meshes, lock, training settings and validation identity; edits invalidate old checkpoints.

The action is a 12-value bounded residual around the crawl, limited to +/-0.10 rad. Observations include sensor gravity/gyro, joint positions/velocities, command, previous action and gait phase. Full jobs randomize masses/inertias, COM, phone presence/offset, friction, voltage, torque, gains, latency, deadband and observation noise. Terrain resets mix flat, low friction, gentle slopes and millimetre roughness. These ranges are synthetic training assumptions, not calibrated uncertainty or a claim about carpet, sand or gravel.

Training saves periodic, best-validation and final checkpoints, summaries, versions and source hashes. SAC saves replay buffers. PPO may exceed the requested budget to finish a rollout; compare actual timesteps. Resume adds steps and can restore SAC replay data, but reseeds environments rather than restoring complete live/RNG state. Fixed validation seeds select checkpoints. Final testing needs untouched seeds, all cardinal commands, all terrains and both payload configurations, with fall fraction, commanded-velocity error, drift, saturation and tracking error reported.

```sh
"$MIST_PYTHON" locomotion/evaluate.py --policy path/to/final.zip --algo ppo \
  --output locomotion/runs/held_out_evaluation.json
"$MIST_PYTHON" locomotion/scripts/benchmark.py --steps 2000 --warmup 100 \
  --workers 1 2 4 --output locomotion/runs/cpu_probe.json
```

`--require-pass` makes evaluation return failure if its screening criteria fail. Short rollout throughput excludes optimizer, evaluation and checkpoint costs. Do not extrapolate it into sustained training time without a bounded end-to-end trial.

## CPU dependencies and later hardware

`setup_cpu.sh` creates a Python 3.11 CPU environment, installs Torch 2.8.0+cpu from the official CPU index, and consumes the complete `requirements.lock.txt`, including websocket-client and the independent MuJoCo CPU comparison dependencies. Keep CUDA experiments in a separate environment with a CUDA-enabled Torch build; do not install this CPU lock there.

CUDA requires a separate compatible PyTorch build and a working NVIDIA driver. `--device cuda` fails if unavailable and accelerates policy optimization only; PyBullet physics stays on CPU. Keep the CPU environment intact when testing alternatives. [UPGRADE.md](UPGRADE.md) and `machine_profiles.json` describe advisory worker probes and future laptop/GPU options. Profiles are not read automatically by the trainer, and proposed hardware/backend throughput has not been measured. MuJoCo/MJX, Genesis and Isaac require separate model ports and validation.

## Evidence status

`runs/nominal_correct_frame.json` and `runs/nominal_converged.json` are older baseline-controller diagnostics, not results for the final controller/sensor integration. `runs/diagnostics/` retains explicitly labeled comparisons, including timestep convergence and pre-integration scheduled feedforward. Bad-frame and unstable-timestep prototype training evidence was retired outside the distributable package under development `work/`. No checkpoint from those runs should be presented as a current policy.

New measured training results should be added only after the final source freeze, with matching hashes and retained evaluation outputs. See the files under `reviews/` for integration findings and the implementation review record. Real walking still requires dimensions, masses, joint calibration, actuator response, sensor timing and supported hardware stance/load tests.

## Sensitivity screening

`sensitivity.py` and `validation_cases.json` prepare 239 deterministic development cases covering terrain, directions/stop, phone presence, MPU/phone/open-loop sensing and held-out mass, COM and motor corners. Strict checks require no fall or forbidden non-toe ground contact, at least 50% commanded progress, and bounded sideways drift, yaw, tilt and stop displacement. This is simulation screening, not measured hardware capability.

These commands run from the repository root:

```sh
"$MIST_PYTHON" locomotion/sensitivity.py --output locomotion/runs/sensitivity_plan.json
"$MIST_PYTHON" locomotion/sensitivity.py --run --steps 960 \
  --output locomotion/runs/current_sensitivity.json
```

Use `--case-id` to restrict cases and `--checkpoint path/to/final.zip --algo ppo` for a selected policy. The full matrix remains pending after the source freeze. Tiny step budgets are execution probes and cannot establish sustained acceptance. See [the sensitivity follow-up review](reviews/sol10_integration.md) for current integration issues.

The acceptance contract is `simulation-walking-v2`: at least 19.2 seconds and complete execution, no fall or loaded body/nonfoot contact above 0.1 N, bounded path/yaw/tracking error and saturation, and no sensor fault. It includes stop, both yaw directions, combined and transient commands. Training ranks reward only among eligible candidates; short smoke evaluations cannot qualify. Recurring validation owns seed base 1,000,000. `evaluate.py` owns the final test base 2,000,000; its results must not be fed back into selection. Sensitivity is a development suite, not the untouched final test.

`--sensor-mode mpu6050|phone|none` and `--sensor-profile '<JSON>'` apply to training, validation, evaluation and benchmarking. Phone mode requires positive payload in every case. Startup has zero unavailable vectors; sensor age uses measurement timestamps. Fresh samples are held only up to the configured maximum age. Missing/stale simulation sensing latches an episode stop until reset. Hardware estimator recovery restores observations only, never arm state. A phone source reboot requires deliberate `PhoneIMU.reset()`; moving pan is unsupported until mount and sensor timestamps can be aligned. The synthetic gravity estimator remains an approximation.

Resume and transfer require a new output directory. Resume verifies the same experiment and matching SAC replay, then uses the checkpoint's recorded fresh continuation seed. It does not restore uninterrupted environment/RNG state. `--transfer --resume ...` starts new ranking history and empty SAC replay from a compatible source/observation contract; source or sensor changes require retraining. Checkpoint sidecars bind checkpoint/replay hashes and retain their envelope. Final-test and remote loads enforce the same verifier.

## Portable archive

`locomotion/scripts/package_simulation.py` audits the package without creating a ZIP:

```sh
"$MIST_PYTHON" locomotion/scripts/package_simulation.py
```

It includes the locomotion tree, current checkpoint/provenance/evidence files, every repository-relative dependency returned by `provenance.source_hashes()`, and STEP/F3D exports from the R7 leg and hub output trees. Caches, `.pio`, Git data, virtual environments, `work` and `retired` directories are excluded. The archive has one `mist-robot/` root with a content-hash manifest. No simulation environment is bundled; run `setup_cpu.sh` after extraction.

Create the final archive only after training, evaluation and documentation are complete and no output files are changing. From the repository root, the final packaging command is:

```sh
"$MIST_PYTHON" locomotion/scripts/package_simulation.py --create \
  --output ../mist-simulation.zip
"$MIST_PYTHON" locomotion/scripts/package_simulation.py \
  --validate ../mist-simulation.zip --relocate
```

Creation refuses to overwrite an archive and rejects output inside the repository. Validation checks members and hashes before extracting to a temporary directory, verifies relocated required-source hashes, then resets and steps a nominal robot with the chosen interpreter. This final relocation check is pending until the archive is created. It does not rerun training or certify physical behavior.
