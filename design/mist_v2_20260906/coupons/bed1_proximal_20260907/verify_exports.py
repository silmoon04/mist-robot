"""Verify delivered meshes and 3MF independently, without importing CadQuery."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

sys.dont_write_bytecode = True
import numpy as np
import trimesh
from mesh_checks import inspect_mesh_shells

OUT = Path(__file__).resolve().parent


def run():
    saved = json.loads((OUT / "validation.json").read_text())
    for name, digest in saved["protected_original_sha256"].items():
        assert hashlib.sha256((OUT.parent / name).read_bytes()).hexdigest() == digest, name
    items = []
    for record in saved["checks"]:
        name = record["part"]
        mesh = trimesh.load_mesh(OUT / (name+".stl"), process=True)
        assert mesh.is_watertight and mesh.is_winding_consistent
        shell_checks = inspect_mesh_shells(mesh)
        assert mesh.volume > 0
        assert np.max(np.abs(mesh.bounds - record["bounds_mm"])) < 1e-6
        items.append(dict(part=name, watertight=True, winding_consistent=True,
                          mesh_shell_checks=shell_checks, triangles=len(mesh.faces)))
        if name.startswith("06_"):
            pads = []
            for x, y in [(73.5, 213), (213, 213), (213, 73.5)]:
                v = mesh.vertices
                select = v[(np.abs(v[:, 0]-x) <= 2.5001) &
                           (np.abs(v[:, 1]-y) <= 2.5001) & (v[:, 2] > 3.01)]
                assert len(select)
                bounds = np.array([select.min(axis=0), select.max(axis=0)])
                assert np.allclose(bounds[:, :2], [[x-2.5, y-2.5], [x+2.5, y+2.5]])
                assert abs(bounds[1, 2]-6) < 1e-6
                pads.append(dict(center_xy_mm=[x, y], raised_mesh_bounds_mm=bounds.tolist()))
    stem = "MIST_BED1_PROXIMAL_ALL_PARTS"
    combined = trimesh.load_mesh(OUT / (stem+".stl"), process=True)
    assert combined.is_watertight and combined.is_winding_consistent
    combined_shells = combined.split()
    assert sum(s.volume > 1e-6 for s in combined_shells) == 7
    assert np.all(combined.extents[:2] <= 216.00001)
    assert combined.bounds[0, 2] >= -1e-6
    with zipfile.ZipFile(OUT / (stem+".3mf")) as archive:
        xml = ET.fromstring(archive.read("3D/3dmodel.model"))
        assert xml.attrib["unit"] == "millimeter"
        objects = xml.findall(".//{*}object")
        assert len(objects) == 7
        assert len(xml.findall(".//{*}item")) == 7
        for obj in objects:
            v = np.array([[float(n.attrib[k]) for k in ["x", "y", "z"]]
                          for n in obj.findall(".//{*}vertex")])
            f = np.array([[int(n.attrib[k]) for k in ["v1", "v2", "v3"]]
                          for n in obj.findall(".//{*}triangle")])
            m = trimesh.Trimesh(v, f, process=True)
            assert m.is_watertight and m.is_winding_consistent
            inspect_mesh_shells(m)
    result = dict(status="independent_mesh_3mf_checks_passed", cadquery_imported=False,
        part_count=7, combined_positive_material_shells=7,
        combined_surface_shells=len(combined_shells), checks=items,
        raised_datum_pads=pads, long_datum_center_distance_xy_mm=[139.5, 139.5],
        long_datum_outer_face_mm=144.5, long_datum_inner_face_mm=134.5,
        extent_mm=combined.extents.tolist(), units_3mf="millimeter",
        original_files_unchanged=True)
    (OUT / "independent_mesh_validation.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    run()
