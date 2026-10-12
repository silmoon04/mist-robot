"""Offline experiment orchestration checks; fake replies are not model evidence."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import experiment


class ExperimentChecks(unittest.TestCase):
    def test_effort_ablation_changes_only_the_assigned_arm_setting(self):
        captured=[]
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);suite=root/'suite.json';persona=root/'persona.txt';output=root/'out'
            suite.write_text(json.dumps({'cases':[{'id':'repair','split':'dev','category':'repair','mode':'text','turns':[{'user':'fixture'}]}]}),encoding='utf-8')
            persona.write_text('Identical fixture persona',encoding='utf-8')
            def fake(case,repeat,folder,config,prompt):
                captured.append((dict(config),prompt))
                return {'case_id':case['id'],'repeat':repeat,'category':'repair','split':'dev','status':'completed','turns':[{'user':'fixture','text':'Fixture response'}], 'events':[],'checks':[],'outcomes':{},'errors':[]}
            with patch.object(experiment.runner,'luna_case',side_effect=fake):
                self.assertEqual(experiment.main(['--suite',str(suite),'--baseline-persona',str(persona),'--candidate-persona',str(persona),'--repeats','1','--output',str(output),'--baseline-reasoning','low','--candidate-reasoning','high']),0)
            self.assertEqual({config['reasoning'] for config,prompt in captured},{'low','high'})
            self.assertEqual(captured[0][1],captured[1][1])
            left,right=[{k:v for k,v in config.items() if k!='reasoning'} for config,prompt in captured]
            self.assertEqual(left,right)
    def test_balanced_schedule_and_coverage(self):
        cases = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        for repeats in (1, 2, 3, 4):
            schedule = experiment.schedule_pairs(cases, repeats, 73)
            self.assertEqual(schedule, experiment.schedule_pairs(cases, repeats, 73))
            self.assertEqual({(b["case_id"], b["repeat"]) for b in schedule},
                             {(c["id"], r) for c in cases for r in range(1, repeats+1)})
            self.assertEqual(len(schedule), len(cases)*repeats)
            first = [b["order"][0] for b in schedule]
            self.assertLessEqual(abs(first.count("baseline")-first.count("candidate")), 1)
            for block in schedule:
                self.assertEqual(set(block["order"]), {"baseline", "candidate"})

    def test_persistence_isolation_and_no_overwrite(self):
        calls = []
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            suite = root / "suite.json"
            suite.write_text(json.dumps({"cases": [{"id": "one", "split": "dev", "category": "test", "mode": "text", "turns": [{"user": "hello"}]}]}), encoding="utf-8")
            persona = root / "persona.txt"
            original = b"Your voice is being converted to the owner's MIST voice.\r\n"
            persona.write_bytes(original)
            output = root / "experiment"
            def fake_case(case, repeat, folder, config, prompt):
                calls.append(folder)
                checkpoint = json.loads((output / "run.json").read_text(encoding="utf-8"))
                self.assertEqual(checkpoint["status"], "running")
                active = [b for b in checkpoint["schedule"] if b["status"] == "running"]
                self.assertEqual(len(active), 1)
                self.assertEqual(active[0]["samples"][-1]["status"], "running")
                self.assertEqual(config["concurrency"], 1)
                return {"case_id": case["id"], "repeat": repeat, "category": case["category"], "split": case["split"],
                        "status": "completed", "turns": [{"user": "hello", "text": "fixture only"}],
                        "events": [], "checks": [], "outcomes": {}, "errors": []}
            argv = ["--suite", str(suite), "--baseline-persona", str(persona), "--candidate-persona", str(persona),
                    "--repeats", "3", "--output", str(output)]
            with patch.object(experiment.runner, "luna_case", side_effect=fake_case):
                self.assertEqual(experiment.main(argv), 0)
                with self.assertRaises(FileExistsError):
                    experiment.main(argv)
            self.assertEqual(len(calls), 6)
            self.assertEqual(len(set(calls)), 6)
            data = json.loads((output / "run.json").read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "finished")
            for block in data["schedule"]:
                self.assertEqual(len(block["samples"]), 2)
                self.assertGreaterEqual(block["stopped_ms"], block["started_ms"])
                self.assertEqual([s["arm"] for s in block["samples"]], block["order"])
            self.assertEqual((output / "baseline/persona.raw.txt").read_bytes(), original)
            self.assertEqual((output / "baseline/cases.frozen.json").read_bytes(), suite.read_bytes())
            self.assertTrue((output / "review/review.html").is_file())

    def test_failure_and_unsupported_are_retained(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            suite, persona, output = root/"suite.json", root/"persona.txt", root/"out"
            suite.write_text(json.dumps({"cases": [
                {"id": "one", "split": "dev", "category": "test", "mode": "text", "turns": [{"user": "hello"}]},
                {"id": "audio", "split": "dev", "category": "test", "mode": "timed_audio"}]}), encoding="utf-8")
            persona.write_text("fixture", encoding="utf-8")
            with patch.object(experiment.runner, "luna_case", side_effect=RuntimeError("fixture failure")) as fake:
                result = experiment.main(["--suite", str(suite), "--baseline-persona", str(persona), "--candidate-persona", str(persona),
                                          "--repeats", "1", "--output", str(output)])
            self.assertEqual(result, 1)
            self.assertEqual(fake.call_count, 2)
            record = json.loads((output/"run.json").read_text(encoding="utf-8"))
            self.assertEqual(record["status_counts"]["baseline"], {"failed": 1, "unsupported": 1})
            self.assertEqual(record["review"]["status"], "not_built")
            self.assertTrue((output/"comparison.json").is_file())


if __name__ == "__main__":
    unittest.main()
