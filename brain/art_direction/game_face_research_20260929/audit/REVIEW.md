# Independent media review

Scope: branch files available during 29 September 2026 research assembly. `http-validation.json` records the precise branch SHA-256 hashes for each network run. This is not yet a review of the assembled UI/catalog.

Checks performed: curl with normal TLS, HTTP headers for all available media, GET checks for suspect Vimeo endpoints, local decoding of publicly supplied stills/GIFs, visual inspection of contact sheets, and independent reads of artist-credit sources. No external videos were downloaded. Contact sheets show static frames and are audit working material, not replacement animation references. No motion has been continuously viewed in this independent audit.

Completed branch sweep: eight JSON branches, 79 media URLs, and 46 decoded image/GIF assets. All 46 decoded successfully. Thirteen GIF containers contain multiple frames; these metadata counts are not animation production specifications. 42 claimed media-source pages were fetched; 65 media URLs or full paths were found literally in the HTML. Many of the remaining cases are relative URLs or alternate YouTube embed syntax. `media-source-validation.json` records literal checks without treating a miss as proof of false provenance.

## Actionable findings

1. `battleblock-cutscene-puppets`: `https://vimeo.com/65080296` returns 404. Remove it from usable media, or explicitly mark unavailable. The official Behemoth post remains useful evidence for Derek Lieu and Dan Paladin.
2. `psychonauts2-richardson-mailroom`: player URL `https://player.vimeo.com/video/619494977?h=831ae4368a` returns 405 to HEAD and 401 to a curl GET. This is a transport-probe limitation, not proof of a dead embed. Root relayed the 3D researcher's successful browser playback and inspection of mailroom frames at 4:08–4:20. Retain the qualified artist entry and exact hash-bearing player URL on that browser evidence; this independent audit did not reproduce playback. Double Fine credits independently support Miyuki Richardson as animator and storyboard artist.
3. Every currently inspected media entry has `motionVerified: false`. Preserve that. A GIF with multiple decoded frames is an animation container, not evidence that its timing, acting arc or transitions were watched. A sequence of expression-sheet crops must not be presented as source gameplay animation.
4. Pip/Dot and Baroness production drawings are authentic, but the drawings occupy a small portion of their full paper frames. Card thumbnails need a zoom affordance or deliberate, credited crop with the original accessible. Their full-sheet thumbnails alone are weak face references.
5. The Antonblast GIF starts with distant platform gameplay; its face is too small for a lead facial reference. The Ori talk thumbnail is mostly black surrounding small characters. Keep these as supporting motion/process links rather than promising a face close-up.
6. Interviews are useful primary testimony when they quote the creator, even if the host is a publication. Label those as creator interviews; do not describe the publication itself as the developer.

## Visual shortlist and placement

The following assesses visible still content only. Media index is zero-based within the branch entry.

