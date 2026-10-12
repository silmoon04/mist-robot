"""Independent OCP and triangle checks for three cropped production coupons."""
from pathlib import Path
import math
import struct
import sys
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'cad'))
from leg import build_coupons
from geom import bounds, valid, volume, export_stl, transform, translate
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID

NAMES = {
    'coupon_femur_bridge_load_main',
    'coupon_femur_bridge_load_aux',
    'coupon_coxa_staggered_nut_post',
}


def mesh_checks(path):
    data = path.read_bytes()
    triangle_count = struct.unpack_from('<I', data, 80)[0]
    if len(data) != 84 + triangle_count * 50:
        raise RuntimeError('Unexpected binary STL length')
    vertex_map = {}
    edges = defaultdict(list)
    signed_volume = 0.0
    degenerate = 0
    for index in range(triangle_count):
        values = struct.unpack_from('<12fH', data, 84 + 50*index)
        points = [tuple(values[start:start+3]) for start in (3, 6, 9)]
        ids = []
        for point in points:
            key = tuple(round(v, 5) for v in point)
            if key not in vertex_map:
                vertex_map[key] = len(vertex_map)
            ids.append(vertex_map[key])
        if len(set(ids)) != 3:
            degenerate += 1
        a, b, c = points
        signed_volume += (a[0]*(b[1]*c[2]-b[2]*c[1])
                         + a[1]*(b[2]*c[0]-b[0]*c[2])
                         + a[2]*(b[0]*c[1]-b[1]*c[0]))/6
        for u, v in zip(ids, ids[1:]+ids[:1]):
            edges[tuple(sorted((u, v)))].append((index, 1 if u < v else -1))
    boundary_edges = sum(len(uses) == 1 for uses in edges.values())
    nonmanifold_edges = sum(len(uses) > 2 for uses in edges.values())
    bad_winding_edges = sum(len(uses) == 2 and uses[0][1] == uses[1][1]
                            for uses in edges.values())
    parents = list(range(triangle_count))
    def find(a):
        while parents[a] != a:
            parents[a] = parents[parents[a]]
            a = parents[a]
        return a
    for uses in edges.values():
        for other in uses[1:]:
            parents[find(other[0])] = find(uses[0][0])
    shells = len({find(i) for i in range(triangle_count)})
    return {
        'triangles': triangle_count,
        'vertices': len(vertex_map),
        'boundary_edges': boundary_edges,
        'nonmanifold_edges': nonmanifold_edges,
        'bad_winding_edges': bad_winding_edges,
        'degenerate_triangles': degenerate,
        'watertight': boundary_edges == 0 and nonmanifold_edges == 0,
        'consistent_winding': bad_winding_edges == 0,
        'triangle_shells': shells,
        'signed_volume_mm3': signed_volume,
    }


for part in build_coupons():
    if part['name'] not in NAMES:
        continue
    shape = part['shape']
    solid_iterator = TopExp_Explorer(shape, TopAbs_SOLID)
    solids = 0
    while solid_iterator.More():
        solids += 1
        solid_iterator.Next()
    lower, upper = bounds(shape)
    print_shape = transform(shape, rpy_deg=part['print_rotation'])
    p0, p1 = bounds(print_shape)
    print_shape = translate(print_shape, (0, 0, -p0[2]))
    path = Path(__file__).parent / (part['name'] + '.stl')
    export_stl(print_shape, path)
    checks = mesh_checks(path)
    exact_volume = volume(shape)
    print(part['name'], flush=True)
    print('OCP valid:', valid(shape), 'solids:', solids, flush=True)
    print('CAD bounds mm:', lower, upper, flush=True)
    print('Print bounds mm:', bounds(print_shape), flush=True)
    print('Print extents mm:', tuple(round(p1[i]-p0[i],6) for i in range(3)), flush=True)
    print('Exact volume mm3:', exact_volume, flush=True)
    print('Mesh checks:', checks, flush=True)
    print('Mesh relative volume error:', abs(checks['signed_volume_mm3']-exact_volume)/exact_volume, flush=True)
