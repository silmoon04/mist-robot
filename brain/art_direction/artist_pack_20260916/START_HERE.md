# MIST: artist handoff, proposed first release

MIST is a small quadruped with an upright phone in landscape orientation. The screen is its face. We want something slightly hand-drawn and a little untidy, but deliberate: soft uneven contours, mild asymmetry and a few expressive accents. It should be comfortable to talk to for several minutes, not constantly performing.

This pack proposes a scope. It contains existing references and blank templates, not finished new artwork. The new style, exact shapes and motion need the owner and artist's review before a full drawing pass. Nothing here replaces the running face.

## Start with the default

The everyday face should have relaxed open eyes and a closed, nearly straight mouth. It can look gently attentive without smiling all the time. Listening uses more alert eyes; thinking has a small focused squint and an upward sideways glance, with the mouth closed. Talking temporarily animates the mouth over the current expression. Speaking is a behavior, not another full face to redraw.

For the visual direction, explore two small style sheets: one soft and rounded, one with a slightly irregular ink-like contour. Each sheet shows neutral, happy and thinking. These six rough compositions are concept work, separate from the production count. Test them at actual phone size with glow off as well as on. Choose the direction before polishing the rest.

## Exact proposed workload

| Item | New component drawings |
| --- | ---: |
| Base eye pairs, E01 to E10 | 10 |
| Reusable mouths, M01 to M08 | 8 |
| Half-closed and closed blink pairs for four eye families, B01 to B08 | 8 |
| Extra accent eye pairs, A01 to A06 | 6 |
| Two alternate redraws each of neutral, happy and focused eyes, R01 to R06 | 6 |
| Total production component drawings | 38 |

An eye-pair drawing is one design unit with two separately editable eyes. If counting individual exported shapes, this is 60 eye layers plus eight mouth layers, or 68 parts. Those numbers are not estimates of equal effort or hours. Do not quote the job as 38 full-screen animation frames.

The 38 components assemble into 12 core face layouts. Supply a review sheet showing all 12 combinations; those are assembled compositions, not another 12 original drawings. The drawing_checklist.csv lists every asset ID, what to draw, its reference and a notes/status column.

## Do it in three passes

1. Style exploration: the six rough neutral/happy/thinking compositions described above. Choose one direction.
2. Small production pilot: E01 neutral eyes, E04 focused eyes, M01 closed mouth, M06 open speech mouth, B01 half-closed eyes and B02 closed eyes. Six components, all included in the total of 38. Assemble neutral and thinking, one blink, a neutral-to-thinking transition and a short AA/rest speech sample. This proves the style at phone scale and during motion.
3. After the pilot works: complete the remaining 32 component drawings, then assemble the 12 layouts and the motion review sheet. Add rarer emotional faces only after this set feels right.

## Core layouts

| Layout | Eyes + mouth | What it communicates |
| --- | --- | --- |
| F01 Available | E01 + M01 | Calm, present; the default |
| F02 Listening | E02 + M01 | Paying attention, mouth closed |
| F03 Thinking | E04 + M01 | Focused, gaze up and sideways |
| F04 Happy | E03 + M02 | Warm pleasure, brief accent |
| F05 Curious | E09 + M01 | A small uneven eye lift |
| F06 Focused | E04 + M01 | Same art as thinking, gaze centered |
| F07 Concerned | E05 + M03 | Gentle concern, no automatic tears |
| F08 Sleepy | E06 + M01 | Heavy lids, slower movement |
| F09 Deadpan | E07 + M01 | Mild annoyance or dry humor |
| F10 Surprised | E08 + M08 | Brief wide-eyed reaction |
| F11 Playful | E10 + M04 | A small asymmetric smile |
| F12 Reassuring | E05 + M02 | Concerned eyes with a warm mouth |

We can keep the app's 20 expression names while sharing these drawings. Proposed aliases: neutral uses F01; listening F02; thinking F03; happy and proud F04; curious F05; alert F06; sad F07; sleepy and bored F08; angry and dead_inside F09; surprised and panic F10; mischief, smug and suspicious F11; love and embarrassed F12. The rarer names would lose some distinctions in this first release. These aliases are a proposal, not current behavior. Strong panic, rage, tears and heart-shaped eyes are deferred.

## What makes it hand-drawn

Use a slightly uneven curve and a little unequal timing between the two eyes. Keep the silhouette readable and the shape intentional. A tiny squish before a happy reaction and a quick overshoot into surprise give more character than adding constant movement.

The alternate drawings are a subtle contour variation of the SAME expression. Their centers and overall scale must stay registered. Start with a one- or two-pixel contour difference when viewed in an 800 x 512 review image. Treat this as a trial amount, not a rigid line-thickness rule. Avoid random position jitter, whole-face shaking, permanently trembling outlines or flickering glow. Let the face become still while the person talks.

Glowing cyan on a dark screen is the reference palette, not a requirement to copy the old shapes. Test a clean silhouette first. We can apply glow in code; do not paint it into the linework.

## What the references mean

index.html works offline after extracting the whole folder. It shows the 12 proposed combinations beside current reference faces, all 40 existing variants, the complete component list and a motion demonstrator. The demonstrator uses current geometry only. It does not show the artist's future style or implement the new hand-drawn blink frames.

The reference archive is derived from surviving local face assets. Original capture images are missing, and this pack does not establish ownership or license of earlier designs. Use the reference faces to discuss readability, mood and placement; develop an original visual treatment rather than copying an unknown artist's design.

The earlier repository contains a 450-frame generated Aseprite study. That is an implementation reference, NOT a request for 450 new hand drawings. It was excluded from the core handoff to avoid confusing the workload.

## Review before proceeding

At actual phone size: can we distinguish listening, thinking and speaking without labels? Does the mouth return to the intended rest shape? Does a blink close cleanly without eyes shrinking into dots? Does a transition avoid showing two mouths or two sets of eyes? Does speech still look like the same character when happy or concerned? Can we watch an idle face for a minute without it feeling nervous?

Approval milestones: selected style, six-component pilot, full 12-layout sheet, and timed motion review. The timing values in MOTION_GUIDE.md are proposed starting points. Animation quality and effort should be judged from the pilot, not from a guessed hour estimate.
