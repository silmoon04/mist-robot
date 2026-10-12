"""Offline contracts for audio cancellation, sensor freshness and bounded previews."""
import asyncio,base64,json,sys,tempfile,time,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from duplex.runtime import RobotRuntime,finite,specs
from duplex.conversion import Segmenter,VoiceMask
from duplex.server import Conversation,create_app
from types import SimpleNamespace
from duplex.sensors import SensorClock
from aiohttp.test_utils import TestClient,TestServer

class RuntimeTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.r=RobotRuntime(self.tmp.name)
    def packet(self,**kw):return {'kind':'phone_motion','seq':1,'captured_at':100,'values':{'ax':0,'ay':9.81,'az':0},**kw}
    def test_fresh_then_stale(self):
        self.r.ingest(self.packet(),100);self.assertTrue(self.r.snapshot(101)['sensors']['phone_motion']['fresh']);self.assertFalse(self.r.snapshot(103)['sensors']['phone_motion']['fresh'])
    def test_reject_timestamp(self):
        for t in [90,104,float('nan'),True]:
            with self.subTest(t=t),self.assertRaises(ValueError):self.r.ingest(self.packet(captured_at=t),100)
    def test_reject_out_of_order(self):
        self.r.ingest(self.packet(),100)
        with self.assertRaises(ValueError):self.r.ingest(self.packet(),100)
    def test_ignores_sensor_instruction(self):
        self.r.ingest(self.packet(values={'ax':1,'instruction':'move physical robot'}),100)
        self.assertEqual(self.r.snapshot(100)['sensors']['phone_motion']['values'],{'ax':1})
    def test_phone_not_body(self):
        self.r.ingest(self.packet(),100);self.assertEqual(self.r.snapshot(100)['sensors']['phone_motion']['coordinate_frame'],'phone_device')
    def test_sensor_bad_vectors(self):
        for v in [True,float('inf'),1e100,'1']:
            with self.subTest(v=v),self.assertRaises(ValueError):self.r.ingest(self.packet(values={'ax':v}),100)
    def test_no_hardware(self):
        self.assertFalse(self.r.snapshot()['hardware_connected']);r=self.r.call('preview_motion',{'action':'walk','amount':.1});self.assertFalse(r['hardware_executed']);self.assertEqual(r['status'],'preview_only')
    def test_yaw_19(self):
        self.r.call('preview_motion',{'action':'turn','amount':19})
        with self.assertRaises(ValueError):self.r.call('preview_motion',{'action':'turn','amount':19.1})
    def test_walk_limit(self):
        with self.assertRaises(ValueError):self.r.call('preview_motion',{'action':'walk','amount':2})
    def test_no_wheels(self):
        with self.assertRaises(ValueError):self.r.call('preview_motion',{'action':'drive','amount':.1})
    def test_usb_gate(self):self.assertEqual(self.r.call('pan_phone',{'angle_deg':30,'usb_connected':True})['status'],'refused')
    def test_pan_bounds(self):
        for v in [-181,181,True]:
            with self.assertRaises(ValueError):self.r.call('pan_phone',{'angle_deg':v,'usb_connected':False})
    def test_stop_latches(self):
        self.r.call('preview_motion',{'action':'walk','amount':.1});self.r.call('stop_robot',{});self.assertFalse(self.r.intents);self.assertEqual(self.r.call('preview_motion',{'action':'stand'})['status'],'refused')
    def test_hot_report_refuses(self):
        self.r.ingest({'kind':'robot_telemetry','seq':1,'captured_at':time.time(),'values':{'servo_temp_c':51}});self.assertEqual(self.r.call('preview_motion',{'action':'stand'})['status'],'refused')
    def test_persist_preference(self):
        self.r.call('remember',{'note':'No jokes when tired.'});other=RobotRuntime(self.tmp.name);self.assertEqual(other.call('recall',{})['notes'][0]['text'],'No jokes when tired.')
    def test_unknown_tool(self):
        with self.assertRaises(ValueError):self.r.call('shell',{'command':'anything'})
    def test_tool_catalog(self):self.assertEqual(len(specs()),7);self.assertTrue(all(not x['inputSchema']['additionalProperties'] for x in specs()))

