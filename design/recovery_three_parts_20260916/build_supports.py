from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'third_leg_20260916'
sys.path.insert(0,str(ROOT.parent/'single_leg_r7_wide_joints_20260914/cad'))
import geom as g
rows=json.loads((ROOT/'support_plan.json').read_text());manifest=json.loads((OLD/'output/manifest.json').read_text())
out=ROOT/'supports';out.mkdir(exist_ok=True)
for name in sorted(set(r['part'] for r in rows)):
 shapes=[]
 for r in [r for r in rows if r['part']==name]:
  s=g.prism_xy(r['base'],0,.56)
  for h in r['base_holes']:s=g.cut(s,g.prism_xy(h,-.1,.8))
  for f in r['fins']:s=g.fuse(s,g.prism_xy(f,0,r['top_mm']))
  shapes.append(s)
 supports=g.fuse(*shapes)
 p=next(p for p in manifest['parts'] if p['name']==name)
 model=g.import_step(OLD/'output/parts_step'/(name+'.step'));model=g.transform(model,rpy_deg=p['print_rotation']);lo,hi=g.bounds(model);model=g.translate(model,[-v for v in lo])
 overlap=g.common_volume(model,supports);assert overlap<.001,(name,overlap)
 g.export_stl(supports,out/(name+'.stl'),.04)
 print(name,'support_volume',g.volume(supports),'intersection',overlap,flush=True)
