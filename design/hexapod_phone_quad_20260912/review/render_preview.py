"""Render the current CAD part meshes in their manifest assembly pose."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.colors import to_rgb
from matplotlib.patches import Patch
from numba import njit


HERE = Path(__file__).resolve().parent
DEFAULT_MANIFEST = HERE.parent / "cad" / "output" / "assembly_manifest.json"
DEFAULT_MASS_MANIFEST = HERE.parent / "cad" / "output" / "assembly_manifest_as_printed.json"
DEFAULT_PRODUCTION_PROPERTIES = (
    HERE.parent / "manufacturing" / "slicing_r4" / "output" / "production_mass_properties.json"
)
BACKGROUND = "#f3f4f0"
INK = "#202c30"
MUTED = "#536268"
TEAL = "#508f88"
GRAPHITE = "#39454b"
PALETTE = {
    "servo": "#303940",
    "metal": "#acb8bc",
    "phone": "#12262e",
    "battery": "#607773",
    "electronics": "#426c63",
    "allowance": "#798486",
}


@dataclass
class Assembly:
    triangles: np.ndarray
    normals: np.ndarray
    colors: np.ndarray
    bounds: np.ndarray
    manifest: dict
    manifest_digest: str
    part_count: int
    mass_manifest: dict
    mass_manifest_digest: str
    production_properties_digest: str


def part_color(part: dict) -> tuple[float, float, float]:
    if part["material"] != "pla":
        return to_rgb(PALETTE.get(part["material"], "#7b898d"))
    name = part["name"].lower()
    if name.startswith(("fl_", "fr_", "rl_", "rr_")):
        return to_rgb(TEAL)
    if "cradle" in name or "phone_pan_hub" in name:
        return to_rgb(TEAL)
    return to_rgb(GRAPHITE)


def validate_mass_reference(geometry: dict, geometry_digest: str, mass: dict, production_digest: str):
    model = mass.get("mass_model", {})
    if model.get("source_solid_manifest_sha256") != geometry_digest:
        raise ValueError("The sliced mass manifest belongs to different CAD geometry.")
    if mass.get("units") != geometry.get("units") or mass.get("revision") != geometry.get("revision"):
        raise ValueError("The sliced mass manifest units or revision do not match the geometry.")
    if model.get("as_sliced") is not True:
        raise ValueError("The mass manifest does not identify a sliced deposition estimate.")
    if model.get("source_production_properties_sha256") != production_digest:
        raise ValueError("The sliced mass manifest does not match the production mass properties.")
    if not np.isfinite(mass.get("total_mass_kg", np.nan)) or mass["total_mass_kg"] <= 0:
        raise ValueError("The sliced assembled mass must be a positive finite value.")


def load_assembly(
    manifest_path: Path,
    mass_manifest_path: Path = DEFAULT_MASS_MANIFEST,
    production_properties_path: Path = DEFAULT_PRODUCTION_PROPERTIES,
) -> Assembly:
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    if manifest.get("units") != "mm":
        raise ValueError("The renderer requires a manifest in millimetres.")
    digest = hashlib.sha256(raw).hexdigest()
    mass_raw = mass_manifest_path.read_bytes()
    mass_manifest = json.loads(mass_raw)
    production_digest = hashlib.sha256(production_properties_path.read_bytes()).hexdigest()
    validate_mass_reference(manifest, digest, mass_manifest, production_digest)
    triangles, normals, colors = [], [], []
    count = 0
    for part in manifest["parts"]:
        if part.get("allowance_only"):
            continue
        if not part.get("stl"):
            raise ValueError(
                f"Part {part['name']} has no STL path. Rebuild the CAD exports first."
            )
        path = manifest_path.parent / part["stl"]
        mesh = trimesh.load_mesh(path, force="mesh", process=False)
        if not isinstance(mesh, trimesh.Trimesh) or not len(mesh.faces):
            raise ValueError(f"Empty or unsupported mesh: {path}")
        transform = np.asarray(
            manifest["links"][part["link"]]["assembly_transform"], dtype=float
        )
        if transform.shape != (4, 4) or not np.isfinite(transform).all():
            raise ValueError(f"Invalid assembly transform for {part['link']}")
        mesh.apply_transform(transform)
        triangles.append(mesh.triangles)
        normals.append(mesh.face_normals)
        colors.append(np.tile(part_color(part), (len(mesh.faces), 1)))
        count += 1
    if not triangles:
        raise ValueError("The manifest contains no visible part meshes.")
    vertices = np.concatenate(triangles)
    bounds = np.array([vertices.min(axis=(0, 1)), vertices.max(axis=(0, 1))])
    if not np.isfinite(bounds).all():
        raise ValueError("The transformed mesh bounds are not finite.")
    return Assembly(
        vertices,
        np.concatenate(normals),
        np.concatenate(colors),
        bounds,
        manifest,
        digest,
        count,
        mass_manifest,
        hashlib.sha256(mass_raw).hexdigest(),
        production_digest,
    )


def camera_basis(elevation: float, azimuth: float) -> np.ndarray:
    elevation, azimuth = np.radians([elevation, azimuth])
    toward_camera = np.array(
        [
            np.cos(elevation) * np.cos(azimuth),
            np.cos(elevation) * np.sin(azimuth),
            np.sin(elevation),
        ]
    )
    right = np.cross([0.0, 0.0, 1.0], toward_camera)
    right /= np.linalg.norm(right)
    up = np.cross(toward_camera, right)
    return np.column_stack([right, up, toward_camera])


@njit(cache=True)
def rasterize(triangles, colors, width, height):
    depth = np.full((height, width), -np.inf)
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    for index in range(len(triangles)):
        triangle = triangles[index]
        x0, y0, z0 = triangle[0]
        x1, y1, z1 = triangle[1]
        x2, y2, z2 = triangle[2]
        denominator = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(denominator) < 1e-12:
            continue
        left = max(0, int(np.floor(min(x0, x1, x2))))
        right = min(width - 1, int(np.ceil(max(x0, x1, x2))))
        bottom = max(0, int(np.floor(min(y0, y1, y2))))
        top = min(height - 1, int(np.ceil(max(y0, y1, y2))))
        for y in range(bottom, top + 1):
            for x in range(left, right + 1):
                a = ((y1 - y2) * (x + 0.5 - x2) + (x2 - x1) * (y + 0.5 - y2)) / denominator
                b = ((y2 - y0) * (x + 0.5 - x2) + (x0 - x2) * (y + 0.5 - y2)) / denominator
                c = 1.0 - a - b
                if a < -1e-8 or b < -1e-8 or c < -1e-8:
                    continue
                z = a * z0 + b * z1 + c * z2
                if z > depth[y, x]:
                    depth[y, x] = z
                    rgba[y, x, 0] = int(colors[index, 0] * 255)
                    rgba[y, x, 1] = int(colors[index, 1] * 255)
                    rgba[y, x, 2] = int(colors[index, 2] * 255)
                    rgba[y, x, 3] = 255
    return rgba


def draw_mesh(ax, assembly: Assembly, basis: np.ndarray) -> np.ndarray:
    projected = assembly.triangles @ basis
    facing = assembly.normals @ basis[:, 2] > 1e-8
    projected = projected[facing]
    normals = assembly.normals[facing]
    colors = assembly.colors[facing]
    key = np.array([0.5, -0.4, 0.78])
    key /= np.linalg.norm(key)
    fill = np.array([-0.5, 0.7, 0.45])
    fill /= np.linalg.norm(fill)
    light = (
        0.53
        + 0.40 * np.maximum(normals @ key, 0)
        + 0.16 * np.maximum(normals @ fill, 0)
    )
    face_colors = np.clip(colors * light[:, None], 0, 1)
    pmin = projected[:, :, :2].min(axis=(0, 1)) - 0.25
    pmax = projected[:, :, :2].max(axis=(0, 1)) + 0.25
    size = pmax - pmin
    width, height = np.ceil(size / size.max() * 2400).astype(int)
    pixel_triangles = projected.copy()
    pixel_triangles[:, :, :2] = (pixel_triangles[:, :, :2] - pmin) / size * [width, height]
    pixels = rasterize(pixel_triangles, face_colors, width, height)
    ax.imshow(
        pixels,
        extent=[pmin[0], pmax[0], pmin[1], pmax[1]],
        origin="lower",
        interpolation="antialiased",
        zorder=1,
    )
    return projected[:, :, :2]


def dimension(ax, start, end, label: str, offset=(0, 0), vertical=False):
    start, end = np.array(start, float), np.array(end, float)
    offset = np.asarray(offset)
    a, b = start + offset, end + offset
    for point, extended in ((start, a), (end, b)):
        ax.plot(*np.vstack([point, extended]).T, color="#a1aaa8", lw=0.7)
    ax.annotate(
        "",
        xy=a,
        xytext=b,
        arrowprops=dict(arrowstyle="|-|", lw=0.9, color=MUTED, shrinkA=0, shrinkB=0),
    )
    center = (a + b) / 2
    ax.text(
        center[0] + (6 if vertical else 0),
        center[1] + (0 if vertical else -7),
        label,
        color=MUTED,
        fontsize=11,
        ha="left" if vertical else "center",
        va="center" if vertical else "top",
        rotation=90 if vertical else 0,
        bbox=dict(facecolor=BACKGROUND, edgecolor="none", pad=3),
    )


def render(assembly: Assembly, destination: Path, view: str, dpi: int):
    side = view == "side"
    basis = camera_basis(0, -90) if side else camera_basis(23, -25)
    fig = plt.figure(figsize=(12, 10), facecolor=BACKGROUND)
    ax = fig.add_axes([0.055, 0.19, 0.89, 0.69], facecolor=BACKGROUND)
    projected = draw_mesh(ax, assembly, basis)
    pmin, pmax = projected.min(axis=(0, 1)), projected.max(axis=(0, 1))
    span = pmax - pmin
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_xlim(pmin[0] - span[0] * 0.055, pmax[0] + span[0] * (0.15 if side else 0.055))
    ax.set_ylim(pmin[1] - span[1] * 0.12, pmax[1] + span[1] * 0.035)
    dims = np.diff(assembly.bounds, axis=0)[0]
    if side:
        x0, _, z0 = assembly.bounds[0]
        x1, _, z1 = assembly.bounds[1]
        dimension(ax, [x0, z0], [x1, z0], f"X span {dims[0]:.1f} mm", offset=[0, -22])
        dimension(
            ax,
            [x1, z0],
            [x1, z1],
            f"Z height {dims[2]:.1f} mm",
            offset=[25, 0],
            vertical=True,
        )
        subtitle = "Orthographic side view  |  Current neutral joint pose"
    else:
        anchor = np.array([pmin[0] + 13, pmin[1] - 17])
        for axis, color, vector in zip(
            "XYZ", ["#976957", "#63866b", "#5d7e94"], np.eye(3), strict=True
        ):
            tip = anchor + (vector @ basis)[:2] * 25
            ax.annotate(
                "",
                xy=tip,
                xytext=anchor,
                arrowprops=dict(arrowstyle="->", color=color, lw=1.0),
            )
            ax.text(*tip, axis, fontsize=8, color=color, ha="center", va="bottom")
        subtitle = "Orthographic assembly view  |  Four legs, 13 servos, landscape phone pan"
    fig.text(0.055, 0.95, "Hex quad with landscape phone", fontsize=25, color=INK, weight="bold")
    fig.text(0.055, 0.912, subtitle, fontsize=11.5, color=MUTED)
    legend = [
        Patch(facecolor=TEAL, label="Printed leg and phone parts"),
        Patch(facecolor=GRAPHITE, label="Body and servos"),
        Patch(facecolor=PALETTE["phone"], label="Bare Mi 9 SE envelope"),
    ]
    fig.legend(
        handles=legend,
        loc="lower left",
        bbox_to_anchor=(0.045, 0.131),
        ncol=3,
        frameon=False,
        fontsize=10,
        labelcolor=MUTED,
        handlelength=1.0,
        columnspacing=2.1,
    )
    fig.text(
        0.055,
        0.114,
        f"Mesh bounds: {dims[0]:.1f} X / {dims[1]:.1f} Y / {dims[2]:.1f} Z mm"
        f"     |     {assembly.part_count} visible CAD parts",
        fontsize=10,
        color=MUTED,
    )
    fig.text(
        0.055,
        0.088,
        f"Estimated assembled mass {assembly.mass_manifest['total_mass_kg']:.2f} kg"
        " (sliced model deposition)",
        fontsize=11,
        color=INK,
        weight="bold",
    )
    fig.text(
        0.055,
        0.067,
        f"Full-solid CAD reference: {assembly.manifest['total_mass_kg']:.2f} kg",
        fontsize=8.5,
        color=MUTED,
    )
    fig.text(
        0.055,
        0.045,
        "Controlled prototype. Fit and load tests next.",
        fontsize=9,
        color=MUTED,
    )
    fig.text(
        0.055,
        0.024,
        f"{assembly.manifest.get('revision', 'Unspecified revision')}"
        f"  |  Geometry SHA256 {assembly.manifest_digest[:16]}"
        f"  |  Mass SHA256 {assembly.mass_manifest_digest[:16]}",
        fontsize=8,
        color="#778380",
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        destination,
        dpi=dpi,
        facecolor=BACKGROUND,
        metadata={
            "Title": f"Hex quad CAD {view} view",
            "Description": "Projection of exported part STL meshes using manifest assembly transforms.",
            "ManifestSHA256": assembly.manifest_digest,
            "MassManifestSHA256": assembly.mass_manifest_digest,
            "ProductionMassPropertiesSHA256": assembly.production_properties_digest,
            "MassReference": (
                f"Sliced assembled estimate {assembly.mass_manifest['total_mass_kg']} kg; "
                f"full-solid CAD reference {assembly.manifest['total_mass_kg']} kg."
            ),
        },
    )
    plt.close(fig)
    print(f"Rendered {destination}: {assembly.part_count} parts, {len(assembly.triangles)} triangles")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--mass-manifest", type=Path, default=DEFAULT_MASS_MANIFEST)
    parser.add_argument("--production-properties", type=Path, default=DEFAULT_PRODUCTION_PROPERTIES)
    parser.add_argument("--output-dir", type=Path, default=HERE)
    parser.add_argument("--dpi", type=int, default=160)
    args = parser.parse_args()
    assembly = load_assembly(
        args.manifest.resolve(), args.mass_manifest.resolve(), args.production_properties.resolve()
    )
    for view in ("hero", "side"):
        render(assembly, args.output_dir / f"{view}.png", view, args.dpi)


if __name__ == "__main__":
    main()
