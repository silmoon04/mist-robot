from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'cad'))
import leg
import tibia_revision
from geom import bounds, volume, rotate, translate
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common

t = tibia_revision.build_tibia_parts(leg)
f = [p for p in leg.build_leg() if p['link'] == 'femur']
for a in t[:2]:
    for b in f:
        if not b['name'].startswith('femur_'): continue
        other = rotate(translate(b['shape'], (-90, 0, 0)), (0, 1, 0), -91)
        op = BRepAlgoAPI_Common(a['shape'], other)
        op.Build()
        if volume(op.Shape()) > .001:
            print(a['name'], b['name'], volume(op.Shape()), bounds(op.Shape()), flush=True)
