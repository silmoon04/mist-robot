# MSI remote interface verification

Completed on 12 October 2026 using the web-design router and Impeccable's polish/operate workflow. The scope was the existing simulation and joint commissioning pages plus a Windows launcher. The frozen physics, controller, sensor and actuator sources were preserved. The user is building the R7; physical measurements and walking qualification remain unfinished.

## Interface and browser evidence

The simulation has a live CAD view, named telemetry with units, held movement controls, explicit connection/reset states, setup disclosures and single-leg IK. The joint page shows bridge interlocks, requested joint angles, four leg projections and a clear dry-run telemetry state. Both retain their existing light/dark teal identity and use local HTML/CSS/JavaScript without a new dependency.

Live Codex browser checks covered desktop and 390-by-844 narrow viewports. Both narrow pages had a 375 px client width and matching scroll width, so neither overflowed horizontally. The initial simulation mobile layout placed the movement heading at y=1143 px, after telemetry. One layout fix placed movement directly after the CAD preview; confirmation measured the heading at y=552 px and Stop at y=754-822 px. The desktop layout and inline simulation script bytes were unchanged by that layout fix. Named regions remained visible in the accessibility tree. Temporary viewport overrides were cleared after verification.

The live simulation accepted held W and Q input and returned to a zero command after release. A phone-sensor/no-phone reset was refused with a specific explanation, preserving the running MPU episode. Restoring the default payload/sensor successfully started a new episode at rest. Single-leg IK returned 0.00/29.99/81.03 degrees. In the joint dry run, enabling preview enabled sliders, a keyboard increment changed FL yaw by .1 degree, Q while focused on that slider did not start a crawl, and IK returned 0.0/28.8/84.2 degrees. Stop and inspected-fault clearing returned the page to disabled preview. No captured browser errors or warnings were present. Final state was a live simulation with zero command and a connected, disabled joint preview.

Saved browser views:

- [Simulation desktop](simulation-desktop.jpg)
- [Simulation narrow viewport](simulation-mobile.jpg)
- [Joint desktop](joints-desktop.jpg)
- [Joint narrow viewport](joints-mobile.jpg)

The manual Impeccable detector ran once. It reported an image without a static `src`; the image is deliberately hidden until the frame fetch supplies its source, with a waiting message shown meanwhile. The browser confirmed a decoded live image. It also caught a 10 px mobile Stop shortcut; that was corrected to 11 px and confirmed through computed style. There was no additional styling pass.

## Control and launcher checks

Thirteen Node regressions passed against the actual inline page scripts. They cover delayed command completion followed by blur/hide/pagehide Stop, autorepeat after button/Space/Escape Stop, editable-field filtering, pointer cancellation, explicit reset refusal versus unknown transport outcome, joint slider/gait ordering in both directions, release-to-Stand ordering and a late arm reply after a newer Stop. The tests use controlled API replies and do not exercise physical hardware.

Five isolated Linux session regressions passed. They cover malformed/stale/unrelated process records, the bridge's actual dry-run versus hardware status boundary and cleanup of an already-started child if a later startup fails. The seven support-transfer tests also passed in the final combined twelve-test Python invocation.

The actual Windows command launcher passed startup, repeated use, two simultaneous launches and a path-with-spaces failure. Readiness requires the supervisor's acknowledgement and both health endpoints; existing healthy endpoints did not mask a failing launch. Stop closed the owned joint service while preserving the separately started simulation, and restart passed. The desktop shortcut targets `Start MIST Remote.cmd`. These checks are recorded in `../../runs/msi_20261012/remote_ui/launcher_checks.json` and `verification.json`.

The launcher supplies no serial port or calibration. Session PID records and logs are local runtime state, excluded from Git and portable archives. A separately started service remains with its original owner when the managed session stops. See [REMOTE_GUIDE.md](../../REMOTE_GUIDE.md) for controls and session commands.

## MSI-REMOTE-001 lesson

A stop can be overwritten by an older request that completes later, even when the visible button changes immediately. The scoped improvement is serialized command delivery with a trailing stop and intent-generation checks, owned by the two inline remote scripts. The thirteen regressions verify those public event boundaries. Likewise, launcher health alone cannot prove a new child started; the supervisor acknowledgement and real Windows failure case verify that boundary. These checks should remain part of later remote changes. The evidence establishes usable simulation/dry-run controls, not physical safety qualification or successful walking.
