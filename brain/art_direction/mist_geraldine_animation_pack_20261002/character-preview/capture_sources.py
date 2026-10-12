"""Record the current local inputs without modifying the shared pack/runtime."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
PACK = ROOT.parent
PROJECT = PACK.parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture():
    manifest = json.loads((PACK / "site/asset-manifest.json").read_text(encoding="utf-8"))
    clips = json.loads((PACK / "site/speech-clips.json").read_text(encoding="utf-8"))
    receipt = json.loads((PACK / "package-receipt.json").read_text(encoding="utf-8"))
    media = set(manifest.get("extraAssets", []))
    for kind in ("eyes", "mouths"):
        for asset in manifest[kind].values():
            media.add(asset["file"])
            for frame in asset["frames"]:
                for part in (frame, frame.get("left", {}), frame.get("right", {})):
                    if part.get("file"):
                        media.add(part["file"])
    media.update(clip["audio"] for clip in clips["clips"])
    records = []
    for name in sorted(media):
        path = (PACK / "site" / name).resolve()
        if not path.is_relative_to((PACK / "site").resolve()):
            raise ValueError("Asset is outside the selected pack")
        actual = digest(path)
        expected = receipt["files"].get(name)
        if actual != expected:
            raise ValueError(f"Selected native asset differs from prior receipt: {name}")
        records.append({"path": "site/" + name, "sha256": actual, "bytes": path.stat().st_size,
                        "priorReceiptMatch": True})
    interfaces = []
    for name in ("site/state.mjs", "site/player.mjs", "site/asset-manifest.json", "site/speech-clips.json", "site/face-tool.json"):
        interfaces.append({"root": "pack", "path": name, "sha256": digest(PACK / name)})
    for name in ("brain/duplex/static/playback.js", "brain/duplex/static/app.js"):
        interfaces.append({"root": "project", "path": name, "sha256": digest(PROJECT / name)})
    result = {"version": 1, "capturedDate": "2026-10-02", "nativeAssets": records,
              "interfaces": interfaces, "policy": "Current local files, including current uncommitted contents. Shared inputs remain read-only.",
              "recordings": "Three existing synthetic MIST recordings from the reviewed pack; no new audio or private conversations."}
    (ROOT / "source-provenance.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"nativeAssetsVerified": len(records), "interfaceSnapshotsHashed": len(interfaces)}))


if __name__ == "__main__":
    capture()
