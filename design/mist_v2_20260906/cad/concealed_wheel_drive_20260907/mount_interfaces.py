"""Bolted motor/sink and removable-cover interfaces in unmirrored tibia axes.

The caller applies handedness and occurrence transforms after applying this
recipe. Existing baseline files are not modified. Threads use nominal smooth
envelopes; the specified thread engagements remain manufacturing requirements.
"""
from __future__ import annotations

import copy
import math


MOTOR_STATIONS_U_MM = (35.0, 70.0)
COVER_STATIONS = ((17.5, 58.0), (11.0, 121.0))


def _box(c, size, mode="add"):
    return dict(kind="box", center=c, size=size, mode=mode)


def _yr(x, u, y0, y1, r, inner=0, mode="add"):
    return dict(kind="annulus" if inner else "cylinder", start=(x, y0, -u), end=(x, y1, -u),
                radius=r, inner=inner, mode=mode)


def _hex(x, u, y0, y1, af, mode="add"):
    radius = af / math.sqrt(3)
    points = [(x+radius*math.cos(math.radians(30+60*i)),
               u+radius*math.sin(math.radians(30+60*i))) for i in range(6)]
    return dict(kind="polygon", points=points, origin=(0, y0, 0), normal=(0, 1, 0),
                x_axis=(1, 0, 0), thickness=y1-y0, mode=mode)


