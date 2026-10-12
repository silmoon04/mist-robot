# MIST Fusion guide progress

Last updated: 2026-07-13

## Goal

Create a beginner-safe, current, polished Autodesk Fusion guide for the complete
MIST CAD workflow. Keep the July 12 master dimensions authoritative, show where
the design is still provisional, and use the six AI posters only as clearly
labelled concept art.

## Measurable completion checks

- [x] Detailed Markdown guide covers setup through export and print validation.
- [x] Local HTML guide is responsive, printable,
      keyboard-accessible, and has
      working navigation, search, progress, parameter explorer, and image zoom.
- [ ] Run `python tools/docs/build_fusion_guide_assets.py` so all six source
      posters have labelled local crops and official Help media is cached.
- [x] Current Fusion terminology and paths are checked against v2704.1.23
      (2026-07-09 hotfix).
- [ ] Replace the guide's five Autodesk hotlinks with the cached attributed
      files produced by the asset builder for reliable offline use.
- [x] Locked, measure-on-arrival, and provisional parameters are visually
      distinct; clearance semantics are explicit.
- [x] Four mounts use +25, -25, +109, -109 degrees, not a 4x90-degree pattern.
- [x] Links/assets/scripts pass automated checks and the guide passes desktop
      and mobile browser inspection.
- [x] Existing Onshape-first and stale Fusion wording is reconciled in current
      MIST documentation.

## Verification completed

- HTML: 12 ordered chapters, 72 unique build gates, 51 unique IDs, all local
  references present, and one valid closing document.
- Parameters: 81 unique CSV rows; every expression name resolves; the guide,
  source chapters, CSV, and master use one canonical namespace.
- JavaScript and tooling: `node --check` passes; the asset builder parses with
  Python; copy, search, progress persistence, presets, ROM warnings,
  unreachable-target rendering, zoom, and drawer interactions were exercised.
- Browser: default desktop, 900 px tablet, and 390 px mobile layouts pass with
  no horizontal page overflow; mobile drawer focus/escape behavior and image
  zoom pass. All five official Autodesk references load after native lazy
  loading is triggered at their chapter anchors.
- Media: five generated SVG teaching assets parse and render: the exact frame
  map, body/service-envelope cutaway, four-axis leg chain, assembly/pose study,
  and rounded Layout A simulator state. Six local AI sources remain linked for
  comparison; the five official Autodesk media URLs returned HTTP 200 during
  the 2026-07-13 check.
- Evidence screenshot:
  [`qa/mist-fusion-guide-desktop.svg`](qa/mist-fusion-guide-desktop.svg).

## Research decisions

- Beginner architecture: Hybrid Design + Parametric Modeling Mode.
- Advanced architecture: separate Part designs inserted into an Assembly, with
  explicit Derive/Edit In Place dependencies.
- Repeat geometry by associative component instances; use Duplicate With Joints
  at four explicit origins. Do not mirror or circular-pattern the four mounts.
- The fixed-wheel heading problem is unresolved. The guide presents scrub/skid,
  omni/caster, steering, and adjustable-pod options rather than claiming normal
  no-slip drive.
- Personal Use does not include editable Configurations; the baseline guide uses
  ordinary User Parameters and saved copies instead.
- The simulation optimizer found a 111 mm femur. The documented 110 mm rounded
  baseline passes the analytic pose battery but retains only 0.221 percentage
  points of reach headroom, so measured servo and horn geometry must trigger a
  full revalidation.

## Known repo conflicts carried as warnings

- `sim/js/config.js` defaults do not match the Fusion master dimensions.
- The old print-kit 65/85 mm leg baseline and 76 mm wheel do not match the
  current 110/70 mm and 70 mm baseline.
- [x] Rear-leg servo ID order reconciled: build docs and simulator hardware
  export now use FL 1-4, FR 5-8, RR 9-12, RL 13-16 (2026-07-13).
- Four servo-bus root taps are not physically resolved in the current BOM.
- Several tools and printable assemblies cited by older docs are absent.
