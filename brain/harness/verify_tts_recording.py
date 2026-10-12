"""Check complete generated recordings independently of the native transcript."""
import argparse, asyncio, json, re, sys, wave
from pathlib import Path
import aiohttp
sys.path.insert(0,str(Path(__file__).resolve().parent))
from pi_client import load_env

async def main():
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--interrupt',action='store_true');a=p.parse_args()
    with wave.open(str(a.folder/('interruption.wav' if a.interrupt else 'converted_conversation.wav')),'rb') as w:raw=w.readframes(w.getnframes())
    async with aiohttp.ClientSession() as http:
        async with http.post('https://api.deepgram.com/v1/listen?model=nova-3&encoding=linear16&sample_rate=24000&channels=1',headers={'Authorization':'Token '+load_env()['DEEPGRAM_API_KEY'],'Content-Type':'application/octet-stream'},data=raw) as r:
            assert r.status==200
            d=await r.json();text=d['results']['channels'][0]['alternatives'][0]['transcript']
    if a.interrupt:
        checks={'correction_audible':'blueteacup' in re.sub(r'[^a-z]','',text.lower())}
    else:
        rows=json.loads((a.folder/'conversations.json').read_text())
        normalized=re.sub(r'[^a-z]','',text.lower())
        checks={}
        for row in rows:
            reply=' '.join(e['text'] for e in row['transcripts'] if e['role']=='assistant')
            prefix=' '.join(reply.strip().split()[:3]);suffix=' '.join(reply.strip().split()[-3:])
            checks[row['case']+'_first_words']=re.sub(r'[^a-z]','',prefix.lower()) in normalized
            checks[row['case']+'_last_words']=re.sub(r'[^a-z]','',suffix.lower()) in normalized
    result={'recognized':text,'checks':checks,'passed':all(checks.values()),'limitation':'ASR confirms words, not subjective voice quality.'}
    (a.folder/'audio_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
    assert result['passed']

asyncio.run(main())
