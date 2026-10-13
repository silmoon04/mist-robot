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
import zipfile

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent))
from locomotion.acceptance import CRITERIA, VERSION
from locomotion.provenance import source_hashes, identity, CONTRACT

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
    if any(type(receipt[key]) is not int for key in ('steps', 'total_cases', 'passed_cases')):
        raise ValueError('Final receipt horizons and counts must be integers')
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
    if not all(type(v) in (float, int) and math.isfinite(v) for v in values):
        raise ValueError('Nonfinite or invalid velocity metrics')
    return {'strict_passes': sum(c['passed'] for c in cases), 'total': len(cases),
            'execution_errors': len(cases) - len(measured),
            'failed_flags': {name: sum(c['checks'][key] is False for c in measured) for name, key in FLAGS.items()},
            'unknown_flags': len(cases) - len(measured),
            'velocity_metric_cases': len(values),
            'velocity_rmse_median_m_s': statistics.median(values) if values else None,
            'velocity_rmse_max_m_s': max(values) if values else None}


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
    data = [summary[k]['velocity_rmse_median_m_s'] if summary[k]['velocity_rmse_median_m_s'] is not None else float('nan') for k in labels]
    axes[1].bar(labels, data, color=['#607d8b', '#3b79b7', '#cc8744'])
    for i, key in enumerate(labels):
        if summary[key]['velocity_rmse_median_m_s'] is None:
            axes[1].text(i, 0, 'No metrics', ha='center', va='bottom', fontsize=8)
    axes[1].axhline(CRITERIA['max_velocity_rmse_m_s'], color='#aa2222', linestyle='--',
                   label=f'Per-case threshold {CRITERIA["max_velocity_rmse_m_s"]} m/s')
    axes[1].set_ylabel('Median velocity RMSE (m/s)'); axes[1].legend(fontsize=8)
    fig.suptitle('Common MPU cases; single-seed candidates; simulation only', fontsize=11)
    fig.savefig(output, dpi=180); plt.close(fig)


def evidence_path(repo, value):
    """Resolve portable inventory paths without accepting paths outside the repo."""
    path = (repo / value).resolve()
    if not path.is_relative_to(repo.resolve()):
        raise ValueError('Evidence path escapes repository')
    return path


def validate_sources(hashes, repo):
    if not hashes:
        raise ValueError('Missing source inventory')
    for name, expected in hashes.items():
        if digest(evidence_path(repo, name)) != expected:
            raise ValueError(f'Source content hash mismatch: {name}')


def validate_periodic(receipt):
    """Training evaluator receipts have nested acceptance, not final_matrix rows."""
    if receipt.get('label') != 'periodic' or receipt.get('status') != 'simulation_evaluation_only_hardware_unvalidated':
        raise ValueError('Expected completed periodic training validation')
    episodes = receipt['episodes']
    if type(receipt['training_timesteps']) is not int or receipt['training_timesteps'] < 0:
        raise ValueError('Periodic training timesteps must be a nonnegative integer')
    if not episodes:
        raise ValueError('Empty periodic validation')
    declarations = [{k: row[k] for k in ('direction', 'command', 'terrain', 'payload', 'seed')}
                    for row in episodes]
    if identity(declarations) != receipt['suite_sha256']:
        raise ValueError('Periodic validation suite identity mismatch')
    if len({identity(row) for row in declarations}) != len(declarations):
        raise ValueError('Duplicate periodic validation cases')
    measured = []
    for row in episodes:
        acceptance = row['acceptance']
        if acceptance.get('criteria') != CRITERIA or acceptance.get('acceptance_version') != VERSION:
            raise ValueError('Periodic acceptance mismatch')
        checks = acceptance['checks']
        if set(FLAGS.values()) - set(checks) or any(type(v) is not bool for v in checks.values()):
            raise ValueError('Periodic checks must contain boolean acceptance flags')
        if type(acceptance['passed']) is not bool or acceptance['passed'] != all(checks.values()):
            raise ValueError('Periodic pass verdict disagrees with checks')
        if any(type(row[k]) is not bool for k in ('fell', 'terminated', 'truncated')):
            raise ValueError('Periodic episode state must be boolean')
        if checks['no_falls'] != (not row['fell']):
            raise ValueError('Periodic fall verdict disagrees with episode')
        measured.append(acceptance)
    eligible = all(row['passed'] for row in measured)
    falls = sum(row['fell'] for row in episodes) / len(episodes)
    if type(receipt['eligible']) is not bool or receipt['eligible'] != eligible:
        raise ValueError('Periodic eligibility disagrees with acceptance')
    if receipt['fall_fraction'] != falls:
        raise ValueError('Periodic fall fraction disagrees with episodes')
    result = summarize(measured)
    result.update(eligible=eligible, fall_fraction=falls, suite_sha256=receipt['suite_sha256'],
                  training_timesteps=receipt['training_timesteps'],
                  checkpoint_binding='not recorded by training evaluator; periodic validation is not an exact checkpoint test')
    return result


