# Continue MIST on the MSI RTX 4080 laptop

Work paused at the user's request on **12 October 2026**. Training, simulation experiments and the active CUDA-setup research agent were stopped. Nothing should restart automatically. This file is the handoff for the next human or coding agent.

## Read first

The R7 CAD, single-leg and quadruped models, CPU simulator, IK remote, servo/sensor approximations, PPO/SAC training, firmware, research and review records are saved. **Accurate walking and real hardware transfer are unfinished.** The baseline passed 20/239 strict cases, all stops. There were no falls; every moving case failed at least one command-tracking check. Do not describe this as a qualified walking policy.

The robot is the user-confirmed R7 direct-drive 82/90/105 mm leg with 12 V STS3215 C018 servos. Sensor options are a fixed MPU6050, Xiaomi Mi 9 SE through Android SensorServer, and explicit open-loop mode. No foot-contact sensors or vision are assumed. The phone's pan is locked during locomotion. Printed masses, motor response, sensor timing and final assembly still need measurement.

Read these files in order:

1. This file and `locomotion/handoff/PAUSED_STATE.json`.
2. `locomotion/README.md`, `RESEARCH.md`, `UPGRADE.md`, `hardware/README.md` and `profiles/README.md`.
3. `locomotion/reviews/astra_reaudit.md`, `astra_revision.md`, `helper_reaudit.md` and `receipt_serialization_plan.md`.
4. `locomotion/handoff/history/CHAT_HISTORY.md` and `thread_public_snapshot.json` for the available conversation and command history.
5. `locomotion/runs/final_baseline_all.json`, `runs/diagnostics/shift_ablation.json`, and each algorithm's `evaluation_periodic_51200.json`.

## Files and downloads

Clone `https://github.com/silmoon04/mist-robot.git`, then use this handoff commit or the `mist-locomotion-handoff-2026-10-12` release. Git contains the simulation source, required CAD meshes, configuration, tests, review/history records, result receipts and policy ZIP checkpoints. The handoff release contains:

- `mist-simulation.zip`: portable simulation tree, source CAD exports, every saved current checkpoint, and SAC replay buffers. Extract over a fresh clone, preserving the `mist-robot/` directory structure.
- `mist-work-history.zip`: scratch scripts, logs, diagnostics and retired experiment artifacts. These are historical evidence; do not load retired policies into the current robot.
- `HANDOFF_SHA256SUMS.txt`: checksums for the release archives.

The pre-existing `build-2026-10-12` release retains the complete original CAD/media archive and other repository exports. Its files were downloaded and checked against its SHA256SUMS. They are already on GitHub and are not duplicated as new Git blobs. Runtime environments, caches and credentials are not portable deliverables.

## Frozen experiment contract

The source inventory is saved in `locomotion/handoff/frozen_sources.json`. Its identity is:

```text
8793d43d546c95c6fd695860305f96a0627e49be9ec81779e313b63d1b92e8c1
```

Do not edit a fingerprinted file or CAD dependency before deciding how to preserve old checkpoint compatibility. `provenance.py` verifies source/CAD hashes, observation/action contract, experiment envelope, checkpoint contents and matching SAC replay. Paths relocate relative to the repository. Never bypass these checks to load an old policy.

Physics is 1000 Hz; command/control is 50 Hz. Earlier 240 Hz damping-unstable runs and the incorrect principal-inertia/body-frame runs were rejected. The stable timestep, correct body frame and effective contact-friction handling have regression coverage. Keep those corrections.

## Saved training state

Both CPU runs reached 51,200 recorded transitions, seed 42, two environments. They were interrupted during the final validation at the pause request. `training_summary.json` and `final.zip` were not produced. Completed periodic validation is available, and the last valid saved artifact for each is:

```text
locomotion/runs/ppo_51200/checkpoint_51200.zip
locomotion/runs/sac_51200/checkpoint_51200.zip
locomotion/runs/sac_51200/checkpoint_51200_replay_buffer.pkl
```

Both have matching `.provenance.json` sidecars and a continuation seed of 1042. PPO's saved checkpoint records 245 optimizer updates; it was saved before the final rollout's optimizer update. SAC records 25,343 updates. The last in-memory update is not an additional recoverable checkpoint. Resume reseeds environments and does not restore an uninterrupted live/RNG/rollout state.

