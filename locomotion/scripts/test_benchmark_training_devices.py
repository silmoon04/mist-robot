"""Guard the matched-budget plan without importing the training runtime."""
import argparse
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("benchmark_training_devices.py")
spec = importlib.util.spec_from_file_location("benchmark_training_devices", SCRIPT)
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


class BenchmarkPlanTest(unittest.TestCase):
    def test_plan_pairs_exact_fresh_budgets_and_reserved_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(python="/trainer/python", output_root=Path(directory) / "new",
                                      algos=["ppo", "sac"], devices=["cpu", "cuda"],
                                      n_envs=[2, 4], seed=630042)
            jobs = benchmark.commands(args)
            self.assertEqual(len(jobs), 8)
            self.assertEqual(len({job["output"] for job in jobs}), 8)
            self.assertFalse(args.output_root.exists())
            for workers in args.n_envs:
                for algorithm in args.algos:
                    pair = [job for job in jobs if job["n_envs"] == workers
                            and job["algorithm"] == algorithm]
                    cpu, cuda = pair
                    self.assertEqual([cpu["device"], cuda["device"]], ["cpu", "cuda"])
                    # Ignore only output and policy device when comparing matched jobs.
                    def normalized(command):
                        command = command[:]
                        for key in ("--output", "--device"):
                            index = command.index(key)
                            del command[index:index + 2]
                        return command
                    self.assertEqual(normalized(cpu["command"]), normalized(cuda["command"]))
                    command = cpu["command"]
                    for flag, value in {"--timesteps": "8192", "--threads": "1",
                                        "--seed": "630042", "--eval-seed": "1000000",
                                        "--eval-max-steps": "960", "--eval-terrains": "flat",
                                        "--eval-payloads": "[0,0.155]"}.items():
                        self.assertEqual(command[command.index(flag) + 1], value)
                    self.assertEqual(8192 % (512 * workers), 0)
                    self.assertIn("--smoke", command)
                    self.assertNotIn("--resume", command)


if __name__ == "__main__":
    unittest.main()
