#!/usr/bin/env python3
"""Train a bounded residual policy; checkpoints are unvalidated on hardware."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from functools import partial
from importlib import import_module, metadata
import hashlib
import json
import math
from pathlib import Path
import platform
import time

import numpy as np
import torch
from stable_baselines3 import PPO, SAC
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.utils import set_random_seed
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv


try:
    from .provenance import source_hashes, check_sources, envelope, bind_checkpoint, verify_checkpoint, identity
    from .acceptance import COMMANDS, score, command_at
    from .sensor_sim import SimulatedIMU
except ImportError:
    from provenance import source_hashes, check_sources, envelope, bind_checkpoint, verify_checkpoint, identity
    from acceptance import COMMANDS, score, command_at
    from sensor_sim import SimulatedIMU
CARDINAL_COMMANDS = COMMANDS

def json_value(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, bool, int)) or value is None:
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(k): json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(v) for v in value]
    return str(value)


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(json_value(value), indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def make_env(module_name: str, kwargs: dict, seed: int, monitor_path=None):
    env = import_module(module_name).MistEnv(**kwargs)
    env.reset(seed=seed)
    env.action_space.seed(seed)
    return Monitor(env, filename=str(monitor_path) if monitor_path else None)


def checked_device(requested: str) -> tuple[str, dict]:
    if requested != "cpu" and requested != "cuda" and not requested.startswith("cuda:"):
        raise ValueError("--device must be cpu or cuda[:index]; automatic device fallback is disabled")
    details = {
        "requested": requested,
        "torch_version": torch.__version__,
        "torch_cuda_build": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(),
        "physics_device": "cpu",
    }
    if requested.startswith("cuda"):
        if not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA was requested but PyTorch cannot use it. No CPU fallback was made. "
                "Use --device cpu or configure a compatible NVIDIA driver and CUDA PyTorch build."
            )
        device = torch.device(requested)
        torch.zeros(1, device=device)
        index = device.index if device.index is not None else torch.cuda.current_device()
        details.update(gpu=torch.cuda.get_device_name(index), gpu_memory_bytes=torch.cuda.get_device_properties(index).total_memory)
    details["selected"] = requested
    return requested, details


def evaluate(model, args, output: Path, timestep: int, label: str, expected_sources=None):
    """Fixed evaluation cases never reuse the training seed range."""
    started = time.perf_counter()
    check_sources(expected_sources)
    records = []
    case = 0
    for terrain in args.eval_terrains:
        for payload in args.eval_payloads:
            for direction, unit in CARDINAL_COMMANDS.items():
                command = tuple(x * (args.eval_speed/.01 if i<2 else 1) for i,x in enumerate(unit))
                for repeat in range(args.eval_episodes):
                    episode_seed = args.eval_seed + case * args.eval_episodes + repeat
                    env = import_module(args.env_module).MistEnv(
                        command=command, terrain=terrain, randomize=args.eval_randomize,
                        payload=payload, render_mode=None, max_steps=args.eval_max_steps,
                        sensor_mode=args.sensor_mode, sensor_profile=args.sensor_profile,
                    )
                    try:
                        obs, reset_info = env.reset(seed=episode_seed)
                        total_reward = 0.0
                        terminated = truncated = False
                        info = {}
                        velocity_errors, saturations, tracking_errors = [], [], []
                        rows = []
                        for step in range(args.eval_max_steps):
                            env.command = np.asarray(command_at(direction, command, step, args.eval_max_steps))
                            action, _ = model.predict(obs, deterministic=True)
                            obs, reward, terminated, truncated, info = env.step(action)
                            if not np.isfinite(reward) or not np.all(np.isfinite(obs)):
                                raise RuntimeError(f"Non-finite evaluation state in case {direction}, seed {episode_seed}")
                            total_reward += float(reward)
                            rows.append(info)
                            measured_velocity = info.get("body_velocity", info.get("velocity"))
                            if measured_velocity is not None:
                                velocity_errors.append(float(np.linalg.norm(np.asarray(measured_velocity)[:2] - np.asarray(command)[:2])))
                            if "torque_saturation_fraction" in info:
                                saturations.append(float(info["torque_saturation_fraction"]))
                            if "tracking_error_rad" in info:
                                tracking_errors.append(float(info["tracking_error_rad"]))
                            if terminated or truncated:
                                break
                        records.append({
                            "acceptance": score(reset_info,rows,command,args.eval_max_steps),
                            "direction": direction, "command": command,
                            "terrain": terrain, "payload": payload, "seed": episode_seed,
                            "reward": total_reward, "steps": step + 1,
                            "terminated": bool(terminated), "truncated": bool(truncated),
                            "fell": bool(info.get("fell", terminated)),
                            "mean_velocity_error_m_s": float(np.mean(velocity_errors)) if velocity_errors else None,
                            "velocity_metric_frame": "body" if "body_velocity" in info else "world_fallback",
                            "mean_torque_saturation_fraction": float(np.mean(saturations)) if saturations else None,
                            "mean_tracking_error_rad": float(np.mean(tracking_errors)) if tracking_errors else None,
                            "initial_info": json_value(reset_info), "final_info": json_value(info),
                        })
                    finally:
                        env.close()
                case += 1
    check_sources(expected_sources)
    summary = {
        "eligible": all(r["acceptance"]["passed"] for r in records),
        "label": label, "training_timesteps": timestep,
        "suite_sha256":identity([{k:r[k] for k in ("direction","command","terrain","payload","seed")} for r in records]),
        "mean_reward": float(np.mean([r["reward"] for r in records])),
        "mean_steps": float(np.mean([r["steps"] for r in records])),
        "termination_fraction": float(np.mean([r["terminated"] for r in records])),
        "fall_fraction": float(np.mean([r["fell"] for r in records])),
        "elapsed_seconds": time.perf_counter() - started,
        "status": "simulation_evaluation_only_hardware_unvalidated",
        "ranking": "mean reward among candidates passing simulation-walking-v2; hardware remains unqualified",
        "episodes": records,
    }
    with (output / "evaluations.jsonl").open("a") as handle:
        handle.write(json.dumps(json_value(summary), allow_nan=False) + "\n")
    write_json(output / f"evaluation_{label}_{timestep}.json", summary)
    print(f"Evaluation {label} at {timestep}: mean_reward={summary['mean_reward']:.4f}, termination_fraction={summary['termination_fraction']:.3f}", flush=True)
    return summary


def save_checkpoint(model, path: Path, save_replay: bool):
    check_sources(model.experiment_envelope["sources"])
    model.save(str(path))
    if save_replay and isinstance(model, SAC):
        model.save_replay_buffer(str(path) + "_replay_buffer.pkl")
    replay = str(path) + "_replay_buffer.pkl" if save_replay and isinstance(model,SAC) else None
    bind_checkpoint(path,model.experiment_envelope,model.experiment_algorithm,model.experiment_status,replay,model.continuation_seed)


class ValidationCallback(BaseCallback):
    def __init__(self, args, output: Path, expected_sources, best_reward=-math.inf):
        super().__init__()
        self.args, self.output = args, output
        self.expected_sources = expected_sources
        self.best_reward = best_reward
        self.last_eval = self.last_checkpoint = 0
        self.evaluation_seconds = 0.0
        self.best_eval = None

    def _on_training_start(self):
        self.last_eval = self.last_checkpoint = self.num_timesteps

    def _on_step(self):
        if self.num_timesteps - self.last_checkpoint >= self.args.checkpoint_freq:
            check_sources(self.expected_sources)
            save_checkpoint(self.model, self.output / f"checkpoint_{self.num_timesteps}", self.args.save_replay_buffer)
            self.last_checkpoint = self.num_timesteps
        if self.num_timesteps - self.last_eval >= self.args.eval_freq:
            self.run_validation("periodic")
        return True

    def run_validation(self, label):
        result = evaluate(self.model, self.args, self.output, self.model.num_timesteps, label, self.expected_sources)
        self.evaluation_seconds += result["elapsed_seconds"]
        self.last_eval = self.model.num_timesteps
        if result["eligible"] and result["mean_reward"] > self.best_reward:
            self.best_reward = result["mean_reward"]
            self.best_eval = result
            save_checkpoint(self.model, self.output / "best", self.args.save_replay_buffer)
            write_json(self.output / "best_evaluation.json", result)
        return result


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--algo", choices=["ppo", "sac"], default="ppo")
    result.add_argument("--timesteps", type=int, default=1_001_472, help="Additional timesteps for a resumed run; PPO rounds to a complete rollout.")
    result.add_argument("--n-envs", type=int, default=1)
    result.add_argument("--seed", type=int, default=42)
    result.add_argument("--output", type=Path, default=Path(__file__).parent / "runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    result.add_argument("--device", default="cpu", help="cpu or cuda[:index]. PyBullet physics remains CPU.")
    result.add_argument("--threads", type=int, default=1)
    result.add_argument("--env-module", default="locomotion.mist_env" if __package__ else "mist_env")
    result.add_argument("--terrain", choices=["flat", "low_friction", "slope", "rough", "mixed"], default="mixed")
    result.add_argument("--payload", type=json.loads, default=None, help="JSON payload passed to MistEnv; omit for its default.")
    result.add_argument("--randomize", action=argparse.BooleanOptionalAction, default=True)
    result.add_argument("--max-steps", type=int, default=1000)
    result.add_argument("--sensor-mode", choices=["mpu6050","phone","none"], default="mpu6050")
    result.add_argument("--sensor-profile", type=json.loads, default=None)
    result.add_argument("--transfer", action="store_true", help="New experiment from compatible policy weights; resets scores and replay")
    result.add_argument("--resume", type=Path, help="Existing SB3 .zip checkpoint.")
    result.add_argument("--replay-buffer", type=Path, help="Matching SAC replay buffer when resuming.")
    result.add_argument("--save-replay-buffer", action=argparse.BooleanOptionalAction, default=True)
    result.add_argument("--checkpoint-freq", type=int, default=25_000)
    result.add_argument("--eval-freq", type=int, default=25_000)
    result.add_argument("--eval-seed", type=int, default=1_000_000)
    result.add_argument("--eval-episodes", type=int, default=1, help="Episodes per direction, terrain and payload combination.")
    result.add_argument("--eval-speed", type=float, default=0.01)
    result.add_argument("--eval-max-steps", type=int, default=960)
    result.add_argument("--eval-terrains", nargs="+", default=["flat"])
    result.add_argument("--eval-payloads", type=json.loads, default=[0.0, 0.155], help="JSON list of payload masses in kg; null uses the environment default.")
    result.add_argument("--eval-randomize", action=argparse.BooleanOptionalAction, default=True)
    result.add_argument("--batch-size", type=int, default=64)
    result.add_argument("--learning-rate", type=float, default=3e-4)
    result.add_argument("--ppo-n-steps", type=int, default=512)
    result.add_argument("--ppo-n-epochs", type=int, default=5)
    result.add_argument("--sac-buffer-size", type=int, default=100_000)
    result.add_argument("--sac-learning-starts", type=int, default=512)
    result.add_argument("--sac-gradient-steps", type=int, default=1)
    result.add_argument("--smoke", action="store_true", help="Label this as a pipeline smoke test, not a qualified policy.")
    return result


def main():
    args = parser().parse_args()
    for key in ["timesteps", "n_envs", "threads", "max_steps", "checkpoint_freq", "eval_freq", "eval_episodes", "eval_max_steps", "batch_size", "ppo_n_steps", "ppo_n_epochs", "sac_buffer_size"]:
        if getattr(args, key) < 1:
            raise ValueError(f"{key} must be positive")
    if not isinstance(args.eval_payloads, list) or not args.eval_payloads:
        raise ValueError("--eval-payloads must be a non-empty JSON list")
    if len(args.eval_terrains)*len(args.eval_payloads)*len(CARDINAL_COMMANDS)*args.eval_episodes>=100000:
        raise ValueError("validation suite exceeds reserved seed block")
    if args.eval_seed != 1_000_000 or args.seed < 0 or args.seed + args.n_envs >= 1_000_000:
        raise ValueError("Training seeds must be nonnegative and below evaluation seeds; validation owns exactly seed base 1000000; final test owns 2000000")
    if args.replay_buffer and args.algo != "sac":
        raise ValueError("--replay-buffer is only supported by SAC")
    if args.algo == "ppo" and ((args.ppo_n_steps * args.n_envs) < args.batch_size or (args.ppo_n_steps * args.n_envs) % args.batch_size):
        raise ValueError("PPO rollout size (n-steps * n-envs) must be at least batch-size and divisible by it")
    sensor = SimulatedIMU(args.sensor_mode,args.sensor_profile)
    args.sensor_profile = sensor.profile if args.sensor_mode != 'none' else None
    if args.sensor_mode == 'phone' and (args.payload is None or args.payload<=0 or any(p is None or p<=0 for p in args.eval_payloads)):
        raise ValueError('phone mode requires positive training and every validation payload')
    if args.env_module not in ('mist_env','locomotion.mist_env'):
        raise ValueError('untracked environment modules are unsupported')
    rollout = args.ppo_n_steps*args.n_envs
    if not args.smoke and args.timesteps % rollout:
        raise ValueError('matched budgets must divide n-envs * ppo-n-steps for both algorithms')
    experiment = {k:v for k,v in vars(args).items() if k not in ('output','resume','replay_buffer','transfer','timesteps','seed','device','threads','env_module')}
    experiment['sensor']={'mode':args.sensor_mode,'profile':args.sensor_profile}
    experiment['validation_commands']=CARDINAL_COMMANDS
    # Normalize tuples identically to the saved JSON envelope.
    experiment=json.loads(json.dumps(experiment))
    frozen=envelope(experiment)
    prior=None
    if args.resume:
        replay=args.replay_buffer or Path(str(args.resume.with_suffix(''))+'_replay_buffer.pkl')
        prior=verify_checkpoint(args.resume,args.algo,None if args.transfer else experiment,
                                replay if args.algo=='sac' and not args.transfer else None,
                                args.sensor_mode,args.sensor_profile)
        if not args.transfer:
            args.seed=prior['continuation_seed']
            if type(args.seed) is not int or args.seed+args.n_envs>=1000000 or args.seed//100000 != (args.seed-1000)//100000: raise ValueError('continuation seed stream exhausted')
    elif args.transfer:
        raise ValueError('--transfer requires --resume')
    device, device_details = checked_device(args.device)
    output = args.output.resolve()
    if (output / "run.json").exists():
        raise FileExistsError(f"{output} already contains a run. Every continuation or transfer requires a new --output; previous artifacts are immutable.")
    output.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(args.threads)
    set_random_seed(args.seed, using_cuda=device.startswith("cuda"))
    if device.startswith("cuda"):
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
    env_kwargs = dict(terrain=args.terrain, randomize=args.randomize, payload=args.payload, render_mode=None, max_steps=args.max_steps,sensor_mode=args.sensor_mode,sensor_profile=args.sensor_profile)
    factories = [partial(make_env, args.env_module, env_kwargs, args.seed + i, output / f"monitor_{i}") for i in range(args.n_envs)]
    env = DummyVecEnv(factories) if args.n_envs == 1 else SubprocVecEnv(factories, start_method="spawn")
    env.seed(args.seed)
    versions = {}
    for name in ["stable-baselines3", "gymnasium", "pybullet", "torch", "numpy"]:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "not installed"
    expected_sources = frozen["sources"]
    check_sources(expected_sources)
    run = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "arguments": vars(args), "versions": versions,
        "platform": platform.platform(), "device": device_details,
        "source_sha256": expected_sources, "envelope": frozen, "envelope_sha256":identity(frozen),
        "seed_plan":{"workers":list(range(args.seed,args.seed+args.n_envs)),"next_continuation_seed":args.seed+1000,"validation_base":1000000,"final_test_base":2000000},
        "observation_space": str(env.observation_space), "action_space": str(env.action_space),
        "policy_status": "novice_pipeline_smoke_test" if args.smoke else "training_candidate_hardware_unvalidated",
        "resume_semantics": "Additional timesteps; RNG state and environment state are reseeded, so resumption is not bit-for-bit continuation.",
    }
    if False:
        write_json(output / f"resume_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.json", run)
    else:
        write_json(output / "run.json", run)
    cls = {"ppo": PPO, "sac": SAC}[args.algo]
    started = time.perf_counter()
    callback = ValidationCallback(args, output, expected_sources)
    interrupted = False
    try:
        if args.resume:
            model = cls.load(str(args.resume), env=env, device=device, seed=args.seed)
            replay = args.replay_buffer or Path(str(args.resume.with_suffix("")) + "_replay_buffer.pkl")
            if args.algo == "sac" and not args.transfer:
                if replay.exists():
                    model.load_replay_buffer(str(replay))
                elif args.replay_buffer:
                    raise FileNotFoundError(replay)
                else:
                    raise FileNotFoundError("SAC continuation requires matching replay")
        else:
            common = dict(env=env, seed=args.seed, device=device, learning_rate=args.learning_rate, batch_size=args.batch_size, verbose=1, policy_kwargs=dict(net_arch=[64, 64]))
            if args.algo == "ppo":
                model = cls("MlpPolicy", n_steps=args.ppo_n_steps, n_epochs=args.ppo_n_epochs, **common)
            else:
                model = cls("MlpPolicy", buffer_size=args.sac_buffer_size, learning_starts=args.sac_learning_starts, train_freq=1, gradient_steps=args.sac_gradient_steps, **common)
        if args.transfer:
            model.num_timesteps=0
        model.experiment_envelope=frozen
        model.experiment_algorithm=args.algo
        model.experiment_status=run['policy_status']
        model.continuation_seed=args.seed+1000
        check_sources(expected_sources)
        effective = {key: getattr(model, key, None) for key in (
            "n_envs", "n_steps", "n_epochs", "batch_size", "learning_rate",
            "buffer_size", "learning_starts", "gradient_steps", "train_freq", "policy_kwargs", "seed", "device")}
        write_json(output / "effective_model_parameters.json", effective)
        initial_timesteps = model.num_timesteps
        if False:
            callback.best_reward = json.loads((output / "best_evaluation.json").read_text())["mean_reward"]
        evaluate(model, args, output, initial_timesteps, "initial", expected_sources)
        try:
            model.learn(total_timesteps=args.timesteps, callback=callback, reset_num_timesteps=args.resume is None, progress_bar=False)
        except KeyboardInterrupt:
            interrupted = True
        final = callback.run_validation("final")
        save_checkpoint(model, output / "final", args.save_replay_buffer)
        elapsed = time.perf_counter() - started
        actual = model.num_timesteps - initial_timesteps
        summary = {
            "algorithm": args.algo, "status": run["policy_status"],
            "hardware_qualified": False, "interrupted": interrupted,
            "requested_additional_timesteps": args.timesteps,
            "expected_additional_timesteps": math.ceil(args.timesteps/rollout)*rollout if args.algo=="ppo" else math.ceil(args.timesteps/args.n_envs)*args.n_envs,
            "optimizer_updates":getattr(model,"_n_updates",None),
            "actual_additional_timesteps": actual, "total_timesteps": model.num_timesteps,
            "elapsed_seconds_including_evaluation": elapsed,
            "end_to_end_timesteps_per_second": actual / elapsed,
            "best_validation_reward": callback.best_reward,
            "final_validation": final,
            "checkpoint": str(output / "final.zip"),
            "limitation": "Checkpoint selection uses these fixed validation seeds. Run a separate untouched test suite before comparing policies or deployment.",
        }
        write_json(output / "training_summary.json", summary)
        print(json.dumps({k: json_value(v) for k, v in summary.items() if k != "final_validation"}, indent=2), flush=True)
    finally:
        env.close()


if __name__ == "__main__":
    main()
