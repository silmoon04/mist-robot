"""Conditional printed-PLA strength screen, using current exported R2 meshes.

Run with Python, numpy, trimesh and shapely. Units: N, mm, MPa.
This is a section/connection calculation, not finite element analysis.
"""
from pathlib import Path
import hashlib
import json
import math
import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
MESH = ROOT / 'cad/output/parts_mesh'
ALLOW = {'XY_tension_MPa': 12., 'Z_tension_MPa': 4., 'shear_MPa': 3., 'bearing_MPa': 8.}
# These are screening assumptions, not measurements of the user's spool.
ETA = 0.5  # conditional effective area/inertia ratio, see report
KT = 2.0   # assumed notch multiplier, not a resolved notch solution


def section(name, axis, position):
    mesh = trimesh.load_mesh(MESH / (name + '.stl'))
    normal = np.eye(3)[axis]
    sec = mesh.section(plane_normal=normal, plane_origin=normal*position)
    axes = [i for i in range(3) if i != axis]
    polygons = [Polygon(points[:, axes]) for points in sec.discrete]
    # Symmetric difference retains holes without relying on mesh winding.
    shape = polygons[0]
    for poly in polygons[1:]:
        shape = shape.symmetric_difference(poly)
    components = [shape] if shape.geom_type == 'Polygon' else list(shape.geoms)
    A = Qx = Qy = Ixx = Iyy = Ixy = 0.
    vertices = []
    for poly in components:
        poly = orient(poly, sign=1.)
        for ring in [poly.exterior, *poly.interiors]:
            xy = np.asarray(ring.coords)
            vertices.extend(xy.tolist())
            x, y = xy[:-1].T
            u, v = xy[1:].T
            c = x*v-u*y
            A += c.sum()/2
            Qx += ((x+u)*c).sum()/6
            Qy += ((y+v)*c).sum()/6
            Ixx += ((y*y+y*v+v*v)*c).sum()/12
            Iyy += ((x*x+x*u+u*u)*c).sum()/12
            Ixy += ((2*x*y+x*v+u*y+2*u*v)*c).sum()/24
    cx, cy = Qx/A, Qy/A
    Ixx -= A*cy*cy
    Iyy -= A*cx*cx
    Ixy -= A*cx*cy
    centered = np.asarray(vertices)-[cx, cy]
    # Unit bending moments in both transverse directions, including Ixy.
    inertia = np.array([[Iyy, Ixy], [Ixy, Ixx]])
    Z = [1/np.max(np.abs(centered @ np.linalg.solve(inertia, vec)))
         for vec in ([0., 1.], [1., 0.])]
    return dict(part=name, cut_axis='xyz'[axis], cut_mm=position,
                transverse_axes=['xyz'[i] for i in axes], area_mm2=A,
                centroid_transverse_mm=[cx, cy], I_transverse_mm4=[Ixx,Iyy,Ixy],
                section_modulus_transverse_mm3=Z)


