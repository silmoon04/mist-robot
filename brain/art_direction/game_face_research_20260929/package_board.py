"""Package only the public reference board and its research notes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
BOARD = ROOT / "board"
WORKSPACE = ROOT.parents[2]
DESTINATION = WORKSPACE / "output/mist-acting-pages/docs/game-face-references"
FILES = ["index.html", "style.css", "app.js", "review-state.js", "catalog.json",
         "research.md", "sources.csv", "research-summary.json", "mist-direction.md"]


def main() -> None:
    audited = json.loads((ROOT / "audit/final-catalog-validation.json").read_text(encoding="utf-8-sig"))
    digest = hashlib.sha256((BOARD / "catalog.json").read_bytes()).hexdigest()
    audit_text = (ROOT / "audit/FINAL_CATALOG_AUDIT.md").read_text(encoding="utf-8")
    if digest not in audit_text:
        raise ValueError("Catalog has changed since the final evidence audit")
    if not audited:
        raise ValueError("Final audit receipt is empty")
    entries = json.loads((BOARD / "catalog.json").read_text(encoding="utf-8"))
    if len(entries) != 35 or len({entry["id"] for entry in entries}) != len(entries):
        raise ValueError("Unexpected catalog count or duplicate entries")
    if not DESTINATION.resolve().is_relative_to((WORKSPACE / "output/mist-acting-pages/docs").resolve()):
        raise ValueError("Destination is outside the Pages documentation tree")
    DESTINATION.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name in FILES:
        content = (BOARD / name).read_text(encoding="utf-8-sig").replace("\r\n", "\n").encode("utf-8")
        (DESTINATION / name).write_bytes(content)
        hashes[name] = hashlib.sha256(content).hexdigest()
    readme = """# Game face references

35 studies assembled from creator portfolios, developer material and direct interviews.

Open the published board at https://silmoon04.github.io/mist/game-face-references/

To run this pack locally, extract it and run `python -m http.server 9050` from the extracted folder. Then open http://127.0.0.1:9050/ . Opening index.html directly may prevent the catalog from loading.

The pack contains the board, linked catalog, research notes and sources. Reference artwork is loaded from its original public host; it is not bundled or licensed for use as MIST artwork. Browser notes are local to each browser and can be exported with the board controls.

Credits distinguish creator and project roles from shot-specific authorship. Supplied GIFs and clips are available for direct review; exact performance timing is not inferred from sampled stills.
"""
    (DESTINATION / "README.md").write_bytes(readme.encode())
    hashes["README.md"] = hashlib.sha256(readme.encode()).hexdigest()
    receipt = {"date": "2026-09-29", "catalogSha256": digest, "studies": len(entries), "files": hashes}
    (DESTINATION / "release.json").write_bytes((json.dumps(receipt, indent=2) + "\n").encode())
    with zipfile.ZipFile(DESTINATION / "research-pack.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in [*FILES, "README.md", "release.json"]:
            archive.write(DESTINATION / name, arcname="game-face-references/" + name)
    (ROOT / "public-release.json").write_bytes((json.dumps(receipt, indent=2) + "\n").encode())
    print(json.dumps({"destination": str(DESTINATION), "files": len(hashes) + 2, "catalogSha256": digest}))


if __name__ == "__main__":
    main()
