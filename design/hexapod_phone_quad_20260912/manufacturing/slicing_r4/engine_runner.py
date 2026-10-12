"""CuraEngine wrapper for temporary deposition analysis, with explicit frames.

The caller owns material parsing and final storage. After consuming the returned
raw_temporary_path, comment out every command, gzip the result, and remove the raw
file. This module never sends files to a printer. Concurrent calls are supported
when their destination directories or SKU names differ.
"""
from __future__ import annotations

import copy
from functools import lru_cache
import hashlib
import io
import json
import math
from pathlib import Path
import re
import subprocess
import time
from typing import Any

import numpy as np
import trimesh

ENGINE = Path('C:/Program Files/UltiMaker Cura 5.13.0/CuraEngine.exe')
ENGINE_VERSION = '5.13.0'
ENGINE_SHA256 = '36e36d4618cd09a0cd8802a565c2cdbe54804eb750ac84303a0c6d6f784afde2'
BASE_PROFILE = Path(__file__).resolve().parents[1] / 'orientation/slicer/resolved_analysis.def.json'
BASE_PROFILE_SHA256 = 'ddf583bf158bc99bb7cbda228cc8ee3e0552ece2764176a89afb9c83048ada1b'
COORDINATE_SOURCE_URL = 'https://github.com/Ultimaker/CuraEngine/blob/5.13.0/src/MeshGroup.cpp#L97-L121'
ROUNDING_SOURCE_URL = 'https://github.com/Ultimaker/CuraEngine/blob/5.13.0/include/utils/Coord_t.h#L23-L25'
PARAMETER = re.compile(r'([XYZEF])(-?\d+(?:\.\d+)?)')


def sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def _frozen_base() -> dict[str, Any]:
    if sha256(ENGINE) != ENGINE_SHA256:
        raise RuntimeError('CuraEngine bytes differ from the validated 5.13.0 executable.')
    data = BASE_PROFILE.read_bytes()
    if hashlib.sha256(data).hexdigest() != BASE_PROFILE_SHA256:
        raise RuntimeError('The frozen numeric base profile has changed.')
    return json.loads(data)


def mm_to_um(value: Any) -> np.ndarray:
    """Cura MM2INT: round to nearest micrometre, with ties away from zero."""
    value = np.asarray(value, dtype=np.float64)
    return np.trunc(value * 1000.0 + np.sign(value) * 0.5).astype(np.int64)


def _translation(offset_mm: Any) -> np.ndarray:
    result = np.eye(4)
    result[:3, 3] = offset_mm
    return result


