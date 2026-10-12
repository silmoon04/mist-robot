"""Regression tests for observable evidence, clock boundaries and turn attribution."""
import copy
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from expectation_trace_audit import analyze, interval, markdown


def row(event_id, time, kind='debug_model', *, source='server', clock='trace_server:test', **event):
    return {'id':event_id, 'elapsed_ms':time, 'clock_id':clock, 'source':source,
            'event':{'type':kind, **event}}


def direct_turn():
    return [
        row(1,90,phase='stt_final',text='Hello'),
        row(2,100,'transcript_done',role='user',text='Hello'),
        row(3,105,phase='user_committed',text='Hello',revision=1,endpoint='speech_final'),
        row(4,150,phase='thinking_started',input_text='Hello',revision=1,turn_id='a'),
        row(5,200,phase='text_delta',turn_id='a',delta='\n\n'),
        row(6,300,phase='text_delta',turn_id='a',delta='Hi'),
        row(7,310,'turn.delta',turn_id='a',delta='Hi'),
        row(8,320,'tts_phrase',sequence=4),
        row(9,330,phase='thinking_finished',turn_id='a',generated_text='Hi'),
        row(10,350,'audio_delivery',seq=4,epoch=2),
        row(11,400,'playback_started',source='browser',sequence=4,epoch=2),
    ]


class ClockTests(unittest.TestCase):
    def test_only_explicit_same_outer_clock_is_subtracted(self):
        a=row(1,10,client_ms=10000,at_ms=222)
        b=row(2,35,client_ms=-200,at_ms=7)
        self.assertEqual(interval(a,b),25)
        for clock in (None,'browser:other',''):
            self.assertIsNone(interval(a,{**b,'clock_id':clock}))
        self.assertIsNone(interval({**a,'clock_id':None},{**b,'clock_id':None}))

    def test_bad_or_backward_time_remains_missing(self):
        a=row(1,10)
        for timestamp in (True,'30',None,9,math.nan,math.inf):
            self.assertIsNone(interval(a,row(2,timestamp)))
        self.assertIsNone(interval(None,a))
        self.assertEqual(interval(a,row(2,10)),0)


class TurnTests(unittest.TestCase):
    def test_queue_public_text_audio_and_usefulness_are_separate(self):
        report=analyze({'events':direct_turn()})
        turn=report['turns'][0]
        self.assertEqual(turn['stages']['first_any_text']['id'],5)
        self.assertEqual(turn['stages']['first_nonblank_text']['id'],6)
        self.assertEqual(turn['stages']['first_public_text']['id'],7)
        self.assertEqual(turn['intervals_ms']['commit_to_model_start'],45)
        self.assertEqual(turn['intervals_ms']['commit_to_public_text'],205)
        self.assertEqual(turn['intervals_ms']['commit_to_playback_receipt'],295)
        self.assertEqual(turn['intervals_ms']['last_asr_final_to_commit'],15)
        self.assertIsNone(turn['first_useful_audio_ms'])
        self.assertIsNone(turn['usefulness_annotation'])

    def test_playback_requires_browser_source_sequence_and_epoch(self):
        rows=direct_turn()[:-1]+[
            row(11,360,'playback_started',source='browser_command',sequence=4,epoch=2),
            row(12,370,'playback_started',source='browser',sequence=5,epoch=2),
            row(13,380,'playback_started',source='browser',sequence=4,epoch=1),
            row(14,390,'debug_client',source='browser_command',event={'type':'playback_started','sequence':4,'epoch':2}),
            row(15,400,'playback_started',source='browser',sequence=4,epoch=2),
        ]
        result=analyze({'events':rows})
        self.assertEqual(result['turns'][0]['stages']['playback_receipt']['id'],15)
        self.assertEqual(result['counts']['with_playback_receipt'],1)

    def test_missing_and_discarded_audio_stay_in_denominator(self):
        rows=direct_turn()[:9]+[
            row(12,500,phase='user_committed',text='Wait',revision=2),
            row(13,501,phase='thinking_started',input_text='Wait',revision=2,turn_id='b'),
            row(14,550,phase='interrupted_generation_discarded',turn_id='b'),
        ]
        result=analyze({'events':rows})
        metric=result['user_generation_distributions_ms']['commit_to_playback_receipt']
        self.assertEqual((metric['n'],metric['missing'],metric['denominator']),(0,2,2))
        self.assertIsNone(metric['median_ms'])
        self.assertEqual(result['counts']['discarded_generations'],1)
        self.assertEqual(result['turns'][1]['status'],'discarded')

    def test_continuation_records_answer_and_reset_without_acoustic_claim(self):
        rows=direct_turn()+[
            row(12,410,'transcript_done',role='assistant',text='Hi'),
            row(13,420,'audio_reset',epoch=3),
            row(14,1000,phase='user_committed',text='I meant hello to the dog',revision=2),
        ]
        pair=analyze({'events':rows})['nearby_user_commit_candidates'][0]
        self.assertEqual(pair['commit_gap_ms'],895)
        self.assertEqual(pair['intervening_assistant_finals'][0]['text'],'Hi')
        self.assertEqual(pair['intervening_playback_receipts'][0]['id'],11)
        self.assertEqual(pair['intervening_resets'][0]['id'],13)
        self.assertIn('Temporal candidate only',pair['interpretation'])


