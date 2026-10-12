"""Verify the deployed generated study bytes against the local release receipt."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
BASE = "https://silmoon04.github.io/mist/game-face-studies/"


def get(name: str) -> bytes:
    timeout = "240" if name == "faces-pack.zip" else "40"
    return subprocess.check_output(["curl.exe", "-sS", "-L", "--fail", "--max-time", timeout, BASE + name])


def main() -> None:
    local = json.loads((ROOT / "site/release.json").read_text(encoding="utf-8"))
    public = json.loads(get("release.json"))
    if public != local:
        raise ValueError("Deployed receipt does not match the selected release")
    def check(item: tuple[str, str]) -> str:
        name, digest = item
        if hashlib.sha256(get(name)).hexdigest() != digest:
            raise ValueError(f"Public bytes differ: {name}")
        return name
    with ThreadPoolExecutor(max_workers=6) as pool:
        verified = list(pool.map(check, local["files"].items()))
    result = {"url": BASE, "studies": 35, "faces": 175, "verifiedFiles": verified, "zipMatches": False}
    (ROOT / "qa/public-verification.json").write_bytes((json.dumps(result, indent=2) + "\n").encode())
    if get("faces-pack.zip") != (ROOT / "site/faces-pack.zip").read_bytes():
        raise ValueError("Public ZIP differs")
    result["zipMatches"] = True
    (ROOT / "qa/public-verification.json").write_bytes((json.dumps(result, indent=2) + "\n").encode())
    print(json.dumps({"verifiedFiles": len(verified), "zipMatches": True, "faces": 175}))


if __name__ == "__main__":
    main()
