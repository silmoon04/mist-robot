"""Package only the current verified parts and register text before archiving."""
from pathlib import Path
import json,hashlib,zipfile,xml.etree.ElementTree as ET,subprocess,sys,shutil
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    subprocess.run([sys.executable,str(ROOT/'write_release.py')],check=True)
    m=json.loads((OUT/'print_validation.json').read_text());ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
    for p in m['plates']:
        with zipfile.ZipFile(OUT/p['three_mf']) as z:
            assert z.testzip() is None
            doc=ET.fromstring(z.read('3D/3dmodel.model'));assert doc.attrib['unit']=='millimeter'
            objects=doc.findall('m:resources/m:object',ns)
            assert [o.attrib['name'] for o in objects]==[x['name'] for x in p['parts']]
    files=sorted([*OUT.rglob('*.json'),*OUT.rglob('*.txt')])
    subprocess.run([sys.executable,'<LOCAL_HOME>/.codex/hooks/output_punctuation.py','register','--fix',*[str(p) for p in files]],check=True)
    # Rebind review hashes in case a prose fix changed an exported report.
    subprocess.run([sys.executable,str(ROOT/'write_release.py')],check=True)
    subprocess.run([sys.executable,'<LOCAL_HOME>/.codex/hooks/output_punctuation.py','check',*[str(p) for p in files]],check=True)
    items={}
    for f in OUT.rglob('*'):
        if not f.is_file() or 'motion_frames' in f.parts or f.name in ('progress.json','SHA256SUMS.txt'):continue
        items[f.relative_to(OUT).as_posix()]=f
    for f in (ROOT/'cad').rglob('*'):
        if f.is_file() and f.suffix in ('.py','.step'):items['source/cad/'+f.relative_to(ROOT/'cad').as_posix()]=f
    items['source/REQUIREMENTS.md']=ROOT/'REQUIREMENTS.md'
    checksum='\n'.join(sha(f)+'  '+name for name,f in sorted(items.items()))+'\n'
    (OUT/'SHA256SUMS.txt').write_text(checksum)
    subprocess.run([sys.executable,'<LOCAL_HOME>/.codex/hooks/output_punctuation.py','register','--fix',str(OUT/'SHA256SUMS.txt')],check=True)
    assert (OUT/'SHA256SUMS.txt').read_text()==checksum
    items['SHA256SUMS.txt']=OUT/'SHA256SUMS.txt'
    archive=ROOT/'Single_Leg_R7_Wide_Joints_Print_Set.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,f in sorted(items.items()):z.write(f,name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name,f in items.items():assert hashlib.sha256(z.read(name)).hexdigest()==sha(f)
    # The previous filename must not remain an accidentally printable old set.
    shutil.copy2(archive,ROOT/'Single_Leg_R7_Print_Set.zip')
    print('PACKAGED',archive,'files',len(items),'MB',round(archive.stat().st_size/1e6,1),'sha256',sha(archive))

if __name__=='__main__':main()
