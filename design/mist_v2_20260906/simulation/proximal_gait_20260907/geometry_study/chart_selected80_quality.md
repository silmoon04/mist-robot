# Selected 80 mm chart quality

## Iteration 1

- Adapted the verified four-panel diagnostic into a separate generator and separate PNG/SVG/PDF outputs, preserving the earlier 4-second artifacts.
- Checked the full-size image: the similar FL hip/knee RMS values caused adjacent labels to touch.
- Adjusted the generator to stagger close RMS labels and give the support annotation a white background.

## Iteration 2

- Checked the revised full-size chart and 50% preview for legibility, clear thresholds, annotation separation and edge clearance.
- Independent numerical review recomputed the selected and lower-grip cases from their saved trajectory and 1 kHz torque arrays. All reported metrics matched.
- Final deterministic image lint is recorded separately in `chart_selected80_lint.md`.
- Input hashes are recorded in `controller_selected80_chart_sources.json`; all source evidence remains unchanged.
