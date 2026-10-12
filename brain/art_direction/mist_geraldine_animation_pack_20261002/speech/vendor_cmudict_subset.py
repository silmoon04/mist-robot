"""Rebuild the small English pronunciation dictionary from pinned CMU data."""
import hashlib
import json
import re
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE_COMMIT = "74790861f652b15e4ac49015a90074ad62a27690"
WORDS = """
a about above across actually after again all almost already also always am an
and another any are around as ask at away back be because been before being
best better big bit blue both bright bring but by call can cannot care change
check close come could day did different do does done down each easy else end
enough even every everyone everything exactly excited face feel few find fine
first for found friend from full get give glad go going good got great had happy
has have he hello help her here him his home hope how i if important in into is
it its just keep kind know last late later let life light like little long look
love made make many may me might mine mist more most much my need never new
news next nice nine no now of off okay old on once one only open opens or other
our out over own part patience people person phone place please point quiet
queue quite read really right same say see seem she should show side since small
so some something soon sound start stay still stop sure take talk tell than
thanks that the their them then there these they thing think this thought those
through time to today together too try turn two under until up us use very wait
waiting want was way we well went were what when where which while who why will
with wonderful word words work worked workshop world would yes yet you your
afterward alligator awesome believe bye calm chocolate comfortable couldn't
don't eight energy eye five four enough friend gentle green half hi hundred
isn't joke knight laugh light little listen mouth must night oh once please
practice seven six sorry speech sweet thank three tired tomorrow twelve warm
welcome won't you're zero people phone thought enough queue quiet knight read
hinge joint connects rigid parts lets pivot line strip holds door frame second
attempt stand reinforced probably won't hurt first one did
""".split()


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "MIST-dictionary-vendor"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def main():
    commit = SOURCE_COMMIT
    base = f"https://raw.githubusercontent.com/cmusphinx/cmudict/{commit}/"
    native = fetch(base + "cmudict.dict")
    license_bytes = fetch(base + "LICENSE")
    selected = set(WORDS)
    entries = {}
    for line in native.decode("utf-8").splitlines():
        if not line or line.startswith(";;;"):
            continue
        word, *phones = line.split()
        word = re.sub(r"\(\d+\)$", "", word)
        if word in selected:
            # Inline source comments are outside the ARPABET sequence.
            phones = phones[:phones.index("#")] if "#" in phones else phones
            entries.setdefault(word, []).append(phones)
    payload = {
        "source": base + "cmudict.dict",
        "sourceCommit": commit,
        "nativeSha256": hashlib.sha256(native).hexdigest(),
        "license": "CMUdict BSD-style data license; see CMUDICT-LICENSE.txt",
        "selection": "Small conversational vocabulary, demo texts, and spelling trap tests.",
        "wordCount": len(entries),
        "missingRequestedWords": sorted(selected - entries.keys()),
        "entries": dict(sorted(entries.items())),
    }
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "cmudict-subset.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (ROOT / "CMUDICT-LICENSE.txt").write_bytes(license_bytes)
    print(json.dumps({"commit": commit, "words": len(entries), "sourceSha256": payload["nativeSha256"],
                      "missing": payload["missingRequestedWords"]}))


if __name__ == "__main__":
    main()
