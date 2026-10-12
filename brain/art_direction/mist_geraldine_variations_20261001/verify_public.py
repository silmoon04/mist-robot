"""Verify the published review pack against its local release receipt."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
BASE = "https://silmoon04.github.io/mist/geraldine-variations/"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify(name, expected):
    request = Request(BASE + name, headers={"Cache-Control": "no-cache", "User-Agent": "MIST-review-release-check"})
    with urlopen(request, timeout=45) as response:
        content = response.read()
    if digest(content) != expected:
        raise ValueError(f"Published bytes differ: {name}")
    return name


def main():
    receipt = json.loads((ROOT / "package-receipt.json").read_text(encoding="utf-8"))
    expected = dict(receipt["files"])
    expected["release.json"] = digest((ROOT / "site/release.json").read_bytes())
    expected["faces-pack.zip"] = receipt["zipSha256"]
    with ThreadPoolExecutor(max_workers=4) as pool:
        verified = list(pool.map(lambda item: verify(*item), expected.items()))
    result = {"url": BASE, "newSheets": 3, "newFaces": 15, "referenceFaces": 5,
              "verifiedFiles": sorted(verified), "zipMatches": True, "zipBytes": receipt["zipBytes"]}
    (ROOT / "qa/public-verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verifiedFiles": len(verified), "zipMatches": True, "newFaces": 15}))


if __name__ == "__main__":
    main()
