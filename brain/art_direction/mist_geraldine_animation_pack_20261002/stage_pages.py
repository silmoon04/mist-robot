"""Stage only this pack's receipted files into the existing Pages checkout."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
CHECKOUT = ROOT.parents[2] / "output/mist-acting-pages"
DESTINATION = CHECKOUT / "docs/geraldine-animations"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


receipt = json.loads((ROOT / "package-receipt.json").read_text(encoding="utf-8"))
manifest = json.loads((SITE / "asset-manifest.json").read_text(encoding="utf-8"))
tool = json.loads((SITE / "face-tool.json").read_text(encoding="utf-8"))
assert tool["function"]["parameters"]["properties"]["face_id"]["enum"] == [p["id"] for p in manifest["presets"]]
assert sha(SITE / "animation-pack.zip") == receipt["zipSha256"]
with zipfile.ZipFile(SITE / "animation-pack.zip") as archive:
    assert archive.testzip() is None
    for name in archive.namelist():
        assert archive.read(name) == (SITE / name).read_bytes(), name

checks = []
for name in receipt["publicFiles"]:
    source, destination = (SITE / name).resolve(), (DESTINATION / name).resolve()
    assert source.is_relative_to(SITE.resolve()) and destination.is_relative_to(DESTINATION.resolve())
    if name in receipt["files"]:
        assert sha(source) == receipt["files"][name], name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    assert sha(source) == sha(destination), name
    checks.append({"path": name, "sha256": sha(source), "bytes": source.stat().st_size})

result = {"url": "https://silmoon04.github.io/mist/geraldine-animations/", "destination": str(DESTINATION),
          "files": checks, "zipCrcPass": True, "zipMembersMatchSources": True, "modelEnumMatchesPresets": True}
(ROOT / "qa/staged-pages.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"files": len(checks), "bytes": sum(c["bytes"] for c in checks), "zipBytes": receipt["zipBytes"], "url": result["url"]}))
