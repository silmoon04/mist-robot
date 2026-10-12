"""Compare actual STL net sections of the R4 and straight R5 lower legs."""

from pathlib import Path
import hashlib
import importlib.util
import json
import math

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
R5 = HERE.parents[1]
R4 = R5.parent / 'hexapod_phone_quad_20260912'
PRODUCER = R4 / 'manufacturing/strength/reassess_r4.py'
spec = importlib.util.spec_from_file_location('r4_section_integrator', PRODUCER)
integrator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(integrator)
CUTS = [11, 20, 25, 30, 40, 50, 60, 80, 95, 100]
PARTS = ['tibia_curved_main_and_foot', 'tibia_auxiliary_cheek']


def checked_section(name, x, region=None):
    mesh = integrator.CACHE[name]
    if not mesh.bounds[0, 0] < x < mesh.bounds[1, 0]:
        return dict(cut_mm=float(x), section_present=False)
    try:
        result = integrator.section(name, 0, float(x), region)
    except (AttributeError, IndexError, ZeroDivisionError, ValueError):
        return dict(cut_mm=float(x), section_present=False)
    assert result['area_mm2'] > 0
    assert all(math.isfinite(z) and z > 0 for z in result['section_modulus_transverse_mm3'])
    result['section_present'] = True
    result['Z_about_y_mm3'], result['Z_about_z_mm3'] = result['section_modulus_transverse_mm3']
    return result


def minima(rows):
    present = [s for s in rows if s['section_present']]
    return {key: dict(value=s[key], cut_mm=s['cut_mm'])
            for key in ('area_mm2', 'Z_about_y_mm3', 'Z_about_z_mm3')
            for s in [min(present, key=lambda s: s[key])]}


