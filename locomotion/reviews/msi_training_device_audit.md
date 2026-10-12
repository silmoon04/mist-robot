# MSI matched CPU/CUDA training audit

Audited 12 October 2026 against the completed Linux receipts in `/home/hssil/mist-locomotion-msi/repo/locomotion/runs/msi_20261012/training_devices_8192`. All four jobs completed with exit code 0, exactly 8192 fresh transitions and no interruption. CPU was faster for both algorithms in this screen. Use CPU for this current small-network, two-worker configuration; this single pair per algorithm does not establish a general device ranking.

| Algorithm | Policy device | Subprocess wall, s | Trainer elapsed, s | Initial + final evaluation, s | Trainer excluding evaluation estimate, s | Wall transitions/s | SB3 update counter |
|---|---|---:|---:|---:|---:|---:|---:|
| PPO | CPU | 177.41 | 169.14 | 145.16 | 23.98 | 46.18 | 40 |
| PPO | CUDA | 269.75 | 264.03 | 221.91 | 42.13 | 30.37 | 40 |
| SAC | CPU | 192.50 | 185.14 | 146.21 | 38.93 | 42.56 | 3840 |
| SAC | CUDA | 284.16 | 278.34 | 208.68 | 69.66 | 28.83 | 3840 |

CUDA took 1.52 times the PPO CPU wall time and 1.48 times the SAC CPU wall time. After subtracting recorded evaluation durations, CUDA took 1.76 times the PPO CPU duration and 1.79 times the SAC CPU duration. That subtraction retains rollout, optimization, model construction and checkpoint/replay writing; it is an estimate of training work outside evaluation, not an optimizer-only measurement. Subprocess wall time additionally includes Python imports, device initialization and environment startup.

The PPO counter is 8 completed rollouts × 5 epochs = 40 SB3 `_n_updates`; it is not a minibatch optimizer-step count. SAC records 3840 gradient steps after its 512-transition learning-start threshold, collecting two transitions per vector step. Both match this trainer configuration. The counts should be compared within an algorithm.

The same interpreter ran all jobs: `/home/hssil/mist-locomotion-msi/venv-cuda/bin/python`, Python 3.11.16, Torch 2.8.0+cu126, Stable-Baselines3 2.7.1, Gymnasium 1.2.3, PyBullet 3.2.7 and NumPy 2.2.6. The platform was WSL2 Linux 6.18.33.2. The verified CUDA device was the NVIDIA GeForce RTX 4080 Laptop GPU, with 12878086144 bytes reported device memory and driver 591.74. `nvidia-smi` reported 12282 MiB and no power-limit value. PyBullet physics remained on CPU for every job.

Jobs ran sequentially in PPO CPU, PPO CUDA, SAC CPU, SAC CUDA order. Within each algorithm, every trainer argument except policy device and output path matched, both experiment envelopes matched, and effective model parameters matched after excluding device. Common settings included seed 630042, two environments, one Torch thread, `[64,64]` MLPs, batch size 64, mixed randomized training terrain and MPU6050 sensor simulation. All jobs were labelled `novice_pipeline_smoke_test`; none resumed a checkpoint.

Every initial and final validation completed 18 cases and 17280 steps, for 34560 validation steps per job. The independent check recomputed each suite hash from case direction, command, terrain, payload and seed, and verified flat terrain, payloads 0/.155, the nine declared command directions and seeds 1000000 through 1000017. There were exactly two evaluations per job, at training timesteps 0 and 8192. The final evaluation receipt matched the training summary. No validation reward, acceptance score or untouched final-test score was used for the device recommendation or policy selection.

| Job | Started UTC | Completed UTC | Initial validation, s | Final validation, s |
|---|---|---|---:|---:|
| PPO CPU | 20:27:46.715035 | 20:30:44.126793 | 77.5926 | 67.5664 |
| PPO CUDA | 20:30:44.150960 | 20:35:13.901362 | 117.6416 | 104.2656 |
| SAC CPU | 20:35:13.925496 | 20:38:26.422170 | 72.1537 | 74.0586 |
| SAC CUDA | 20:38:26.496503 | 20:43:10.655581 | 110.3491 | 98.3343 |

The job timestamps confirm no overlap. The report spans 20:27:42.821967 through 20:43:10.720504 UTC on 12 October 2026; the four job wall durations sum to 923.81 seconds. Although the whole screen lasted about 15.5 minutes, each run lasted only about 3–5 minutes and changed algorithm/device. There was no sustained thermal test, temperature trace, repeated pairing or reversed-order pairing. No 15-minute thermal-capacity conclusion follows from this batch. Four-worker training was not measured here. CUDA evaluation was slower as well as the work outside evaluation; separating transfer, prediction, physics and optimizer costs would require different instrumentation.

Independent provenance checks passed for every job: current Linux source/CAD hashes equalled the frozen manifest; run source maps and source envelopes matched; envelope identities recomputed correctly; final checkpoint sidecars matched each run envelope; checkpoint bytes matched their sidecar hashes; both SAC replay buffers matched their bound replay hashes; and metric-envelope snapshots matched run receipts. Source hashes still matched after reading all jobs. The Windows checkout has the same source bytes after normalizing path separators, and its benchmark-helper bytes match the executed helper. The wrapper report is complete and records successful post-run source verification.

The following SHA-256 values were independently checked:

```text
Frozen source identity:
8793d43d546c95c6fd695860305f96a0627e49be9ec81779e313b63d1b92e8c1
Executed benchmark_training_devices.py:
8a0c5b63272c9e98dff375eae1b70ea89d7312a6089da0c85a4284f384704dcc
benchmark_report.json:
817850b50badf00613774639d1be896bb38453c01cfe2391b1997cfda6c8bf0a
Validation suite (all eight evaluations):
0b83926d99659107ad1175150fd1d9ba0d73f333727874b8fe8fedf69e692d9e

PPO envelope (CPU and CUDA):
7fc43e2e75103e861116a838058c08961a9a2a3fb41f11e564c69da3ae6335e4
PPO CPU final.zip:
57d6a463a8ce6848a34df18f8b94ec158a005f78c4ff53b5a649f0e27eb8761f
PPO CUDA final.zip:
6af827291b675d71d087c08a9477544d7b5c2871401799094903e6fc645fc341

SAC envelope (CPU and CUDA):
bfe0d4f4509e44149c663bde5b7f4cb0b497714dfd7e13bc09ad4aed1a938108
SAC CPU final.zip:
acd02e34dadf596e253d04656a6e54934e9693bb0fa89ae7a889f63b19cbd494
SAC CPU final_replay_buffer.pkl:
6f617aaf69f90fd61c7175f1b94abb7178e8b1763c126f8ad0d74f8b9ef9ac10
SAC CUDA final.zip:
59994adbbd6b2e7aa8ab57619f59ead06a69ba99e9e8ed5d06d2511bf56a1304
SAC CUDA final_replay_buffer.pkl:
2c243b9974a3a1eb01672b41517dd69cbbde370382a39919127bdff710afa8c7
```

This audit used file reads, SHA-256 checks and the standard-library provenance verifier. It launched no simulator, training process or additional benchmark, and changed only this review document. The result establishes completion and measured throughput for these bounded smoke jobs; walking accuracy and hardware transfer remain unqualified.
