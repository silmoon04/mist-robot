"""Tapered tibia covers and an aluminium motor heat path, in native CAD ops.

Axes: x spans the leg plane, y is the wheel axle, z=-u points toward the foot.
The caller supplies tibia transforms and handedness. This recipe does not add
motor, shaft, bearing or structural-cheek solids. Dimensions are millimetres.
"""
from __future__ import annotations


VENTS = ((30.0, 4.0, "upper_exhaust"), (39.0, 4.0, "upper_exhaust"),
         (48.0, 4.0, "upper_exhaust"), (89.5, 5.0, "lower_intake"),
         (99.5, 5.0, "lower_intake"))


def build_shell_recipe():
    """Return separate machinable metal parts and two removable printed covers."""
    parts = []

    def box(center, size, mode="add"):
        return dict(kind="box", center=center, size=size, mode=mode)

    def cyl(start, end, radius, inner=0, mode="add"):
        return dict(kind="annulus" if inner else "cylinder", start=start, end=end,
                    radius=radius, inner=inner, mode=mode)

    def xz_polygon(points_x_u, y0, y1, mode="add"):
        # For normal +Y, plane local +v is world -Z, hence points use +u.
        return dict(kind="polygon", points=points_x_u, origin=(0, y0, 0),
                    normal=(0, 1, 0), x_axis=(1, 0, 0), thickness=y1-y0, mode=mode)

    def new(name, ops, metal=False, note=""):
        entry = dict(name=name, ops=ops, link="tibia", rigid_group="tibia",
                     category="hardware_reference" if metal else "print",
                     color="metal" if metal else "white",
                     material="aluminium_6061_candidate" if metal else "PETG",
                     density_g_cm3=2.70 if metal else 1.27,
                     mass_provenance="Solid material-volume estimate; no supplier mass or slicer infill applied.",
                     note=note)
        parts.append(entry)
        return entry

    # Two axial stations each have separate front/rear half-clamps. The split
    # lies across y=20 with a 0.6 mm closure gap, and M3 clamp bolts run along Y.
    for station, u0, inner in (("motor", 30.0, 12.30), ("gearbox", 65.0, 12.60)):
        outer = inner + 2.5
        for side, ycut, cut_size in (("front", 45.0, 50.6), ("rear", -5.0, 50.6)):
            ops = [cyl((0, 20, -u0), (0, 20, -(u0+10)), outer)]
            for x in (-16.0, 16.0):
                ops.append(box((x, 20, -(u0+5)), (6, 11, 10)))
            if side == "rear":
                # This bridge touches the sink at y=35.5 and remains outside
                # the motor bore; two M3 attachment holes enter the heat spine.
                ops.append(box((0, 33.75, -(u0+5)), (18, 3.5, 10)))
            ops.append(cyl((0, 20, -(u0-1)), (0, 20, -(u0+11)), inner, mode="cut"))
            ops.append(box((0, ycut, -(u0+5)), (80, cut_size, 14), "cut"))
            for x in (-16.0, 16.0):
                ops.append(cyl((x, 10, -(u0+5)), (x, 30, -(u0+5)), 1.7, mode="cut"))
            if side == "rear":
                for x in (-6.0, 6.0):
                    ops.append(cyl((x, 29, -(u0+5)), (x, 37, -(u0+5)), 1.25, mode="cut"))
            new(f"TH01_{station}_clamp_{side}", ops, metal=True,
                note=(f"2.5 mm radial aluminium half-clamp, u{u0:g}..{u0+10:g}; "
                      f"{inner*2:g} mm nominal bore. M3 split-bolt bores and tapped sink attachment "
                      "holes are explicit. Bore fit, clamp preload and interface grease require validation."))

    # A single continuous spine carries fourteen longitudinal fins. The narrow
    # fin bank fits between structural rails whose inner faces are at x=+/-15.
    sink_ops = [box((0, 36.5, -63.5), (28, 2, 79))]
    for index in range(14):
        x = -13.0 + 2.0 * index
        sink_ops.append(box((x, 42.75, -63.5), (0.8, 10.5, 79)))
    for center_u, slot_height, _kind in VENTS:
        sink_ops.append(box((0, 48.2, -center_u), (29, 3.6, slot_height+3), "cut"))
    for u in (35.0, 70.0):
        for x in (-6.0, 6.0):
            sink_ops.append(cyl((x, 34, -u), (x, 50, -u), 1.7, mode="cut"))
            sink_ops.append(cyl((x, 37.5, -u), (x, 50, -u), 2.9, mode="cut"))
    for hand in (-1, 1):
        pocket = [(hand*x, u) for x, u in ((14.7, 90), (25, 90), (25, 104), (10.08, 104))]
        sink_ops.append(xz_polygon(pocket, 36.7, 43.3, "cut"))
    new("TH02_aluminium_heat_spine_and_fins", sink_ops, metal=True,
        note=("Continuous x+/-14, y35.5..37.5, u24..103 spine. Fourteen 0.8 mm fins have "
              "1.2 mm clear channels and end at y48; five tip reliefs clear the vent baffles. "
              "Tapered root pockets below u90 clear the structural rails, while fin tips remain continuous above y43.3. "
              "Machined or brazed construction, flat clamp contacts and measured airflow are required."))

    outer = [(-15, 14), (15, 14), (23.6, 23), (23.6, 90), (17, 110),
             (17, 146), (13, 150), (-13, 150), (-17, 146), (-17, 110),
             (-23.6, 90), (-23.6, 23)]
    inner = [(-14.0, 16.1), (14.0, 16.1), (21.5, 24), (21.5, 90), (14.9, 110),
             (14.9, 145.1), (12.1, 147.9), (-12.1, 147.9), (-14.9, 145.1),
             (-14.9, 110), (-21.5, 90), (-21.5, 24)]
    for side, y0, y1, inner_y0, inner_y1 in (
            ("front", -24.4, 13.8, -22.3, 14.0), ("rear", 14.2, 52.4, 14.0, 50.0)):
        ops = [xz_polygon(outer, y0, y1), xz_polygon(inner, inner_y0, inner_y1, "cut")]
        ops.append(cyl((0, y0-1, 0), (0, y1+1, 0), 18, mode="cut"))
        ops.append(cyl((0, y0-1, -140), (0, y1+1, -140), 10, mode="cut"))
        if side == "front":
            ops.append(cyl((0, -12.8, -140), (0, 12.8, -140), 43.3, mode="cut"))
        else:
            ops.append(cyl((0, 36.7, -140), (0, 48.4, -140), 17.1, mode="cut"))
            for x in (-18.0, 18.0):
                ops.append(box((x, 40.0, -18.5), (7.0, 6.6, 15.0), "cut"))
            for center_u, slot_height, _kind in VENTS:
                ops.append(box((0, 51.5, -center_u), (25.6, 5, slot_height), "cut"))
                ops.append(box((0, 47.4, -center_u), (26.8, 0.8, slot_height+3)))
                for x in (-14.1, 14.1):
                    ops.append(box((x, 49.0, -center_u), (1.4, 4, slot_height+3)))
        # Mount through the covers into the caller's frame with removable M3
        # screws. Short bosses strengthen only the local cover wall.
        for x, u in ((-17.5, 55), (17.5, 55), (-11.0, 124), (11.0, 124)):
            a, b = ((-24.4, -21.8) if side == "front" else (49.5, 52.4))
            ops.append(cyl((x, a, -u), (x, b, -u), 3.2))
            ops.append(cyl((x, a-1, -u), (x, b+1, -u), 1.7, mode="cut"))
        cover = new(f"TH03_white_faceted_cover_{side}", ops,
                    note=("Removable white PETG cover, 0.4 mm central seam, upper width 47.2 mm tapering "
                          "to 34 mm. Knee scallop and 20 mm circular foot service opening remain open. "
                          "The rear cover has a 34.2 mm internal foot-boss pocket through y36.7..48.4. "
                          "M3 mount bores require matching caller-frame inserts; no thermal insulation liner."))
        if side == "rear":
            cover["ventilation"] = thermal_assumptions()["ventilation"]
    return parts


