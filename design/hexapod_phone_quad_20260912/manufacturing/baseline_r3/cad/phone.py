"""Bare Mi 9 SE cradle and fixed STS3215 pan mount, in millimetres.

Moving parts use the pan output bearing face as their origin. Fixed parts
already use robot coordinates. Charging is permitted only while pan is parked.
"""

from __future__ import annotations

import math

import geom as g


PAN_Z = 98.0
CLAMP_BASE_Z = 66.0
MOUNT_XY = ((-39.0, -20.0), (-39.0, 20.0), (19.0, -20.0), (19.0, 20.0))
CASE_X = (-32.73, 12.5)
CASE_HALF_Y = 12.365
PHONE_WIDTH = 147.5
PHONE_THICKNESS = 7.45
PHONE_HEIGHT = 70.5
PHONE_BOTTOM = 18.0
PHONE_TOP = PHONE_BOTTOM + PHONE_HEIGHT
TOP_SEAT = PHONE_TOP + .5
TOP_FRAME = TOP_SEAT + 8
TOP_SCREW = TOP_SEAT + 3.5
PORT_CENTER_Z = PHONE_BOTTOM + PHONE_HEIGHT / 2
END_CONTACT_Y = PHONE_WIDTH / 2 - 13.75
FRAME_REAR_X = -4.5
COLUMN_REAR_X = -8.5
PORT_BACK_X = -2.5
TOP_BRIDGE_REAR_X = -12.5
HUB_BOLT_XY = ((-16.0, -24.0), (12.0, -24.0), (-16.0, 24.0), (12.0, 24.0))


def _box(x0, x1, y0, y1, z0, z1):
    return g.box(x1 - x0, y1 - y0, z1 - z0,
                 center=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))


def _hole_z(x, y, z0, z1, diameter=3.4):
    return g.cylinder(diameter / 2, z1 - z0, base=(x, y, z0))


def _hole_x(y, z, x0=-20, x1=20, diameter=3.4):
    return g.cylinder(diameter / 2, x1 - x0, base=(x0, y, z), axis=(1, 0, 0))


def _nut_z(x, y, z0, z1, across_flats=5.8):
    r = across_flats / math.sqrt(3)
    return g.prism_xy([(x + r * math.cos(math.radians(30 + a)),
                        y + r * math.sin(math.radians(30 + a)))
                       for a in range(0, 360, 60)], z0, z1 - z0)


def _nut_x(y, z, x0, x1, across_flats=5.8):
    return g.translate(g.rotate(_nut_z(0, 0, 0, x1 - x0, across_flats),
                                (0, 1, 0), 90), (x0, y, z))


def _slot_z(x, y, z0, z1):
    return g.fuse(_hole_z(x - .45, y, z0, z1),
                  _hole_z(x + .45, y, z0, z1),
                  _box(x - .45, x + .45, y - 1.7, y + 1.7, z0, z1))


def _rounded_port(y0, y1):
    """Round the back corners of the side-port opening with a 2 mm radius."""
    x0, x1, z0, z1, r = PORT_BACK_X, 13.0, PORT_CENTER_Z - 11, PORT_CENTER_Z + 11, 2.0
    pieces = [_box(x0 + r, x1 - r, y0, y1, z0, z1),
              _box(x0, x1, y0, y1, z0 + r, z1 - r)]
    for x in (x0 + r, x1 - r):
        for z in (z0 + r, z1 - r):
            pieces.append(g.cylinder(r, y1 - y0, base=(x, y0, z), axis=(0, 1, 0)))
    return g.fuse(*pieces)


def _part(name, shape, link="phone_pan", material="pla", printable=True,
          mass_kg=None, print_rotation=(0, 0, 0), note=""):
    part = {"name": name, "shape": shape, "link": link, "material": material,
            "printable": printable, "print_rotation": print_rotation}
    if mass_kg is not None:
        part["mass_kg"] = mass_kg
    if note:
        part["assembly_note"] = note
    return part


