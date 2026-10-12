"""Eight requested general-purpose M3 spacers; not yaw-joint spacers."""
import build_hub as b
import json,math
g=b.g;OUT=b.OUT
shape=g.cut(g.cylinder(6.5,8,(0,0,0)),g.cylinder(1.7,8,(0,0,0)))
assert g.valid(shape)
assert abs(g.volume(shape)-math.pi*(6.5**2-1.7**2)*8)<1e-6
g.export_stl(shape,OUT/'Spacer_8H_13OD_M3.stl',.025);g.export_step(shape,OUT/'Spacer_8H_13OD_M3.step')
(OUT/'Spacer_Dimensions.json').write_text(json.dumps({'height_mm':8,'outside_diameter_mm':13,'bore_diameter_mm':3.4,'quantity':8,'units':'mm','stl_sha256':b.sha(OUT/'Spacer_8H_13OD_M3.stl'),
    'interpretation':'8mm tall and13mm outside diameter, following the direct reading of the request. These are general M3 spacers, not substitutes for the11.6mm-long OD5.8 yaw spacers or the integral pitch rings.'},indent=2))