class SegmentTests(unittest.TestCase):
    def test_silence_free(self):
        s=Segmenter();self.assertEqual(s.feed(b'\0'*32000),[])
    def test_bounded_segments(self):
        s=Segmenter();pcm=np.full(320,800,dtype='<i2').tobytes();out=[]
        for _ in range(150):out.extend(s.feed(pcm))
        self.assertTrue(out);self.assertTrue(all(len(p)<=57600 for p in out))
    def test_reset_no_tail(self):
        s=Segmenter();s.feed(np.full(1000,800,dtype='<i2').tobytes());s.reset();self.assertFalse(s.buffer);self.assertFalse(s.active)

    def test_preserves_first_word_context(self):
        s=Segmenter();pcm=np.full(320,800,dtype='<i2').tobytes()
        for _ in range(60):self.assertEqual(s.feed(pcm),[])
        out=[]
        for _ in range(4):out.extend(s.feed(b'\0'*640))
        self.assertEqual(b''.join(out),pcm*60+b'\0'*2560)
    def test_equal_caps_and_lossless_tail(self):
        s=Segmenter();pcm=np.full(320,800,dtype='<i2').tobytes();out=[]
        for _ in range(190):out.extend(s.feed(pcm))
        for _ in range(9):out.extend(s.feed(b'\0'*640))
        self.assertEqual([len(p) for p in out[:2]],[57600,57600])
        self.assertEqual(b''.join(out),pcm*190+b'\0'*5760)
    def test_complete_short_reply_flushes(self):
        s=Segmenter();pcm=np.full(320,800,dtype='<i2').tobytes();out=[]
        for _ in range(15):out.extend(s.feed(pcm))
        for _ in range(9):out.extend(s.feed(b'\0'*640))
        self.assertEqual(len(out),1)
        self.assertEqual(out[0],pcm*15+b'\0'*5760)

class SensorClockTests(unittest.TestCase):
    def test_monotonic_not_epoch(self):
        c=SensorClock();d={'type':'android.sensor.gyroscope','values':[1,2,3],'timestamp':1_000_000_000}
        self.assertEqual(c.packet(d,100)['captured_at'],100)
        self.assertEqual(c.packet(dict(d,timestamp=2_000_000_000),101)['captured_at'],101)
    def test_backward_timestamp(self):
        c=SensorClock();d={'type':'android.sensor.gyroscope','values':[1,2,3],'timestamp':10}
        c.packet(d,100)
        with self.assertRaises(ValueError):c.packet(d,101)
    def test_clock_drift(self):
        c=SensorClock();d={'type':'android.sensor.gyroscope','values':[1,2,3],'timestamp':10}
        c.packet(d,100)
        with self.assertRaises(ValueError):c.packet(dict(d,timestamp=100_000_000_000),101)

