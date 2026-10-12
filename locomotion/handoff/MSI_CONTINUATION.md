# MIST continuation on the MSI

Work resumed on 12 October 2026 at the user's request. The portable experiment runs on the MSI; accurate walking and physical transfer remain unfinished. The original chat and pause record stay in `history/CHAT_HISTORY.md` and `PAUSED_STATE.json`. This document owns the current continuation; `../DIRECTIONS.md` retains the earlier frozen contract and checkpoint details.

## Local execution

The Windows review checkout is `C:/Users/hssil/Downloads/03_Programming_Projects/spider-robot/output/mist-locomotion-msi/repo`. The runnable Ubuntu WSL2 checkout is `/home/hssil/mist-locomotion-msi/repo`. Execute source-bound jobs in WSL: native Windows produces backslash keys in the frozen source inventory. Git line-ending conversion is disabled locally. Both checkouts were restored to the verified release bytes, and all 55 frozen source/CAD files match identity `8793d43d546c95c6fd695860305f96a0627e49be9ec81779e313b63d1b92e8c1`.

The machine is an MSI Stealth 16 AI Studio A1VHG with Core Ultra 9 185H, 16 cores/22 logical processors, 63.49 GiB usable RAM and RTX 4080 Laptop GPU with 12,282 MiB dedicated memory. The installed NVIDIA driver is 591.74. Machine and installed-package evidence is in `MSI_STATE.json`.

The exact CPU environment is `.venv-locomotion/bin/python` under the WSL checkout, Python 3.11.16 with Torch 2.8.0+cpu. The separate `/home/hssil/mist-locomotion-msi/venv-cuda/bin/python` environment has Torch 2.8.0+cu126, CUDA 12.6 and every other exact lock pin. GPU allocation, matrix multiplication, synchronization and CPU comparison passed. Use [MSI_SETUP.md](MSI_SETUP.md) to verify it. Runtime environments and downloaded caches are local dependencies.

```bash
cd /home/hssil/mist-locomotion-msi/repo
export MIST_PYTHON="$PWD/.venv-locomotion/bin/python"
"$MIST_PYTHON" -c 'from locomotion.provenance import source_hashes,identity; print(identity(source_hashes()))'
"$MIST_PYTHON" locomotion/sim_remote.py --port 8131
```

The simulation remote is at `http://127.0.0.1:8131`. It displays the R7 assembly and simulated sensors. The shipped physical calibration remains unconfigured.

The user is building the R7 now. Hardware measurements wait until assembly. For the Windows launcher and simulation/dry-run interface controls, see [REMOTE_GUIDE.md](../REMOTE_GUIDE.md). UI changes preserve the frozen simulation backend and experiment sources.

## Verified frozen evidence

The release simulation archive SHA-256 is `2775f145610f7a15dbea87ced4c27cbda5427a55bf1ca650a1f303f200a3534f`. Archive validation and relocation passed with 213 payload files, all 55 required sources, and a reset/step producing the 47-value observation. Saved PPO/SAC checkpoints and the matching SAC replay verified against their provenance sidecars.

The frozen test suite passed 99 pytest tests plus 12 subtests. Hardware bridge/sensor tests passed 21 tests. The first helper suite passed 20 tests after the report stdout fix; the separate recovery-wrapper regression passed as well. Test and run logs are under `../runs/msi_20261012/`.

The untouched MPU final suite completed for both saved 51,200-transition candidates. Source and suite identities matched, and independent receipt review found complete ordered evidence. See [the results report](../reports/msi_20261012/RESULTS.md) and [the independent audit](../reviews/msi_final_receipt_audit.md).

| Candidate | Strict passes | Scored failures | Execution errors | Falls |
| --- | ---: | ---: | ---: | ---: |
| PPO | 12/131 | 119 | 0 | 0 |
| SAC | 0/131 | 131 | 0 | 0 |

All twelve PPO passes are stop commands. Both retain the intentional sensor-dropout failure at 336 samples; the other 130 cases reach 960 samples. The old training was not resumed and has no new final training checkpoint or fabricated summary. These final receipts are reporting evidence; development work uses separate seeds and does not tune against them.

