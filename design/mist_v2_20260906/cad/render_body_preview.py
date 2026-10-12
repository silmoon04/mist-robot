"""Render the generated solid model; no generated or edited reference artwork."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import trimesh

out = Path(__file__).parent / "output"
scene = trimesh.load(out / "MIST_body_candidate.glb", force="scene")
fig = plt.figure(figsize=(16, 10), facecolor="#f4f1e8")
views = [(221, "MIST body candidate | assembled", 16, -32, False),
         (222, "Front | inset portrait phone", 0, 0, False),
         (223, "Internal layout | shell and lid removed", 23, -34, True),
         (224, "Rear | power access", 10, 180, False)]
for subplot, title, elev, azim, cutaway in views:
    ax = fig.add_subplot(subplot, projection="3d", facecolor="#f4f1e8")
    triangles_all, colors_all = [], []
    for node in scene.graph.nodes_geometry:
        transform, geo_name = scene.graph[node]
        if cutaway and any(token in node for token in ("B06", "B07", "B08", "B09", "B10", "B11", "B12")):
            continue
        mesh = scene.geometry[geo_name].copy()
        mesh.apply_transform(transform)
        verts = mesh.vertices[mesh.faces]
        base = mesh.visual.face_colors[:, :3] / 255
        light = np.array([0.7, -0.3, 0.8])
        light /= np.linalg.norm(light)
        shade = 0.63 + 0.37 * np.maximum(0, mesh.face_normals @ light)
        colors = np.clip(base * shade[:, None], 0, 1)
        triangles_all.extend(verts)
        colors_all.extend(colors)
    poly = Poly3DCollection(np.asarray(triangles_all), facecolors=np.asarray(colors_all), edgecolors="none", linewidths=0, alpha=1)
    ax.add_collection3d(poly)
    ax.set_xlim(-115, 115)
    ax.set_ylim(-115, 115)
    ax.set_zlim(-40, 232)
    ax.set_box_aspect([230, 230, 272])
    ax.view_init(elev=elev, azim=azim)
    ax.set_proj_type("ortho")
    ax.set_axis_off()
    ax.set_title(title, fontsize=13, color="#243137", loc="left", pad=-5)
fig.text(0.04, 0.024, "180mm barrel / 260mm overall. Native feature recipe + STEP solids. Measurement and assembly gates remain open.",
         fontsize=11, color="#48545a")
fig.subplots_adjust(left=0.015, right=0.985, bottom=0.05, top=0.97, wspace=-0.09, hspace=0.02)
fig.savefig(out / "body_preview.png", dpi=150, facecolor=fig.get_facecolor())
print(out / "body_preview.png")