def _fixed_clamp():
    """Bottom seat, removable upper strap, and four independent body feet."""
    b = CLAMP_BASE_Z
    outer = (-36.23, 16.0, -15.865, 15.865)
    # The 2 mm floor sits below the foot plane and leaves 2 mm above the cover.
    saddle = _box(*outer, b - 2, b + 20.5)
    saddle = g.cut(saddle, _box(-33.03, 12.8, -12.665, 12.665, b, b + 22),
                   _hole_z(0, 0, b - 3, b + 1, 16),
                   _box(-42, -27, -9, 9, b - 3, b + 23),
                   _box(10.5, 20, -7, 7, b + 2, b + 17))

    for x, y in MOUNT_XY:
        connector = _box(min(x, -34), max(x, 14),
                         min(y, -13), max(y, 13), b, b + 4)
        # Remove the servo cavity from each foot connector as well.
        connector = g.cut(connector,
                          _box(-33.03, 12.8, -12.665, 12.665, b, b + 5),
                          _box(-42, -27, -9, 9, b - 1, b + 5))
        saddle = g.fuse(saddle, connector,
                        g.cylinder(5, 4, base=(x, y, b)))

    clamp_xy = ((-25, -19), (-25, 19), (5, -19), (5, 19))
    for x, y in clamp_xy:
        tower = g.fuse(g.cylinder(5, 20.5, base=(x, y, b)),
                       _box(x - 5, x + 5, min(y, -13), max(y, 13), b, b + 20.5))
        saddle = g.fuse(saddle, tower)
    saddle = g.cut(saddle, _box(-33.03, 12.8, -12.665, 12.665, b, b + 22))
    for x, y in MOUNT_XY:
        saddle = g.cut(saddle, _hole_z(x, y, b - 1, b + 5))
    for x, y in clamp_xy:
        saddle = g.cut(saddle, _hole_z(x, y, b - 1, b + 22),
                       _nut_z(x, y, 80.9, 83.6),
                       _box(x - 2.95, x + 2.95,
                            y if y > 0 else y - 6, y + 6 if y > 0 else y,
                            80.9, 83.6))

    # The upper lip overlaps case edges, clear of the output horn's radius.
    cap = _box(*outer, b + 21, PAN_Z + 3.2)
    cap = g.cut(cap,
                _box(-33.18, 12.95, -12.815, 12.815, b + 20, PAN_Z + .2),
                _box(-29, 11.2, -11.2, 11.2, PAN_Z, PAN_Z + 4.2),
                _box(-42, -27, -9, 9, b + 20, PAN_Z - 3))
    for x, y in clamp_xy:
        ear = g.fuse(g.cylinder(5, 4, base=(x, y, b + 21)),
                     _box(x - 5, x + 5, min(y, -13), max(y, 13), b + 21, b + 25))
        cap = g.fuse(cap, ear)
    cap = g.cut(cap, _box(-33.18, 12.95, -12.815, 12.815, b + 20, PAN_Z + .2))
    for x, y in clamp_xy:
        cap = g.cut(cap, _slot_z(x, y, b + 20, b + 26))
    cap = g.translate(cap, (0, 0, -.2))

    return [
        _part("phone_pan_servo_saddle", saddle, link="base",
              note="Four M3x16 screws pass through the 4 mm feet and 4 mm cover spacers into captured body nuts. Seat the servo on the lower ledges. Slide four M3 nuts inward through the outward-facing slots at Z80.9 to 83.6 before fitting the cap; a 2.9 mm roof retains them against cap screw tension. Bridge the short pocket ceilings without internal support."),
        _part("phone_pan_servo_cap", cap, link="base", print_rotation=(180, 0, 0),
              note="Four M3x10 screws secure the cap to the saddle. Upper lips contact the nominal case top before the ears close: the ears retain 0.3 mm tightening travel. Stop when the case is retained without distortion. Slots allow 0.45 mm lateral adjustment each way."),
    ]


