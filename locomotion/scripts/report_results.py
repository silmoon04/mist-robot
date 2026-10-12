#!/usr/bin/env python3
"""Report completed receipts without rewriting evidence or changing acceptance."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent))
from locomotion.acceptance import CRITERIA, VERSION
from locomotion.provenance import source_hashes, identity

RECEIPTS = {'baseline': 'final_baseline_all.json', 'PPO': 'final_ppo_mpu.json', 'SAC': 'final_sac_mpu.json'}
FLAGS = {'falls': 'no_falls', 'body_contact': 'no_body_ground_contact',
         'nonfoot_contact': 'no_nonfoot_ground_contact', 'sensor_fault': 'no_sensor_fault',
         'velocity': 'velocity', 'path': 'path', 'duration': 'duration', 'complete': 'complete',
         'progress': 'progress', 'yaw': 'yaw', 'yaw_rate': 'yaw_rate', 'tilt': 'tilt',
         'tracking': 'tracking', 'saturation': 'saturation', 'finite': 'finite'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(), parse_constant=lambda s: (_ for _ in ()).throw(ValueError(f'Nonfinite JSON: {s}')))


def validate_cases(receipt):
    # Explicit final_matrix schema. Sensitivity plan/executor receipts are different.
    if receipt.get('schema') != 1 or receipt.get('purpose') != 'untouched final simulation test; no checkpoint selection':
        raise ValueError('Expected final_matrix schema 1 receipt')
    cases = receipt['results']
    resolved = receipt['ordered_resolved_cases']
    if receipt.get('criteria') != CRITERIA:
        raise ValueError('Receipt acceptance criteria differ from fixed thresholds')
    expected_suite = identity({'criteria': receipt['criteria'], 'cases': resolved, 'steps': receipt['steps']})
    if receipt['suite_sha256'] != expected_suite:
        raise ValueError('Resolved suite identity mismatch')
    for key in ('wrapper_sha256', 'suite_sha256'):
        if len(receipt[key]) != 64 or any(c not in '0123456789abcdef' for c in receipt[key]):
            raise ValueError('Malformed wrapper or suite hash')
    if not receipt['source_hashes'] or receipt['steps'] < 960:
        raise ValueError('Missing source identity or acceptance horizon')
    if len(cases) != len(resolved) or receipt['total_cases'] != len(cases):
        raise ValueError('Receipt total disagrees with ordered suite/results')
    if receipt['passed_cases'] != sum(c.get('passed') is True for c in cases):
        raise ValueError('Receipt pass count disagrees with results')
    if len({c['case_id'] for c in cases}) != len(cases):
        raise ValueError('Duplicate case IDs')
    from locomotion.sensor_sim import SimulatedIMU
    for case, declaration in zip(cases, resolved):
        for key in ('case_id', 'command_name', 'seed', 'status', 'env_kwargs'):
            if case[key] != declaration[key]:
                raise ValueError(f'Ordered case metadata mismatch: {case["case_id"]} {key}')
        if declaration['steps'] != receipt['steps']:
            raise ValueError('Case horizon differs from suite horizon')
        kwargs = declaration['env_kwargs']
        profile = SimulatedIMU(kwargs['sensor_mode'], kwargs.get('sensor_profile')).profile
        if declaration['resolved_sensor_profile'] != profile:
            raise ValueError('Resolved sensor profile disagrees with case settings')
        if type(declaration['sensor_distribution_shift']) is not bool:
            raise ValueError('Distribution-shift marker must be boolean')
        if 'execution_error' in case:
            if case.get('passed') is not False:
                raise ValueError('Execution error cannot pass')
            continue
        if case.get('criteria') != CRITERIA or case.get('acceptance_version') != VERSION:
            raise ValueError(f'Acceptance mismatch: {case["case_id"]}')
        if case.get('source_hashes') != receipt['source_hashes']:
            raise ValueError('Per-case source identity differs from suite')
        checks = case['checks']
        if not checks or any(type(v) is not bool for v in checks.values()):
            raise ValueError('Checks must be boolean')
        if type(case.get('passed')) is not bool or case['passed'] != all(checks.values()):
            raise ValueError('Pass verdict disagrees with checks')
        if set(FLAGS.values()) - set(checks):
            raise ValueError('Required acceptance flags absent')
    return {c['case_id']: c for c in cases}


def summarize(cases):
    if not cases:
        raise ValueError('No comparable cases')
    measured = [c for c in cases if 'execution_error' not in c]
    values = [c['metrics']['body_velocity_rmse_m_s'] for c in measured]
    if not values or not all(isinstance(v, (float, int)) and math.isfinite(v) for v in values):
        raise ValueError('No finite velocity metrics')
    return {'strict_passes': sum(c['passed'] for c in cases), 'total': len(cases),
            'execution_errors': len(cases) - len(measured),
            'failed_flags': {name: sum(c['checks'][key] is False for c in measured) for name, key in FLAGS.items()},
            'unknown_flags': len(cases) - len(measured),
            'velocity_metric_cases': len(values),
            'velocity_rmse_median_m_s': statistics.median(values),
            'velocity_rmse_max_m_s': max(values)}


def normalize_environment(case):
    # Explicit default sensor settings and an omitted default are equivalent.
    from locomotion.sensor_sim import SENSOR_PROFILES
    kwargs = dict(case['env_kwargs'])
    profile = dict(SENSOR_PROFILES.get(kwargs['sensor_mode'], {}))
    profile.update(kwargs.pop('sensor_profile', None) or {})
    kwargs['effective_sensor_profile'] = profile
    return kwargs


def lineage(receipt, current):
    hashes = receipt.get('source_hashes', {})
    return {'source_hashes': hashes, 'checkpoint_sha256': receipt.get('checkpoint_sha256'),
            'wrapper_sha256': receipt['wrapper_sha256'], 'suite_sha256': receipt['suite_sha256'],
            'checkpoint_envelope_sha256': receipt.get('checkpoint_envelope_sha256'),
            'ordered_resolved_cases': receipt['ordered_resolved_cases'],
            'changed_from_current': {name: {'receipt': value, 'current': current.get(name)}
                                     for name, value in hashes.items() if current.get(name) != value},
            'current_dependencies_absent_from_receipt': sorted(set(current) - set(hashes))}


def plot(summary, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    labels = list(summary)
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), constrained_layout=True)
    passed = [summary[k]['strict_passes'] for k in labels]
    totals = [summary[k]['total'] for k in labels]
    axes[0].bar(labels, passed, color=['#607d8b', '#3b79b7', '#cc8744'])
    axes[0].set_ylim(0, max(totals)); axes[0].set_ylabel('Cases passing every fixed check')
    for i, (p, n) in enumerate(zip(passed, totals)):
        axes[0].text(i, p + max(totals)*.025, f'{p}/{n}', ha='center')
    data = [summary[k]['velocity_rmse_median_m_s'] for k in labels]
    axes[1].bar(labels, data, color=['#607d8b', '#3b79b7', '#cc8744'])
    axes[1].axhline(CRITERIA['max_velocity_rmse_m_s'], color='#aa2222', linestyle='--',
                   label=f'Per-case threshold {CRITERIA["max_velocity_rmse_m_s"]} m/s')
    axes[1].set_ylabel('Median velocity RMSE (m/s)'); axes[1].legend(fontsize=8)
    fig.suptitle('Common MPU cases; single-seed candidates; simulation only', fontsize=11)
    fig.savefig(output, dpi=180); plt.close(fig)


def generate(root=HERE):
    runs = root / 'runs'
    paths = [runs / n for n in RECEIPTS.values()]
    paths += [runs / f'{algo}_51200' / 'training_summary.json' for algo in ('ppo', 'sac')]
    paths += [runs / 'cpu_benchmark.json', runs / 'leg_check.json', runs / 'mujoco_comparison.json']
    lineage_paths = sorted(set(runs.rglob('*.provenance.json')) | set(runs.rglob('*migration*.json')))
    paths += lineage_paths
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        raise FileNotFoundError('Final reporting inputs incomplete:\n' + '\n'.join(missing))
    frozen = {str(p.relative_to(root)): digest(p) for p in paths}
    receipts = {name: read(runs / file) for name, file in RECEIPTS.items()}
    indexed = {name: validate_cases(r) for name, r in receipts.items()}
    if len(indexed['baseline']) != 239:
        raise ValueError('Baseline requires the complete 239-case all-sensor receipt')
    for name in ('PPO', 'SAC'):
        if len(indexed[name]) != 131 or any(c['env_kwargs']['sensor_mode'] != 'mpu6050' for c in indexed[name].values()):
            raise ValueError(f'{name} requires the complete 131-case MPU receipt')
    common = set.intersection(*(set(c) for c in indexed.values()))
    common = sorted(i for i in common if indexed['baseline'][i]['env_kwargs']['sensor_mode'] == 'mpu6050')
    if len(common) != 131:
        raise ValueError(f'Expected 131 common MPU cases, found {len(common)}')
    mismatch = {i: {name: normalize_environment(indexed[name][i]) for name in indexed}
                for i in common if any(normalize_environment(indexed[name][i]) != normalize_environment(indexed['baseline'][i])
                                       or indexed[name][i]['seed'] != indexed['baseline'][i]['seed'] for name in ('PPO', 'SAC'))}
    aggregates = {name: summarize([cases[i] for i in common]) for name, cases in indexed.items()}
    all_cases = {name: summarize(list(cases.values())) for name, cases in indexed.items()}
    training = {algo.upper(): read(runs / f'{algo}_51200' / 'training_summary.json') for algo in ('ppo', 'sac')}
    for name, record in training.items():
        if record.get('interrupted') or record.get('actual_additional_timesteps') != 51200:
            raise ValueError(f'{name} training is incomplete or has an unexpected budget')
    checkpoint_records = {}
    for name in ('PPO', 'SAC'):
        checkpoint = Path(receipts[name]['checkpoint'])
        sidecar = checkpoint.with_suffix('.provenance.json')
        record = read(sidecar)
        if digest(checkpoint) != receipts[name]['checkpoint_sha256'] or record['checkpoint_sha256'] != receipts[name]['checkpoint_sha256']:
            raise ValueError('Final matrix checkpoint hash mismatch')
        if identity(record['envelope']) != record['envelope_sha256'] or record['envelope_sha256'] != receipts[name]['checkpoint_envelope_sha256']:
            raise ValueError('Final matrix checkpoint envelope mismatch')
        if record['algorithm'] != name.lower():
            raise ValueError('Checkpoint algorithm mismatch')
        declared = record['envelope']['experiment']['sensor']
        for case in receipts[name]['ordered_resolved_cases']:
            shift = declared['mode'] != case['env_kwargs']['sensor_mode'] or declared['profile'] != case['resolved_sensor_profile']
            if case['sensor_distribution_shift'] != shift:
                raise ValueError('Checkpoint distribution-shift metadata mismatch')
        checkpoint_records[name] = record
    current = source_hashes()
    benchmark = read(runs / 'cpu_benchmark.json')
    summary = {'generated_utc': datetime.now(timezone.utc).isoformat(), 'hardware_qualified': False,
               'acceptance_version': VERSION, 'criteria': CRITERIA, 'input_sha256': frozen,
               'common_mpu_case_ids': common, 'common_mpu': aggregates, 'all_receipt_cases': all_cases,
               'environment_mismatches': mismatch, 'training': training,
               'lineage': {name: lineage(r, current) for name, r in receipts.items()},
               'selected_checkpoint_records': checkpoint_records,
               'checkpoint_lineage_records': {str(p.relative_to(root)): read(p) for p in lineage_paths},
               'cpu_benchmark': benchmark,
               'queue': {'status': 'prepared_not_scheduled', 'jobs': 6, 'steps_per_job': 1001472},
               'limitations': ['One training seed per algorithm, 51200 transitions; convergence not established',
                               'Source/checkpoint receipt lineage preserved; differences are not silently normalized',
                               'Synthetic actuators, mass and sensors; hardware calibration and walking unqualified']}
    lines = ['# Measured simulation results', '',
             'These are completed simulation receipts for the IK baseline and two 51,200-transition learned candidates. '
             'Each algorithm used one training seed. This budget does not establish convergence, and hardware walking remains unqualified.', '',
             f'Acceptance is `{VERSION}` with fixed thresholds. The comparison uses {len(common)} common MPU case IDs; effective environments and seeds are audited below.', '']
    if mismatch:
        lines.append(f'**Environment audit found {len(mismatch)} common IDs with different effective settings or seeds. '
                     'The table is an ID-matched comparison; those mismatches prevent a fully matched experiment claim. '
                     'See `runs/result_summary.json` for the exact settings.**')
        lines.append('')
    lines += ['| Controller | Strict passes / cases | Falls | Nonfoot contact | Sensor faults | Velocity failures | Path failures | Median velocity RMSE m/s |',
              '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for name, data in aggregates.items():
        f = data['failed_flags']
        lines.append(f'| {name} | {data["strict_passes"]}/{data["total"]} | {f["falls"]} | {f["nonfoot_contact"]} | {f["sensor_fault"]} | {f["velocity"]} | {f["path"]} | {data["velocity_rmse_median_m_s"]:.6f} |')
    lines += ['', 'Failure columns overlap: one case can fail several checks. Execution errors have unknown metric flags, recorded separately in the JSON summary. Strict passes require every check, including complete 19.2-second duration, finite metrics, progress, yaw, tilt, tracking and saturation. Counts do not turn a failed controller into a qualified one.', '',
              '![Common MPU comparison](runs/result_comparison.png)', '',
              'The left panel counts strict case passes. The right panel shows median velocity RMSE; its dashed line is the fixed per-case 0.015 m/s threshold. A median below that line would not establish that every case passes.', '',
              '## Scope and training receipts', '']
    for name, data in all_cases.items():
        lines.append(f'- {name} full receipt: {data["strict_passes"]}/{data["total"]} strict passes. Baseline-only phone/open-loop cases are excluded from the common MPU table.')
    for name, data in training.items():
        lines.append(f'- {name}: {data["actual_additional_timesteps"]:,} actual transitions, {data["elapsed_seconds_including_evaluation"]:.1f} seconds including evaluation, {data["end_to_end_timesteps_per_second"]:.2f} end-to-end transitions/s. See `runs/{name.lower()}_51200/training_summary.json` for optimizer and validation details.')
    lines += ['', 'The six prepared PPO/SAC jobs use matched seeds and 1,001,472 transitions per job. They are prepared, not scheduled or completed. Validation selects checkpoints; final receipts use their recorded held-out cases. A single candidate per algorithm cannot establish an algorithm ranking across seeds.', '',
              '## CPU throughput and model checks', '',
              '| CPU workers | Transitions/s | Startup seconds |', '| ---: | ---: | ---: |']
    for row in benchmark['results']:
        lines.append(f'| {row["workers"]} | {row["transitions_per_second"]:.2f} | {row["startup_seconds"]:.2f} |')
    lines += ['', 'This short PyBullet CPU rollout benchmark uses zero residual actions. It excludes policy optimization and is not a sustained thermal measurement or a prediction of queue runtime.', '',
              'Single-leg tracking uses synthetic downward toe force without added payload inertia. The bounded servo response, gains and thermal model are estimates. The MuJoCo receipt checks fixed-leg mass/FK and rigid-body trajectories against PyBullet; it does not validate full-robot contact, real servo behavior or GPU training.', '',
              '## Evidence lineage', '',
              'Raw receipts are unchanged. `runs/result_summary.json` retains their SHA-256 hashes, source maps, checkpoint hashes and differences from the current source tree. The baseline may precede a serializer-only fix; copied policy weights may have a receipt migration. Those are lineage differences, not newly measured physics. Inspect migration records beside the checkpoints before claiming identical source provenance.', '',
              'See [RESEARCH.md](RESEARCH.md) for primary simulator, actuator and training references, and [UPGRADE.md](UPGRADE.md) for measured-versus-proposed machine settings. Further work requires matched multi-seed training, failure analysis, measured dimensions/masses/actuators/sensor timing, then supported hardware stance and load tests.']
    if {str(p.relative_to(root)): digest(p) for p in paths} != frozen:
        raise RuntimeError('Reporting inputs changed while reading; wait until receipts are immutable')
    plot(aggregates, runs / 'result_comparison.png')
    (runs / 'result_summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    (root / 'RESULTS.md').write_text('\n'.join(lines) + '\n')
    return aggregates


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(generate(), indent=2))


if __name__ == '__main__':
    main()
