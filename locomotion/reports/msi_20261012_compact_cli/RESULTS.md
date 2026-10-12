# Paused simulation results

Training was paused during final validation. Completed periodic validations are reported below. The final training checkpoints and summaries are absent. Hardware walking remains unqualified.

Frozen source fingerprint: `8793d43d546c95c6fd695860305f96a0627e49be9ec81779e313b63d1b92e8c1`. All inventory, checkpoint, sidecar and replay bytes were verified.

Baseline: 20/239 strict passes; 0 falls.

| Candidate | Recorded transitions | Saved optimizer updates | Periodic passes / cases | Falls | Eligible | Untouched final test |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| PPO | 51200 | 245 | 6/72 | 0 | False | 12/131 strict passes |
| SAC | 51200 | 25343 | 0/72 | 0 | False | 0/131 strict passes |

Periodic validation uses development validation cases. Its producer does not record checkpoint or source hashes, so these receipts cannot establish the performance of exact saved checkpoint bytes. The handoff hashes verify the preserved receipts and candidate artifacts separately.

Untouched final results, when explicitly supplied, are verified against the exact handoff checkpoint, frozen sources, final-test wrapper and all 131 MPU baseline cases. They are reported separately and do not select a checkpoint.

Missing final training artifacts:

- `locomotion/runs/ppo_51200/final.zip`
- `locomotion/runs/ppo_51200/training_summary.json`
- `locomotion/runs/sac_51200/final.zip`
- `locomotion/runs/sac_51200/training_summary.json`

The saved PPO checkpoint precedes the final rollout optimizer update. Recorded transitions and saved optimizer updates do not represent completed training. Resume reseeds environments; it does not restore uninterrupted live rollout or RNG state.

Neither these periodic validations nor an untouched simulation test establishes calibrated actuators, sensors, whole-robot contact equivalence or physical walking. See `result_summary.json` for input hashes and receipt lineage.