def validate_candidate(checkpoint, expected, algorithm, sources, repo):
    record = read(checkpoint.with_suffix('.provenance.json'))
    if digest(checkpoint) != expected['sha256'] or record['checkpoint_sha256'] != expected['sha256']:
        raise ValueError('Paused checkpoint content hash mismatch')
    if record['algorithm'] != algorithm or record['hardware_qualified'] is not False:
        raise ValueError('Paused checkpoint algorithm or hardware status mismatch')
    if identity(record['envelope']) != record['envelope_sha256']:
        raise ValueError('Paused checkpoint envelope identity mismatch')
    if record['envelope']['sources'] != sources or record['envelope']['contract'] != CONTRACT:
        raise ValueError('Paused checkpoint source or observation/action contract mismatch')
    validate_sources(record['envelope']['sources'], repo)
    if record['continuation_seed'] != expected['continuation_seed']:
        raise ValueError('Paused continuation seed mismatch')
    if record['replay_sha256'] != expected['replay_sha256']:
        raise ValueError('Paused replay identity mismatch')
    with zipfile.ZipFile(checkpoint) as archive:
        saved = json.loads(archive.read('data'))
    if saved['num_timesteps'] != expected['recorded_timesteps'] or saved['_n_updates'] != expected['optimizer_updates']:
        raise ValueError('Paused saved timestep or optimizer count mismatch')
    return record


