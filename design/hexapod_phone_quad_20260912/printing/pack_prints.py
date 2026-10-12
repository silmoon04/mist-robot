"""Pack already oriented coupon STL geometry. No machine profile or G-code."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
NS = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
ET.register_namespace('', NS)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def three_mf(path, placed):
    model = ET.Element(f'{{{NS}}}model', unit='millimeter')
    resources = ET.SubElement(model, f'{{{NS}}}resources')
    build = ET.SubElement(model, f'{{{NS}}}build')
    for i, (name, mesh) in enumerate(placed, 1):
        obj = ET.SubElement(resources, f'{{{NS}}}object', id=str(i), type='model', name=name)
        m = ET.SubElement(obj, f'{{{NS}}}mesh')
        vertices = ET.SubElement(m, f'{{{NS}}}vertices')
        for v in mesh.vertices:
            ET.SubElement(vertices, f'{{{NS}}}vertex', **dict(zip(('x','y','z'), (f'{x:.8f}' for x in v))))
        triangles = ET.SubElement(m, f'{{{NS}}}triangles')
        for f in mesh.faces:
            ET.SubElement(triangles, f'{{{NS}}}triangle', **dict(zip(('v1','v2','v3'), map(str, f))))
        ET.SubElement(build, f'{{{NS}}}item', objectid=str(i))
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels', '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model', ET.tostring(model, encoding='utf-8', xml_declaration=True))
    with zipfile.ZipFile(path) as z:
        doc = ET.fromstring(z.read('3D/3dmodel.model'))
        assert doc.attrib['unit'] == 'millimeter'
        assert len(doc.findall(f'.//{{{NS}}}object')) == len(placed)


def csv_file(path, fields, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


STRUCTURAL_COUPONS = {'r4_top_bridge_load_main','r4_top_bridge_load_aux','r4_post_staggered_nut_section'}


def coupon_stage(entry):
    selected = entry.get('mandatory',False) or entry['name'] in STRUCTURAL_COUPONS or entry['name']=='phone_usb_spine_6mm_coupon'
    return 'first_print' if selected else 'optional'


def run(manifest_path):
    manifest_bytes = manifest_path.read_bytes()
    source_hash = hashlib.sha256(manifest_bytes).hexdigest()
    manifest = json.loads(manifest_bytes)
    assert manifest['units'] == 'mm'
    source_dir = manifest_path.parent
    plates = []
    loaded = []
    for entry in manifest['coupons']:
        path = source_dir / entry['stl']
        mesh = trimesh.load_mesh(path, process=True)
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0, entry['name']
        mesh.apply_translation(-mesh.bounds[0])
        assert np.allclose(mesh.extents, entry['dimensions_mm'], atol=.04), entry['name']
        loaded.append((entry, mesh, sha(path)))
    # First-fit decreasing shelf packing, allowing only rotations about Z.
    loaded.sort(key=lambda x: (-max(x[1].extents[:2]), -np.prod(x[1].extents[:2]), x[0]['name']))
    for entry, original, digest in loaded:
        family = coupon_stage(entry)
        choice = None
        for pi, plate in enumerate(plates):
            if plate['family'] != family:
                continue
            for si, shelf in enumerate(plate['shelves']):
                for rot in (False, True):
                    w, h = original.extents[:2][::-1] if rot else original.extents[:2]
                    if h <= shelf['height'] + 1e-6 and shelf['x'] + w <= 215 + 1e-6:
                        choice = (pi, si, rot, w, h)
                        break
                if choice: break
            if choice: break
            y = max((s['y'] + s['height'] + 8 for s in plate['shelves']), default=0)
            possibilities = []
            for rot in (False, True):
                w, h = original.extents[:2][::-1] if rot else original.extents[:2]
                if w <= 215 and y + h <= 215: possibilities.append((h, rot, w))
            if possibilities:
                h, rot, w = min(possibilities)
                plate['shelves'].append(dict(y=y, height=h, x=0.0))
                choice = (pi, len(plate['shelves'])-1, rot, w, h)
                break
        if choice is None:
            w, h = original.extents[:2]
            rot = h > w
            if rot: w, h = h, w
            assert max(w,h) <= 215, entry['name']
            plates.append(dict(family=family, shelves=[dict(y=0.0, height=h, x=0.0)], parts=[]))
            choice = (len(plates)-1, 0, rot, w, h)
        pi, si, rot, w, h = choice
        shelf = plates[pi]['shelves'][si]
        mesh = original.copy()
        if rot:
            mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0,0,1]))
            mesh.apply_translation(-mesh.bounds[0])
        mesh.apply_translation([shelf['x'], shelf['y'], 0])
        plates[pi]['parts'].append((entry['name'], mesh, entry['stl'], digest))
        shelf['x'] += w + 8
    report = dict(status='Geometry plates only. Print coupons before production parts.',
                  units='mm', source_manifest_sha256=source_hash,
                  source_manifest=str(manifest_path.relative_to(ROOT)), spacing_mm=8,
                  packing_area_mm=[215,215], machine_bed_mm=[225,225], plates=[])
    report['coupon_selection'] = dict(first_print=sum(coupon_stage(e)=='first_print' for e in manifest['coupons']),
        optional=sum(coupon_stage(e)=='optional' for e in manifest['coupons']),available=len(loaded),
        reason='Mandatory R4 fits, phone USB spine and three section specimens needed before loading. Alternatives remain available.')
    plates.sort(key=lambda p: p['family'])
    for pi, plate in enumerate(plates, 1):
        name = f'coupon_plate_{pi:02}'
        parts = plate['parts']
        # Center the complete packing within the physical 225 mm bed.
        total = trimesh.util.concatenate([p[1] for p in parts])
        xy = total.extents[:2]
        delta = np.r_[(225-xy)/2, 0.0]
        for _, mesh, _, _ in parts: mesh.apply_translation(delta)
        for a in range(len(parts)):
            lo, hi = parts[a][1].bounds
            assert np.all(lo >= -1e-5) and np.all(hi[:2] <= 225+1e-5)
            for b in range(a):
                blo, bhi = parts[b][1].bounds
                gaps = np.maximum(lo[:2]-bhi[:2], blo[:2]-hi[:2])
                assert max(gaps) >= 8-1e-5, (parts[a][0],parts[b][0],gaps)
        stl = OUT / f'{name}.stl'
        three = OUT / f'{name}.3mf'
        total = trimesh.util.concatenate([p[1] for p in parts])
        total.export(stl)
        three_mf(three, [(p[0],p[1]) for p in parts])
        report['plates'].append(dict(name=name, family=plate['family'], bounds_mm=total.bounds.tolist(),
            stl=stl.name, stl_sha256=sha(stl), model_3mf=three.name, model_3mf_sha256=sha(three),
            parts=[dict(name=n, source_stl=s, source_sha256=d, bounds_mm=m.bounds.tolist()) for n,m,s,d in parts]))
    bom = []
    for e in manifest['print_parts']:
        production = trimesh.load_mesh(source_dir/e['stl'], process=True)
        assert production.is_watertight and production.is_winding_consistent and production.volume > 0, e['sku']
        assert np.isfinite(production.vertices).all() and np.isfinite(production.face_normals).all(), e['sku']
        assert np.allclose(production.extents, e['dimensions_mm'], atol=.04), e['sku']
        bom.append(dict(part=e['sku'],quantity=e['quantity'],
            X_mm=round(e['dimensions_mm'][0],3),Y_mm=round(e['dimensions_mm'][1],3),
            Z_mm=round(e['dimensions_mm'][2],3), source_stl='../cad/output/'+e['stl'],
            source_sha256=sha(source_dir/e['stl']), stage='Production after coupon and one-leg fit',
            supports_required=e.get('supports_required', e['sku'] in {
                'coxa_upper_and_hip_saddle', 'femur_main_and_knee_saddle',
                'tibia_curved_main_and_foot'}),
            note=e.get('supports','')))
    csv_file(OUT/'manufacturing_bom.csv', list(bom[0]), bom)
    coupon_rows = [dict(part=e['name'], quantity=1, stage=coupon_stage(e),source_mandatory=e.get('mandatory',False),
        selection_reason='Section specimen required before load tests' if e['name'] in STRUCTURAL_COUPONS else (
            'USB spine and plug check' if e['name']=='phone_usb_spine_6mm_coupon' else 'Source mandatory fit' if e.get('mandatory',False) else 'Alternative fit'),
        source_stl='../cad/output/'+e['stl'], source_sha256=sha(source_dir/e['stl']),
        note=e.get('note','')) for e in manifest['coupons']]
    csv_file(OUT/'coupon_bom.csv', list(coupon_rows[0]), coupon_rows)
    feedback = OUT/'coupon_feedback.csv'
    # Preserve operator measurements when plates are regenerated.
    if not feedback.exists():
        rows = [dict(part=e['name'], measurement='Fit and free motion',nominal='',measured='',
                     material='',layer_mm='',pass_fail='',notes='') for e in manifest['coupons']]
        for part, field, nominal in [
            ('C018','Case length / width / local face span','45.23 / 24.73 / 29 mm'),
            ('C018','Mounted main horn outer face from servo face','Provisional 4.5 mm'),
            ('C018','Mounted auxiliary disc outer face from servo face','Provisional 4.5 mm'),
            ('C018','Auxiliary disc free rotation after retention','No binding'),
            ('C018','Clamp cap contacts case before closure shoulders','Contact, no lift'),
            ('C018','Connector plug insertion and swept cable bend','Unmeasured'),
            ('phone_pan_hub','M3x6 washer thickness / OD / engagement','0.5 / <=6 / 2 mm'),
            ('yaw_auxiliary_spacer','R3 M3x20 auxiliary thread engagement','2 mm with two OD6 x 0.5 mm washers'),
            ('Mi9SE','Phone long side / thickness / short side','147.5 / 7.45 / 70.5 mm'),
            ('Mi9SE','Camera bump / USB plug / screen edge clearance','Unmeasured'),
            ('electronics','PDB / ESP32 / interface / UBEC actual envelopes','Unmeasured'),
            ('assembled_leg','Mass / torque-off sweep / screw clearance','Unmeasured')]:
            rows.append(dict(part=part,measurement=field,nominal=nominal,measured='',material='',layer_mm='',pass_fail='',notes=''))
        csv_file(feedback,list(rows[0]),rows)
    with feedback.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        feedback_fields = reader.fieldnames
        feedback_rows = list(reader)
    feedback_changed = False
    current_names = {e['name'] for e in manifest['coupons']}
    for row in feedback_rows:
        if row['part'].startswith('coupon_') and row['part'] not in current_names:
            if 'Historical R3 coupon' not in row['notes']:
                row['notes']=('Historical R3 coupon; use current R4 datum and interfaces. '+row['notes']).strip()
                feedback_changed=True
        if row['part'].startswith('phone_fit_') and row['part'] not in current_names:
            if 'Superseded R2 retainer' not in row['notes']:
                row['notes'] = ('Superseded R2 retainer; R3 uses two short clips. '+row['notes']).strip()
                feedback_changed = True
        if (row['part'] == 'yaw_auxiliary_spacer' and row['measurement'] == 'M3x16 auxiliary thread engagement'
                and not row['measured'] and not row['pass_fail']):
            row['measurement'] = 'R3 M3x20 auxiliary thread engagement'
            row['nominal'] = '2 mm with two OD6 x 0.5 mm washers'
            feedback_changed = True
    for entry in manifest['coupons']:
        if not any(row['part'] == entry['name'] for row in feedback_rows):
            feedback_rows.append(dict(part=entry['name'], measurement='Fit and controlled fixture response',
                nominal='', measured='', material='', layer_mm='', pass_fail='', notes=entry.get('note','')))
            feedback_changed = True
    for part, measurement, nominal in [
        ('R4_bridge','M3x50 external nut and two washers; tip emergence','49.4 mm stack / 0.6 mm emergence'),
        ('R4_post','Opposite staggered nut slots and lower-arm screw access','M3x20; no forced insertion'),
        ('R4_pan_cap','Side-loaded plain nuts and retained roof under preload','Roof 2.9 mm; no lift or crack'),
        ('phone_usb_spine_6mm_coupon','Side plug fit / bending / residual set','6 x 8 mm residual spine'),
        ('R4_leg_fixture','Force / lever / tip displacement / twist / residual set','Record both lateral directions'),
        ('R4_clamp','Creep after one hour and one day / measured temperature','No established warm allowable'),
        ('R4_full_coxa_fixture','Vertical force at hip / reversing Y torque / upper and lower frame response','Hip X50, post near X32; include access cut at Z=-25'),
        ('R4_pitch_auxiliary','M3x8 with TWO thin washers / actual tip margin / free rotation','1.1 mm land, 1.9 mm engagement, 0.2 mm nominal rear margin'),
        ('R4_auxiliary_retainer','OD7 centre washer / stub seating / free disc axial movement','0.7 mm nominal disc-to-washer gap; verify PA pilot depth')]:
        if not any(row['part']==part and row['measurement']==measurement for row in feedback_rows):
            feedback_rows.append(dict(part=part,measurement=measurement,nominal=nominal,measured='',
                material='',layer_mm='',pass_fail='',notes=''))
            feedback_changed = True
    for row in feedback_rows:
        if not row['measured'] and not row['pass_fail']:
            if row['part']=='C018' and row['measurement']=='Case length / width / local face span':
                row['nominal']='45.23 / 24.73 / 29 mm; axis offset 12.5 mm from CASE MIDPOINT'
                feedback_changed=True
            if row['part']=='C018' and row['measurement']=='Mounted auxiliary disc outer face from servo face':
                row['nominal']='3.4 mm from auxiliary face, outer face servo Z=-32.4; verify seating'
                feedback_changed=True
            if row['part']=='yaw_auxiliary_spacer' and 'thread engagement' in row['measurement']:
                row['measurement']='R4 M3x20 auxiliary thread engagement'
                row['nominal']='1.9 mm with TWO OD6 x 0.5 mm washers, 3.5 mm counterbore and 11.6 mm spacer'
                feedback_changed=True
        if (row['part'] == 'Mi9SE' and row['measurement'] == 'Bare phone width / thickness / height'
                and not row['measured'] and not row['pass_fail']):
            row['measurement'] = 'Phone long side / thickness / short side'
            row['nominal'] = '147.5 / 7.45 / 70.5 mm'
            feedback_changed = True
    landscape_measurement = 'Landscape mounted width / thickness / height'
    if not any(r['measurement'] == landscape_measurement for r in feedback_rows):
        feedback_rows.append(dict(part='Mi9SE', measurement=landscape_measurement,
            nominal='147.5 / 7.45 / 70.5 mm', measured='', material='', layer_mm='',
            pass_fail='', notes='Screen upright; USB exits beside the short edge while parked.'))
        feedback_changed = True
    if feedback_changed:
        csv_file(feedback, feedback_fields, feedback_rows)
    assert sha(manifest_path) == source_hash, 'CAD regenerated during packing; run again.'
    slicing_path=ROOT/'manufacturing/slicing_r4/output/PRODUCTION_SLICING.md'
    current_slicing=slicing_path.exists() and source_hash in slicing_path.read_text(encoding='utf-8')
    report['validation'] = dict(coupon_meshes_watertight=len(loaded),
        production_meshes_watertight=len(bom), production_piece_quantity=sum(e['quantity'] for e in bom),
        positive_volumes=True, winding_consistent=True, finite_vertices_and_normals=True,
        dimensions_match_manifest=True, minimum_bbox_spacing_mm=8,
        model_3mf_object_count_checked=True, physical_fit_verified=False,
        coupon_plates_machine_sliced=False, production_analysis_sliced=current_slicing,
        printer_calibration_verified=False, loaded_robot_tested=False,
        next_step='Slice coupon geometry with the actual printer profile, print and record measurements.')
    report['packer_source_sha256'] = sha(Path(__file__))
    report['production_slicing_report'] = str(slicing_path.relative_to(ROOT)) if current_slicing else None
    report['production_slicing_report_sha256'] = sha(slicing_path) if current_slicing else None
    if not (OUT/'INTERFACE_REVIEW_HOLD.txt').exists():
        first_fit=OUT/'FIRST_FIT_CHECKS.txt'
        assert first_fit.exists() and source_hash in first_fit.read_text(encoding='utf-8'), 'First-fit disposition must match the current CAD review.'
        report['first_fit_notice']=first_fit.name
        report['first_fit_notice_sha256']=sha(first_fit)
    assert len(coupon_rows)==28 and sum(r['stage']=='first_print' for r in coupon_rows)==16
    (OUT/'plate_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    first = [p for p in report['plates'] if p['family']=='first_print']
    optional = [p for p in report['plates'] if p['family']=='optional']
    quick = '\n'.join([
        'R4 FIRST PRINT: CORRECTED DATUM AND INWARD KNEE', '',
        'Read FIRST_FIT_CHECKS.txt for the controlled first-fit disposition and remaining physical gates.',
        '1. Open '+', '.join(p['model_3mf'] for p in first)+' in your Neptune 4 Pro slicer.',
        '   These are 13 fit pieces plus three section specimens required before loading.',
        '   Keep millimetres, orientation and plate positions.',
        '   The 3MF files contain geometry only. They do not contain a machine profile or G-code.',
        '2. Use 0.4 mm nozzle, 0.20 mm layers, 0.42 mm lines, five walls, six top/bottom layers',
        '   and 35% gyroid. Start PLA at 210/60 C within the filament maker\'s range.',
        '   Cap flow at 8 mm3/s. Check supports under raised sections and the phone tray rear plate.',
        '   Read PRINT_AND_ASSEMBLE.md for support settings and inspect every first unsupported layer.',
        '3. Print the nominal 0.3 mm case fit and reuse its single cap for alternative end gaps.',
        '   Preload clamp nuts into bare carriers before servos/caps; hip-front nuts use staged side entry.',
        '   Use the nominal 0.5 mm landscape phone tray with TWO SHORT CLIPS, not the old long bar.',
        '4. Clamp the real servo and use the case-to-shaft registration plate with its metal horn.',
        '   The output axis is 12.5 mm from the CASE MIDPOINT. Verify this fit before a whole leg.',
        '   Assemble horn/auxiliary fits and the three R4 section coupons. Use real metal discs.',
        '   Have M3x35 clamp screws, M3x50 external bridge bolts, plain M3 nuts and OD7 washers.',
        '   Pitch auxiliary screws are M3x8 with TWO OD6 x 0.5 mm washers and integral 1.1 mm lands.',
        '   Yaw uses M3x20, TWO OD6 x 0.5 mm washers, 3.5 mm counterbores and 11.6 mm spacers.',
        '   Each auxiliary center retainer also needs the specified OD7 washer against the fixed stub.',
        '   After initial fit, print the full production coxa_upper_and_hip_saddle.stl and lower arm',
        '   coxa_lower_auxiliary_arm.stl for the frame load test. The cropped post misses the Z=-25 access cut.',
        '5. Record results in coupon_feedback.csv. Stop on binding, roof lift, cracking or permanent set.',
        '   Use captured fixtures and a dummy phone; follow the incremental force/deflection loop',
        '   in PRINT_AND_ASSEMBLE.md before any full robot run. No full strength certificate exists.',
        '6. Only if a nominal fit needs adjustment, print individual alternatives from coupon_bom.csv',
        '   or the complete optional set: '+', '.join(p['model_3mf'] for p in optional)+'.',
        '   The twelve optional pieces include two duplicate caps that can normally be omitted.',
        '', 'All 28 coupons remain available. manufacturing_bom.csv lists the current production quantities.',
        'Consult the current R4 production slicing report for material and time totals when available.',
        'R3 mass, support and time estimates are historical and do not qualify the corrected geometry.',
        'Use the slicer\'s time for the actual coupon plate. Infill percentage is not a mass fraction.',
        'The phone stays landscape and upright. Park pan before charging through a short-side USB opening.',
        'Source CAD manifest SHA-256: '+source_hash, ''])
    if (OUT/'INTERFACE_REVIEW_HOLD.txt').exists():
        quick='INTERFACE REVIEW: read INTERFACE_REVIEW_HOLD.txt. Independent R4 interface checks are still being finalized.\n\n'+quick
    (OUT/'PRINT_FIRST.txt').write_text(quick,encoding='utf-8')
    for guide in ('PRINT_AND_ASSEMBLE','WIRING'):
        (OUT/(guide+'.txt')).write_text((OUT/(guide+'.md')).read_text(encoding='utf-8'),encoding='utf-8')
    # Only retire plate files this script owns, after all new geometry passes.
    for prior in OUT.iterdir():
        match = re.fullmatch(r'coupon_plate_(\d+)\.(3mf|stl)', prior.name)
        if match and int(match.group(1)) > len(plates):
            assert prior.resolve().parent == OUT.resolve()
            prior.unlink()
    print(json.dumps(dict(plates=len(plates),coupons=len(loaded),production_skus=len(bom),source_manifest_sha256=source_hash)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, default=ROOT/'cad/output/assembly_manifest.json')
    run(parser.parse_args().manifest.resolve())
