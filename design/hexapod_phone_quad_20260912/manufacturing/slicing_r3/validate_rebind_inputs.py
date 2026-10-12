"""Read-only gate for reusing sliced properties after a bounded CAD revision.

No files are written and no slicing is performed. The caller owns any saved
validation receipt. A same-path old/new manifest comparison is an explicitly
labeled historical preflight using retained source snapshots, not live CAD.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any


class RebindValidationError(ValueError):
    """Validation failed; report contains structured reasons and partial checks."""

    def __init__(self, report: dict[str, Any]):
        self.report = report
        errors = report.get('errors', [])
        super().__init__('Rebind inputs failed validation: ' + '; '.join(errors))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> tuple[dict[str, Any], str]:
    data = path.read_bytes()
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError('Non-finite JSON number: ' + value)
    decoded = json.loads(data, object_pairs_hook=pairs, parse_constant=nonfinite)
    if not isinstance(decoded, dict):
        raise ValueError('Expected a JSON object: ' + str(path))
    return decoded, hashlib.sha256(data).hexdigest()


def _index(rows: Any, key: str, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        raise ValueError(label + ' must be a nonempty array')
    result = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get(key), str) or not row[key]:
            raise ValueError(label + ' has an invalid ' + key)
        if row[key] in result:
            raise ValueError(label + ' has duplicate ' + key + ': ' + row[key])
        result[row[key]] = row
    return result


def _diff(old: Any, new: Any, path: str = '') -> list[dict[str, Any]]:
    """Return exact numerical/value differences, including additions/removals."""
    if old == new:
        return []
    if isinstance(old, dict) and isinstance(new, dict):
        changes = []
        for key in sorted(set(old) | set(new)):
            child = path + '/' + str(key).replace('~', '~0').replace('/', '~1')
            if key not in old:
                changes.append({'path': child, 'change': 'added', 'new': new[key]})
            elif key not in new:
                changes.append({'path': child, 'change': 'removed', 'old': old[key]})
            else:
                changes.extend(_diff(old[key], new[key], child))
        return changes
    return [{'path': path or '/', 'change': 'changed', 'old': old, 'new': new}]


def _finite_matrix(value: Any) -> bool:
    return (isinstance(value, list) and len(value) == 4
            and all(isinstance(row, list) and len(row) == 4 for row in value)
            and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                    and math.isfinite(v) for row in value for v in row)
            and value[3] == [0, 0, 0, 1])


def validate(
    old_aggregate_path: str | Path,
    old_manifest_path: str | Path,
    new_manifest_path: str | Path,
    allowed_changed_skus: list[str] | tuple[str, ...] = ('body_deck',),
) -> dict[str, Any]:
    """Return evidence for a permitted rebind, or raise RebindValidationError.

    Only listed SKUs may change STL bytes, print rotation or print-to-link frame.
    All names, SKUs, quantities and part link assignments must remain identical.
    Metadata differences are reported for caller review, not silently approved.
    No change to an allowed SKU is required, so historical preflight can pass.
    """
    paths = [Path(p).resolve(strict=True) for p in
             (old_aggregate_path, old_manifest_path, new_manifest_path)]
    aggregate, aggregate_hash = _json(paths[0])
    old, old_hash = _json(paths[1])
    new, new_hash = _json(paths[2])
    historical = paths[1] == paths[2]
    allowed = set(allowed_changed_skus)
    if any(not isinstance(sku, str) or not sku for sku in allowed):
        raise ValueError('allowed_changed_skus must contain nonempty strings')
    report = {
        'status': 'pending', 'validated_utc': datetime.now(timezone.utc).isoformat(),
        'validation_mode': 'archived_same_manifest_preflight' if historical else 'new_manifest_file_hash_validation',
        'new_manifest_readiness': 'historical_preflight_only' if historical else 'provided_by_caller',
        'old_aggregate_path': str(paths[0]), 'old_aggregate_sha256': aggregate_hash,
        'old_manifest_path': str(paths[1]), 'old_manifest_sha256': old_hash,
        'new_manifest_path': str(paths[2]), 'new_manifest_sha256': new_hash,
        'allowed_changed_skus': sorted(allowed), 'errors': [],
    }
    errors = report['errors']
    if aggregate.get('status') != 'pass':
        errors.append('The old aggregate is not marked pass')
    if aggregate.get('source_manifest_hash') != old_hash:
        errors.append('The old aggregate is not bound to the supplied old manifest bytes')
    if aggregate.get('source_revision') != old.get('revision'):
        errors.append('The old aggregate revision differs from the old manifest revision')
    if old.get('units') != 'mm' or new.get('units') != 'mm':
        errors.append('Both source manifests must use millimetres')
    try:
        sliced = _index(aggregate.get('parts'), 'sku', 'Old aggregate parts')
        old_print = _index(old.get('print_parts'), 'sku', 'Old manifest print_parts')
        new_print = _index(new.get('print_parts'), 'sku', 'New manifest print_parts')
        old_parts = _index(old.get('parts'), 'name', 'Old assembly parts')
        new_parts = _index(new.get('parts'), 'name', 'New assembly parts')
    except ValueError as error:
        errors.append(str(error))
        report['status'] = 'fail'
        raise RebindValidationError(report) from error
    if set(sliced) != set(old_print) or set(old_print) != set(new_print):
        errors.append('Production SKU sets differ among the aggregate and manifests')
    if not allowed <= set(old_print):
        errors.append('An allowed changed SKU is absent from the old production set')
    if set(old_parts) != set(new_parts):
        errors.append('Named assembly part sets changed')
    report['part_names_added'] = sorted(set(new_parts) - set(old_parts))
    report['part_names_removed'] = sorted(set(old_parts) - set(new_parts))
    report['production_sku_count'] = len(old_print)
    report['expected_unchanged_sku_count'] = len(set(old_print) - allowed)
    report['named_assembly_part_count'] = len(old_parts)
    # Every manifest quantity must equal its actual number of printed instances.
    for label, manifest_parts, manifest_print in (
        ('old', old_parts, old_print), ('new', new_parts, new_print)
    ):
        counts = Counter(row.get('sku') for row in manifest_parts.values() if row.get('printable'))
        if set(counts) != set(manifest_print):
            errors.append(label + ' printable instance SKU set differs from print_parts')
        for sku, entry in manifest_print.items():
            quantity = entry.get('quantity')
            if (not isinstance(quantity, int) or isinstance(quantity, bool)
                    or quantity <= 0 or counts.get(sku) != quantity):
                errors.append(f'{label} quantity or printed instance count is invalid for {sku}')
    part_changes = []
    for name in sorted(set(old_parts) & set(new_parts)):
        before, after = old_parts[name], new_parts[name]
        for key in ('sku', 'link', 'printable', 'allowance_only', 'material'):
            if before.get(key) != after.get(key):
                errors.append(f'Assembly identity field {key} changed for {name}')
        for key in ('quantity',):
            if before.get(key) != after.get(key):
                errors.append(f'Assembly quantity changed for {name}')
        old_frame = before.get('print_to_link_transform')
        new_frame = after.get('print_to_link_transform')
        if after.get('printable') and not _finite_matrix(new_frame):
            errors.append('Invalid new print_to_link_transform for ' + name)
        if old_frame != new_frame:
            part_changes.append({'name': name, 'sku': before.get('sku'),
                                 'field': 'print_to_link_transform', 'old': old_frame, 'new': new_frame})
            if before.get('sku') not in allowed:
                errors.append('Non-permitted print_to_link_transform change for ' + name)
    report['print_to_link_transform_changes'] = part_changes
    checks = []
    # Refuse to inspect new STL data until the identity and old receipt binding
    # are valid. This also avoids confusing stale aggregate metadata with CAD.
    if errors:
        report['status'] = 'fail'
        raise RebindValidationError(report)
    for sku in sorted(old_print):
        before, after, prior = old_print[sku], new_print[sku], sliced[sku]
        if before.get('quantity') != after.get('quantity') or prior.get('quantity') != before.get('quantity'):
            errors.append('Production quantity changed or is inconsistent for ' + sku)
        old_rotation = before.get('print_rotation')
        new_rotation = after.get('print_rotation')
        if prior.get('source_print_rotation_deg') != old_rotation:
            errors.append('Old aggregate print rotation differs from its source manifest for ' + sku)
        if old_rotation != new_rotation and sku not in allowed:
            errors.append('Non-permitted print rotation change for ' + sku)
        expected_hash = prior.get('source_stl_hash')
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            errors.append('Missing old sliced STL hash for ' + sku)
            continue
        if historical:
            snapshot_name = prior.get('engine', {}).get('original_snapshot_path')
            if not snapshot_name:
                errors.append('Missing retained original source snapshot for historical preflight: ' + sku)
                continue
            candidate = Path(snapshot_name).resolve(strict=True)
        else:
            relative_name = after.get('stl')
            if not isinstance(relative_name, str):
                errors.append('Missing new STL path for ' + sku)
                continue
            candidate = (paths[2].parent / relative_name).resolve(strict=True)
            if not candidate.is_relative_to(paths[2].parent):
                errors.append('New STL path leaves the supplied manifest directory: ' + sku)
                continue
        actual_hash = _sha(candidate)
        changed = actual_hash != expected_hash
        if changed and sku not in allowed:
            errors.append('Unexpected STL byte change for ' + sku)
        checks.append({
            'sku': sku, 'quantity': after['quantity'], 'stl_path': str(candidate),
            'old_sliced_stl_sha256': expected_hash, 'new_stl_sha256': actual_hash,
            'stl_bytes_changed': changed, 'change_permitted': sku in allowed,
            'old_print_rotation': old_rotation, 'new_print_rotation': new_rotation,
        })
    report['sku_checks'] = checks
    report['changed_skus'] = [row['sku'] for row in checks if row['stl_bytes_changed']]
    report['unchanged_skus'] = [row['sku'] for row in checks if not row['stl_bytes_changed']]
    report['non_permitted_stl_changes'] = [sku for sku in report['changed_skus'] if sku not in allowed]
    report['requires_reslice_skus'] = sorted(set(report['changed_skus']) | {
        row['sku'] for row in checks if row['old_print_rotation'] != row['new_print_rotation']
    })
    report['deck_hash_difference'] = next((row for row in checks if row['sku'] == 'body_deck'), None)
    report['piece_count'] = sum(row['quantity'] for row in new_print.values())
    report['revisions'] = {
        'old_aggregate': aggregate.get('source_revision'),
        'old_manifest': old.get('revision'), 'new_manifest': new.get('revision'),
        'old_parameters': old.get('parameters', {}).get('revision'),
        'new_parameters': new.get('parameters', {}).get('revision'),
    }
    metadata_keys = (set(old) | set(new)) - {'parts', 'print_parts', 'links', 'coupons'}
    metadata_old = {key: old[key] for key in metadata_keys if key in old}
    metadata_new = {key: new[key] for key in metadata_keys if key in new}
    metadata_changes = _diff(metadata_old, metadata_new)
    report['metadata_changes'] = metadata_changes
    report['joint_limit_metadata_changes'] = [change for change in metadata_changes
        if any(term in change['path'].lower() for term in ('joint', 'limit', 'sweep'))]
    report['source_code_hash_changes'] = _diff(old.get('source_hashes', {}), new.get('source_hashes', {}), '/source_hashes')
    report['metadata_review_note'] = (
        'Metadata changes are reported for caller review. This gate does not authorize changes to joint limits or attest to URDF files outside the supplied manifests.'
    )
    if set(old.get('links', {})) != set(new.get('links', {})):
        errors.append('Assembly link names changed')
    report['link_metadata_changes'] = _diff(old.get('links', {}), new.get('links', {}), '/links')
    # Catch a rebuild racing the check. Source bytes are reread, with no writes.
    for path, expected in zip(paths, (aggregate_hash, old_hash, new_hash)):
        if _sha(path) != expected:
            errors.append('Input JSON changed during validation: ' + str(path))
    for row in checks:
        if _sha(Path(row['stl_path'])) != row['new_stl_sha256']:
            errors.append('STL changed during validation: ' + row['sku'])
    report['all_non_permitted_stl_hashes_unchanged'] = not report['non_permitted_stl_changes']
    report['all_non_permitted_frames_unchanged'] = not any(
        row['sku'] not in allowed for row in part_changes
    )
    report['all_identity_and_quantity_checks_pass'] = not any(
        term in error for error in errors for term in ('identity', 'quantity', 'instance', 'sets changed')
    )
    report['status'] = 'fail' if errors else 'pass'
    if errors:
        raise RebindValidationError(report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--old-aggregate', required=True)
    parser.add_argument('--old-manifest', required=True)
    parser.add_argument('--new-manifest', required=True)
    parser.add_argument('--allow-changed-sku', action='append', default=None)
    args = parser.parse_args()
    try:
        result = validate(args.old_aggregate, args.old_manifest, args.new_manifest,
                          args.allow_changed_sku if args.allow_changed_sku is not None else ['body_deck'])
    except RebindValidationError as error:
        print(json.dumps(error.report, indent=2, allow_nan=False))
        raise SystemExit(1)
    print(json.dumps(result, indent=2, allow_nan=False))
