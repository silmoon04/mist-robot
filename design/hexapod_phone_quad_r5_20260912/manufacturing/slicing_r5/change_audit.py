"""Current-orientation mesh and support audit for the separate R5 design."""
from pathlib import Path
import hashlib
import json
import math
import numpy as np
import trimesh

HERE=Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def geometry(row):
    path=Path(row['engine']['original_snapshot_path'])
    assert sha(path)==row['source_stl_hash']
    mesh=trimesh.load_mesh(path,process=True)
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0,row['sku']
    triangles=mesh.triangles.copy()
    triangles[:,:,2]-=mesh.bounds[0,2]
    normals=mesh.face_normals[:,2]
    projected=mesh.area_faces*np.maximum(0,-normals)
    bed=triangles[:,:,2].max(axis=1)<1e-5
    downward=(normals<=-math.cos(math.radians(45))+1e-7)&(triangles[:,:,2].max(axis=1)>.21)
    return dict(watertight=True,winding_consistent=True,connected_component_count=int(mesh.body_count),
        volume_mm3=float(mesh.volume),dimensions_mm=mesh.extents.tolist(),
        print_rotation_deg=row['source_print_rotation_deg'],
        bed_contact_mm2=float(projected[bed].sum()),projected_overhang_45_inclusive_mm2=float(projected[downward].sum()),
        fits_225_bed_with_4mm_brim=bool(np.all(mesh.extents[:2]+8<=225)))


