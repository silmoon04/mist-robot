"""Compare the public review release and native image pack to local bytes."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
BASE = "https://silmoon04.github.io/mist/animation-ideas/"


def get(name: str) -> bytes:
    timeout = "240" if name == "concepts-pack.zip" else "60"
    return subprocess.check_output(["curl.exe", "-sS", "-L", "--fail", "--max-time", timeout, BASE + name])


def main() -> None:
    receipt = json.loads((ROOT / "site/release.json").read_text(encoding="utf-8"))
    local = json.loads((ROOT / "package-receipt.json").read_text(encoding="utf-8"))
    if json.loads(get("release.json")) != receipt:
        raise ValueError("Public release receipt differs")

    def check(item: tuple[str, str]) -> str:
        name, expected = item
        if hashlib.sha256(get(name)).hexdigest() != expected:
            raise ValueError(f"Public file differs: {name}")
        return name

    with ThreadPoolExecutor(max_workers=6) as pool:
        verified = list(pool.map(check, receipt["files"].items()))
    result = {"url": BASE, "concepts": 12, "images": 36, "verifiedFiles": verified, "zipMatches": False}
    output = ROOT / "qa/public-verification.json"
    output.write_bytes((json.dumps(result, indent=2) + "\n").encode())
    if hashlib.sha256(get("concepts-pack.zip")).hexdigest() != local["zipSha256"]:
        raise ValueError("Public concept ZIP differs")
    result["zipMatches"] = True
    output.write_bytes((json.dumps(result, indent=2) + "\n").encode())
    print(json.dumps({"verifiedFiles": len(verified), "zipMatches": True, "images": 36}))


if __name__ == "__main__":
    main()
