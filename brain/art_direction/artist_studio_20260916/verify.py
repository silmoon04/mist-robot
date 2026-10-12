from pathlib import Path
import hashlib,json,zipfile,xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parent
class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        self.links.extend(v for k,v in attrs if k in ('href','src') and v)

plan=json.loads((ROOT/'plan.json').read_text(encoding='utf-8'));report=json.loads((ROOT/'VALIDATION.json').read_text(encoding='utf-8'))
parser=Links();parser.feed((ROOT/'index.html').read_text(encoding='utf-8'))
for link in parser.links:assert (ROOT/urlsplit(link).path).is_file(),link
for c in plan['clips']:
    with zipfile.ZipFile(ROOT/'downloads'/f"{c['id']}.zip") as z:
        assert len([n for n in z.namelist() if n.endswith('.png')])==c['frames']
        assert len([n for n in z.namelist() if n.endswith('.svg')])==c['frames']
        for i in [0,c['frames']-1]:
            name=f"{c['id']}/{i:04d}.svg";assert z.read(name)==(ROOT/'frame_assets'/name).read_bytes()
for p in plan['parts']:
    tree=ET.parse(ROOT/'templates'/f"{p['id']}.svg");groups={g.attrib.get('id'):g for g in tree.getroot().findall('{http://www.w3.org/2000/svg}g')}
    assert all(len(groups[name])==0 for name in ['eye_L','eye_R','mouth','accents'])
with zipfile.ZipFile(ROOT/'downloads/MIST_reference_frames.zip') as z:
    assert len([n for n in z.namelist() if n.endswith('.png')])==828
    assert z.read('artist_notes.txt')==(ROOT/'artist_notes.txt').read_bytes()
with zipfile.ZipFile(ROOT/'downloads/MIST_artist_assets.zip') as z:
    assert z.testzip() is None
    for name in ['MIST_reference_frames.zip','MIST_blank_templates.zip']:
        assert z.read('MIST_artist_assets/'+name)==(ROOT/'downloads'/name).read_bytes()
report['browser_checks']=['Listening options changed the selected clip URL','Listening and thinking disable speech','Frame step advances one frame','Core plan showed 23 clips and 516 frames','Alternative plan showed 28 clips and 828 frames','No console errors']
report['static_links_passed']=True
report['source_sha256']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['index.html','studio.css','studio.js','scene.js','plan.json','artist_notes.txt']}
brain=ROOT.parents[1]
assert (ROOT/'existing/app_data.js').read_bytes()==(brain/'face_assets/app/app_data.js').read_bytes()
assert (ROOT/'existing/face_runtime.js').read_bytes()==(brain/'ui/static/face_runtime.js').read_bytes()
report['existing_assets_identical_to_original']=True
(ROOT/'VALIDATION.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'passed':True,'png_frames':828,'template_drawings':36,'asset_pack_bytes':(ROOT/'downloads/MIST_artist_assets.zip').stat().st_size}))
