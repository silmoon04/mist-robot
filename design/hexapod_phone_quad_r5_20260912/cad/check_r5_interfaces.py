"""Check the changed R5 deck clearance and bare hip-carrier nut entry."""
from pathlib import Path
import hashlib
import json
import math
import body
import build
import geom as g
import hip_revision as hip
import leg
from OCP.BRepExtrema import BRepExtrema_DistShapeShape

CAD=Path(__file__).resolve().parent
ROOT=CAD.parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def source_hashes():
    return {name:sha(CAD/name) for name in ['body.py','leg.py','hip_revision.py',
        'tibia_revision.py','servo_contract.py','geom.py','check_r5_interfaces.py']}


def overlap(a,b):
    aa,bb=g.bounds(a),g.bounds(b)
    if any(aa[1][k]<=bb[0][k] or bb[1][k]<=aa[0][k] for k in range(3)):
        return 0.0
    return g.common_volume(a,b)


def raw_nut(x,z,start_y,depth,bore=False):
    sh=leg._hex_z(x,-z,0,depth,5.5)
    sh=g.translate(g.rotate(sh,(1,0,0),-90),(0,start_y,0))
    if bore:sh=g.cut(sh,leg._hole_y(x,z,start_y-1,depth+2,radius=1.5))
    return sh


def main():
    manifest=CAD/'output/assembly_manifest.json'
    data=json.loads(manifest.read_text(encoding='utf-8'))
    cfg=data['parameters']
    before=source_hashes()
    assert data['source_hashes']['body.py']==before['body.py']
    assert cfg['coxa_mm']==hip.SELECTED_COXA_LENGTH_MM
    parts=hip.build_coxa()
    deck=next(p['shape'] for p in body.build_body() if p['name']=='body_deck')
    gaps=[]
    for label,azimuth in cfg['leg_azimuth_deg'].items():
        a=math.radians(azimuth)
        for yaw in (-cfg["yaw_operating_limit_deg"],-15,0,15,cfg["yaw_operating_limit_deg"]):
            pose=build.pose((75*math.cos(a),75*math.sin(a),36),(0,0,azimuth+yaw))
            for p in parts:
                if p['name'] not in ('coxa_upper_and_hip_saddle','coxa_lower_auxiliary_arm'):
                    continue
                shape=build.shape_at(p['shape'],pose)
                operation=BRepExtrema_DistShapeShape(shape,deck)
                operation.Perform()
                assert operation.IsDone()
                gaps.append({'leg':label,'yaw_deg':yaw,'part':p['name'],
                    'intersection_mm3':overlap(shape,deck),'gap_mm':operation.Value()})
    carrier=next(p['shape'] for p in parts if p['name']=='coxa_upper_and_hip_saddle')
    nuts=[]
    for index,(x,z) in enumerate(hip.HIP_CLAMP_BOLT_XZ):
        entry=leg._pitch(raw_nut(x,z,-60,46.3),False,cfg['coxa_mm'])
        nuts.append({'bolt':index+1,'stage':'nut entry into bare carrier',
                     'obstacle':'coxa carrier','intersection_mm3':overlap(entry,carrier)})
        seated=leg._pitch(raw_nut(x,z,-16.1,2.4,True),False,cfg['coxa_mm'])
        for p in parts:
            nuts.append({'bolt':index+1,'stage':'nut seated with own case and cap',
                         'obstacle':p['name'],'intersection_mm3':overlap(seated,p['shape'])})
    fixings=list(body.COVER_FIXINGS)
    for azimuth in cfg['leg_azimuth_deg'].values():
        a=math.radians(azimuth)
        for x in (-29,9):
            for y in (-20,20):
                fixings.append(((75+x)*math.cos(a)-y*math.sin(a),
                                (75+x)*math.sin(a)+y*math.cos(a)))
    ligaments=[]
    for sx in (-1,1):
        for sy in (-1,1):
            a=(sx*85,sy*54);b=(sx*77,sy*58)
            dx,dy=b[0]-a[0],b[1]-a[1]
            for x,y in fixings:
                t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy)))
                distance=math.hypot(x-a[0]-t*dx,y-a[1]-t*dy)
                ligaments.append(distance-7.5-1.7)
    after=source_hashes()
    passed=(before==after and all(p['intersection_mm3']<=.01 and p['gap_mm']>=1.5 for p in gaps)
            and all(p['intersection_mm3']<=.01 for p in nuts) and min(ligaments)>3)
    report={'passed':passed,'revision':data['revision'],'source_manifest_sha256':sha(manifest),
        'source_hashes_before':before,'source_hashes_after':after,'deck_checks':gaps,
        'minimum_deck_gap_mm':min(p['gap_mm'] for p in gaps),'hip_nut_checks':nuts,
        'minimum_relief_to_named_fixing_hole_ligament_mm':min(ligaments),
        'assembly_order':'Preload the three hip nuts into the bare carrier from above before fitting servo and cap. Assemble the leg module before mounting it to the body.',
        'limitations':['The nut entry uses a filled 5.5 mm hexagonal exterior; thread form and tightening are not simulated.',
            'Nut pockets have nominal 0.1 mm flat clearance. Fingers and nut-holding tools are not modeled.',
            'The seated check includes the carrier, own servo, cap, lower arm and yaw accessories. It does not sweep servo/cap insertion.',
            'The deck check samples five yaw values on each leg; it is not a continuous-motion proof.',
            'The ligament calculation covers the yaw-mount and cover-fixing holes, not a structural analysis of the deck.',
            'Physical fit, lead flexibility, printed strength and hardware walking remain unverified.']}
    target=CAD/'output/r5_interface_check.json'
    target.write_text(json.dumps(report,indent=2),encoding='utf-8')
    target.with_suffix('.txt').write_text(
        f"R5 changed-interface check passed: {passed}\n"
        f"Deck/arm checks: {len(gaps)}; minimum gap: {report['minimum_deck_gap_mm']:.6f} mm.\n"
        f"Hip nut entry and seating checks: {len(nuts)}.\n"
        f"Minimum relief-to-fixing-hole ligament: {min(ligaments):.6f} mm.\n"
        +report['assembly_order']+'\n'+'\n'.join(report['limitations'])+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['passed','minimum_deck_gap_mm','minimum_relief_to_named_fixing_hole_ligament_mm']}))
    assert passed


if __name__=='__main__':main()
