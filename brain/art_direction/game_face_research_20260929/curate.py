"""Assemble the reference board without changing the research evidence."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
BOARD = ROOT / "board"
FEATURED = [
    "later-alligator-sweet-geraldine", "slime-rancher-face-shader",
    "dicey-dungeons-lady-luck-warrior", "omori-held-pencil-face",
    "cuphead-hopus-pocus-pencil", "smile-for-me-response-comparisons",
    "isat-odile-mixed-affect", "chicory-feeling-first-faces",
    "undertale-flowey-denial", "great-god-grove-god-faces",
    "cuphead-baroness-pencil", "pizza-tower-peppino-poses",
    "spiritfarer-trailer-stella-daffodil", "dory-independent-face-prototype",
    "astro-bot-led-acting", "night-in-the-woods-graphic-gaze",
    "antonblast-anton-reaction", "moss-quill-lico-process",
    "cuphead-pip-dot-pencil", "wandersong-singing-face",
    "cult-lamb-follower-reaction", "webbed-social-acting",
    "pikuniku-minimal-body-language", "lil-gator-head-followthrough",
]
PREVIEWS = {
    "chicory-feeling-first-faces": 1,
    "antonblast-anton-reaction": 0,
    "cuphead-hopus-pocus-pencil": 2,
    "cuphead-baroness-pencil": 1,
    "dory-independent-face-prototype": 2,
    "botanicula-tiny-faces": 1,
    "ori-james-benson-process": 0,
    "thank-goodness-pip-animation-process": 0,
}
LABELS = {
    "later-alligator-sweet-geraldine": "Later Alligator / Sweet Geraldine",
    "smile-for-me-response-comparisons": "Smile For Me / responses",
    "great-god-grove-god-faces": "Great God Grove / god faces",
    "thank-goodness-pip-animation-process": "Pip Williamson / drawn poses in-engine",
    "isat-odile-mixed-affect": "In Stars and Time / Odile",
    "chicory-feeling-first-faces": "Chicory / character studies",
    "dicey-dungeons-lady-luck-warrior": "Dicey Dungeons / Lady Luck",
    "undertale-flowey-denial": "UNDERTALE / Flowey",
    "omori-held-pencil-face": "OMORI / pencil portrait",
    "cuphead-hopus-pocus-pencil": "Cuphead / Hopus Pocus",
    "cuphead-baroness-pencil": "Cuphead / Baroness",
    "cuphead-pip-dot-pencil": "Cuphead / Pip and Dot",
    "cuphead-jake-clark-process": "Jake Clark / Cuphead process",
    "pizza-tower-peppino-poses": "Pizza Tower / Peppino",
    "slime-rancher-face-shader": "Slime Rancher / six faces",
    "spiritfarer-trailer-stella-daffodil": "Spiritfarer / Stella and Daffodil",
    "astro-bot-led-acting": "Astro Bot / eye acting",
    "night-in-the-woods-graphic-gaze": "Night in the Woods / gaze",
    "antonblast-anton-reaction": "ANTONBLAST / Anton",
    "moss-quill-lico-process": "Moss / Quill",
    "wandersong-singing-face": "Wandersong / singing",
    "cult-lamb-follower-reaction": "Cult of the Lamb / reaction",
    "webbed-social-acting": "Webbed / greeting",
    "pikuniku-minimal-body-language": "Pikuniku / body language",
    "lil-gator-head-followthrough": "Lil Gator Game / head follow-through",
    "klei-symbol-animation-process": "Klei / animation symbols",
    "spiritfarer-game-individual-actions": "Spiritfarer / individual actions",
    "psychonauts2-richardson-mailroom": "Psychonauts 2 / mailroom acting",
    "ori-james-benson-process": "James Benson / Ori reel",
    "dory-independent-face-prototype": "Dory / independent face controls",
    "farewell-north-kyle-banks-face-process": "Farewell North / face process",
    "wirm-event-face": "Wirm / falling reaction",
}


def valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"https", "http"} and bool(parsed.netloc) and not parsed.username


def write_json(path: Path, value: object) -> None:
    path.write_bytes((json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode())


def main() -> None:
    BOARD.mkdir(exist_ok=True)
    entries, seen, branch_receipts = [], set(), []
    for path in sorted((ROOT / "branches").glob("*.json")):
        raw = path.read_bytes()
        values = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(values, list):
            raise ValueError(f"Branch needs an entry array: {path.name}")
        branch_receipts.append({"file": path.name, "sha256": hashlib.sha256(raw).hexdigest(), "entries": len(values)})
        for original in values:
            entry = json.loads(json.dumps(original))
            key = entry["id"]
            if key in seen:
                raise ValueError(f"Duplicate reference ID: {key}")
            seen.add(key)
            for field in ("title", "studio", "category", "summary", "observations", "mistIdeas", "media", "sources"):
                if field not in entry:
                    raise ValueError(f"Missing {field}: {key}")
            for source in entry["sources"] + entry.get("people", []):
                if not valid_url(source.get("url", source.get("sourceUrl", ""))):
                    raise ValueError(f"Invalid source URL: {key}")
            for media in entry["media"]:
                if not valid_url(media["url"]) or not valid_url(media["sourceUrl"]):
                    raise ValueError(f"Invalid media URL: {key}")
                if media["url"] == "https://vimeo.com/65080296":
                    media["verified"] = False
                    media["availability"] = "The original video link returned 404 during research."
                if "619494977" in media["url"]:
                    media["availability"] = "Played in the research browser; some direct HTTP probes were rejected by Vimeo."
                if media.get("motionVerified"):
                    raise ValueError(f"Unexpected continuous-motion claim needs manual evidence: {key}")
            entry["branch"] = path.stem
            entry["featured"] = key in FEATURED
            entry["displayTitle"] = LABELS.get(key, entry["title"])
            if key in PREVIEWS:
                entry["previewIndex"] = PREVIEWS[key]
            if key == "bugsnax-eggabell-rosenthal":
                entry["featured"] = False
                entry["researchStatus"] = "The credited model could not be rendered during research."
            entries.append(entry)

    order = {key: i for i, key in enumerate(FEATURED)}
    entries.sort(key=lambda entry: (not entry["featured"], order.get(entry["id"], len(order)), entry["title"]))
    write_json(BOARD / "catalog.json", entries)
    sources = {source["url"] for entry in entries for source in entry["sources"]}
    people = {person["name"] for entry in entries for person in entry.get("people", [])}
    media = {item["url"] for entry in entries for item in entry["media"] if item.get("verified")}
    summary = {"date": "2026-09-29", "entries": len(entries), "featured": sum(e["featured"] for e in entries),
               "creditedPeople": len(people), "primarySources": len(sources), "mediaUrls": len(media),
               "branches": branch_receipts,
               "method": "Creator credits, supplied media and sampled visual frames; production timing is not inferred from stills."}
    write_json(BOARD / "research-summary.json", summary)
    with (BOARD / "sources.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["reference", "source", "url", "supports"])
        for entry in entries:
            for source in entry["sources"]:
                writer.writerow([entry["displayTitle"], source["title"], source["url"], source.get("supports", "")])
    notes = ["# Game face animation research", "", "Research collected on 29 September 2026.", "",
             "This board gathers real game and animator references for the next MIST acting studies. Credits follow creator portfolios, official game material and direct interviews. Each observation separates a sampled visual reading from a creator's account of the work. MIST adaptations are our proposals.", "",
             "The supplied GIFs and clips let you judge the motion directly. Still inspection does not establish exact blink timing, frame counts or the feel of a full performance.", "",
             "[Proposed MIST studies and playback tests](mist-direction.md) | [Download the board and research pack](research-pack.zip)", ""]
    for entry in entries:
        notes += ["## " + entry["displayTitle"], "", entry["summary"], ""]
        for person in entry.get("people", []):
            notes.append(f"- [{person['name']}]({person['sourceUrl']}): {person['role']}")
        notes += [""]
        for observation in entry["observations"]:
            notes.append(f"- {observation['text']} [{observation['basis']}]({observation['sourceUrl']})")
        notes += ["", "MIST experiments:", ""] + ["- " + idea for idea in entry["mistIdeas"]]
        notes += ["", "Sources:", ""] + [f"- [{s['title']}]({s['url']})" for s in entry["sources"]]
        if entry.get("researchNotes"):
            notes += ["", entry["researchNotes"]]
        notes += [""]
    (BOARD / "research.md").write_bytes(("\n".join(notes).rstrip() + "\n").encode())
    print(json.dumps({key: value for key, value in summary.items() if key != "branches"}))


if __name__ == "__main__":
    main()
