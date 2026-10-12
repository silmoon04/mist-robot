"""Small frozen speaker-policy comparison; no service, audio, or tool actions."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tempfile
import time

BRAIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BRAIN))

from benchmarks.naturalness.cerebras_client import CerebrasClient
from duplex.conversation_policy import GROUNDED_PROMPT
from duplex.session_memory import SessionMemory
from duplex.session_store import SessionStore


OLD_GROUNDING = ("Use the supplied session ledger and sourced working notes to stay with the person's task. "
                 "A summary is a fallible index, not new evidence. Keep their corrections and unresolved questions. "
                 "Never turn a total into an unprovided causal breakdown or invent why someone wrote code. "
                 "When a name or number sounds wrong, ask one precise clarification. "
                 "Use recall with a short query when the relevant earlier detail is missing; "
                 "an empty preference list does not mean it was never said.")
NEW_GROUNDING = next(line for line in GROUNDED_PROMPT.splitlines()
                     if line.startswith('Use the supplied session ledger'))
assert NEW_GROUNDING.startswith('Use the supplied session ledger')
BASELINE_PROMPT = GROUNDED_PROMPT.replace(NEW_GROUNDING, OLD_GROUNDING)

CASES = [
    {'id': 'implicit_recall',
     'turns': [*[f'Initial chassis note {n}.' for n in range(4)],
               'I have never run the battery endurance test.',
               *[f'Discussing the bracket geometry, part {n}.' for n in range(16)],
               'Back to the battery module.', 'Did we already try it?'],
     'query': 'Did we already try it?'},
    {'id': 'negation_correction',
     'turns': ['I have never run the battery endurance test.',
               'Correction: I ran it yesterday, but the result was inconclusive.',
               'What is the test status now?'],
     'query': 'What is the test status now?'},
    {'id': 'unknown_cause',
     'turns': ['I suspect the controller may be overheating, but I have not measured its temperature.',
               'The chassis is painted blue.',
               'Returning to the controller.',
               'Did we establish what caused the shutdown?'],
     'query': 'Did we establish what caused the shutdown?'},
    {'id': 'asr_ambiguity',
     'turns': ['I need to measure motor torque before assessing the left leg.',
               'The transcript says motor talk. What did I probably mean?'],
     'query': 'The transcript says motor talk. What did I probably mean?'},
    {'id': 'known_measurement',
     'turns': ['I measured the front left motor torque at 0.8 newton metres.',
               'The load target is 250 grams, but I have not tested the assembled leg.',
               'What torque did I report, and can we say the leg holds the load?'],
     'query': 'What torque did I report, and can we say the leg holds the load?'},
    {'id': 'planned_action',
     'turns': ['I plan to inspect the left leg wiring tomorrow.',
               'The right leg has a red cover.',
               'About the left leg wiring, what did the inspection show?'],
     'query': 'About the left leg wiring, what did the inspection show?'},
]


def context_for(case, baseline=False):
    with tempfile.TemporaryDirectory() as temp:
        store = SessionStore(Path(temp) / 'session.sqlite3')
        memory = SessionMemory(store, case['id'], summary_client_factory=lambda: None,
                               summary_every=1000)
        try:
            for turn in case['turns']:
                memory.observe('user', turn)
            if baseline:
                # Reproduce the former FTS lookup, before the prior-topic bridge.
                original_search = store.search_turns
                words = re.findall(r'[\w]+', case['query'].casefold())[:10]
                lookup = ' OR '.join('"' + word + '"' for word in words if len(word) > 2)
                store.search_turns = lambda _query, **kwargs: original_search(lookup, **kwargs) if lookup else []
            return memory.context(case['query'], max_chars=2600)
        finally:
            memory.close()
            store.close()


def run():
    out = []
    for case in CASES:
        for condition, policy in [('baseline_policy', BASELINE_PROMPT),
                                  ('revised_policy', GROUNDED_PROMPT)]:
            context = context_for(case, baseline=condition == 'baseline_policy')
            client = CerebrasClient(model='qwen-3.8-27b', thinking='low',
                                    system_prompt=policy, max_output_tokens=600)
            try:
                client.new_session()
                started = time.perf_counter()
                result = client.ask('Session evidence:\n' + context + '\n\nLatest user request: '
                                    + case['query'], timeout=30)
                out.append({'case': case['id'], 'condition': condition,
                            'answer': result.text.strip(), 'errors': result.errors,
                            'wall_ms': round((time.perf_counter() - started) * 1000),
                            'context': context})
            finally:
                client.close()
    target = BRAIN / 'results' / 'brain-quality-20260929' / 'memory' / 'live-policy-pair.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')
    print(str(target))


if __name__ == '__main__':
    run()
