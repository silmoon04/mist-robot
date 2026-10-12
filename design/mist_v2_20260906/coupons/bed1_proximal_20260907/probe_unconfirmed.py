"""Exercise draft geometry in memory. This script writes no printable exports."""
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
import build_bed as build

OUT = Path(__file__).resolve().parent
PROVISIONAL = dict(status="unconfirmed_probe_only", carrier_boss=dict(
    outer_diameter_mm=34, height_mm=8.4, through_diameter_mm=20,
    floor_mm=1.2, seat_depth_mm=7.2, candidate_seats_mm=[22.25,22.4,22.7],
    lead_in_height_mm=.6, lead_in_diametral_mm=1.2,
    bolt_centers_local_mm=[[-14,0],[14,0]], bolt_diameter_mm=3.4),
    carrier_keeper=dict(outer_diameter_mm=34, inner_diameter_mm=20,
        thickness_mm=2.4, bolt_centers_local_mm=[[-14,0],[14,0]], bolt_diameter_mm=3.4),
    face_carrier=dict(thickness_mm=8, center_bore_mm=7.3, sleeve_seat_mm=6.6),
    jack_bridge=dict(nut_pocket_af_mm=7.2, plate_side_opening=True))


def run():
    import cadquery as cq
    import trimesh
    from mesh_checks import inspect_mesh_shells
    before = build.protected_hashes()
    recipe, original = build.make_recipe(PROVISIONAL)
    parts, meshes = [], []
    checks = []
    for data in recipe["parts"]:
        print("Probing", data["name"], flush=True)
        body = build.build_shape(cq, data)
        valid = body.isValid()
        count = len(body.Solids())
        assert valid and count == 1, (data["name"], valid, count)
        v, f = body.tessellate(.03, .08)
        mesh = trimesh.Trimesh([p.toTuple() for p in v], f, process=True)
        assert mesh.is_watertight and mesh.is_winding_consistent, data["name"]
        shell_checks = inspect_mesh_shells(mesh)
        parts.append(body)
        meshes.append(mesh)
        checks.append(dict(part=data["name"], brep_valid=valid, solid_count=count,
            volume_mm3=body.Volume(), watertight=True, mesh_shell_checks=shell_checks))
    pairs = []
    for i, a in enumerate(parts):
        for j, b in enumerate(parts[:i]):
            overlap = a.intersect(b).Volume()
            gap = a.distance(b)
            assert overlap < 1e-5 and gap > 1e-5, (j, i, overlap, gap)
            pairs.append(dict(parts=[j+1,i+1], overlap_mm3=overlap, gap_mm=gap))
    old06 = build.build_shape(cq, original["parts"][5])
    loss = old06.cut(parts[5]).Volume()
    assert loss < 1e-5
    bb = cq.Compound.makeCompound(parts).BoundingBox()
    combined = trimesh.util.concatenate(meshes)
    print("Mesh bounds", combined.bounds.tolist(), "OCC extents", [bb.xlen,bb.ylen,bb.zlen], flush=True)
    assert all(d <= 216.00001 for d in combined.extents[:2]), combined.bounds
    assert before == build.protected_hashes()
    result = dict(status="unconfirmed_geometry_probe_passed_not_final", print_exports_written=False,
        dimensions_confirmed=False, provisional_contract=PROVISIONAL,
        checks=checks, pairwise_checks=pairs, extent_mm=combined.extents.tolist(),
        occ_bounding_extent_mm=[bb.xlen,bb.ylen,bb.zlen],
        original06_removed_mm3=loss, original_files_unchanged=True)
    (OUT / "probe_unconfirmed.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k not in ["checks","pairwise_checks"]},indent=2), flush=True)


if __name__ == "__main__":
    run()
