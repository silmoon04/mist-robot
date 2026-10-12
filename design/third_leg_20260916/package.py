from pathlib import Path
import json,hashlib,shutil,zipfile,csv,subprocess
ROOT=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

for name,updates in [
    ('output/Geometry_Check.json',{'manifest_sha256':sha(ROOT/'output/manifest.json')}),
    ('print/Print_Check.json',{'manifest_sha256':sha(ROOT/'output/manifest.json')})]:
    p=ROOT/name;v=json.loads(p.read_text());v.update(updates);p.write_text(json.dumps(v,indent=2))
p=ROOT/'print/Support_Check.json';v=json.loads(p.read_text());v['print_check_sha256']=sha(ROOT/'print/Print_Check.json');p.write_text(json.dumps(v,indent=2))
package=ROOT/'Third_Leg_Print_Set'
package.mkdir(exist_ok=True)
shutil.copytree(ROOT/'print',package/'Print_This',dirs_exist_ok=True)
shutil.copytree(ROOT/'output',package/'CAD',dirs_exist_ok=True)
files=[*list((package/'Print_This').glob('*.json')),*list((package/'CAD').glob('*.json')),package/'Print_This/START_HERE.txt']
files+=[ROOT/'output/manifest.json',ROOT/'output/Geometry_Check.json',ROOT/'print/Print_Check.json',ROOT/'print/Support_Check.json',ROOT/'print/START_HERE.txt']
subprocess.run(['python','<LOCAL_HOME>/.codex/hooks/output_punctuation.py','register','--fix',*[str(p) for p in files]],check=True)
# Punctuation changes would invalidate the linked checks or source snapshots.
assert json.loads((ROOT/'print/Support_Check.json').read_text())['print_check_sha256']==sha(ROOT/'print/Print_Check.json')
for p in (package/'Print_This').iterdir():assert sha(p)==sha(ROOT/'print'/p.name)
with (package/'SHA256SUMS.csv').open('w',newline='') as f:
    writer=csv.writer(f);writer.writerow(['path','sha256'])
    for p in sorted(package.rglob('*')):
        if p.is_file() and p.name!='SHA256SUMS.csv':writer.writerow([p.relative_to(package).as_posix(),sha(p)])
archive=ROOT/'Third_Leg_Print_Set.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(package.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(package).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for p in package.rglob('*'):
        if p.is_file():assert hashlib.sha256(z.read(p.relative_to(package).as_posix())).hexdigest()==sha(p)
print('PACKAGE_OK',archive,archive.stat().st_size,flush=True)
