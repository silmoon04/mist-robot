# Speaking-mouth family review

Reviewed all 40 faces in the canonical contact sheet and compared their parts and runtime aliases. The mapping below keeps each original resting face. It changes only the drawings used during audible speech.

| Family | Faces |
|---|---:|
| Angry / tense | 4 |
| Skeptical / restrained | 5 |
| Neutral / indifferent | 16 |
| Happy / warm | 7 |
| Worried / distressed | 5 |
| Sad / low energy | 3 |

## Mapping

| Face | Speaking family | Reason |
|---|---|---|
| `01_angry_01_manual` | `mouth_angry` | Inward slanted lids and a tense straight mouth. |
| `02_angry_02_manual` | `mouth_angry` | Steep inward lids and a tall shouting opening. |
| `03_angry_07_manual` | `mouth_angry` | Compressed slot eyes and a pronounced crooked frown. |
| `04_angry_08_manual` | `mouth_angry` | Glaring lids and a centered frown. |
| `05_annoyed_01_manual` | `mouth_skeptical` | Unequal drooping lids and a pinched inverted-V mouth. |
| `06_annoyed_02_manual` | `mouth_skeptical` | Closed, uneven lids with a small crooked frown; restrained asymmetry fits both error and mischief aliases. |
| `07_annoyed_03_manual` | `mouth_flat` | One attentive round eye and one lowered lid; the flat-topped opening should stay neutral for its alert and listening aliases. |
| `08_annoyed_04_manual` | `mouth_skeptical` | Squeezed chevron eyes and a narrow tense opening; avoid rounded smiling vowel corners. |
| `09_happy_03_manual` | `mouth_smile` | Open round eyes and a broad smiling opening. |
| `10_happy_04_manual` | `mouth_smile` | Raised happy arcs and a playful curved mouth. |
| `11_happy_05_manual` | `mouth_smile` | Open eyes and an explicit upward-cornered smile. |
| `12_happy_09_manual` | `mouth_smile` | Happy chevron-eye identity with no canonical mouth; smiling fallback only while audio is active. |
| `13_happy_14_manual` | `mouth_smile` | Raised happy arcs and an explicit smile, shared by happy, love and proud. |
| `14_happy_16_manual` | `mouth_smile` | Raised happy arcs carry affection despite a small straight rest mouth. |
| `15_misc_15_manual` | `mouth_flat` | Level closed bars and an uninflected small oval; keep the deadpan read. |
| `16_misc_16_manual` | `mouth_flat` | Lowered closed lids and a yawn-like oval; smiling vowels would contradict sleepiness. |
| `17_misc_2_01_manual` | `mouth_flat` | Three horizontal bars, a fully flat reaction. |
| `18_misc_2_02_manual` | `mouth_worried` | Heavy uneven eyes and an uncertain opening; a mild downward tension suits uncertainty. |
| `19_misc_2_03_manual` | `mouth_flat` | Squeezed eyes and a straight rest mouth; keep embarrassment restrained rather than adding a smile or a strong frown. |
| `20_neutral_06_manual` | `mouth_flat` | Round attentive eyes and a dot mouth; curiosity does not imply happiness. |
| `21_neutral_11_manual` | `mouth_flat` | Closed lids and a plain dome opening; supports both neutral and sleepy aliases. |
| `22_neutral_12_manual` | `mouth_flat` | Closed low lids with a straight mouth, used for boredom. |
| `23_neutral_13_manual` | `mouth_flat` | Closed low lids and a tiny vertical oval, used for boredom. |
| `24_neutral_2_01_manual` | `mouth_flat` | Level slot eyes with a straight mouth; alertness should not gain a smile. |
| `25_neutral_2_03_manual` | `mouth_flat` | Round attentive eyes and a small round opening, shared by curious and listening. |
| `26_sad_01_manual` | `mouth_flat` | Lowered closed lids and a straight mouth; used as bored despite the sad filename. |
| `27_sad_02_manual` | `mouth_sad` | Heavy tilted eyes and a low-energy opening; its runtime alias is sad. |
| `28_sad_03_manual` | `mouth_worried` | Uneven heavy eyes, a wavering mouth and a tear; anxious surprise rather than cheerful surprise. |
| `29_sad_04_manual` | `mouth_skeptical` | Closed lowered lids and a pinched W-shaped mouth; a restrained asymmetric family is safer across smug and embarrassed aliases than a broad happy mouth. |
| `30_sad_05_manual` | `mouth_worried` | Tightly squeezed eyes and a sharp downward-cornered mouth, used for panic. |
| `31_sad_06_manual` | `mouth_sad` | Drooping inward lids and a tall lamenting opening. |
| `32_sad_07_manual` | `mouth_sad` | Large eyes, a clear downward-cornered frown and a tear. |
| `33_sad_08_manual` | `mouth_worried` | Uneven raised/low lids and a wavering mouth, used for panic. |
| `34_sad_09_manual` | `mouth_worried` | Heavy eyes and a deep frown, used for panic; worried vowels retain distress. |
| `35_sad_10_manual` | `mouth_flat` | Lowered closed lids with no canonical mouth; flat fallback only while audio is active. |
| `36_misc_03_manual` | `mouth_skeptical` | Uneven alert/squint eyes and a diagonal mouth; preserve its crooked doubtful read. |
| `37_misc_06_manual` | `mouth_smile` | Narrow level eyes and an actual upward-cornered smirk; its smug alias has visible positive curvature. |
| `38_misc_2_06_manual` | `mouth_flat` | Heavy lifted lids and a tall oval read as surprise; keep a neutral round opening without adding distress. |
| `39_neutral_02_manual` | `mouth_flat` | Round neutral eyes and a straight mouth; shared neutral/thinking identity. |
| `40_neutral_03_manual` | `mouth_flat` | Slot eyes and a dot mouth; retain a quiet neutral read. |

## Shared identities and ambiguity

- Assign by canonical face ID, not filename prefix or current preset. A face may be shared by several presets.
- Preserve the original canonical mouth at rest and immediately on silence or interruption. Family rest is a speech-transition drawing, not a replacement for the original face.
- The source assets have 40 canonical face IDs, 21 public presets and aliases; counts of presets do not describe counts of mouths.
- 12_happy_09_manual and 35_sad_10_manual have no canonical mouth. Preserve that at rest and use the assigned fallback only during audible speech.
- 29_sad_04_manual is an ambiguous closed-eye W-mouth face shared by smug and embarrassed. The sad filename is insufficient evidence. Prefer restrained skeptical speech over either broad happiness or heavy sadness.
- 37_misc_06_manual has a clear smirk, so its smug alias can use smile. The two smug variants need not have identical speaking families.
- 38_misc_2_06_manual and 28_sad_03_manual both expose surprised, but 28 has a wavering mouth and tear whereas 38 has a plain O; worried and flat respectively preserve that distinction.
- 06_annoyed_02_manual is shared by error and mischief. Its crooked frown is best served by restrained asymmetric speech, without changing its resting identity.
- Do not give all faces in a public preset the same family: neutral includes a sleepy alternate, surprised includes a tearful alternate, and smug includes a pinched W-mouth alternate.
- Labels describe the speech drawing set, not an instruction to a model to change emotion. Agents should continue choosing existing expression and variant; the renderer resolves the mouth family.

## Evidence and limits

The review used `reuse/faces_sheet.png`, the original/cleaned/canonical comparison in `brain/face_assets/reports/canonical_gallery_3.png`, canonical part slots and `brain/duplex/face_map.json`. New ImageGen family sheets still need a separate artwork review. Ambiguous family choices are art-direction recommendations.
