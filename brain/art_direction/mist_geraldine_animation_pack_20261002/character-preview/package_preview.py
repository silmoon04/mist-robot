"""Build a portable local preview ZIP from an explicit file allowlist."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
PACK = ROOT.parent
VERSION = "1.0.1"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    provenance = json.loads((ROOT / "source-provenance.json").read_text(encoding="utf-8"))
    files = {}
    for record in provenance["nativeAssets"]:
        path = PACK / record["path"]
        data = path.read_bytes()
        if sha(data) != record["sha256"]:
            raise ValueError("Native input changed: " + record["path"])
        files[record["path"]] = data
    for name in ("asset-manifest.json", "speech-clips.json", "face-tool.json"):
        files["site/" + name] = (PACK / "site" / name).read_bytes()
    for name in ("serve.py", "README.md", "INTEGRATION.md", "ACCEPTANCE.md", "source-provenance.json", "input-verification.json"):
        files["character-preview/" + name] = (ROOT / name).read_bytes()
    for folder in ("adapter", "contract", "direction", "speech-review", "preview", "qa"):
        for path in sorted((ROOT / folder).rglob("*")):
            if not path.is_file() or "history" in path.relative_to(ROOT).parts:
                continue
            if path.suffix.lower() not in {".mjs", ".js", ".html", ".css", ".json", ".md", ".txt", ".png", ".jpg"}:
                continue
            files["character-preview/" + path.relative_to(ROOT).as_posix()] = path.read_bytes()
    receipt = {"version": VERSION, "adapterVersion": "1.0.0", "builtAt": datetime.now(timezone.utc).isoformat(),
               "purpose": "Portable local review and integration adapter; no live runtime or deployment included.",
               "launch": "python character-preview/serve.py --port 9064", "url": "http://127.0.0.1:9064/",
               "nativeMediaFiles": len(provenance["nativeAssets"]),
               "files": {name: {"bytes": len(data), "sha256": sha(data)} for name, data in sorted(files.items())},
               "manifestRule": "Hashes cover each listed payload; this manifest is excluded from its own hash list."}
    manifest = (json.dumps(receipt, indent=2) + "\n").encode()
    (ROOT / "release-manifest.json").write_bytes(manifest)
    files["character-preview/release-manifest.json"] = manifest
    target = ROOT / ("mist-geraldine-character-preview-" + VERSION + ".zip")
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
    with zipfile.ZipFile(target) as archive:
        for name, data in files.items():
            if sha(archive.read(name)) != sha(data):
                raise ValueError("Archive verification failed: " + name)
    delivery = {"version": VERSION, "zip": target.name, "zipBytes": target.stat().st_size,
                "zipSha256": sha(target.read_bytes()), "verifiedEntries": len(files), "nativeMediaMatch": True,
                "localCompletion": True, "humanStyleApproval": "pending", "liveIntegration": "pending",
                "published": False, "liveDefaultChanged": False}
    (ROOT / "delivery-local.json").write_text(json.dumps(delivery, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(delivery))


if __name__ == "__main__":
    main()
