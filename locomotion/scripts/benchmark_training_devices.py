#!/usr/bin/env python3
"""Screen CPU/CUDA training throughput with sequential 8192-transition smoke jobs."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from locomotion.provenance import source_hashes, check_sources, identity, verify_checkpoint

TRANSITIONS = 8192
COMMON = [
    "--timesteps", str(TRANSITIONS), "--threads", "1", "--terrain", "mixed",
    "--randomize", "--max-steps", "1000", "--sensor-mode", "mpu6050",
    "--checkpoint-freq", "25000", "--eval-freq", "25000",
    "--eval-seed", "1000000", "--eval-episodes", "1", "--eval-speed", "0.01",
    "--eval-max-steps", "960", "--eval-terrains", "flat",
    "--eval-payloads", "[0,0.155]", "--eval-randomize", "--batch-size", "64",
    "--learning-rate", "0.0003", "--ppo-n-steps", "512", "--ppo-n-epochs", "5",
    "--sac-buffer-size", "100000", "--sac-learning-starts", "512",
    "--sac-gradient-steps", "1", "--save-replay-buffer", "--smoke",
]
LIMITATION = (
    "Endpoint throughput screen only; this does not measure 15-minute thermal capacity. "
    "PyBullet physics runs on CPU. Validation scores must not select a policy or checkpoint. "
    "These are fresh smoke jobs, not qualified walking policies. CPU/CUDA numerical results may differ."
)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_report(path, report):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def commands(args):
    jobs = []
    for workers in args.n_envs:
        for algorithm in args.algos:
            for device in args.devices:
                name = f"{algorithm}-{device}-{workers}envs-seed{args.seed}"
                output = args.output_root / name
                command = [args.python, str(REPO / "locomotion/train.py"),
                           "--algo", algorithm, "--device", device,
                           "--n-envs", str(workers), "--seed", str(args.seed),
                           *COMMON, "--output", str(output)]
                jobs.append({"name": name, "algorithm": algorithm, "device": device,
                             "n_envs": workers, "seed": args.seed, "output": str(output),
                             "command": command, "status": "not_run"})
    return jobs


def preflight(python, devices):
    # Use the trainer's device check in the interpreter that will run every job.
    code = """
import json, platform, sys
from importlib import metadata
import torch
from locomotion.train import checked_device
details = []
for requested in json.loads(sys.argv[1]):
    _, record = checked_device(requested)
    if requested.startswith('cuda'):
        torch.cuda.synchronize(torch.device(requested))
    details.append(record)
versions = {name: metadata.version(name) for name in
            ('stable-baselines3', 'gymnasium', 'pybullet', 'torch', 'numpy')}
print('BENCHMARK_RUNTIME=' + json.dumps({'python': sys.version, 'executable': sys.executable,
      'platform': platform.platform(), 'devices': details, 'versions': versions}))
