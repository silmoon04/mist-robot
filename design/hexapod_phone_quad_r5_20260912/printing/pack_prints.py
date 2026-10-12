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


STRUCTURAL_COUPONS = {'r4_top_bridge_load_main','r4_top_bridge_load_aux','r5_top_bridge_load_main','r5_top_bridge_load_aux'}


def coupon_stage(entry):
    if entry.get('print_stage')=='revision_check':
        return 'revision_check'
    selected = entry.get('mandatory',False) or entry['name'] in STRUCTURAL_COUPONS or entry['name']=='phone_usb_spine_6mm_coupon'
    return 'first_print' if selected else 'optional'


def run(manifest_path):
    manifest_bytes = manifest_path.read_bytes()
    source_hash = hashlib.sha256(manifest_bytes).hexdigest()
    manifest = json.loads(manifest_bytes)
    assert manifest['units'] == 'mm'
    source_dir = manifest_path.parent
    display_by_sku={e['sku']:e.get('display_name',e['sku']) for e in manifest['print_parts']}
    for entry in manifest['coupons']:
        if entry.get('print_stage')=='revision_check' and entry.get('display_name',entry['name'])==entry['name']:
            sku=entry['name'].removeprefix('r5_revision_')
            if sku=='straight_tibia_main_and_foot':
                sku='tibia_curved_main_and_foot'
            entry['display_name']=display_by_sku.get(sku,sku.replace('_',' '))
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
        plates[pi]['parts'].append((entry['name'], mesh, entry['stl'], digest, entry.get('display_name',entry['name'])))
        shelf['x'] += w + 8
    report = dict(status='Geometry plates only. Print coupons before production parts.',
                  units='mm', source_manifest_sha256=source_hash,
                  source_manifest=str(manifest_path.relative_to(ROOT)), spacing_mm=8,
                  packing_area_mm=[215,215], machine_bed_mm=[225,225], plates=[])
    report['coupon_selection'] = dict(revision_check=sum(coupon_stage(e)=='revision_check' for e in manifest['coupons']), first_print=sum(coupon_stage(e)=='first_print' for e in manifest['coupons']),
        optional=sum(coupon_stage(e)=='optional' for e in manifest['coupons']),available=len(loaded),
        reason='Common fits and two femur sections; five reusable R5 revision parts on dedicated plates; alternatives remain available.')
    plates.sort(key=lambda p: {'first_print':0,'revision_check':1,'optional':2}[p['family']])
    for pi, plate in enumerate(plates, 1):
        name = f'coupon_plate_{pi:02}'
        parts = plate['parts']
        # Center the complete packing within the physical 225 mm bed.
        total = trimesh.util.concatenate([p[1] for p in parts])
        xy = total.extents[:2]
        delta = np.r_[(225-xy)/2, 0.0]
        for _, mesh, _, _, _ in parts: mesh.apply_translation(delta)
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
        three_mf(three, [(p[4],p[1]) for p in parts])
        report['plates'].append(dict(name=name, family=plate['family'], bounds_mm=total.bounds.tolist(),
            stl=stl.name, stl_sha256=sha(stl), model_3mf=three.name, model_3mf_sha256=sha(three),
            parts=[dict(name=n, display_name=label, source_stl=s, source_sha256=d, bounds_mm=m.bounds.tolist()) for n,m,s,d,label in parts]))
    bom = []
    for e in manifest['print_parts']:
        production = trimesh.load_mesh(source_dir/e['stl'], process=True)
        assert production.is_watertight and production.is_winding_consistent and production.volume > 0, e['sku']
        assert np.isfinite(production.vertices).all() and np.isfinite(production.face_normals).all(), e['sku']
        assert np.allclose(production.extents, e['dimensions_mm'], atol=.04), e['sku']
        bom.append(dict(part=e['sku'],display_name=e.get('display_name',e['sku']),quantity=e['quantity'],
            X_mm=round(e['dimensions_mm'][0],3),Y_mm=round(e['dimensions_mm'][1],3),
            Z_mm=round(e['dimensions_mm'][2],3), source_stl='../cad/output/'+e['stl'],
            source_sha256=sha(source_dir/e['stl']), stage='Production after coupon and one-leg fit',
            supports_required=e.get('supports_required', e['sku'] in {
                'coxa_upper_and_hip_saddle', 'femur_main_and_knee_saddle',
                'tibia_curved_main_and_foot'}),
            note=e.get('supports','')))
    csv_file(OUT/'manufacturing_bom.csv', list(bom[0]), bom)
    coupon_rows = [dict(part=e['name'], display_name=e.get('display_name',e['name']), quantity=1, stage=coupon_stage(e),source_mandatory=e.get('mandatory',False),
        selection_reason='Section specimen required before load tests' if e['name'] in STRUCTURAL_COUPONS else (
            'USB spine and plug check' if e['name']=='phone_usb_spine_6mm_coupon' else 'Source mandatory fit' if e.get('mandatory',False) else 'Alternative fit'),
        source_stl='../cad/output/'+e['stl'], source_sha256=sha(source_dir/e['stl']),
        note=e.get('note','')) for e in manifest['coupons']]
    csv_file(OUT/'coupon_bom.csv', list(coupon_rows[0]), coupon_rows)
    feedback = OUT/'coupon_feedback.csv'
    fields=['revision','part','display_name','measurement','nominal','measured','material','layer_mm','pass_fail','notes']
    feedback_rows=[]
    if feedback.exists():
        with feedback.open(newline='',encoding='utf-8') as f:
            previous=list(csv.DictReader(f))
        if previous and 'revision' not in previous[0]:
            assert all(not r.get('measured') and not r.get('pass_fail') for r in previous), 'Copied legacy feedback contains entered measurements; preserve it separately before R5 initialization.'
        else:
            feedback_rows=previous
    def add_measurement(part,label,measurement,nominal='',notes=''):
        match=next((r for r in feedback_rows if r['part']==part and r['measurement']==measurement),None)
        if match:
            match['display_name']=label
        else:
            feedback_rows.append(dict(revision='R5',part=part,display_name=label,measurement=measurement,
                nominal=nominal,measured='',material='',layer_mm='',pass_fail='',notes=notes))
    for e in manifest['coupons']:
        add_measurement(e['name'],e.get('display_name',e['name']),'Fit / dimensions / fixture response',notes=e.get('note',''))
    for part,label,measurement,nominal in [
        ('servo_datum','Clamped C018 datum','Case length / width / shaft offset from midpoint','45.23 / 24.73 / 12.5 mm'),
        ('main_horn','Main metal horn','Mounted face and peripheral thread engagement','Verify actual seating'),
        ('auxiliary','Auxiliary disc and retainer','Free rotation / washer seating / pilot depth','Measure delivered hardware'),
        ('pitch_auxiliary','Pitch auxiliary land','M3x8 + TWO OD6 washers; tip margin','1.1 mm land / 1.9 mm engagement / 0.2 mm nominal rear margin'),
        ('yaw_auxiliary','Yaw disc spacer','M3x20 + paired OD6 washers; free rotation','11.6 mm spacer / 3.5 mm counterbore'),
        ('R5_hip_cap','Dedicated inward-hip cap','Rear bolt location and nut/driver access','Servo X=-38.915, Z=-27.5 mm'),
        ('R5_hip_nuts','Bare inward-hip carrier','Three nuts enter from above before servo/cap','Verify actual print fit; complete leg before body mounting'),
        ('R5_frame','Complete 70 mm coxa fixture','Hip force / reversible Y torque / post and flange response','Hip X=70; post holes X=28.5, Y=+/-4.5 mm'),
        ('R5_tibia','Straight 105 mm tibia fixture','Bridge preload / deflection / twist / residual set','Bridge holes X=36 and 44, Z=0 mm'),
        ('R5_clamps','Loaded clamp retention','One hour / one day movement and measured temperature','No established warm allowable'),
        ('pan_cap','Pan servo-cap roof','Preload seating / roof lift','Body and cap screws before horn/hub'),
        ('Mi9SE','Landscape Mi9SE','Mounted width / thickness / height','147.5 / 7.45 / 70.5 mm'),
        ('Mi9SE_interfaces','Phone USB and camera openings','Plug fit / camera/button clearance / dummy-phone response','USB on short side; pan parked'),
        ('electronics','Actual boards and plugs','Measured envelopes / connector access','Measure owned parts'),
        ('R5_full_leg','Complete R5 leg','Unpowered sweep / screw clearance / measured mass','Use current restricted joint range')]:
        add_measurement(part,label,measurement,nominal)
    csv_file(feedback,fields,feedback_rows)
    assert sha(manifest_path) == source_hash, 'CAD regenerated during packing; run again.'
    slicing_path=ROOT/'manufacturing/slicing_r5/output/PRODUCTION_SLICING.md'
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
    assert len([e for e in manifest['coupons'] if coupon_stage(e)=='revision_check'])==5
    first_fit='\n'.join([
        'R5 FIRST-FIT AND REVISION CHECKS','',
        'Disposition: controlled fit and fixture printing. Full production remains gated on R5 load results and physical fixtures.',
        'Use only the files in this R5 directory. R4 is preserved separately.',
        'Final yaw operating limit: +/-19 degrees, retaining a 1.61054 mm nominal fixed-saddle gap.',
        'The +/-22 degree pose leaves only 0.656 mm and fails the clearance criterion. Printed geometry is unchanged.',
        'The five revision-check pieces are complete reusable production parts, not cropped substitutes.',
        'Fit the 70 mm coxa, its lower arm and dedicated hip cap together with the real servos/discs.',
        'Load all three hip nuts from above into the bare carrier. Complete leg modules before body mounting.',
        'The hip rear cap bolt is at servo X=-38.915, Z=-27.5. Do not substitute a generic cap.',
        'Retain the full-depth triangular flange and post bolts at X=28.5, Y=+/-4.5.',
        'Fit the straight 105 mm tibia and its short auxiliary cheek; bridge bolts are X=36/44, Z=0.',
        'Check all nut loading, driver access, screw tips, connector bends and free auxiliary rotation.',
        'Use captured full-frame load tests with hip force at X=70 and independently reversing Y torque.',
        'Record force, lever arm, displacement, twist and residual set. Stop on cracking, whitening,',
        'binding, forced alignment, slip, progressive deflection, roof lift or permanent set.',
        'R4 access-cut limitations and numerical load margins do not qualify this revised structure.',
        'Use R5 source-matched strength and slicing reports when available. No physical strength pass is claimed.',
        'Complete fixtures and one supported leg before a full robot run. Weigh actual printed parts.',
        'Source CAD manifest SHA-256: '+source_hash,''])
    (OUT/'FIRST_FIT_CHECKS.txt').write_text(first_fit,encoding='utf-8')
    report['first_fit_notice']='FIRST_FIT_CHECKS.txt'
    report['first_fit_notice_sha256']=sha(OUT/'FIRST_FIT_CHECKS.txt')
    (OUT/'plate_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    groups={stage:[p['model_3mf'] for p in report['plates'] if p['family']==stage]
            for stage in ('first_print','revision_check','optional')}
    quick='\n'.join([
        'R5 PRINT FIRST: 70 MM INWARD HIP AND STRAIGHT TIBIA','',
        'Final yaw operating limit is +/-19 degrees. This update does not change any print pieces.',
        '1. Read FIRST_FIT_CHECKS.txt and PRINT_AND_ASSEMBLE.md. Keep units in millimetres.',
        '2. Common fit plate(s): '+', '.join(groups['first_print']),
        '   Use the case-to-shaft gauge with the actual clamped servo and metal horn. Preload nuts',
        '   in bare carriers, then check alignment before tightening. Keep auxiliary discs free.',
        '3. Dedicated revision plate(s): '+', '.join(groups['revision_check']),
        '   These five full production pieces are the upper coxa/hip carrier, lower yaw arm,',
        '   dedicated hip cap, straight tibia main/foot and short auxiliary cheek.',
        '   Passing parts can be reused. Count them toward the production BOM to avoid duplicates.',
        '4. Optional fit plate(s): '+', '.join(groups['optional']),
        '   Use alternative case/phone clearances and yaw spacers only if nominal fits need adjustment.',
        '5. Start PLA with a 0.4 mm nozzle, 0.20 mm layers, 0.42 mm lines, five walls, six top/bottom',
        '   layers, 35% gyroid and an 8 mm3/s flow ceiling. Starting temperatures are 210/60 C',
        '   within the filament maker\'s range. Inspect support beneath every raised feature.',
        '   Plates contain geometry only; slice for the actual Neptune 4 Pro before printing.',
        '6. Hip auxiliary screws remain M3x8 with TWO OD6 x 0.5 mm washers. Yaw uses M3x20,',
        '   paired OD6 washers and nominal 11.6 mm spacers. Read R5_FASTENER_STACKS.md.',
        '   The hip uses its dedicated rear-bolt position. The full coxa must be load-tested.',
        '   Load the three hip nuts from above into the bare carrier; assemble legs before body mounting.',
        '7. Use fresh R5 coupon_feedback.csv records. The old R4 records remain in the R4 folder.',
        '   Check fixtures and one supported leg before full-robot movement. This is not physical qualification.',
        '   Phone remains landscape and upright; park pan before side USB charging.',
        'Source CAD manifest SHA-256: '+source_hash,''])
    (OUT/'PRINT_FIRST.txt').write_text(quick,encoding='utf-8')
    for guide in ('PRINT_AND_ASSEMBLE','WIRING','ASSEMBLY_DFM_REVIEW'):
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
