"""Read configured voice access and subscription availability; never print secrets."""
import asyncio
import json
from pathlib import Path
import sys
import aiohttp
BRAIN=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BRAIN))
from pi_client import load_env
from duplex.conversion import VOICE

async def main():
    key=load_env()['ELEVENLABS_API_KEY'].strip('"\'')
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as client:
        for route in (f'/v1/voices/{VOICE}','/v1/user/subscription'):
            async with client.get('https://api.elevenlabs.io'+route,headers={'xi-api-key':key}) as response:
                payload=await response.json()
                if response.status==200:
                    safe={k:payload.get(k) for k in ('name','category','available_for_tiers','is_owner','character_count','character_limit','status','can_extend_character_limit') if k in payload}
                else:safe={'detail':str(payload.get('detail',''))[:300].replace(key,'[redacted]')}
                print(json.dumps({'route':route,'status':response.status,'result':safe}),flush=True)
        async with client.post(f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE}/with-timestamps?output_format=pcm_24000',
                headers={'xi-api-key':key},json={'text':'Hello.','model_id':'eleven_flash_v2_5'}) as response:
            payload=await response.json()
            safe={'detail':str(payload.get('detail',''))[:600].replace(key,'[redacted]')} if response.status!=200 else {
                'audio_base64_characters':len(payload.get('audio_base64') or ''),'has_alignment':bool(payload.get('normalized_alignment') or payload.get('alignment'))}
            print(json.dumps({'route':'minimal_same_voice_synthesis','status':response.status,'result':safe}),flush=True)

if __name__=='__main__':asyncio.run(main())
