"""Dependency-free polygon outlines for external, unshifted involute spur gears."""

import math


def involute_spur_points(teeth, module=1.0, pressure_angle_deg=20,
                         backlash_mm=0.12, phase_deg=0, samples=5):
    """Return an unclosed, counterclockwise list of XY points in millimetres.

    Standard full-depth proportions give pitch radius m*z/2, base radius
    pitch*cos(alpha), addendum radius pitch+m and root radius pitch-1.25*m.
    The involute of the base circle is (rb*(cos(t)+t*sin(t)),
    rb*(sin(t)-t*cos(t))). Its radius is rb*sqrt(1+t*t), and its polar
    angle is t-atan(t). Mirroring and rotating this curve makes the flanks;
    at the pitch circle each tooth has arc thickness pi*m/2-backlash_mm.
    Thus backlash_mm removes that much thickness from THIS gear; using it
    on both mating gears gives twice that nominal tangential clearance.

    ``samples`` is the number of segments per flank and per circular arc.
    Below the base circle, a radial segment joins the flank to the root.
    This omits cutter-generated root fillets and low-tooth-count undercut.
    Phase zero puts a tooth centre on +X. For two gears with centres on +X,
    use phases 0 and 180+180/z2 degrees, and centre distance m*(z1+z2)/2.
    Additional rotation theta on gear 1 requires -theta*z1/z2 on gear 2.
    """
    if isinstance(teeth, bool) or int(teeth) != teeth or teeth < 3:
        raise ValueError("teeth must be an integer of at least 3")
    if isinstance(samples, bool) or int(samples) != samples or samples < 2:
        raise ValueError("samples must be an integer of at least 2")
    teeth, samples = int(teeth), int(samples)
    module, pressure_angle_deg, backlash_mm, phase_deg = map(
        float, (module, pressure_angle_deg, backlash_mm, phase_deg))
    if not all(math.isfinite(value) for value in (
            module, pressure_angle_deg, backlash_mm, phase_deg)):
        raise ValueError("gear dimensions and angles must be finite")
    if module <= 0 or not 0 < pressure_angle_deg < 90 or backlash_mm < 0:
        raise ValueError("module must be positive, angle in (0, 90), backlash nonnegative")

    pitch = module * teeth / 2.0
    base = pitch * math.cos(math.radians(pressure_angle_deg))
    tip = pitch + module
    root = pitch - 1.25 * module
    half_thickness = (math.pi * module / 2.0 - backlash_mm) / (2.0 * pitch)
    if half_thickness <= 0:
        raise ValueError("backlash removes the entire tooth")
    pitch_t = math.tan(math.radians(pressure_angle_deg))
    pitch_involute = pitch_t - math.atan(pitch_t)
    start_radius = max(base, root)
    start_t = math.sqrt(max(0.0, (start_radius / base) ** 2 - 1.0))
    tip_t = math.sqrt((tip / base) ** 2 - 1.0)
    flank = []
    for index in range(samples + 1):
        parameter = start_t + (tip_t - start_t) * index / samples
        radius = base * math.sqrt(1.0 + parameter * parameter)
        half_angle = half_thickness + pitch_involute - (
            parameter - math.atan(parameter))
        flank.append((radius, half_angle))
    tooth_pitch = 2.0 * math.pi / teeth
    if flank[-1][1] <= 0 or flank[0][1] >= tooth_pitch / 2.0:
        raise ValueError("parameters produce pointed tips or overlapping tooth roots")

    phase = math.radians(phase_deg % 360.0)
    outline = []
    for tooth in range(teeth):
        centre = phase + tooth * tooth_pitch
        # Walk the negative-angle flank outward, then the positive flank inward.
        polar = []
        if root < base:
            polar.append((root, centre - flank[0][1]))
        polar.extend((radius, centre - angle) for radius, angle in flank)
        tip_half_angle = flank[-1][1]
        polar.extend((tip, centre - tip_half_angle +
                      2.0 * tip_half_angle * index / samples)
                     for index in range(1, samples + 1))
        polar.extend((radius, centre + angle) for radius, angle in reversed(flank[:-1]))
        if root < base:
            polar.append((root, centre + flank[0][1]))
        root_start = centre + flank[0][1]
        root_gap = tooth_pitch - 2.0 * flank[0][1]
        # The next tooth supplies the arc endpoint; do not repeat it here.
        polar.extend((root, root_start + root_gap * index / samples)
                     for index in range(1, samples))
        outline.extend((radius * math.cos(angle), radius * math.sin(angle))
                       for radius, angle in polar)
    return outline
