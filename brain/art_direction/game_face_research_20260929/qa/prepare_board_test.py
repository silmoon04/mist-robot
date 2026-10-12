"""Copy the board into a disposable QA site with current research entries."""
from pathlib import Path
import json
import shutil

root = Path(__file__).resolve().parents[1]
site = root / "qa" / "board-site"
site.mkdir(parents=True, exist_ok=True)
for filename in ("index.html", "style.css", "app.js", "review-state.js"):
    shutil.copy2(root / "board" / filename, site / filename)
entries = []
for branch in sorted((root / "branches").glob("*.json")):
    data = json.loads(branch.read_text(encoding="utf-8-sig"))
    entries.extend(data if isinstance(data, list) else data.get("entries", []))
(site / "catalog.json").write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
(site / "research.md").write_text("# QA preview\n\nDraft references copied from research branches; not the published catalog.\n", encoding="utf-8")
print(json.dumps({"entries": len(entries), "site": str(site)}))