def _hub():
    hub = g.cylinder(24, 5, base=(0, 0, 4.5))
    for x, y in HUB_BOLT_XY:
        hub = g.fuse(hub, g.cylinder(5.3, 5, base=(x, y, 4.5)))
    hub = g.cut(hub, _hole_z(0, 0, 3.5, 10.5, 6))
    for x, y in ((7, 0), (-7, 0), (0, 7), (0, -7)):
        hub = g.cut(hub, _hole_z(x, y, 3.5, 10.5),
                    _hole_z(x, y, 8.0, 10.5, 6.2))
    for x, y in HUB_BOLT_XY:
        hub = g.cut(hub, _hole_z(x, y, 3.5, 10.5),
                    _nut_z(x, y, 4.4, 7.1))
    return _part("phone_pan_hub", hub,
                 note="Seat directly on the metal horn outer face. Four M3x6 screws with 0.5 mm washers of at most 6.0 mm outer diameter sit in the 1.5 mm deep counterbores and engage 2.0 mm of the 2.5 mm metal flange. Verify this stack with the real horn. Fit the spline retaining screw before the cradle. Four M3 nuts enter the bottom pockets for the cradle feet.")


def _frame(clearance=.5, front_clearance=.55):
    inner = PHONE_WIDTH / 2 + clearance
    post_y = inner + 4
    outer = inner + 8
    front = PHONE_THICKNESS + front_clearance
    pieces = [
        _box(COLUMN_REAR_X, -.5, -outer, -inner, 13.5, TOP_FRAME),
        _box(COLUMN_REAR_X, -.5, inner, outer, 13.5, TOP_FRAME),
        _box(-4.5, -.5, -outer, outer, 14, PHONE_BOTTOM),
        # This central plate retains both L-foot bolt rows without covering end cameras.
        _box(-4.5, -.5, -44, 44, 14, 40),
        _box(-.5, front, -inner, -END_CONTACT_Y, 14, PHONE_BOTTOM),
        _box(-.5, front, END_CONTACT_Y, inner, 14, PHONE_BOTTOM),
    ]
    for sign in (-1, 1):
        a, c = sorted((sign * inner, sign * outer))
        pieces.extend([
            _box(-.5, front, a, c, PHONE_BOTTOM - .2, PHONE_BOTTOM + 25),
            _box(-.5, front, a, c, TOP_SEAT, TOP_FRAME),
        ])
        # A 45 degree transition joins the deep column to the lower rear rail.
        pieces.append(g.prism_xy([
            (COLUMN_REAR_X, sign * inner),
            (FRAME_REAR_X, sign * (inner - 4)),
            (FRAME_REAR_X, sign * (inner + .2)),
            (COLUMN_REAR_X, sign * (inner + .2)),
        ], 14, PHONE_BOTTOM - 14))
    frame = g.fuse(*pieces)
    # Both short ends admit a USB plug. Rear spines remain outside its 12 mm depth.
    for sign in (-1, 1):
        y0, y1 = sorted((sign * (PHONE_WIDTH / 2 - .1), sign * (outer + 14)))
        frame = g.cut(frame, _rounded_port(y0, y1))
    for y in (-post_y, post_y):
        for z in (25.5, TOP_SCREW):
            # Nut location and the M3x16 stack remain at the original plane.
            frame = g.cut(frame, _hole_x(y, z),
                          _hole_x(y, z, COLUMN_REAR_X - .1, FRAME_REAR_X + .05, 7.4),
                          _nut_x(y, z, -4.6, -1.8))
    for y in (-24, 24):
        for z in (24, 34):
            frame = g.cut(frame, _hole_x(y, z), _nut_x(y, z, -3.1, -.4))
    return frame


def _lower_clips(clearance=.5, front_clearance=.55):
    inner = PHONE_WIDTH / 2 + clearance
    post_y, outer = inner + 4, inner + 8
    front = PHONE_THICKNESS + front_clearance
    result = []
    for sign, name in ((-1, "left"), (1, "right")):
        y0, y1 = sorted((sign * (inner - 8.5), sign * outer))
        clip = _box(front, front + 3, y0, y1, PHONE_BOTTOM, PHONE_BOTTOM + 11)
        clip = g.cut(clip, _hole_x(sign * post_y, 25.5))
        result.append((name, clip))
    return result


