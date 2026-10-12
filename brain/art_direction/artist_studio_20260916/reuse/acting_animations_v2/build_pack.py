"""Package the public animation viewer and its exact source/layer assets."""
from pathlib import Path
import hashlib
import json
import re
import zipfile

ROOT = Path(__file__).resolve().parent
PACK_NAME = "MIST_acting_animations_v2.zip"
PUBLIC_ROOT = "https://silmoon04.github.io/mist/"


def build():
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    checks = json.loads((ROOT / "asset_checks.json").read_text(encoding="utf-8"))
    if not manifest.get("complete") or not checks.get("passed") or not checks.get("complete"):
        raise RuntimeError("Refusing an incomplete or mechanically invalid asset pack.")
    required = ["index.html", "style.css", "app.js", "runtime.js", "review-state.js", "manifest.json", "asset_checks.json", "README.md", "transition_plans.json"]
    for group in manifest["groups"]:
        for example in group["examples"]:
            required += [example["sheet"], example["contact"], example["filmstrip"]]
            for frame in example["frames"]:
                required.append(frame["file"])
                required += [layer["file"] for layer in frame["layers"].values()]
    required += [p.relative_to(ROOT).as_posix() for p in (ROOT / "prompts").rglob("*.txt")]
    required += [p.relative_to(ROOT).as_posix() for p in (ROOT / "previews").rglob("*.gif")]
    files = {}
    for relative in sorted(set(required)):
        target = (ROOT / relative).resolve()
        if not target.is_relative_to(ROOT) or not target.is_file():
            raise RuntimeError(f"Missing or unsafe public asset: {relative}")
        data = target.read_bytes()
        if target.suffix in {".html", ".css", ".js", ".json", ".txt", ".md"}:
            text = data.decode("utf-8-sig").replace("\r\n", "\n")
            if re.search(r"C:[/\\]Users|127\.0\.0\.1|localhost|gh[pousr]_[A-Za-z0-9]{20}|sk-[A-Za-z0-9]{20}", text, re.I):
                raise RuntimeError(f"Local path, server, or credential-like text in public file: {relative}")
            if target.suffix == ".html":
                text = text.replace('href="../"', f'href="{PUBLIC_ROOT}"')
                text = text.replace('href="../acting_studies_v1/"', f'href="{PUBLIC_ROOT}acting-review/"')
            data = text.encode("utf-8")
        files[relative] = data
    receipt = {"schema": "mist-animation-pack", "version": 2, "examples": 18, "frames": 216,
               "files": [{"file": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                         for name, data in sorted(files.items())]}
    files["pack-files.json"] = (json.dumps(receipt, indent=2) + "\n").encode("utf-8")
    output = ROOT / PACK_NAME
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
    with zipfile.ZipFile(output) as archive:
        invalid = archive.testzip()
        if invalid:
            raise RuntimeError(f"ZIP CRC failure: {invalid}")
    result = {"file": PACK_NAME, "files": len(files), "bytes": output.stat().st_size,
              "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
    (ROOT / "pack_receipt.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    build()
