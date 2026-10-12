"""Render a watermarked draft; this does not create printable CAD or meshes."""
from pathlib import Path
import sys
sys.dont_write_bytecode = True
import build_bed as build
from probe_unconfirmed import PROVISIONAL


def run():
    import cadquery as cq
    import trimesh
    recipe, _ = build.make_recipe(PROVISIONAL)
    meshes = {}
    for i, data in enumerate(recipe["parts"]):
        if i == 5:
            body = build.build_shape(cq, data)
            v, f = body.tessellate(.03, .08)
            mesh = trimesh.Trimesh([p.toTuple() for p in v], f, process=True)
        else:
            mesh = trimesh.load_mesh(build.OUT.parent / "bed1" / (data["name"]+".stl"), process=True)
        meshes[data["name"]] = mesh
    build.preview(meshes, recipe, watermark="UNCONFIRMED LAYOUT")
    print("Watermarked draft views written; no print exports", flush=True)


if __name__ == "__main__":
    run()