def _top_cap():
    inner = PHONE_WIDTH / 2 + .5
    outer, front = inner + 8, PHONE_THICKNESS + .55
    # The 12 by 8 mm rear bridge carries the span without covering the screen.
    cap = _box(TOP_BRIDGE_REAR_X, -.5, -inner, inner, TOP_SEAT, TOP_FRAME)
    cap = g.fuse(cap,
                 _box(-.5, front + 3, -outer, -END_CONTACT_Y, TOP_SEAT, TOP_SEAT + 4),
                 _box(-.5, front + 3, END_CONTACT_Y, outer, TOP_SEAT, TOP_SEAT + 4),
                 _box(front, front + 3, -outer, -(inner - 8.5), TOP_SEAT - 11, TOP_FRAME),
                 _box(front, front + 3, inner - 8.5, outer, TOP_SEAT - 11, TOP_FRAME))
    for y in (-(inner + 4), inner + 4):
        cap = g.cut(cap, _hole_x(y, TOP_SCREW))
    # The shelf overlaps the top posts only outside the frame footprint.
    cap = g.cut(cap,
                _box(-1, front, -outer - 1, -inner, TOP_SEAT - 1, TOP_FRAME + 1),
                _box(-1, front, inner, outer + 1, TOP_SEAT - 1, TOP_FRAME + 1))
    return cap


def _feet():
    profile = [(-20, 9.5), (17, 9.5), (17, 13.5), (-4.5, 13.5),
               (-4.5, 40), (-10.5, 40), (-10.5, 13.5), (-20, 13.5)]
    result = []
    for sign, name in ((-1, "left"), (1, "right")):
        y = sign * 24
        foot = g.prism_xz(profile, y - 7, 14)
        for x in (-16, 12):
            foot = g.cut(foot, _hole_z(x, y, 8.5, 14.5))
        for z in (24, 34):
            foot = g.cut(foot, _hole_x(y, z))
        result.append(_part(f"phone_cradle_foot_{name}", foot,
                            print_rotation=(90, 0, 0),
                            note="Print on a broad Y side. Fit two M3x10 screws downward through the foot into hub nuts, then two M3x10 screws from behind into the frame nuts. Check tips remain behind the phone cavity."))
    return result


def build_phone():
    """Return assembled CAD parts, with the moving origin at the pan axis."""
    result = _fixed_clamp()
    result.extend([
        _hub(),
        _part("phone_cradle_rear_frame", _frame(), print_rotation=(0, -90, 0),
              note="Print on the column rear faces at X=-8.5, with removable build-plate support beneath the central rear plate at X=-4.5. The USB spine retains 6 mm of material and rounded port transitions. Fit the outer post nuts through the 7.4 mm rear access wells, at the unchanged M3x16 stack plane. Fit four nuts from the phone side for the unchanged rear feet. Both camera ends and long-edge button relief remain open. Measure actual buttons, cameras and the parked charging plug before assembly."),
        _part("phone_cradle_top_cap", _top_cap(), print_rotation=(180, 0, 0),
              note="Insert the landscape bare phone from above, then attach this cap with two M3x16 screws. The corner-seat top gap is 0.5 mm. The central long edge has button relief; front retention covers the outer corner regions, with both rear ends open for the camera."),
    ])
    for name, clip in _lower_clips():
        result.append(_part(f"phone_cradle_lower_clip_{name}", clip,
                            print_rotation=(0, 90, 0),
                            note="One M3x16 screw attaches this short corner clip at the unchanged lower post hole. The two clips retain the lower corners independently. The landscape bare phone has 0.5 mm end clearance and 0.55 mm screen clearance; do not tighten against the glass."))
    result.extend(_feet())

    servo = _box(CASE_X[0], CASE_X[1], -CASE_HALF_Y, CASE_HALF_Y,
                 CLAMP_BASE_Z, PAN_Z)
    result.append(_part("phone_pan_STS3215_envelope", servo, link="base",
                        material="servo", printable=False, mass_kg=.055,
                        note="Nominal case envelope only. Verify actual connector and underside boss positions against the servo before the complete saddle print."))
    horn = g.fuse(g.cylinder(9.975, 2.5, base=(0, 0, 2)),
                  g.cylinder(3.7, 2, base=(0, 0, 0)))
    horn = g.cut(horn, _hole_z(0, 0, -.1, 4.6, 3))
    for x, y in ((7, 0), (-7, 0), (0, 7), (0, -7)):
        horn = g.cut(horn, _hole_z(x, y, 1.9, 4.6, 3))
    result.append(_part("phone_pan_C018_metal_horn", horn,
                        material="metal", printable=False, mass_kg=.006,
                        note="The narrow boss faces the servo. The broad face is local Z4.5. This is a hardware envelope, not a printed spline adapter."))
    phone = _box(0, PHONE_THICKNESS, -PHONE_WIDTH / 2, PHONE_WIDTH / 2,
                 PHONE_BOTTOM, PHONE_BOTTOM + PHONE_HEIGHT)
    result.append(_part("Xiaomi_Mi9SE_bare_phone_envelope", phone,
                        material="phone", printable=False, mass_kg=.155,
                        note="Landscape screen faces +X, with the 147.5 mm dimension along Y. Use Wi-Fi and the phone battery during pan. USB is at a short side edge; park and disable pan before attaching power."))
    return result


