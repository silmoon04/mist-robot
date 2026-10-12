"""Build an inspectable inward-knee proposal without changing production CAD."""
from pathlib import Path
import sys
import json
import hashlib
import math
import tempfile
import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

STUDY=Path(__file__).resolve().parent
CAD=STUDY.parents[1]/"cad"
sys.path.insert(0,str(STUDY))
sys.path.insert(1,str(CAD))
import candidate_leg as candidate
import servo_contract as sc
import leg as production
import geom
from check_leg import transformed,overlaps


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def properties(part):
    v=geom.volume(part["shape"])
    density={"pla":1.24e-6,"metal":2.70e-6}.get(part["material"],1.24e-6)
    mass=part.get("mass_kg",v*density)
    return {"name":part["name"],"link":part["link"],"material":part["material"],
            "mass_kg":mass,"com_mm":list(geom.centroid(part["shape"])),
            "inertia_kg_m2":(np.array(geom.inertia(part["shape"]))*mass/v*1e-6).tolist(),
            "solid_volume_mm3":v}


def totals(parts):
    rows=[properties(p) for p in parts]
    mass=sum(r["mass_kg"] for r in rows)
    com=sum(r["mass_kg"]*np.array(r["com_mm"]) for r in rows)/mass
    return {"mass_kg":mass,"com_mm":com.tolist(),
            "printed_solid_mass_kg":sum(r["mass_kg"] for r in rows if r["material"]=="pla")}


def render_variants(base,cand,path):
    colors={"pla":"#91b5a2","servo":"#303943","metal":"#bfc7ce"}
    fig=plt.figure(figsize=(14,8),facecolor="#f5f4ef")
    all_bounds=[geom.bounds(p["shape"]) for p in base+cand]
    low=np.min([b[0] for b in all_bounds],axis=0);high=np.max([b[1] for b in all_bounds],axis=0)
    with tempfile.TemporaryDirectory(prefix="inward_leg_view_") as td:
        for index,(parts,title) in enumerate(((base,"A  |  Previous outward layout"),(cand,"B  |  Inward knee proposal")),1):
            ax=fig.add_subplot(1,2,index,projection="3d",facecolor="#f5f4ef")
            all_triangles=[];all_colors=[]
            for j,p in enumerate(parts):
                out=Path(td)/f"{index}_{j}.stl";geom.export_stl(p["shape"],out)
                mesh=trimesh.load_mesh(out)
                light=np.array([-.4,-.6,1.0]);light/=np.linalg.norm(light)
                shade=.48+.52*np.clip(mesh.face_normals@light,0,1)
                face_colors=np.array(to_rgb(colors.get(p["material"],"#aaaaaa")))[None,:]*shade[:,None]
                all_triangles.append(mesh.vertices[mesh.faces]);all_colors.append(face_colors)
            ax.add_collection3d(Poly3DCollection(np.concatenate(all_triangles),
                facecolors=np.concatenate(all_colors),edgecolors="none",linewidths=0))
            ax.set_xlim(low[0]-6,high[0]+6);ax.set_ylim(low[1]-6,high[1]+6);ax.set_zlim(low[2]-6,high[2]+6)
            ax.set_box_aspect(high-low);ax.set_proj_type("ortho");ax.view_init(elev=17,azim=-64)
            ax.set_axis_off();ax.set_title(title,fontsize=16,pad=6)
    fig.suptitle("Same 50 / 90 / 105 mm joint spacing and 30 / 81 degree stance",fontsize=15,y=.95)
    fig.text(.5,.07,"Study model only. Corrected C018 datum, case steps, auxiliary cable pockets and top bridge.",
             ha="center",fontsize=11)
    fig.savefig(path,dpi=160,bbox_inches="tight");plt.close(fig)


