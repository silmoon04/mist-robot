from pathlib import Path
import json,shutil,sys,hashlib
root=Path(__file__).resolve().parents[1]/'art_direction/artist_studio_20260916'
sys.path.insert(0,str(root))
from build import zip_files
plan=json.loads((root/'plan.json').read_text(encoding='utf-8'));downloads=root/'downloads'
p=root/'artist_notes.txt';s=p.read_text(encoding='utf-8');s=s.split('\nDesign reference search:')[0].rstrip()+'\n';p.write_text(s,encoding='utf-8');shutil.copyfile(p,downloads/p.name)
allowed={c['id']+'.zip' for c in plan['clips']}|{'MIST_reference_frames.zip','MIST_blank_templates.zip','MIST_artist_assets.zip'}
archive=(root.parent/'retired_concept_downloads_20260916').resolve();archive.mkdir(exist_ok=True)
for p in downloads.glob('*.zip'):
    if p.name not in allowed:
        source=p.resolve();target=(archive/p.name).resolve()
        assert source.is_relative_to(downloads.resolve()) and target.is_relative_to(root.parent.resolve())
        if not target.exists():shutil.move(str(source),str(target))
frames=[]
for c in plan['clips']:
    folder=root/'frame_assets'/c['id']
    frames.extend((p,c['id']+'/'+p.name) for p in folder.iterdir() if p.suffix in ('.png','.svg','.csv'))
zip_files(downloads/'MIST_reference_frames.zip',frames+[(downloads/'frame_plan.csv','frame_plan.csv'),(downloads/'artist_notes.txt','artist_notes.txt')])
zip_files(downloads/'MIST_blank_templates.zip',[(p,p.name) for p in sorted((root/'templates').glob('*.svg'))]+[(downloads/'drawing_list.csv','drawing_list.csv'),(downloads/'artist_notes.txt','artist_notes.txt')])
zip_files(downloads/'MIST_artist_assets.zip',[(downloads/name,name) for name in ['MIST_reference_frames.zip','MIST_blank_templates.zip','frame_plan.csv','drawing_list.csv','artist_notes.txt']],'MIST_artist_assets/')
report=json.loads((root/'VALIDATION.json').read_text(encoding='utf-8'))
report['downloads']={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(downloads.glob('*.zip'))}
(root/'VALIDATION.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('Active downloads rebuilt from existing assets; obsolete concept clip ZIPs archived outside the preview server root.')
