"""Rank a bounded set of postures using the current CAD mass distribution."""
import json
from pathlib import Path
import numpy as np
from export_urdf import DESIGN, HERE, digest, load_manifest
from kinematics import COXA, FEMUR, LEGS, TIBIA, crawl_plan, sample_phase
from statics import loads


def screen():
    manifest_path=DESIGN/"cad/output/assembly_manifest.json"
    manifest=load_manifest(manifest_path)
    rows=[]
    for hip,knee in [(25,76),(30,75),(30,78),(30,80),(35,75),(35,78)]:
        for shift in (15,20):
            peak,margin,outward=0,1,1
            bounds=np.array([[1e5,-1e5]]*3)
            error=None
            try:
                for phase in crawl_plan(stride=.03,shift=shift/1000,lower=0,lift=.02,neutral=np.radians([0,hip,knee])):
                    for t in np.linspace(0,1,21):
                        base,feet=sample_phase(phase,float(t))
                        support=[leg for leg in LEGS if not(phase["kind"]=="swing" and leg==phase["leg"])]
                        result=loads(manifest,base,feet,support)
                        peak=max(peak,max(abs(v) for v in result["torques"].values()))
                        margin=min(margin,result["support_margin_m"])
                        for q in result["angles"].values():
                            deg=np.degrees(q)
                            bounds[:,0]=np.minimum(bounds[:,0],deg)
                            bounds[:,1]=np.maximum(bounds[:,1],deg)
                            outward=min(outward,FEMUR*np.cos(q[1])+TIBIA*np.cos(q[1]+q[2]))
            except ValueError as exc:
                error=str(exc)
            rows.append({"hip_deg":hip,"knee_deg":knee,"shift_mm":shift,"stride_mm":30,"peak_torque_nm":peak,"minimum_support_margin_mm":margin*1000,"minimum_outward_toe_mm":outward*1000,"joint_ranges_deg":bounds.tolist(),"ik_failure":error,"candidate_0588":bool(error is None and peak<=.588 and outward>=.03)})
    output={"manifest_sha256":digest(manifest_path),"mass_kg":sum(i["mass_kg"] for i in manifest["links"].values()),"femur_mm":FEMUR*1000,"candidates":sorted(rows,key=lambda r:r["peak_torque_nm"]),"scope":"Quasi-static candidate screen only; CAD collision sweeps and dynamics must independently pass."}
    (HERE/"posture_screen.json").write_text(json.dumps(output,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(output,indent=2))


if __name__=="__main__":screen()
