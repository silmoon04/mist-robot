# Astra batch critique

Reviewed 12 October 2026 after the ten Sol assignments were launched. This report applies the unslop writing skill. It consolidates the simulation, profiles, hardware/sensors, training and upgrade reviews and independently checks their integration. No core source, firmware configuration or physical device was changed. The sensitivity and README work arrived during the audit; final integration notes below distinguish the first snapshot from those additions.

The current deliverable is an R7 simulation and commissioning foundation. It is not yet a qualified walking policy or a complete sensor-to-actuator deployment. The nominal crawl result is useful evidence of simulated movement, but it does not close the training, remote-control or varied-condition requirements. Keep all physical gait gates closed. Run expensive training only after the source, sensor contract and acceptance suite are frozen.

## Revision order

The next reviser should implement the following in order. P1 items block a meaningful training or commissioning release; P2 items block claiming the affected feature works as configured. These priorities concern software correctness and experiment integrity, not a new estimate of physical risk.

### A1, P1: freeze a complete experiment envelope and verify every checkpoint consumer

`train.py` still hashes only seven local files, silently skips missing files, snapshots after worker creation and accepts arbitrary resumes. The omitted sensor modules, source URDF/manifest/CAD inputs and external profiles can alter the experiment without changing its recorded envelope. Resume imports prior best scores regardless of suite/lineage and SAC accepts a missing replay buffer. `evaluate.py` and `sim_remote.py` also load policies without checking source or observation meaning. A 47-element space alone cannot prove compatibility.

Create one shared provenance module. Require all imported controller/environment inputs, the resolved sensor/config profile, generated-model recipe and source assets, dependency lock, algorithm/effective parameters, observation/action contract and ordered validation suite. Hash before environment allocation and check after setup and around evaluation/checkpoint writes. Bind each checkpoint and SAC replay artifact by content hash to its immutable run and envelope. Reject missing/mismatched provenance on resume, evaluation and remote policy selection. Incompatible transfer must explicitly create a new experiment with fresh ranking history. SAC continuation must require its matching replay; an explicit fresh-replay transfer needs distinct status. Resume must use recorded continuation seeds or restored state and must report that it is not uninterrupted RNG continuation.

Tests should mutate each omitted input, remove a required source, mismatch checkpoint/replay, alter validation cases and attempt a policy load through each entry point. Every incompatible continuation must fail before overwriting run artifacts. An intentional transfer must leave the original run untouched.

### A2, P1: make stop/disarm invalidate earlier arm intent and enforce cumulative slew

The browser sends Arm, Disarm and STOP independently; the host lock serializes arrival, not user intention. A delayed arm can follow a disarm. Page departure sends STOP only when the local `armed` flag is true, so departure while arm is pending does not invalidate that request. Firmware and host also replenish a two-tick allowance on every target packet, allowing a request-frequency-dependent rate above the stated 0.5 rad/s.

Add a server-checked session/intent generation or equivalent invalidation mechanism, serialize browser state transitions, disable duplicate pending arms, and invalidate arm intent on departure regardless of the last observed armed state. Keep emergency stop immediately effective. Replace renewable rounding slack with a cumulative displacement/time budget or continuous limiter with a single quantization allowance. Apply equivalent rules in firmware and host. Test reversed arm/disarm arrival, arm/departure, delayed replies, repeated clear/arm intents and target streams at multiple rates over equal wall time. Rebuild both firmware environments and refresh `hardware/VALIDATION.json` only from actual outputs.

### A3, P1: define one sensor validity and recovery contract before training

The actor and gait share delayed simulated vectors, which is correct. They nevertheless keep driving on indefinitely old data and fabricated startup gravity. Hardware rejects stale readings. The hardware estimator also becomes permanently unusable after a gap over 100 ms because its last timestamp is never reset. These are different control systems under the exact disturbances the user wants explored.

Specify startup, bounded hold, stale stop/fault and deliberate recovery states. Carry measurement and arrival timestamps, source/frame/units, age and validity consistently. Choose the same age semantics in simulation and deployment. An estimator reset may restore observation availability but must not silently re-arm control. Test packet gaps, repeated/out-of-order timestamps, source reboot/wrap and resumed valid samples. Phone gyro/gravity pairing and moving-pan timestamps need explicit alignment; retaining locked pan is acceptable for this release. A simulated gravity estimator remains an approximation and must be labelled as such.

Propagate validated `sensor_mode` and resolved profile through training, validation, final evaluation, benchmark, sensitivity and simulation remote. Phone mode must require a present positive payload in every relevant case. Expose MPU6050, phone and explicit open-loop operation without silent fallback. If validity/age changes actor dimensions, revise the observation contract and reject old checkpoints.

### A4, P2: make configuration changes actually reach the simulation

The Sol03 observations remain current: voltage, gain/deadband ranges and thermal parameters in `config.json` are bypassed by servo literals; restitution is ignored. Also inspect nominal voltage, encoder velocity noise, encoder quantization, roughness range semantics and timing fields so the resolved record describes actual behavior. Reject unsupported settings instead of recording ineffective overrides. Validate finite values, positive physical rates/gains and ordered ranges once, before allocating a simulation.