def generate_paused(root=HERE, output_dir=None, final_receipts=None):
    """Report explicitly paused artifacts; optional final tests never select policies."""
    root = Path(root).resolve()
    repo = root.parent
    if output_dir is None:
        raise ValueError('Paused reports require a separate output directory')
    output_dir = Path(output_dir).resolve()
    if output_dir == root or output_dir.is_relative_to(root / 'runs') or output_dir.is_relative_to(root / 'handoff'):
        raise ValueError('Paused output must be outside protected runs and handoff evidence')
    if output_dir.exists():
        raise FileExistsError('Paused output already exists; choose a fresh directory')
    final_receipts = final_receipts or {}
    if set(final_receipts) - {'ppo', 'sac'}:
        raise ValueError('Only explicit PPO/SAC final receipts are supported')
    paths = {}
    def consume(path, expected=None):
        path = Path(path).resolve()
        actual = digest(path)
        if expected is not None and actual != expected:
            raise ValueError(f'Evidence content hash mismatch: {path}')
        paths[path] = actual
        return read(path)
    state = consume(root / 'handoff/PAUSED_STATE.json')
    if state.get('schema') != 1 or state.get('status') != 'paused_at_user_request':
        raise ValueError('Expected explicit paused handoff state')
    sources = consume(root / 'handoff/frozen_sources.json')
    if identity(sources) != state['source_fingerprint']:
        raise ValueError('Frozen source fingerprint mismatch')
    validate_sources(sources, repo)
    for name in sources:
        path = evidence_path(repo, name)
        paths[path] = sources[name]
    baseline_path = evidence_path(repo, state['baseline']['receipt'])
    baseline = consume(baseline_path)
    indexed_baseline = validate_cases(baseline)
    if baseline['source_hashes'] != sources or len(indexed_baseline) != state['baseline']['cases']:
        raise ValueError('Paused baseline source or case count mismatch')
    baseline_summary = summarize(list(indexed_baseline.values()))
    if baseline_summary['strict_passes'] != state['baseline']['passes'] or baseline_summary['failed_flags']['falls'] != state['baseline']['falls']:
        raise ValueError('Paused baseline summary disagrees with evidence')
    policies = {}
    final_tests = {}
    for algorithm in ('ppo', 'sac'):
        entry = state['checkpoints'][algorithm]
        if entry['final_checkpoint_written'] is not False or entry['final_summary_written'] is not False or entry['hardware_qualified'] is not False:
            raise ValueError('Handoff does not describe an unfinished paused candidate')
        checkpoint = evidence_path(repo, entry['path'])
        paths[checkpoint] = digest(checkpoint)
        sidecar = evidence_path(repo, entry['sidecar'])
        if sidecar != checkpoint.with_suffix('.provenance.json'):
            raise ValueError('Paused sidecar path mismatch')
        consume(sidecar, entry['sidecar_sha256'])
        record = validate_candidate(checkpoint, entry, algorithm, sources, repo)
        if entry['replay']:
            replay = evidence_path(repo, entry['replay'])
            paths[replay] = digest(replay)
            if paths[replay] != entry['replay_sha256']:
                raise ValueError('Paused replay content hash mismatch')
        periodic = [r for r in entry['validation'] if r['label'] == 'periodic']
        if len(periodic) != 1:
            raise ValueError('Expected one explicit completed periodic receipt')
        validation = periodic[0]
        measured = validate_periodic(consume(evidence_path(repo, validation['path']), validation['sha256']))
        for field, key in (('total', 'episodes'), ('strict_passes', 'strict_passes'), ('eligible', 'eligible'), ('fall_fraction', 'fall_fraction')):
            if measured[field] != validation[key]:
                raise ValueError('Paused periodic summary disagrees with evidence')
        if measured['training_timesteps'] != entry['recorded_timesteps']:
            raise ValueError('Paused periodic timestep mismatch')
        missing = []
        for filename in ('final.zip', 'training_summary.json'):
            path = checkpoint.parent / filename
            if path.exists():
                raise ValueError(f'Paused artifact is now present; use a completed run report: {path}')
            missing.append(path.relative_to(repo).as_posix())
        policies[algorithm.upper()] = {'status': 'training_paused_during_' + entry['interrupted_during'].replace(' ', '_'),
            'recorded_timesteps': entry['recorded_timesteps'], 'optimizer_updates': entry['optimizer_updates'],
            'missing_final_artifacts': missing, 'checkpoint': str(checkpoint), 'checkpoint_record': record,
            'periodic_validation': measured, 'final_test_status': 'not_supplied', 'hardware_qualified': False}
        if algorithm in final_receipts:
            receipt = consume(final_receipts[algorithm])
            indexed = validate_cases(receipt)
            if len(indexed) != 131 or any(row['env_kwargs']['sensor_mode'] != 'mpu6050' for row in indexed.values()):
                raise ValueError('Explicit final test requires all 131 MPU cases')
            expected_cases = [{k: v for k, v in case.items() if k != 'sensor_distribution_shift'}
                for case in baseline['ordered_resolved_cases'] if case['env_kwargs']['sensor_mode'] == 'mpu6050']
            actual_cases = [{k: v for k, v in case.items() if k != 'sensor_distribution_shift'}
                for case in receipt['ordered_resolved_cases']]
            if receipt['steps'] != 960 or actual_cases != expected_cases:
                raise ValueError('Final test horizon or ordered declarations differ from the frozen suite')
            if receipt['controller'] != algorithm or receipt['checkpoint_sha256'] != record['checkpoint_sha256'] or receipt['checkpoint_envelope_sha256'] != record['envelope_sha256'] or receipt['source_hashes'] != sources:
                raise ValueError('Final test source or exact paused checkpoint mismatch')
            if receipt['wrapper_sha256'] != digest(root / 'final_matrix.py'):
                raise ValueError('Final test wrapper content hash mismatch')
            paths[root / 'final_matrix.py'] = receipt['wrapper_sha256']
            declared = record['envelope']['experiment']['sensor']
            for case in receipt['ordered_resolved_cases']:
                shift = declared['mode'] != case['env_kwargs']['sensor_mode'] or declared['profile'] != case['resolved_sensor_profile']
                if case['sensor_distribution_shift'] != shift:
                    raise ValueError('Final test distribution-shift metadata mismatch')
            common = set(indexed) & set(indexed_baseline)
            if len(common) != 131 or any(normalize_environment(indexed[i]) != normalize_environment(indexed_baseline[i]) or indexed[i]['seed'] != indexed_baseline[i]['seed'] for i in common):
                raise ValueError('Final test cases differ from the untouched baseline suite')
            final_tests[algorithm.upper()] = {'summary': summarize(list(indexed.values())),
                'lineage': lineage(receipt, sources), 'receipt_checkpoint_path': receipt['checkpoint'],
                'verified_checkpoint_path': str(checkpoint), 'checkpoint_selection': False}
            policies[algorithm.upper()]['final_test_status'] = 'completed_explicit_receipt'
    summary = {'mode': 'paused', 'generated_utc': datetime.now(timezone.utc).isoformat(),
        'paused_at_utc': state['paused_at_utc'], 'hardware_qualified': False, 'acceptance_version': VERSION,
        'criteria': CRITERIA, 'source_fingerprint': state['source_fingerprint'], 'baseline': baseline_summary,
        'policies': policies, 'untouched_final_tests': final_tests, 'checkpoint_selection': False,
        'input_sha256': {str(p): value for p, value in paths.items()},
        'limitations': ['Periodic validation is completed; final training validation and summaries are unfinished.',
            'Periodic receipts record training timesteps but do not bind exact checkpoint bytes or source hashes.',
            'Untouched tests appear only when explicitly supplied and never qualify hardware or select checkpoints.',
            'One training seed per algorithm; simulation uses unmeasured actuator, mass and sensor approximations.']}
    lines = ['# Paused simulation results', '',
        'Training was paused during final validation. Completed periodic validations are reported below. '
        'The final training checkpoints and summaries are absent. Hardware walking remains unqualified.', '',
        f'Frozen source fingerprint: `{state["source_fingerprint"]}`. All inventory, checkpoint, sidecar and replay bytes were verified.', '',
        f'Baseline: {baseline_summary["strict_passes"]}/{baseline_summary["total"]} strict passes; {baseline_summary["failed_flags"]["falls"]} falls.', '',
        '| Candidate | Recorded transitions | Saved optimizer updates | Periodic passes / cases | Falls | Eligible | Untouched final test |',
        '| --- | ---: | ---: | ---: | ---: | --- | --- |']
    for name, policy in policies.items():
        measured = policy['periodic_validation']
        final = final_tests.get(name)
        test = f'{final["summary"]["strict_passes"]}/{final["summary"]["total"]} strict passes' if final else 'Not supplied'
        lines.append(f'| {name} | {policy["recorded_timesteps"]} | {policy["optimizer_updates"]} | {measured["strict_passes"]}/{measured["total"]} | {measured["failed_flags"]["falls"]} | {measured["eligible"]} | {test} |')
    lines += ['', 'Periodic validation uses development validation cases. Its producer does not record checkpoint or source hashes, '
        'so these receipts cannot establish the performance of exact saved checkpoint bytes. '
        'The handoff hashes verify the preserved receipts and candidate artifacts separately.', '',
        'Untouched final results, when explicitly supplied, are verified against the exact handoff checkpoint, '
        'frozen sources, final-test wrapper and all 131 MPU baseline cases. They are reported separately and do not select a checkpoint.', '',
        'Missing final training artifacts:', '']
    lines += [f'- `{path}`' for policy in policies.values() for path in policy['missing_final_artifacts']]
    lines += ['', 'The saved PPO checkpoint precedes the final rollout optimizer update. '
        'Recorded transitions and saved optimizer updates do not represent completed training. '
        'Resume reseeds environments; it does not restore uninterrupted live rollout or RNG state.', '',
        'Neither these periodic validations nor an untouched simulation test establishes calibrated actuators, sensors, '
        'whole-robot contact equivalence or physical walking. See `result_summary.json` for input hashes and receipt lineage.']
    if any(digest(path) != expected for path, expected in paths.items()):
        raise RuntimeError('Reporting inputs changed while reading')
    if any((evidence_path(repo, entry['path']).parent / name).exists() for entry in state['checkpoints'].values() for name in ('final.zip', 'training_summary.json')):
        raise RuntimeError('Paused final artifacts changed while reading')
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / 'result_summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    (output_dir / 'RESULTS.md').write_text('\n'.join(lines) + '\n')
    return summary