| Entry and media | Face visibility | Recommendation and observed value |
|---|---|---|
| `slime-rancher-face-shader` 0 | Excellent | Lead tile. Six simple round faces make mouth shapes and eye openness easy to compare. The first inspected frame alone is already an expression reference. |
| `dicey-dungeons-lady-luck-warrior` 0 | Excellent for Lady Luck | Lead tile. Large sideways glance, strongly shaped lids and mouth, with a supporting hand gesture. The small die is secondary. |
| `spiritfarer-trailer-stella-daffodil` 0 | Excellent | Lead tile. Stella and Daffodil have clearly readable contrasting eye shapes and a shared embrace. Identify it as trailer artwork, not gameplay animation. |
| `spiritfarer-trailer-stella-daffodil` 1 | Good | Supporting group reference. The shark profile is readable; Stella and other faces are smaller. |
| `pizza-tower-peppino-poses` 0 | Excellent | Lead pose sheet. Three visibly distinct whole-body and facial extremes, including wide-eyed strain and a compressed expression. It is a drawing sheet, not a viewed transition. |
| `battleblock-cutscene-puppets` 0 | Good | Supporting graphic face reference. Simple mouth silhouettes survive a crowded composition; many faces remain readable. |
| `battleblock-cutscene-puppets` 1 | Poor at card size | Process-only sketch page: faint, tiny drawings need opening at full size. |
| `night-in-the-woods-graphic-gaze` 0 | Fair | Useful graphic restraint reference, but wide environment consumes much of the tile. Provide a large view. |
| `wandersong-singing-face` 0 | Fair | Colour and body gesture dominate. Face is visible but small; use as contextual motion link, not detailed mouth reference. |
| `wandersong-singing-face` 1 | Poor at card size | Two figures are small in a broad environment. Supporting only. |
| `chicory-feeling-first-faces` 1 | Good when enlarged | Strong ink expression/design sheet; selected heads show different lids and muzzles. Full-size inspection is necessary for individual faces. |
| `chicory-feeling-first-faces` 0 | Fair | Sketchbook context has many small drawings. Useful process companion, weaker lead tile. |
| `cuphead-hopus-pocus-pencil` 0 | Good | The rabbit's small mouth and narrowed lids read clearly when enlarged. Preserve the full paper source. |
| `cuphead-hopus-pocus-pencil` 2 | Good | Strong grin and coordinated head/hand distortion. Best as one of a few selected production drawings. |
| `cuphead-hopus-pocus-pencil` 4 | Good | Stretched eye/neck design remains recognizable; a useful expression extreme. |
| `cuphead-pip-dot-pencil` 0 | Small | Excellent opposing attitudes in principle, but needs an enlarged view/crop to study the separate faces. |
| `cuphead-baroness-pencil` 1 | Small | Useful jaw/eye extreme, weak uncropped tile because paper dominates. |
| `moss-quill-lico-process` 1 | Fair | Character visible among foliage; body acting stronger than facial detail at thumbnail scale. |
| `ori-james-benson-process` 2 | Poor | Process link thumbnail, not a lead face image. |
| `dory-independent-face-prototype` 2 | Excellent | Lead close-up. Simple circular eyes and small beak/mouth read immediately on the rounded body. |
| `lil-gator-head-followthrough` 0 | Good silhouette, limited facial detail | Good supporting character reference; large profile eye is visible, but one still cannot support follow-through timing. |
| `isat-odile-mixed-affect` 0 | Good | Clear portrait against the dialogue panel; a useful modest smile with heavy lids. Lead dialogue reference when enlarged. |
| `isat-odile-mixed-affect` 1 | Good in portrait strip | Four contrasting face treatments are readable, although the battle takes most of the screenshot. |
| `undertale-flowey-denial` 0 and 1 | Good but small | Authentic static text panels. Valuable face/dialogue contrast; do not call these a GIF or viewed game animation. |
| `omori-held-pencil-face` 0 | Excellent | Strong lead face tile: near-neutral frontal expression and tiny mouth. GIF validity and decoded changes do not establish continuously watched motion. |
| `omori-held-pencil-face` 1 | Excellent | Readable closed lids and restrained mouth; suitable companion expression. |
| `astro-bot-led-acting` 0 and 1 | Excellent | Strong direct robot comparison: cyan eye marks read against a dark faceplate; body gestures support the face. |
| `webbed-social-acting` 0 and 1 | Small | Appropriate body/social context, weak detailed face tiles at board size. |
| `botanicula-tiny-faces` 1 | Good | Large one-eyed central form and tiny companion eyes show how little facial information can carry character. |
| `wirm-event-face` 0 | Poor at card size | The whole worm is visible but the head/face is tiny. Keep as supporting process/game reference. |

## Credit spot checks

Independently fetched text supports Marlowe Dobbe's Art and Animation credit; Spiritfarer's separate game animation team and Knights of the Light Table trailer team; Tina Nawrocki's authorship of the three Cuphead character studies; Derek Lieu's cutscene role and Dan Paladin's opening/prologue work; Ian McConville's shader work; Scott Slucher's direct implementation discussion; and Miyuki Richardson's official animator credit. `source-validation.json` preserves source URLs and local fetched text paths.

Several exact-name searches report false negatives because the entry contains aliases or expanded names. Those are not automatically attribution failures. ArtStation returned 403 for the Bugsnax page; Tumblr failed for Jake Clark; the Klei forum returned 403. Their claims need the branch's other evidence or an explicit limitation. GDC independently confirms the Klei presenters.

The audit does not assign a specific trailer shot to one animator merely because they appear in a team credit. It also does not turn an art-director or developer title into a shot-level animation credit.
