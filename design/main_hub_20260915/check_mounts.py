"""Check the short mounting-screw stack against the actual local leg."""
import json,math
import numpy as np
import build_hub as bh
g=bh.g;lb=bh.lb;leg=bh.leg;OUT=bh.OUT

def main():
    hub=g.import_step(OUT/'Main_Hub_4Leg.step');parts=leg.build_leg()
    for p in parts:
        if p['name'] in ('coxa_upper_and_hip_saddle','coxa_lower_auxiliary_arm'):
            p['shape']=g.import_step(bh.ROOT.parent/'print_dfm_20260914/output/parts_step'/(p['name']+'.step'))
    checks=0;hits=[];stack=[]
    for x,y in leg.CONSTANTS['mount_holes_xy']:
        # Local shaft datum: top of foot=-29, hub top=-32, bottom=-38.
        # M12 without an upper washer: tip=-41. Nut/washer end=-40.7.
        tools=[('M3x12 shaft',g.cylinder(1.5,12,(x,y,-41))),('head',g.cylinder(2.85,3,(x,y,-29))),
               ('bottom washer',g.cut(g.cylinder(3.85,.5,(x,y,-38.5)),g.cylinder(1.6,.5,(x,y,-38.5)))),
               ('nut',g.cut(leg._hex_z(x,y,-40.7,2.2,5.2),g.cylinder(1.5,2.2,(x,y,-40.7))))]
        for deg in bh.ANGLES.values():
            xx,yy=bh.point(75,0,deg);mount=lb.pose((xx,yy,38),(0,0,deg))
            for tag,shape in tools:
                s=lb.shape_at(shape,mount);a,b=g.bounds(s),g.bounds(hub)
                if all(a[1][i]>b[0][i]+1e-6 and b[1][i]>a[0][i]+1e-6 for i in range(3)):
                    checks+=1;v=g.common_volume(s,hub)
                    if v>.001:hits.append({'part':'hub','tool':tag,'mm3':v})
        for yaw in (-60,-55,-30,0,30,55,60):
            frames=bh.local_frames(yaw,30,81)
            for p in parts:
                s=lb.shape_at(p['shape'],frames[p['link']]);b=g.bounds(s)
                for tag,shape in tools:
                    a=g.bounds(shape)
                    if not all(a[1][i]>b[0][i]+1e-6 and b[1][i]>a[0][i]+1e-6 for i in range(3)):continue
                    checks+=1;v=g.common_volume(shape,s)
                    if v>.001:hits.append({'part':p['name'],'yaw':yaw,'tool':tag,'mm3':v})
        stack.append({'mount_local_xy_mm':[x,y],'screw_under_head_length_mm':12,'printed_stack_mm':9,'flat_washer_mm':.5,'nut_mm':2.2,'tip_beyond_nut_mm':.3})
    result={'status':'pass' if not hits else 'fail','hub_stl_sha256':bh.sha(OUT/'Main_Hub_4Leg.stl'),'checks':checks,'intersections':hits,'fastener_stacks':stack,
        'hardware_per_leg':'Four M3x12 screws, four M3 nuts, four flat washers below deck. No top washers because OD7.7 washers touch the clamp.',
        'limitation':'Nominal0.3mm beyond nut is small; confirm the actual screw traverses the entire nut before loading. Nut thickness2.2mm is the user approximation; washer0.5mm remains unmeasured. Longer M18 screws must not be substituted without checking the rotating lower-arm path.'}
    (OUT/'Mount_Fasteners.json').write_text(json.dumps(result,indent=2));print(result);assert not hits

if __name__=='__main__':main()
