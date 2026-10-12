"""Check sampled phone-pan poses against the stationary assembly geometry."""
from __future__ import annotations

import build
import geom as g


ANGLES_DEG = tuple(range(-180, 181, 30))
AABB_TOLERANCE_MM = 1e-5
INTERSECTION_THRESHOLD_MM3 = 0.01


def _aabb_overlaps(a, b):
    amin, amax = a
    bmin, bmax = b
    return all(
        amax[k] > bmin[k] + AABB_TOLERANCE_MM
        and bmax[k] > amin[k] + AABB_TOLERANCE_MM
        for k in range(3)
    )


def run_phone_samples(cfg, parts, poses) -> dict:
    """Check phone_pan against other links without changing the supplied poses.

    All other links remain at their supplied assembly poses. Internal pairs on
    phone_pan and allowance-only shapes are outside this check's scope.
    """
    physical = [p for p in parts if not p.get('allowance_only')]
    moving = [p for p in physical if p['link'] == 'phone_pan']
    stationary = [p for p in physical if p['link'] != 'phone_pan']
    if not moving or not stationary:
        raise ValueError('Phone-pan checking requires moving and stationary parts')

    fixed_shapes = [build.shape_at(p['shape'], poses[p['link']]) for p in stationary]
    fixed_bounds = [g.bounds(shape) for shape in fixed_shapes]
    samples = []
    failures = []
    boolean_pairs = 0
    for angle in ANGLES_DEG:
        pan_pose = build.pose(cfg['phone_pan_origin_mm'], [0, 0, angle])
        sample_failures = []
        sample_pairs = 0
        for moving_part in moving:
            moving_shape = build.shape_at(moving_part['shape'], pan_pose)
            moving_bounds = g.bounds(moving_shape)
            for fixed_part, fixed_shape, fixed_bbox in zip(
                stationary, fixed_shapes, fixed_bounds
            ):
                if not _aabb_overlaps(moving_bounds, fixed_bbox):
                    continue
                sample_pairs += 1
                volume = g.common_volume(moving_shape, fixed_shape)
                if volume > INTERSECTION_THRESHOLD_MM3:
                    sample_failures.append(dict(
                        angle_deg=angle,
                        a=moving_part['name'],
                        b=fixed_part['name'],
                        link_a=moving_part['link'],
                        link_b=fixed_part['link'],
                        volume_mm3=volume,
                    ))
        boolean_pairs += sample_pairs
        failures.extend(sample_failures)
        samples.append(dict(
            angle_deg=angle,
            phone_pan_pose_matrix=pan_pose.tolist(),
            candidate_boolean_pair_count=sample_pairs,
            failures=sample_failures,
        ))

    return dict(
        status='pass' if not failures else 'fail',
        scope='Sampled phone_pan intersections with all other physical links',
        angles_deg=list(ANGLES_DEG),
        sample_count=len(samples),
        moving_part_count=len(moving),
        stationary_part_count=len(stationary),
        excluded_allowance_part_count=len(parts) - len(physical),
        fixed_link_pose_matrices={
            link: matrix.tolist() for link, matrix in poses.items()
            if link != 'phone_pan'
        },
        thresholds=dict(
            aabb_tolerance_mm=AABB_TOLERANCE_MM,
            intersection_volume_mm3=INTERSECTION_THRESHOLD_MM3,
            intersection_failure_comparison='strictly greater than',
        ),
        aabb_pair_count=len(moving) * len(stationary) * len(samples),
        candidate_boolean_pair_count=boolean_pairs,
        samples=samples,
        failures=failures,
        limitations=[
            'Angles between samples are not checked.',
            'Stationary links retain the supplied poses throughout the check.',
            'Parts sharing phone_pan are not compared with each other.',
        ],
    )


if __name__ == '__main__':
    config, assembly_parts, assembly_poses, _ = build.load_assembly()
    result = run_phone_samples(config, assembly_parts, assembly_poses)
    for sample in result['samples']:
        print(
            f"pan={sample['angle_deg']:4d} deg "
            f"boolean_pairs={sample['candidate_boolean_pair_count']} "
            f"failures={len(sample['failures'])}",
            flush=True,
        )
    print(
        f"{result['status'].upper()}: {result['sample_count']} phone-pan poses, "
        f"{result['candidate_boolean_pair_count']} candidate Boolean pairs, "
        f"{len(result['failures'])} intersections above "
        f"{INTERSECTION_THRESHOLD_MM3} mm3"
    )
    for failure in result['failures']:
        print(failure)
    raise SystemExit(0 if result['status'] == 'pass' else 1)
