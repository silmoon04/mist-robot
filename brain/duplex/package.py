"""Bundle the native voice source and its runtime assets without credentials."""
from pathlib import Path
import hashlib,json,zipfile

BRAIN=Path(__file__).resolve().parents[1]
ROOT=BRAIN.parent

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    files=[]
    for p in (BRAIN/'duplex').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.zip','.log','.pyc') and p.name!='CHECKSUMS.sha256':files.append(p)
    names=['codex_client.py','pi_client.py','response_format.py','test_duplex.py','test_voice_recovery.py','test_duplex_playback.mjs','check_face_runtime.cjs',
           'eval_duplex_live.py','eval_duplex_interrupt.py','test_streaming_tts.py','eval_streaming_tts.py','verify_tts_recording.py',
           'test_background.py','test_phrasing.py','test_delivery.mjs','eval_background.py','eval_layered_conversation.py','eval_parallel_audio.py','compare_phrase_streaming.py','test_debugging.py']
    files.extend(BRAIN/'harness'/n for n in names)
    files.extend([BRAIN/'ui/static/face_runtime.js',BRAIN/'face_assets/app/app_data.js',
        BRAIN/'soul/runtime-contract.txt',ROOT/'design/hexapod_phone_quad_r5_20260912/cad/output/assembly_manifest.json'])
    current_report=BRAIN/'duplex/DEBUG_REPORT.json'
    evaluation=json.loads((current_report if current_report.exists() else BRAIN/'duplex/EVALUATION.json').read_text(encoding='utf-8'))
    for path,digest in evaluation['implementation_sha256'].items():
        assert sha(BRAIN/path)==digest,'Implementation changed after review: '+path
    assert all(x['passed'] for x in evaluation['tests'])
    records={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(files))}
    checks=BRAIN/'duplex/CHECKSUMS.sha256';checks.write_text(''.join(f'{v}  {k}\n' for k,v in records.items()),encoding='utf-8')
    target=BRAIN/'duplex/MIST_Native_Voice_20260914.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(set(files))+[checks]:z.write(p,arcname='MIST_Native_Voice/'+p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        for path,digest in records.items():assert hashlib.sha256(z.read('MIST_Native_Voice/'+path)).hexdigest()==digest
    print(json.dumps({'archive':str(target),'bytes':target.stat().st_size,'files':len(records)+1,'sha256':sha(target)}))

if __name__=='__main__':main()
