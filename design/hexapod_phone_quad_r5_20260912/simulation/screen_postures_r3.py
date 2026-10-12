"""Bounded static candidate screen against an explicit R3 mass manifest."""
import argparse
import json
from pathlib import Path
import numpy as np
from export_urdf import digest, load_manifest
from kinematics import FEMUR, LEGS, TIBIA, crawl_plan, sample_phase
from statics import loads


CANDIDATES=[
    ("rest_r2",30,75,30,15,20),
    ("hip30_knee81_shift10_lift10",30,81,20,10,10),
    ("hip30_knee81_shift10_lift15",30,81,20,10,15),
    ("hip30_knee81_shift15_lift10",30,81,20,15,10),
    ("hip30_knee81_shift15_lift15",30,81,20,15,15),
    ("hip29_knee82_shift15_lift15",29,82,20,15,15),
    ("hip29_knee82_shift10_lift15",29,82,20,10,15),
    ("hip30_knee81_stride22_shift10_lift15",30,81,22,10,15),
    ("hip30_knee81_stride24_shift10_lift15",30,81,24,10,15),
]


def screen(manifest_path,output,selected=None):
    initial_hash=digest(manifest_path)
    manifest=load_manifest(manifest_path)
    rows=[]
    candidates=[case for case in CANDIDATES if selected is None or case[0] in selected]
    if selected is not None and set(selected)!={case[0] for case in candidates}:
        raise ValueError("Unknown candidate case requested")
    for name,hip,knee,stride,shift,lift in candidates:
        peak,margin,outward=0.0,1.0,1.0
        minimum_force=1e9
        bounds=np.array([[1e5,-1e5]]*3)
        error=None
        samples=[]
        try:
            for phase_index,phase in enumerate(crawl_plan(stride=stride/1000,shift=shift/1000,lower=0,lift=lift/1000,neutral=np.radians([0,hip,knee]))):
                for t in np.linspace(0,1,41):
                    base,feet=sample_phase(phase,float(t))
                    support=[leg for leg in LEGS if not(phase["kind"]=="swing" and leg==phase["leg"])]
                    result=loads(manifest,base,feet,support)
                    local_peak=max(abs(v) for v in result["torques"].values())
                    peak=max(peak,local_peak)
                    margin=min(margin,result["support_margin_m"])
                    minimum_force=min(minimum_force,min(result["normal_forces"].values()))
                    for q in result["angles"].values():
                        deg=np.degrees(q)
                        bounds[:,0]=np.minimum(bounds[:,0],deg)
                        bounds[:,1]=np.maximum(bounds[:,1],deg)
                        outward=min(outward,float(FEMUR*np.cos(q[1])+TIBIA*np.cos(q[1]+q[2])))
                    samples.append({"phase":phase_index,"kind":phase["kind"],"fraction":float(t),"base_mm":(result["base"]*1000).tolist(),"joint_deg":{leg:np.degrees(q).tolist() for leg,q in result["angles"].items()},"torque_nm":result["torques"]})
        except ValueError as exc:
            error=str(exc)
        rows.append({"case":name,"hip_deg":hip,"knee_deg":knee,"stride_mm":stride,"shift_mm":shift,"lift_mm":lift,"sample_count":len(samples),"peak_torque_nm":peak,"minimum_support_margin_mm":margin*1000,"minimum_outward_toe_mm":outward*1000,"minimum_support_force_n":minimum_force,"joint_ranges_deg":bounds.tolist(),"ik_failure":error,"static_screen_0588":bool(error is None and peak<=.588 and minimum_force>=0),"samples":samples})
    result={"scope":"Mass-corrected kinematics and gravity loads only. No dynamics or physical contact pass. Outward-toe clearance must be verified using the actual CAD.","manifest_sha256":initial_hash,"inputs_unchanged":digest(manifest_path)==initial_hash,"mass_model":manifest.get("mass_model"),"mass_kg":sum(v["mass_kg"] for v in manifest["links"].values()),"cases":rows}
    output.mkdir(parents=True,exist_ok=True)
    (output/"static_candidates.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    lines=["R3 STATIC CANDIDATE SCREEN",result["scope"],f"Mass: {result['mass_kg']:.6f} kg",f"Manifest SHA256: {initial_hash}",""]
    for row in rows:
        lines.append(f"{row['case']}: static screen {row['static_screen_0588']}; peak {row['peak_torque_nm']:.6f} Nm; outward {row['minimum_outward_toe_mm']:.3f} mm; support margin {row['minimum_support_margin_mm']:.3f} mm; IK failure {row['ik_failure']}")
    (output/"static_candidates.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({**{k:v for k,v in result.items() if k!="cases"},"cases":[{k:v for k,v in row.items() if k!="samples"} for row in rows]},indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--cases",nargs="+")
    args=parser.parse_args()
    screen(args.manifest,args.output,args.cases)
