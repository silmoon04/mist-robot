#!/usr/bin/env python3
"""Audit, package, or validate the portable MIST simulation tree."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tempfile
import zipfile

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from locomotion.provenance import source_hashes

SKIP = {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.pio',
        '.git', '.venv', '.venv-locomotion', 'venv', 'work', 'retired'}
PREFIX = 'mist-robot'
MANIFEST = 'PACKAGE_MANIFEST.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_relative(name):
    """Reject POSIX/Windows escapes before filesystem access or extraction."""
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        raise ValueError(f'Unsafe archive path: {name!r}')
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ('', '.', '..') for part in name.split('/')):
        raise ValueError(f'Unsafe archive path: {name!r}')
    return path


def source_file(name):
    relative = safe_relative(name)
    path = REPO.joinpath(*relative.parts)
    if path.resolve().is_relative_to(REPO) is False:
        raise ValueError(f'Source escapes repository: {name}')
    # Reject links, including parent directories; do not copy a redirected tree.
    current = REPO
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f'Symlink is not portable: {current}')
    if not path.is_file():
        raise FileNotFoundError(path)
    if SKIP.intersection(relative.parts):
        raise ValueError(f'Required file is in an excluded directory: {name}')
    return path


def inventory():
    required = source_hashes()
    names = set(required)
    for path in (REPO / 'locomotion').rglob('*'):
        relative = path.relative_to(REPO)
        if SKIP.intersection(relative.parts) or path.suffix in ('.pyc', '.pyo'):
            continue
        if path.is_symlink():
            raise ValueError(f'Symlink is not portable: {path}')
        if path.is_file():
            names.add(relative.as_posix())
    # Include current-source CAD exports, without unrelated old design families.
    for directory in ('single_leg_r7_wide_joints_20260914', 'main_hub_20260915'):
        for path in (REPO / 'design' / directory / 'output').rglob('*'):
            if path.suffix.lower() in ('.step', '.stp', '.f3d'):
                names.add(path.relative_to(REPO).as_posix())
    files = {name: sha(source_file(name)) for name in sorted(names)}
    if any(files[name] != value for name, value in required.items()):
        raise RuntimeError('Required sources changed during inventory')
    return {'schema': 1, 'root': PREFIX, 'files': files, 'required_sources': required,
            'excluded_directory_names': sorted(SKIP),
            'scope': 'Simulation, evidence, source dependencies and current-source CAD exports; physical transfer unvalidated'}


def create_archive(output, manifest):
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f'Refusing to overwrite {output}')
    if output.is_relative_to(REPO):
        raise ValueError('Archive output must be outside mist-robot to avoid recursive packaging')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Private temporary archive becomes visible only after every content check passes.
    with tempfile.TemporaryDirectory(prefix='mist-package-', dir=output.parent) as tmp:
        pending = Path(tmp) / 'package.zip'
        with zipfile.ZipFile(pending, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for name, expected in manifest['files'].items():
                path = source_file(name)
                content = path.read_bytes()
                if hashlib.sha256(content).hexdigest() != expected:
                    raise RuntimeError(f'File changed while packaging: {name}')
                info = zipfile.ZipInfo(f'{PREFIX}/{name}')
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (stat.S_IFREG | (path.stat().st_mode & 0o777)) << 16
                archive.writestr(info, content)
            archive.writestr(f'{PREFIX}/{MANIFEST}', json.dumps(manifest, indent=2) + '\n')
        if source_hashes() != manifest['required_sources']:
            raise RuntimeError('Required sources changed during packaging')
        # Hard-link publication is atomic and cannot overwrite an existing output.
        output.hardlink_to(pending)
    return output


def validate_archive(path, relocate=False):
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = [item.filename for item in entries]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive members')
        for item in entries:
            relative = safe_relative(item.filename)
            if relative.parts[0] != PREFIX or len(relative.parts) < 2:
                raise ValueError('Unexpected archive root')
            if SKIP.intersection(relative.parts):
                raise ValueError('Excluded directory found in archive')
            mode = stat.S_IFMT(item.external_attr >> 16)
            if mode not in (0, stat.S_IFREG) or item.is_dir():
                raise ValueError('Archive must contain regular files only')
        manifest = json.loads(archive.read(f'{PREFIX}/{MANIFEST}'))
        if manifest.get('schema') != 1 or manifest.get('root') != PREFIX:
            raise ValueError('Unsupported manifest')
        expected_names = {f'{PREFIX}/{safe_relative(name)}' for name in manifest['files']}
        if set(names) != expected_names | {f'{PREFIX}/{MANIFEST}'}:
            raise ValueError('Manifest and archive members differ')
        for name, expected in manifest['files'].items():
            if hashlib.sha256(archive.read(f'{PREFIX}/{name}')).hexdigest() != expected:
                raise ValueError(f'Content hash mismatch: {name}')
        for name, expected in manifest['required_sources'].items():
            if manifest['files'].get(name) != expected:
                raise ValueError(f'Required dependency absent or changed: {name}')
        if relocate:
            with tempfile.TemporaryDirectory(prefix='mist-relocated-') as tmp:
                # All paths were checked before extraction; avoid ZipFile.extractall.
                for item in entries:
                    target = Path(tmp).joinpath(*safe_relative(item.filename).parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(item.filename))
                code = ('import json; from locomotion.provenance import source_hashes; '
                        'from locomotion.mist_env import MistEnv; '
                        'm=json.load(open("PACKAGE_MANIFEST.json")); '
                        'assert source_hashes()==m["required_sources"]; '
                        'e=MistEnv(randomize=False); o,i=e.reset(seed=7); '
                        'e.step(e.action_space.sample()*0); e.close(); '
                        'print("Relocated dependency hashes and nominal reset/step passed", o.shape)')
                subprocess.run([sys.executable, '-c', code], cwd=Path(tmp) / PREFIX, check=True,
                               timeout=120)
    return {'files': len(manifest['files']), 'required_sources': len(manifest['required_sources']),
            'archive_sha256': sha(path), 'relocated': relocate}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--create', action='store_true', help='Create only after final results/docs are frozen')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--validate', type=Path, help='Validate an existing archive')
    parser.add_argument('--relocate', action='store_true', help='Also extract and reset/step using this interpreter')
    args = parser.parse_args()
    if args.validate:
        if args.create or args.output:
            parser.error('--validate cannot be combined with creation options')
        print(json.dumps(validate_archive(args.validate, args.relocate), indent=2))
        return
    if args.relocate:
        parser.error('--relocate requires --validate')
    if args.create != bool(args.output):
        parser.error('Creation requires both --create and --output')
    manifest = inventory()
    report = {'mode': 'audit', 'files': len(manifest['files']),
              'required_sources': len(manifest['required_sources']),
              'uncompressed_bytes': sum(source_file(name).stat().st_size for name in manifest['files'])}
    if args.create:
        report.update(mode='created', output=str(create_archive(args.output, manifest)))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