def main():
    trajectory = json.loads((ROOT/'simulation/output/trajectory.json').read_text())
    sim = json.loads((ROOT/'simulation/output/simulation_report.json').read_text())
    frames = trajectory['frames']
    peak_f = max((v,f['time_s'],leg) for f in frames for leg,v in f['foot_normal_n'].items())
    peak_t = max((abs(v),f['time_s'],j) for f in frames for j,v in f['joint_torque_nm'].items())
    mass = sim['mass_kg']
    loads = {'mass_kg':mass, 'gravity_m_s2':9.81,
             'sampled_peak_foot_N_time_s_leg':peak_f,
             'sampled_peak_torque_Nm_time_s_joint':peak_t,
             'two_leg_static_N_per_leg':mass*9.81/2,
             'two_leg_2g_N_per_leg':mass*9.81,
             'assumed_side_force_N_per_leg':5.,
             'proof_phone_horizontal_force_N':5.,
             'torque_cap_Nm':.588,
             'note':'Two leg and 2g cases are structural envelopes; balance and servo feasibility are not established.'}
    # Freeze the load envelope before calculating or recommending changes.
    (OUT/'frozen_loads.json').write_text(json.dumps(loads,indent=2)+'\n')
    specs = [('FL_femur_main_and_knee_saddle',0,40),
             ('FL_tibia_curved_main_and_foot',0,30),
             ('FL_tibia_curved_main_and_foot',0,80),
             ('FL_coxa_lower_auxiliary_arm',0,20),
             ('FL_coxa_upper_and_hip_saddle',2,-25),
             ('FL_coxa_upper_and_hip_saddle',2,-38),
             ('FL_femur_main_and_knee_saddle',1,0),
             ('FL_tibia_curved_main_and_foot',1,0)]
    sections = [section(*s) for s in specs]
    F = loads['two_leg_2g_N_per_leg']
    results=[]
    def stress(label, nominal, allowable, detail):
        demand = nominal*KT/ETA
        results.append(dict(check=label, solid_nominal_MPa=nominal,
                            screening_demand_MPa=demand, allowable_MPa=allowable,
                            margin_ratio=allowable/demand, detail=detail))
    # Full actuator torque on the main cheek: auxiliary share is not credited.
    for s in sections[:2]:
        zy,zz = s['section_modulus_transverse_mm3']
        stress(s['part']+' sagittal sampled envelope',peak_t[0]*1000/zy,12,
               'Sampled global maximum joint torque on one cheek, applied conservatively also to tibia. No lateral load in this isolated check.')
        stress(s['part']+' combined bending',588/zy+500/zz,12,
               'Moment about Y = 588 Nmm; assumed side load gives moment about Z = 500 Nmm; conservative absolute superposition on one cheek.')
    foot=sections[2]
    stress('Curved foot x80 combined bending',F*25/foot['section_modulus_transverse_mm3'][0]+5*25/foot['section_modulus_transverse_mm3'][1],12,
           'Upper bound perpendicular 2g vertical load over 25 mm and 5 N lateral over 25 mm, full foot section.')
    lower=sections[3]
    stress('Yaw lower arm bending',F*32/lower['section_modulus_transverse_mm3'][0],12,
           'Entire 2g leg load assigned to lower plate at x32. Deliberately conservative unknown upper/lower load sharing.')
    for s in sections[4:6]:
        stress('Coxa post z'+str(s['cut_mm'])+' combined bending',F*18/s['section_modulus_transverse_mm3'][1]+5*50/s['section_modulus_transverse_mm3'][0],12,
               'Vertical load 18 mm eccentric from post, side load 50 mm lever. Net section cut includes actual nut slots at z=-38.')
    # Isolated rectangular bridge section avoids crediting unrelated solids in the same slice.
    for name,b,h in [('Femur cross bridge',5.97,6.8),('Tibia cross bridge',12.5,10.)]:
        stress(name+' across layers',F*38/4/(b*h*h/6),4,
               'Simply supported 38 mm bridge, central 2g leg force. Z tension because print build normal is assembly Y. Check also loss of auxiliary support.')
    bolt_force = 588/(4*7)+F/4
    stress('Horn M3 group projected bearing',bolt_force/(3.4*4),8,
           'Four bolts radius7; force=T/(4r)+F/4. Metal horn thread stripping, preload and splitting are excluded.')
    stress('Horn cheek net section at x0',588/((4*(28**3-7**3-2*(3.4**3+12*3.4*7**2))/12)/14),12,
           'Circular cheek at x0 simplified to outer28 high, central7 and two3.4 holes at z+/-7; exact circular hole widths on this plane. Moment only.')
    stress('Nut pocket remaining face punching shear',bolt_force/(math.pi*5.7*.8),3,
           '0.8 mm face at 3.2 deep nut in4 cheek, approximate cylindrical punch perimeter. Bolt preload can dominate this service force.')
    stress('Single cheek torsion from side eccentricity',3*(5*21)/(30*4**2),3,
           'Thin rectangular open cheek torsion tau~3T/(b*t^2), side force5N at21mm eccentricity; b30,t4. Closed yoke behavior is not credited.')
    stress('Yaw saddle mounting foot strip bending',(F/4)*8/(12*3**2/6),12,
           'Each of four feet carries one quarter 2g load on12x3 strip over8mm. Actual deck load spread and screw contact require fixture test.')
    stress('Case cap end bolt edge ligament',bolt_force/(2*(3.5-1.7)*4),3,
           'Nearest endwall bolt x17 vs outside20.5 gives3.5mm center edge; two1.8mm ligaments through4mm thickness. Preload not included.')
    stress('Phone rear spine through USB opening',2.5*43.25/(8*2**2/6),12,
           '5 N total horizontal screen push shared between two 2x8 spines at z53.25, top frame z97. Worst case remains on the upper posts.')
    stress('Phone lower front bar center push',5*148.5/4/(3*3**2/6),12,
           'Separate misuse screen: 5 N at midpoint of 3x3 bar, simply supported. Phone contact may reduce span but is not credited.')
    # Euler comparison is an elastic upper-level mode check, not shell/local buckling proof.
    I = min(4*30**3/12,30*4**3/12)*ETA
    buckling = math.pi**2*1200*I/(2*90)**2
    paths=[ROOT/'cad/leg.py',ROOT/'cad/body.py',ROOT/'cad/phone.py',
           ROOT/'cad/output/assembly_manifest.json',ROOT/'simulation/output/trajectory.json']
    paths += [MESH/(s[0]+'.stl') for s in specs]
    record=dict(status='conditional_section_screen_not_validated_FEA',loads=loads,
                allowable_assumptions=ALLOW,effective_section_ratio=ETA,notch_factor=KT,
                sections=sections,results=results,
                femur_single_cheek_euler_load_N=buckling,
                source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    (OUT/'strength_results.json').write_text(json.dumps(record,indent=2)+'\n')
    print('Peak sampled foot:',peak_f,'Peak sampled torque:',peak_t)
    for r in results:
        print(f"{r['check']}: {r['screening_demand_MPa']:.2f} MPa; conditional margin {r['margin_ratio']:.2f}")
    print('Euler single cheek N:',buckling)


if __name__=='__main__':
    main()
