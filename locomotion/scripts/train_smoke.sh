#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
locomotion_dir="$(dirname -- "$script_dir")"
mist_python="${MIST_PYTHON:-python3}"
run_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
output_root="${1:-$locomotion_dir/runs/smoke-$run_stamp}"
"$mist_python" "$locomotion_dir/train.py" --algo ppo --terrain flat --smoke --timesteps 2048 --seed 42 --device cpu --n-envs 1 --ppo-n-steps 256 --eval-freq 1024 --checkpoint-freq 1024 --eval-max-steps 480 --output "$output_root/ppo"
"$mist_python" "$locomotion_dir/train.py" --algo sac --terrain flat --smoke --timesteps 2048 --seed 42 --device cpu --n-envs 1 --eval-freq 1024 --checkpoint-freq 1024 --eval-max-steps 480 --output "$output_root/sac"
