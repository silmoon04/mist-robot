#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(dirname -- "$(dirname -- "$script_dir")")"
if [[ -n "${MIST_PYTHON:-}" ]]; then
    mist_python="$MIST_PYTHON"
elif [[ -x "$repo_dir/.venv-locomotion/bin/python" ]]; then
    mist_python="$repo_dir/.venv-locomotion/bin/python"
elif [[ -x "$repo_dir/../../work/py311/bin/python" ]]; then
    mist_python="$repo_dir/../../work/py311/bin/python"
else
    echo "Run scripts/setup_cpu.sh or set MIST_PYTHON to your Python environment." >&2
    exit 2
fi
cd -- "$repo_dir"
exec "$mist_python" -m locomotion.sim_remote "$@"