def build_mount_recipe():
    """Return added parts, target-specific operations and an assembly contract."""
    parts, additions = [], {}

    def add(target, operations):
        additions.setdefault(target, []).extend(operations)

    def part(name, operations, material="steel_candidate", density=7.85, note=""):
        entry = dict(name=name, ops=operations, link="tibia", rigid_group="tibia",
                     category="hardware_reference", color="metal", material=material,
                     density_g_cm3=density, note=note,
                     mass_provenance="Solid hardware-envelope estimate; helical threads and socket recesses omitted.")
        parts.append(entry)
        return entry

    def nut(name, x, u, y0, y1):
        return part(name, [_hex(x, u, y0, y1, 5.5), _yr(x, u, y0-.1, y1+.1, 1.6, mode="cut")],
                    note="M3 hex nut, 5.5 mm across flats and 2.4 mm thick; nominal female thread shown as a smooth clearance bore.")

    def bolt(name, x, u, tip, under_head, head_end, radius=2.75, note=""):
        part(name, [_yr(x, u, min(tip, under_head), max(tip, under_head), 1.5),
                    _yr(x, u, min(under_head, head_end), max(under_head, head_end), radius)], note=note)

    # Each split-clamp bolt also fixes its motor station to the positive frame.
    # Metal tubes support the entire gap between the clamp's rear pad and rail.
    for station, u in zip(("motor", "gearbox"), MOTOR_STATIONS_U_MM):
        rear = f"TH01_{station}_clamp_rear"
        front = f"TH01_{station}_clamp_front"
        for hand in (-1, 1):
            x = 16.0 * hand
            tag = f"{station}_{'L' if hand < 0 else 'R'}"
            add(rear, [_box((x, 26.85, -u), (6, 2.7, 10)),
                       _yr(x, u, 25.4, 28.3, 1.7, mode="cut")])
            add("CW09_positive_tibia_frame", [_yr(x, u, 37, 43, 3.4),
                                              _yr(x, u, 36.9, 43.1, 1.7, mode="cut")])
            add("TH02_aluminium_heat_spine_and_fins", [
                _yr(x, u, 35.2, 43.6, 3.6, mode="cut"),
                _yr(x, u, 43.5, 46.8, 3.0, mode="cut")])
            part(f"MI01_clamp_frame_tube_{tag}", [_yr(x, u, 28.2, 37, 3, 1.6)],
                 material="aluminium_6061_candidate", density=2.7,
                 note="8.8 mm long, OD6/ID3.2 aluminium compression tube. End faces bear on the machined clamp pad and printed rail.")
            part(f"MI02_clamp_frame_washer_{tag}", [_yr(x, u, 43, 43.5, 3.4, 1.6)],
                 note="OD6.8, ID3.2, 0.5 mm steel washer spreads the bolt-head load on the rail boss.")
            bolt(f"MI03_clamp_frame_M3x35_{tag}", x, u, 8.5, 43.5, 46.5,
                 note="M3x35 socket screw from the rear; 3 mm head. Passes through the rail, tube and both clamp lugs to a front nut.")
            nut(f"MI04_clamp_front_M3_nut_{tag}", x, u, 12.1, 14.5)
            add(front, [_hex(x, u, 11.8, 14.5, 5.7, "cut")])

        # Captive nuts replace the original unmodelled tapped connection. Their
        # pockets open toward the motor and must be filled before motor fitting.
        add(rear, [_box((0, 33.75, -u), (20, 3.5, 10))])
        for x in (-6.0, 6.0):
            add(rear, [_hex(x, u, 30.5, 34.8, 5.7, "cut"),
                       _yr(x, u, 34.7, 35.6, 1.6, mode="cut")])
            tag = f"{station}_{'L' if x < 0 else 'R'}"
            nut(f"MI05_sink_captive_M3_nut_{tag}", x, u, 32.4, 34.8)
            bolt(f"MI06_sink_M3x5_{tag}", x, u, 32.5, 37.5, 40.5,
                 note="M3x5 socket screw seats on the spine at y37.5; engages 2.3 mm of captive nut without entering the motor envelope.")
        add(rear, [dict(kind="cylinder", start=(0, 20, -(u-6)), end=(0, 20, -(u+6)),
                        radius=12.3 if station == "motor" else 12.6, inner=0, mode="cut")])

    # Frame entry clearances open only into the internal cover cavity. The
    # outer faces remain in place around the existing knee service openings.
    add("TH03_white_faceted_cover_front", [
        _box((0, -19, -18), (28.6, 6.6, 10), "cut"),
        _yr(0, 140, -22.3, -15.7, 14.3, mode="cut")])
    for hand in (-1, 1):
        add("TH03_white_faceted_cover_front", [_box((hand*17.1, -19, -90), (7.8, 6.6, 8.6), "cut")])
    add("TH03_white_faceted_cover_rear", [_yr(0, 0, 27.8, 36.5, 22.3, mode="cut")])
    for hand in (-1, 1):
        add("TH03_white_faceted_cover_rear", [_box((hand*18, 35.55, -18.5), (7, 15.5, 15), "cut")])

    # Cover heads are recessed, keeping the existing outer envelope. Each
    # cover has four captive frame nuts, so service needs one hex key only.
    for xabs, u in COVER_STATIONS:
        for hand in (-1, 1):
            x = hand*xabs
            tag = f"{'upper' if u == 58 else 'lower'}_{'L' if hand < 0 else 'R'}"
            if u == 58:
                front_pad = _box((hand*16.6, -18.5, -u), (9.2, 7, 9))
            else:
                front_pad = _yr(x, u, -22, -15, 3.6)
            add("T02_tibia_main_cheek", [front_pad,
                _yr(x, u, -22.1, -14.9, 1.7, mode="cut"),
                _yr(x, u, -22.1, -20.2, 3.4, mode="cut"),
                _hex(x, u, -18.4, -16, 5.7, "cut")])
            nut(f"MI07_front_cover_captive_nut_{tag}", x, u, -18.4, -16)
            bolt(f"MI08_front_cover_M3x8_{tag}", x, u, -14.6, -22.6, -24.25, radius=2.85,
                 note="M3x8 button-head envelope, Ø5.7x1.65 mm. Recessed 0.15 mm below the front cover; 2 mm hex-key access.")
            # Small bosses make the nut traps closed even at the narrow rails.
            add("CW09_positive_tibia_frame", [_box((x, 39.6, -u), (6.8, 6.8, 8)),
                _yr(x, u, 36.1, 43.1, 1.7, mode="cut"),
                _hex(x, u, 37.2, 39.6, 5.7, "cut")])
            nut(f"MI09_rear_cover_captive_nut_{tag}", x, u, 37.2, 39.6)
            part(f"MI10_rear_cover_standoff_{tag}", [_yr(x, u, 43, 48.4, 3, 1.6)],
                 material="aluminium_6061_candidate", density=2.7,
                 note="5.4 mm OD6/ID3.2 aluminium stand-off supports the cover boss directly against the frame.")
            bolt(f"MI11_rear_cover_M3x16_{tag}", x, u, 34.6, 50.6, 52.25, radius=2.85,
                 note="M3x16 button-head envelope, Ø5.7x1.65 mm. Recessed into the rear cover and retained by a captive frame nut.")

    return dict(parts=parts, add_ops=additions, cover_mount_updates=dict(
        old_to_new_u_mm={55.0: 58.0, 124.0: 121.0}, front_boss_end_y_mm=-20.2,
        rear_boss_start_y_mm=48.4, button_head_counterbore_diameter_mm=6.1,
        front_counterbore_y_mm=[-24.5, -22.6], rear_counterbore_y_mm=[50.6, 52.5]),
        metadata=mounting_contract())


