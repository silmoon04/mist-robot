# Crawl diagnostic chart quality

## Iteration 1

- Generated: four panels for body X/Y progress, every scheduled swing's actual clearance, loaded-wheel count and individual actuator RMS.
- Lint: failed the preview-size limit because the initial PNG was 2400 pixels wide.
- Visual findings: the clearance threshold text crossed coloured bars, reducing contrast.
- Fixes: render PNG at 1800 × 1200 pixels and give the threshold label a white background. Vector exports remain available.

## Iteration 2

- Generated: corrected full-size chart and a separate 50% preview.
- Independent visual review: pass at full size and 50%, with no clipping, overlapping labels or misleading visual summary identified.
- Data check: derive the contact-loss episode from the saved contact threshold rather than copying the negative-margin episode's start time. The count first drops below three at 11.46 s; negative support margin starts at 11.48 s.
- Evidence handling: SHA-256 checks confirm that the source report, trajectory, controller and parameter snapshots were unchanged by chart generation.
- Final lint and preview results are saved in `chart_lint.md`.

## Iteration 3

- Linting the separate 50% preview exposed gutters below its fixed 24-pixel rule even though the full-size image passed.
- Increased left/top/bottom spacing in the generator and separated the footnotes from axis labels.
- Final lint: pass for both the 1800 × 1200 image and 900 × 600 preview, with zero findings.
- Final 50% inspection: all four panels, the support-loss annotation, and footnotes remain readable without clipping or overlap.
