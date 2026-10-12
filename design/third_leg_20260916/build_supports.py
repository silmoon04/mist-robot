from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'single_leg_r7_wide_joints_20260914/cad'))
import geom as g
p=json.loads((ROOT/'support_plan.json').read_text());shapes=[]
for row in p['combs']:
    s=g.prism_xy(row['base'],0,.56)
    for hole in row['base_holes']:s=g.cut(s,g.prism_xy(hole,-.1,.8))
    for fin in row['fins']:s=g.fuse(s,g.prism_xy(fin,0,row['height_mm']))
    assert g.valid(s);shapes.append(s)
model=g.import_step(ROOT/'output/parts_step'/(p['part']+'.step'))
model=g.rotate(model,(1,0,0),-90);lo,hi=g.bounds(model);model=g.translate(model,[-v for v in lo])
supports=g.compound(shapes)
assert g.common_volume(supports,model)<.001
g.export_stl(supports,ROOT/'output/Knee_Saddle_Removable_Combs.stl',.04)
g.export_step(supports,ROOT/'output/Knee_Saddle_Removable_Combs.step')
print('SUPPORTS_OK',g.volume(supports),flush=True)
