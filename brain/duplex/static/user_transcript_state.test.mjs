import test from 'node:test';
import assert from 'node:assert/strict';
import {UserTranscriptState} from './user_transcript_state.mjs';

test('partial snapshots replace text and a final rejects later interim revisions', () => {
  const state = new UserTranscriptState();
  assert.equal(state.replace({utterance_id: 'a', text: 'turn left', final: false}).text, 'turn left');
  assert.equal(state.replace({utterance_id: 'a', text: 'turn left now', final: false}).text, 'turn left now');
  assert.equal(state.replace({utterance_id: 'a', text: 'turn left now', final: true}).final, true);
  assert.equal(state.replace({utterance_id: 'a', text: 'turn left', final: false}).text, 'turn left now');
});

test('older same-utterance revisions cannot overwrite a newer partial or final', () => {
  const state = new UserTranscriptState();
  state.replace({utterance_id: 'a', revision: 4, text: 'I was thinking', final: false});
  assert.equal(state.replace({utterance_id: 'a', revision: 3, text: 'I was', final: false}).text, 'I was thinking');
  state.replace({utterance_id: 'a', revision: 5, text: 'I was thinking about it', final: false});
  state.replace({utterance_id: 'a', revision: 7, text: 'I was thinking about it.', final: true});
  assert.equal(state.replace({utterance_id: 'a', revision: 6, text: 'I was thinking', final: true}).text,
    'I was thinking about it.');
  assert.equal(state.snapshot().revision, 7);
});

test('an empty acoustic event preserves the last final until new speech has text', () => {
  const state = new UserTranscriptState();
  state.replace({utterance_id: 1, revision: 3, text: 'hello', final: true});
  const acousticStart = state.replace({utterance_id: 2, revision: 0, text: '', final: false});
  assert.equal(acousticStart.text, 'hello');
  assert.equal(acousticStart.final, true);
  assert.equal(acousticStart.visible, true);
  assert.equal(acousticStart.utteranceId, 'server:1');
  state.replace({utterance_id: 2, revision: 1, text: '', final: false});
  const newSpeech = state.replace({utterance_id: 2, revision: 2, text: 'good morning', final: false});
  assert.equal(newSpeech.text, 'good morning');
  assert.equal(newSpeech.final, false);
  assert.equal(newSpeech.utteranceId, 'server:2');
  assert.equal(state.replace({utterance_id: 1, revision: 4, text: 'stale', final: false}).text, 'good morning');
});

test('legacy transcript deltas append only when no authoritative snapshots arrived', () => {
  const state = new UserTranscriptState();
  state.appendFallback('good ');
  state.appendFallback('morning');
  assert.equal(state.snapshot().text, 'good morning');
  assert.equal(state.finalizeFallback('Good morning.').final, true);
  state.appendFallback('stale');
  assert.equal(state.snapshot().text, 'stale');
  state.replace({utterance_id: 'native', text: 'morning again', final: false});
  assert.equal(state.appendFallback(' duplicated').text, 'morning again');
});
