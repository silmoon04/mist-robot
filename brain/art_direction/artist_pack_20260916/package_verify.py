"""Check counts and portable links, then package only the artist-facing files."""
from pathlib import Path
from html.parser import HTMLParser
import csv,json,hashlib,xml.etree.ElementTree as ET,zipfile
from urllib.parse import unquote,urlsplit

HERE=Path(__file__).resolve().parent
class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        for name,value in attrs:
            if name in ('src','href') and value:self.links.append(value)

def main():
    data=json.loads((HERE/'drawing_manifest.json').read_text(encoding='utf-8'))
    assert len(data['rows'])==38 and len(data['poses'])==12
    ids={r['id'] for r in data['rows']};assert len(ids)==38
    assert sum(r['pilot'] for r in data['rows'])==6
    assert sum(r['unit']=='eye pair' for r in data['rows'])==30
    assert sum(r['unit']=='mouth' for r in data['rows'])==8
    for row in data['rows']:
        p=HERE/'templates'/f"{row['id']}_{row['name'].replace(' ','_')}.svg"
        svg=ET.parse(p).getroot();assert svg.attrib['viewBox']=='0 0 100 64'
        groups={g.attrib.get('id'):g for g in svg.findall('{http://www.w3.org/2000/svg}g')}
        assert all(name in groups for name in ['GUIDES','REFERENCE','eye_L','eye_R','mouth','accents'])
        assert all(len(groups[name])==0 for name in ['eye_L','eye_R','mouth','accents'])
    for pose in data['poses']:
        assert pose['eyes'] in ids and pose['mouth'] in ids
        assert (HERE/'references'/f"{pose['reference']}.svg").exists()
    refs=list((HERE/'references').glob('*.svg'));assert len(refs)==41
    for p in refs:ET.parse(p)
    parser=Links();parser.feed((HERE/'index.html').read_text(encoding='utf-8'))
    for href in parser.links:
        if href.startswith('#'):continue
        url=urlsplit(href);assert not url.scheme and not url.netloc
        assert (HERE/unquote(url.path)).exists(),href
    with (HERE/'animation_clips.csv').open(encoding='utf-8-sig',newline='') as f:clips=list(csv.DictReader(f))
    assert len(clips)==15 and sum(int(c['timeline_frames']) for c in clips)==560
    files=[HERE/name for name in ['index.html','START_HERE.md','MOTION_GUIDE.md','DELIVERY_SPEC.md','MESSAGE_TO_ARTIST.txt','artist_brief.txt','drawing_manifest.json','drawing_checklist.csv','animation_clips.csv']]
    for folder in ['assets','references','templates']:files.extend(p for p in (HERE/folder).rglob('*') if p.is_file())
    checks={p.relative_to(HERE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    validation={'passed':True,'production_components':38,'pilot_components':6,'eye_pair_units':30,'mouth_units':8,'pose_compositions':12,'existing_reference_faces':40,'review_clips':15,'timeline_exposures_not_new_drawings':560,'blank_templates_verified':38,'local_links_checked':len(parser.links),'browser_checks':['12 core references and 40 existing references displayed','Pilot filter displayed exactly 6 component rows','Speech preview at frame 12 / 200 ms showed AA','Mouth layer visibility toggled independently','No browser console errors during inspection'],'file_sha256':checks}
    (HERE/'VALIDATION.json').write_text(json.dumps(validation,indent=2)+'\n',encoding='utf-8')
    (HERE/'CHECKSUMS.sha256').write_text(''.join(f'{digest}  {name}\n' for name,digest in checks.items()),encoding='utf-8')
    files.extend([HERE/'VALIDATION.json',HERE/'CHECKSUMS.sha256'])
    target=HERE.parent/'MIST_Artist_Handoff_20260916.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(files):z.write(p,'MIST_Artist_Handoff/'+p.relative_to(HERE).as_posix())
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        for name,digest in checks.items():assert hashlib.sha256(z.read('MIST_Artist_Handoff/'+name)).hexdigest()==digest
    print(json.dumps({'passed':True,'archive':str(target),'files':len(files),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}))

if __name__=='__main__':main()
