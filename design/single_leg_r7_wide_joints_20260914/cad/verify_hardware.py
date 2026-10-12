from pathlib import Path
import json
import build,leg,geom as g

def main():
    parts,frames=build.load_assembly()
    hits=[]
    for x,y in ((7,0),(-7,0),(0,7),(0,-7)):
        washer=g.cut(g.cylinder(3.85,1,(x,y,-50.5)),g.cylinder(1.6,1.2,(x,y,-50.6)))
        head=g.cylinder(2.85,3,(x,y,-53.5));shaft=g.cylinder(1.5,20,(x,y,-50.5))
        for tag,shape in [('two OD7.7 washers',washer),('M20 head',head),('M20 shaft',shaft)]:
            for p in parts:
                if p['link']!='coxa' or not p['printable']:continue
                a,b=g.bounds(shape),g.bounds(p['shape'])
                if any(a[1][k]<=b[0][k] or b[1][k]<=a[0][k] for k in range(3)):continue
                v=g.common_volume(shape,p['shape'])
                if v>.01:hits.append({'part':p['name'],'hardware':tag,'mm3':v})
    def ring(point,axis=(0,0,1),thickness=.5):
        return g.cut(g.cylinder(3.85,thickness,point,axis),g.cylinder(1.6,thickness,point,axis))
    hardware=[]
    import servo_contract as sc
    from hip_revision import HIP_CLAMP_BOLT_XZ
    for link,bolts,xf in [('base_mount',sc.CLAMP_BOLT_XZ,lambda s:s),('coxa',HIP_CLAMP_BOLT_XZ,lambda s:leg._pitch(s,False,82)),('femur',sc.CLAMP_BOLT_XZ,lambda s:leg._pitch(s,False,90))]:
        for x,z in bolts:hardware.append((link,'case washer',xf(ring((x,16.365,z),(0,1,0)))))
    for x,y in ((7,0),(-7,0),(0,7),(0,-7)):hardware.append(('coxa','yaw main washer',ring((x,y,8.5))))
    hardware.append(('coxa','yaw centre washer',ring((0,0,-33.6))))
    for link in ('femur','tibia'):
        for x,z in ((7,0),(-7,0),(0,7),(0,-7)):
            hardware.append((link,'main washer',ring((x,23,z),(0,1,0))))
            hardware.append((link,'auxiliary washers',ring((x,-28,z),(0,1,0),1)))
            hardware.append((link,'M12 auxiliary shaft',g.cylinder(1.5,12,(x,-28,z),(0,1,0))))
        hardware.append((link,'auxiliary centre washer',ring((0,-19.1,0),(0,1,0))))
    for link,coords in [('femur',[(65,20.5)]),('tibia',[(36,0),(44,0)])]:
        for x,z in coords:hardware.append((link,'bridge washer',ring((x,-27.5,z),(0,1,0))))
    for y in (-4.5,4.5):hardware.append(('coxa','post washer',ring((40.5,y,-53.5))))
    for x,y in leg.CONSTANTS['mount_holes_xy']:
        hardware.append(('base_mount','bench head directly on foot',g.cylinder(2.85,3,(x,y,-29))))
        hardware.append(('base_mount','bench M18 shaft without top washer',g.cylinder(1.5,18,(x,y,-47))))
        hardware.append(('base_mount','bench bottom washer',ring((x,y,-39.5))))
    for link,tag,shape in hardware:
        for p in parts:
            if p['link']!=link:continue
            if tag=='M12 auxiliary shaft' and p['material']=='metal':continue
            a,b=g.bounds(shape),g.bounds(p['shape'])
            if any(a[1][k]<=b[0][k]+1e-6 or b[1][k]<=a[0][k]+1e-6 for k in range(3)):continue
            v=g.common_volume(shape,p['shape'])
            if v>.01:hits.append({'part':p['name'],'hardware':tag,'mm3':v})
    print('Hardware intersections',hits,flush=True)
    assert not hits,hits
    report={'status':'pass','manifest_sha256':build.sha(build.OUT/'manifest.json'),'washer_outer_diameter_mm':7.7,'washer_thickness_assumption_mm':.5,'intersections':hits,'bench_top_washers_omitted':True}
    (build.OUT/'hardware_check.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':main()
