"""Cached synthetic speech inputs with explicit gaps and measured WAV durations."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
import wave

import httpx
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'harness'))
from pi_client import load_env


def save(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')


def wav(path,pcm):
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(pcm)


def read_pcm(path):
    with wave.open(str(path),'rb') as w:
        assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,16000)
        return w.readframes(w.getnframes())


def synthesize(text,directory,key):
    spec={'text':text,'provider':'deepgram','model':'aura-2-thalia-en','sample_rate':16000}
    name=hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest()[:20]+'.wav'
    target=directory/name
    if not target.exists():
        r=httpx.post('https://api.deepgram.com/v1/speak?model=aura-2-thalia-en&encoding=linear16&sample_rate=16000&container=none',
            headers={'Authorization':'Token '+key},json={'text':text},timeout=35)
        if r.status_code!=200:raise RuntimeError('Input synthesis HTTP '+str(r.status_code))
        if not r.content or len(r.content)%2:raise RuntimeError('Invalid synthesis PCM')
        wav(target,r.content)
    return name


def build(suite,output):
    output.mkdir(parents=True,exist_ok=True)
    audio=output/'audio';audio.mkdir(exist_ok=True)
    cases=[c for c in suite['cases'] if c['mode']=='timed_audio']
    texts={e['text'] for c in cases for e in c.get('timeline',[]) if e['type'] in ('user_start','user_resume','background_speech_start') and e.get('text')}
    texts.update(t['user'] for c in cases for t in c.get('turns',[]))
    key=load_env()['DEEPGRAM_API_KEY']
    with ThreadPoolExecutor(max_workers=3) as pool:
        names=dict(zip(sorted(texts),pool.map(lambda t:synthesize(t,audio,key),sorted(texts))))
    fixtures=[]
    for case in cases:
        slug=case['id'].split('.')[-1]
        entry={'id':case['id'],'title':case['title'],'steps':[],'tail_ms':11000,
            'speech_fixture':'synthetic Deepgram Aura2 Thalia; not a recording of a human',
            'source_mode':'timed_audio','conditions_uncontrolled':[], 'rubric':case['rubric']}
        timeline=case.get('timeline',[])
        seed=next((e['text'] for e in timeline if e['type']=='assistant_start'),None)
        if seed:
            entry['steps'].append({'type':'seed_text','text':seed,'trigger':'ready','delay_ms':0})
            entry['setup_note']='The native model is asked to read the seed. Input then begins relative to actual browser playback, not the original fixed timestamp.'
        utterances=[]
        for i,e in enumerate(timeline):
            if e['type'] not in ('user_start','background_speech_start'):continue
            pieces=[(e['text'],0)]
            j=i+1;pause=None
            while j<len(timeline) and timeline[j]['type'] not in ('user_end','background_speech_end','user_start','trial_end'):
                nxt=timeline[j]
                if nxt['type']=='user_pause':pause=nxt['at_ms']
                if nxt['type']=='user_resume':pieces.append((nxt['text'],max(0,nxt['at_ms']-(pause if pause is not None else nxt['at_ms']))))
                j+=1
            utterances.append({'pieces':pieces,'at_ms':e['at_ms'],'end_ms':timeline[j]['at_ms'] if j<len(timeline) else e['at_ms'], 'background':e['type']=='background_speech_start'})
        if not timeline:
            utterances=[{'pieces':[(t['user'],0)],'at_ms':0,'end_ms':0,'background':False} for t in case['turns']]
        for index,u in enumerate(utterances):
            pcm=bytearray();segments=[]
            for text,gap in u['pieces']:
                pcm.extend(b'\0'*int(gap*32));start=len(pcm)/32
                block=read_pcm(audio/names[text]);pcm.extend(block)
                segments.append({'text':text,'start_ms':start,'end_ms':len(pcm)/32})
            gain=.12 if slug=='audio_soft_voice' else .2 if u['background'] else 1
            if gain!=1:pcm=(np.frombuffer(pcm,dtype='<i2').astype(np.float32)*gain).astype('<i2').tobytes()
            name=slug+'-'+str(index+1)+'.wav';wav(audio/name,pcm)
            trigger='after_playback' if (seed and index==0) or (not timeline and index>0) else 'ready' if index==0 else 'after_idle'
            delay=min(u['at_ms'],1200) if seed and index==0 else 150
            if slug=='audio_friday_saturday' and index==1:trigger='after_input';delay=600
            if slug=='audio_silence' and index==1:delay=12000
            if slug=='audio_resume_unheard' and index==1:delay=1500
            entry['steps'].append({'type':'audio','file':name,'trigger':trigger,'delay_ms':delay,'role':'user','segments':segments,'duration_ms':len(pcm)/32,'gain':gain})
        if slug=='audio_noise_cough':
            rng=np.random.default_rng(20260924);n=6400
            noise=rng.normal(0,1,n);noise=np.convolve(noise,np.ones(7)/7,mode='same')
            noise*=np.sin(np.linspace(0,np.pi,n))**2
            pcm=(noise*7000).clip(-32767,32767).astype('<i2').tobytes();name=slug+'-noise.wav';wav(audio/name,pcm)
            entry['steps'].append({'type':'audio','file':name,'trigger':'after_playback','delay_ms':850,'role':'synthetic_noise','duration_ms':400})
            entry['conditions_uncontrolled'].append('Synthetic non-speech noise surrogate; not a real cough. Cough-specific quality remains unmeasured.')
        if slug.startswith('audio_echo'):
            entry['digital_echo']={'gain':.2,'delay_ms':120}
            entry['conditions_uncontrolled'].append('Digital loopback echo bypasses the physical microphone and browser AEC; room echo handling is unmeasured.')
        if slug=='audio_background_speaker':entry['conditions_uncontrolled'].append('Attenuated synthesized speech does not prove speaker identity or spatial addressing.')
        if slug=='audio_same_words':entry['conditions_uncontrolled'].append('One synthetic delivery only; sarcastic versus sincere prosody is not established.')
        if slug=='audio_spanish_interrupt':entry['conditions_uncontrolled'].append('English synthesis voice speaking Spanish text; accent coverage is not established.')
        if slug=='audio_asr_revision':entry['conditions_uncontrolled'].append('Real ASR revisions are observed, not forced to the original scripted partials.')
        if slug in ('audio_friday_saturday','audio_background_late'):entry['conditions_uncontrolled'].append('Actual background jobs may run; prescribed delayed-result timing is not injected in this audio run.')
        if slug=='queue_depth_correction':entry['conditions_uncontrolled'].append('Natural queue depth observed; the planned 0/300/1200 ms queue-depth sweep is separate.')
        entry['fixture_status']='ready_for_software_e2e'
        fixtures.append(entry)
    for path in audio.glob('*.wav'):
        pcm=read_pcm(path)
        if len(pcm)%2:raise ValueError('Invalid fixture')
    manifest={'version':'2026-09-24.1','suite_sha256':hashlib.sha256(json.dumps(suite,sort_keys=True).encode()).hexdigest(),
        'sample_rate':16000,'synthetic':True,'human_naturalness':'unrated','fixtures':fixtures,
        'assets':[{'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'duration_ms':len(read_pcm(p))/32} for p in sorted(audio.glob('*.wav'))]}
    save(output/'manifest.json',manifest)
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--suite',type=Path,default=HERE/'cases_v2.json')
    a=p.parse_args();m=build(json.loads(a.suite.read_text(encoding='utf-8')),a.output)
    print(json.dumps({'fixtures':len(m['fixtures']),'wav_files':len(m['assets']),'total_asset_seconds':sum(v['duration_ms'] for v in m['assets'])/1000}))
