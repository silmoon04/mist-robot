# Independent support-transfer audit

Reviewed on 12 October 2026. Verdict: preserve the experiment and diagnose its saved traces; **do not expand to the 960-step matrix on this pilot**. Nominal support feasibility improved, but velocity tracking, actuator saturation and front-leg stance contact did not meet the predeclared improvement condition.

This review inspected the controller, static audit, v1/v2 wrappers, regression source and saved development receipts. It performed read-only receipt/hash checks and calculations from saved targets. No physics, training, real services or hardware actuation ran. Untouched final policy receipts were not inspected.

## Controller and static evidence

The planned shift is the only controller intervention. Translation gain 1.15, clearance timing .84-.96, cycle 3.2 s, lift .012 m, swing order, attitude compensation, startup ramp, support weights, centred-COM load solver and sensor/servo settings remain inherited. Requested and scored commands stay unchanged. Planned geometry and known payload determine the spline; simulator contacts, pose and velocity remain diagnostic output.

The triangle constraints are consistent: putting the common shift `s` inside the unshifted stance triangle places the assumed centred COM inside the translated triangle `p-s`. Barycentric force fractions are affine in `s`. The all-phase weighted-load constraint matches the original solver: weighted centroid/covariance gives each raw fraction as `w_i/sum(w) + w_i * delta_i.T * covariance^-1 * (s-centroid)`. The dual active-set QP signs and reported primal/stationarity/complementarity checks agree with minimizing `.5*x.T*H*x` subject to `A*x >= b`.

The static receipt has 12 unique cases: six commands, each at payload 0/.155 kg. Every nominal gate passes on the independent 2,048-phase grid; the planner also checks 4,096 refinement phases. This is sampled nominal feasibility, not a continuous robustness proof. The periodic cubic spline is C2; the inherited startup ramp has a derivative corner and the full recovery path remains C1.

For backward/.155, peak shift is .008507 m, shift velocity RMS .011846 m/s and peak .020654 m/s. Maximum biased 50 Hz target rate is 1.75475 rad/s versus reference 1.79675, below the nominal 1.8 rad/s filter. Tilt sensitivity remains material: the +/- .05 rad audit corners include raw planned forces down to -.405 N. Forward has almost no planned shift and worse corner sensitivity than its reference, so the static pass cannot establish contact stability across directions.

## Paired receipts

V1 retains its completed reference and the candidate's pre-reset `phone_mass` construction error. V2 uses the declared case payload before reset, checks realized simulated payload against that declaration and verifies the plan uses that same mass. Both v2 cases declare and realize .155 kg, share development seed `1154976095502900`, complete 480 steps and save 480 planned-support trace rows from command time 0 through 9.58 s. The simulation payload is not a physical mass measurement.

The v1/v2 reference acceptance, steady metrics, all/steady telemetry, planned-support trace and original trace compare **exactly equal**. The construction repair preserved the causal baseline.

| Pilot metric | Reference | Planned support |
| --- | ---: | ---: |
| Full-episode velocity RMSE, m/s | .017963 | .020554 |
| Whole-cycle velocity-error ripple, m/s | .017897 | .018724 |
| Peak path error, m | .017752 | .021440 |
| Saturation fraction | .003446 | .036918 |
| Peak tilt, rad | .043795 | .034409 |
| Backward progress, m; requested .096 m | .082148 | .100305 |

Both fail velocity and duration acceptance. The candidate saturation remains below the original acceptance limit but increases about 10.7 times; it contradicts the predicted improvement without higher actuator demand. Whole-cycle metrics use `6.4 < sample_time <= 9.6`.

Saved command-time traces over `6.4 <= command_time < 9.6` show the intended nominal correction: candidate raw forces are nonnegative and maximum clipped moment residual is about 1.3e-15 N m. The reference has negative raw forces in 14.4% of these rows, minimum -.597 N, and maximum clipped moment residual .112 N m. Actual scheduled-stance contact still deteriorates at the front: FL loaded fraction .944 -> .808 and FR .904 -> .823. Rear fractions improve only from about .797 to .822. The load model's feasibility and actual contact sufficiency are therefore separate findings.

An additional static estimate from saved geometric targets and clipped loads gives maximum hip/knee support torque about .517/.515 N m for reference and .555/.574 N m for candidate. Neither exceeds the nominal .588 N m cap in this estimate, but candidate knee headroom is only .014 N m. This supports investigating transfer dynamics and actuator demand; it does not justify raising an uncalibrated cap.

## Provenance and remaining coverage

Read-only WSL checks found all 55 source/CAD hashes unchanged in all three receipts, with identity `8793d43d546c95c6fd695860305f96a0627e49be9ec81779e313b63d1b92e8c1`. All 11 static/v1 helper hashes and all 13 v2 helper hashes match their current recorded files.

| Receipt | SHA-256 |
| --- | --- |
| `dev_support_static_01.json` | `d2ca986b083e1d3c9e03ac8441c0546bc76b6e2bf05eba53bab4884a3f4aff10` |
| `dev_support_backward480_01.json` | `bd76c94e06c026e3eb00903a2dcbf8af0977b9efa1bce97bf6536cb98ce3c37e` |
| `dev_support_backward480_02.json` | `18b0b2ac700f308cb7b6f0b2b292f8e35c5fa314ef805e83b155744ffba2de90` |

V2 binds static controller/audit bytes and stores the static receipt digest. Its coverage check requires complete status and 12 rows but does not verify every requested command/payload against a passed static row, nor pin that receipt to an expected digest. The current pilot and proposed six-command 0/.155 scope are covered. Any broader payload request needs a new wrapper with explicit coverage validation; preserve v2 rather than editing it in place.

## MSI-SUPPORT-001 continuation

This extends [the existing support diagnosis](msi_support_diagnosis.md): nominal feasibility was corrected, while its sufficiency for dynamic contact and tracking was falsified in this pilot. The owning behavior remains the planned body shift and inherited load estimate. The applied scoped improvement is this evidence-bound review gate: inspect actual stance contact and actuator demand alongside planned moments before another expansion. It correctly rejects this pilot despite all nominal static gates passing. Preserve the failed initialization receipt and both completed measurements. The next diagnosis should explain front contact loss and increased saturation from these traces before choosing one further intervention; physical transfer remains unvalidated.