Completed periodic validation covered 72 cases per algorithm. PPO passed 6/72; SAC passed 0/72. Both had zero falls and neither was eligible. No `best.zip` qualified. Final untouched policy tests have **not** run. Preserve those distinctions when reporting results.

## Setup on the MSI

These commands assume Linux or a Linux/WSL Bash environment with Python 3.11. Native Windows installation has not been tested. Start with the reproducible CPU environment:

```bash
git clone https://github.com/silmoon04/mist-robot.git
cd mist-robot
bash locomotion/scripts/setup_cpu.sh
export MIST_PYTHON="$PWD/.venv-locomotion/bin/python"
"$MIST_PYTHON" -c 'from locomotion.provenance import source_hashes,identity; print(identity(source_hashes()))'
"$MIST_PYTHON" -m pytest locomotion/tests -q
"$MIST_PYTHON" -m unittest locomotion.hardware.test_bridge locomotion.hardware.test_sensors -q
bash locomotion/scripts/start_sim.sh
```

The simulation remote is at `http://127.0.0.1:8131`; it sends no hardware commands. Use the hardware bridge only after reading its commissioning instructions. Its shipped calibration is unconfigured and hardware walking remains gated.

Inspect the actual MSI's CPU SKU, RAM, GPU, dedicated VRAM and driver. The usual RTX 4080 **Laptop** GPU has 12 GB VRAM; 64 GB system RAM does not add dedicated VRAM. The current published standard Isaac Lab floor is 16 GB VRAM. See the official links in `UPGRADE.md` before choosing Isaac.

