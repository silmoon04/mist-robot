# Game face reference research

The user rejected the MIST animation quality and asked for very deep research specifically into game animators, especially indie work, with many agents and a visual moodboard or GIF references. This pass should give them real references to choose from before another animation revision.

Keep the original MIST identity in mind, but research broadly enough to find acting methods outside robot faces. Look for specific eye and mouth choices, anticipation, held reactions, asymmetry, blink motivation, readable silhouettes, expression changes, recovery, and how motion responds to game/dialogue events. Distinguish a drawing style from an acting technique.

Use first-party material: artist portfolios, developer blogs, official trailers, official game pages/press kits, developer interviews and credited conference talks. Follow artist credit claims to evidence. A game title alone is not an animator credit. Do not invent names, timestamps, production frame counts, or observations of motion you have not seen.

## Deliverables per research branch

Own `branches/<branch>.md` and `branches/<branch>.json`. Aim for 3–5 strong entries, with depth and usable visual references rather than a large name list. Include adjacent work if it supplies a different useful method. Mark failures and uncertainty explicitly.

JSON is an array of entries. Each entry follows this shape:

```json
{
  "id": "game-character-or-study",
  "title": "Game or specific character study",
  "studio": "Verified studio",
  "category": "dialogue | graphic | handdrawn | cozy | action | 3d | process",
  "people": [{"name": "Verified name", "role": "Exact supported credit", "sourceUrl": "https://..."}],
  "tags": ["eyes", "asymmetry", "held poses"],
  "summary": "One concrete reason this reference belongs here.",
  "observations": [{"text": "Specific visible acting choice.", "basis": "visual observation | creator statement", "sourceUrl": "https://..."}],
  "mistIdeas": ["Specific adaptation worth trying; label this as our inference."],
  "media": [{"kind": "gif | image | youtube | video | page", "url": "https://...", "sourceUrl": "https://...", "credit": "Creator/studio", "alt": "What this shows", "verified": true, "motionVerified": false}],
  "sources": [{"title": "Page or talk title", "url": "https://...", "kind": "artist | developer | talk | official media", "supports": "What the source establishes"}],
  "confidence": "high | medium",
  "researchNotes": "Any gaps, such as a still-only inspection."
}
```

Media must be a real verified URL returned by a source, not a guessed thumbnail. Prefer actual expressive face images/GIFs and official motion clips over logos or storefront capsules. Source URLs that are only pages are useful for bibliography but do not count as a visual moodboard image. YouTube embeds are acceptable for motion references. Give exact useful timestamps only after verifying that moment. Report when you inspected stills but could not continuously perceive motion.

Do not download external videos or manufacture GIFs that might be mistaken for source animation. Link/embed publicly supplied reference media with credits. Do not use ImageGen to imitate references for this research board. Keep artist prose quotes short; write our analysis in our own words.

No edits to existing MIST art, voice application or deployment by research agents. Root assembles and publishes a new reference-board route. Each branch should send an early message with its strongest candidates and usable media, then a final evidence-bound report.
