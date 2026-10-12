# Review of the 4-second, three-cycle supported crawl

The saved `supported_60mm_4s_3cycles` run passes its recorded model criteria and advances **183.97 mm in 51.52 seconds**. It also contains a brief loss of the intended three-wheel support: **0.280% of samples after initial settling have fewer than three wheels carrying more than 1 N**, and the minimum sampled support margin is **−17.89 mm**. The result demonstrates slow simulated crawling with recovery from a transient support loss. It does not establish continuously positive support, physical reliability or fast walking.

This review is limited to that completed run. It does not rank the later force-feedback experiments or change any raw report, trajectory, parameter or controller file.

![Four-panel diagnostic chart](controller_review_4s_3cycles.png)

Vector exports: [SVG](controller_review_4s_3cycles.svg) · [PDF](controller_review_4s_3cycles.pdf). The generator is [plot_controller_review.py](plot_controller_review.py). The exact input hashes and the check that source evidence remained unchanged are recorded in [controller_review_chart_sources.json](controller_review_chart_sources.json).

## Result and limits

| Measurement | Saved or independently derived result |
|---|---:|
| Model mass | 6.341 kg |
| Planned translation | 180 mm over three four-leg cycles |
| Actual translation | 183.975 mm forward |
| Duration / mean forward speed | 51.521 s / 3.571 mm/s |
| Verified swings | 12, each unloaded and subsequently touched down |
| Smallest peak clearance among all 12 swings | 17.907 mm, against a 15 mm requirement |
| Largest individual actuator RMS | 0.616955 Nm, against an assumed 0.728144 Nm continuous limit |
| Actuator saturation | 3.280% of physics steps have at least one saturated servo |
| Maximum tilt | 5.332° |
| Maximum yaw / final yaw | 5.421° / 0.168°, derived from saved base quaternions |
| Maximum lateral excursion / final lateral displacement | 48.540 mm / −0.273 mm |
| Matching cycle-to-cycle milestone advances | 58.207 mm and 58.870 mm |
| Minimum support margin | −17.894 mm |
| Samples with fewer than three loaded wheels | 7 after settling, or 0.280% |

The lateral excursions are largely intentional COM shifts, so maximum excursion and final drift are different measurements. The two cycle-to-cycle distances compare the same support phase after successive complete leg sequences. They are not three independent neutral-to-neutral distance measurements.

The contact-count episode spans sampled times **11.46–11.60 s**, during the first RR swing. FL also unloads, leaving FR and RL to carry most of the robot. The sampled support margin first becomes negative at 11.48 s and reaches −17.894 mm. Contact count uses a **1 N per-wheel threshold**, while the support polygon uses qualifying individual contacts above **0.25 N**. These two diagnostics can therefore disagree on a weakly loaded third wheel; the chart keeps their definitions explicit.

The saved criterion allows fewer than three loaded wheels for up to 5% of sampled time, so the 0.280% episode passes that criterion. There is no requirement for a positive minimum support margin, and yaw is not part of the pass criteria. Pre-lift support gating is enabled and waited zero seconds in this run. It does not prevent the later mid-swing loss of another support wheel. Contact-force feedback is disabled in this particular controller snapshot (`contact_gain_m_per_n = 0`).

## Findings and corrections

| Issue discovered during review | State relevant to this report |
|---|---|
| The first cycle distance compared an initial neutral pose to a later shifted support pose. This caused a false failure even when the final body had advanced the commanded distance. | Corrected in this saved run: only equivalent complete-cycle milestones are compared. The earlier `selected_60mm_4s_3cycles` failure remains unchanged. |
| A whole-run maximum clearance per leg could hide a failed swing in a later cycle. | Corrected: the report now contains a clearance, unloading and touchdown audit for each of the 12 scheduled swings. |
| Earlier completion counts advanced purely with elapsed phase time, and touchdown was not part of the pass criteria. | Corrected: support gating is enabled and each swing has an explicit unloading/touchdown check. This still permits the transient support loss described above. |
| Recorded clearance mixed pre-step joint states with post-step base pose. | Corrected in this saved controller: recorded states and contacts are refreshed after the physics step. |
| Final recentering used nominal wall-clock completion, so a support-gate delay could skip part of the settling motion. | Corrected: the saved controller uses actual completion time and records an abort reason if progress cannot finish. There was no gate delay or abort in this run. |
| Negative support margin and transient contact loss were hidden by the aggregate pass label. | The report now records minimum margin and negative-margin fraction. The permissive 95% contact criterion itself remains, so the transient must still accompany any claim about this run. |
| Optional exact link masses/COMs were supported by the URDF model but not by the analytic COM planner. | Corrected in the revised geometry helper for future refreezing. This run has no `link_mass_properties` override, so its original coarse COM helper remains consistent with its parameter mass layout. |
| The shared base-pose helper omitted the local inertial quaternion after PyBullet diagonalized a full inertia tensor. | The shared helper has now been corrected to remove both the local translation and rotation. This saved run uses the older frozen helper with diagonal inertias; its local inertial quaternion is identity, so that particular bug does not affect its results. |

The inertia-frame issue was demonstrated by [verify_link_com.py](verify_link_com.py) using six original/synthetic kinematic fixtures. The revised analytic helper matches the frozen PyBullet world COM within **0.019 µm**. The older base-pose shortcut gives **22.7–23.6 mm** of COM projection error in the synthetic full-inertia fixture. Those synthetic masses and tensors are test inputs, not revised estimates for the robot. Exact results and source hashes are in [link_com_verification.json](link_com_verification.json).

## Physical interpretation

The free base moves through the existing torque-controlled joints and bounded wheel motors. The reviewed controller does not reset the base during motion, add external forces, impose artificial contact constraints or raise actuator limits. The wheel orientation compensation has the correct small-angle sign: with wheel axis `[sin(heading), −cos(heading), 0]`, the body correction is `pitch × cos(heading) − roll × sin(heading)`. Its finite-angle accuracy remains limited by the stated small-angle approximation.

The RMS calculation is separate for every actuator and includes the complete recorded run, including settling. The 0.728 Nm limit, gearbox backlash, delay, compliance, grip and servo response are unmeasured assumptions. Peak limiting and a passing RMS statistic are not a measured thermal qualification. The slow crawl also relies on ideal simulator pose and contact feedback, coarse collision shapes, and the hypothetical femur-mounted knee actuator reaction frame. It does not establish fitted brackets, cable clearance, belt retention, print strength, stairs or hardware-safe control.

For this run, retain the model pass together with its explicit support-loss caveat. A claim of a consistently supported crawl would need the lost-support episode eliminated or independently justified with a dynamic stability criterion. Later controller variants require their own evidence and are outside this review.

## Evidence

- [Saved report](../supported_60mm_4s_3cycles/report.json)
- [Saved trajectory](../supported_60mm_4s_3cycles/trajectory.json)
- [Saved controller settings](../supported_60mm_4s_3cycles/controller.json)
- [Saved controller source](../supported_60mm_4s_3cycles/supported_crawl.py)
- [Saved parameter snapshot](../supported_60mm_4s_3cycles/parameters_used.json)
- [Earlier report with the cycle-distance metric failure](../selected_60mm_4s_3cycles/report.json)

The chart uses the saved report's per-actuator RMS and per-swing audits, plus the trajectory's body positions and contact forces. Source hashes are checked before and after chart generation. Plot dependencies are isolated in `geometry_study/.plot_deps`; the simulation environment and recorded evidence are unchanged.
