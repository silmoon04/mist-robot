"""3D servo-case OBBs from the proposed contract, not completed CAD clearance."""
import itertools
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
AZ = [45,-45,135,-135]
HAND = [1,-1,-1,1]
HOME = [-45,45,45,-45]
L, T = 139.5,130
K = -math.acos((60**2+190**2-L**2-T**2)/(2*L*T))
H = math.atan2(60,190)-math.atan2(T*math.sin(K),L+T*math.cos(K))


def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def case(leg,q):
    theta,phi=math.radians(AZ[leg]+q),math.radians(AZ[leg])
    c,s,ch,sh=math.cos(theta),math.sin(theta),math.cos(H),math.sin(H)
    axes=((c*ch,s*ch,sh),(-s,c,0),(-c*sh,-s*sh,ch))
    pitch=(103*math.cos(phi)+35*c-HAND[leg]*30*s,
           103*math.sin(phi)+35*s+HAND[leg]*30*c,0)
    local=(0,HAND[leg]*59.125,-40.115)
    center=tuple(pitch[i]+sum(local[j]*axes[j][i] for j in range(3)) for i in range(3))
    return center,axes,(24.73/2,35/2,45.23/2)


def sat(a,b):
    ca,aa,ha=a;cb,ab,hb=b
    delta=tuple(cb[i]-ca[i] for i in range(3))
    axes=list(aa)+list(ab)+[cross(x,y) for x in aa for y in ab]
    deficits=[]
    for axis in axes:
        length=math.sqrt(dot(axis,axis))
        if length<1e-10: continue
        axis=tuple(x/length for x in axis)
        ra=sum(ha[i]*abs(dot(axis,aa[i])) for i in range(3))
        rb=sum(hb[i]*abs(dot(axis,ab[i])) for i in range(3))
        deficits.append(ra+rb-abs(dot(delta,axis)))
    return min(deficits)


def main():
    examples=[]
    for delta in (-10,0,10):
        boxes=[case(i,HOME[i]+delta) for i in range(4)]
        examples.append(dict(common_heading_delta_deg=delta,
                             largest_pair_separation_deficit_mm=max(sat(boxes[i],boxes[j]) for i,j in itertools.combinations(range(4),2))))
    convergence=[]
    for yaw in (0,10,20,22,25,30,35,40):
        convergence.append(dict(FL_yaw_deg=yaw,RL_yaw_deg=-yaw,
                                separation_deficit_mm=sat(case(0,yaw),case(2,-yaw))))
    result=dict(status="proposed_knee_servo_cases_only_not_whole_assembly",hip_deg=math.degrees(H),
                contract=dict(case_local_center=[0,59.125,-40.115],case_size=[24.73,35,45.23],
                              complete_handed_mirror=True),
                meaning="Positive separation deficit means intersecting case boxes; negative gives a separating-axis witness, not an exact Euclidean gap.",
                common_heading_samples=examples,convergent_samples=convergence)
    (HERE/"contract_clearance.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__": main()
