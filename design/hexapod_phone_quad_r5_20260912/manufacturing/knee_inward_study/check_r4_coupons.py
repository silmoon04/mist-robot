"""Independent mesh, registration and retainer checks for the R4 fixtures."""
from pathlib import Path
import tempfile
import json
import numpy as np
import trimesh
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
import r4_coupons as rc

g=rc.g;leg=rc.leg;sc=rc.sc
ROOT=Path(__file__).resolve().parent


def distance(a,b):
    d=BRepExtrema_DistShapeShape(a,b);d.Perform()
    if not d.IsDone():raise RuntimeError("Distance calculation failed")
    return float(d.Value())


def main():
    coupons=rc.build_coupons();rows=[];failures=[]
    export=ROOT/"r4_coupon_stl";export.mkdir(exist_ok=True)
    for p in coupons:
        shape=g.transform(p["shape"],rpy_deg=p["print_rotation"])
        low,high=g.bounds(shape);shape=g.translate(shape,[-v for v in low])
        out=export/(p["name"]+".stl");g.export_stl(shape,out)
        mesh=trimesh.load_mesh(out)
        e=TopExp_Explorer(shape,TopAbs_SOLID);solids=0
        while e.More():solids+=1;e.Next()
        row={"name":p["name"],"solids":solids,"watertight":bool(mesh.is_watertight),
             "winding_consistent":bool(mesh.is_winding_consistent),
             "dimensions_mm":[high[i]-low[i] for i in range(3)]}
        rows.append(row)
        if solids!=1 or not mesh.is_watertight or not mesh.is_winding_consistent:failures.append(row)
    saddle,cap=leg.case_clamp(True,.3);gauge=rc.datum_registration_plate()
    nominal_case=leg.servo_envelope();horn=leg.main_horn()
    fixture_pairs=[]
    for name,shape in (("case",nominal_case),("cap",cap),("saddle",saddle),("main_horn",horn)):
        v=g.common_volume(gauge,shape)
        fixture_pairs.append({"part":name,"intersection_mm3":v})
        if v>.01:failures.append(fixture_pairs[-1])
    wrong= g.translate(nominal_case,(2.385,0,0))
    wrong_overlap=g.common_volume(wrong,saddle)
    if wrong_overlap<=.01:failures.append({"wrong_datum_was_not_rejected":True})
    # The factory-style retainer washer seats on the fixed stub tip. It is
    # separated axially from the freely rotating auxiliary disc.
    washer=g.cut(g.cylinder(3.5,.5,(0,0,sc.AUX_STUB_TIP_Z-.5)),
                 g.cylinder(1.6,.7,(0,0,sc.AUX_STUB_TIP_Z-.6)))
    aux=leg.auxiliary_disc()
    washer_disc_gap=distance(washer,aux)
    if abs(washer_disc_gap-.7)>.001:failures.append({"unexpected_retainer_gap":washer_disc_gap})
    production={p["name"]:p for p in leg.build_leg()}
    pitchwasher=leg._pitch(washer,True)
    washer_cheek=production["femur_auxiliary_cheek"]["shape"]
    washer_cheek_gap=distance(pitchwasher,washer_cheek)
    if g.common_volume(pitchwasher,washer_cheek)>.01 or washer_cheek_gap<.39:
        failures.append({"retainer_washer_cheek_gap":washer_cheek_gap})
    result={"passed":not failures,"coupon_count":len(rows),"meshes":rows,
            "registration_fixture_intersections":fixture_pairs,
            "wrong_2p385_case_datum_intersection_mm3":wrong_overlap,
            "aux_retainer_washer_disc_axial_gap_mm":washer_disc_gap,
            "pitch_retainer_washer_cheek_gap_mm":washer_cheek_gap,
            "horn_pcd_hole_radial_ligament_mm":7-1.7-3.9,
            "retainer_washer_overlap_of_disc_bore_mm":3.5-6.05/2,
            "failures":failures,
            "limits":"Nominal geometry only. Actual horn seating, case fit, washer fit and free rotation require hand assembly."}
    (ROOT/"r4_coupon_checks.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    (ROOT/"r4_coupon_checks.txt").write_text(
        f"R4 coupons: {len(rows)}\nPassed: {result['passed']}\n"
        f"Wrong 2.385 mm datum rejected by {wrong_overlap:.3f} mm3 case-to-clamp intersection.\n"
        f"Auxiliary retainer washer-to-disc gap: {washer_disc_gap:.3f} mm.\n"
        f"Retainer washer-to-printed-cheek gap: {washer_cheek_gap:.3f} mm.\n"+result["limits"]+"\n",encoding="utf-8")
    print(json.dumps({"passed":result["passed"],"coupon_count":len(rows),"failures":failures,
                      "wrong_datum_overlap_mm3":wrong_overlap,"washer_disc_gap_mm":washer_disc_gap,
                      "washer_cheek_gap_mm":washer_cheek_gap}),flush=True)
    return 0 if result["passed"] else 1


if __name__=="__main__":raise SystemExit(main())
