from pathlib import Path
import sys
import json
import hashlib
import itertools
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'cad'))
import leg
import tibia_revision
from geom import (bounds, volume, valid, common_volume, rotate, translate,
                  export_stl, export_step, cylinder, compound, centroid)
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID

OUT = Path(__file__).resolve().parent
BASELINE_LEG = ROOT.parent / 'hexapod_phone_quad_20260912/cad/leg.py'
spec = importlib.util.spec_from_file_location('baseline_r4_leg_for_tibia', BASELINE_LEG)
baseline_leg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline_leg)


def overlaps(a, b):
    aa, bb = bounds(a), bounds(b)
    return all(aa[0][i] < bb[1][i] and bb[0][i] < aa[1][i] for i in range(3))


def main():
    tibia = tibia_revision.build_tibia_parts(leg)
    previous = baseline_leg.build_leg()
    femur = [p for p in previous if p['link'] == 'femur']
    rows = []
    collisions = []
    checks = 0
    for p in tibia:
        count = 0
        solids = TopExp_Explorer(p['shape'], TopAbs_SOLID)
        while solids.More():
            count += 1
            solids.Next()
        rows.append(dict(name=p['name'], valid=valid(p['shape']), solid_count=count,
                         volume_mm3=volume(p['shape']), bounds_mm=bounds(p['shape']),
                         centroid_mm=centroid(p['shape'])))
        export_stl(p['shape'], OUT / (p['name'] + '.stl'))
    for a, b in itertools.combinations(tibia, 2):
        if overlaps(a['shape'], b['shape']):
            checks += 1
            v = common_volume(a['shape'], b['shape'])
            if v > 1e-3:
                collisions.append(dict(angle=None, a=a['name'], b=b['name'], volume_mm3=v))
    # Dense local knee sweep; whole-robot checks are a separate release check.
    for angle in range(70, 92):
        for a in tibia:
            for b in femur:
                moving = rotate(translate(b['shape'], (-90, 0, 0)), (0, 1, 0), -angle)
                if overlaps(a['shape'], moving):
                    checks += 1
                    v = common_volume(a['shape'], moving)
                    if v > 1e-3:
                        collisions.append(dict(angle=angle, a=a['name'], b=b['name'], volume_mm3=v))
    wire_checks = []
    for angle in range(70, 92):
        reserve = rotate(leg._pitch(leg.sc.plugged_profile_reserve(), False), (0, 1, 0), -angle)
        for p in tibia[:2]:
            checks += 1
            v = common_volume(p['shape'], reserve)
            wire_checks.append(dict(angle=angle, part=p['name'], volume_mm3=v))
            if v > 1e-3:
                collisions.append(dict(angle=angle, a=p['name'], b='plugged_wire_reserve', volume_mm3=v))
    access = []
    for x, z in tibia_revision.BRIDGE_BOLT_XZ:
        # Screw shaft through the whole fork and OD7 nut/washer access on both faces.
        for label, tool in [('shaft', cylinder(1.69, 52, (x, -26, z), (0, 1, 0))),
                            ('aux_washer', cylinder(3.5, 5, (x, -28, z), (0, 1, 0))),
                            ('main_washer', cylinder(3.5, 5, (x, 23, z), (0, 1, 0)))]:
            v = sum(common_volume(p['shape'], tool) for p in tibia[:2])
            access.append(dict(x=x, z=z, kind=label, volume_mm3=v))
            if v > 1e-3:
                collisions.append(dict(angle=None, a='tibia', b=label, volume_mm3=v))
    old_print = sum(volume(p['shape']) for p in previous if p['link'] == 'tibia' and p['printable'])
    new_print = sum(volume(p['shape']) for p in tibia if p['printable'])
    report = dict(status='pass' if not collisions else 'fail',
                  source_sha256=hashlib.sha256((ROOT / 'cad/tibia_revision.py').read_bytes()).hexdigest(),
                  baseline_leg_sha256=hashlib.sha256(BASELINE_LEG.read_bytes()).hexdigest(),
                  bridge_bounds_xz=tibia_revision.BRIDGE_BOUNDS_XZ,
                  bridge_bolt_xz=tibia_revision.BRIDGE_BOLT_XZ, parts=rows,
                  checks=checks, collisions=collisions, wire_checks=wire_checks,
                  fastener_access=access, printable_volume_mm3=new_print,
                  previous_printable_volume_mm3=old_print,
                  solid_PLA_mass_delta_g=(new_print-old_print)*0.00124,
                  interpretation='The main structural piece is straight in side profile. The separate short auxiliary cheek permits assembly around both servo shafts. Dense local checks cover integer knee angles from 70 to 91 degrees; they do not prove all configurations or printed strength.')
    (OUT / 'geometry_check.json').write_text(json.dumps(report, indent=2) + '\n')
    (OUT / 'geometry_check.txt').write_text(json.dumps(report, indent=2) + '\n')
    export_step([p['shape'] for p in tibia], OUT / 'straight_tibia.step')
    print(json.dumps({k:report[k] for k in ('status','checks','collisions','printable_volume_mm3','solid_PLA_mass_delta_g')}, indent=2))


if __name__ == '__main__':
    main()
