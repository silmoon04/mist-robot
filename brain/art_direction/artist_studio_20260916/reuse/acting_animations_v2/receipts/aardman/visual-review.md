# Aardman group generation review

Built-in ImageGen produced all three final sheets. Original study poses were inspected first and used only as identity and acting references. No procedural artwork was drawn. Source PNGs are unchanged copies of the selected ImageGen outputs.

- `listening.png`: 12 frames, gentle attentive blink, a restrained right eyebrow lift, closed neutral mouth. Two targeted blink corrections removed an erroneous helmet-like upper arc. A final ImageGen alpha cleanup removed real diffuse edge haze introduced by the edit. Current SHA-256: `7182a8b48ab19ce46599023698ce49cce8219dbbd022b1120eddb14720f10dca`.
- `disbelief.png`: 12 frames, descending lids, asymmetrical dry scepticism, neutral dash mouth. The targeted blink correction moves the outside lid contour instead of only reducing the pupil opening.
- `realisation.png`: 12 frames, thoughtful gaze, blink, brief soft smile, return to neutral. The second closing frame is already nearly shut; the next frame completes the closed lid curve.

All final images are 1536 x 1024 RGBA sheets in a 4-column by 3-row grid. Every sheet contains 12 distinct raster frames. Transparent pixel fractions are approximately 85%, 89%, and 87%. All have alpha-zero exterior areas and genuine transparent eye holes. Raw RGB previews can display cyan fog under alpha-zero pixels; the diagnostic composites apply the alpha correctly against #101c20.

Each face has two clearly separated eyes and a mouth below. No text, border, phone frame or props are present. There is some registration variation between generated sheet rows, so the compiler should align the extracted components consistently. Source cells themselves must remain traceable to their generated image crops.

Final diagnostic composites: `listening-alpha-diagnostic.jpg`, `disbelief-blink-diagnostic.jpg`, and `realisation-blink-diagnostic.jpg`. Earlier diagnostic files document iterations and are not final assets. `generation.json` contains source hashes, alpha metrics, frame crop bounds, and frame hashes.