"""
    completed = subprocess.run([python, "-c", code, json.dumps(devices)], cwd=REPO,
                               capture_output=True, text=True, timeout=120, check=False)
    if completed.returncode:
        raise RuntimeError(f"Runtime preflight failed ({completed.returncode}): "
                           f"{completed.stderr.strip()} {completed.stdout.strip()}")
    records = [line.removeprefix("BENCHMARK_RUNTIME=") for line in completed.stdout.splitlines()
               if line.startswith("BENCHMARK_RUNTIME=")]
    if len(records) != 1:
        raise RuntimeError("Runtime preflight did not emit exactly one metadata record")
    runtime = json.loads(records[0])
    try:
        gpu = subprocess.run([
            "nvidia-smi", "--query-gpu=name,driver_version,memory.total,power.limit",
            "--format=csv,noheader"], capture_output=True, text=True, timeout=15, check=False)
        runtime["nvidia_smi"] = {"returncode": gpu.returncode, "stdout": gpu.stdout.strip(),
                                 "stderr": gpu.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as error:
        runtime["nvidia_smi"] = {"unavailable": str(error)}
    return runtime


def run_trainer(command, log, timeout):
    started = time.perf_counter()
    with log.open("x", encoding="utf-8") as handle:
        child = subprocess.Popen(command, cwd=REPO, stdout=handle, stderr=subprocess.STDOUT,
                                 start_new_session=os.name == "posix")
        try:
            returncode = child.wait(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            # Kill the Linux process group, including spawned CPU physics workers.
            if os.name == "posix":
                os.killpg(child.pid, signal.SIGKILL)
            else:
                child.kill()
            child.wait()
            raise
    return returncode, time.perf_counter() - started


def completed_metrics(job, sources, wall_seconds):
    output = Path(job["output"])
    run = json.loads((output / "run.json").read_text())
    summary = json.loads((output / "training_summary.json").read_text())
    if run["source_sha256"] != sources or run["envelope"]["sources"] != sources:
        raise ValueError("Trainer source envelope differs from benchmark sources")
    if identity(run["envelope"]) != run["envelope_sha256"]:
        raise ValueError("Trainer envelope hash mismatch")
    for key, value in {"algo": job["algorithm"], "device": job["device"],
                       "n_envs": job["n_envs"], "seed": job["seed"], "threads": 1,
                       "timesteps": TRANSITIONS, "smoke": True, "eval_seed": 1000000,
                       "eval_max_steps": 960, "eval_terrains": ["flat"],
                       "eval_payloads": [0, .155], "resume": None}.items():
        if run["arguments"].get(key) != value:
            raise ValueError(f"Trainer argument mismatch: {key}")
    if run["device"]["selected"] != job["device"]:
        raise ValueError("Trainer device differs from requested device")
    if (summary["interrupted"] or summary["actual_additional_timesteps"] != TRANSITIONS
            or summary["total_timesteps"] != TRANSITIONS
            or summary["expected_additional_timesteps"] != TRANSITIONS
            or summary["status"] != "novice_pipeline_smoke_test"
            or summary["algorithm"] != job["algorithm"]):
        raise ValueError("Trainer did not complete the matched fresh smoke budget")
    updates = summary["optimizer_updates"]
    if type(updates) is not int or updates <= 0:
        raise ValueError("Trainer did not record optimizer updates")
    replay = output / "final_replay_buffer.pkl" if job["algorithm"] == "sac" else None
    checkpoint = verify_checkpoint(output / "final.zip", job["algorithm"],
                                   run["envelope"]["experiment"], replay)
    evaluations = [json.loads(line) for line in (output / "evaluations.jsonl").read_text().splitlines()]
    if [(record["label"], record["training_timesteps"]) for record in evaluations] != [
            ("initial", 0), ("final", TRANSITIONS)]:
        raise ValueError("Expected exactly initial and final validation receipts")
    evaluation_seconds = sum(record["elapsed_seconds"] for record in evaluations)
    trainer_seconds = summary["elapsed_seconds_including_evaluation"]
    if not all(math.isfinite(value) and value > 0 for value in
               (wall_seconds, trainer_seconds, evaluation_seconds)) or evaluation_seconds >= trainer_seconds:
        raise ValueError("Invalid training/evaluation timing")
    return {
        "wall_seconds_including_startup_and_initial_final_evaluation": wall_seconds,
        "wall_transitions_per_second": TRANSITIONS / wall_seconds,
        "trainer_seconds_including_initial_final_evaluation": trainer_seconds,
        "evaluation_seconds_from_receipts": evaluation_seconds,
        "trainer_seconds_excluding_evaluation_estimate": trainer_seconds - evaluation_seconds,
        "non_evaluation_transitions_per_second_estimate": TRANSITIONS / (trainer_seconds - evaluation_seconds),
        "non_evaluation_timing_scope": "Rollout and optimization plus model construction/checkpoint I/O overhead; no optimizer-only measurement.",
        "actual_transitions": summary["actual_additional_timesteps"], "optimizer_updates": updates,
        "update_count_scope": "SB3 _n_updates: PPO completed training epochs; SAC gradient steps. Counts are not comparable across algorithms.",
        "device": run["device"], "versions": run["versions"], "platform": run["platform"],
        "envelope_sha256": run["envelope_sha256"], "envelope": run["envelope"],
        "checkpoint_sha256": checkpoint["checkpoint_sha256"],
        "replay_sha256": checkpoint["replay_sha256"],
        "effective_model_parameters": json.loads((output / "effective_model_parameters.json").read_text()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable, help="Trainer interpreter; CUDA jobs require a verified CUDA runtime.")
    parser.add_argument("--output-root", required=True, type=Path, help="New directory for this screen; existing paths are refused.")
    parser.add_argument("--algos", nargs="+", choices=["ppo", "sac"], default=["ppo", "sac"])
    parser.add_argument("--devices", nargs="+", choices=["cpu", "cuda"], default=["cpu", "cuda"])
    parser.add_argument("--n-envs", nargs="+", type=int, choices=[2, 4], default=[2])
    parser.add_argument("--seed", type=int, default=630042)
    parser.add_argument("--timeout-seconds", type=int, default=3600, help="Maximum wall time per job; stop and report on timeout.")
    parser.add_argument("--plan", action="store_true", help="Print exact argv commands without running or creating files.")
    args = parser.parse_args()
    args.output_root = args.output_root.resolve()
    if args.seed < 0 or args.seed + max(args.n_envs) >= 1000000 or args.timeout_seconds < 1:
        parser.error("Training seed range must stay below 1000000 and timeout must be positive")
    for values in (args.algos, args.devices, args.n_envs):
        if len(values) != len(set(values)):
            parser.error("Repeated algorithms, devices or worker counts are unsupported")
    if args.output_root.exists():
        raise FileExistsError(f"Refusing existing output root: {args.output_root}")
    sources = source_hashes()
    frozen = json.loads((REPO / "locomotion/handoff/frozen_sources.json").read_text())
    if sources != frozen:
        raise RuntimeError("Current source/CAD hashes differ from the frozen handoff")
    jobs = commands(args)
    if args.plan:
        print(json.dumps({"commands": [job["command"] for job in jobs], "source_sha256": sources,
                          "source_identity": identity(sources), "limitation": LIMITATION}, indent=2))
        return 0
    args.output_root.mkdir(parents=True, exist_ok=False)
    report_path = args.output_root / "benchmark_report.json"
    helper_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report = {"schema": 1, "status": "running", "started_utc": utc_now(),
              "requested_transitions_per_job": TRANSITIONS, "execution": "sequential",
              "source_sha256": sources, "source_identity": identity(sources),
              "helper_sha256": helper_sha, "jobs": jobs, "limitation": LIMITATION}
    write_report(report_path, report)
    active = None
    try:
        report["runtime"] = preflight(args.python, args.devices)
        for job in jobs:
            active = job
            check_sources(sources)
            job.update(status="running", started_utc=utc_now())
            write_report(report_path, report)
            print(json.dumps(job["command"]), flush=True)
            returncode, seconds = run_trainer(job["command"], args.output_root / (job["name"] + ".log"), args.timeout_seconds)
            job.update(returncode=returncode, completed_utc=utc_now(), wall_seconds=seconds)
            check_sources(sources)
            if returncode:
                raise RuntimeError(f"Trainer exited with code {returncode}; see {job['name']}.log")
            job["metrics"] = completed_metrics(job, sources, seconds)
            job["status"] = "completed"
            write_report(report_path, report)
        report["status"] = "completed"
    except (Exception, KeyboardInterrupt) as error:
        report.update(status="incomplete", error=f"{type(error).__name__}: {error}")
        if active is not None:
            active.update(status="incomplete", error=report["error"], completed_utc=utc_now())
    finally:
        try:
            check_sources(sources)
            if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != helper_sha:
                raise RuntimeError("Benchmark helper changed during execution")
            report["sources_verified_after"] = True
        except Exception as error:
            report.update(status="incomplete", sources_verified_after=False,
                          source_verification_error=f"{type(error).__name__}: {error}")
        report["completed_utc"] = utc_now()
        write_report(report_path, report)
    print(f"{report['status']}: {report_path}", flush=True)
    return 0 if report["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
