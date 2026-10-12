"""Inspect material shells and verify enclosed voids without an R-tree library."""
import numpy as np


def winding_number(triangles, point):
    a, b, c = (triangles[:, i] - point for i in range(3))
    la, lb, lc = (np.linalg.norm(v, axis=1) for v in (a, b, c))
    numerator = np.einsum("ij,ij->i", a, np.cross(b, c))
    denominator = (la*lb*lc + np.einsum("ij,ij->i", a, b)*lc +
                   np.einsum("ij,ij->i", b, c)*la + np.einsum("ij,ij->i", c, a)*lb)
    return np.arctan2(numerator, denominator).sum() / (2*np.pi)


def inspect_mesh_shells(mesh):
    assert mesh.is_watertight and mesh.is_winding_consistent
    shells = mesh.split()
    positive = [s for s in shells if s.volume > 1e-6]
    negative = [s for s in shells if s.volume < -1e-6]
    assert len(positive) == 1, "Expected one connected material shell"
    assert len(positive)+len(negative) == len(shells), "Zero-volume shell"
    outer = positive[0]
    voids = []
    for inner in negative:
        points = np.concatenate([inner.vertices, inner.triangles_center])
        winding = np.array([winding_number(outer.triangles, p) for p in points])
        assert np.allclose(np.abs(winding), 1, atol=1e-5), "Void shell is not enclosed"
        voids.append(dict(signed_volume_mm3=float(inner.volume),
            bounds_mm=inner.bounds.tolist(), containment_sample_count=len(points),
            absolute_winding_min=float(np.min(np.abs(winding))),
            absolute_winding_max=float(np.max(np.abs(winding))),
            containment="All vertices and triangle centroids lie inside the positive shell"))
    return dict(positive_material_shells=1, surface_shells=len(shells),
                enclosed_void_shells=len(negative), void_shell_checks=voids)