## Compute measurements

The short CPU physics probe used 2,000 vector steps after 100 warmup steps. It measured 296.81 transitions/s with one worker, 513.03 with two, 848.78 with four, and 1,042.31 with eight. These rates exclude policy optimization, evaluation overhead and sustained thermal limits. Source-bound continuation of an old run still requires its original two-environment contract.

The bounded CPU/CUDA training screen completed four fresh 8,192-transition jobs with the same Torch build, two environments, sequential execution, and initial/final development validation. Every job completed its budget and checkpoint verification. PPO recorded 40 optimizer epochs; SAC recorded 3,840 gradient steps.

| Algorithm/device | Wall time with startup and validation | Validation time | Trainer time after subtracting validation |
| --- | ---: | ---: | ---: |
| PPO CPU | 177.41 s | 145.16 s | 23.98 s |
| PPO CUDA | 269.75 s | 221.91 s | 42.13 s |
| SAC CPU | 192.50 s | 146.21 s | 38.93 s |
| SAC CUDA | 284.16 s | 208.68 s | 69.66 s |

Use CPU for the present small-policy/PyBullet configuration: both total time and time after subtracting evaluation were lower. The last column includes rollout, optimization, model construction and checkpoint overhead; it is not an optimizer-only measurement. This single short trial does not establish sustained thermal performance or device ranking for other models/batches. CUDA remains available for later workloads. The full receipt is `../runs/msi_20261012/training_devices_8192/benchmark_report.json`; the independent review is `../reviews/msi_training_device_audit.md`.

The prepared six million-transition jobs have not started: first settle the controller and hardware timing contract.

## Development findings

All gait development probes use zero residual actions and seeds starting above `2**50`; they preserve the original acceptance criteria and frozen source bytes. Simulator contact truth is diagnostic output only. Receipts include the experimental code hashes, so preserve the corresponding helper versions.

The 480-step forward probe reproduced a tracking failure. Reducing planned body shift from 20 mm to 5 mm reduced velocity RMSE from 0.0501 to 0.0137 m/s. This removes most periodic velocity ripple but leaves a roughly 0.00244 m/s forward speed deficit. Removing shift entirely worsened some yaw behavior; the small-shift result is not a qualified controller.

The first recovery experiment changes only horizontal swing interpolation. Its endpoint velocity matches stance velocity while keeping the 5 mm shift, vertical lift, stance timing, support logic and actuator model. The paired forward probe reduced steady speed bias from -0.002442 to -0.002170 m/s and peak path error from 0.03789 to 0.03555 m. Both short screens still failed; duration qualification requires 960 steps.

This experiment uses `scripts/experimental_recovery.py` and `scripts/dev_recovery_probe.py`. A shared case collector retains later successes when an earlier case fails. Astra caught a repeated wrapper `pool.map` defect before execution; the repair reuses the owning collector and has a real failed-first/successful-second process-pool regression. Review evidence is in `../reviews/msi_astra_critique.md` and `msi_astra_revision.md`.

The clearance-window experiment changes only horizontal recovery timing to planned phases .84–.96, while retaining vertical lift, support schedule, stance-compatible boundary velocity and 5 mm body shift. It passed the 480-step forward tracking screen, reducing steady bias to -0.000796 m/s and peak path error to 0.02479 m. A full 960-step paired test then covered four cardinal directions and both yaw directions, with phone payloads 0 and 0.155 kg. The matched reference passed 0/12; clearance passed 4/12, all yaw. Every cardinal case still failed path or velocity tracking. This is a useful causal improvement, not qualified walking. The complete receipt is `../runs/msi_20261012/dev_clearance_cardinal_yaw960_01.json`.

A 48-case, full-duration factorial comparison then isolated smaller body shift and a 15% translational geometric stride gain. Requested/scored commands stayed fixed, gain left yaw unchanged, and pure-yaw gain pairs gave identical results. All four combinations completed without execution errors. The receipt is `../runs/msi_20261012/dev_stride_factorial960_01.json`.

