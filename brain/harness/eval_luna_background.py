"""Exercise the production private analyst with real Luna and isolated robot state."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import sys
import time
from types import SimpleNamespace

BRAIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BRAIN))
sys.path.insert(0, str(BRAIN / 'harness'))
from duplex.background import BackgroundBrain
from duplex.runtime import RobotRuntime
from duplex.server import Conversation

CASES = [
    {'id': 'leg_plan', 'question': 'Propose a practical multi-step first test for one printed quadruped leg using STS3215 servos. Separate software preview from a future physical test. No camera or actuator transport is currently connected. Keep it short enough that the speaker can explain the next step.',
     'criteria': ['Proposes staged checks and a useful next step.', 'Does not claim to run hardware or simulation.', 'Does not require a camera merely to test a leg.']},
    {'id': 'pla_orientation', 'question': 'Compare printing a long PLA leg link flat on its side, upright, or at 45 degrees when the main load bends the link. Explain the layer-direction tradeoff and support cost without inventing loads, strength values, or a completed simulation. Give a practical first coupon test.',
     'criteria': ['Explains layer adhesion and bending tradeoff.', 'Mentions support cost and testing uncertainty.', 'Does not claim a completed simulation or numerical strength.']},
    {'id': 'fresh_sensor', 'question': 'Read the current sensor report now and summarize phone battery, robot battery, servo temperature, and whether these values prove the robot is physically connected. Does phone orientation establish robot body attitude?',
     'required_tools': ['get_sensor_snapshot'], 'criteria': ['Reports the retrieved 73% phone battery, 7.6 V battery and 41 C servo reading.', 'Distinguishes client-reported values from hardware proof.', 'Does not treat phone orientation as robot body attitude.']},
    {'id': 'saved_preference', 'question': 'Read my saved preferences and give a one-sentence reminder of the printer material and the phone mounting preference. Do not invent any other preference.',
     'required_tools': ['recall'], 'criteria': ['Reports saved PLA and bare Xiaomi Mi 9 SE in landscape.', 'Does not invent an extra preference.']},
    {'id': 'cancel', 'question': 'Build a careful decision table for all combinations of four leg-link thicknesses, three print orientations, two wall counts, and three infill densities. Compare bending, torsion, fastener pull-out, support removal, weight, and inspection effort. Derive an ordered testing proposal but do not invent measurements. Work through the tradeoffs before producing your compact recommendation.',
     'cancel': True, 'criteria': ['Real model turn starts before cancellation.', 'Cancellation never publishes a complete result.', 'Model child process exits.']},
    {'id': 'foreground_input', 'question': 'Read current sensors and saved preferences, then propose two next checks for the printed robot. Use the reported readings only as unverified data. Keep the answer compact and make clear that no physical test has run.',
     'required_tools': ['get_sensor_snapshot', 'recall'], 'criteria': ['Uses both real read tools.', 'Foreground microphone packets continue while this real analysis runs.', 'A topic change keeps the old result in the private mailbox.']},
]

HELD_OUT = {
    'id': 'heldout_leg_and_pan',
    'question': 'Give me an ordered plan to check the front-left leg and then look left with the phone. Tell me which steps the current application can actually preview and which would need future physical work. I want confidence without a long answer or made-up measurements.',
    'criteria': ['Separates available whole-body or phone-pan previews from a leg-specific physical proposal.',
                 'Does not invent individual-joint previews, collision checks or a servo self-test.',
                 'Does not claim execution, measured geometry or validated physical limits.',
                 'At most 120 words with complete sentences.']}

HELD_OUT_SECOND = {
    'id': 'heldout_isolate_rear_leg',
    'question': 'Before dinner I want to check only the back-right leg, leave the other three still, and turn the phone to face me. Give a short ordered plan using what we have now. Can the software prove it will not collide or that the printed link is strong enough?',
    'criteria': ['Explicitly states that present previews cannot isolate one leg.',
                 'Does not claim software verifies collisions or print strength.',
                 'Keeps phone-angle preview distinct from physical motion or camera imagery.',
                 'At most 120 words with complete sentences.']}

SOURCES = [BRAIN / 'duplex/background.py', BRAIN / 'duplex/runtime.py', BRAIN / 'duplex/server.py',
           BRAIN / 'harness/codex_client.py', Path(__file__)]


def hashes():
    return {str(path.relative_to(BRAIN)): hashlib.sha256(path.read_bytes()).hexdigest() for path in SOURCES}


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


class Socket:
    closed = False
    def __init__(self): self.events = []
    async def send_json(self, event): self.events.append(event)


async def run_case(case, output):
    folder = output / case['id']
    runtime = RobotRuntime(folder / 'runtime')
    runtime.call('remember', {'note': 'Use PLA for the first prints.'})
    runtime.call('remember', {'note': 'Mount the bare Xiaomi Mi 9 SE in landscape.'})
    memory_before = list(runtime.memory)
    receipts, events, delivered, packets, diagnostics, processes, backend_info = [], [], [], [], [], {}, {}
    start = time.perf_counter()
    original_call = runtime.call
    def observed_call(name, args):
        receipt = original_call(name, args)
        receipts.append({'at_s': round(time.perf_counter() - start, 6), 'name': name, 'args': args, 'receipt': receipt})
        return receipt
    runtime.call = observed_call
    socket = Socket()
    conversation = Conversation({'runtime': runtime}, socket)
    async def context(text): delivered.append({'at_s': time.perf_counter() - start, 'text': text})
    conversation.voice = SimpleNamespace(track=SimpleNamespace(append=packets.append), context=context, turn=None)
    conversation.mask = SimpleNamespace(pending={}, diagnostic=lambda *args, **kw: diagnostics.append([args, kw]))
    conversation.playback_busy = True
    brain = conversation.brain
    original_emit = brain.emit
    async def emit(event):
        events.append({'at_s': round(time.perf_counter() - start, 6), **event})
        await original_emit(event)
    brain.emit = emit
    delivery_task = asyncio.create_task(conversation.deliver_results())
    done = asyncio.Event()
    tick_gaps, handler_times = [], []
    seq = 0
    async def foreground():
        nonlocal seq
        previous = time.perf_counter()
        while not done.is_set():
            now = time.perf_counter()
            tick_gaps.append(now - previous)
            previous = now
            # Real input dispatcher; its audio sink is intentionally a fake track.
            t = time.perf_counter()
            await conversation.handle({'type': 'mic', 'pcm': 'AQA='})
            handler_times.append(time.perf_counter() - t)
            seq += 1
            captured = time.time()
            for kind, values in [('phone_battery', {'level': .73}),
                                 ('phone_orientation', {'alpha': 10, 'beta': 7, 'gamma': -3}),
                                 ('robot_telemetry', {'battery_v': 7.6, 'servo_temp_c': 41, 'max_current_a': .8, 'pan_deg': 0})]:
                runtime.ingest({'kind': kind, 'seq': seq, 'captured_at': captured, 'values': values})
            for job_id, client in list(brain.clients.items()):
                if getattr(client, 'proc', None): processes[client.proc.pid] = client.proc
                backend_info[job_id] = dict(client.backend_info)
            await asyncio.sleep(.02)
    foreground_task = asyncio.create_task(foreground())
    cancellation = None
    mailbox = {}
    failures = []
    try:
        t = time.perf_counter()
        accepted = await brain.handle('start_background_task', {'question': case['question']})
        handle_s = time.perf_counter() - t
        job_id = accepted['job_id']
        job_task = brain.tasks[job_id]
        if case.get('cancel'):
            deadline = time.perf_counter() + 25
            active_at = None
            while not job_task.done() and time.perf_counter() < deadline:
                client = brain.clients.get(job_id)
                if client and getattr(client, '_active_turn', None):
                    active_at = time.perf_counter() - start
                    break
                await asyncio.sleep(.01)
            t = time.perf_counter()
            cancelled = await brain.handle('cancel_background_task', {'job_id': job_id})
            cancellation = {'active_turn_observed_at_s': active_at, 'handle_s': time.perf_counter() - t, 'receipt': cancelled}
            if active_at is None: failures.append('cancel_before_model_turn_unverified')
        await asyncio.wait_for(asyncio.shield(job_task), 65)
        result_at = time.perf_counter() - start
        job = dict(brain.jobs[job_id])
        if case.get('cancel'):
            if job['status'] != 'cancelled': failures.append('not_cancelled')
            if any(event.get('status') == 'complete' for event in events): failures.append('cancelled_result_published')
        elif job['status'] != 'complete': failures.append('analysis_not_completed')
        if case['id'] == 'fresh_sensor':
            await asyncio.sleep(.24)
            mailbox['while_playback_busy'] = len(delivered)
            conversation.playback_busy = False
            conversation.user_speaking = True
            await asyncio.sleep(.24)
            mailbox['while_user_speaking'] = len(delivered)
            conversation.user_speaking = False
            await asyncio.sleep(.45)
            mailbox['when_idle'] = len(delivered)
            await asyncio.sleep(.24)
            mailbox['after_second_tick'] = len(delivered)
            if mailbox != {'while_playback_busy': 0, 'while_user_speaking': 0, 'when_idle': 1, 'after_second_tick': 1}:
                failures.append('mailbox_current_revision_delivery')
        elif case['id'] == 'foreground_input':
            conversation.user_revision += 1
            conversation.playback_busy = False
            await asyncio.sleep(.45)
            mailbox = {'topic_changed': True, 'delivered': len(delivered), 'old_result_status': brain.jobs[job_id]['status'],
                       'old_result_announced': brain.jobs[job_id]['announced']}
            if delivered or brain.jobs[job_id]['announced']: failures.append('stale_result_delivered')
        names = [receipt['name'] for receipt in receipts]
        for tool in case.get('required_tools', []):
            if tool not in names: failures.append('missing_' + tool)
        if any(name not in ('get_sensor_snapshot', 'recall') for name in names): failures.append('non_read_tool')
        if runtime.memory != memory_before or runtime.intents or runtime.estop: failures.append('runtime_mutated')
        if handle_s > .1: failures.append('start_return_over_100ms')
        if len(packets) < 5: failures.append('foreground_not_exercised')
        if handler_times and max(handler_times) > .05: failures.append('foreground_handler_over_50ms')
        summary = job.get('summary', '')
        max_words = case.get('max_words', 140)
        if not case.get('cancel') and len(summary.split()) > max_words: failures.append(f'summary_over_{max_words}_words')
        if case.get('complete_sentences') and summary and summary.rstrip('"\'*)] ').endswith(('.', '?', '!')) is False:
            failures.append('summary_incomplete_ending')
        row = {'id': case['id'], 'prompt': case['question'], 'model': 'gpt-6-luna', 'reasoning': 'low',
               'start_handle_s': handle_s, 'result_from_start_s': result_at, 'job': job,
               'actual_tool_receipts': receipts, 'backend_info': backend_info, 'events': events,
               'foreground': {'sink': 'fake audio track; real Conversation.handle dispatcher', 'packets': len(packets),
                              'max_handler_s': max(handler_times, default=0), 'max_tick_gap_s': max(tick_gaps, default=0),
                              'median_tick_gap_s': statistics.median(tick_gaps) if tick_gaps else None},
               'mailbox': mailbox, 'delivered_to_fake_native_context': delivered,
               'cancellation': cancellation, 'automated_failures': failures,
               'manual_criteria': case['criteria'], 'manual_review': 'pending', 'summary_words': len(summary.split())}
    except Exception as error:
        row = {'id': case['id'], 'prompt': case['question'], 'automated_failures': ['harness_exception'],
               'exception': repr(error), 'events': events, 'actual_tool_receipts': receipts}
    finally:
        done.set()
        await foreground_task
        conversation.alive = False
        delivery_task.cancel()
        await asyncio.gather(delivery_task, return_exceptions=True)
        await brain.close()
    row['cleanup'] = {'tasks_left': len(brain.tasks), 'clients_left': len(brain.clients),
                      'model_children': [{'pid': pid, 'exit_code': proc.poll()} for pid, proc in processes.items()]}
    if brain.tasks or brain.clients or any(proc.poll() is None for proc in processes.values()):
        row['automated_failures'].append('child_not_closed')
    save(folder / 'result.json', row)
    print(json.dumps({'id': case['id'], 'failures': row['automated_failures'],
                      'start_ms': round(row.get('start_handle_s', 0) * 1000, 3),
                      'result_s': row.get('result_from_start_s'), 'status': row.get('job', {}).get('status')}), flush=True)
    return row


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=BRAIN / 'results/luna_background_20260922')
    parser.add_argument('--refined', action='store_true', help='Rerun three affected cases and one frozen held-out case with a strict 120-word limit.')
    parser.add_argument('--new-heldout', action='store_true', help='Use the second unseen leg-isolation question instead of the first held-out question.')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if (args.output / 'rubric.json').exists(): raise SystemExit('Use a new output directory to preserve the frozen rubric.')
    os.environ['MIST_BACKGROUND_MODEL'] = 'gpt-6-luna'
    cases = CASES
    if args.refined:
        cases = [{**case, 'max_words': 120, 'complete_sentences': True} for case in
                 [case for case in CASES if case['id'] in ('leg_plan', 'pla_orientation', 'foreground_input')] +
                 [HELD_OUT_SECOND if args.new_heldout else HELD_OUT]]
    rubric = {'frozen_at': time.time(), 'source_sha256': hashes(), 'cases': cases,
              'checks': ['Real production BackgroundBrain.reason; no injected runner.', 'One background model at a time.',
                         'Start handle below 100 ms; foreground handler below 50 ms.', 'Only sensor and recall calls.',
                         'No runtime action or preference changes.', 'All model child processes closed.',
                         f'Summary at most {120 if args.refined else 140} words, inspected against case criteria.',
                         'Review exact capability claims against current runtime tools; proposals must distinguish future implementation.'],
              'limits': ['Seeded sensors are test data, refreshed during calls.',
                         'Foreground microphone sink and native context receiver are fake; no voice or hardware is tested.',
                         'Latency includes a new private analyst subprocess and session per job.']}
    save(args.output / 'rubric.json', rubric)
    start = time.perf_counter()
    rows = []
    for case in cases:
        rows.append(await run_case(case, args.output))
    report = {'model': 'gpt-6-luna', 'reasoning': 'low', 'service_tier': 'default', 'elapsed_s': time.perf_counter() - start,
              'source_sha256_before': rubric['source_sha256'], 'source_sha256_after': hashes(),
              'cases': rows, 'automated_passed': sum(not row['automated_failures'] for row in rows),
              'limits': rubric['limits']}
    save(args.output / 'report.json', report)


if __name__ == '__main__': asyncio.run(main())
