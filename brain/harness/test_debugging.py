import asyncio,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from duplex.debugging import DebugJournal
from duplex.server import create_app
from aiohttp.test_utils import TestClient,TestServer

class Tests(unittest.IsolatedAsyncioTestCase):
    def test_secrets_and_audio_excluded(self):
        j=DebugJournal();j.record({'type':'event','pcm':'raw','authorization':'secret','nested':{'api_key':'secret','text':'visible'}})
        s=json.dumps(j.since(0));self.assertNotIn('secret',s);self.assertNotIn('raw',s);self.assertIn('visible',s)
    def test_bounded_trace_and_cursor(self):
        j=DebugJournal()
        for i in range(2200):j.record({'type':'test','n':i})
        self.assertEqual(len(j.rows),2000);self.assertEqual(j.since(2198)['cursor'],2200);self.assertEqual(len(j.since(2198)['events']),2)
    def test_audio_sampling(self):
        j=DebugJournal()
        for _ in range(100):j.record({'type':'audio','epoch':0,'seq':0,'pcm':'abcd'})
        self.assertEqual(len(j.rows),1);self.assertNotIn('pcm',j.rows[0]['event'])
    def test_paging_does_not_skip_retained_events(self):
        j=DebugJournal()
        for i in range(1800):j.record({'type':'event'})
        cursor=0;ids=[]
        while cursor<j.sequence:
            page=j.since(cursor);ids.extend(r['id'] for r in page['events']);cursor=page['cursor']
        self.assertEqual(ids,list(range(1,1801)))
    async def test_debug_requires_pairing(self):
        with tempfile.TemporaryDirectory() as d:
            app=create_app(SimpleNamespace(run_dir=d,pair_code='test',enable_fixtures=False,cert=None))
            async with TestClient(TestServer(app)) as client:
                self.assertEqual((await client.get('/debug/events')).status,403)
                self.assertEqual((await client.get('/expressions')).status,200)
                origin=str(client.make_url('/')).rstrip('/')
                self.assertEqual((await client.post('/pair',json={'code':'test'},headers={'Origin':origin})).status,200)
                app['journal'].record({'type':'test'})
                data=await(await client.get('/debug/events')).json();self.assertTrue(data['events'])
                recovered=await(await client.get('/debug/events?after=999999&trace=old-server')).json();self.assertTrue(recovered['events'])
                self.assertEqual((await client.get('/debug/events?after=bad')).status,400)

if __name__=='__main__':unittest.main(verbosity=2)
