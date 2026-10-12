"""Sample the mass-screened gait envelope and reserved connector volumes."""
import itertools
from leg import build_leg,_b,_pitch
from check_leg import transformed,overlaps
from geom import bounds

parts=build_leg()
connector=_b(-47.73,-32.73,-9,9,-27,-9)
reserves=[
    {'name':'reserved_connector_yaw','shape':connector,'link':'base_mount'},
    {'name':'reserved_connector_hip','shape':_pitch(connector,True,50),'link':'coxa'},
    {'name':'reserved_connector_knee','shape':_pitch(connector,True,90),'link':'femur'},
]
samples=list(itertools.product((-18.78,0,18.78),(13.90,24,34.15),(55,70,86.79)))
failures=[]
for yaw,hip,knee in samples:
    posed=transformed(parts,hip,knee,yaw)
    hits=overlaps(posed,different_link_only=True)
    cables=transformed(reserves,hip,knee,yaw)
    cablehits=overlaps(posed+cables)
    cablehits=[h for h in cablehits if any(name.startswith('reserved_connector_') for name in h[:2])]
    if hits or cablehits:failures.append((yaw,hip,knee,hits,cablehits))
print('GAIT_GRID_SAMPLES',len(samples),flush=True)
print('POSITIVE_INTERSECTION_FAILURES',failures,flush=True)
print('Cable reserves use15mm insertion length,18mm width and18mm height; plug dimensions remain unmeasured.',flush=True)
print('Discrete samples do not establish continuous collision freedom.',flush=True)
if failures:raise SystemExit(1)
