# Mouth component review

The three immutable source sheets were made with the built-in ImageGen tool, using the original MIST dash, smile, bowl and frown components as references. Each sheet contains six drawings. Cell 0 in every production strip is replaced by the same original MIST dash, giving a stable neutral for face changes. The delivered assets use fifteen generated drawings and one reused canonical drawing.

The original PNG alpha removes the apparent glow seen in some raw tool previews. Dark-background composites were checked before extraction. Production cels preserve that alpha, resample each complete strip with one shared scale, and set visible RGB to MIST's #5eeadd. The untouched source PNGs remain beside the extracted cells.

Each cel is 128 by 64 pixels. The mouth attachment is (64, 26). Source placement drift is corrected using the mouth's rounded corner centers; changing mouth depth never recenters the shape vertically. Smiles therefore deepen below the corners, concerned mouths lift between the corners, and bowls open downward. No silhouette is redrawn or deformed by the extraction script.

Review of the eighteen delivered cels in `all_contacts.png`:

- Smile: one rounded stroke progresses into a compact U. The middle step accelerates slightly, but no frame reverses the curve, gains a feature, or changes topology. The final smile is intentionally smaller than the old exaggerated grins.
- Bowl: the upper edge remains near its attachment while the lower edge opens gradually. There are no teeth, tongue tips, notches or separate floating marks.
- Concern: one shallow downward expression develops gradually, without a smiling midpoint. It stays symmetrical and restrained.
- All three start with exactly the same original dash. Component width stays around 80 pixels, without per-frame size fitting.

`preview.gif` in each family shows a forward/reverse motion study. These are component previews, not final acting timing or speech-sync validation. The compositor must review them in the full face at its authored exposures; this review does not claim that every possible voice sequence is natural.

`technical_qa.json` checks dimensions, unclipped bounds, shared-neutral equality and the ink palette. Those checks supplement the visual review; they do not establish motion quality by themselves.
