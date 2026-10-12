"""Sixteen new Luna face-control inputs through the existing isolated evaluator.

This freezes expectations before inference and does not alter the production
prompt. It tests tool decisions, not rendered frames or synthesized speech.
"""
from __future__ import annotations

import math
import eval_luna_faces as evaluator


def face(expression, variant=None, duration_ms=None):
    arguments = {'expression': expression}
    if variant is not None:
        arguments['variant'] = variant
    if duration_ms is not None:
        arguments['duration_ms'] = duration_ms
    return [{'name': 'set_expression', 'arguments': arguments}]


def cases():
    rows = [
        ('sequence_calm', 'sequence', False,
         'Let us start calmly. Put on your neutral face, please.', face('neutral')),
        ('sequence_curious', 'sequence', True,
         'Now curious, variation one. I want to inspect that particular one.', face('curious', 1)),
        ('sequence_happy', 'sequence', True,
         'And now happy, variation two, please.', face('happy', 2)),
        ('sequence_chat', 'sequence', True,
         'Keep that expression. The first foot finally fits the servo. A dry one-liner seems appropriate.', []),
        ('speaking_expression', 'speaking', False,
         'Show your curious face while you explain in two short sentences why the sky is blue. Let your normal speech animation handle the mouth.', face('curious')),
        ('speaking_keep', 'speaking', True,
         'Keep the face unchanged and explain why sunsets can be red. No animation instructions in your answer.', []),
        ('correction_within_turn', 'corrections', False,
         'Put on angry variant three. Wait, cancel that: I only want happy variant one instead.', face('happy', 1)),
        ('correction_next_turn', 'corrections', True,
         'Actually neutral, variant two, please. Just that one.', face('neutral', 2)),
        ('unknown_exact', None, False,
         'Select the exact preset velvet_cloud. If you do not have it, leave the face unchanged.', []),
        ('invalid_variant', None, False,
         'Set sleepy to zero-based variant two. Keep the display as it is if that exact variation is unavailable.', []),
        ('duration_selection', None, False,
         'For an acting check, show suspicious variant one for 1600 milliseconds.', face('suspicious', 1, 1600)),
        ('difficult_name', None, False,
         'For the next acting check, use dead inside variant two.', face('dead_inside', 2)),
        ('theatrical_requested', None, False,
         'A deliberate overreaction for our little play: show panic variation two.', face('panic', 2)),
        ('ordinary_context', 'chat', False,
         'The print finished after seven hours. I am going to leave it to cool before touching it.', []),
        ('ordinary_followup', 'chat', True,
         'It is just a small bracket. What is a brim in 3D printing? One sentence is enough.', []),
        ('explain_controls', None, False,
         'Explain how changing your face differs from animating your mouth. Keep the display unchanged while answering, and use one short sentence.', []),
    ]
    result = []
    for case_id, session, continuation, prompt, expected in rows:
        case = {'id': case_id, 'group': 'face_switching_v3', 'prompt': prompt,
                'expected_calls': expected, 'max_words': 65, 'max_questions': 1}
        if session:
            case.update(session=session, **{'continue': continuation})
        result.append(case)
    assert len(result) == 16
    return result


if __name__ == '__main__':
    evaluator.make_cases = cases
    original_summary = evaluator.summary

    def summary(rows):
        result = original_summary(rows)
        # The older evaluator used a floor-index estimate. Use nearest-rank p90.
        for key, groups in result['latency_seconds'].items():
            for label, selected_rows in [('all', rows), ('warm', rows[1:])]:
                values = sorted(row[key] for row in selected_rows if row.get(key) is not None)
                if values:
                    groups[label]['p90'] = values[math.ceil(len(values) * .9) - 1]
        result['percentile_method'] = 'nearest-rank'
        return result

    evaluator.summary = summary
    evaluator.main()
