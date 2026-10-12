"""Compare actual yaw packaging candidates before changing print geometry."""
from pathlib import Path
import json,math
import build,leg,hip_revision as hip,geom as g
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
OUT=build.ROOT/'yaw_study';OUT.mkdir(exist_ok=True)

def clipped_plate():
    outside=g.cut(g.box(120,130,20,(60,0,-35)),g.cylinder(30,30,(0,0,-50)))
    return g.cut(build.mounting_plate(),outside)

def main():
    saddle,cap=leg.case_clamp(True)
    fixed=[('yaw_saddle',saddle),('yaw_cap',cap),('yaw_case',leg.servo_envelope())]
    results=[]
    for length,post in [(70,24.5),(75,29.5),(80,34.5),(82,36.5)]:
        parts=hip.build_coxa(length,post)
        upper=next(p['shape'] for p in parts if p['name']=='coxa_upper_and_hip_saddle')
        lower=next(p['shape'] for p in parts if p['name']=='coxa_lower_auxiliary_arm')
        # Check internal case and bracket intersections independently first.
        own=build.intersections(parts,{'coxa':build.pose()})
        row={'length_mm':length,'post_x_mm':post,'internal':own,'samples':[]}
        targets=[*fixed,('bench_plate',clipped_plate())]
        for angle in (0,19,30,40,45,50,55,60,-30,-45,-60):
            sample={'yaw_deg':angle,'intersections':[],'minimum_printed_clearance_mm':1e9,'closest_pair':None}
            for p in parts:
                if not p['printable'] or 'spacer' in p['name']:continue
                shape=g.rotate(p['shape'],(0,0,1),angle)
                for name,target in targets:
                    v=g.common_volume(shape,target)
                    if v>.01:sample['intersections'].append({'moving':p['name'],'fixed':name,'mm3':v})
                    if p['name'] not in ('coxa_upper_and_hip_saddle','coxa_lower_auxiliary_arm'):continue
                    dist=BRepExtrema_DistShapeShape(shape,target);dist.Perform();assert dist.IsDone()
                    if dist.Value()<sample['minimum_printed_clearance_mm']:
                        sample['minimum_printed_clearance_mm']=dist.Value();sample['closest_pair']=[p['name'],name]
            row['samples'].append(sample);print(length,angle,round(sample['minimum_printed_clearance_mm'],3),len(sample['intersections']),flush=True)
        results.append(row);(OUT/'candidates.json').write_text(json.dumps(results,indent=2))
    return results

if __name__=='__main__':main()