def main():
    all_data = {}
    for revision, folder, prefix in [('R4', R4/'cad/output/parts_mesh', 'FL_'),
                                     ('R5 straight candidate', HERE, '')]:
        integrator.MESH = folder
        integrator.CACHE = {}
        parts = {}
        for part in PARTS:
            name = prefix + part
            path = folder / (name + '.stl')
            mesh = trimesh.load_mesh(path)
            integrator.CACHE[name] = mesh
            scan_end = min(100, math.floor(mesh.bounds[1, 0] * 2 - 1) / 2)
            rows = [checked_section(name, x) for x in CUTS]
            sweep = [checked_section(name, x) for x in np.arange(11, scan_end + .01, .5)]
            parts[part] = dict(source_path=str(path), source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                               watertight=bool(mesh.is_watertight), winding_consistent=bool(mesh.is_winding_consistent),
                               connected_mesh_components=len(mesh.split(only_watertight=False)),
                               bounds_mm=mesh.bounds.tolist(), volume_mm3=float(mesh.volume),
                               solid_PLA_mass_g=float(mesh.volume)*.00124,
                               selected_sections=rows, full_part_sweep=sweep,
                               full_part_sweep_minima=minima(sweep))
            if part == PARTS[0]:
                # Both versions have the same main-cheek position. This crop
                # prevents the central bridge from hiding the thin root strip.
                root_rows = [checked_section(name, x, [14.99, -100, 23.01, 100])
                             for x in np.arange(11, 32, .5)]
                parts[part]['common_main_cheek_root_sweep'] = root_rows
                parts[part]['common_main_cheek_root_minima'] = minima(root_rows)
        all_data[revision] = dict(parts=parts,
                                 total_solid_PLA_mass_g=sum(p['solid_PLA_mass_g'] for p in parts.values()))
    old, new = all_data.values()
    comparisons = []
    for part in PARTS:
        for a, b in zip(old['parts'][part]['selected_sections'], new['parts'][part]['selected_sections']):
            row = dict(part=part, cut_mm=a['cut_mm'], R4_present=a['section_present'], R5_present=b['section_present'])
            if a['section_present'] and b['section_present']:
                for metric in ('area_mm2', 'Z_about_y_mm3', 'Z_about_z_mm3'):
                    row[metric] = dict(R4=a[metric], R5=b[metric], ratio_R5_over_R4=b[metric]/a[metric])
            comparisons.append(row)
    result = dict(status='pass' if all(p['watertight'] and p['winding_consistent']
                                      for v in all_data.values() for p in v['parts'].values()) else 'fail',
                  scope='Geometric net-section comparison of the R4 and straight R5 candidate lower leg. No material failure simulation.',
                  producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  section_integrator_sha256=hashlib.sha256(PRODUCER.read_bytes()).hexdigest(),
                  coordinate_convention='Longitudinal axis X runs from knee centre 0 to toe centre 105 mm. Sections lie in YZ. Bending about Y loads the leg side profile; bending about Z applies lateral bending.',
                  method='Trimesh plane cuts with Shapely polygon integration. Holes subtract area. Unsymmetric elastic section modulus uses the complete 2 by 2 second-moment tensor and extreme actual polygon vertices.',
                  assumptions=['Solid geometry is used for the section and mass comparison. PLA density is 1.24 g/cm3 for volume-based mass only.',
                               'The independent auxiliary cheek is not combined with the main piece as a bonded cross section.',
                               'No infill, layer adhesion, creep, bolt contact, preload or actual load sharing is modeled.',
                               'Full-part minima occur at different physical locations and cannot be compared as a failure margin without a bending-moment diagram.',
                               'The thin main-cheek root remains sensitive to lateral bending. A straight distal shank does not resolve uncertain sharing between the two shaft-support cheeks.',
                               'The bridge moves closer to the knee and the auxiliary cheek is shorter. These changes contribute to the section differences, so this is not an isolated comparison of straight versus curved centreline.',
                               'Scan interval is 0.5 mm. Local stress concentrations and unsampled narrower features are not resolved.'],
                  revisions=all_data, selected_comparison=comparisons,
                  total_solid_PLA_mass_delta_g=new['total_solid_PLA_mass_g']-old['total_solid_PLA_mass_g'])
    lines = [result['scope'], '', result['coordinate_convention'], '',
             f"Watertight and consistent winding: {result['status']}.",
             f"Both printed parts per leg, solid PLA estimate: R4 {old['total_solid_PLA_mass_g']:.3f} g; R5 {new['total_solid_PLA_mass_g']:.3f} g; change {result['total_solid_PLA_mass_delta_g']:+.3f} g.", '',
             'Selected complete-part net sections. A is mm2; Zy and Zz are mm3.',
             'part, x mm, R4 A, R5 A, R4 Zy, R5 Zy, R4 Zz, R5 Zz']
    for row in comparisons:
        label = 'main' if row['part'] == PARTS[0] else 'auxiliary'
        if not row['R4_present'] or not row['R5_present']:
            lines.append(f"{label}, {row['cut_mm']:g}, R4 present {row['R4_present']}, R5 present {row['R5_present']}")
            continue
        numbers = [row[m][r] for m in ('area_mm2', 'Z_about_y_mm3', 'Z_about_z_mm3') for r in ('R4', 'R5')]
        lines.append(f"{label}, {row['cut_mm']:g}, " + ', '.join(f'{n:.3f}' for n in numbers))
    lines += ['', 'Isolated main-cheek root minima, common x range 11 to 31.5 mm.']
    for label, data in all_data.items():
        mn = data['parts'][PARTS[0]]['common_main_cheek_root_minima']
        lines.append(label + ': ' + '; '.join(f"{key} {value['value']:.3f} at x {value['cut_mm']:g} mm" for key, value in mn.items()))
    lines += ['', 'Complete-part sweep minima, x=11 mm to x=100 mm or 0.5 mm before the part end.']
    for label, data in all_data.items():
        for part, properties in data['parts'].items():
            mn = properties['full_part_sweep_minima']
            lines.append(label + ', ' + part + ': ' + '; '.join(f"{key} {value['value']:.3f} at x {value['cut_mm']:g} mm" for key, value in mn.items()))
    lines += ['',
              'In the common main-cheek root window, R5 has larger sampled minimum net area and section moduli. This does not make every cut stronger: at x=11 mm, both moduli are smaller; at the x=100 mm foot-strap cut, R5 has a smaller section in both bending directions.',
              'The foot-end reduction is far from the knee and normally has a shorter external-force lever arm. A final load-specific check must apply the actual moment at each cut before deciding whether it matters.',
              'Neither the curved nor straight main part introduces an extra joint. The separate short auxiliary cheek supports the opposite shaft and permits assembly.']
    lines += ['', 'Interpretation limits:', *[f'* {s}' for s in result['assumptions']], '', result['method']]
    (HERE/'section_comparison.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    (HERE/'section_comparison.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
