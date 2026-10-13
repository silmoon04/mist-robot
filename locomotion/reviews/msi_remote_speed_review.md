# Interactive remote speed review

Reviewed on 13 October 2026. Scope: the new interactive simulator and fast-session launchers, their separate runtime profile, the updated simulation UI, and the added regression tests. The original simulator, training configuration and 55 fingerprinted files remain outside the edit scope. This pass launches no HTTP service, training job or physical interface.

## Findings and corrections

- The initial interactive import lacked the scripts directory needed by the experimental controller's sibling imports. The initial constructor also passed an unsupported `shift_m` argument. The parent corrected both before the first real reset check.
- Initial UI synchronization omitted randomization and custom sensor settings and could overwrite fields edited while the first response was pending. The UI owner now initializes untouched fields from the applied setup, preserves dirty fields, and uses the applied controller to bound movement commands. Six new UI regressions cover these paths.
- The first metadata implementation hashed the current profile file on every state request, despite loading its values only once. The parent now retains the loaded profile bytes and hash together. A regression checks that later disk bytes cannot change the reported identity of the loaded settings.

## Isolation and behavior

The selected v3 preview uses `WideRecoveryFastCrawl`: 1.2-second cycle, 0.001875 m body shift, horizontal recovery starting at phase .82, and translation gain 1.15. Its servo target slew is the original 1.8 rad/s. The copied runtime configuration is equal to the frozen configuration in every value; torque cap, gains, dimensions, physics timestep and sensor contract remain inherited. The fast reset refuses checkpoint paths. IK/PPO/SAC delegate to the original reset, including its policy provenance checks, and construct an environment without the preview controller. Tests exercise the real dispatch while replacing only the expensive environment and policy loading boundaries.

The actual command method accepts and caps translation at 0.025 m/s in fast mode, caps original modes at 0.012 m/s, rejects nonfinite commands and accepts an explicit zero command. The selected yaw cap is 0.06 rad/s. UI caps follow received controller state, not pending selector choices. Existing lifecycle-stop, autorepeat, delayed-request and joint-preview regressions remain unchanged.

Clock changes preserve 1000 Hz physics and 50 Hz control. A deterministic stall test checks the stale-command watchdog and bounded catch-up after an 0.8-second render stall. Clock tests do not claim a measured frame rate or sustained machine capacity.

Fast resets build and render a candidate before replacing the active episode. A failed candidate closes its resources and preserves the existing environment, information record and clock generation. The real-reset test also queries Bullet directly to require zero mass and no collision shape for the added floor landmarks.

The fast launcher uses the existing ownership and cleanup supervisor. Its health adapter rejects the original simulator on the same port instead of treating it as the interactive service. The dry-run bridge remains the companion service; no serial argument is introduced.

## Validation status

Final verification is complete. All six backend tests passed again after the mesh correction in the WSL Python 3.11 environment in 1.312 seconds. The suite performed one real reset, verified the v3 controller parameters and original servo slew, and confirmed that the combined grid mesh had zero mass and no collision shape. Failure cleanup, legacy dispatch, loaded-profile identity, command limits, clock behavior and the launcher compatibility check passed.

All six new speed-UI tests and thirteen unchanged interaction regressions passed together under Node on Windows: 19 tests, no failures. These tests run the actual inline script with deferred producer-shaped API replies; they do not substitute for the parent's browser layout checks. The new test files were copied to WSL, and hashes of the tested backend, profile, v3 helper, HTML and test files match between both trees. All 55 frozen source/CAD files still match their inventory.

| Tested artifact | SHA-256 |
| --- | --- |
| `sim_remote_interactive.py` | `87340b78196b7cdaeb852a6e65aa8e4ec9d95c7c6ecde1d49de76dd71594dd2c` |
| `profiles/interactive_fast.json` | `5ae2d0d13a8f142bd650eacd1bed7ade32ab14f2853d1e54f70a76913355bcaf` |
| `scripts/experimental_fast_crawl_v3.py` | `629f93ba11ff85b34287f4fe670645442e982838a40652347762c4e9181d7fe2` |
| `sim_remote.html` | `f76bfe59e99b2f195b6777568205b23af7fec392b03938314435b4e10db5691a` |
| `scripts/test_remote_interactive.py` | `53eec0e1c4b01b287b8b616801867ced6ff4445a1172e3359e04824409c032af` |
| `scripts/test_remote_speed_ui.mjs` | `f236d683e4aaa582fc0f9f84e718dc342bb8c17516f2c8f175309e4e1dda3791` |
| Unchanged `scripts/test_remote_ui.mjs` | `b82eec88e2abe4397a1a18d0e38360f0066ec33f2e677f11f3e28bc5310907ba` |

The API and control regressions pass at these revisions. Rendering performance remains subject to the measured limitation below; service migration and sustained live verification belong to the parent.

The development gait comparisons belong to the separate locomotion experiment stream. These remote tests establish construction, configuration isolation, API behavior and display consistency. They do not establish accurate walking, measured loaded motor speed, randomized robustness or hardware transfer.

## Rendering performance follow-up

The initial grid used 42 separate visual bodies. A bounded isolated diagnostic disabled the background worker and ran 150 control steps with exactly three frames in total, including the constructor frame. Idle steps averaged 3.48 ms; walking steps averaged 4.34 ms, including 1.26 ms for gait targets. Rendering plus JPEG took 476.01 ms with those bodies. Removing only the 42 bodies, after verifying each had zero mass and no collision geometry, reduced the next render plus JPEG to 130.59 ms. The subsequent walking batch averaged 4.87 ms. Successive batches covered different gait phases, and the render comparison used one frame per condition, so these numbers identify the dominant cost rather than establish a precise speedup. No HTTP service or existing episode was modified.

The parent replaced those bodies with one combined visual mesh containing 168 vertices and 84 triangles, retaining 10 cm landmarks and the same extent. The six backend tests passed again. The new `scripts/probe_remote_render_cost.py` constructed one isolated simulator with its worker disabled and timed exactly one cold reset frame: rasterization 271.29 ms, JPEG encoding 5.65 ms, and 280.01 ms from render entry through completed JPEG encoding. It directly verified one mesh body, zero mass and no collision shape. The receipt is `runs/msi_20261013/remote_speed/render_cost.json` and includes the loaded profile, tested hashes, frame count and scope.

The mesh reduces the observed render cost, but the remaining 280 ms frame still blocks the simulation worker substantially. The new measurement is at the reset pose and includes a cold frame; the earlier measurements were after walking, so their ratio is not a controlled benchmark. Sustained live throughput must be measured before claiming the performance issue is resolved. The prior 50 Hz walking cost plus a nominal five 280 ms frames per second would exceed one wall second of work per second. The worker schedules its next frame 200 ms after rendering completes, so its actual frame rate is lower and this arithmetic is a capacity warning, not a throughput prediction.

Repeat the one-frame probe from the repository root with `.venv-locomotion/bin/python -B locomotion/scripts/probe_remote_render_cost.py --output locomotion/runs/msi_20261013/remote_speed/render_cost.json`. It launches no service and executes no control steps. The probe SHA-256 is `4d25200b41b0c022228a4631a02d198266cce093ea59c55913c80e6f6b896bf1`.
