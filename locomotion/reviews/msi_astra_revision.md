# MSI batch: Astra revision

Reviewed and revised 12 October 2026 against `msi_astra_critique.md`, with a subsequent parent-runtime follow-up. This pass addresses its two P2 findings and the paused reporter's excessive stdout. The parent confirmed that the relevant helper was idle before each edit. The Windows repository is the edited copy; the parent owns synchronization into the WSL runtime copy.

## Changes and checks

The development collector finding and its wrapper recurrence below share the local tracking ID **MSI-DEV-CASE-COLLECTION**.

`scripts/dev_tracking_probe.py` now submits cases individually and collects futures as they finish. A worker exception becomes a case-specific `execution_error` row; later completed outcomes remain available. Every saved result list follows the declared case order, even when futures finish out of order. The receipt becomes `failed` and the command exits 1 if any case has an execution error. Tracking thresholds and the controller are unchanged.

On interruption, collection retains already completed futures, cancels queued futures where possible, and labels other cases `uncollected` or `not_submitted`. Already-running workers may finish after interruption, but their unavailable outcomes are explicitly marked in the saved receipt. This does not promise immediate termination of active simulation workers.

`scripts/test_dev_tracking_probe.py` adds two narrow regressions. A real single-worker process pool fails its first case and then successfully completes the second; both outcomes and their ordering survive. A controlled interruption retains a completed result, identifies a running result as uncollected, and cancels a queued future.

`handoff/MSI_SETUP.md` now resolves its bootstrap interpreter with `uv python find 3.11`. That exact command succeeded in Ubuntu and returned `/home/hssil/.local/share/uv/python/cpython-3.11-linux-x86_64-gnu/bin/python3.11`. The setup script itself did not require a change.

Checks run in this revision pass:

- `python -m unittest locomotion.scripts.test_dev_tracking_probe -v`: 2 passed.
- `python locomotion/scripts/test_report_results.py -q`: initially 16 passed; 17 passed after the stdout regression was added.
- `python -m unittest locomotion.scripts.test_benchmark_training_devices -q`: 1 passed.
- Independent SHA-256 comparison of every entry in `handoff/frozen_sources.json`: all 55 files matched, including the CAD dependencies.

The report and training benchmark helpers were reread alongside the critic's review. The initial static pass found no further must-fix defect. Parent execution then exposed the stdout issue described below. The paused report still requires explicit source/checkpoint evidence, and its default completed-report path still refuses absent final summaries. The benchmark remains a sequential fresh 8192-transition screen; its existing unit test covers the plan rather than runtime completion or timeout handling.

## Runtime follow-up and bounded retrospective

The parent reported 99 pytest tests plus 12 subtests, 21 hardware tests, and the initial 19 helper tests passing. The portable archive check passed with 213 files, 55 frozen sources, and a relocated reset. The saved policy finals completed all 131 cases each, with PPO 12 strict passes and SAC zero; the parent verified the expected source and suite identities. These outcomes were supplied for reporting and were not used to choose development controller changes.

**MSI-REPORT-STDOUT:** The first real paused report wrote its files correctly but printed roughly 110,000 tokens of evidence to stdout. `main()` printed the complete return value from paused generation, including checkpoint envelopes and resolved final-case lineage. After reading the bounded retrospective workflow, the scoped correction was placed in the existing report CLI and its regression suite.

Paused-mode stdout now contains output paths, report-write status, hardware/checkpoint-selection flags, policy status, and baseline/periodic/final pass, total and execution-error counts. Full evidence remains in `result_summary.json`; report generation and default complete-mode stdout retain their prior behavior. The new regression calls the real CLI entry point with and without the existing 131-case all-error final fixture. It requires stdout below 4096 characters, correct counts, and the preserved checkpoint envelope and all 131 resolved declarations in the saved file. All 17 report tests pass. A fresh independent check again confirmed all 55 frozen hashes.

The reusable lesson is local to this helper: console receipts should summarize file outputs and verdicts; evidence expansion belongs in the saved artifact. The regression owns that boundary. The independent Astra critic reviewed the stdout diff, reran all 17 report tests with `python -B`, and found no actionable issue. This repair is applied and validated.