def thermal_assumptions():
    """Return arithmetic estimates and explicit commissioning conditions."""
    slot_width = 25.6
    upper_area = sum(slot_width * height for _, height, kind in VENTS if kind == "upper_exhaust")
    lower_area = sum(slot_width * height for _, height, kind in VENTS if kind == "lower_intake")
    # Air exits above and below each offset baffle through a nominal 2.2 mm gap.
    throat_each = 2 * slot_width * 2.2
    upper_throat = sum(min(slot_width * height, throat_each) for _, height, kind in VENTS
                       if kind == "upper_exhaust")
    lower_throat = sum(min(slot_width * height, throat_each) for _, height, kind in VENTS
                       if kind == "lower_intake")
    relieved_u = sum(height+3 for _, height, _ in VENTS)
    # Each head-access bore reaches two fins, hence four broad faces. Deducting
    # its full diameter across each face overestimates the removed area.
    head_access_area_upper_bound_mm2 = 4 * 4 * 5.8 * 10.5
    rail_pocket_face_area_mm2 = 0.0
    for index in range(14):
        for face_x in (-13+2*index-0.4, -13+2*index+0.4):
            pocket_begins_u = 90 + (14.7-abs(face_x))/0.33
            rail_pocket_face_area_mm2 += max(0.0, 103-max(90.0, pocket_begins_u)) * 5.8
    fin_two_face_area = (2 * 14 * (79 * 10.5 - relieved_u * 1.6)
                         - head_access_area_upper_bound_mm2 - rail_pocket_face_area_mm2) / 1e6
    h_values = (3.0, 5.0, 8.0)
    return dict(
        status="Unvalidated thermal design estimate; no CFD, flow test or temperature test performed.",
        outer_envelope_mm=dict(x_upper=[-23.6, 23.6], x_lower=[-17, 17], y=[-24.4, 52.4], u=[14, 150]),
        required_frame_clearance=("Positive-side rails must taper from x15..21 to x9..14.4 by u110 "
                                  "to fit the lower cover. The y35.5..48 fin bank occupies x+/-14, u24..103."),
        hardware_to_integrate=dict(clamp_split_M3_bolts=4, clamp_split_M3_nuts=4,
                                   clamp_to_spine_M3_bolts=4, cover_M3_screws=8,
                                   note=("Fastener solids belong to the caller assembly. Select actual lengths after "
                                         "the frame and cover mounting interfaces are fixed. Four 5.8 mm access "
                                         "counterbores pass through the fin bank at x+/-6, u35 and u70.")),
        ventilation=dict(direction="Rear-facing lower intake and upper exhaust; buoyancy depends on leg pose.",
                         upper_slot_area_mm2=upper_area, lower_slot_area_mm2=lower_area,
                         upper_baffled_throat_area_mm2=upper_throat, lower_baffled_throat_area_mm2=lower_throat,
                         series_path_area_upper_bound_mm2=min(upper_throat, lower_throat),
                         baffle_to_cover_gap_mm=2.2, baffle_to_relief_fin_gap_mm=0.6,
                         fin_channel_clear_width_mm=1.2,
                         fin_bank_axial_channel_area_mm2=13*1.2*10.5,
                         fin_bank_axial_channel_area_at_tip_reliefs_mm2=13*1.2*8.9,
                         method=("Rectangular geometric free areas. The series bound covers the two baffled vent groups; "
                                 "the fin-bank channel cross-sections are listed separately. Side bypasses, entrance losses, "
                                 "fouling and pressure drop are unmodelled.")),
        heat_path="Motor case -> split aluminium clamp -> bolted aluminium spine -> exposed fin channels -> baffled vents.",
        fin_two_face_area_m2=fin_two_face_area,
        area_method=("Both broad fin faces after five tip reliefs, with a conservative full-diameter rectangle "
                     "deducted for each screw-head access bore crossing each fin face, plus the tapered rail-root pockets. "
                     "Spine and fin-edge areas are omitted; this is an arithmetic area estimate."),
        winding_resistance_ohm_assumed=2.18, winding_current_limit_a_proposed=1.0,
        copper_heat_at_1a_w=2.18, total_motor_heat_w_assumed=[5.0, 7.0],
        total_heat_note="5..7 W includes an unmeasured allowance for other motor/gearbox losses; I^2R alone is 2.18 W at 1 A.",
        convection_sensitivity=[dict(h_w_m2_k=h, sink_to_air_k_per_w=1/(h*fin_two_face_area),
                                      rise_at_5w_k=5/(h*fin_two_face_area), rise_at_7w_k=7/(h*fin_two_face_area))
                                for h in h_values],
        sensitivity_note="h=3,5,8 W/m^2/K are assumed sensitivity cases, not measured coefficients. Contact resistance adds rise.",
        conditional_limits=dict(ambient_assumed_c=25, case_cutoff_c_proposed=60, shell_cutoff_c_proposed=45,
                                winding_cutoff_c_proposed=80,
                                duty_at_7w_for_25k_rise_h5_upper_bound=25*5*fin_two_face_area/7,
                                note=("These are proposed controller limits, not validated material or motor ratings. "
                                      "Fit case and shell sensors and verify winding temperature before sustained operation. "
                                      "The duty estimate omits contact resistance and requires a steady averaged heat model; "
                                      "a stalled motor cannot be approved by averaging duty. Reduce current/duty or add airflow "
                                      "if measured temperatures approach the limits.")))