def apply_to_parts(parts):
    """Return (new_parts, metadata); input parts must be in unmirrored tibia axes.

    Existing occurrence transforms are retained. New parts have no transform;
    the caller supplies the tibia frame and then applies handedness consistently.
    """
    result = copy.deepcopy(list(parts))
    by_name = {part["name"]: part for part in result}
    recipe = build_mount_recipe()
    required = set(recipe["add_ops"]) | {"TH03_white_faceted_cover_front", "TH03_white_faceted_cover_rear"}
    missing = sorted(required-set(by_name))
    if missing:
        raise ValueError("Mounting targets missing: " + ", ".join(missing))
    if any(part["name"].startswith("MI") for part in result):
        raise ValueError("Mounting interfaces have already been applied")
    for target, operations in recipe["add_ops"].items():
        by_name[target]["ops"].extend(copy.deepcopy(operations))
    for side in ("front", "rear"):
        cover = by_name[f"TH03_white_faceted_cover_{side}"]
        moved = 0
        for operation in cover["ops"]:
            if operation["kind"] not in ("cylinder", "annulus"):
                continue
            x, _y, z = operation["start"]
            if abs(x) not in (17.5, 11.0) or -z not in (55.0, 124.0):
                continue
            new_u = {55.0: 58.0, 124.0: 121.0}[-z]
            for key in ("start", "end"):
                px, py, _pz = operation[key]
                operation[key] = (px, py, -new_u)
            if operation.get("mode") != "cut" and operation["radius"] == 3.2:
                if side == "front":
                    operation["end"] = (x, -20.2, -new_u)
                else:
                    operation["start"] = (x, 48.4, -new_u)
            moved += 1
        if moved != 8:
            raise ValueError(f"Expected eight original {side} cover mount operations, found {moved}")
        for xabs, u in COVER_STATIONS:
            for hand in (-1, 1):
                x = hand*xabs
                a, b = ((-24.5, -22.6) if side == "front" else (50.6, 52.5))
                cover["ops"].append(_yr(x, u, a, b, 3.05, mode="cut"))
                # The extended boss must retain a through clearance hole.
                a, b = ((-22.0, -20.1) if side == "front" else (48.3, 49.5))
                cover["ops"].append(_yr(x, u, a, b, 1.7, mode="cut"))
        cover["note"] += " Recessed M3 button screws now mount at u58 and u121 into captive frame nuts."
    result.extend(recipe["parts"])
    return result, recipe["metadata"]