def main():
    original_hash=sha(CAD/"leg.py")
    a=production.build_leg();b=candidate.build_leg()
    ap=transformed(a,30,81);bp=transformed(b,30,81)
    solid_hits=overlaps(bp)
    print("NEUTRAL_SOLID_INTERSECTIONS",solid_hits,flush=True)
    geom.export_step([p["shape"] for p in bp],STUDY/"inward_leg_candidate.step")
    geom.export_stl(geom.compound([p["shape"] for p in bp]),STUDY/"inward_leg_candidate_assembly.stl")
    print("STEP_AND_STL_EXPORTED",flush=True)
    render_variants(ap,bp,STUDY/"inward_leg_comparison.png")
    print("PREVIEW_EXPORTED",flush=True)
    bore_checks=[]
    groups=(("yaw",False,0,"base_mount",("yaw_case_saddle","case_cap_yaw")),
            ("hip",True,50,"coxa",("coxa_upper_and_hip_saddle","case_cap_hip")),
            ("knee",False,90,"femur",("femur_main_and_knee_saddle","case_cap_knee")))
    byname={p["name"]:p for p in b}
    for name,tail_out,x0,link,part_names in groups:
        for x,z in sc.CLAMP_BOLT_XZ:
            tool=candidate._hole_y(x,z,-18.3,35.6,radius=1.5)
            if name!="yaw":tool=candidate._pitch(tool,tail_out,x0)
            hits=[{"part":pn,"volume_mm3":geom.common_volume(byname[pn]["shape"],tool)} for pn in part_names]
            bore_checks.append({"joint":name,"servo_local_axis_xz_mm":[x,z],"checks":hits,
                                "passed":all(h["volume_mm3"]<.01 for h in hits)})
    walk=[]
    for hip,knee in ((16,70),(16,91),(30,81),(34,70),(34,91)):
        for yaw in (-22,22):
            hits=overlaps(transformed(b,hip,knee,yaw),different_link_only=True)
            walk.append({"yaw_deg":yaw,"hip_deg":hip,"knee_deg":knee,"solid_intersections":hits})
            print("WALK_SAMPLE",yaw,hip,knee,"INTERSECTIONS",len(hits),flush=True)
    result={"status":"Analysis candidate, not production release",
            "production_source_sha256":original_hash,"production_source_unchanged":original_hash==sha(CAD/"leg.py"),
            "candidate_source_sha256":sha(STUDY/"candidate_leg.py"),"contract_source_sha256":sha(STUDY/"servo_contract.py"),
            "source_corrections":["Shaft is 12.5 mm from the case center, not the short end",
                                  "Sockets exit the auxiliary face, not the longitudinal tail",
                                  "Supplier case steps retained using valid exterior geometry",
                                  "Auxiliary disc uses a provisional 0.3 mm face clearance and integral lands"],
            "joint_centers_mm":{"hip":[50,0,0],"knee":[90,0,0],"toe":[105,0,0]},
            "bridge":{"bounds_xz_mm":[[58,13.5],[72,27.5]],"crossbolt_xz_mm":[65,20.5]},
            "neutral_solid_intersections":solid_hits,"clamp_screw_path_checks":bore_checks,"walking_samples":walk,
            "baseline_neutral_model":totals(ap),"candidate_neutral_model":totals(bp),
            "candidate_parts_in_owning_frames":[properties(p) for p in b],
            "baseline_parts_in_owning_frames":[properties(p) for p in a],
            "limitations":["Baseline includes known case-datum and screw-access errors and is not a validated reference assembly",
                           "Servo center of mass is a uniform exterior-volume estimate with a 55 g total, not a measured servo mass distribution",
                           "Printed mass uses solid PLA at 1.24 g per cubic centimeter; slicing and changed fasteners are not included",
                           "Supplier shell geometry is dimensionally compatible but not proven to be the exact owned C018 version",
                           "User plug projection is approximate and not measured from the shaft datum",
                           "Blind auxiliary cable pockets and 0.3 mm axial float require physical fit and free-rotation checks",
                           "Local leg tests do not establish full-body clearance or printed strength"],
            "artifacts":{"step":"inward_leg_candidate.step","assembly_stl":"inward_leg_candidate_assembly.stl",
                         "preview":"inward_leg_comparison.png"}}
    result["printed_solid_mass_delta_g"]=(result["candidate_neutral_model"]["printed_solid_mass_kg"]-
                                           result["baseline_neutral_model"]["printed_solid_mass_kg"])*1000
    result["leg_com_shift_mm"]=(np.array(result["candidate_neutral_model"]["com_mm"])-
                                 result["baseline_neutral_model"]["com_mm"]).tolist()
    result["minimum_checks_passed"]=(not solid_hits and all(c["passed"] for c in bore_checks)
                                       and all(not s["solid_intersections"] for s in walk))
    (STUDY/"candidate_comparison.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    text=f"Inward knee study\nMinimum solid and clamp-path checks passed: {result['minimum_checks_passed']}\n"
    text+=f"Printed solid mass change per leg: {result['printed_solid_mass_delta_g']:.3f} g\n"
    text+=f"Model leg center shift in the 30/81 stance: {result['leg_com_shift_mm']} mm\n"
    text+="The comparison includes corrected hardware geometry and bracket changes, not just rotating the knee case.\n"
    text+="\n".join(result["limitations"])+"\n"
    (STUDY/"candidate_comparison.txt").write_text(text,encoding="utf-8")
    print("COMPARISON_WRITTEN",result["minimum_checks_passed"],flush=True)


if __name__=="__main__":main()
