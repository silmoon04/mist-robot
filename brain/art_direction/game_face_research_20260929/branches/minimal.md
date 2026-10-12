# Minimal and nonhuman game faces

Research date: 2026-09-29. Four selected references; no changes to MIST artwork or animation.

The strongest direct reference is Astro Bot: an eye-only face, named animation staff, documented process and original studio GIFs. Webbed supplies the strongest small-creature social gestures. Botanicula supplies still-image evidence of attention and silhouette. Wirm supplies an unusually concrete creator statement linking a minimal face to a gameplay event.

## Evidence limits

The GIFs loaded and browser screenshots captured individual poses. This verifies their source and appearance, but it is not continuous motion analysis. All motionVerified values remain false. There are no invented timestamps, frame counts, blink rates or expression-hold durations. MIST timing suggestions below are our inferences.

## Candidate notes

### Astro Bot: LED eyes and physical acting

A directly relevant screen-face reference with named animation staff and original studio-published GIFs.

People: Jamie Alexander Smith (Animation Lead, Astro Bot Rescue Mission); Jamie Smith (Principal Animation Director, Team Asobi (2024 interview)); Maki Murakami (Senior Animator, Team Asobi (2024 interview)); Sebastian Brueckner (Art Director, Astro Bot Rescue Mission).

