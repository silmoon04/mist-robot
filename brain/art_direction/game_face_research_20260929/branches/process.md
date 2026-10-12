# Animator process references

Research date: 2026-09-29. The companion JSON contains four schema-complete entries. I used the research and unslop skills. Text evidence is primary; motion files are verified references, not visually analysed performances. No exact performance timestamps are asserted.

## Recommended order

1. **Richard Lico, Moss / Quill.** Start with the [official GDC talk](https://www.youtube.com/watch?v=u3CzLVpuE4k). His [authored explanation](https://blog.playstation.com/2018/04/09/the-magic-of-animation-in-moss-how-polyarc-brought-quill-to-life/) is the strongest source here for connecting an expression to the user's action. The [slides](https://media.gdcvault.com/gdc2018/presentations/Lico_Richard_Animating_Quill_Creating.pdf) provide the reaction-system and overlap context. For MIST, our inference is to author recognition, response and recovery around real conversation events.

2. **James Benson, Ori and the Blind Forest.** The [artist's reel](https://www.youtube.com/watch?v=gPWsk8N-EfE) pairs with his [GDC process talk](https://www.youtube.com/watch?v=m8lOwrWNbEY). This is a portfolio and workflow reference: no eye- or ear-specific lesson was verified. Our inference is to approve a small interaction reel before expanding MIST's expression vocabulary.

3. **Chris / twocentstudios, Dory prototype.** The [original face devlog](https://twocentstudios.com/2024/04/01/indie-game-devlog-04/) includes a [direct blink MP4](https://twocentstudios.com/images/devlog04-08.mp4). This is a useful implementation study, not a released-game acting benchmark. Our inference is to keep MIST's gaze, blink, expression and speech channels independent enough to edit without destroying one another.

4. **Kyle Banks, Farewell North.** His [facial-animation devlog](https://www.youtube.com/watch?v=fkB3tK6zZSo) is useful for evaluating whether a companion's face survives close inspection. The creator divides the video into eye/blink, lip-sync and facial-expression sections. Our inference is to review those channels independently and then together at MIST's real display size.

## Media and evidence checks

- Quill and both Ori videos have verified YouTube oEmbed titles and uploader identities. Farewell North additionally has its original YouTube description inspected directly.
- Dory's automatic blink MP4 returned HTTP 200 and `video/mp4`; the Dory image and official Moss still returned HTTP 200 and `image/jpeg`. The other Dory MP4 is present in the author's page HTML.
- No continuous motion was visually inspected. Every media entry therefore has `motionVerified: false`. This is deliberate: do not convert the supplied creator statements into claims about observed frame timing, asymmetry, gaze shifts or ear settles.
- The Quill blog's five historic GIF examples use Gfycat. They were not accepted as reliable playable media for the board. Use the official talk instead.
- The still images are source assets, but their pixels were not inspected in this branch. Captions identify their provenance and avoid invented face details.

## Leads not promoted

[Jonathan Cooper's own biography](https://www.gameanim.com/about/) verifies extensive game-animation credits. Searches found facial-animation categories, book contents and curated material, but not a sufficiently specific open authored eye/blink passage paired with an attributable visual demonstration. His name should not be attached to a technique merely because Game Anim links to another creator's work.

The process evidence is strongest for Quill. Dory and Farewell North complement the professional animator references with transparent implementation accounts. None should be presented as independent proof that continuous morphing, random blinking or lip sync automatically produces good acting.
