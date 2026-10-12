"""Compare public response bytes against the final local package receipt."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parent
BASE = "https://silmoon04.github.io/mist/geraldine-animations/"
receipt = json.loads((ROOT / "package-receipt.json").read_text(encoding="utf-8"))
expected = dict(receipt["files"])
expected["animation-pack.zip"] = receipt["zipSha256"]
expected["release.json"] = hashlib.sha256((ROOT / "site/release.json").read_bytes()).hexdigest()


def check(item):
    name, expected_hash = item
    request = urllib.request.Request(BASE + name, headers={"User-Agent": "MIST-asset-verification/1.0", "Cache-Control": "no-cache"})
    try:
        if name == "animation-pack.zip":
            # Bounded ranges avoid a proxy truncating a long single response.
            digest, total, parts = hashlib.sha256(), 0, 0
            for start in range(0, receipt["zipBytes"], 2 * 1024 * 1024):
                end = min(start + 2 * 1024 * 1024, receipt["zipBytes"]) - 1
                ranged = urllib.request.Request(BASE + name, headers={"User-Agent": "MIST-asset-verification/1.0", "Range": f"bytes={start}-{end}"})
                with urllib.request.urlopen(ranged, timeout=35) as response:
                    assert response.status == 206 and response.headers["Content-Range"] == f"bytes {start}-{end}/{receipt['zipBytes']}"
                    body = response.read()
                    assert len(body) == end - start + 1
                    digest.update(body)
                    total += len(body)
                    parts += 1
            actual = digest.hexdigest()
            return {"path": name, "status": 206, "bytes": total, "rangeParts": parts,
                    "sha256": actual, "match": actual == expected_hash}
        with urllib.request.urlopen(request, timeout=35) as response:
            body = response.read()
            actual = hashlib.sha256(body).hexdigest()
            return {"path": name, "status": response.status, "bytes": len(body), "sha256": actual,
                    "match": actual == expected_hash}
    except Exception as error:
        return {"path": name, "match": False, "error": str(error)}


previous = {}
if "--retry-failures" in sys.argv:
    report_path = ROOT / "qa/public-verification.json"
    prior = json.loads(report_path.read_text(encoding="utf-8"))
    previous = {r["path"]: r for r in prior["files"] if r.get("match") and r.get("sha256") == expected.get(r["path"])}
pending = [(name, digest) for name, digest in expected.items() if name not in previous]
with ThreadPoolExecutor(max_workers=2 if previous else 6) as pool:
    retried = {r["path"]: r for r in pool.map(check, pending)}
results = [previous.get(name) or retried[name] for name in expected]
matches = sum(result["match"] for result in results)
report = {"url": BASE, "files": results, "matched": matches, "expected": len(expected),
          "allMatch": matches == len(expected)}
(ROOT / "qa/public-verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"matched": matches, "expected": len(expected), "allMatch": report["allMatch"],
                  "failures": [r for r in results if not r["match"]]}))
raise SystemExit(0 if report["allMatch"] else 1)