def mounting_contract():
    removed_fin_area_mm2 = 0.0
    for x in (12.6, 13.4):
        offset = 16.0-x
        removed_fin_area_mm2 += 4 * (
            2*math.sqrt(max(0.0, 3.6**2-offset**2))*6.1
            + 2*math.sqrt(max(0.0, 3.0**2-offset**2))*3.2)
    return dict(
        status="Native-recipe mounting candidate; strength, preload, thread fit and assembly trials remain required.",
        coordinates="Unmirrored tibia-local x,y,z=-u, dimensions in mm.",
        motor_station_u_mm=list(MOTOR_STATIONS_U_MM), unchanged_frame_tie_u_mm=[50, 90],
        cover_station_u_mm=[58, 121],
        load_paths=[
            "Motor clamp front nut -> front/rear clamp lugs -> aluminium compression tube -> positive-frame boss -> washer -> M3x35 head.",
            "Rear clamp captive nut -> M3x5 screw -> continuous aluminium heat spine; four fasteners retain the spine.",
            "Front cover recessed screw -> extended cover boss -> frame pocket floor -> captive frame nut.",
            "Rear cover recessed screw -> cover boss -> aluminium stand-off -> positive frame -> captive nut."],
        assembly_sequence=[
            "Print the frame parts in a suitable Y direction and pause to insert the eight cover nuts before closing their axial retaining walls. Slicer orientation and pause layers must be planned from these pocket coordinates.",
            "Fit the four sink nuts into the open motor-facing pockets in the rear clamp halves before inserting the motor.",
            "Bolt the rear clamps to the spine with four M3x5 screws through its existing fin access bores.",
            "Place the motor between the clamp halves. Insert the four OD6 compression tubes between rear clamp pads and positive frame.",
            "Fit the four M3x35 screws from the rear with rail washers and front nuts. Tighten the clamp stations gradually while checking case alignment.",
            "Install the existing u50/u90 frame ties independently; their axes are unchanged.",
            "Check that the eight embedded cover nuts remain free of plastic in their threads. Seat the four rear aluminium stand-offs.",
            "Fit the front and rear covers using recessed M3 button screws. Removal uses one 2 mm hex key; internal nuts remain captive."],
        hand_tool_access=[
            "M3x35 heads: straight 2.5 mm hex-key approach from +Y with the rear cover removed; local fin clearance is included.",
            "Front clamp nuts: 5.5 mm spanner from the -Y side before fitting the front cover.",
            "M3x5 spine heads: straight 2.5 mm hex key through the four Ø5.8 fin bores before either cover is fitted.",
            "Cover heads: straight 2 mm hex key normal to each exterior face; recessed head bores are Ø6.1."],
        interfaces_to_validate=[
            "Motor case clamping remains a frictional interface. Confirm the manufacturer face-hole pattern before claiming positive motor torque/axial retention.",
            "The 0.6 mm clamp split closes under preload; the declared tubes support the frame gap without bridging that split.",
            "M3 threads are nominal engineering features represented by smooth bores and shanks; no thread holding-strength claim is made.",
            "Printed bosses and nut pockets require creep/preload checks. Recheck thermal fin area after the additional mounting access cuts."],
        embedded_cover_nut_pockets=dict(front_y_mm=[-18.4, -16.0], rear_y_mm=[37.2, 39.6],
                                       front_retaining_wall_mm=1.0, rear_retaining_wall_mm=1.0,
                                       process="Insert hex nuts during a planned print pause; pockets are closed in both axial directions."),
        thermal_area_adjustment=dict(additional_fin_area_removed_upper_bound_m2=removed_fin_area_mm2/1e6,
                                     remaining_fin_area_lower_bound_m2=0.02037043636363636-removed_fin_area_mm2/1e6,
                                     note="Arithmetic bound for the four rail-boss and screw-head access cuts; no CFD or thermal test."),
        cooling_alternative="Baseline preserved. Active cooling is a separate component-selection study after these mounting interfaces are validated.")


