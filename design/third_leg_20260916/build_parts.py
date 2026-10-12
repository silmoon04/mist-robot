"""Localized insert pockets and nut lead-ins on the fitted leg geometry."""
from pathlib import Path
import sys,json,math,hashlib,shutil
ROOT=Path(__file__).resolve().parent; PROJECT=ROOT.parent.parent
OLD=ROOT.parent/'print_dfm_20260914/output';OUT=ROOT/'output'
sys.path.insert(0,str(ROOT.parent/'single_leg_r7_wide_joints_20260914/cad'))
import geom as g, leg, servo_contract as sc
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon
from OCP.gp import gp_Pnt
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def mouth(x,z):
    loft=BRepOffsetAPI_ThruSections(True,True)
    for y,af in [(-16.465,6.6),(-15.965,5.6)]:
        w=BRepBuilderAPI_MakePolygon();r=af/math.sqrt(3)
        for i in range(6):
            a=math.radians(30+i*60);w.Add(gp_Pnt(x+r*math.cos(a),y,z-r*math.sin(a)))
        w.Close();loft.AddWire(w.Wire())
    loft.Build();assert loft.IsDone();return loft.Shape()

def main():
    for folder in ('print_stl','assembly_mesh','parts_step'): (OUT/folder).mkdir(parents=True,exist_ok=True)
    manifest=json.loads((OLD/'manifest.json').read_text());rows=[];checks=[]
    for entry in manifest['parts']:
        if not entry['printable'] or entry['name']=='bench_mounting_plate':continue
        p=dict(entry);n=p['name'];shape=g.import_step(OLD/'parts_step'/(n+'.step'));original=shape;changes=[]
        if n in ('yaw_case_saddle','coxa_upper_and_hip_saddle','femur_main_and_knee_saddle'):
            bolts=list(sc.CLAMP_BOLT_XZ)
            if n.startswith('coxa'):bolts[0]=(sc.CLAMP_REAR_BOLT_X,-27.5)
            for x,z in bolts:
                tool=mouth(x,z)
                if n!='yaw_case_saddle':tool=leg._pitch(tool,False,82 if n.startswith('coxa') else 90)
                shape=g.cut(shape,tool)
            changes.append('Three shallow tapered nut entries; original inner nut seats retained.')
        bridges=[(65,20.5)] if n=='femur_main_and_knee_saddle' else [(36,0),(44,0)] if n=='tibia_curved_main_and_foot' else []
        for x,z in bridges:
            # Entry is on the bridge face behind the detachable 5 mm cheek.
            # Existing deeper bores and unused nut slots are retained.
            shape=g.cut(shape,g.cylinder(1.75,5.7,(x,-22.1,z),(0,1,0)),g.cylinder(2.0,.65,(x,-22.1,z),(0,1,0)))
            changes.append('M3 insert pocket: 3.5 mm pilot, 5.6 mm depth, 4 mm entry for 0.55 mm.')
            checks.append({'part':n,'insert_axis_xz_mm':[x,z],'nominal_insert_od_mm':4,'nominal_insert_length_mm':5,
                           'screw':'M3x10 with one 0.5 mm flat washer through 5 mm cheek',
                           'calculated_engagement_mm':4.5,'insert_end_clearance_mm':.5})
        if n.startswith('yaw_auxiliary_spacer_'):
            shape=g.cut(g.cylinder(2.75,13,(0,0,0)),g.cylinder(1.7,13.2,(0,0,-.1)))
            changes.append('User-confirmed fitted spacer dimensions: 5.5 mm outside diameter, 13 mm height, 3.4 mm bore.')
        assert g.valid(shape)
        e=TopExp_Explorer(shape,TopAbs_SOLID);count=0
        while e.More():count+=1;e.Next()
        assert count==1,(n,count)
        if not n.startswith('yaw_auxiliary_spacer_'):
            added=g.volume(shape)-g.common_volume(shape,original)
            assert abs(added)<.001,(n,added)
        rotation=p['print_rotation'] if not n.startswith('yaw_auxiliary_spacer_') else [0,0,0]
        posed=g.transform(shape,rpy_deg=rotation);lo,hi=g.bounds(posed);posed=g.translate(posed,[-v for v in lo])
        g.export_stl(posed,OUT/p['print_stl'],.04);g.export_stl(shape,OUT/p['assembly_stl'],.04);g.export_step(shape,OUT/'parts_step'/(n+'.step'))
        p.update(print_rotation=rotation,dimensions_mm=[hi[i]-lo[i] for i in range(3)],stl_sha256=sha(OUT/p['print_stl']),volume_mm3=g.volume(shape),com_mm=g.centroid(shape),solid_mass_kg=g.volume(shape)*.00000124,changes=changes)
        if n.startswith('yaw_auxiliary_spacer_'):
            p.update(link='unplaced_printed_spacer',transform=None,assembly_placement_status='Print-local geometry only. User-confirmed 13 mm length differs from historical CAD stack; installed placement and screw engagement not recomputed.')
        rows.append(p)
    manifest.update(revision='third_leg_insert_bridges_20260916',parts=rows,baseline_manifest_sha256=sha(OLD/'manifest.json'))
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    report={'parts':len(rows),'solid_checks':'One valid solid per printed component. No added material on revised leg bodies.',
            'insert_connections':checks,'nut_entry_chamfer_depth_mm':.4,
            'spacer_basis':'User reports 13 mm spacers are installed and rotate freely. This differs from the historical 11.6 mm CAD stack; no new axial-stack calculation is claimed.',
            'limits':'New insert retention and chamfers require physical evaluation. Existing joint holes and horn seats retained. No new structural or full-robot load qualification.'}
    (OUT/'Geometry_Check.json').write_text(json.dumps(report,indent=2));print('BUILD_OK',flush=True)

if __name__=='__main__':main()