For CUDA, create a **separate** Python 3.11 environment. Install an official CUDA-enabled PyTorch 2.8.0 wheel for the installed driver using [PyTorch's versioned instructions](https://pytorch.org/get-started/previous-versions/). Install the other pinned dependencies with the CPU-only `torch==2.8.0+cpu` entry omitted; never run the full CPU lock in that CUDA environment. Verify `torch.cuda.is_available()`, allocate a tensor on CUDA, synchronize, and record GPU name/VRAM. The proposed dedicated CUDA setup script was interrupted before creation and is an unfinished task.

PPO's small MLP often belongs on CPU; benchmark rather than assuming CUDA helps. SAC can use `--device cuda` after verification. That accelerates policy optimization; **PyBullet physics remains on CPU**. MJX/Genesis/Isaac GPU physics ports are research directions, not implemented environments. The independent MuJoCo fixed-leg comparison and full-robot MJCF export are implemented; whole-robot contact equivalence is not established.

## Next work, in order

1. Verify dependency/checkpoint/replay hashes and run the portable package relocation check. Record the MSI environment. Benchmark 1/2/4/8 CPU workers, then a bounded end-to-end training trial; avoid changing dynamics for throughput.
2. Evaluate the saved candidates on the already prepared untouched MPU suite, retaining all failures. Commands below run 131 cases per policy with new seeds, all commands/terrains/payloads plus held-out variations. Do not use these final results to select checkpoints or tune the controller.
3. Correct the known sensitivity receipt serializer **after** any source-bound jobs finish. The reviewed exact patch is printed by `scripts/migrate_receipt_only.py`. The utility archives original source/sidecar history and copies weights/replay byte-identically across only that exact serializer edit. It refuses other source changes, disables ordinary continuation for the migrated diagnostic copy, and requires diagnostic revalidation. No patch or migration has been applied yet. The final-matrix wrapper's serializer is already corrected.
4. Investigate velocity/path/yaw failures using separate development seeds. The 24-case shift ablation found that changing the body shift from .020 to .010 m reduced median velocity RMSE .05064 to .02466 m/s, while progress and tilt stayed similar; all cases still failed. Zero shift worsened tilt and some commands. Test smaller shifts/timing and stance-slip/progress causes separately. Do not simply loosen acceptance or change the default from this limited experiment.
5. Run the prepared fresh multi-seed PPO/SAC jobs once the design/controller contract is deliberately settled. Six jobs pair seeds 42, 100042 and 200042, each with exactly 1,001,472 transitions. They are prepared, not scheduled. Re-train when dynamics, observations, geometry or sensor contracts change. Preserve completed old evidence.
6. Measure masses/COM, joint zero/sign/ticks/limits, loaded servo response and sensor mount/bias/timing. Fill the R7 measurement/calibration templates. The historical four-bar bench calibration is incompatible with R7. Do supported single-leg and standing tests before hardware walking; no firmware was flashed and no physical motor was actuated in this work.

```bash
# Untouched tests, using the currently frozen source and saved candidates.
"$MIST_PYTHON" locomotion/final_matrix.py --suite all --sensor mpu6050 \
  --workers 4 --steps 960 --algo ppo \
  --checkpoint locomotion/runs/ppo_51200/checkpoint_51200.zip \
  --output locomotion/runs/final_ppo_mpu.json
"$MIST_PYTHON" locomotion/final_matrix.py --suite all --sensor mpu6050 \
  --workers 4 --steps 960 --algo sac \
  --checkpoint locomotion/runs/sac_51200/checkpoint_51200.zip \
  --output locomotion/runs/final_sac_mpu.json

# Inspect a fresh portable job; choose the device after measuring the MSI.
"$MIST_PYTHON" locomotion/scripts/run_job.py --job ppo-seed42 \
  --n-envs 4 --device cpu --print-command

# Resume the saved experiment; all recorded experiment arguments must match.
# Additional 950,272 transitions brings the recorded total to 1,001,472.
"$MIST_PYTHON" locomotion/train.py --algo ppo --terrain mixed \
  --resume locomotion/runs/ppo_51200/checkpoint_51200.zip \
  --timesteps 950272 --n-envs 2 --seed 42 --device cpu \
  --eval-terrains flat low_friction slope rough --eval-payloads '[0,0.155]' \
  --eval-episodes 1 --eval-max-steps 960 --eval-freq 51200 \
  --checkpoint-freq 12800 --output locomotion/runs/ppo_msi_resume
```

For SAC resume, use `--algo sac`, the SAC checkpoint, its matching `--replay-buffer`, and a new output directory; other experiment arguments above remain the same. A CUDA-enabled environment may set its device to `cuda` without changing physics. Do not overwrite paused runs.

`scripts/report_results.py` deliberately requires complete policy receipts and completed training summaries. Those summaries are absent because of the pause; add a truthful paused-report mode or use later completed run summaries. Do not fabricate final files to satisfy the helper.

## Review workflow and evidence limits

The requested batch used ten GPT-6.1 Sol implementation/review agents, one Astra critic and one Astra reviser, with a four-slot concurrency limit. Follow-ups identified and corrected model frames, timestep stability, sensor staleness, firmware/bridge slew and arming races, experiment provenance and serializer/helper issues. Reviews and remaining concerns are in `locomotion/reviews/`.

The short CPU rollout benchmark measured about 171/296/401 transitions/s at 1/2/4 workers on the old i5-9300H laptop, excluding optimizer/evaluation cost. The MuJoCo/PyBullet leg trajectories differed by at most about .0007 rad RMS in the compared cases. Neither establishes calibrated motors, compliant terrain, structural clearance or real-world success. The CAD animation is a nominal demonstration, with its own source/output hashes, not an acceptance result.

The work-history archive preserves old failed-frame/unstable-timestep checkpoints explicitly as retired evidence. Recreate runtimes from setup/locks; do not copy the old virtual environments. The conversation export saves available public messages and command activity, not private reasoning or unrelated chats. Local paths in historical logs identify the old machine and must not become MSI configuration paths.

## Prompt for the next agent

> Read DIRECTIONS.md and locomotion/handoff/PAUSED_STATE.json before changing files. Resume this paused R7/C018 robot project on the actual MSI RTX 4080 laptop only when asked. Inspect hardware and verify the frozen source/checkpoint/replay contract first. Preserve all failed and interrupted evidence. Finish untouched evaluation, then use isolated development experiments to correct tracking and deliberately version any new model/controller. Follow the ten-Sol plus Astra-critic/Astra-reviser workflow, paired reviews and real checks. Keep hardware actuation gated pending measured R7 calibration. Report what is implemented, measured, proposed and unfinished separately.