def run():
    path=HERE/'output/production_mass_properties.json'
    current=json.loads(path.read_text())
    manifest=json.loads(Path(current['source_manifest_path']).read_text())
    declared={p['sku']:p for p in manifest['print_parts']}
    binding=current['preserved_r4_properties']
    assert sha(binding['path'])==binding['sha256']
    old=json.loads(Path(binding['path']).read_text())
    previous={p['sku']:p for p in old['parts']}
    rows=[]
    for part in current['parts']:
        before=previous.get(part['sku'])
        after_geometry=geometry(part)
        declared_dimensions=declared[part['sku']]['dimensions_mm']
        dimension_error=float(np.max(np.abs(np.array(after_geometry['dimensions_mm'])-np.array(declared_dimensions))))
        assert dimension_error<=.1,(part['sku'],dimension_error)
        after_geometry.update(declared_dimensions_mm=declared_dimensions,maximum_dimension_error_mm=dimension_error)
        changed=before is None or part['source_stl_hash']!=before['source_stl_hash']
        before_geometry=geometry(before) if before and changed else after_geometry if before else None
        rows.append(dict(sku=part['sku'],quantity=part['quantity'],stl_bytes_changed=changed,
            old_stl_hash=before['source_stl_hash'] if before else None,new_stl_hash=part['source_stl_hash'],
            old_geometry=before_geometry,new_geometry=after_geometry,
            r4_model_mass_g=before['mass_kg']*1000 if before else None,r5_model_mass_g=part['mass_kg']*1000,
            r4_support_mass_g=before['support_mass_g'] if before else None,r5_support_mass_g=part['support_mass_g'],
            r4_time_min=before['estimated_print_time_s']/60 if before else None,r5_time_min=part['estimated_print_time_s']/60))
    old_skus=set(previous);new_skus={r['sku'] for r in rows}
    changed=[r for r in rows if r['stl_bytes_changed']]
    assert sha(current['source_manifest_path'])==current['source_manifest_hash']
    quantities={r['sku']:dict(r4=previous[r['sku']]['quantity'],r5=r['quantity']) for r in rows
                if r['sku'] in previous and r['quantity']!=previous[r['sku']]['quantity']}
    status='pass' if all(r['new_geometry']['connected_component_count']==1 and r['new_geometry']['fits_225_bed_with_4mm_brim'] for r in rows) else 'review_required'
    answer=dict(status=status,source_manifest_hash=current['source_manifest_hash'],
        production_properties_hash=sha(path),preserved_r4_properties_hash=binding['sha256'],
        production_sku_count=len(rows),piece_count=sum(r['quantity'] for r in rows),
        changed_stl_hash_count=len(changed),added_skus=sorted(new_skus-old_skus),removed_skus=sorted(old_skus-new_skus),
        quantity_changes=quantities,all_current_meshes_watertight_winding_consistent_positive_volume=True,
        all_current_meshes_have_one_connected_component=all(r['new_geometry']['connected_component_count']==1 for r in rows),
        all_current_footprints_fit_225mm_bed_with_4mm_brim=all(r['new_geometry']['fits_225_bed_with_4mm_brim'] for r in rows),
        all_export_dimensions_within_0p1mm=True,
        maximum_dimension_error_mm=max(r['new_geometry']['maximum_dimension_error_mm'] for r in rows),
        rows=rows,limitations=['STL byte differences alone do not prove a significant geometry change.',
            'The face-area screen uses the current export orientation at a conservative 45 degree threshold. It does not search alternative angles.',
            'Actual support masses come from the fixed Cura profile. Adhesion, support removal and physical strength require printed tests.'])
    (HERE/'R5_CHANGE_AUDIT.json').write_text(json.dumps(answer,indent=2)+'\n')
    total=current['quantity_weighted_totals'];old_total=old['quantity_weighted_totals']
    lines=['# R5 printing and changed support audit','',
        f"The audit covers {len(rows)} production SKUs and {answer['piece_count']} printed pieces. All current meshes are watertight, consistently wound and have positive volume. The overall result is `{status}`. Component counts and bed fit are checked for every current export.",'',
        'The legacy `tibia_curved_main_and_foot` SKU contains the straight R5 tibia. Its broad main cheek remains the print base; the central transverse shank and short bridge require local support review. Remove support from the knee interface and transverse fastener access before measuring fit. The separate auxiliary cheek remains on its broad face.','',
        f"The complete recorded slices predict {total['model_mass_g']:.2f} g of part PLA and {total['support_mass_g']:.2f} g of removable support. Relative to R4, model PLA changes by {total['model_mass_g']-old_total['model_mass_g']:+.2f} g and support by {total['support_mass_g']-old_total['support_mass_g']:+.2f} g. These are commanded-filament estimates.",'',
        '| Changed SKU | Current dimensions, mm | Current bed contact, mm2 | R4 / R5 support, g | R4 / R5 time, min |',
        '| --- | --- | ---: | ---: | ---: |']
    fmt=lambda n:'new' if n is None else f'{n:.2f}'
    for row in changed:
        g=row['new_geometry'];dims=' x '.join(f'{d:.2f}' for d in g['dimensions_mm'])
        lines.append(f"| `{row['sku']}` | {dims} | {g['bed_contact_mm2']:.1f} | {fmt(row['r4_support_mass_g'])} / {row['r5_support_mass_g']:.2f} | {fmt(row['r4_time_min'])} / {row['r5_time_min']:.2f} |")
    lines += ['',
        'The JSON records volumes, dimensions, connected components, print rotations, bed contact and projected downward area for every SKU. A low support mass does not establish that an inaccessible interface will cleanly release. Inspect the actual sliced layers around servo seats, nut pockets and the central tibia shank. Use local support and an appropriate brim where the supplied orientation has small first-layer contact.','',
        f"Added SKUs: {', '.join(answer['added_skus']) or 'none'}. Removed SKUs: {', '.join(answer['removed_skus']) or 'none'}. Quantity changes: {len(quantities)}.",'',
        f"Source manifest SHA-256: `{current['source_manifest_hash']}`. Production-properties SHA-256: `{sha(path)}`.",'']
    text='\n'.join(lines)
    (HERE/'R5_CHANGE_AUDIT.md').write_text(text)
    (HERE/'R5_CHANGE_AUDIT.txt').write_text(text)
    print(json.dumps({k:v for k,v in answer.items() if k!='rows'}))


if __name__=='__main__':
    run()
