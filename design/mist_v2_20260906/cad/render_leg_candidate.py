"""Render existing candidate GLB triangles as orthographic engineering previews."""

import argparse
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np
import trimesh


def mesh_data(path):
    scene = trimesh.load(path, force="scene")
    items = []
    for node in scene.graph.nodes_geometry:
        transform, geometry = scene.graph[node]
        mesh = scene.geometry[geometry].copy()
        mesh.apply_transform(transform)
        triangles = mesh.vertices[mesh.faces] * 1000.0
        colors = mesh.visual.face_colors[:, :3] / 255.0
        items.append((node, triangles, mesh.face_normals, colors))
    return items


def panel(ax, items, azimuth, elevation, title):
    az, el = np.deg2rad([azimuth, elevation])
    toward_camera = np.array([np.cos(el)*np.cos(az), np.cos(el)*np.sin(az), np.sin(el)])
    right = np.array([-np.sin(az), np.cos(az), 0.0])
    up = np.cross(toward_camera, right)
    projection = np.column_stack((right, up, toward_camera))
    triangles = np.concatenate([item[1] for item in items])
    normals = np.concatenate([item[2] for item in items])
    colors = np.concatenate([item[3] for item in items])
    visible = normals @ toward_camera > 1e-9
    triangles, normals, colors = triangles[visible], normals[visible], colors[visible]
    light = toward_camera + up * 0.8 - right * 0.4
    light /= np.linalg.norm(light)
    shade = 0.48 + 0.52 * np.clip(normals @ light, 0, 1)
    colors = np.clip(colors * shade[:, None], 0, 1)
    projected = triangles @ projection
    depth_order = np.argsort(projected[:, :, 2].mean(axis=1))
    faces = PolyCollection(projected[depth_order, :, :2],
                           facecolors=colors[depth_order], edgecolors="none",
                           linewidth=0, antialiased=False, rasterized=True)
    ax.add_collection(faces)
    low = projected[:, :, :2].min(axis=(0, 1))
    high = projected[:, :, :2].max(axis=(0, 1))
    span = high-low
    margin = max(span)*0.08
    ax.set_xlim(low[0]-margin, high[0]+margin)
    ax.set_ylim(low[1]-margin, high[1]+margin)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, loc="left", fontsize=12, pad=12, color="#25303a")
    scale = 20 if max(span) < 190 else 50
    x, y = low[0], low[1]-margin*0.45
    ax.plot([x, x+scale], [y, y], color="#25303a", linewidth=2)
    ax.text(x+scale/2, y+margin*0.15, f"{scale} mm", ha="center", va="bottom",
            fontsize=9, color="#25303a")


def render(path, output, label, whole_robot=False):
    items = mesh_data(path)
    modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")
    footer = (f"Source: {path.name} | {modified} | {len(items)} components\n"
              "Existing CAD mesh, orthographic projection. Hidden contacts and tolerances require solid-model checks.")
    bg = "#f6f5f0"
    if whole_robot:
        fig, axes = plt.subplots(1, 2, figsize=(16, 10), facecolor=bg)
        for ax, view in zip(axes, [(35, 15, "Whole robot / front oblique"),
                                   (135, 20, "Whole robot / opposite oblique")]):
            ax.set_facecolor(bg)
            panel(ax, items, *view)
        fig.suptitle(f"MIST whole robot | {label}", x=0.04, ha="left", fontsize=18, color="#25303a")
        fig.text(0.04, 0.02, footer, fontsize=9, color="#4d5b65", linespacing=1.7)
        fig.subplots_adjust(left=0.03, right=0.98, bottom=0.09, top=0.90, wspace=0.1)
        fig.savefig(output / "whole_robot_view.png", dpi=160, facecolor=bg)
        plt.close(fig)
        print(f"Rendered {len(items)} components; {sum(len(item[1]) for item in items)} triangles")
        print(output / "whole_robot_view.png")
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 9), facecolor=bg)
    for ax in axes:
        ax.set_facecolor(bg)
    panel(axes[0], items, 135, 8, "Leg / side")
    panel(axes[1], items, 90, 20, "Leg / oblique")
    fig.suptitle(f"MIST FL leg | {label}", x=0.045, ha="left", fontsize=18, color="#25303a")
    fig.text(0.045, 0.02, footer, fontsize=9, color="#4d5b65", linespacing=1.7)
    fig.subplots_adjust(left=0.04, right=0.98, bottom=0.10, top=0.90, wspace=0.12)
    fig.savefig(output / "leg_view.png", dpi=160, facecolor=bg)
    plt.close(fig)

    hip = [item for item in items if item[0].split("__")[-1][0] in "YPHKS"]
    fig, axes = plt.subplots(1, 3, figsize=(18, 7), facecolor=bg)
    for ax in axes:
        ax.set_facecolor(bg)
    for ax, view in zip(axes, [(135, 18, "Hip / output side"),
                               (-45, 18, "Hip / opposite side"),
                               (45, 90, "Hip / above")]):
        panel(ax, hip, *view)
    fig.suptitle(f"MIST FL hip module | {label}", x=0.035, ha="left", fontsize=18, color="#25303a")
    fig.text(0.035, 0.02, footer + "\nHip view includes Y/P/H/K/S components; femur, tibia and wheel are hidden.",
             fontsize=9, color="#4d5b65", linespacing=1.6)
    fig.subplots_adjust(left=0.03, right=0.98, bottom=0.16, top=0.88, wspace=0.12)
    fig.savefig(output / "hip_view.png", dpi=160, facecolor=bg)
    plt.close(fig)
    print(f"Rendered {len(items)} components; {sum(len(item[1]) for item in items)} triangles")
    print(output / "leg_view.png")
    print(output / "hip_view.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path,
                        default=Path(__file__).parent / "leg_output" / "MIST_leg_FL_candidate.glb")
    parser.add_argument("--label", default="engineering candidate")
    parser.add_argument("--whole-robot", action="store_true")
    args = parser.parse_args()
    render(args.input, args.input.parent, args.label, args.whole_robot)
