# Final catalog evidence audit

Audited file: `board/catalog.json`

SHA-256: `489dd7822c08ccdbfbc47ae612608ec2d9e91d46663b30dabbe093d80e602f9e`

Bound result: 35 studies, 86 distinct media URLs, 85 marked verified and one known unavailable URL marked unverified. `final-catalog-validation.json` contains the catalog path, hash and per-URL HTTP evidence. This review applies to that byte sequence; later catalog edits require rebinding.

No unresolved source or media blocker was found in the four added narrative entries. This is an evidence/media audit, not a certification of final browser layout or continuous playback. The original branch report is `REVIEW.md`.

## Network and display findings

- 84 of 86 catalog media URLs returned HTTP 200 to normal-TLS curl HEAD requests. All direct image/GIF media decoded successfully across the nine branches (50 assets). These checks establish availability and format, not rights or continuously perceived motion.
- BattleBlock's old Vimeo URL returns 404 and is correctly marked `verified: false` in the final catalog. It must be excluded from playable/display media. The associated official artwork and source article remain valid.
- The Psychonauts hash-bearing Vimeo player returns 405 to curl HEAD and previously returned 401 to curl GET. Root relayed successful browser playback by the 3D researcher. This is recorded as a curl limitation, not a dead-embed finding. This audit did not independently reproduce the browser playback.
- No individual `motionVerified: true` claim was present in the audited catalog. This preserves the distinction between inspected stills/decoded GIF frames and watched timing. The UI should preserve the explanation rather than presenting every linked clip as watched research.

## Four new narrative studies

| Entry | Independent source and credit assessment | Display assessment |
|---|---|---|
| Later Alligator | Wacom's joint creator interview supports Lindsay's directing, writing and design work, Alex's keyframing role, and shared animation/design. It supports choosing reactions around individual conversation nodes. The entry correctly avoids assigning this exact GIF to only one person. | GIF is HTTP 200 image/gif, 800×450, 48 stored frames. Sampled first frame shows Sweet Geraldine's directional eyes, curved mouth and body posture clearly. Good lead reference. No continuous timing claim made. |
| Smile For Me | Official press history supports Day/Yugo co-creation and distinguishes nod/shake controls from multimedia art direction. Studio biography supports Yugo's animator role and Day's production/programming/design roles. These are project credits, not exclusive ownership of every character shot. | Both supplied comparison GIFs are HTTP 200 image/gif and decode successfully: 640×152 and 639×152. They show two copies of a character side by side. At thumbnail size, the face is small and dialogue/environment dominate. Useful response comparison when enlarged; weaker than Slime Rancher, OMORI or Dicey as an opening facial close-up. |
| Great God Grove | Official press page's embedded structured content explicitly gives Jack Cornish the role “3d animations.” A text-only extraction misses this because it is stored in page data, but the fetched original HTML preserves it. Developer and studio-bio roles are also supported. Entry explicitly limits this to a project-wide credit rather than the individual shot. | GIF is HTTP 200 image/gif, 600×150, 192 stored frames. First frame shows green and orange god faces with contrasting eye silhouettes. Its wide split-screen format needs enlargement; keep below stronger close-up references. |
| Thank Goodness You're Here! | Pip Williamson's portfolio directly describes leading the animation team, the hybrid in-engine/replacement-sprite workflow, and the Design/Development credits for James Carbutt/Will Todd. | Correctly process-only. Portfolio URL and supplied YouTube URL are available; no substitute image was manufactured. `start=248` originates in the portfolio and is not a researcher-verified timing claim. Retain this qualification. |

Source evidence is saved under `audit/sources/`, with lookup details in `source-validation.json`. Source-to-media checks in `media-source-validation.json` cover 46 source pages; 71 of the 86 media URLs or complete paths occur literally in source HTML. Remaining literal misses include relative URLs, alternative embed syntax and restricted source fetching, and are not automatically provenance failures.

## Curation recommendations after the updated order

The explicit preview choices improve Chicory, Hopus Pocus, Baroness, Dory and Botanicula. Dory's close-up still is a better lead than its process video. Later Alligator is a strong opener.

The final order now places Smile For Me after Slime Rancher, Dicey, OMORI and Hopus Pocus, resolving the opening-order concern. Still give its 4.2:1 strip enough width to read. Its value is the paired response context; it is not a facial close-up. Great God Grove has the same 4:1 display issue but is already lower in the order.

Pip/Dot and Baroness remain small within full paper sheets, even with a better selected drawing. Give the user an original-size view. Webbed and Wirm are body/social references with distant faces, so keep them in supporting/process positions. Ori's talk thumbnail and Klei's PDF are process material. Do not promote those as eye/mouth close-ups.

ANTONBLAST's selected close-up video is network-valid; this independent pass did not continuously inspect it. Preserve the branch's scope of observation and avoid implying that the distant-platform GIF was the facial close-up.

No branch, catalog or UI files were changed by this auditor.
