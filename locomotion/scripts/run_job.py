#!/usr/bin/env python3
"""Run one prepared training job locally or on a machine you supply."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=root / "training_queue.json")
    parser.add_argument("--job", required=True)
    parser.add_argument("--device", default="cpu", help="cpu or cuda[:index]; CUDA only accelerates the policy network.")
    parser.add_argument("--n-envs", type=int, help="Override the prepared CPU physics worker count.")
    parser.add_argument("--output-root", type=Path, default=root / "runs" / "queued")
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--replay-buffer", type=Path)
    parser.add_argument("--print-command", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    matching = [job for job in manifest["jobs"] if job["id"] == args.job]
    if len(matching) != 1:
        raise ValueError(f"Expected exactly one job named {args.job}; choose from {[j['id'] for j in manifest['jobs']]}")
    job = matching[0]
    output = args.output_root.resolve() / job["id"]
    command = [sys.executable, str(root / "train.py"), *job["arguments"], "--device", args.device, "--output", str(output)]
    if args.n_envs is not None:
        command.extend(["--n-envs", str(args.n_envs)])
    if args.resume:
        command.extend(["--resume", str(args.resume.resolve())])
    if args.replay_buffer:
        command.extend(["--replay-buffer", str(args.replay_buffer.resolve())])
    print(json.dumps(command), flush=True)
    if args.print_command:
        return
    output.mkdir(parents=True, exist_ok=True)
    receipt = {
        "job": job, "command": command,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "status": "running", "provider": "none; executing on the current machine",
    }
    receipt_path = output / f"job_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    completed = subprocess.run(command, cwd=root, check=False)
    receipt.update(completed_utc=datetime.now(timezone.utc).isoformat(), returncode=completed.returncode, status="completed" if completed.returncode == 0 else "failed")
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
