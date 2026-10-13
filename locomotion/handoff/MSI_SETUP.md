# MSI CUDA setup in Ubuntu WSL2

Use the installed Ubuntu WSL2 distribution. Keep the full restored repository tree and run provenance checks there: native Windows changes path separators in the frozen source inventory. Read [the current continuation](MSI_CONTINUATION.md) and [the frozen checkpoint directions](../DIRECTIONS.md) before loading saved policies. This setup does not launch training or simulation.

For a fresh checkout, disable Git line-ending conversion when cloning:

```bash
git -c core.autocrlf=false clone https://github.com/silmoon04/mist-robot.git
cd mist-robot
git config --local core.autocrlf false
```

The frozen source hashes require the original bytes. A checkout produced with `core.autocrlf=true` needs exact restoration from the verified release before validation. Setting the option afterward does not repair existing files.

From PowerShell, enter Ubuntu:

```powershell
wsl -d Ubuntu
```

The current MSI environment is already installed and verified. From its Bash shell, check that environment in the Linux execution checkout:

```bash
cd /home/hssil/mist-locomotion-msi/repo
export MIST_CUDA_ENV=/home/hssil/mist-locomotion-msi/venv-cuda
export MIST_CUDA_PYTHON="$(uv python find 3.11)"
"$MIST_CUDA_PYTHON" -c 'from locomotion.provenance import source_hashes,identity; expected="8793d43d546c95c6fd695860305f96a0627e49be9ec81779e313b63d1b92e8c1"; actual=identity(source_hashes()); print(actual); assert actual == expected, "Frozen source mismatch"'
bash locomotion/scripts/setup_cuda.sh --verify-only
export MIST_PYTHON="$MIST_CUDA_ENV/bin/python"
```

The MSI has uv-managed Python 3.11.16; `uv python find 3.11` resolves its installed executable even though `python3.11` is absent from PATH. This environment was installed with uv from the official Torch index and the exact non-Torch lock entries. The script's verification path passed against it. Its full pip installation path was reviewed but has not been executed on this machine.

For a new environment, choose a new `MIST_CUDA_ENV` path and run `bash locomotion/scripts/setup_cuda.sh` without `--verify-only`. If Python 3.11 is installed under another path, set `MIST_CUDA_PYTHON` to that interpreter. The script creates a missing environment, accepts a pristine Python 3.11 venv, and permits reruns of an environment it marked for this exact lock. It refuses the CPU environment and populated environments without its marker, including this manually installed environment in install mode. The script does not delete environments.

The script installs `torch==2.8.0+cu126` from the [official CUDA 12.6 index documented for PyTorch 2.8.0](https://pytorch.org/get-started/previous-versions/). It removes only `torch==2.8.0+cpu` from a temporary requirements copy and verifies every other pinned version. Keep `requirements.lock.txt` unchanged. Do not run the full CPU lock inside this environment.

Each invocation writes evidence under `$MIST_CUDA_ENV/mist-cuda-records/`: installation reports with downloaded wheel URLs/hashes when installation occurs, pip freeze/inspect/check output, driver output when available, and `environment.json` after verification. The JSON records the lock/script hashes, Python, Torch, CUDA runtime, GPU names/VRAM and successful device allocation, matrix multiplication and synchronization. A failed invocation has `status.txt` marked failed and can be rerun with the same variables. An already prepared environment can be checked without package changes:

```bash
bash locomotion/scripts/setup_cuda.sh --verify-only
```

`--verify-only` still writes a new evidence directory. Installation reports from earlier invocations remain in their original directories. These records document the installed environment; dependency resolution is not a hash-locked replacement for the frozen CPU lock.

CUDA speeds policy optimization when `--device cuda` is selected; PyBullet physics remains on CPU. Benchmark PPO and SAC before selecting their devices. Passing the setup check establishes a working CUDA runtime, not a qualified walking policy or physical robot calibration.