def _resolved_profile(overrides: dict[str, Any] | None) -> dict[str, Any]:
    definition = copy.deepcopy(_frozen_base())
    definition['name'] = 'R4 frozen numeric PLA deposition analysis'
    values = definition['settings']
    overrides = dict(overrides or {})
    controlled = {
        'center_object', 'mesh_position_x', 'mesh_position_y', 'mesh_position_z',
        'mesh_rotation_matrix', 'machine_center_is_zero',
        'material_shrinkage_percentage_xy', 'material_shrinkage_percentage_z',
        'machine_nozzle_offset_x', 'machine_nozzle_offset_y',
        'machine_extruder_count', 'relative_extrusion', 'machine_gcode_flavor',
        'machine_start_gcode', 'machine_end_gcode',
        'machine_extruder_start_code', 'machine_extruder_end_code',
        'machine_extruder_prestart_code', 'machine_extruder_start_pos_abs',
        'machine_extruder_end_pos_abs',
    }
    prohibited = controlled.intersection(overrides)
    if prohibited:
        raise ValueError('Frame or startup settings are controlled by the runner: ' + ', '.join(sorted(prohibited)))
    unknown = set(overrides).difference(values)
    if unknown:
        raise ValueError('Unknown settings: ' + ', '.join(sorted(unknown)))
    for key, value in overrides.items():
        expected_type = values[key].get('type')
        if expected_type == 'bool' and not isinstance(value, bool):
            raise TypeError(key + ' requires a boolean, not a frontend expression.')
        if expected_type in {'float', 'int', 'extruder'}:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise TypeError(key + ' requires a finite numeric value.')
    # Resolve the common density-dependent distances explicitly. Other supplied
    # settings are literal values; there is no Cura frontend formula evaluator.
    if 'infill_sparse_density' in overrides and 'infill_line_distance' not in overrides:
        pattern = overrides.get('infill_pattern', values['infill_pattern']['default_value'])
        if pattern != 'gyroid':
            raise ValueError('A changed infill density with a non-gyroid pattern requires infill_line_distance.')
        density = float(overrides['infill_sparse_density'])
        width = float(overrides.get('infill_line_width', values['infill_line_width']['default_value']))
        overrides['infill_line_distance'] = width * 100.0 / density if density > 0 else 0.0
    if 'support_infill_rate' in overrides:
        density = float(overrides['support_infill_rate'])
        width = float(overrides.get('support_line_width', values['support_line_width']['default_value']))
        distance = width * 100.0 / density if density > 0 else 0.0
        overrides.setdefault('support_line_distance', distance)
        overrides.setdefault('support_initial_layer_line_distance', distance)
    if 'support_roof_density' in overrides and 'support_roof_line_distance' not in overrides:
        density = float(overrides['support_roof_density'])
        width = float(overrides.get('support_roof_line_width', values['support_roof_line_width']['default_value']))
        overrides['support_roof_line_distance'] = width * 100.0 / density if density > 0 else 0.0
    for key, value in overrides.items():
        values[key]['default_value'] = value
    for key, value in {
        'center_object': False, 'machine_center_is_zero': False,
        'material_shrinkage_percentage_xy': 100.0, 'material_shrinkage_percentage_z': 100.0,
        'machine_nozzle_offset_x': 0.0, 'machine_nozzle_offset_y': 0.0,
        'machine_extruder_count': 1, 'relative_extrusion': False,
        'machine_start_gcode': '', 'machine_end_gcode': '',
        'machine_extruder_start_code': '', 'machine_extruder_end_code': '',
        'machine_extruder_prestart_code': '',
    }.items():
        values[key]['default_value'] = value
    if not 0 < float(values['material_max_flowrate']['default_value']) <= 8:
        raise ValueError('The analysis flow cap must be positive and no greater than 8 mm3/s.')
    for key in ('machine_width', 'machine_depth', 'machine_height'):
        if float(values[key]['default_value']) <= 0:
            raise ValueError('Build dimensions must be positive.')
    return definition


def _gcode_envelope(path: Path, build_mm: np.ndarray) -> dict[str, Any]:
    xyz = np.zeros(3)
    lower = np.full(3, np.inf)
    upper = np.full(3, -np.inf)
    count = 0
    elapsed = None
    with path.open(encoding='utf-8') as handle:
        for line in handle:
            if line.startswith(';TIME_ELAPSED:'):
                elapsed = float(line.partition(':')[2])
            command = line.split(';', 1)[0].strip()
            verb = command.partition(' ')[0]
            if verb in {'G20', 'G91', 'G2', 'G3'}:
                raise RuntimeError('Unexpected coordinate mode or arc in analysis G-code: ' + verb)
            if verb not in {'G0', 'G1'}:
                continue
            fields = {axis: float(value) for axis, value in PARAMETER.findall(command)}
            if not any(axis in fields for axis in 'XYZ'):
                continue
            for index, axis in enumerate('XYZ'):
                if axis in fields:
                    xyz[index] = fields[axis]
            lower = np.minimum(lower, xyz)
            upper = np.maximum(upper, xyz)
            count += 1
    if not count or elapsed is None:
        raise RuntimeError('The engine emitted no usable spatial moves or final time estimate.')
    return {
        'motion_bounds_mm': [lower.tolist(), upper.tolist()],
        'motion_count': count,
        'motion_inside_build_envelope': bool(np.all(lower >= -0.001) and np.all(upper <= build_mm + 0.001)),
        'estimated_time_seconds': elapsed,
    }