class FaceAndMouthTests(unittest.TestCase):
    def test_rapid_overwrite_does_not_invent_missing_face_or_settled_duration(self):
        rows=direct_turn()[:4]+[
            row(5,160,'tool',name='set_expression',turn_id='a',result={'expression':'happy'}),
            row(6,161,'face',expression='happy',duration_ms=2000),
            row(7,162,'tool',name='set_expression',turn_id='a',result={'expression':'curious'}),
            row(8,163,'face',expression='curious',duration_ms=2000),
            row(9,164,'expression',source='browser',name='happy',variant='h',pinned=True),
            row(10,165,'tool',name='set_expression',turn_id='a',result={'expression':'smug'}),
            row(11,166,'face',expression='smug',duration_ms=400),
            row(12,200,'expression',source='browser',name='smug',variant='s',pinned=True),
            row(13,210,'tts_phrase',sequence=1),
            row(14,220,'audio_delivery',seq=1,epoch=1),
            row(15,230,'expression',source='browser',name='neutral',variant='n',pinned=False),
            row(16,240,'playback_started',source='browser',sequence=1,epoch=1),
        ]
        faces=analyze({'events':rows})['faces']
        self.assertTrue(faces[0]['competing_command_before_hold_end'])
        self.assertEqual(faces[0]['next_command_after_ms'],2)
        self.assertIsNone(faces[1]['browser_applied'])
        self.assertEqual(faces[2]['displacement_to_playback_receipt_ms'],10)
        self.assertIsNone(faces[2]['full_raster_visible_duration_ms'])
        self.assertEqual(faces[2]['browser_state_lifetime_ms'],30)

    def test_mouth_telemetry_is_not_rendered_openness(self):
        rows=[
            row(1,10,'audio_scheduled',source='browser',audio_active=False,viseme=None),
            row(2,20,'audio_scheduled',source='browser',audio_active=False,viseme='rest'),
            row(3,30,'audio_scheduled',source='browser',audio_active=True,viseme='AA'),
            row(4,40,'debug_client',source='browser_command',event={'type':'audio_scheduled','audio_active':False,'viseme':'AA'}),
            row(5,50,'transcript_done',role='user',text='Why is your mouth open?'),
        ]
        result=analyze({'events':rows})['mouth']
        self.assertEqual((result['sample_count'],result['inactive_sample_count']),(3,2))
        self.assertEqual(result['inactive_nonrest_viseme_count'],0)
        self.assertIsNone(result['rendered_idle_mouth_openness'])
        self.assertEqual(len(result['complaints'][0]['preceding_10s_samples']),3)
        rows.append(row(6,60,'audio_scheduled',source='browser',audio_active=False,viseme='AA'))
        self.assertEqual(analyze({'events':rows})['mouth']['inactive_nonrest_viseme_count'],1)


class BackgroundTests(unittest.TestCase):
    def test_ack_and_report_are_distinct_and_wrong_job_report_is_not_linked(self):
        rows=direct_turn()
        rows.extend([
            row(12,410,'brain_job',job_id='job-123',status='running'),
            row(13,420,'tool',name='start_background_task',turn_id='a',result={'job_id':'job-123'}),
            row(14,450,'brain_job',job_id='job-123',status='complete'),
            row(15,600,'playback_idle',source='browser'),
            row(16,601,'brain_delivery',job_id='job-123'),
            row(17,610,phase='thinking_started',turn_id='unrelated',application_context=True,input_text='other-job'),
            row(18,650,phase='thinking_finished',turn_id='unrelated',generated_text='Other report'),
            row(19,700,phase='thinking_started',turn_id='report',application_context=True,input_text='Application data: {"job_id":"job-123"}'),
            row(20,710,phase='text_delta',turn_id='report',delta='Report'),
            row(21,720,'tts_phrase',sequence=5),
            row(22,730,'audio_delivery',seq=5,epoch=2),
            row(23,740,phase='thinking_finished',turn_id='report',generated_text='Report'),
            row(24,800,'playback_started',source='browser',sequence=5,epoch=2),
        ])
        result=analyze({'events':rows})
        job=result['background_jobs'][0]
        self.assertEqual(job['initial_response_turn_id'],'a')
        self.assertEqual(job['report_response_turn_id'],'report')
        self.assertEqual(job['intervals_ms']['user_commit_to_initial_playback_receipt'],295)
        self.assertEqual(job['intervals_ms']['user_commit_to_report_playback_receipt'],695)
        self.assertEqual(job['intervals_ms']['terminal_to_delivery_queue'],151)
        self.assertEqual(job['intervals_ms']['last_idle_to_delivery_queue'],1)
        self.assertIsNone(job['first_useful_audio_ms'])
        self.assertIsNone(result['turns'][-1]['stages']['commit'])
        self.assertEqual(result['counts']['user_generations'],1)


class InputTests(unittest.TestCase):
    def test_input_is_not_mutated_and_empty_has_explicit_denominators(self):
        document={'session':{'status':'ended'},'events':direct_turn()}
        original=copy.deepcopy(document)
        result=analyze(document)
        self.assertEqual(document,original)
        self.assertNotIn('export is marked active',markdown(result))
        empty=analyze({'events':[]})
        self.assertEqual(empty['counts']['events'],0)
        self.assertEqual(empty['turns'],[])
        self.assertIsNone(empty['capture']['duration_ms'])

    def test_duplicate_out_of_order_or_invalid_events_rejected(self):
        for events in ([row(1,10),row(1,11)],[row(2,10),row(1,11)], [{'id':1,'event':'bad'}]):
            with self.assertRaises(ValueError):analyze({'events':events})


if __name__=='__main__':unittest.main()
