"""Analytic mass, frame, inertia and G-code mode checks for deposited paths."""
import json
import math
from pathlib import Path
import numpy as np
from deposition_properties import parse_gcode


def run():
    tests = []
    baseline = "G90\nM82\nG92 E0\nG0 X0 Y0 Z0.2\n;TYPE:WALL-OUTER\nG1 X10 E1 F600\n"
    d = parse_gcode(baseline)
    m = math.pi*(1.75/2)**2*1.24e-6
    p = d["properties"]["model"]
    assert math.isclose(p["mass_kg"], m, rel_tol=1e-12)
    assert np.allclose(p["com_mm"], [5,0,.1])
    assert np.allclose(p["inertia_line_about_com_kg_m2"], np.diag([0,m*100/12*1e-6,m*100/12*1e-6]), atol=1e-18)
    tests.append("10 mm straight rod mass, COM and analytic inertia")
    t = np.eye(4); t[:3,3] = [-100,-80,0]
    translated = baseline.replace("X0 Y0", "X100 Y80").replace("X10 E1", "X110 E1")
    p2 = parse_gcode(translated,t)["properties"]["model"]
    assert np.allclose(p2["com_mm"], p["com_mm"])
    assert np.allclose(p2["inertia_line_about_com_kg_m2"], p["inertia_line_about_com_kg_m2"], atol=1e-18)
    tests.append("STL-to-machine translation is removed from COM and inertia")
    rotation = np.eye(4); rotation[:3,:3] = [[0,1,0],[-1,0,0],[0,0,1]]
    rotated = baseline.replace("G1 X10", "G1 Y10")
    p3 = parse_gcode(rotated,rotation)["properties"]["model"]
    assert np.allclose(p3["com_mm"], p["com_mm"])
    assert np.allclose(p3["inertia_line_about_com_kg_m2"], p["inertia_line_about_com_kg_m2"], atol=1e-18)
    tests.append("Rotated frame transforms segment inertia correctly")
    mixed = baseline+"G1 E0.5\nG92 E0\nM83\nG1 E0.5\nG1 X20 E1\nG91\nG1 X10 E1\nM82\nG1 X10 E3.5\nG90\nG92 X0 E0\nG1 X10 E1\n"
    q = parse_gcode(mixed)
    assert math.isclose(q["properties"]["model"]["mass_kg"],5*m,rel_tol=1e-12),q
    assert np.allclose(q["properties"]["model"]["com_mm"],[25,0,.1]),q
    assert math.isclose(q["extrusion_accounting"]["repaid_retraction_filament_mm"],.5)
    tests.append("M82/M83, G90/G91, G92 XYZ/E and stationary retraction recovery")
    kinds = baseline+";TYPE:SUPPORT\nG1 X20 E2\n;TYPE:SUPPORT-INTERFACE\nG1 X30 E3\n;TYPE:SKIRT\nG1 X40 E4\n;TYPE:FILL\nG1 X50 E5\n"
    q = parse_gcode(kinds)
    assert math.isclose(q["properties"]["model"]["mass_kg"],2*m)
    assert math.isclose(q["properties"]["support"]["mass_kg"],2*m)
    assert math.isclose(q["properties"]["adhesion"]["mass_kg"],m)
    tests.append("Support, interface and skirt are excluded from model properties")
    moving_recovery = baseline+"G1 E0\nG1 X30 E2\n"
    q = parse_gcode(moving_recovery)
    assert math.isclose(q["properties"]["model"]["mass_kg"],2*m)
    assert np.allclose(q["properties"]["model"]["com_mm"],[15,0,.1])
    tests.append("Moving recovery deposits only its fresh-material tail")
    for invalid in ("G20", "M200 D1.75", "G2 X20 E2", "G2 X20", "G1 X20 Z.4 E2", "T1"):
        try:
            parse_gcode(baseline+invalid+"\n")
        except ValueError:
            continue
        raise AssertionError(invalid)
    tests.append("Unsupported units, volumetric E, arcs and extruding Z moves fail explicitly")
    for bad in (np.diag([1.,1.,1.,2.]), np.array([[1,0,0,float('nan')],[0,1,0,0],[0,0,1,0],[0,0,0,1]])):
        try:
            parse_gcode(baseline,bad)
        except ValueError:
            continue
        raise AssertionError("Malformed frame accepted")
    tests.append("Malformed homogeneous transforms fail explicitly")
    receipt = dict(result="pass", test_count=len(tests), tests=tests,
                   references=["https://marlinfw.org/docs/gcode/M082.html", "https://marlinfw.org/docs/gcode/G092.html"])
    (Path(__file__).parent/"parser_test_results.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    run()
