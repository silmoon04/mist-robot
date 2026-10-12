import json,hashlib,math
from pathlib import Path
root=Path.cwd();folder=root/'cad'/'leg_proximal_20260907';out=folder/'output_candidate'
r=json.loads((out/'leg_geometry_report.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(out/'leg_geometry_report.json')=='6eb16f526239fcb64b52d29b171c6e0a213683a6cd7da0355804a2b4689871c0'
links=r['link_mass_properties']
contract={k:{'mass_kg':v['mass_kg'],'com_local_m':v['com_local_m'],'inertia_com_local_kg_m2':v['inertia_com_local_kg_m2']} for k,v in links.items()}
(out/'link_mass_contract.json').write_text(json.dumps({'source_report_sha256':sha(out/'leg_geometry_report.json'),'link_mass_properties':contract},indent=2))
files=[folder/'proximal_leg.py',folder/'retention_recipe.py',folder/'export_proximal.py',folder/'inertia_report.py',out/'parameters_used.json',out/'leg_geometry_report.json',out/'MIST_proximal_robot_candidate.step',out/'MIST_proximal_robot_candidate.glb',root/'coupons'/'bed1_proximal_20260907'/'interface_contract.json']
manifest={str(p.relative_to(root)):sha(p) for p in files}
(out/'artifact_hashes.json').write_text(json.dumps(manifest,indent=2))
rows=[]
for key in ('base_link','FL_yaw','FL_femur','FL_tibia','FL_wheel'):
 v=links[key];rows.append(f"| {key} | {v['mass_kg']:.6f} | "+', '.join(f'{x*1000:.3f}' for x in v['com_local_m'])+' |')
text='''# Proximal-femur knee-drive candidate

The new knee servo housing moves with the femur and reacts its torque into the femur cartridge. A 25:50 spur stage drives equal 32-tooth belt pulleys. The resulting coordinate contract is `s = [2*yaw, 2*hip, 2*knee]`. This is a physical change from the carriage-mounted absolute-tibia drive, not a software-only matrix change.

The full recorded drive pose contains **657 valid single solids**. OpenCascade considered **215,496 part pairs**, reporting **zero positive-volume intersections above 0.01 mm3, zero Boolean failures and zero shape-check issues**. These results establish this pose only. The report and geometry are frozen; the previous 577-part candidate was preserved.

The estimated total is **7.108160 kg**, comprising 6.658160 kg assigned to exported geometry and 0.450 kg added once for electronics, harness and unmatched hardware. Printed parts account for **2.829003 kg**; the FL leg has about **507.603 g** of fully solid printed material, compared with 415.236 g in the previous candidate. The new cartridge is 121.61 cm3 of printed geometry before infill. This revision did not achieve a mass reduction.

Per-part tensors use the OpenCascade solid COM tensor, scaled to the assigned material or manufacturer mass. Tensors are in kg m2; link COM coordinates below are millimetres in the corresponding simulator link axes. Hardware envelopes, solid-print masses and the 450 g supplemental allocations are estimates. Internal transmission rotors remain lumped into their enclosing simulator links.

| Link | Mass kg | Local COM x, y, z mm |
|---|---:|---|
'''+ '\n'.join(rows)+'''

Left/right geometry uses local Y signs `[+1, -1, -1, +1]` for FL, FR, RL, RR. The actual knee-servo case COM is `(0, hand*69.125, -47.615)` mm in the femur frame. The common hip-to-knee distance remains 139.5 mm, and the selected belt remains Gates 375-3MGT-09 with 32:32 pulleys and a 9 mm width.

A 10 mm steel spacer bridge moves the input spur stage clear of the fixed yaw servo. The input pulley remains at Y14.125..28.125, the metal gear occupies Y38.125..46.125, and the input bearings occupy Y5..12 and Y52.325..59.325. Four M4x25 screws give 7 mm nominal engagement into the proposed 8 mm pulley taps. The part identifiers inherited from the retention module still contain `M4x14`; their emitted note and actual geometry specify M4x25. The knee adapter continues to use M4x14. Neither supplier machining acceptance nor torque rating is established here.

The nominal input shaft is 7 mm steel with M3 axial retention, steel washers and spacers. The knee axle remains 8 mm. The rendered threaded bores show the M3 major diameter to prevent false overlap with the simplified screw shanks; the machining operation uses the separately documented 2.5 mm tap drill. A controlled endfloat scheme is proposed, not measured.

The first fit-bed contract is embedded and hashed in the report. The new input carriers use OD34, a 22.4 mm straight seat 7.2 mm deep, a 1.2 mm floor and a 20 mm through aperture, with no lead-in. Keepers are OD34/ID20/t2.4 with M3 clearance holes at x=+/-14. The left cup is reversed about its bearing center to clear the pulley. The fixed jack bridge has an explicit side opening into the steel load-plate pocket; a retaining side cover is still missing.

This is not a first-leg print or load release. The remaining defects and gates are concrete:

- The retained yaw and hip 20T printed pinions have the previously identified weak horn-hole web and tooth-strength problem.
- The new metal 25:50 gears, custom 7 mm output bore and face-drilled GT pulleys remain conditional manufacturing choices.
- The printed knee adapter has only 0.6 mm between its central bore and sleeve seats; the narrow knee spacer neck has a 0.2 mm radial wall. Both need redesign or qualification.
- Keeper screws, lower slider nuts and washers, the jack side cover, controlled motor-case preload and horn mounting screws are incomplete hardware details.
- The thick carriage, bridge and case support need stiffness, creep, print-orientation and fatigue work. The mass increase is material to the actuator limits.
- Only the nominal locked cartridge position was checked. Installation travel, continuous yaw/hip/knee clearance, cables and tool access through motion are not certified.
- The recipe does not itself create native motion joints; the separate reviewed native replay and motion helper own that step.

The Python/CadQuery process returned exit code 1 after completing its outputs without a traceback, consistent with the independently observed runtime teardown issue. Artifact completion and geometry checks are recorded separately from process status.
'''
(out/'README.md').write_text(text)
print(json.dumps({'report_sha256':sha(out/'leg_geometry_report.json'),'mass_kg':r['physical_mass_properties']['assigned_mass_kg'],'parts':len(r['parts']),'links':len(links)},indent=2))
