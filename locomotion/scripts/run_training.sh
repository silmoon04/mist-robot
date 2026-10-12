#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
mist_python="${MIST_PYTHON:-python3}"
if [[ "$#" -lt 1 ]]; then
    echo "Usage: MIST_PYTHON=/path/to/python bash scripts/run_training.sh ppo-seed42 [run_job.py options]" >&2
    exit 2
fi
job_id="$1"
shift
exec "$mist_python" "$script_dir/run_job.py" --job "$job_id" "$@"