def slice_one(
    source_stl: str | Path,
    destination_dir: str | Path,
    sku: str,
    settings_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Slice one supplied print STL and return its coordinate and byte provenance.

    All matrices are row-major arrays, use column vectors, and have millimetre
    translations. source_to_gcode_transform maps the ORIGINAL supplied STL frame
    into machine coordinates. Its inverse therefore restores original STL COM.
    Coordinate quantization is recorded separately because it is not affine.

    The raw G-code is temporary and intended only for the caller's parser. A
    successful call returns it; exceptions remove it. A 300 second process limit
    bounds each slice. Run two calls concurrently using distinct output names.
    """
    start = time.monotonic()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', sku):
        raise ValueError('SKU must be a filename-safe identifier.')
    source = Path(source_stl).resolve(strict=True)
    destination = Path(destination_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    lock = destination / (sku + '.slice.lock')
    with lock.open('x', encoding='utf-8') as handle:
        handle.write('Active CuraEngine slice.\n')
    raw = destination / (sku + '.temporary.gcode')
    raw_owned = False
    try:
        if raw.exists():
            raise FileExistsError('An unconsumed raw G-code already exists for this SKU.')
        definition = _resolved_profile(settings_overrides)
        source_bytes = source.read_bytes()
        source_hash = hashlib.sha256(source_bytes).hexdigest()
        original_snapshot = destination / (sku + '.source.stl')
        original_snapshot.write_bytes(source_bytes)
        mesh = trimesh.load_mesh(io.BytesIO(source_bytes), file_type='stl', process=False)
        if not isinstance(mesh, trimesh.Trimesh) or not len(mesh.faces) or not np.isfinite(mesh.vertices).all():
            raise ValueError('The source must be a finite, nonempty STL mesh.')
        bounds = mesh.bounds.copy()
        source_to_normalized = _translation(-bounds[0])
        mesh.apply_transform(source_to_normalized)
        normalized = destination / (sku + '.normalized.stl')
        mesh.export(normalized)
        # Read the emitted float32 vertices, then reproduce Cura's integer
        # coordinate conversion. The source-to-snapshot shift stays unrounded.
        stored_mesh = trimesh.load_mesh(normalized, process=False)
        quantized = mm_to_um(stored_mesh.vertices)
        lower_um = quantized.min(axis=0)
        upper_um = quantized.max(axis=0)
        position_um = np.array([
            -lower_um[0] - (upper_um[0] - lower_um[0]) // 2,
            -lower_um[1] - (upper_um[1] - lower_um[1]) // 2,
            -lower_um[2],
        ], dtype=np.int64)
        values = definition['settings']
        for index, axis in enumerate('xyz'):
            values['mesh_position_' + axis]['default_value'] = float(position_um[index]) / 1000.0
        build_mm = np.array([values[key]['default_value'] for key in ('machine_width', 'machine_depth', 'machine_height')], dtype=float)
        build_um = mm_to_um(build_mm)
        group_um = np.array([build_um[0] // 2, build_um[1] // 2, 0])
        normalized_to_gcode = _translation((position_um + group_um) / 1000.0)
        source_to_gcode = normalized_to_gcode @ source_to_normalized
        model_bounds = np.array([lower_um, upper_um]) / 1000.0 + normalized_to_gcode[:3, 3]
        if np.any(model_bounds[0] < -0.001) or np.any(model_bounds[1] > build_mm + 0.001):
            raise ValueError('The positioned STL exceeds the recorded build envelope.')
        profile_path = destination / (sku + '.resolved.def.json')
        resolved_path = destination / (sku + '.resolved_settings.json')
        profile_path.write_text(json.dumps(definition, indent=2) + '\n', encoding='utf-8')
        resolved_path.write_text(json.dumps({k: v['default_value'] for k, v in values.items()}, indent=2) + '\n', encoding='utf-8')
        log_path = destination / (sku + '.engine.log.txt')
        args = [str(ENGINE), 'slice', '-m4', '-v', '-j', str(profile_path), '-e0', '-o', str(raw), '-l', str(normalized)]
        engine_start = time.monotonic()
        raw_owned = True
        try:
            process = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
        except subprocess.TimeoutExpired as error:
            output = error.stdout or b''
            error_output = error.stderr or b''
            if isinstance(output, bytes):
                output = output.decode('utf-8', errors='replace')
            if isinstance(error_output, bytes):
                error_output = error_output.decode('utf-8', errors='replace')
            log_path.write_text(output + '\n' + error_output + '\nTIMEOUT\n', encoding='utf-8')
            raise
        engine_elapsed = time.monotonic() - engine_start
        log_text = process.stdout + '\n' + process.stderr
        log_path.write_text(log_text, encoding='utf-8')
        if process.returncode != 0 or not raw.exists():
            raise RuntimeError(f'CuraEngine failed with code {process.returncode}; see {log_path}')
        # The command-line engine leaves placeholder file headers. Replace the
        # header using its final logged values, preserving every toolpath line.
        header_match = re.search(r'Gcode header after slicing: (;FLAVOR:.*?)(?:\n\s*\n)', log_text, re.S)
        if header_match is None:
            raise RuntimeError('Missing final CuraEngine header in the log.')
        gcode = raw.read_text(encoding='utf-8')
        gcode, replacements = re.subn(r'\A;FLAVOR:.*?\n\s*\n', header_match.group(1) + '\n\n', gcode, count=1, flags=re.S)
        if replacements != 1:
            raise RuntimeError('The placeholder G-code header could not be replaced.')
        raw.write_text('; TEMPORARY DEPOSITION ANALYSIS. DO NOT PRINT.\n' + gcode, encoding='utf-8')
        envelope = _gcode_envelope(raw, build_mm)
        if not envelope['motion_inside_build_envelope']:
            raise RuntimeError('Generated G-code moves exceed the build envelope; see ' + str(log_path))
        engine_filament = re.findall(r'Filament \(mm\^3\): (\d+(?:\.\d+)?)', log_text)
        if not engine_filament:
            raise RuntimeError('Missing final engine filament volume.')
        return {
            'sku': sku, 'source_stl_path': str(source), 'source_sha256': source_hash,
            'original_snapshot_path': str(original_snapshot), 'original_snapshot_sha256': sha256(original_snapshot),
            'normalized_snapshot_path': str(normalized), 'normalized_snapshot_sha256': sha256(normalized),
            'source_bounds_mm': bounds.tolist(), 'normalized_snapshot_bounds_mm': stored_mesh.bounds.tolist(),
            'source_to_normalized_snapshot_transform': source_to_normalized.tolist(),
            'normalized_snapshot_to_gcode_transform': normalized_to_gcode.tolist(),
            'source_to_gcode_transform': source_to_gcode.tolist(),
            'gcode_to_source_transform': np.linalg.inv(source_to_gcode).tolist(),
            'transform_convention': 'Row-major 4x4 matrices multiply homogeneous column vectors; translations are millimetres.',
            'model_bounds_in_gcode_mm': model_bounds.tolist(), 'build_envelope_mm': build_mm.tolist(),
            'engine_coordinate_quantization_mm': 0.001,
            'maximum_float32_export_error_mm': float(np.abs(stored_mesh.vertices - mesh.vertices).max()),
            'maximum_engine_vertex_rounding_error_mm': float(np.abs(quantized / 1000.0 - stored_mesh.vertices).max()),
            'coordinate_limitation': 'The matrix exactly records commanded frame translations. Float32 export and 0.001 mm engine vertex quantization alter geometry separately.',
            'coordinate_source_url': COORDINATE_SOURCE_URL, 'rounding_source_url': ROUNDING_SOURCE_URL,
            'profile_path': str(profile_path), 'profile_sha256': sha256(profile_path),
            'resolved_settings_path': str(resolved_path), 'resolved_settings_sha256': sha256(resolved_path),
            'base_profile_sha256': BASE_PROFILE_SHA256, 'settings_overrides': settings_overrides or {},
            'log_path': str(log_path), 'log_sha256': sha256(log_path),
            'raw_temporary_path': str(raw), 'raw_temporary_sha256': sha256(raw),
            'raw_file_disposition': 'Caller must consume, disable all commands, gzip, and remove this temporary file.',
            'engine_path': str(ENGINE), 'engine_version': ENGINE_VERSION, 'engine_sha256': ENGINE_SHA256,
            'return_code': process.returncode, 'command': args,
            'elapsed_seconds': engine_elapsed, 'total_wrapper_seconds': time.monotonic() - start,
            'engine_filament_volume_mm3': float(engine_filament[-1]), **envelope,
        }
    except BaseException:
        if raw_owned and raw.exists() and raw.parent == destination:
            raw.unlink()
        raise
    finally:
        lock.unlink(missing_ok=True)
