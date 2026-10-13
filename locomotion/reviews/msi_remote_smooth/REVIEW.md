# Smooth remote and speed ceiling — 13 October 2026

The user's next report was that the UI felt choppy and the speed still looked low. The earlier near-real-time physics measurement did not establish smooth display updates. This work measures those two paths separately, preserves the frozen simulation contract and adds an optional higher-speed preview.

## Reproduced latency and corrected rendering

The unchanged `scripts/probe_remote_latency.py` probes actual loopback HTTP, with concurrent state reads every 25 ms and zero-command POSTs every 100 ms. It sends no hardware command. Its thresholds are state/command P95 below 80 ms and at least 15 observed visual updates/s.

| Receipt | State P95 | Command P95 | Observed visual updates |
| --- | ---: | ---: | ---: |
| `baseline_01.json`, v1 on 8131 | 258.4 ms | 267.4 ms | about 2 Hz JPEG changes |
| `baseline_02.json`, v1 on 8131 | 265.5 ms | 289.2 ms | about 2 Hz JPEG changes |
| `green_final_01.json`, v2 on 8131 | 8.36 ms | 3.16 ms | 40.00 Hz poses |

The final four-second probe passed all three predeclared thresholds. Its observed 40 Hz is bounded by polling; the worker publishes each fixed 20 ms physics step. The old renderer held the physics lock while producing software JPEGs. The new versioned server publishes small pose snapshots and model metadata, and the browser draws the actual CAD geometry using locally bundled Three.js r170 and its MIT license. Visual origins come from the generated URDF; pose frames use Bullet link frames, with the base inertial transform converted to the body frame. Rough terrain capture reproduces the frozen heightfield draws without consuming additional randomness.

The embedded browser initially supplied display callbacks near 1 Hz despite reporting the document visible. `viewer/frame_clock.mjs` schedules one frame via the display callback or a 33 ms fallback timer, whichever arrives first. It cancels the losing callback and never runs two draws for one scheduled frame. Hidden documents still skip rendering. This app displayed 23–25 fps with about 0.8–1.9 ms draw work, 423,080 triangles and 105 draw calls for the bare setup. This is the measured app result, not a promise of 60 fps or a general GPU benchmark.

Pose interpolation uses an 80 ms buffer and does not predict motion beyond the last measured pose. A repeated stopped pose neither resets its age nor rewinds the display. Epoch changes rebuild the model and clear the buffer. The view exposes current fps and pose age to the user. The original held-control queue, explicit stop, focus-loss stop and independent 350 ms watchdog remain active.

## Highest tested preview

The complete receipt `runs/msi_20261013/speed_ceiling/forward480_01.json` contains eight fresh forward cases; `analysis_01.json` checks its helper hashes and compares saved paired reference results. Every case completed 480 steps. No training, 960-step qualification, calibration or physical actuation ran.

| Preview | Cycle | Requested forward speed | Average progress, bare / 155 g |
| --- | ---: | ---: | ---: |
| Default Faster crawl | 1.2 s | 0.025 m/s | 0.01702 / 0.01699 m/s |
| Optional Higher speed | 1.0 s | 0.040 m/s | 0.02430 / 0.02382 m/s |
| Faster cadence trial | 0.8 s | 0.040 m/s | 0.02084 / 0.02033 m/s |
| Larger request trial | 0.8 s | 0.060 m/s | untested bare / 0.01931 m/s |

The optional preview gains about 40–43% average forward progress over the default. Its geometric stride cap is 35 mm, with 1.15 translational gain; at a 1.0-second cycle, requested speed above about 0.03804 m/s is already stride-clipped. Raising a UI slider cannot remove this controller limit or contact/actuator dynamics. The shorter cadence regressed progress, and a larger motor target filter had already failed to improve it in the prior paired screen.

The selected preview retains the frozen 1.8 rad/s target slew, torque cap, timestep and sensors. Maximum-joint target-lag P95 was about 0.131/0.133 rad for bare/phone cases. All eight new cases avoided falls, sensor faults, IK rejection and body/nonfoot floor contact. Path and velocity acceptance still fail, and directions other than forward were not screened here. Faster crawl remains the default; Higher speed is an explicit option. Loaded servo speed and timing remain unmeasured while the user builds the robot.

## Verification and bounded retrospective

Ten backend regressions passed, covering real image-free reset payloads, immutable pose/model epochs, exact mesh bytes, atomic reset failure, original policy config/provenance handling, watchdog/error zeroing, asset bounds and paired rough-terrain physics. Thirty UI/viewer regressions passed, including the nineteen preserved control tests, pose interpolation, duplicate/stall timing and frame scheduling. Three v4 gait tests passed through the module runner. The first direct script invocation lacked the repository import root; that failed log is retained separately from the successful module log.

`launcher_final_01.json` records successful Windows launch, repeated launch retaining PID/start identity, owned stop and restart, and a dry-run joint bridge. The desktop shortcut targets the smooth command file. The live main page applied Higher speed, drove forward at the 0.040 m/s setting, and returned its command to zero on release/Stop. It then restored Faster crawl, flat terrain, MPU6050, seed 42 and the user's absent-phone setup. The final state and screenshots are saved with this review.

Finding **REMOTE-DISPLAY-01**: prior physics pace near 1× coexisted with roughly 2 Hz visual updates and 250+ ms HTTP stalls. The owning check is now the actual concurrent HTTP probe, supplemented by measured browser fps. Its two red receipts and green final receipt close the rendering-lock regression for this device; sustained multi-client performance remains outside this bounded check.

Finding **REMOTE-HEALTH-01**: the old supervisor required an `image` field, while the new producer correctly returns poses. An initial adapted health result also labeled connection refusal as an occupied port. The versioned health adapter now validates the actual v2 pose payload and only sets an occupant mode after a successful response. Real producer-state and connection-refusal regressions pass, followed by actual launcher start/reuse/stop/restart. Earlier launcher/helper bytes remain exact. Reuse these checks when changing this producer/consumer seam.

The 55 frozen source/CAD files and previously recorded helper/receipt bytes are audited against the prior milestone. The current qualification failures remain in the receipts and guide. No global agent instructions were changed.
