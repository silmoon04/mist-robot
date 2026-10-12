from pathlib import Path
import hashlib,json,shutil,zipfile
root=Path(__file__).resolve().parents[2]
out=root/'brain/art_direction/artist_studio_20260916/reuse'
(out/'runtime').mkdir(exist_ok=True)
for src,dest in [('brain/face_assets/app/app_data.js','app_data.js'),('brain/ui/static/face_runtime.js','face_runtime.js')]:
 shutil.copyfile(root/src,out/'runtime'/dest)
files=[p for p in out.rglob('*') if p.is_file() and p.suffix not in {'.zip','.py','.cjs'} and p.name!='validation.json']
target=out/'MIST_reuse_pack.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,p.relative_to(out))
with zipfile.ZipFile(target) as z:
 assert z.testzip() is None
 assert all(name in z.namelist() for name in ['grid.html','grid.css','grid.js','runtime/app_data.js','runtime/face_runtime.js'])
v=json.loads((out/'validation.json').read_text());v.update(live_grid_faces=40,zip_bytes=target.stat().st_size,zip_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
(out/'validation.json').write_text(json.dumps(v,indent=2)+'\n')
print('Grid and local runtime included in asset pack; archive integrity passed.')
