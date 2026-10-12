from pathlib import Path
import sys
import json
import hashlib
import importlib.util

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT / 'cad'))
import leg
import tibia_revision
from geom import cylinder, rotate, translate, common_volume, bounds

source = ROOT.parent / 'hexapod_phone_quad_20260912/cad/leg.py'
spec = importlib.util.spec_from_file_location('r4_tool_access_reference', source)
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)
fixed = [p for p in reference.build_leg() if p['link'] == 'femur']
rows = []
for angle in (70, 81, 91):
    for x, z in tibia_revision.BRIDGE_BOLT_XZ:
        for side, tool in [('main', cylinder(4.0, 20, (x, 23, z), (0, 1, 0))),
                           ('auxiliary', cylinder(4.0, 20, (x, -43, z), (0, 1, 0)))]:
            hits = []
            for p in fixed:
                shape = rotate(translate(p['shape'], (-90, 0, 0)), (0, 1, 0), -angle)
                a, b = bounds(tool), bounds(shape)
                if not all(a[0][i] < b[1][i] and b[0][i] < a[1][i] for i in range(3)):
                    continue
                v = common_volume(tool, shape)
                if v > .001:
                    hits.append(dict(part=p['name'], volume_mm3=v))
            rows.append(dict(knee_angle_deg=angle, bolt_xz=[x, z], side=side, collisions=hits))
report = dict(status='pass' if not any(r['collisions'] for r in rows) else 'fail',
              source_sha256=hashlib.sha256((ROOT / 'cad/tibia_revision.py').read_bytes()).hexdigest(),
              probe='Diameter 8 mm by 20 mm driver or socket corridor outside both fork faces.',
              tested_knee_degrees=[70, 81, 91], checks=rows,
              scope='Neighboring femur printed parts and servo hardware. Whole-robot access is outside this study.')
for suffix in ('json', 'txt'):
    (OUT / ('tool_access.' + suffix)).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