class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_current_failed_analysis_reports_once_without_partial_answer(self):
        notices=[];events=[];delivered=asyncio.Event()
        class Socket:
            closed=False
            async def send_json(self,event):events.append(event)
        class Voice:
            supports_background_result_guard=True
            async def context(self,text,**kwargs):
                notices.append((text,kwargs));delivered.set()
        with tempfile.TemporaryDirectory() as tmp:
            c=Conversation({'runtime':RobotRuntime(tmp)},Socket())
            c.voice=Voice();c.mask=SimpleNamespace(pending={},diagnostic=lambda *a,**kw:None)
            c.user_revision=3
            for job_id,status,revision in [('current','failed',3),('old','failed',2),('cancelled','cancelled',3),('stale','stale',3),('running','running',3)]:
                c.brain.jobs[job_id]={'job_id':job_id,'status':status,'revision':revision,'announced':False,
                                      'summary':'UNVERIFIED_PARTIAL_RESULT','error_type':'UNVERIFIED_CAUSE'}
            task=asyncio.create_task(c.deliver_results())
            try:
                await asyncio.wait_for(delivered.wait(),1)
                await asyncio.sleep(.23)
                self.assertEqual(len(notices),1)
                text,guard=notices[0]
                self.assertEqual(guard,{'job_id':'current'})
                self.assertIn('could not finish',text)
                self.assertIn('Do not invent',text)
                self.assertNotIn('UNVERIFIED_',text)
                self.assertTrue(c.brain.jobs['current']['announced'])
                self.assertTrue(all(not j['announced'] for key,j in c.brain.jobs.items() if key!='current'))
                report=next(e for e in events if e.get('type')=='brain_delivery')
                self.assertEqual(report['terminal_status'],'failed')
                self.assertFalse(report['playback_verified'])
            finally:
                task.cancel();await asyncio.gather(task,return_exceptions=True);await c.brain.close()

    async def test_ordered_delivery(self):
        from collections import deque
        events=[]
        async def emit(e):events.append(e)
        m=VoiceMask('fake',emit);m.pending={1:{'epoch':0,'chunks':deque([b'\1\0']),'done':True}}
        await m.drain();self.assertFalse(events)
        m.pending[0]={'epoch':0,'chunks':deque([b'\2\0']),'done':True};await m.drain();self.assertEqual([e['seq'] for e in events],[0,1])
    async def test_interrupt_invalidates_audio(self):
        events=[]
        async def emit(e):events.append(e)
        m=VoiceMask('fake',emit);m.sequence=2;await m.interrupt();self.assertEqual(m.epoch,1);self.assertEqual(m.next,2);self.assertEqual(events[-1]['type'],'audio_reset')
    async def test_close_cancels_requests(self):
        async def emit(e):pass
        m=VoiceMask('fake',emit);t=asyncio.create_task(asyncio.sleep(30));m.tasks.add(t);await m.close();self.assertTrue(t.cancelled())
    async def test_pair_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=SimpleNamespace(run_dir=tmp,pair_code='fixture-code',enable_fixtures=False,cert=None)
            async with TestClient(TestServer(create_app(args))) as client:
                r=await client.post('/pair',json={'code':'fixture-code'},headers={'Origin':'https://foreign.example'});self.assertEqual(r.status,403)
                r=await client.get('/config');self.assertFalse((await r.json())['paired'])
                r=await client.get('/voice');self.assertEqual(r.status,403)
    async def test_no_ambient_sensor_speech(self):
        class Voice:
            async def context(self,text):raise AssertionError('Sensors must not trigger speech')
        class Socket:
            closed=False
            async def send_json(self,event):pass
        with tempfile.TemporaryDirectory() as tmp:
            c=Conversation({'runtime':RobotRuntime(tmp),'enable_fixtures':False},Socket());c.voice=Voice()
            await c.handle({'type':'sensors','packet':{'kind':'phone_motion','seq':1,'captured_at':time.time(),'values':{'ax':0}}})
    async def test_early_stop_and_negation(self):
        class Socket:
            closed=False
            async def send_json(self,event):pass
        with tempfile.TemporaryDirectory() as tmp:
            c=Conversation({'runtime':RobotRuntime(tmp)},Socket())
            await c.realtime_event({'type':'input_transcript.added','item':{'text':'Do not '}})
            await c.realtime_event({'type':'input_transcript.added','item':{'text':'stop'}})
            self.assertFalse(c.runtime.estop)
            await c.realtime_event({'type':'turn.done','turn':{'role':'user','id':'negated','transcript':'Do not stop'}})
            await c.realtime_event({'type':'input_transcript.added','item':{'text':'Stop'}})
            self.assertTrue(c.runtime.estop)

    async def test_aligned_caption_debug_event_is_recorded(self):
        recorded=[]
        with tempfile.TemporaryDirectory() as tmp:
            c=Conversation({'runtime':RobotRuntime(tmp),'journal':SimpleNamespace(record=lambda e,s:recorded.append((e,s)))},SimpleNamespace(closed=False))
            event={'type':'caption_progress','text':'Maybe','source':'elevenlabs_normalized_alignment','epoch':1,'sequence':0}
            await c.handle({'type':'debug_client','event':event})
            self.assertEqual(recorded,[(event,'browser')])
            configuration={'type':'playback_configuration','playback_buffer_ms':120}
            await c.handle({'type':'debug_client','event':configuration})
            self.assertEqual(recorded[-1],(configuration,'browser'))
            with self.assertRaisesRegex(ValueError,'Unsupported debug event'):
                await c.handle({'type':'debug_client','event':{'type':'unknown'}})

    async def test_native_interruption_clears_already_delivered_audio(self):
        events=[];received=[]
        class Socket:
            closed=False
            async def send_json(self,event):events.append(event)
        class Voice:
            track=SimpleNamespace(append=received.append)
            async def interrupt(self):pass
        with tempfile.TemporaryDirectory() as tmp:
            c=Conversation({'runtime':RobotRuntime(tmp)},Socket());c.voice=Voice()
            c.mask=VoiceMask('fake',c.emit);c.assistant_turn='old';c.assistant_done=True
            await c.realtime_event({'type':'turn.created','turn':{'role':'user','id':'u','start_ms':100}})
            self.assertTrue(any(e['type']=='audio_reset' for e in events))
            self.assertTrue(c.blocked)
            await c.handle({'type':'mic','pcm':base64.b64encode(b'\1\0'*320).decode()})
            self.assertEqual(received,[b'\1\0'*320],'mic continues during interruption')
            await c.realtime_event({'type':'turn.created','turn':{'role':'assistant','id':'new','start_ms':200}})
            self.assertFalse(c.mask.muted)

if __name__=='__main__':unittest.main(verbosity=2)
