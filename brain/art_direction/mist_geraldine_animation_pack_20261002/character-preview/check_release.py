"""Extract the ZIP inside this subtree and check a fresh portable launch."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parent


def main():
    delivery = json.loads((ROOT / "delivery-local.json").read_text(encoding="utf-8"))
    archive_path = ROOT / delivery["zip"]
    destination = (ROOT / "release-check" / delivery["version"]).resolve()
    if not destination.is_relative_to(ROOT.resolve()):
        raise ValueError("Extraction target must stay inside character-preview")
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        for name in archive.namelist():
            if not (destination / name).resolve().is_relative_to(destination):
                raise ValueError("Archive path escapes release target")
        archive.extractall(destination)
    manifest = json.loads((destination / "character-preview/release-manifest.json").read_text(encoding="utf-8"))
    for name, record in manifest["files"].items():
        actual = hashlib.sha256((destination / name).read_bytes()).hexdigest()
        if actual != record["sha256"]:
            raise ValueError("Extracted payload mismatch: " + name)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base = "http://127.0.0.1:" + str(port)
    process = subprocess.Popen([sys.executable, "character-preview/serve.py", "--port", str(port)],
                               cwd=destination, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    results = []
    try:
        deadline = time.monotonic() + 10
        while True:
            try:
                with urlopen(base + "/__health", timeout=1) as response:
                    health = json.load(response)
                break
            except OSError:
                if time.monotonic() >= deadline or process.poll() is not None:
                    raise RuntimeError("Fresh portable preview did not start")
                time.sleep(0.1)
        results.append({"id": "fresh-launch", "pass": health["status"] == "ok"})
        for path, content_type in (("/character-preview/preview/", "text/html"),
                                   ("/character-preview/preview/app.mjs", "application/javascript"),
                                   ("/site/asset-manifest.json", "application/json")):
            with urlopen(base + path) as response:
                results.append({"id": path, "pass": response.status == 200 and content_type in response.headers["Content-Type"]})
        source = json.loads((destination / "character-preview/source-provenance.json").read_text(encoding="utf-8"))
        for record in source["nativeAssets"]:
            with urlopen(base + "/" + record["path"]) as response:
                actual = hashlib.sha256(response.read()).hexdigest()
            results.append({"id": "served-native/" + record["path"], "pass": actual == record["sha256"]})
        for method in ("GET", "HEAD"):
            try:
                urlopen(Request(base + "/production-contract.json", method=method))
                results.append({"id": "route-boundary/" + method, "pass": False})
            except HTTPError as error:
                results.append({"id": "route-boundary/" + method, "pass": error.code == 404})
    finally:
        process.terminate()
        process.wait(timeout=5)
    receipt = {"checkedAt": datetime.now(timezone.utc).isoformat(), "passed": all(r["pass"] for r in results),
               "archiveEntriesVerified": len(manifest["files"]), "total": len(results), "results": results,
               "scope": "Fresh extracted portable server, HTTP payload bytes and MIME; browser motion is reviewed separately.",
               "temporaryServerStopped": process.poll() is not None}
    (ROOT / "release-check-results.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in receipt.items() if key != "results"}))
    if not receipt["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