Use one resolved configuration passed into model export, gait, servo and environment. The pending sensitivity code must use that route, rather than changing module globals or reporting requested overrides that components reload away. Deliberately set nondefault values and verify dynamics/readback or the relevant generated targets; include nonzero restitution and distinct thermal coefficients. Preserve the known 1000 Hz/50 Hz contract and reject nonintegral rate ratios unless deliberately implemented.

### A5, P2: connect profile provenance to the actual model exporter

The profile audit has strong checks, but `model.export_models` does not call it. Matching alternate tibia lengths in config/manifest still bypass the fixed R7 IK/toe geometry. The exporter also checks joint xyz, axis and limits without checking joint-origin rotation or the full topology.

I independently copied the source into a temporary directory, changed `hip/origin` rpy to `0.2 0 0`, retained its assets and called `export_models(config=changed_config)`. Export succeeded with the incompatible rotation. Nothing in the repository source was changed by this probe.

For the current fixed R7 implementation, reject changed lengths, nonzero moving-joint origins, changed topology/transmission and unapproved source hashes before creating output. Prefer invoking the existing pinned profile audit. Do not imply that alternate profile validation instantiates an alternate dynamic robot: it currently supports kinematic auditing only. Test coordinated config/manifest tibia edits and nonzero joint rpy, as well as approved unchanged R7 export. Fix periodic-angle IK handling or restrict supported yaw limits explicitly.

### A6, P2: freeze meaningful simulation acceptance and an untouched test suite

`evaluate.py` accepts any upright stop and very weak projected progress, regardless of drift, velocity error or saturation. The training callback ranks only reward. These can remain smoke diagnostics but cannot be the walking gate. Define an explicit, versioned simulation requirement with duration, fall, translational/yaw tracking, lateral and stop drift, finite metrics and actuator-limit criteria. Thresholds should be visible engineering targets, not retroactively selected to pass current results. Retain rejected candidates as unqualified and rank only eligible candidates.

Add stop, clockwise/counterclockwise rotation and combined-direction/transient commands to the relevant suites; stationary cardinal commands do not exercise remote command changes. Freeze ordered case IDs, per-case seeds and suite hashes. Keep training, recurring validation and final test ranges disjoint. The existing evaluation script can become the final test runner; it already starts at seed 2,000,000, so a second competing evaluator is unnecessary. Protect its suite from checkpoint selection and record final test execution separately. Compare algorithms across all three independent repetitions, not just their best seed.

The parent corrected CAD-origin velocity during this audit using the COM angular cross term and retained `com_velocity` separately. Keep a regression test for that correction. The new sensitivity scorer unwraps yaw increments, but the old evaluator still needs the same treatment. Tests should reject pathological upright but drifting stops and poor tracking, not merely confirm current outputs.

### A7, P2: use real matched budgets and independent repetitions

The six queue jobs request 1,000,000 transitions, but four-worker PPO completes 1,001,472 and SAC completes 1,000,000. Worker seed ranges 42-45, 43-46 and 44-47 overlap across repetitions. Choose disjoint run streams with matching per-run seeds between algorithms, and a common achievable transition budget after worker count is fixed. Record expected and actual transitions, optimizer work and wall time separately. Recompute divisibility after worker overrides. Persist a full seed plan, including continuation streams and suite identity.

Complete the CPU lock, including websocket-client, and make setup consume it. Keep CUDA installation separate from `torch==2.8.0+cpu`; add the Sol05 handoff explanation. Machine presets remain advisory until the actual Ultra 9 laptop is inspected and benchmarked. The 12 GB mobile GPU must not be presented as satisfying the cited 16 GB Isaac floor. No extra GPU backend is needed to release this CPU pipeline, but a backend research plan is not an implemented accelerated trainer.

### A8, P2: make the requested expansion discoverable and accurately bounded

Users need a reproducible route to change payload, terrain, friction, actuator and sensor assumptions, inspect results and launch the same job on another machine. The simulation remote currently exposes terrain/payload/randomization but not sensor choice/profile or verified checkpoint selection. Update its controls and status to show the resolved profile, qualified versus smoke policy state, seed and relevant errors. Add sensitivity cases for heavier/lighter body and phone, COM offsets, low-friction/rough/slope ground, torque/latency and sensor delay/dropout. Report individual outcomes and assumptions, including failures; do not convert sensitivity survival into physical confidence.

The hardware bridge exposes raw IMU telemetry and a commissioning target interface; it does not yet assemble the 47-value policy observation or run the learned actor through calibrated joints. Document that missing deployment boundary. A future runner needs one serial owner, joint telemetry freshness, shared observation construction, gait phase, residual scaling/clipping, command timeout, sensor stop behavior and calibration/geometry identity. Do not open a second serial monitor alongside the bridge or remove the physical-gait interlock to appear complete.

## Release gate

