#!/usr/bin/env bash
# Separate Python 3.11 environment; never install the CPU lock into it.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
locomotion_dir="$(dirname -- "$script_dir")"
repo_dir="$(dirname -- "$locomotion_dir")"
mode="${1:-install}"
if [[ "$mode" != install && "$mode" != --verify-only ]] || (( $# > 1 )); then
    echo 'Usage: setup_cuda.sh [--verify-only]' >&2
    exit 2
fi
if [[ "$(uname -s)" != Linux ]]; then
    echo 'Run this script in Linux/Ubuntu WSL2 with the Windows NVIDIA driver available.' >&2
    exit 2
fi
bootstrap_python="${MIST_CUDA_PYTHON:-python3.11}"
env_dir="${MIST_CUDA_ENV:-$repo_dir/.venv-locomotion-cuda}"
lock_path="$locomotion_dir/requirements.lock.txt"
torch_index='https://download.pytorch.org/whl/cu126'
torch_pin='torch==2.8.0+cu126'
"$bootstrap_python" -c 'import sys; assert sys.version_info[:2] == (3, 11), "Python 3.11 is required"'
env_dir="$("$bootstrap_python" -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).expanduser().resolve())' "$env_dir")"
cpu_dir="$("$bootstrap_python" -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())' "$repo_dir/.venv-locomotion")"
if [[ "$env_dir" == "$cpu_dir" || "${env_dir##*/}" == .venv-locomotion || "$env_dir" == / || "$env_dir" == "$repo_dir" ]]; then
    echo "Refusing unsafe/CPU environment destination: $env_dir" >&2
    exit 2
fi
lock_sha="$("$bootstrap_python" - "$lock_path" <<'PY'
import hashlib, pathlib, sys
data = pathlib.Path(sys.argv[1]).read_bytes()
lines = data.decode('utf-8').splitlines()
assert lines.count('torch==2.8.0+cpu') == 1, 'Expected exactly one unchanged CPU Torch pin'
assert sum(line.lower().startswith('torch') for line in lines) == 1, 'Unexpected additional Torch requirements'
print(hashlib.sha256(data).hexdigest())
PY
)"
if [[ "$mode" == install ]]; then
    if [[ ! -e "$env_dir" ]]; then
        "$bootstrap_python" -m venv "$env_dir"
    elif [[ ! -f "$env_dir/pyvenv.cfg" || ! -x "$env_dir/bin/python" ]]; then
        echo "Destination exists but is not a Python venv: $env_dir. Choose a new MIST_CUDA_ENV." >&2
        exit 2
    fi
fi
python="$env_dir/bin/python"
"$python" - "$env_dir" <<'PY'
import pathlib, sys
env = pathlib.Path(sys.argv[1]).resolve()
assert sys.version_info[:2] == (3, 11), 'Environment must use Python 3.11'
assert pathlib.Path(sys.prefix).resolve() == env and sys.prefix != sys.base_prefix, 'Expected a separate venv'
cfg = (env / 'pyvenv.cfg').read_text().lower()
assert 'include-system-site-packages = false' in cfg, 'System site packages must be disabled'
PY
marker="$env_dir/.mist-cuda-setup.json"
if [[ "$mode" == install ]]; then
    "$python" - "$marker" "$lock_sha" <<'PY'
import importlib.metadata as md, json, pathlib, sys
marker, lock_sha = pathlib.Path(sys.argv[1]), sys.argv[2]
expected = {'schema': 1, 'lock_sha256': lock_sha, 'torch': '2.8.0+cu126'}
if marker.exists():
    assert json.loads(marker.read_text()) == expected, 'Setup marker differs; choose a new MIST_CUDA_ENV'
else:
    packages = {d.metadata['Name'].lower().replace('_', '-') for d in md.distributions()}
    assert packages <= {'pip', 'setuptools', 'wheel'}, 'Existing environment contains packages; choose a new MIST_CUDA_ENV or use --verify-only'
    marker.write_text(json.dumps(expected, indent=2) + '\n')
PY
fi
record_dir="$env_dir/mist-cuda-records/$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p -- "$record_dir"
on_exit() {
    code=$?
    if (( code != 0 )); then
        printf 'failed (exit %s)\n' "$code" > "$record_dir/status.txt"
        echo "CUDA setup failed. Evidence: $record_dir" >&2
        echo "The CPU environment and lock are unchanged. Rerun with the same MIST_CUDA_ENV and MIST_CUDA_PYTHON; incompatible existing environments need a new path." >&2
    fi
}
trap on_exit EXIT
"$python" - "$lock_path" "$record_dir/requirements-without-cpu-torch.txt" <<'PY'
import pathlib, sys
source, target = map(pathlib.Path, sys.argv[1:])
lines = source.read_text().splitlines(keepends=True)
target.write_text(''.join(line for line in lines if line.rstrip('\r\n') != 'torch==2.8.0+cpu'))
PY
printf '%s\n' "$torch_pin" > "$record_dir/torch-constraint.txt"
if [[ "$mode" == install ]]; then
    if ! "$python" -m pip --version >/dev/null 2>&1; then
        "$python" -m ensurepip
    fi
    "$python" -m pip --isolated install "$torch_pin" --index-url "$torch_index" \
        --report "$record_dir/torch-install.json" 2>&1 | tee "$record_dir/torch-install.log"
    "$python" -m pip --isolated install -r "$record_dir/requirements-without-cpu-torch.txt" \
        -c "$record_dir/torch-constraint.txt" --index-url https://pypi.org/simple \
        --report "$record_dir/dependencies-install.json" 2>&1 | tee "$record_dir/dependencies-install.log"
fi
"$python" -m pip --isolated check 2>&1 | tee "$record_dir/pip-check.txt"
"$python" -m pip --isolated freeze --all > "$record_dir/pip-freeze.txt"
"$python" -m pip --isolated inspect > "$record_dir/pip-inspect.json"
nvidia_smi="$(command -v nvidia-smi || true)"
if [[ -z "$nvidia_smi" && -x /usr/lib/wsl/lib/nvidia-smi ]]; then
    nvidia_smi=/usr/lib/wsl/lib/nvidia-smi
fi
if [[ -n "$nvidia_smi" ]]; then
    "$nvidia_smi" > "$record_dir/nvidia-smi.txt" 2>&1 || true
    "$nvidia_smi" --query-gpu=name,driver_version,memory.total --format=csv,noheader > "$record_dir/nvidia-gpus.csv" 2>&1 || true
fi
"$python" - "$record_dir" "$lock_path" "$script_dir/setup_cuda.sh" "$torch_index" "$mode" <<'PY'
import datetime, hashlib, importlib.metadata as md, json, os, pathlib, platform, sys
import torch
record, lock, script = map(pathlib.Path, sys.argv[1:4])
for line in lock.read_text().splitlines():
    if not line or line.startswith('#') or line == 'torch==2.8.0+cpu':
        continue
    name, version = line.split('==')
    actual = md.version(name)
    assert actual == version, f'Lock mismatch for {name}: {actual} != {version}'
assert md.version('torch') == '2.8.0+cu126', f'Incorrect installed Torch: {md.version("torch")}'
assert torch.__version__ == '2.8.0+cu126', f'Incorrect imported Torch: {torch.__version__}'
assert torch.version.cuda == '12.6', f'Incorrect CUDA runtime: {torch.version.cuda}'
assert torch.cuda.is_available(), 'CUDA unavailable: check the Windows NVIDIA driver and WSL GPU visibility'
devices = []
for i in range(torch.cuda.device_count()):
    with torch.cuda.device(i):
        a = torch.ones((64, 64), device=f'cuda:{i}', dtype=torch.float32)
        product = a @ a
        torch.cuda.synchronize(i)
        assert product.is_cuda and torch.equal(product.cpu(), torch.full((64, 64), 64.0)), 'CUDA matmul failed'
        props = torch.cuda.get_device_properties(i)
        devices.append({'index': i, 'name': props.name, 'total_memory_bytes': props.total_memory,
                        'compute_capability': list(torch.cuda.get_device_capability(i)),
                        'check': 'CUDA allocation, 64x64 float32 matmul, synchronization and exact CPU comparison passed'})
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
metadata = {
    'schema': 1, 'verified_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'mode': sys.argv[5], 'python_executable': sys.executable, 'python_version': sys.version,
    'venv': sys.prefix, 'platform': platform.platform(), 'kernel': platform.release(),
    'torch': torch.__version__, 'cuda_runtime': torch.version.cuda, 'torch_index': sys.argv[4],
    'cpu_lock_path': str(lock.resolve()), 'cpu_lock_sha256': sha(lock),
    'derived_requirements_sha256': sha(record / 'requirements-without-cpu-torch.txt'),
    'setup_script_sha256': sha(script), 'pip_version': md.version('pip'), 'devices': devices,
    'cuda_visible_devices': os.environ.get('CUDA_VISIBLE_DEVICES'),
    'artifacts': {p.name: sha(p) for p in sorted(record.iterdir()) if p.is_file()},
    'scope': 'Policy CUDA runtime verified; PyBullet physics remains CPU. No training or policy qualification.'
}
(record / 'environment.json').write_text(json.dumps(metadata, indent=2) + '\n')
print(json.dumps({'torch': metadata['torch'], 'cuda_runtime': metadata['cuda_runtime'], 'devices': devices}, indent=2))
PY
printf 'verified\n' > "$record_dir/status.txt"
echo "CUDA environment verified: $python"
echo "Environment evidence: $record_dir"
printf 'Set interpreter: export MIST_PYTHON=%q\n' "$python"