## Recovery wrapper recurrence

**MSI-DEV-CASE-COLLECTION, recurrence:** The independent critic found that the new `scripts/dev_recovery_probe.py` copied the original `ProcessPoolExecutor.map` path instead of using the repaired collector. It could again discard later successful results after an earlier worker failed. The parent assigned this wrapper-only repair; the diagnosis owner was notified before editing. The already published `dev_tracking_probe.py` was left byte-identical.

The recovery wrapper now calls `original_probe.collect_cases(cases, workers, publish, runner=run_case)`. Its callback saves ordered partial results, including execution errors and interruption labels. Collected execution errors produce a `failed` receipt and exit 1. Other exceptions retain `interrupted_or_failed` with the exception type. The recovery interpolation and original acceptance are unchanged.

`scripts/test_dev_recovery_probe.py` calls the real wrapper entry point with a synthetic process worker that fails the first variant and completes the second. It verifies use of the shared collector, retained case identities and second result, failed receipt status, and nonzero exit. It exercises the existing collector rather than duplicating its scheduling algorithm. That regression and the two existing collector regressions passed together: `python -B -m unittest locomotion.scripts.test_dev_recovery_probe locomotion.scripts.test_dev_tracking_probe -v` (3 tests). All 55 frozen source/CAD hashes still match. The original probe hash remains `54915f674b74392cf24102b16c21562dbecff041167845a39644b171dbfbbc0e`.

The local lesson is to route experimental wrappers through the owning collector, with a wrapper-level regression proving that the delegation preserves receipt and exit behavior. A copied execution loop does not inherit fixes made to its original. The collector repair is applied and tested; this synthetic regression does not validate recovery kinematics or simulation performance.

## Reviewed bytes

SHA-256 hashes of the helper set after revision:

| Path under locomotion | SHA-256 |
| --- | --- |
| `scripts/setup_cuda.sh` | `0a112606629027b9a3c6af712558f50936a87666c92c974478bb9ce9d3d0851c` |
| `handoff/MSI_SETUP.md` | `391ecc80f34d715f0e452364778b8b24c5294096690abf9c6332452e0d20cecd` |
| `scripts/dev_tracking_probe.py` | `54915f674b74392cf24102b16c21562dbecff041167845a39644b171dbfbbc0e` |
| `scripts/test_dev_tracking_probe.py` | `e1528a6d9e6272fd7ab3551c648bea4effed302d0f8d247cfa44258cf8860910` |
| `scripts/dev_recovery_probe.py` | `39556a2584c7912354aba2e2693ecacca5adead101ef2b5c1bb2664510566907` |
| `scripts/test_dev_recovery_probe.py` | `c216cecee2a1e49a8f6d08f6c5b887606c6299b451352be2563a2cdb46d9e9af` |
| `scripts/report_results.py` | `b555d8b9b7213a936e8f36b3a34be0674a3aff86ea0db6680b0bdb010e7c8511` |
| `scripts/test_report_results.py` | `06e835a699ecc22dae8fe105853ebb0efde7bef5884ddf43e8dd5c29dce56354` |
| `scripts/benchmark_training_devices.py` | `8a0c5b63272c9e98dff375eae1b70ea89d7312a6089da0c85a4284f384704dcc` |
| `scripts/test_benchmark_training_devices.py` | `c7780f47389208f80f75c793b7040e2a24132755899329e524b60e13130b81fa` |

## Remaining evidence

The parent runtime results above supersede the earlier pending-tests checkpoint. This revision pass has not independently examined CUDA setup, completed CPU/CUDA training-pair receipts, or PyBullet telemetry. Those require separate parent evidence. This agent did not install packages, launch training, inspect new untouched final-policy results for development choices, edit fingerprinted source, migrate checkpoints, or change saved evidence.

The saved policies remain unqualified for walking. Simulated tracking, physical actuator dynamics, masses, sensor timing, hardware calibration, and whole-robot contact equivalence retain the limits described in the frozen handoff and independent reviews.
