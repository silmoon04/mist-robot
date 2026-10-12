# MSI frozen final receipt audit

Independent audit of the completed PPO/SAC receipts in `runs/msi_20261012/` and the explicit paused report in `reports/msi_20261012/`. No actionable findings. Code and evidence were read only; this review is the only file written by the reviewer.

| Candidate | Strict passes | Scored failures | Execution errors | Falls | Cases reaching 960 samples |
| --- | ---: | ---: | ---: | ---: | ---: |
| PPO | 12/131 | 119 | 0 | 0 | 130/131 |
| SAC | 0/131 | 131 | 0 | 0 | 130/131 |

Every PPO pass is a stop case. No moving case passed. Both runs retained the `sensor-dropout` case, which stopped at 336 samples with a sensor fault and failed the complete/duration checks. Completing the 131-case execution does not mean every episode reached its requested horizon or passed acceptance. There are no unknown metric flags or execution exceptions in either final receipt.

Both final logs end at 131/131 and contain the same counts as the receipts. The suite requests exactly 960 steps. All ordered case IDs, commands, seeds, status, environment settings and resolved sensor profiles match the frozen baseline's 131 MPU cases. The three policy sensor distribution shifts agree with each checkpoint's sensor envelope.

Verified all 55 frozen source/CAD bytes, candidate ZIPs and sidecars, the SAC replay buffer, checkpoint envelopes, wrapper and per-case sources. The ZIP metadata records 51,200 transitions and saved optimizer updates of 245 for PPO and 25,343 for SAC. Neither run has `final.zip` or `training_summary.json`.

| Evidence | SHA-256 |
| --- | --- |
| Frozen source inventory identity | `8793d43d546c95c6fd695860305f96a0627e49be9ec81779e313b63d1b92e8c1` |
| Final wrapper | `2a08fe84ee32a1fdb178df0aaed44868838c657bd9d1f6e2a5a0f507d0664918` |
| Both ordered policy suites | `f21c4f1ababd320dcf82328913353c117e9d1525a7dad7d65bdf8c1dc33a4506` |
| PPO final receipt | `7fb365ca048f740568334b355d85abe8413065b6cc5f83919fed784f4e9c1842` |
| SAC final receipt | `e261c0839159bc83360c4f550e952a55b795da9837e604542012f2bc43b39b49` |
| Paused report JSON | `545e8af27ae9464d84d7c491d8938793d3c915785c2d0437e1ad6aa8cb7bca6c` |

Independently recomputed passes, every failed flag, execution errors, unknown flags and velocity aggregates; all match the saved report. Verified every reported input digest after relocating recorded WSL paths to this repository. Recomputed the paused report in memory with filesystem writes mocked: it matches the saved report after excluding generation time and resolving the WSL/Windows path spelling. Periodic results remain separate at PPO 6/72 and SAC 0/72, both ineligible despite zero falls. Final tests do not select checkpoints, establish convergence, rank algorithms across seeds or qualify hardware. Hardware qualification and checkpoint selection remain false.

The reporter's 16 unittest tests passed independently before the real receipts arrived. The real-receipt audit added direct assertions for all identities, ordered declarations, samples, outcomes, report aggregates and unchanged input bytes. No policy or controller was tuned from these final results.
