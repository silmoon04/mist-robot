"""Offline checks only; no provider connection."""
import pytest

try:
    from . import scribe_language_probe_20260930 as probe
except ImportError:
    import scribe_language_probe_20260930 as probe


def test_plan_is_exact_balanced_serial_pairs():
    order = probe.plan()
    assert len(order) == 8
    assert order == probe.plan()
    for start in range(0, len(order), 2):
        pair = order[start:start + 2]
        assert pair[0]['case_id'] == pair[1]['case_id']
        assert pair[0]['repetition'] == pair[1]['repetition']
        assert {row['language'] for row in pair} == {'auto', 'en'}
    assert {(row['case_id'], row['repetition']) for row in order} == {
        ('normal_end', 1), ('normal_end', 2), ('yeah_backchannel', 1),
        ('yeah_backchannel', 2)}


def test_language_override_changes_only_hint():
    automatic = probe.ScribeRealtimeASR('placeholder').url
    english = probe.EnglishScribe('placeholder').url
    assert english == automatic + '&language_code=en'
    assert 'language_code=' not in automatic
    assert 'commit_strategy=vad' in english
    assert 'no_verbatim=false' in english


def test_wer():
    assert probe.wer('yeah', 'Ja') == 1.0
    assert probe.wer('yeah', 'Yeah.') == 0.0
    assert probe.wer('a b c', 'a c') == pytest.approx(1 / 3, abs=1e-6)


def test_summary_reports_commit_rate_without_imputing_missing_wer():
    rows = [{'case_id': 'yeah_backchannel', 'language': 'auto', 'status': 'complete',
             'wer': 1.0, 'final_transcript': 'Ja'},
            {'case_id': 'yeah_backchannel', 'language': 'auto', 'status': 'incomplete',
             'wer': None, 'final_transcript': ''}]
    result = probe.summarize(rows)[0]
    assert result['trials'] == 2
    assert result['committed'] == 1
    assert result['mean_wer_on_committed'] == 1.0


@pytest.mark.asyncio
async def test_trial_with_fake_adapter_preserves_evidence_without_api():
    case = probe.cases()['yeah_backchannel']

    class Fake:
        def __init__(self):
            self.raw_events = [{'message_type': 'session_started',
                                'config': {'language_code': 'en'}}]
            self.timing_summary = {'wire_send_count': 1}
            self.sent = 0

        async def start(self, callback):
            self.callback = callback

        async def send_pcm16k(self, data):
            self.sent += len(data)
            if self.sent >= (probe.LEAD_S * 32000 + 16640):
                if not hasattr(self, 'done'):
                    self.done = True
                    for kind in ('final', 'turn_end'):
                        self.callback({'type': kind, 'segment': 'Yeah.',
                                       'text': 'Yeah.', 'metadata': {}, 'words': [],
                                       'raw': None})

        async def close(self):
            pass

    async def no_sleep(_):
        pass

    row = await probe.trial({'case_id': 'yeah_backchannel', 'repetition': 1,
                             'language': 'en'}, case, 'placeholder',
                            adapter_factory=Fake, sleep=no_sleep)
    assert row['status'] == 'complete'
    assert row['wer'] == 0
    assert row['provider_session_started']
    assert row['provider_language_config'] == 'en'
    assert row['sent_pcm_s'] == pytest.approx(probe.LEAD_S + row['fixture_s'] + probe.TAIL_S)
