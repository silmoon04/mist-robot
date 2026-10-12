# Faster remote verification — 13 October 2026

The user reported slow walking, then clarified that the motors also appeared slow. The selected Faster crawl preview is running at http://127.0.0.1:8131/ through the Windows fast launcher. The desktop MIST Remote shortcut targets `Start MIST Remote (Fast).cmd`. The active flat-floor, zero-payload, MPU6050, seed-42 setup was carried across the migration. Motion is stopped; the joint service remains dry-run.

## Measured change

The same `probe_remote_speed_v2.py` loop requested 0.025 m/s before and after the change. The original server clipped it to 0.012 m/s and advanced at 0.47282 times wall speed. The final interactive server accepted 0.025 m/s and advanced at 1.03240 times wall speed over the short sample. Its cumulative live telemetry stayed near 1.00 after more than 100 simulated seconds. These are runtime measurements, not a walking qualification.

The selected controller uses a 1.2-second cycle instead of the 3.2-second reference, a cadence-scaled 1.875 mm body shift, gain 1.15 and horizontal recovery phases .82–.96. The paired 480-step forward experiment measured average progress 0.01702/0.01699 m/s for bare/0.155 kg payload versus 0.00875/0.00898 m/s for the slower clearance/gain reference. Requested speed is 0.025 m/s; the achieved speed remains lower. The four phone-payload cardinal cases completed without falls, rejected IK, sensor faults or body/nonfoot contact. Original path and velocity criteria still fail.

Maximum-joint qdot P95 increased from 1.196/0.967 to 3.166/2.224 rad/s for bare/phone payload. Target slew remains 1.8 rad/s: a 3 rad/s trial did not improve forward progress. Actual physical velocity in simulation differs from filtered target velocity because of inertia/contact dynamics. No loaded hardware response was measured. The development yaw cases used ±0.106667 rad/s and are above the remote's 0.06 rad/s cap; they do not qualify that cap.

## Runtime and interface

The separate interactive worker keeps the frozen physics timestep, schedules steps against wall deadlines, bounds catch-up after stalls and retains a wall-time 350 ms command watchdog. Legacy IK/PPO/SAC reset paths retain the original configuration and command limits. Fast mode rejects a checkpoint path instead of loading a policy under changed gait settings. Configuration/profile hashes report the settings actually loaded.

A bounded rendering probe found a 476 ms frame with 42 visual grid objects versus 131 ms after their removal in the isolated walking episode. The final grid uses one collision-free, zero-mass mesh; a separate cold-frame probe measured 280 ms. The poses and coldness differ, so those frame timings are not a controlled speedup ratio. Final live throughput, rather than that ratio, supports the near-real-time result. Frame cadence is lower than the UI's polling cadence when rendering is expensive.

Live browser checks used held W and Q, release, Stop and Escape. The telemetry showed the corresponding 0.025 m/s and 0.06 rad/s commands, then all zeros. Sensor state remained valid, with no reported fall or simulator error. Untouched controls synchronized to the live zero-payload setup. Desktop 1280×900 and phone 390×844 checks showed no horizontal overflow. The phone Stop target measured about 101×68 px. Temporary viewport overrides were reset. [Desktop proof](desktop.jpg) and [phone proof](phone.jpg) show the final interface.

Actual Windows launch, stop/restart and repeated launch succeeded. A repeated launch reused the same supervisor PID/start identity. `launcher_verification.json` records the final profile and dry-run joint mode. Separately started services were stopped only after verifying argv, checkout and kernel start identity through pidfds. Original launcher bytes remain preserved.

## Evidence and limits

Six backend tests, nineteen UI interaction tests and eight fast-gait static tests passed. The final combined-mesh backend revision passed the six backend tests again. The independent [boundary review](../msi_remote_speed_review.md) and [preservation audit](../msi_remote_speed_preservation.json) record tested hashes. All 55 frozen sources/CAD files and 139 prior protected run/helper/launcher files remain exact in Windows and WSL.

Live receipts are in `../../runs/msi_20261013/remote_speed/`. The versioned development probes and fast walking receipts remain under `msi_20261012` because their recorded reference paths and helper hashes bind that location. They were executed on 13 October. Failed trials are retained. No training, 960-step qualification, serial actuation or calibration was performed.

The reusable lesson is to measure command acceptance, actual body/joint motion and wall pacing separately. Raising a target filter did not solve this walking deficit; shortening the gait and reducing rendering stalls did. The CLI probe now waits for a fresh nonzero command sample before judging acceptance, avoiding an initial cached-state false result. Boundary, watchdog and profile-identity regressions retain those distinctions for later changes.
