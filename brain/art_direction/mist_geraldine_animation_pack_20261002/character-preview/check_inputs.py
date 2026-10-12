"""Verify reused inputs against the checkpoint without changing those inputs."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACK = ROOT.parent
PROJECT = PACK.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    checkpoint = json.loads((ROOT / "source-provenance.json").read_text(encoding="utf-8"))
    results = []
    for record in checkpoint["nativeAssets"]:
        path = PACK / record["path"]
        actual = sha(path) if path.is_file() else None
        results.append({"path": record["path"], "kind": "native-media", "expected": record["sha256"],
                        "actual": actual, "pass": actual == record["sha256"]})
    for record in checkpoint["interfaces"]:
        path = (PACK if record["root"] == "pack" else PROJECT) / record["path"]
        actual = sha(path) if path.is_file() else None
        results.append({"path": record["path"], "kind": record["root"] + "-interface",
                        "expected": record["sha256"], "actual": actual, "pass": actual == record["sha256"]})
    for name in ("state.mjs", "player.mjs"):
        original = PACK / "site" / name
        copy = ROOT / "adapter/source" / name
        results.append({"path": "adapter/source/" + name, "kind": "source-copy",
                        "expected": sha(original), "actual": sha(copy), "pass": sha(original) == sha(copy)})
    receipt = {"checkedAt": datetime.now(timezone.utc).isoformat(), "passed": all(r["pass"] for r in results),
               "scope": "Current local inputs compared with the 2 October checkpoint; public deployment not rechecked.",
               "total": len(results), "results": results}
    target = ROOT / "input-verification.json"
    target.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": receipt["passed"], "checked": len(results),
                      "differences": [r["path"] for r in results if not r["pass"]]}))
    if not receipt["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
