"""Offline receipt-clock audit of conversation, expression and playback events.

No provider calls, renderer mutation, private-reasoning analysis or acoustic claims.
Run with an exported trace path and --output-dir. Input is never modified.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import statistics


def event_name(row):
    event = row['event']
    return event.get('type', event.get('event'))


def first(rows, predicate):
    return next((row for row in rows if predicate(row)), None)


def last(rows, predicate):
    return first(reversed(rows), predicate)


def reference(row):
    return None if row is None else {'id': row['id'], 'receipt_ms': row.get('elapsed_ms'),
                                    'clock_id': row.get('clock_id')}


def interval(start, end):
    """Return a forward interval only with an explicit shared outer clock."""
    if start is None or end is None or not start.get('clock_id') or start.get('clock_id') != end.get('clock_id'):
        return None
    a, b = start.get('elapsed_ms'), end.get('elapsed_ms')
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in (a, b)) or b < a:
        return None
    return round(b-a, 3)


def distribution(values, denominator):
    values = sorted(v for v in values if v is not None)
    def quantile(q):
        index = (len(values)-1)*q
        lo = int(index)
        return round(values[lo]+(values[min(lo+1,len(values)-1)]-values[lo])*(index-lo),3)
    return {'n':len(values), 'denominator':denominator, 'missing':denominator-len(values),
            'median_ms':round(statistics.median(values),3) if values else None,
            'p90_ms':quantile(.9) if values else None, 'max_ms':max(values) if values else None,
            'small_n':len(values)<20}


def turn_audit(events):
    starts = [r for r in events if r['event'].get('phase')=='thinking_started' and r['event'].get('turn_id')]
    turns = []
    for index, start in enumerate(starts):
        stop = starts[index+1]['id'] if index+1<len(starts) else events[-1]['id']+1
        window = [r for r in events if start['id']<=r['id']<stop]
        before = [r for r in events if r['id']<start['id']]
        turn_id = start['event']['turn_id']
        own = [r for r in window if r['event'].get('turn_id')==turn_id]
        application = bool(start['event'].get('application_context'))
        commit = None if application else last(before,lambda r:r['event'].get('phase')=='user_committed'
                    and r['event'].get('text')==start['event'].get('input_text')
                    and r['event'].get('revision')==start['event'].get('revision'))
        user = last(before,lambda r:event_name(r)=='transcript_done' and r['event'].get('role')=='user'
                    and not r['event'].get('backchannel') and r['event'].get('text')==start['event'].get('input_text')) if commit else None
        any_text = first(own,lambda r:r['event'].get('phase')=='text_delta')
        text = first(own,lambda r:r['event'].get('phase')=='text_delta' and str(r['event'].get('delta','')).strip())
        public_text = first(own,lambda r:event_name(r)=='turn.delta' and str(r['event'].get('delta','')).strip())
        done = first(own,lambda r:r['event'].get('phase')=='thinking_finished')
        discarded = first(own,lambda r:r['event'].get('phase')=='interrupted_generation_discarded')
        final = first(window,lambda r:event_name(r)=='turn.done' and r['event'].get('turn',{}).get('id')==turn_id)
        phrases = [r for r in window if event_name(r)=='tts_phrase']
        seqs = {r['event']['sequence'] for r in phrases if 'sequence' in r['event']}
        audio = first(window,lambda r:event_name(r)=='audio_delivery' and r['event'].get('seq') in seqs)
        playback = first(window,lambda r:r.get('source')=='browser' and event_name(r)=='playback_started'
                         and audio is not None and r['event'].get('sequence')==audio['event'].get('seq')
                         and r['event'].get('epoch')==audio['event'].get('epoch'))
        asr = last(before,lambda r:r['event'].get('phase')=='stt_final') if commit else None
        tool_rows = [r for r in window if event_name(r)=='tool' and r['event'].get('turn_id')==turn_id]
        generated = final['event']['turn'].get('transcript') if final else (done['event'].get('generated_text') if done else None)
        stages = dict(user_final=user, commit=commit, model_start=start, first_any_text=any_text,
                      first_nonblank_text=text, first_public_text=public_text, first_phrase=phrases[0] if phrases else None,
                      first_audio_delivery=audio, playback_receipt=playback, model_finished=done, discarded=discarded)
        intervals = {'commit_to_model_start':interval(commit,start), 'model_start_to_nonblank_text':interval(start,text),
                     'commit_to_nonblank_text':interval(commit,text), 'commit_to_playback_receipt':interval(commit,playback),
                     'commit_to_public_text':interval(commit,public_text),
                     'public_text_to_playback_receipt':interval(public_text,playback),
                     'model_start_to_playback_receipt':interval(start,playback),
                     'nonblank_text_to_audio_delivery':interval(text,audio),
                     'audio_delivery_to_playback_receipt':interval(audio,playback),
                     'last_asr_final_to_commit':interval(asr,commit)}
        timings = done['event'].get('timings',{}) if done else {}
        waiting_samples = [r for r in window if r.get('source')=='browser' and event_name(r)=='audio_scheduled'
                           and playback is not None and r['id']<playback['id']]
        turns.append({'index':index+1,'turn_id':turn_id,'application_report':application,
                      'input_text':start['event'].get('input_text'), 'generated_text':generated,
                      'status':'completed' if done else ('discarded' if discarded else 'incomplete'),
                      'endpoint':commit['event'].get('endpoint') if commit else None,
                      'stages':{key:reference(value) for key,value in stages.items()}, 'intervals_ms':intervals,
                      'tts_sequences':sorted(seqs), 'tools':[{'id':r['id'],'name':r['event'].get('name'),'arguments':r['event'].get('arguments')} for r in tool_rows],
                      'pre_playback_speech_samples':{'n':len(waiting_samples),
                          'inactive':sum(r['event'].get('audio_active') is False for r in waiting_samples),
                          'first':reference(waiting_samples[0]) if waiting_samples else None,
                          'last':reference(waiting_samples[-1]) if waiting_samples else None},
                      'model_http_requests':[{'round':r.get('round'),'headers_ms':r.get('headers_ms'),'total_ms':r.get('total_ms'),'selected_tool_calls':r.get('selected_tool_calls')} for r in timings.get('http_requests',[])],
                      'first_useful_audio_ms':None, 'usefulness_annotation':None})
    return turns


def face_audit(events, turns):
    commands = [r for r in events if event_name(r)=='face']
    shown = [r for r in events if r.get('source')=='browser' and event_name(r)=='expression']
    turn_map = {t['turn_id']:t for t in turns}
    used = set()
    faces = []
    for index, command in enumerate(commands):
        event = command['event']
        tool = last(events,lambda r:r['id']<command['id'] and event_name(r)=='tool'
                    and r['event'].get('name')=='set_expression'
                    and r['event'].get('result',{}).get('expression')==event.get('expression')
                    and interval(r,command) is not None and interval(r,command)<1000)
        turn = turn_map.get(tool['event'].get('turn_id')) if tool else None
        applied = first(shown,lambda r:r['id'] not in used and r['event'].get('name')==event.get('expression')
                        and r['event'].get('pinned') is True and interval(command,r) is not None and interval(command,r)<=5000)
        if applied:used.add(applied['id'])
        displaced = first(shown,lambda r:applied is not None and r['id']>applied['id']
                          and (r['event'].get('name'),r['event'].get('variant'))!=(applied['event'].get('name'),applied['event'].get('variant')))
        next_command = commands[index+1] if index+1<len(commands) else None
        next_gap = interval(command,next_command)
        playback_ref = turn['stages']['playback_receipt'] if turn else None
        playback = first(events,lambda r:playback_ref is not None and r['id']==playback_ref['id'])
        gap = interval(displaced,playback)
        faces.append({'command':reference(command),'expression':event.get('expression'),'variant':event.get('variant'),
                      'requested_hold_ms':event.get('duration_ms'),'turn_id':turn['turn_id'] if turn else None,
                      'browser_applied':reference(applied),'browser_displaced':reference(displaced),
                      'displaced_by':displaced['event'].get('name') if displaced else None,
                      'command_to_browser_receipt_ms':interval(command,applied),
                      'browser_state_lifetime_ms':interval(applied,displaced),
                      'next_command_after_ms':next_gap,
                      'competing_command_before_hold_end':next_gap is not None and type(event.get('duration_ms')) in (int,float) and next_gap<event['duration_ms'],
                      'associated_playback_receipt':playback_ref,
                      'displaced_before_playback_receipt':gap is not None,
                      'displacement_to_playback_receipt_ms':gap,
                      'full_raster_visible_duration_ms':None,
                      'attribution':'Expression name and pinned state within 5 seconds; browser telemetry has no originating command ID.'})
    return faces


def background_audit(events, turns):
    jobs = []
    for started in [r for r in events if event_name(r)=='brain_job' and r['event'].get('status')=='running']:
        job_id = started['event']['job_id']
        terminal = first(events,lambda r:r['id']>started['id'] and event_name(r)=='brain_job' and r['event'].get('job_id')==job_id and r['event'].get('status') in ('complete','failed','cancelled','stale'))
        queued = first(events,lambda r:r['id']>started['id'] and event_name(r)=='brain_delivery' and r['event'].get('job_id')==job_id)
        tool = first(events,lambda r:event_name(r)=='tool' and r['event'].get('name')=='start_background_task' and r['event'].get('result',{}).get('job_id')==job_id)
        acknowledgement = next((t for t in turns if tool and t['turn_id']==tool['event'].get('turn_id')),None)
        report = next((t for t in turns if queued and t['application_report']
                       and t['stages']['model_start']['id']>queued['id']
                       and job_id in str(t['input_text'])),None)
        lookup = {r['id']:r for r in events}
        def stage(turn,key):
            value=turn['stages'][key] if turn else None
            return lookup.get(value['id']) if value else None
        origin=stage(acknowledgement,'commit')
        initial_playback=stage(acknowledgement,'playback_receipt')
        report_playback=stage(report,'playback_receipt')
        idle=last(events,lambda r:queued is not None and r['id']<queued['id'] and r.get('source')=='browser' and event_name(r)=='playback_idle')
        jobs.append({'job_id':job_id,'started':reference(started),'terminal':reference(terminal),
                     'terminal_status':terminal['event'].get('status') if terminal else None,
                     'delivery_queued':reference(queued),'initial_response_turn_id':acknowledgement['turn_id'] if acknowledgement else None,
                     'report_response_turn_id':report['turn_id'] if report else None,
                     'initial_generated_text':acknowledgement['generated_text'] if acknowledgement else None,
                     'report_generated_text':report['generated_text'] if report else None,
                     'initial_playback_receipt':reference(initial_playback),'report_playback_receipt':reference(report_playback),
                     'last_idle_before_queue':reference(idle),
                     'intervals_ms':{'user_commit_to_initial_playback_receipt':interval(origin,initial_playback),
                                     'job_start_to_terminal':interval(started,terminal),
                                     'terminal_to_delivery_queue':interval(terminal,queued),
                                     'last_idle_to_delivery_queue':interval(idle,queued),
                                     'user_commit_to_report_playback_receipt':interval(origin,report_playback),
                                     'queue_to_report_playback_receipt':interval(queued,report_playback)},
                     'first_useful_audio_ms':None,'usefulness_annotation':None})
    return jobs


def analyze(document):
    events=document.get('events',[])
    if not isinstance(events,list) or any(not isinstance(r,dict) or not isinstance(r.get('event'),dict) or type(r.get('id')) is not int for r in events):
        raise ValueError('Expected exported event rows with integer IDs and event objects')
    ids=[r['id'] for r in events]
    if ids!=sorted(set(ids)):raise ValueError('Event IDs must be unique and increasing')
    turns=turn_audit(events)
    faces=face_audit(events,turns)
    commits=[r for r in events if r['event'].get('phase')=='user_committed']
    splits=[]
    for a,b in zip(commits,commits[1:]):
        gap=interval(a,b)
        if gap is None or gap>5000:continue
        between=[r for r in events if a['id']<r['id']<b['id']]
        splits.append({'first':reference(a),'first_text':a['event'].get('text'),'second':reference(b),
                       'second_text':b['event'].get('text'),'commit_gap_ms':gap,
                       'intervening_assistant_finals':[{'event':reference(r),'text':r['event'].get('text')} for r in between if event_name(r)=='transcript_done' and r['event'].get('role')=='assistant'],
                       'intervening_playback_receipts':[reference(r) for r in between if r.get('source')=='browser' and event_name(r)=='playback_started'],
                       'intervening_resets':[reference(r) for r in between if event_name(r)=='audio_reset'],
                       'interpretation':'Temporal candidate only; intention and acoustic pause duration require additional evidence.'})
    samples=[r for r in events if r.get('source')=='browser' and event_name(r)=='audio_scheduled']
    inactive=[r for r in samples if r['event'].get('audio_active') is False]
    nonrest_inactive=[r for r in inactive if r['event'].get('viseme') not in (None,'rest')]
    complaints=[]
    for r in events:
        if event_name(r)=='transcript_done' and r['event'].get('role')=='user' and 'mouth' in str(r['event'].get('text','')).lower():
            preceding=[s for s in samples if interval(s,r) is not None and interval(s,r)<=10000]
            complaints.append({'event':reference(r),'text':r['event'].get('text'),
                               'preceding_10s_samples':[{'event':reference(s),**{k:s['event'].get(k) for k in ('playing','audio_active','viseme','queue_ms')}} for s in preceding]})
    metric_names=list(turns[0]['intervals_ms']) if turns else []
    direct=[t for t in turns if not t['application_report']]
    long_waits=sorted((t for t in direct if t['intervals_ms']['commit_to_playback_receipt'] is not None),key=lambda t:t['intervals_ms']['commit_to_playback_receipt'],reverse=True)
    return {'schema_version':1,'session':document.get('session',{}),
            'method':{'clock':'Explicit matching outer clock_id with elapsed_ms; browser events use server receipt timestamps.',
                      'duplicates':'Count browser source records once; debug_client wrappers are not independent observations.',
                      'playback':'Software playback notification, not acoustic onset or proof every generated word was heard.',
                      'usefulness':'No semantic useful-audio onset annotation supplied; related values remain null.'},
            'counts':{'events':len(events),'user_commits':len(commits),'generation_attempts':len(turns),
                      'user_generations':len(direct),'application_report_generations':len(turns)-len(direct),
                      'completed_generations':sum(t['status']=='completed' for t in turns),
                      'discarded_generations':sum(t['status']=='discarded' for t in turns),
                      'with_playback_receipt':sum(t['stages']['playback_receipt'] is not None for t in turns),
                      'face_commands':len(faces),'browser_expression_reports':sum(r.get('source')=='browser' and event_name(r)=='expression' for r in events),
                      'incomplete_hold_events':sum(r['event'].get('phase')=='floor_incomplete_hold' for r in events),
                      'backchannels_preserved':sum(r['event'].get('phase')=='floor_backchannel_kept' for r in events)},
            'capture':{'first':reference(events[0]) if events else None,
                       'last':reference(events[-1]) if events else None,
                       'duration_ms':interval(events[0],events[-1]) if events else None},
            'user_generation_distributions_ms':{key:distribution([t['intervals_ms'][key] for t in direct],len(direct)) for key in metric_names},
            'turns':turns,'longest_user_waits':long_waits[:6],'nearby_user_commit_candidates':splits,
            'faces':faces,'background_jobs':background_audit(events,turns),
            'mouth':{'sample_count':len(samples),'inactive_sample_count':len(inactive),
                     'inactive_nonrest_viseme_count':len(nonrest_inactive),
                     'inactive_nonrest_viseme_events':[reference(r) for r in nonrest_inactive],
                     'viseme_sample_counts':dict(Counter(str(r['event'].get('viseme')) for r in samples)),
                     'complaints':complaints,'rendered_idle_mouth_openness':None,
                     'limit':'Speech sample telemetry does not describe the base expression artwork, mouth raster, transition frame, or acoustic output.'},
            'required_missing_signals':['Final voiced microphone sample on an attributable clock; ASR-final receipt is not speech end.',
                'Recorded speaker audio/acoustic onset and cutoff; the trace removes PCM payloads.',
                'Renderer frame/asset IDs and mouth geometry/openness for idle, listening, thinking and transitions.',
                'Activity-overlay state/frame telemetry to verify whether thinking is visibly communicated.',
                'A face command ID propagated through renderer acceptance, transition completion and expiry reason.',
                'Human or scenario-rule annotations for useful answer onset, intended continuation and perceived expression.']}


def markdown(report):
    lines=['# Conversation timing audit','',
           f"Trace `{report['session'].get('trace_id')}`; status `{report['session'].get('status')}`. Source SHA-256 `{report.get('source_sha256','unavailable')}`.",'',
           'All intervals below use the same explicit server receipt clock. Playback means a browser notification, not measured speaker onset. Missing playback and useful-answer annotations are not assigned zero latency.','',
           '## Coverage','',json.dumps(report['counts'],ensure_ascii=False),'',
           '## Longest waits after user commitment','',
           '| Request | Commit → model start | Commit → public text | Commit → playback receipt | Evidence |',
           '|---|---:|---:|---:|---|']
    def ms(value):return 'unavailable' if value is None else f'{value:.0f} ms'
    def eid(value):return 'missing' if value is None else '#'+str(value['id'])
    for turn in report['longest_user_waits']:
        metric=turn['intervals_ms'];stage=turn['stages']
        text=str(turn['input_text']).replace('|','/').replace('\n',' ')
        lines.append(f"| {text} | {ms(metric['commit_to_model_start'])} | {ms(metric['commit_to_public_text'])} | {ms(metric['commit_to_playback_receipt'])} | {eid(stage['commit'])} → {eid(stage['model_start'])} → {eid(stage['first_public_text'])} → {eid(stage['playback_receipt'])} |")
    lines+=['','The JSON retains every generation, interruptions, queue delay and model HTTP-header timings. It does not equate a server thinking state with a visible thinking animation.','',
            'Public text means the first nonblank turn.delta published by the model protocol. This is neither a caption-render timestamp nor the onset of speech. Browser speech activity samples during these waits are retained in the JSON; they are sampled observations, not continuous acoustic measurements.','',
            '## User-turn latency distributions','',
            '| Stage | Observed / all attempts | Missing | Median | P90 |',
            '|---|---:|---:|---:|---:|']
    for key,metric in report['user_generation_distributions_ms'].items():
        lines.append(f"| {key} | {metric['n']} / {metric['denominator']} | {metric['missing']} | {ms(metric['median_ms'])} | {ms(metric['p90_ms'])} |")
    lines+=['','Missing observations, including interrupted generations, stay in the denominator. These are descriptive values from one conversation, not a controlled model comparison.','',
            '## Nearby user turns','']
    for split in report['nearby_user_commit_candidates']:
        responses='; '.join(f"{eid(v['event'])} {v['text'].strip()!r}" for v in split['intervening_assistant_finals']) or 'none'
        lines.append(f"- {eid(split['first'])} {split['first_text']!r} → {eid(split['second'])} {split['second_text']!r}: {ms(split['commit_gap_ms'])} between commitments. Intervening generated answer: {responses}. Playback receipts: {', '.join(eid(v) for v in split['intervening_playback_receipts']) or 'none'}. Resets: {', '.join(eid(v) for v in split['intervening_resets']) or 'none'}.")
    lines+=['','These are temporal candidates, not automatic judgments of intent. No incomplete-clause hold was recorded in this trace.' if report['counts']['incomplete_hold_events']==0 else '',
            '','## Face commands and browser state','',
            '| Command | Requested hold | Browser application | Next reported state | State lifetime | Displaced before associated playback? |',
            '|---|---:|---|---|---:|---|']
    for face in report['faces']:
        before=(f"yes, by {ms(face['displacement_to_playback_receipt_ms'])}" if face['displaced_before_playback_receipt'] else 'not established')
        lines.append(f"| {eid(face['command'])} {face['expression']} | {ms(face['requested_hold_ms'])} | {eid(face['browser_applied'])} | {eid(face['browser_displaced'])} {face['displaced_by'] or ''} | {ms(face['browser_state_lifetime_ms'])} | {before} |")
    lines+=['','Browser expression records describe selected state. They do not prove that a full raster face remained visibly settled for that duration. Matching uses expression name/pinned state because the browser records do not carry originating command IDs.']
    for face in report['faces']:
        if face['competing_command_before_hold_end']:
            lines.append(f"- {eid(face['command'])} {face['expression']} was followed by another face command after {ms(face['next_command_after_ms'])}, before its requested hold elapsed.")
    lines+=['','## Background acknowledgement versus result response','']
    for job in report['background_jobs']:
        m=job['intervals_ms']
        lines.append(f"- Job `{job['job_id']}`: started {eid(job['started'])}; terminal {eid(job['terminal'])} ({job['terminal_status']}); queued {eid(job['delivery_queued'])}. Initial response playback {eid(job['initial_playback_receipt'])} arrived {ms(m['user_commit_to_initial_playback_receipt'])} after user commitment. The separate report response {eid(job['report_playback_receipt'])} arrived after {ms(m['user_commit_to_report_playback_receipt'])}.")
        lines.append(f"  The job finished in {ms(m['job_start_to_terminal'])}; it waited {ms(m['terminal_to_delivery_queue'])} before delivery was queued. Last browser idle receipt → queue was {ms(m['last_idle_to_delivery_queue'])}. Queue → report playback receipt was {ms(m['queue_to_report_playback_receipt'])}. No useful-answer/audio onset was annotated; these are not interchangeable with that metric.")
        lines.append(f"  Initial generated response: {str(job['initial_generated_text']).strip()!r}. Separate generated report: {str(job['report_generated_text']).strip()!r}. Generated wording does not prove all those words were heard.")
    mouth=report['mouth']
    lines+=['','## Mouth while speech is inactive','',
            f"There are {mouth['sample_count']} browser speech samples, including {mouth['inactive_sample_count']} with audio_active=false. {mouth['inactive_nonrest_viseme_count']} of those request a speech viseme other than rest or none. This does not establish whether the idle/listening artwork itself has an open mouth."]
    for complaint in mouth['complaints']:
        rows=complaint['preceding_10s_samples']
        inactive=sum(r['audio_active'] is False for r in rows)
        lines.append(f"At {eid(complaint['event'])}, the user asks {complaint['text']!r}. In the preceding ten seconds, {inactive}/{len(rows)} sampled speech states were inactive. The JSON records their IDs; no actual mouth raster or screen frames are available.")
    lines+=['','## Signals needed to settle the remaining questions','']+['- '+v for v in report['required_missing_signals']]
    if report['session'].get('status')=='active':
        lines+=['','The export is marked active. Counts describe the captured interval only; an active export does not establish an unfinished model generation.']
    lines+=['','No provider calls, browser changes or production fixes were performed by this analyzer.','']
    return '\n'.join(lines)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace',type=Path)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    data=args.trace.read_bytes()
    report=analyze(json.loads(data.decode('utf8')))
    report.update(source_path=str(args.trace.resolve()),source_sha256=hashlib.sha256(data).hexdigest(),
                  analyzer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir/'TIMING-AUDIT.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    (args.output_dir/'TIMING-AUDIT.md').write_text(markdown(report),encoding='utf8')
    print(json.dumps(report['counts']))


if __name__=='__main__':main()
