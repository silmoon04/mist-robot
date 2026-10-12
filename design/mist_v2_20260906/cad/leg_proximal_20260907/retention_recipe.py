"""Prototype retention and sliding adjustment recipes; dimensions are millimetres.

Coordinates: x is transverse, y is shaft axis, z=-u points toward the knee.
All datum choices are engineering proposals, not supplied-part certifications.
The caller builds the motor cassette, rails and bearings and applies `cuts`.
The selected belt report remains the authority for belt capacity.
"""
from __future__ import annotations

import math


def build_retention_recipe(femur_length_mm=139.5, carriage_u_mm=0.0,
                           mount_y_mm=-7.0, input_right_bearing_start_y_mm=42.325,
                           knee_right_bearing_start_y_mm=42.325,
                           axial_endfloat_mm=0.05):
    """Return parts, target-specific cuts and datums; no CAD imports or I/O.

    Input components move by carriage_u_mm. Knee components use tibia-local z=0.
    Fixed rail/bridge parts remain in the femur frame. Mount_y is the contact
    plane between a 6 mm fixed rail and a 4 mm sliding plate above it in +y.
    Apply input_gear cuts to an 8 mm gear at y28.125..36.125. Change the input
    shaft to y3..(right bearing end+2) before applying end-tap cuts. The output shaft remains
    y-24..52. Mirroring and world transforms belong to the caller.
    """
    delta = float(carriage_u_mm)
    if not -1.0 <= delta <= 3.0:
        raise ValueError("Carriage travel is -1 to +3 mm from nominal")
    if abs(float(femur_length_mm) - 139.5) > 0.001:
        raise ValueError("This recipe retains the 375 mm / 32T belt datum")
    parts, cuts = [], []
    right_start = float(input_right_bearing_start_y_mm)
    right_end = right_start + 7.0
    knee_right_start = float(knee_right_bearing_start_y_mm)
    knee_right_end = knee_right_start + 7.0
    input_shaft_end = right_end + 2.0
    axial_float = float(axial_endfloat_mm)
    if not 0.02 <= axial_float <= 0.10:
        raise ValueError("Prototype rotor endfloat must be specified within0.02..0.10mm")
    if right_start < 41.125:
        raise ValueError("Right bearing must clear the ordinary M4 face heads")
    if not 41.125 <= knee_right_start <= 44.0:
        raise ValueError("Outer knee bearing must clear M4heads and retain an end spacer before y52")

    def box(c, size, mode="add"):
        return dict(kind="box", center=c, size=size, mode=mode)

    def cyl(a, b, radius, inner=0, mode="add"):
        return dict(kind="annulus" if inner else "cylinder", start=a, end=b,
                    radius=radius, inner=inner, mode=mode)

    def yr(x, u, a, b, radius, inner=0, mode="add"):
        return cyl((x, a, -u), (x, b, -u), radius, inner, mode)

    def new(name, ops, link="femur", category="hardware_reference", note="",
            material="steel_candidate", density=7.85):
        p = dict(name=name, link=link, category=category,
                 color="metal" if category == "hardware_reference" else "structure",
                 note=note, ops=ops, material=material, density_g_cm3=density,
                 mass_provenance="Recipe solid-volume estimate; not weighed")
        parts.append(p)
        return p

    def cut(target, ops, note=""):
        cuts.append(dict(target=target, ops=ops, note=note))

    def y_bolt(name, x, u, head_base, length, diameter, head_diameter,
               head_height, direction=-1, link="femur", note=""):
        end = head_base + direction * length
        head_end = head_base - direction * head_height
        new(name, [yr(x, u, min(end, head_base), max(end, head_base), diameter/2),
                   yr(x, u, min(head_base, head_end), max(head_base, head_end),
                      head_diameter/2)], link=link,
            note=note + " Thread and hex socket are simplified envelopes.")

    # Plain-bore A pulleys transfer torque through axial bolts, not set screws.
    # Ordinary M4 heads remain visible. M4x14 through an 8mm carrier gives6mm
    # nominal engagement into an 8mm tap. Sleeve/body fit and face friction need
    # testing; thread clearance in an ordinary sleeve is not a zero-backlash fit.
    for label, link, axis_u, target in (
            ("input", "femur", delta, "input_gear"),
            ("knee", "tibia", 0.0, "tibia_hub")):
        ops = []
        for i in range(4):
            angle = math.pi*i/2
            x, u = 8*math.cos(angle), axis_u + 8*math.sin(angle)
            ops += [yr(x, u, 28.0, 36.3, 3.3, mode="cut")]
            new(f"RT_{label}_face_sleeve_{i}",
                [yr(x, u, 28.125, 36.125, 3.25, 2.15)], link=link,
                note="Custom steel compression sleeve OD6.5/ID4.3/L8; printed seat and sleeve-length fit need coupon validation. Clearance alone does not give a low-backlash torque path.")
            y_bolt(f"RT_{label}_M4x14_face_{i}", x, u, 36.125, 14, 4, 7, 4,
                   link=link, note="M4x14 socket screw, nominal6mm pulley engagement, ordinary heady36.125..40.125; confirm useful thread depth and screw length before assembly.")
        cut(target, ops, "Four 16 mm PCD holes with metal sleeve seats; no supplier torque rating for the printed carrier.")

    # Output adapter joins the existing tibia at u48, x+/-9. Main must merge or
    # through-bolt these overlapping rails to its own tibia structure.
    hub = [yr(0, 0, 28.125, 36.125, 19, 4.1)]
    for x in (-9, 9):
        hub.append(box((x, 32.125, -32), (6.8, 8, 40)))
        hub.append(yr(x, 48, 27.9, 36.4, 1.7, mode="cut"))
    new("RT_knee_face_bolted_adapter", hub, link="tibia", category="print",
        material="PETG", density=1.27,
        note="Prototype OD38x8 hub with two6.8mm rails to existing tibia u48/x+/-9; apply tibia_hub cuts and merge/bolt to the real tibia. Sleeve seat and reversing stiffness are unvalidated.")

    # Each end washer spans the shaft end and an inner-race-only spacer. Do not
    # preload a fixed outer-race pair by tightening mismatched spacer lengths.
    shaft_stacks = (
        ("input", "femur", delta, 7.0, 3.0, input_shaft_end,
         [(3.0, 5.0), (12.0, 14.125), (36.125, right_start), (right_end, input_shaft_end)]),
        ("knee", "tibia", 0.0, 8.0, -24.0, 52.0,
         [(-24.0, -14.2), (-7.2, 14.125), (36.125, knee_right_start), (knee_right_end, 52.0)]),
    )
    for label, link, axis_u, diameter, lo, hi, spans in shaft_stacks:
        for i, (a, b) in enumerate(spans):
            if i == 0:
                a += axial_float
            od = 8.6 if i == 2 else 10.0
            spacer_ops = [yr(0,axis_u,a,b,od/2,diameter/2+0.1)]
            if i == 2 and b > 40.625:
                spacer_ops = [yr(0,axis_u,a,40.625,4.3,diameter/2+0.1),
                              yr(0,axis_u,40.625,b,5.0,diameter/2+0.1)]
            new(f"RT_{label}_inner_spacer_{i}",
                spacer_ops, link=link,
                note=f"Custom steel OD{od:g} inner-race spacer; OD8.6 neck clears M4heads by0.2mm then grows toOD10 aftery40.625. Knee neck wall0.2mm remains unvalidated. Shortened low-end spacer reserves measured{axial_float:g}mm endfloat so M3tightening reacts on shaft end,not bearing stack. Verify abutment and actual stack.")
        cut(label+"_shaft", [yr(0, axis_u, lo-.1, lo+10, 1.25, mode="cut"),
                              yr(0, axis_u, hi-10, hi+.1, 1.25, mode="cut")],
            "M3 axial end taps, at least8mm useful thread;2.5mm pilot envelopes. Material and machining are procurement requirements.")
        for side, end, direction in (("low", lo, 1), ("high", hi, -1)):
            a, b = (end-1.6, end) if direction == 1 else (end, end+1.6)
            new(f"RT_{label}_end_washer_{side}",
                [yr(0, axis_u, a, b, 6.0, 1.6)], link=link,
                note="Custom steel OD12/ID3.2/t1.6 washer bears directly on shaft end; selected spacer train is shorter by endfloat allowance. Do not torque an oversized spacer train into bearing preload; outer races and shields remain clear.")
            head_base = a if direction == 1 else b
            y_bolt(f"RT_{label}_M3x8_end_{side}", 0, axis_u, head_base, 8, 3,
                   5.5, 3, direction=direction, link=link,
                   note="M3x8 end screw gives6.4mm nominal engagement; use removable thread locking after setting free rotation/endfloat. End screws locate axially; they are not drive keys.")
    cut("tibia_main_cheek", [yr(0, 0, -24.1, -14.1, 5.15, mode="cut")],
        "Clear OD10 inner-race spacer through prior8mm shaft opening; recheck local cheek strength.")

    # Rail contact y=mount_y. Lock bolts remain fixed at nominal coordinates;
    # asymmetric slots permit -1..+3 mm carriage movement.
    slot_ops, fixed_ops = [], []
    for u0, x_positions in ((22.0, (-18.0, 18.0)), (56.0, (-18.0, 18.0))):
        for x in x_positions:
            a, b = u0-3+delta, u0+1+delta
            slot_ops += [box((x, mount_y_mm+2, -(a+b)/2), (4.4, 6, b-a), "cut"),
                         yr(x, a, mount_y_mm-1, mount_y_mm+5, 2.2, mode="cut"),
                         yr(x, b, mount_y_mm-1, mount_y_mm+5, 2.2, mode="cut")]
            fixed_ops.append(yr(x, u0, mount_y_mm-7, mount_y_mm+1, 2.2, mode="cut"))
            spreader = ([yr(x, u0, mount_y_mm+4, mount_y_mm+5.5, 4.5, 2.2)]
                        if u0 < 0 else
                        [box((x, mount_y_mm+4.75, -u0), (12, 1.5, 14)),
                         yr(x, u0, mount_y_mm+3.9, mount_y_mm+5.6, 2.2, mode="cut")])
            new(f"RT_slider_spreader_{x}_{u0}", spreader,
                note="Custom steel12x14xt1.5 spreader bridges slot. Bolt lands widen tox+/-25; stationsu22/56 avoid proximal bearing cup. Verify slot-edge bearing and cantilever moment.")
            y_bolt(f"RT_slider_M4x20_{x}_{u0}", x, u0, mount_y_mm+5.5, 20,
                   4, 7, 4, note="M4x20 clamp bolt through6mm rail and4mm carriage; use steel nut and lower washer, modeled separately by main.")
    cut("carriage_plate", slot_ops, "4.4mm width,8.4mm total slot length. Proximal end must be circularR17, not upper rectangular corners; plate widens only distally after collision check.")
    cut("fixed_rails", fixed_ops, "Fixed through holes; rails and compression-bearing lands must carry locked cartridge forces.")

    # Fixed distal jack reacts into a broad metal plate. Head is accessed along
    # the femur from u>108, without reaching through the motor or belt.
    jack_y = mount_y_mm+2
    def z_hex(af, u0, u1, mode="add"):
        radius = af/math.sqrt(3)
        points = [(radius*math.cos(i*math.pi/3),
                   radius*math.sin(i*math.pi/3)) for i in range(6)]
        return dict(kind="polygon", points=points, origin=(0,jack_y,-u0),
                    normal=(0,0,-1), x_axis=(1,0,0), thickness=u1-u0, mode=mode)
    bridge = [box((0, jack_y, -86), (26, 22, 20)),
              cyl((0, jack_y, -75.8), (0, jack_y, -96.2), 2.2, mode="cut"),
              z_hex(7.2,75.9,90.0,"cut"),
              box((0,jack_y,-91),(18.2,18.2,2.1),"cut")]
    new("RT_fixed_jack_bridge", bridge, category="print", material="PETG",
        density=1.27, note="Fixed to femur rails at u76..96; add structural gussets to parent rails. Insert M4x12 coupling nut from proximal end,then load plate from side pocket. Downstream4mm wall reacts screw load through steel plate.")
    new("RT_M4_coupling_nut",[z_hex(7.0,78.0,90.0),
        cyl((0,jack_y,-77.9),(0,jack_y,-90.1),2,mode="cut")],
        note="M4 coupling nut,7mmAFx12mm length; steel hardware. Captured in7.2AF prototype pocket; calibrate printed fit.")
    new("RT_M4_adjuster_jam_nut",[z_hex(7.0,96.0,99.2),
        cyl((0,jack_y,-95.9),(0,jack_y,-99.3),2,mode="cut")],
        note="M4 jam nut envelope7mmAFx3.2mm; final position against fixed bridge after tensioning. Reserve7mm spanner access.")
    for tag, u, size in (("carriage_tip_pad", 70+delta, (12, 12, 1.5)),
                         ("fixed_nut_load_plate", 90, (18, 18, 2))):
        ops = [box((0, jack_y, -u-size[2]/2), size)]
        if tag.startswith("fixed"):
            ops.append(cyl((0, jack_y, -89.9), (0, jack_y, -92.1), 2.2, mode="cut"))
        new("RT_"+tag, ops, note="Custom steel load-spreading plate; provide captured pocket/fastening in parent. Tip pad moves with cassette.")
    tip_u = 71.5+delta
    head_u = tip_u+30
    new("RT_M4x30_adjuster",
        [cyl((0, jack_y, -tip_u), (0, jack_y, -head_u), 2),
         cyl((0, jack_y, -head_u), (0, jack_y, -(head_u+4)), 3.5)],
        note="M4x30 fully threaded steel adjuster,0.7mm pitch;12mm steel coupling nut at u78..90 plus jam nut. Set tension by measurement,then lock. Simplified screw envelope.")
    cut("fixed_jack_bridge_parent", [],
        "Connect fixed bridgeu76..96 to fixed rails. Cut side loading opening for steel load plateu90..92 and add its small retaining cover; keep4mm downstream load wallu92..96 intact. Reserve7mm jam-nut spanner access.")

    metadata = dict(
        status="prototype_dimensioned_interface_not_strength_release",
        nominal_belt_centre_distance_mm=139.5,
        actual_geometric_centre_distance_mm=139.5-delta,
        carriage_travel_mm=[-1, 3],
        mount_y_mm=mount_y_mm,
        plate_own_bounds=dict(proximal_end_radius_mm=17, distal_x=[-25,25], u=[-17,70], thickness_mm=4,
                             note="Use circular proximal end; main owns contour transition and collision check"),
        recommended_fixed_rail_bounds=dict(distal_x_bands=[[-25,-11],[11,25]],u=[16,96],
                                           proximal_pad_radius_mm=17,thickness_mm=6),
        input_shaft=dict(diameter_mm=7,y_mm=[3,input_shaft_end],end_tap="M3",pilot_mm=2.5),
        knee_shaft=dict(diameter_mm=8,y_mm=[-24,52],end_tap="M3",pilot_mm=2.5),
        rotor_axial_endfloat_mm=axial_float,
        input_bearing_centres_y_mm=[8.5,right_start+3.5],
        knee_bearing_centres_y_mm=[-10.7,knee_right_start+3.5],
        pulley_y_mm=[14.125,28.125],gear_or_adapter_y_mm=[28.125,36.125],
        face_bolt=dict(count=4,pcd_mm=16,thread="M4",length_mm=14,
                       nominal_engagement_mm=6,nominal_tapped_depth_mm=8,
                       counterbore_diameter_mm=None,counterbore_depth_mm=0,
                       head_projection_mm=4.0,steel_sleeve_od_mm=6.5),
        screw_access=dict(adjuster_from_u_mm=110,hex_mm=3,
                          input_end_screws_from_y_mm=[-8,input_shaft_end+12],end_hex_mm=2.5),
        unresolved=["Factory acceptance of proposed MISUMI QFC16-M4 configuration and exact usable tap depth",
                    "Centring register, sleeve seat fit and reversing compliance of printed carriers",
                    "Actual bearing abutment diameter/chamfer, shaft bearing fit, matched spacer stack and axial endfloat",
                    "Nut, lower clamp washer and jack plate pocket integration by parent",
                    "Root/frame collisions throughout motion and installation travel",
                    "FDM compression/creep and stiffness verification; no screw tightening torque assigned to printed clamps"])
    for p in parts:
        if p["name"].startswith("RT_input_"):
            p["rigid_group"] = "knee_input_rotor"
    return dict(parts=parts,cuts=cuts,metadata=metadata)


def retention_recipe(**kwargs):
    """Short alias for callers."""
    return build_retention_recipe(**kwargs)
