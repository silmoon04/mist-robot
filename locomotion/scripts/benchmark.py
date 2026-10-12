#!/usr/bin/env python3
"""Measure CPU rollout throughput for 1, 2 and 4 simulation workers."""
import argparse
from functools import partial
import json
from pathlib import Path
import sys
import time

import numpy as np
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from train import make_env, write_json
from provenance import source_hashes, check_sources
from sensor_sim import SimulatedIMU


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=500, help="Vector steps per measurement; total transitions = steps * workers.")
    parser.add_argument("--warmup", type=int, default=50)
    parser.add_argument("--workers", nargs="+", type=int, default=[1, 2, 4])
    parser.add_argument("--env-module", default="mist_env")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "runs" / "cpu_benchmark.json")
    parser.add_argument("--sensor-mode",choices=["mpu6050","phone","none"],default="mpu6050")
    parser.add_argument("--sensor-profile",type=json.loads)
    args = parser.parse_args()
    sensor=SimulatedIMU(args.sensor_mode,args.sensor_profile)
    profile=sensor.profile if args.sensor_mode!="none" else None
    frozen=source_hashes()
    if args.steps < 1 or args.warmup < 0 or any(n < 1 for n in args.workers):
        raise ValueError("Positive steps/workers and nonnegative warmup are required")
    results = []
    for workers in args.workers:
        before = time.perf_counter()
        kwargs = dict(command=(0.01, 0.0, 0.0), terrain="flat", randomize=True, payload=None, render_mode=None, max_steps=1000,sensor_mode=args.sensor_mode,sensor_profile=profile)
        if args.sensor_mode=="phone": kwargs["payload"]=.155
        factories = [partial(make_env, args.env_module, kwargs, 70 + i) for i in range(workers)]
        env = DummyVecEnv(factories) if workers == 1 else SubprocVecEnv(factories, start_method="spawn")
        try:
            env.seed(70)
            env.reset()
            startup = time.perf_counter() - before
            actions = np.zeros((workers, *env.action_space.shape), dtype=np.float32)
            for _ in range(args.warmup):
                env.step(actions)
            before = time.perf_counter()
            terminations = 0
            for _ in range(args.steps):
                observations, rewards, dones, info = env.step(actions)
                if not np.all(np.isfinite(observations)) or not np.all(np.isfinite(rewards)):
                    raise RuntimeError("Non-finite benchmark state")
                terminations += int(np.sum(dones))
            elapsed = time.perf_counter() - before
            result = dict(workers=workers, vector_steps=args.steps, transitions=args.steps * workers, elapsed_seconds=elapsed, transitions_per_second=args.steps * workers / elapsed, vector_steps_per_second=args.steps / elapsed, startup_seconds=startup, episode_ends=terminations)
            results.append(result)
            print(json.dumps(result), flush=True)
        finally:
            env.close()
    check_sources(frozen)
    write_json(args.output.resolve(), {
        "source_hashes":frozen,"sensor":{"mode":args.sensor_mode,"profile":profile},
        "backend": "PyBullet CPU physics; zero residual IK controller",
        "status": "throughput_only_not_gait_qualification",
        "results": results,
        "recommended_measured_worker_count": max(results, key=lambda r: r["transitions_per_second"])["workers"],
    })


if __name__ == "__main__":
    main()
