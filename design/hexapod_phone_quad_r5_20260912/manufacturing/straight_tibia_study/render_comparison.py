from pathlib import Path
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
OLD = ROOT.parent / 'hexapod_phone_quad_20260912/cad/output/parts_mesh'

fig, axes = plt.subplots(2, 1, figsize=(11.5, 7.2), layout='constrained')
fig.patch.set_facecolor('#f7f8f8')
fig.suptitle('A straight lower leg, with the same joint positions', fontsize=19,
             fontweight='bold', color='#17262d')

for ax, prefix, directory, color, title in [
    (axes[0], 'FL_', OLD, '#71828b', 'R4: curved main body and foot'),
    (axes[1], '', OUT, '#188a91', 'R5: continuous straight tapered shank'),
]:
    mesh = trimesh.load_mesh(directory / (prefix + 'tibia_curved_main_and_foot.stl'))
    triangles = mesh.triangles[:, :, [0, 2]]
    twice_area = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    triangles = triangles[np.abs(twice_area) > 1e-5]
    ax.add_collection(PolyCollection(triangles, facecolors=color, edgecolors='none', antialiased=False))
    ax.plot([0, 105], [0, 0], color='#b64336', linewidth=1.2, linestyle=(0, (4, 4)), zorder=4)
    ax.scatter([0, 105], [0, 0], s=38, facecolors='white', edgecolors='#b64336', linewidths=1.3, zorder=5)
    ax.text(0, -20, 'Knee', ha='center', fontsize=10, color='#263942')
    ax.text(105, -20, 'Toe', ha='center', fontsize=10, color='#263942')
    ax.annotate('', xy=(0, -25), xytext=(105, -25),
                arrowprops=dict(arrowstyle='|-|', color='#455962', linewidth=.9))
    ax.text(52.5, -24.5, '105 mm', ha='center', va='bottom', fontsize=10,
            bbox=dict(facecolor='#f7f8f8', edgecolor='none', pad=2), color='#263942')
    ax.set_title(title, loc='left', fontsize=13, color='#17262d', pad=10)
    ax.set_aspect('equal')
    ax.set_xlim(-19, 117)
    ax.set_ylim(-29, 33)
    ax.set_axis_off()

fig.supxlabel('Side silhouettes from the actual CAD meshes. The separate short auxiliary cheek supports the opposite shaft.',
               fontsize=9, color='#455962')
fig.savefig(OUT / 'straight_tibia_comparison.png', dpi=170, facecolor=fig.get_facecolor())
print(OUT / 'straight_tibia_comparison.png')
