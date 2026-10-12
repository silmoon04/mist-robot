# Training on the planned laptop

Checked against official documentation on **12 October 2026**. The planned laptop has not been inspected or benchmarked. All new-machine settings below are starting points, not tested capacity or speed claims.

The proposed Intel Core Ultra 9, 64 GB DDR5 laptop with an RTX 4080 Laptop GPU should give MIST more room for CPU workers and enable CUDA experiments once its driver and framework work together. Start with the existing PyBullet pipeline, then compare a MuJoCo CPU model before porting training to batched GPU physics. More compute will not resolve estimated mass, servo response, sensor timing or contact parameters.

## What the hardware names mean

| Item | Current laptop | Planned laptop | What still needs checking |
| --- | --- | --- | --- |
| CPU | Intel i5-9300H, from earlier inspection | Intel Core Ultra 9, user-supplied description | Exact processor SKU, performance/efficiency core counts, sustained clocks and cooling. The family name cannot establish a speedup. |
| System RAM | About 24 GB, from earlier inspection | 64 GB DDR5, user-supplied description | Usable memory, channel configuration and memory consumed by other applications. |
| GPU | GTX 1650 mobile, from earlier inspection | GeForce RTX 4080 Laptop GPU | Exact device name, installed VRAM, power limit, driver and framework device detection. |
| CUDA | Earlier inspection reported Nouveau and no working CUDA | Unverified | A GPU model name alone does not establish usable CUDA. |

NVIDIA lists the **RTX 4080 Laptop GPU with 12 GB GDDR6**, third-generation RT cores and a 60 to 150 W GPU subsystem power range. This is the laptop specification; do not substitute the desktop RTX 4080's memory or benchmark results. Check the OEM laptop specification and the delivered device. [NVIDIA laptop comparison](https://www.nvidia.com/en-us/geforce/laptops/compare/).

64 GB of system RAM does not turn 12 GB of dedicated VRAM into 16 GB. Driver reporting may use MiB, while product pages use GB; preserve the reported units and bytes in the inspection record. The laptop's shared graphics-memory figure is not dedicated VRAM.

## Backend choices

