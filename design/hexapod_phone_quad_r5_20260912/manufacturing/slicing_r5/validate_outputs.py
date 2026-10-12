"""Verify R5 deposited properties and retained inert slicing evidence."""
from pathlib import Path
import gzip
import hashlib
import json
import math
import numpy as np

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run():
    out = HERE/"output"
    path = out/"production_mass_properties.json"
    data = json.loads(path.read_text())
    manifest = json.loads(Path(data["source_manifest_path"]).read_text())
    assert manifest["revision"] == "hex_quad_r5_inward_hip_straight_tibia"
    assert sha(data["source_manifest_path"]) == data["source_manifest_hash"]
    assert sha(out/"source_assembly_manifest.json") == data["source_manifest_hash"]
    assert len(data["parts"]) == len(manifest["print_parts"])
    expected = {p["sku"]:p for p in manifest["print_parts"]}
    checked = 0
    for row in data["parts"]:
        sku = row["sku"]
        assert row["quantity"] == expected[sku]["quantity"]
        assert sha(row["source_stl_path"]) == row["source_stl_hash"]
        engine = row["engine"]
        for pk,hk in (("original_snapshot_path","original_snapshot_sha256"),
                      ("normalized_snapshot_path","normalized_snapshot_sha256"),
                      ("profile_path","profile_sha256"),
                      ("resolved_settings_path","resolved_settings_sha256"),
                      ("log_path","log_sha256")):
            assert sha(engine[pk]) == engine[hk], (sku,pk)
        evidence = row["gcode_evidence"]
        assert sha(evidence["path"]) == evidence["sha256"]
        lines = gzip.decompress(Path(evidence["path"]).read_bytes()).decode().splitlines()
        assert all(not line.strip() or line.lstrip().startswith(";") for line in lines)
        raw = "\n".join(line[len("; DISABLED| "):] if line.startswith("; DISABLED| ") else line
                         for line in lines[1:])+"\n"
        assert hashlib.sha256(raw.encode()).hexdigest() == evidence["raw_text_sha256"]
        assert not Path(engine["raw_temporary_path"]).exists()
        assert np.allclose(np.asarray(engine["gcode_to_source_transform"]) @
                           np.asarray(engine["source_to_gcode_transform"]), np.eye(4),atol=1e-10)
        deposition = row["deposition"]
        part = deposition["properties"]["model"]
        assert np.array_equal(row["com_mm"],part["com_mm"])
        assert np.array_equal(row["inertia_kg_m2"],part["inertia_line_about_com_kg_m2"])
        assert row["mass_kg"] == part["mass_kg"]
        model_feature_mass = sum(f["mass_g"] for f in deposition["features"].values() if f["category"] == "model")
        assert math.isclose(row["mass_kg"]*1000,model_feature_mass,rel_tol=1e-10,abs_tol=1e-10)
        tensor = np.asarray(row["inertia_kg_m2"])
        eigen = np.linalg.eigvalsh(tensor)
        assert np.allclose(tensor,tensor.T,atol=1e-12)
        assert eigen.min() >= -1e-12
        assert eigen[0]+eigen[1] >= eigen[2]-1e-12
        assert row["extrusion_accounting_relative_difference"] <= row["extrusion_accounting_tolerance"]
        assert deposition["unclassified_deposition_is_zero"]
        assert engine["motion_inside_build_envelope"]
        checked += 1
    piece_count=sum(p["quantity"] for p in data["parts"])
    assert piece_count == sum(p["quantity"] for p in manifest["print_parts"])
    for name,expected_hash in data["source_script_hashes"].items():
        assert sha(HERE/name) == expected_hash
    previous = data["preserved_r4_properties"]
    assert sha(previous["path"]) == previous["sha256"]
    rebind=None
    if data.get("rebind"):
        bound=data["rebind"]
        assert sha(bound["previous_aggregate_path"])==bound["previous_aggregate_hash"]
        earlier=json.loads(Path(bound["previous_aggregate_path"]).read_text())
        by_sku={row["sku"]:row for row in earlier["parts"]}
        retained=[row for row in data["parts"] if row["sku"] not in bound["changed_skus"]]
        assert all(row==by_sku[row["sku"]] for row in retained)
        rebind=dict(previous_aggregate_hash_matches=True,unchanged_records_equal=True,
                    retained_record_count=len(retained),resliced_skus=bound["changed_skus"])
    receipt = dict(status="pass",production_case_count=checked,printed_piece_count=piece_count,
        production_manifest_sha256=sha(path),source_manifest_sha256=data["source_manifest_hash"],
        all_current_source_stl_hashes_match=True,all_profile_and_snapshot_hashes_match=True,
        all_compressed_evidence_hashes_match=True,all_compressed_commands_disabled=True,
        all_restored_raw_text_hashes_match=True,all_inverse_transforms_match=True,
        all_part_properties_exclude_support_and_adhesion=True,
        all_inertia_tensors_symmetric_psd_and_triangle_inequality=True,
        all_motion_bounds_fit=True,all_extrusion_accounting_within_rounded_volume_tolerance=True,
        all_script_hashes_match=True,preserved_r4_aggregate_unchanged=True,
        no_raw_gcode_remains=not bool(list(out.rglob("*.temporary.gcode"))),rebind=rebind)
    (out/"validation.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    run()
