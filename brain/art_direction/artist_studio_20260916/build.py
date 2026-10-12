"""Generate counted frame references and artist downloads from the shared SVG scene."""
from pathlib import Path
import csv,hashlib,json,shutil,subprocess,zipfile,xml.etree.ElementTree as ET
import cairosvg
from PIL import Image

ROOT=Path(__file__).resolve().parent

def zip_files(target,files,prefix=''):
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for p,name in files:z.write(p,prefix+name)
    with zipfile.ZipFile(target) as z:assert z.testzip() is None

def main():
    subprocess.run(['node',str(ROOT/'export.cjs')],check=True,cwd=ROOT)
    plan=json.loads((ROOT/'plan.json').read_text(encoding='utf-8'))
    downloads=ROOT/'downloads';downloads.mkdir(exist_ok=True);templates=ROOT/'templates';templates.mkdir(exist_ok=True)
    for p in plan['parts']:
        (templates/(p['id']+'.svg')).write_text(f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1024" viewBox="0 0 100 64"><title>{p['id']} blank template</title><g id="GUIDES" fill="none" stroke="#929990" stroke-width=".15"><rect x="5" y="5" width="90" height="54"/><path d="M28 10V57M72 10V57M5 29H95M5 48H95"/><text x="6" y="8" font-size="1.6" stroke="none" fill="#687061">{p['id']} / hide guides before export</text></g><g id="eye_L"/><g id="eye_R"/><g id="mouth"/><g id="accents"/></svg>''',encoding='utf-8')
    with (downloads/'frame_plan.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['clip','frames','fps','seconds','core','reuse','layer_scope'])
        for c in plan['clips']:w.writerow([c['id'],c['frames'],24,c['seconds'],c['core'],c['reuse'],'eyes only' if c['settings'].get('mouth') is False else 'composed reference'])
    with (downloads/'drawing_list.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=['id','group','name','note','unit']);w.writeheader();w.writerows(plan['parts'])
    shutil.copyfile(ROOT/'artist_notes.txt',downloads/'artist_notes.txt')
    allframes=[];png_count=0
    for c in plan['clips']:
        folder=ROOT/'frame_assets'/c['id'];files=[]
        for i in range(c['frames']):
            svg=folder/f'{i:04d}.svg';png=svg.with_suffix('.png')
            cairosvg.svg2png(url=str(svg),write_to=str(png),output_width=800,output_height=512)
            with Image.open(png) as image:assert image.size==(800,512) and image.mode=='RGBA'
            files.extend([(svg,svg.name),(png,png.name)]);png_count+=1
        with (folder/'frames.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.writer(f);w.writerow(['frame','svg','png','duration_ms','is_new_artist_drawing'])
            for i in range(c['frames']):w.writerow([i,f'{i:04d}.svg',f'{i:04d}.png',41.666667,False])
        files.append((folder/'frames.csv','frames.csv'))
        zip_files(downloads/(c['id']+'.zip'),files,c['id']+'/')
        allframes.extend((p,c['id']+'/'+name) for p,name in files)
        print(c['id'],c['frames'],flush=True)
    assert png_count==828
    zip_files(downloads/'MIST_reference_frames.zip',allframes+[(downloads/'frame_plan.csv','frame_plan.csv'),(downloads/'artist_notes.txt','artist_notes.txt')])
    zip_files(downloads/'MIST_blank_templates.zip',[(p,p.name) for p in sorted(templates.glob('*.svg'))]+[(downloads/'drawing_list.csv','drawing_list.csv'),(downloads/'artist_notes.txt','artist_notes.txt')])
    zip_files(downloads/'MIST_artist_assets.zip',[(downloads/'MIST_reference_frames.zip','MIST_reference_frames.zip'),(downloads/'MIST_blank_templates.zip','MIST_blank_templates.zip'),(downloads/'frame_plan.csv','frame_plan.csv'),(downloads/'drawing_list.csv','drawing_list.csv'),(downloads/'artist_notes.txt','artist_notes.txt')],'MIST_artist_assets/')
    verification={'passed':True,'component_drawings':36,'individual_eye_mouth_parts':64,'png_frames':png_count,'svg_frames':png_count,'core_frames':sum(c['frames'] for c in plan['clips'] if c['core']),'core_clips':sum(c['core'] for c in plan['clips']),'all_clips':len(plan['clips']),'templates':len(list(templates.glob('*.svg'))),'fps':24,'reference_only':True,'downloads':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(downloads.glob('*.zip'))}}
    assert verification['templates']==36 and verification['core_frames']==516
    (ROOT/'VALIDATION.json').write_text(json.dumps(verification,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in verification.items() if k!='downloads'}),flush=True)

if __name__=='__main__':main()