def build_coupons():
    """Bottom 24.8 mm cradle samples with three practical clearance choices."""
    result = []
    for clearance in (.3, .5, .7):
        suffix = f"{clearance:.1f}".replace(".", "p")
        frame = _frame(clearance, clearance)
        frame = g.cut(frame, _box(-30, 30, -110, 110, 42.8, TOP_FRAME + 10))
        result.append(
            _part(f"phone_fit_{suffix}_tray", frame,
                  print_rotation=(0, -90, 0),
                  note=f"Assemble with the two matching corner clips and two M3x16 screws. This full-width landscape coupon uses {clearance:.1f} mm end and front clearance; test the bare phone bottom 24.8 mm. Print on its reinforced column backs with removable support beneath the central rear plate. Start with 0.5 mm; alternative full-width fits are optional."))
        for name, clip in _lower_clips(clearance, clearance):
            result.append(_part(f"phone_fit_{suffix}_clip_{name}", clip,
                                print_rotation=(0, 90, 0),
                                note=f"Matching short corner clip for the {clearance:.1f} mm phone fit tray. Use one M3x16 screw."))
    inner, outer = PHONE_WIDTH / 2 + .5, PHONE_WIDTH / 2 + 8.5
    spine = _frame()
    spine = g.cut(spine,
                  _box(-30, 30, -110, inner, 0, TOP_FRAME + 10),
                  _box(-30, 30, outer, 110, 0, TOP_FRAME + 10),
                  _box(-30, 30, -110, 110, 0, PORT_CENTER_Z - 22),
                  _box(-30, 30, -110, 110, PORT_CENTER_Z + 22, TOP_FRAME + 10))
    result.append(_part("phone_usb_spine_6mm_coupon", spine,
                        print_rotation=(0, -90, 0),
                        note="Exact 44 mm tall crop of the production USB column, with a 6 by 8 mm residual spine, 2 mm rounded transitions and the actual plug opening. Print on its rear face. Check the parked charging plug and inspect layer bonding before a controlled load fixture test; this coupon does not by itself validate the complete phone mount."))
    horn_coupon = _hub()
    horn_coupon["name"] = "phone_pan_horn_stack_fit"
    horn_coupon["assembly_note"] += " This coupon is the complete production hub and can be retained after a passing fit test."
    result.append(horn_coupon)
    return result


if __name__ == "__main__":
    for p in build_phone() + build_coupons():
        print(p["name"], "valid", g.valid(p["shape"]),
              "volume_mm3", round(g.volume(p["shape"]), 2),
              "bounds", g.bounds(p["shape"]))
