"""Straight R5 lower leg with a removable opposite-side bearing cheek.

The tibia link axis runs from the knee at (0, 0, 0) to the unchanged toe
centre at (105, 0, 0). The second part closes the short shaft-support fork;
it is not a second serial segment in the lower leg.
"""

import math

from geom import cylinder, prism_xz, fuse, cut, volume, valid


BRIDGE_BOUNDS_XZ = ((32.0, -7.0), (48.0, 7.0))
BRIDGE_BOLT_XZ = ((36.0, 0.0), (44.0, 0.0))


def build_tibia_parts(leg):
    """Return the four tibia-owned records, using the canonical leg helpers."""
    # The local lower shoulder clears the neighboring femur cheek during
    # knee flexion. The load-bearing shank beyond the fork remains straight.
    profile = [(0, 14), (18, 14), (48, 11.5), (51, 9),
               (51, -9), (48, -11.5), (32, -11.5), (18, -7), (0, -14)]
    main = leg._cheek(profile, 19)
    auxiliary = leg._cheek(profile, -27, 5)
    top = [(18, 14), (48, 11.5)]
    bottom = [(18, -7), (32, -11.5), (48, -11.5)]
    for y0 in (15,):
        ribs = fuse(leg._edge_rib(top, -1, y0),
                    leg._edge_rib(bottom, 1, y0))
        ribs = cut(ribs, cylinder(38, 2.7, (0, 15, 0), (0, 1, 0)))
        main = fuse(main, ribs)

    bridge = prism_xz([(32, -5.5), (33.5, -7), (46.5, -7), (48, -5.5),
                       (48, 5.5), (46.5, 7), (33.5, 7), (32, 5.5)], -22, 45)
    # The straight symmetric taper carries force along the knee-to-toe axis.
    # A 14 mm transverse thickness avoids a thin flat blade under side load.
    shank = fuse(prism_xz([(40, 11.5), (51, 11.5), (105, 5),
                           (105, -5), (51, -11.5), (40, -11.5)], -7, 14),
                 cylinder(5, 14, (105, -7, 0), (0, 1, 0)))
    angle = math.radians(leg.CONSTANTS['toe_nominal_total_pitch_deg'])
    normal = (math.sin(angle), -math.cos(angle))
    tangent = (math.cos(angle), math.sin(angle))
    p = (105 + 4.8 * normal[0], 4.8 * normal[1])
    outside = [(p[0] + u*tangent[0] + v*normal[0],
                p[1] + u*tangent[1] + v*normal[1])
               for u, v in ((100, 0), (-100, 0), (-100, 100), (100, 100))]
    shank = cut(shank, prism_xz(outside, -9, 18),
                leg._b(98, 102, -9, 9, -0.5, 2.5))
    main = fuse(main, bridge, shank)
    for x, z in BRIDGE_BOLT_XZ:
        main = cut(main, leg._hole_y(x, z, -30, 60))
        auxiliary = cut(auxiliary, leg._hole_y(x, z, -30, 60))
        import fastener_revision as fr
        main = fr.bridge_nut(main,x,z,11.5,leg._b)
    auxiliary = leg._aux_standoff_lands(auxiliary)

    assert valid(main) and valid(auxiliary)
    assert min(volume(main), volume(auxiliary)) > 0
    return [
        leg._part('tibia_curved_main_and_foot', main, 'tibia',
                  display_name='Straight tibia main and foot'),
        leg._part('tibia_auxiliary_cheek', auxiliary, 'tibia',
                  display_name='Short tibia auxiliary bearing cheek'),
        leg._part('horn_knee_main', leg._pitch(leg.main_horn(), True),
                  'tibia', 'metal', False),
        leg._part('horn_knee_auxiliary', leg._pitch(leg.auxiliary_disc(), True),
                  'tibia', 'metal', False),
    ]


def replace_tibia_parts(parts, leg):
    return [part for part in parts if part['link'] != 'tibia'] + build_tibia_parts(leg)