| Clearance variant | Strict development passes | Passing commands |
| --- | ---: | --- |
| 5 mm shift, gain 1.00 | 4/12 | Both yaw directions, both payloads |
| 3 mm shift, gain 1.00 | 0/12 | None |
| 5 mm shift, gain 1.15 | 6/12 | Forward and both yaw directions, both payloads |
| 3 mm shift, gain 1.15 | 2/12 | Forward, both payloads |

The gain reduced cardinal peak path errors to roughly 1.7–2.0 cm at 5 mm shift, but backward/lateral velocity RMSE rose to 0.017–0.021 m/s. The smaller shift worsened support-sensitive cases. Forward plus yaw improvement does not establish reliable four-direction walking. Preserve these failed cases when investigating support transfer; simply increasing gain or shrinking shift is insufficient.

## Planned support-transfer trial

The implemented reference changes only the common planned body shift, fitting a bounded periodic cubic spline with a NumPy active-set QP. Its inputs are requested command, planned foot geometry/phase and declared payload. It retains the 5 mm-reference clearance/gain contract, cycle, lift, swing order, attitude compensation, sensors and actuator settings. Solver failure is explicit. All twelve command/payload cases pass the sampled nominal static audit, including IK limits, periodic C2 shift continuity and moment balance. Attitude corners can still invalidate nominal feasibility; this is not a robustness qualification.

The matched backward/.155 kg pilot completed 480 steps per case using development seed `1154976095502900`. Planned negative-force rows disappeared, but velocity RMSE increased from .017963 to .020554 m/s, peak path error from .017752 to .021440 m and saturation from .003446 to .036918. Front scheduled-stance contact worsened. Both cases fail the original velocity and duration criteria. The candidate is not promoted and the 960-step expansion did not run.

The saved-target torque estimate places candidate peak knee demand at .5744 N m against the uncalibrated .588 N m cap, leaving .014 N m before dynamic error. This supports investigating actuator demand and transfer dynamics; it does not justify increasing the cap. The original v1 wrapper's initialization error and completed reference are preserved. V2 repairs declared-payload initialization, and its reference results and traces match v1 exactly. Seven supporting tests passed. See [the independent support-transfer audit](../reviews/msi_support_transfer_audit.md), `../runs/msi_20261012/dev_support_static_01.json`, and the paired `dev_support_backward480_02.json` with its saved analysis and mechanism receipts.

## Remote interface

Both remotes now have readable state and telemetry, held direction controls, visible stop actions, setup error feedback and single-leg IK. The simulation retains its light teal CAD view; the joint preview retains its dark teal layout and distinguishes requested angles from physical feedback. Keyboard shortcuts leave editable fields alone. Serialized command queues ensure a late movement or arm reply cannot override a newer stop. The Windows launcher has a desktop shortcut, waits for actual service readiness, reuses an existing session and stops only its owned processes.

The local launcher starts no serial connection and supplies no measured calibration. Hardware remains under construction. The control regressions and live-browser evidence are recorded in [the remote UI review](../reviews/msi_remote_ui/REVIEW.md); operating instructions are in [REMOTE_GUIDE.md](../REMOTE_GUIDE.md).

## Next action

Read [MSI_NEXT_CONTRACT.md](MSI_NEXT_CONTRACT.md) before new training or hardware integration. It identifies command-filter, joint telemetry, observation ordering and sensor-estimator timing differences that a new source/config contract must represent.

Continue from [the support-transfer audit](../reviews/msi_support_transfer_audit.md). The static support deficit was corrected, but that correction was insufficient for dynamic contact and tracking. Diagnose front-leg contact loss, torque headroom and the whole-body COM assumption using the saved traces before selecting another single-variable intervention. No larger controller sweep or training is justified by this pilot. Promote a controller only after development/validation evidence justifies a deliberately frozen new experiment, including surfaces and coupled weight/motor/sensor variation. Start fresh training for changed dynamics or observations.

The reviewed sensitivity serializer migration remains unapplied. Use its narrow migration workflow only after source-bound jobs finish; it cannot convert old checkpoints to a changed controller. Physical walking still requires the R7 mass, actuator, calibration and sensor measurements in the next-contract document.