1. Close A1-A7 with focused regression evidence and update the affected docs/manifests. Complete A8's simulation interfaces and sensitivity record, while clearly retaining the physical deployment limitation.
2. Re-run the full Python suite and both firmware builds. Test remote request order and long command streams without connecting actuators. Verify all model/source/calibration hashes after final edits.
3. Freeze source, resolved configuration, observation contract, acceptance suites, lock, seed plan and actual budgets. Benchmark the chosen CPU worker configuration on those exact inputs. Only then run short PPO/SAC pipeline smoke jobs; their checkpoints remain smoke candidates.
4. Queue the six planned runs only after the freeze. Validate periodically, select eligible checkpoints and evaluate the selected candidates once on the untouched test suite. Report actual results, including failed acceptance or interrupted runs.
5. Keep physical walking disabled until measured servo calibration, sensor mounts/bias/timing, loaded actuator behavior, assembled mass/COM and restrained commissioning evidence exist. These are measurement requirements, not software defects the reviser can fabricate away.

## Evidence and limits

Independent Python test command from the workspace: `PYTHONPATH=outputs/mist-robot work/py311/bin/python -m pytest outputs/mist-robot/locomotion/tests outputs/mist-robot/locomotion/hardware/test_bridge.py outputs/mist-robot/locomotion/hardware/test_sensors.py -q`. Result: 79 passed, 12 subtests passed, two Gymnasium unbounded-observation warnings, 19.07 s. An initial invocation without the repository PYTHONPATH failed hardware-test import collection; correcting the import path produced the stated result. Passing tests do not cover the findings above.

The existing reviews remain supporting evidence: `sol03_simulation.md`, `sol06_profiles.md`, `sol07_hardware_sensors.md`, `sol08_training.md` and repository `reviews/sol05_upgrade.md`. I read the upgrade research and its independent official-source review; I did not independently re-fetch every vendor page or inspect the planned laptop. No optimization, physical actuation or new firmware upload occurred during this audit.

The attitude-compensation sign remains a controller-design question. Sol03's dynamic probes slightly favoured the original sign, while the geometric test favoured the current transform. Define the objective and compare delayed-sensor perturbations across gait phases before changing it. This is not evidence to revert the prior inertia-frame or timestep corrections, and it is not a demonstrated instability blocker.


## Final integration additions

The parent added per-instance `MistEnv(scenario=...)` overrides for mass scale, body COM, phone offset, motor strength, voltage, motor delay and friction. These are applied to physics without changing nominal feedforward and are recorded in `info.randomization.scenario`. This closes part of A4/A8. It does not make the ignored configuration fields effective, and it does not add sensor-delay/dropout cases by itself. The parent also corrected CAD-origin velocity and added loaded body/nonfoot contact flags. My 79-test run preceded these final changes; it is not their regression evidence.

Sol09's `sensitivity.py` and `validation_cases.json` now define 130 executable cases: 100 terrain/direction/payload/sensor combinations plus 30 nominal held-out mass/COM/motor corners. Phone-without-phone cases are excluded, case IDs produce order-independent seeds and pass requires finite metrics, no fall/contact, progress and drift/tilt bounds. This materially improves screening. Preserve those additions, with these remaining corrections:

- The scorer has no required episode duration/completion check. A one-step upright stop can pass. It records velocity RMSE without limiting it and does not gate saturation/tracking. The criteria are screening thresholds, not complete acceptance. Integrate one versioned acceptance definition with training and the legacy evaluator instead of leaving contradictory pass flags.
- `run_case.contact()` overwrites `body_ground_contact` with any non-toe external contact at any force. The environment defines body contact as loaded base contact and nonfoot contact separately at greater than 0.1 N. Use named, consistent contact metrics with a declared force threshold. Do not silently change a field's meaning in one consumer.
- Source fingerprints include top-level Python/config/source paths but omit `hardware/sensors.py`; declared missing inputs are skipped. Hashes are captured after a case without checking the before/after envelope. Use A1's shared frozen envelope and checkpoint verifier here too.
- The suite seed base is 9,100,000 plus a case-name hash, but `train.py` accepts arbitrary evaluation seeds above 1,000,000. A named high range is not an enforced test separation. Reserve explicit suite identity/seed ownership. Keep sensitivity development cases separate from the untouched final test if their outcomes guide revisions.
- Add sensor delay/dropout/bias corners and independent phone-mass changes. Current mass scaling changes all robot links, so it does not substitute for a heavier phone. Add yaw and command-transition coverage when the scorer supports them. Freeze the case manifest before final selection.

Sol10's README correctly labels absent checkpoints, simulation limits and portability dependencies. Its new review confirms two concrete integration defects to include in A1/A8: default `python -m locomotion.train` cannot resolve top-level `mist_env`, and timestamped default smoke output disagrees with the remote's fixed `runs/smoke` lookup. Test actual environment construction in direct and package/subprocess modes. Give the remote explicit verified checkpoint selection rather than relying on a particular smoke folder.

The alternate hardware/backend research passes the supporting Sol05 review, subject to an explicit CPU-to-CUDA environment handoff. No new-machine throughput claim is warranted. All ten Sol workstreams are now represented in this specification; their completion does not itself close the listed defects.
