"""Loopback-only experiment server around the production voice and playback paths."""
import argparse
import asyncio
import base64
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import sys
import time

from aiohttp import web

HERE=Path(__file__).resolve().parent
BRAIN=HERE.parents[1]
sys.path.insert(0,str(BRAIN));sys.path.insert(0,str(BRAIN/'harness'));sys.path.insert(0,str(HERE))
from duplex import server
from duplex.runtime import RobotRuntime


def save(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')


class CapturedConversation(server.Conversation):
    async def emit(self,event):
        folder=self.app.get('lab_current')
        if folder:
            copy=dict(event)
            if event.get('type')=='audio':
                pcm=base64.b64decode(copy.pop('pcm'))
                copy.update(pcm_bytes=len(pcm),pcm_sha256=hashlib.sha256(pcm).hexdigest())
                with (folder/('received-epoch-'+str(event['epoch'])+'.pcm')).open('ab') as f:f.write(pcm)
            with (folder/'server_events.jsonl').open('a',encoding='utf-8') as f:
                f.write(json.dumps({'server_ms':(time.perf_counter()-self.app['lab_origin'])*1000,'event':copy},ensure_ascii=False)+'\n')
        await super().emit(event)

    async def realtime_event(self,event):
        folder=self.app.get('lab_current')
        if folder:
            # Native protocol observation, never interpreted as browser playback.
            selected={k:event[k] for k in ('type','turn_id','turn','delta','item') if k in event}
            with (folder/'native_events.jsonl').open('a',encoding='utf-8') as f:
                f.write(json.dumps({'server_ms':(time.perf_counter()-self.app['lab_origin'])*1000,'event':selected},ensure_ascii=False)+'\n')
        await super().realtime_event(event)


def create_lab(args):
    endpoint_ms=getattr(args,'endpoint_ms',300)
    if type(endpoint_ms) is not int or not 100<=endpoint_ms<=2000:
        raise ValueError('Lab endpoint must be an integer from 100 to 2000 ms')
    effective_endpoint_ms=endpoint_ms if args.backend=='cascade' else None
    if args.backend=='cascade':
        from cascade_voice import CascadeVoice
        server.NativeVoice=CascadeVoice
    server.Conversation=CapturedConversation
    # One isolated server process per backend. Production process/config stay unchanged.
    os.environ['MIST_BRAIN_MODEL']=args.model
    os.environ['MIST_BACKGROUND_MODEL']=args.background_model
    os.environ['MIST_LAB_MODEL']=args.model
    os.environ['MIST_LAB_PROVIDER']=args.provider
    os.environ['MIST_LAB_FLOOR']=args.floor
    os.environ['MIST_LAB_ENDPOINT_MS']=str(endpoint_ms)
    args.enable_fixtures=True;args.sensor_url=None;args.cert=None;args.key=None;args.pair_code=None
    args.speech_backend='streaming-tts'
    app=server.create_app(args)
    app._client_max_size=32*1024*1024
    output=Path(args.run_dir).resolve()
    fixtures=Path(args.fixtures).resolve()
    manifest=json.loads((fixtures/'manifest.json').read_text(encoding='utf-8'))
    ids={c['id']:c for c in manifest['fixtures']}
    app['lab_current']=None;app['lab_origin']=time.perf_counter();app['lab_sequence']=0
    def authorize(r):
        if r.headers.get('Origin')!=f'http://{r.host}':raise web.HTTPForbidden()
    async def setup(r):
        authorize(r)
        response=web.json_response({'fixtures':manifest['fixtures'],'backend':args.backend,'model':args.model,'floor':args.floor,'endpoint_ms':effective_endpoint_ms,
            'capture_scope':'Synthetic input to production browser WebAudio playback. No physical microphone, room AEC or human ratings.'})
        response.set_cookie('mist_session',app['cookie'],httponly=True,samesite='Strict')
        return response
    async def begin(r):
        authorize(r);packet=await r.json();cid=packet.get('case_id')
        if cid not in ids:raise web.HTTPBadRequest(text='Unknown case')
        for _ in range(50):
            if app['sessions']['owner'] is None:break
            await asyncio.sleep(.1)
        if app['sessions']['owner'] is not None:raise web.HTTPConflict(text='Previous voice session still closing')
        app['lab_sequence']+=1
        folder=output/(f'{app["lab_sequence"]:03d}-'+cid.split('.')[-1]);folder.mkdir(exist_ok=False)
        app['lab_current']=folder
        app['runtime']=RobotRuntime(folder/'state')
        save(folder/'fixture.json',ids[cid])
        save(folder/'configuration.json',{'backend':args.backend,'model':args.model,'provider':args.provider,'floor':args.floor,'endpoint_ms':effective_endpoint_ms,'background_model':args.background_model,'started_unix':time.time(),'server_origin_perf':app['lab_origin']})
        return web.json_response({'case_id':cid,'run_id':folder.name})
    async def seed(r):
        authorize(r);data=await r.json();text=data.get('text')
        if not isinstance(text,str) or not 1<=len(text)<=1500:raise web.HTTPBadRequest()
        session=app['sessions']['owner']
        if not session or not session.voice:raise web.HTTPConflict(text='No voice session')
        await session.voice.say_text('For this reading test, read this passage aloud exactly, without an introduction: '+text)
        return web.json_response({'requested':True,'setup':'text-seeded native generation; not microphone input'})
    async def result(r):
        authorize(r);data=await r.json();folder=app['lab_current']
        if folder is None:raise web.HTTPConflict()
        if data.get('case_id')!=json.loads((folder/'fixture.json').read_text(encoding='utf-8'))['id']:raise web.HTTPBadRequest(text='Case mismatch')
        save(folder/'browser.json',data)
        print(json.dumps({'case':data['case_id'],'status':data.get('status'),'output':folder.name}),flush=True)
        return web.json_response({'saved':True,'run_id':folder.name})
    async def audio(r):
        authorize(r);folder=app['lab_current']
        if folder is None:raise web.HTTPConflict()
        raw=await r.read()
        kind=r.query.get('kind','audio');fmt=r.query.get('format','webm')
        if kind not in ('audio','face_video') or fmt not in ('webm','ogg','mp4'):raise web.HTTPBadRequest()
        filename=('browser-output' if kind=='audio' else 'face-output')+'.'+fmt
        (folder/filename).write_bytes(raw)
        save(folder/(kind+'-recording.json'),{'file':filename,'bytes':len(raw),'mime':r.content_type,'sha256':hashlib.sha256(raw).hexdigest(),'scope':'Digital WebAudio/canvas capture; not external acoustic recording'})
        return web.json_response({'saved':True,'bytes':len(raw)})
    lab_assets=output/'sources'/HERE.relative_to(BRAIN.parent)
    app.router.add_get('/lab',lambda r:web.FileResponse(lab_assets/'browser_lab.html'))
    app.router.add_get('/lab.js',lambda r:web.FileResponse(lab_assets/'browser_lab.js'))
    app.router.add_post('/lab/setup',setup);app.router.add_post('/lab/begin',begin);app.router.add_post('/lab/seed',seed)
    app.router.add_post('/lab/result',result);app.router.add_post('/lab/audio',audio)
    app.router.add_static('/lab/fixture/',fixtures/'audio',show_index=False)
    log=logging.getLogger('mist.voice');log.setLevel(logging.INFO);log.propagate=False
    handler=logging.FileHandler(output/'diagnostics.jsonl',encoding='utf-8');handler.setFormatter(logging.Formatter('%(message)s'));log.addHandler(handler)
    sources={}
    for p in list(HERE.glob('*.py'))+list(HERE.glob('browser_lab.*'))+list((BRAIN/'duplex').glob('*.py'))+list((BRAIN/'duplex/static').glob('*.js')):
        rel=p.relative_to(BRAIN.parent)
        dest=output/'sources'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
        sources[rel.as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    save(output/'manifest.json',{'backend':args.backend,'model':args.model,'provider':args.provider,'floor':args.floor,'endpoint_ms':effective_endpoint_ms,'source_hashes':sources,
        'input_manifest_sha256':hashlib.sha256((fixtures/'manifest.json').read_bytes()).hexdigest(),'evidence_scope':'software_e2e','physical_audio':False,'human_quality':'unrated'})
    return app


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=9043);p.add_argument('--run-dir',required=True);p.add_argument('--fixtures',required=True)
    p.add_argument('--backend',choices=['native','cascade'],default='native');p.add_argument('--provider',default='codex');p.add_argument('--model',default='gpt-6-luna');p.add_argument('--background-model',default='gpt-6-luna');p.add_argument('--floor',default='cancel_all')
    p.add_argument('--endpoint-ms',type=int,default=300,help='Deepgram silence endpoint in ms, from 100 to 2000; cascade only')
    args=p.parse_args()
    if not 100<=args.endpoint_ms<=2000:p.error('--endpoint-ms must be from 100 to 2000')
    Path(args.run_dir).mkdir(parents=True,exist_ok=False)
    web.run_app(create_lab(args),host='127.0.0.1',port=args.port,print=lambda s:print('Synthetic voice lab ready on port '+str(args.port),flush=True))