def generate(root=HERE, *, mode='complete', output_dir=None, final_receipts=None):
    if mode == 'paused':
        return generate_paused(root, output_dir, final_receipts)
    if mode != 'complete' or output_dir is not None or final_receipts:
        raise ValueError('Paused report options require mode=paused')
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
        median = data['velocity_rmse_median_m_s']
        metric = f'{median:.6f}' if median is not None else 'Unavailable'
        lines.append(f'| {name} | {data["strict_passes"]}/{data["total"]} | {f["falls"]} | {f["nonfoot_contact"]} | {f["sensor_fault"]} | {f["velocity"]} | {f["path"]} | {metric} |')
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['complete', 'paused'], default='complete')
    parser.add_argument('--output-dir', type=Path, help='Fresh directory for a paused report')
    parser.add_argument('--ppo-final', type=Path, help='Explicit completed 131-case PPO final_matrix receipt')
    parser.add_argument('--sac-final', type=Path, help='Explicit completed 131-case SAC final_matrix receipt')
    args = parser.parse_args()
    finals = {algo: path for algo, path in (('ppo', args.ppo_final), ('sac', args.sac_final)) if path}
    if args.mode == 'paused' and args.output_dir is None:
        parser.error('--mode paused requires --output-dir')
    if args.mode == 'complete' and (args.output_dir or finals):
        parser.error('--output-dir and explicit final receipts require --mode paused')
    result = generate(mode=args.mode, output_dir=args.output_dir, final_receipts=finals)
    if args.mode == 'paused':
        def counts(measured):
            return {key: measured[key] for key in ('strict_passes', 'total', 'execution_errors')}
        policies = {}
        for name, policy in result['policies'].items():
            policies[name] = {'status': policy['status'],
                              'periodic_validation': counts(policy['periodic_validation']),
                              'final_test_status': policy['final_test_status']}
            if name in result['untouched_final_tests']:
                policies[name]['untouched_final_test'] = counts(result['untouched_final_tests'][name]['summary'])
        output = args.output_dir.resolve()
        result = {'mode': 'paused', 'status': 'report_written',
                  'output_files': {name: str(output / name) for name in ('result_summary.json', 'RESULTS.md')},
                  'hardware_qualified': result['hardware_qualified'],
                  'checkpoint_selection': result['checkpoint_selection'],
                  'baseline': counts(result['baseline']), 'policies': policies}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