def active_cooling_screen():
    """Return a separate sourced blower screen; it changes no geometry or rating."""
    sink_area = 0.008
    flows_cfm = (0.5, 0.75, 1.0)
    rho, cp = 1.18, 1005.0
    # This is a proposed 28x40x1.5 mm base with ten 0.5x10x40 mm fins.
    proposed_sink_mass = (28*40*1.5 + 10*0.5*10*40) / 1000 * 2.7
    fan_power = 1.15
    airflow_cases = []
    for cfm in flows_cfm:
        flow = cfm * 0.00047194745
        capacity = rho * cp * flow
        velocity = flow / (160e-6)
        dynamic_pressure = 0.5 * rho * velocity**2
        airflow_cases.append(dict(assumed_delivered_flow_cfm=cfm,
                                 air_heat_capacity_rate_w_k=capacity,
                                 air_temperature_rise_at_7w_plus_fan_k=(7+fan_power)/capacity,
                                 velocity_in_160mm2_duct_m_s=velocity,
                                 pressure_loss_for_assumed_K5_to_K10_pa=[5*dynamic_pressure, 10*dynamic_pressure],
                                 note="Delivered flow and loss coefficients are scenarios; add unmeasured fin-channel friction."))
    return dict(
        status="Separate screening study; no active-cooling geometry or higher motor rating has been adopted.",
        supplier_candidate=dict(model="Delta BFB0305HHA-CF00", dimensions_mm=[30, 30, 10],
                                mass_g_ref=11, nominal_voltage_v=5, operating_voltage_v=[4.5, 5.5],
                                nominal_current_a=0.23, nominal_power_w=1.15, maximum_power_w=1.75,
                                free_air_flow_cfm=1.66, shutoff_pressure_pa=9.4*9.80665,
                                tachometer=True,
                                source="https://www.delta-fan.com/Download/Spec/BFB0305HHA-CF00.pdf",
                                source_product="https://www.delta-fan.com/products/bfb0305hha-cf00.html",
                                note="Free-air flow and shutoff pressure are separate endpoints, not one operating point."),
        tentative_mount_allocation_mm=dict(x=[-16, 16], y=[-11, 1], u=[54, 86],
                                           note=("32x32x12 mm allocation between the u50/u90 ties, in front of the motor. "
                                                 "A side-fed intake and outlet duct are needed. Supplier mounting holes, cable exit, "
                                                 "flow path and complete hardware clearance have not been checked.")),
        proposed_sink=dict(area_two_fin_faces_m2=sink_area, solid_mass_g=proposed_sink_mass,
                           base_mm=[28, 40, 1.5], fin_count=10, fin_mm=[0.5, 10, 40],
                           note="Concept dimensions only; no part recipe or mounting claim."),
        airflow_sensitivity=airflow_cases,
        film_temperature_rise_sensitivity=[dict(h_assumed_w_m2_k=h, at_5w_k=5/(h*sink_area),
                                                 at_7w_k=7/(h*sink_area)) for h in (30, 50, 80)],
        thermal_note=("h values are sensitivity assumptions. Add case/contact resistance and local bulk-air warming. "
                      "The published blower curve and measured duct resistance must determine delivered airflow. "
                      "Tach loss must force motor derating or shutdown; fan power comes from a suitable regulated 5 V rail."),
        mass_screen=dict(baseline_sink_g_rounded=33.3, proposed_sink_g=proposed_sink_mass,
                         blower_g=11, duct_and_mount_budget_g_assumed=4,
                         sink_only_net_saving_g_estimate=33.3-proposed_sink_mass-11-4,
                         note=("Saving more than 50 g cannot come from the roughly 33 g sink alone. "
                               "It also requires a lighter cover or changes to the approximately 17 g clamp assembly and its fixings.")),
        motor_data_caution=("The manufacturer's torque/speed/power rows do not reconcile exactly. The 5..7 W heat load at 1 A "
                            "remains a conservative screen, not a measured loss. Do not increase allowed motor performance from this study."))