| Backend | Where physics runs | Requirements and fit for this laptop |
| --- | --- | --- |
| Existing PyBullet DIRECT | CPU | Usable on both machines. `train.py --device cuda` changes the SB3 policy device only. It does not move this environment's physics to the GPU. Benchmark CPU workers before selecting a count. |
| MuJoCo native | CPU | First independent dynamics check. The official Python wheel includes the engine. Headless physics does not require a rendered viewer or an RTX GPU. The installation documentation does not publish a universal minimum RAM/VRAM capacity for a small robot; model size and worker count decide usage. [Python package](https://mujoco.readthedocs.io/en/stable/python.html), [physics and visualization](https://mujoco.readthedocs.io/en/stable/programming/simulation.html). |
| MJX-JAX | Accelerator selected by JAX | Real batched accelerator physics, after an MIST model/trainer port. Best suited to many scenes; one scene can be slower than native MuJoCo. No fixed VRAM minimum is given in the cited MJX documentation. Measure compiled rollout and training memory rather than assuming a batch fits. [MJX](https://mujoco.readthedocs.io/en/stable/mjx.html). |
| MJX-Warp / MuJoCo Warp | NVIDIA GPU | Real GPU physics, after a separate port. Worth comparing with MJX-JAX on the RTX laptop. Feature support and contact handling differ; retain the CPU reference. It is designed for throughput, while native MuJoCo is optimized for a low-latency single step. [MJX](https://mujoco.readthedocs.io/en/stable/mjx.html), [MuJoCo Warp](https://mujoco.readthedocs.io/en/stable/mjwarp/). |
| Genesis CUDA | NVIDIA GPU | Another real batched GPU physics option. Installation lists Python 3.10 to 3.13 and a matching NVIDIA driver; Linux CUDA is recommended for performance. The cited page gives no fixed RAM/VRAM minimum. Test the actual MIST scene and peak training allocations. [Installation](https://genesis-world.readthedocs.io/en/latest/user_guide/overview/installation.html), [parallel simulation](https://genesis-world.readthedocs.io/en/latest/user_guide/getting_started/parallel_simulation.html). |
| Standard Isaac Lab with Isaac Sim | GPU physics and RTX rendering, depending on task configuration | The current published floor is 32 GB RAM and 16 GB VRAM. The 64 GB RAM meets that floor, but the advertised 12 GB RTX 4080 Laptop GPU falls below the VRAM requirement. It has RT cores, but that alone does not make it meet the full specification. Keep this an optional compatibility experiment or use a supplied host that meets the requirements. [Isaac Lab installation](https://isaac-sim.github.io/IsaacLab/main/source/setup/installation/index.html). |

The current Isaac Sim requirements list Ubuntu 22.04/24.04 or Windows 11, a desktop RTX 4080 minimum, 32 GB RAM, 16 GB VRAM and 50 GB SSD space. They state that Lab training needs additional RAM/VRAM and that GPUs without RT cores are unsupported. Small headless scenes might run below the memory floor, but that is not evidence of supported MIST training capacity. [Isaac Sim requirements](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html).

The existing `MistEnv`/SB3 subprocess loop is a CPU physics implementation. Neither installing MJX/Genesis nor passing a new policy device replaces it. A GPU physics port needs device-resident batched state, servo history, observations, resets, terrain/payload randomization, rewards and rollout storage. It also needs tests against the same reference model. Current SB3 guidance recommends CPU for PPO with an MLP; measure CUDA SAC separately before adopting it. [SB3 PPO guidance](https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html).

## Version and driver gates

Use separate Python environments for the existing locked PyBullet pipeline, MuJoCo/MJX, Genesis and Isaac. Record package versions after a successful smoke test. An unpinned `latest` page is a research snapshot, not a reproducible installation specification.

- JAX currently requires Linux NVIDIA driver **525 or newer for CUDA 12**, or **580 or newer for CUDA 13**. Check `jax.devices()` in the chosen environment and execute a synchronized operation on the GPU. The supported-platform table treats native Windows NVIDIA GPU support differently from Linux; choose the documented platform/wheel combination. [JAX installation](https://docs.jax.dev/en/latest/installation.html).
- Current Warp documentation says its default Linux/Windows wheels use CUDA 13.4 and require an **R580-series or newer driver** and a **Turing (`sm_75`) or newer GPU**. Its CUDA 12 compatibility wheels require R525 or newer. The requirement belongs to the selected wheel, so record it with the wheel version. [Warp installation](https://nvidia.github.io/warp/latest/user_guide/installation.html).
- Genesis CUDA needs a PyTorch CUDA build and a matching NVIDIA driver. Check both PyTorch allocation and an explicit `gs.cuda` scene; a successful CPU fallback would not validate the CUDA path. [Genesis installation](https://genesis-world.readthedocs.io/en/latest/user_guide/overview/installation.html).
- Isaac Lab's current `main` installation page recommends Isaac Sim **5.1.0**, Python **3.11** for Sim 5.X and Linux driver **580.65.06 or later**. The current Isaac Sim `latest` page separately records tested drivers **595.58.03 on Linux** and **595.97 on Windows**. These pages are not a single pinned release contract. Follow the requirements for the chosen Sim/Lab release and run its Compatibility Checker before a scene smoke test. [Isaac Lab installation](https://isaac-sim.github.io/IsaacLab/main/source/setup/installation/index.html), [Isaac Sim requirements](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html).

No driver changes or GPU backend installation were performed for this research.

## Conservative starting settings

`machine_profiles.json` records advisory settings. The trainer does not read that file automatically. Use only the settings whose named backend is implemented, and pass their `train_arguments` explicitly. Leave the six-run queue unchanged until a benchmark selects a worker count.

1. On either laptop, begin with one PyBullet environment, CPU policy optimization and one Torch thread. Retain the 1000 Hz physics/50 Hz control settings and the current bounded action/servo configuration.
2. On the current laptop, benchmark 1, 2 and 4 workers. On the planned laptop, benchmark 1, 2, 4 and 8. Start a training trial at four only after confirming that it improves sustained end-to-end throughput without memory pressure. The exact Ultra 9 SKU and thermal limits are still unknown.
3. Keep PPO's existing 512 steps per environment, batch size 64, five epochs and `[64, 64]` MLP for the first machine comparison. Keep SAC's replay buffer at 100,000 and batch size 64. This isolates the machine/worker change. Different PPO worker counts change the aggregate rollout size, so do not call these identical optimization schedules.
4. After a backend port passes its model checks, begin GPU physics with 16 environments and no cameras. Try 64, 256 and 512 sequentially, stopping on allocation failure, numerical errors or contact-buffer overflow. These are proposed probe counts, not guaranteed capacity or preferred final throughput. Keep at least 20 percent of reported dedicated VRAM free as an initial operating margin; measure the full rollout plus optimizer peak, not idle memory.
5. Treat standard Isaac Lab as below the documented VRAM floor until inspection proves a different GPU/memory configuration. No Isaac training batch is promised in these profiles.

Example CPU probes, run from `locomotion/` in its established environment:

```bash
python scripts/benchmark.py --steps 2000 --warmup 100 --workers 1 2 4 --output runs/current_cpu_probe.json
python scripts/benchmark.py --steps 2000 --warmup 100 --workers 1 2 4 8 --output runs/planned_cpu_probe.json
python scripts/run_job.py --job ppo-seed42 --n-envs 4 --device cpu --print-command
```

These commands are instructions for a future check. They were not run on the planned laptop. The rollout benchmark excludes policy optimization and uses flat terrain. Follow it with a bounded training trial on the mixed-terrain configuration, including evaluation/checkpoint time, before estimating the million-step queue runtime. Record actual PPO timesteps because PPO completes its rollout budget.

## Required validation record

Save a dated inspection with OS/kernel, exact CPU SKU/core topology, usable RAM, laptop model, power mode, cooling conditions and GPU name/driver/dedicated VRAM. A useful read-only GPU query on a working NVIDIA driver is:

```bash
nvidia-smi --query-gpu=name,driver_version,memory.total,power.limit --format=csv
```

Some laptop power fields may be unavailable. Record that result rather than guessing the power limit. Test the chosen framework too: `torch.cuda.is_available()`, a tensor allocation and `torch.cuda.get_device_properties(0).total_memory` for PyTorch; a synchronized GPU computation and actual device list for JAX; an explicit GPU scene for Genesis/Warp. Retain raw versions and outputs.

For each worker/batch probe, record startup/compile time separately from warmed throughput, peak host RAM and GPU VRAM, finite observations/rewards, reset counts, sustained clocks/temperature if exposed, and a trial lasting at least 15 minutes after warmup. That duration is a proposed thermal check, not a benchmark already completed.

A new backend must preserve joint order, mass/inertia/COM, gravity, contact shape/friction, the 50 Hz command schedule and estimated servo limits, latency, quantization, slew, deadband and thermal state. Compare unloaded and loaded single-leg tracking at 1000 and 2000 Hz, then standing/contact and directional rollouts. Recheck convergence if solver or integrator changes; never reduce the timestep just to reach a throughput target. Compare tracking error, contact behavior, torque saturation and falls rather than requiring bit-identical trajectories across solvers.

Only after those checks should PPO/SAC repeat the matched seeds and validation cases. A final untouched test suite must use seeds distinct from the checkpoint-selection suite, all four cardinal commands, all four terrains, and both phone configurations. Report fall fraction, commanded-velocity error, drift, actuator saturation and tracking error. New-machine throughput and simulated policy scores remain separate from hardware calibration and walking qualification.

The CPU setup and lock install `torch==2.8.0+cpu`. A working NVIDIA driver cannot turn that wheel into a CUDA build. Create a separate environment with an official CUDA-enabled Torch wheel and the locomotion dependencies, excluding the CPU lock. Verify `torch.version.cuda`, tensor allocation and a synchronized operation before requesting `--device cuda`.
