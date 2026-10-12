"""Collect already executed cases without pretending they used identical inputs."""
import hashlib
import json
from pathlib import Path
from model import ROOT


def refresh(root=ROOT/"outputs"):
    root=Path(root)
    reports=[]
    for path in sorted(root.glob("*/report.json")):
        report=json.loads(path.read_text(encoding="utf-8"))
        params=json.loads((path.parent/"parameters_used.json").read_text(encoding="utf-8"))
        report["parameters_sha256"]=hashlib.sha256(json.dumps(params,sort_keys=True).encode()).hexdigest()
        reports.append(report)
    result={"schema_version":1,"reports":reports,"note":"Each case keeps its own input snapshot. PASS_IN_MODEL never implies hardware validation."}
    (root/"summary.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    return result


if __name__=="__main__":
    r=refresh()
    print("Collected",len(r["reports"]),"executed cases")
