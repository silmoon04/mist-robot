"""Check the chosen wider-yaw geometry throughout a sampled guard range."""
import json,math
import build,leg,geom as g
from OCP.BRepExtrema import BRepExtrema_DistShapeShape

def main():
    digest=build.sha(build.OUT/'manifest.json');parts,frames=build.load_assembly()
    fixed=[p for p in parts if p['link']=='base_mount']
    moving=[p for p in parts if p['link']=='coxa' and p['printable']]
    rows=[]
    for angle in sorted(set(range(-60,61,2))|{-55,55}):
        row={'angle_deg':angle,'intersections':[],'minimum_printed_clearance_mm':1e9,'closest_pair':None}
        for a in moving:
            shape=g.rotate(a['shape'],(0,0,1),angle);aa=g.bounds(shape)
            for b in fixed:
                bb=g.bounds(b['shape']);separation=[max(0,aa[0][i]-bb[1][i],bb[0][i]-aa[1][i]) for i in range(3)]
                if max(separation)==0:
                    v=g.common_volume(shape,b['shape'])
                    if v>.01:row['intersections'].append({'moving':a['name'],'fixed':b['name'],'mm3':v})
                if not b['printable'] or sum(x*x for x in separation)**.5 >= row['minimum_printed_clearance_mm']:continue
                d=BRepExtrema_DistShapeShape(shape,b['shape']);d.Perform();assert d.IsDone()
                if d.Value()<row['minimum_printed_clearance_mm']:
                    row['minimum_printed_clearance_mm']=d.Value();row['closest_pair']=[a['name'],b['name']]
        rows.append(row);print(angle,round(row['minimum_printed_clearance_mm'],3),len(row['intersections']),flush=True)
    report={'status':'pass' if not any(r['intersections'] for r in rows) else 'fail','manifest_sha256':digest,'coxa_length_mm':82,
        'operating_limits_deg':[-55,55],'sampled_guard_limits_deg':[-60,60],'sample_count':len(rows),'samples':rows,
        'minimum_printed_clearance_mm':min(r['minimum_printed_clearance_mm'] for r in rows),
        'scope':'63 discrete yaw poses, including a five-degree guard beyond the operating limits. Printed-part clearance is distinct from intended horn/shaft contact. Flexible cable loops and continuous sweeps still need physical checking.'}
    assert digest==build.sha(build.OUT/'manifest.json')
    (build.OUT/'yaw_clearance.json').write_text(json.dumps(report,indent=2));print(report['status'],report['minimum_printed_clearance_mm'])

if __name__=='__main__':main()
