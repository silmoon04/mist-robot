#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
locomotion_dir="$(dirname -- "$script_dir")"
repo_dir="$(dirname -- "$locomotion_dir")"
if command -v uv >/dev/null 2>&1; then
    uv venv --python 3.11 "$repo_dir/.venv-locomotion"
    uv pip install --python "$repo_dir/.venv-locomotion/bin/python" 'torch==2.8.0+cpu' --index-url https://download.pytorch.org/whl/cpu
    uv pip install --python "$repo_dir/.venv-locomotion/bin/python" -r "$locomotion_dir/requirements.lock.txt"
else
    python3.11 -m venv "$repo_dir/.venv-locomotion"
    "$repo_dir/.venv-locomotion/bin/python" -m pip install 'torch==2.8.0+cpu' --index-url https://download.pytorch.org/whl/cpu
    "$repo_dir/.venv-locomotion/bin/python" -m pip install -r "$locomotion_dir/requirements.lock.txt"
fi
echo "CPU environment ready: $repo_dir/.venv-locomotion/bin/python"