- Doucet says the design deliberately avoided a mouth and stretching faces, leaving the eyes as its main expressive feature. [creator statement](https://www.pushsquare.com/features/interview-the-making-of-astro-bot-the-ps5s-next-great-exclusive)
- The inspected celebration GIF frame combines two upward blue eye arcs with lifted hands and an upright body. The face has no separately drawn pupil, brow or mouth; the silhouette reinforces the eye expression. [visual observation](https://farm5.staticflickr.com/4836/39891228403_12f092a56a_o.gif)
- The Rescue Mission team reports that conventional cartoon exaggeration required timing adjustments for VR. They also describe bosses becoming vulnerable and silly as the player hits back, making expression a response to progress in the encounter. [creator statement](https://blog.playstation.com/2019/01/24/astro-bot-rescue-mission-inside-the-art-and-animation-of-japan-studios-ps-vr-hit/)
- Jamie Smith describes studying children's excited actions, including jumping, to build playfulness into animation. [creator statement](https://blog.playstation.com/2024/09/09/astro-bot-how-team-asobi-created-a-unified-vision-for-fun/)

MIST experiments:

- Our inference: test a small eye-shape vocabulary on MIST's existing face before adding extra facial features. Pair each shape with one readable head or body attitude.
- Our inference: make a completed action trigger a held pleased shape, followed by a small recovery. Do not run the entire expressive vocabulary as an idle loop.
- Our inference: use a blink at a change of attention or after a completed reaction, then let the new gaze settle. This is a proposed MIST experiment, not a verified Astro blink rule.

Visual references:

- [Astro celebration animation; inspected frame shows curved blue eyes and lifted hands](https://farm5.staticflickr.com/4836/39891228403_12f092a56a_o.gif) | Team Asobi / Sony Interactive Entertainment. Source: [official page](https://blog.playstation.com/2019/01/24/astro-bot-rescue-mission-inside-the-art-and-animation-of-japan-studios-ps-vr-hit/).
- [Studio-published Astro body-action loop; head lowered in sampled poses](https://farm8.staticflickr.com/7881/31914878607_25f295492a_o.gif) | Team Asobi / Sony Interactive Entertainment. Source: [official page](https://blog.playstation.com/2019/01/24/astro-bot-rescue-mission-inside-the-art-and-animation-of-japan-studios-ps-vr-hit/).
- [Official 2024 Astro Bot launch trailer](https://www.youtube.com/watch?v=unYFdcEjV9k) | PlayStation / Team Asobi. Source: [official page](https://www.youtube.com/watch?v=unYFdcEjV9k).

Limit: Official GIF URLs resolved and were inspected through browser screenshots. Sampled poses only, not continuous motion perception; no exact timing or blink-rate claim. The 2019 and 2024 credit labels are kept separate as published. Specific GIF authorship is not assigned to an individual.

### Webbed: greeting and dance as social expression

A tiny spider remains socially readable through visible eyes, orientation and raised front limbs; the developer provides original greeting and dance GIFs.

People: Riley Neville (Programming, Art, Sound and Game Design).

- In the greeting GIF's inspected frame, the spider sits directly beside another insect under its speech balloon. The small bright eye marks remain visible against the dark face, while proximity makes the interaction legible. [visual observation](https://webbed.website/img/presskit/gifs/G_day.gif)
- The dance GIF's inspected frame shows the spider leaning with front limbs raised beside a much larger moth. The face occupies very little of the image; the limb silhouette supplies a stronger signal. [visual observation](https://webbed.website/img/presskit/gifs/danceparty.gif)
- Neville describes the spider's dance as a wiggle-arms move and discusses procedurally animated characters in the GameMaker interview. [creator statement](https://gamemaker.io/en/blog/webbed-interview)

MIST experiments:

- Our inference: make a greeting a brief acknowledgement of the arriving person, with a held look and one small gesture. The social target matters more than adding a large smile.
- Our inference: test MIST reactions at the smallest intended display size. If the face becomes hard to read, reinforce the same intent through a body tilt rather than adding tiny facial detail.
- Our inference: reserve an energetic celebration for meaningful success; return to a settled attentive pose after it.

Visual references:

- [Webbed spider and insect greeting with a dialogue balloon](https://webbed.website/img/presskit/gifs/G_day.gif) | Sbug Games / Riley Neville. Source: [official page](https://webbed.website/presskit.html).
- [Webbed spider social dance beside a moth](https://webbed.website/img/presskit/gifs/danceparty.gif) | Sbug Games / Riley Neville. Source: [official page](https://webbed.website/presskit.html).
- [Webbed official site trailer](https://www.youtube.com/embed/xcSo912bT44) | Sbug Games. Source: [official page](https://webbed.website/).

Limit: GIF assets loaded in browser and sampled frames were inspected. No continuous playback analysis or frame counts. Neville is credited exactly as the game credits state, without inventing a separate lead-animator title.

### Botanicula: tiny eyes, unusual bodies and group staging

The botanical cast shows how much character can survive when faces are a few tiny marks on strongly different bodies.

People: Jaromír Plachý (Animator and creator of Botanicula, as described on Amanita's official forum index).

- In screenshot 04, several small protagonists cluster together on a branch opposite a huge hanging dark creature. Tiny bright eyes, very different body proportions and the distance between groups carry the scene; a detailed human face is unnecessary. [visual observation](https://amanita-design.net/img/games/botanicula-04@2x.jpg)
- Screenshot 03 repeats a one-eyed creature at different sizes. The large foreground eye gives a clear directional cue, while the surrounding small versions retain the same instantly readable eye-and-body arrangement. [visual observation](https://amanita-design.net/img/games/botanicula-03@2x.jpg)
- In the archived IndieCade interview, Plachý and Stehlík describe nature and an old garden as inspiration; they also say the musicians saw animations during the collaboration. [creator statement](https://forum.amanita-design.net/index.php?topic=4278.0)

MIST experiments:

- Our inference: let a shift of attention move the whole eye pair or head toward a specific target, then hold. Avoid continual wandering that has no apparent object.
- Our inference: try quiet listening with a nearly still face and a slight body lean. Contrast will give the next clear reaction more weight.
- Our inference: borrow the clarity of silhouette and gaze, not the botanical textures or character shapes.

Visual references:

- [Tiny botanical protagonists face a large dark hanging creature](https://amanita-design.net/img/games/botanicula-04@2x.jpg) | Amanita Design / Jaromír Plachý. Source: [official page](https://amanita-design.net/games/botanicula.html).
- [One-eyed creatures at multiple scales around tree branches](https://amanita-design.net/img/games/botanicula-03@2x.jpg) | Amanita Design / Jaromír Plachý. Source: [official page](https://amanita-design.net/games/botanicula.html).
- [Botanicula trailer embedded on the developer's official page](https://www.youtube.com/embed/gxoxCxLdsNE) | Amanita Design. Source: [official page](https://amanita-design.net/games/botanicula.html).

Limit: Three official stills were inspected. Trailer embed URL verified in developer page HTML, but its motion was not inspected. Credit evidence is Amanita's own forum description rather than a full production credit roll; the interview is a moderator-posted archive of the original interview. Do not infer expression hold lengths from these stills.

### Wirm: a minimal face reacts to falling

A useful indie comparator because its creator explicitly ties a tiny facial change to a physical event: falling off a rock.

People: Riley Neville (Developer; describes making Wirm in a direct 2022 interview).

- Neville describes Wirm's smiling face changing to an open-mouth expression when it falls off a rock. This is direct evidence of an event-driven expression rather than a claim inferred from a trailer. [creator statement](https://gamemaker.io/en/blog/webbed-interview)
- The inspected official screenshot shows only small dark face marks at the worm's end, while the body drapes over a rock toward a gap. The facial marks remain attached to the body's orientation. [visual observation](https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1934870/c0838cc251025a7c7750ab960fc6559668463c72/ss_c0838cc251025a7c7750ab960fc6559668463c72.1920x1080.jpg?t=1765317868)

MIST experiments:

- Our inference: connect surprise to a real interrupt or unexpected outcome, then let the face recover when that condition ends.
- Our inference: test the same causal structure with MIST's eyes alone: a brief opening change followed by a stable look at the cause. The mouth is optional; the event relationship is the useful reference.
- Our inference: a blink can punctuate the return to listening after surprise, but the sources here do not establish a Wirm blink technique.

Visual references:

- [Wirm draped over a rock toward a gap, showing its tiny face](https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1934870/c0838cc251025a7c7750ab960fc6559668463c72/ss_c0838cc251025a7c7750ab960fc6559668463c72.1920x1080.jpg?t=1765317868) | Sbug Games. Source: [official page](https://store.steampowered.com/app/1934870/Wirm/).
- [Official store-page looping Wirm banner video; supplementary visual only](https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1934870/extras/9777660c6fab28be4121e14c09f7cef9.mp4?t=1765317868) | Sbug Games. Source: [official page](https://store.steampowered.com/app/1934870/Wirm/).

Limit: Screenshot inspected; MP4 URL came directly from the official Steam description via its app-details API and was not continuously viewed. Falling expression evidence is a 2022 development statement, not a verification of the shipped 2025 build. No specific animator title is claimed.

## Choices to carry into review

1. **Eye-only emotion:** Astro is the main comparator. Use eye contours plus a compatible posture; separate brows and pupils are not prerequisites.
2. **Gaze as attention:** decide what MIST is looking at before deciding how its eyes move. Botanicula supplies a useful compositional reference, not a measured gaze-animation recipe.
3. **Blink as thought punctuation:** test a blink around a change of attention or recovery. None of the inspected sources establishes this as the named creators' rule, so it must stay labelled as a proposed experiment.
4. **Hold and response:** Wirm supplies the clearest causal statement. A meaningful event changes the face. The precise onset, hold and recovery must be designed and reviewed for MIST rather than copied from unmeasured footage.
5. **Small-scale readability:** Webbed makes social intent visible through proximity and gesture even when the face is tiny. Keep that option available if MIST's eye detail disappears at display size.

## Leads not promoted

- Grow Home: Ubisoft's [official article](https://news.ubisoft.com/en-us/article/7fDmgKCCwWJQtyoVoOvvGM/get-ready-to-grow-home) documents BUD's procedural motion and quotes producer Pete Young. This is useful for whole-body physics but weaker for the requested facial acting. Pete Young was not labelled an animator.
- Sackboy, Kirby and Chibi-Robo were considered as possible comparators but not promoted without comparable primary credit/process evidence in this branch.
