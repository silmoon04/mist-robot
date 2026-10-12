"""Separate angular travel, yaw inertia and vertical-load bending effects."""
import json
import numpy as np
import build,leg,hip_revision as hip,geom as g

def main():
    all_parts=leg.build_leg();rows=[]
    for length,post in [(70,24.5),(82,36.5)]:
        parts=[p for p in all_parts if p['link'] not in ('base_mount','coxa')]+hip.build_coxa(length,post)
        frames={'coxa':build.pose(),'femur':build.pose((length,0,0),(0,30,0))}
        frames['tibia']=frames['femur']@build.pose((90,0,0),(0,81,0))
        mass_total=0;izz=0
        for p in parts:
            mass=p.get('mass_kg',g.volume(p['shape'])*(.0000027 if p['material']=='metal' else .00000124));mass_total+=mass
            r=frames[p['link']][:3,:3];t=frames[p['link']][:3,3]
            com=(r@np.array(g.centroid(p['shape']))+t)/1000
            inertia=r@(np.array(g.inertia(p['shape']))*mass/g.volume(p['shape'])*1e-6)@r.T
            izz+=inertia[2,2]+mass*(com[0]**2+com[1]**2)
        rows.append({'coxa_mm':length,'moving_mass_full_solid_kg':mass_total,'yaw_axis_inertia_kg_m2':izz})
    report={'cases':rows,'yaw_inertia_ratio':rows[1]['yaw_axis_inertia_kg_m2']/rows[0]['yaw_axis_inertia_kg_m2'],
        'added_vertical_force_bending_moment_Nm_per_N':.012,
        'explanation':'Angular travel is not itself a torque demand. At unchanged angular acceleration, inertial yaw torque scales with Izz. A vertical toe force adds bending about a horizontal axis through the yaw support; it does not directly create torque about an ideal vertical yaw axis.',
        'scope':'Comparison at the same relative hip/knee pose, using full-solid printed geometry and declared servo mass. Omits fasteners, flexible cables and ground-contact friction.'}
    (build.OUT/'yaw_load_comparison.json').write_text(json.dumps(report,indent=2));print(report)

if __name__=='__main__':main()
