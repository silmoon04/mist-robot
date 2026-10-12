# MIST game-inspired faces

User scope: five new MIST faces for every one of the 35 studies on the game reference board, 175 faces total. Use the built-in image_gen tool and parallel agents. These are static expression studies for review, not animation frames or a live-face replacement.

Research catalog: ../game_face_research_20260929/board/catalog.json

Each study is one raster expression-sheet asset containing exactly five independently drawn MIST faces. One built-in imagegen call per study sheet; do not substitute code-drawn faces. Export the complete original sheet. All 35 study IDs must be represented, including process-only references, where the adaptation is explicitly our experiment.

## MIST identity

Inspect these local inputs with view_image before using them:

- Existing MIST palette/shape sheet: /brain/art_direction/artist_studio_20260916/reuse/faces_sheet.png
- User-liked visual reference: /brain/art_direction/artist_studio_20260916/reuse/style_studies_v3/user_reference.png

Use the local MIST image as the edit target, with the prompt asking to reinterpret it into a new five-pose expression study. Preserve cyan/turquoise facial marks on an almost-black flat backdrop, two eyes and one mouth per face, and the recognizable graphic screen-face identity. The nine-face reference's physical bezels, props, white paper and labels are not part of the requested asset.

Give each inspiration a visible acting/design approach beyond line thickness. Read its exact catalog observations and MIST ideas. Use original MIST forms with the studied gaze, eyelids, asymmetry, mouth silhouette, pose contrast or material handling. Do not simply copy game characters or add their anatomy, costumes or logos. Process entries inform the authored pose workflow rather than imply a verified source facial style.

## Sheet layout and pose order

Landscape raster, six equal cells in an invisible 3-column by 2-row grid. Exactly five faces: positions 1,2,3 across the top row, then 4,5 across the bottom row; lower-right cell remains completely empty dark background. No grid lines, numbers, words, labels, props, screen frames or watermark. Keep each face completely inside its own cell with comfortable margins, consistent scale and a stable face baseline.

1. Attentive welcome: friendly, receptive, closed small mouth. Listening must not look like loud speech.
2. Consideration / doubt: thoughtful directional gaze or asymmetry, restrained uncertain mouth.
3. Dry skepticism / mild frustration: clearly different eyelid attitude and mouth; avoid a happy smile.
4. Amused recognition: readable warmth and delight, with modest mouth opening or a gentle smile.
5. Gentle concern / sadness: empathetic eyes and a small concerned mouth, not happy speech.

Design all five as real held acting poses, not resized duplicates. Preserve the intended emotion in the mouth. Clean organic contours and intentional asymmetry; no random wobble, extra eye fragments, accidental teeth, tongue or stray features. Do not make all sheets merely the same eye model with different stroke widths. Some inspirations can use filled apertures, clipped lids, restrained pupils or open C shapes while remaining clearly MIST.

## Files and evidence

Each agent owns only its assigned IDs under sheets/, manifests/ and prompts/ here. Copy the returned built-in generated image into sheets/<id>.png (preserve original bytes/format; use correct extension if not PNG). Save the exact prompt in prompts/<id>.txt. Never select another concurrent agent's output by guessing the newest generated file. Use the result's returned path or unambiguous artifact identity.

Record a JSON array in manifests/<group>.json. Per study:

{"id":"catalog ID","sheet":"sheets/id.png","prompt":"prompts/id.txt","poses":["Attentive","Considering","Skeptical","Amused","Concerned"],"approach":"Concrete original adaptation","tool":"built-in image_gen","sourceStudyUrl":"catalog source","qa":{"fiveFaces":true,"blankSixthCell":true,"mistIdentity":true,"emotionContrast":true},"limitations":"Anything actually uncertain"}

Inspect every generated sheet. Reject wrong counts, fused features, happy skeptical/concerned mouths, or unreadable tiny faces. If needed, request one targeted imagegen edit of the returned local sheet after viewing it. Save the selected version non-destructively. Report honestly if generation failed rather than fabricate faces or silently use CLI.

The UI will show each original sheet with HTML pose captions and per-pose save/why controls. Original sheets and prompts will be downloadable. No external game art will be bundled as our generated output.
