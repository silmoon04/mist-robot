# MSI development support diagnosis

Status: development diagnosis complete; proposed support change unimplemented and unrun. No new simulation or training is scheduled by this note. Frozen source, checkpoints, previous experimental files and acceptance thresholds remain unchanged. Untouched final-policy outcomes were not used.

## Development evidence

The source is [dev_stride_factorial960_01.json](../runs/msi_20261012/dev_stride_factorial960_01.json): 48 completed, paired 19.2-second flat-terrain development cases, six commands, payloads 0/.155 kg, zero policy residuals. The experiment changes body shift .005/.003 m and translational geometric stride gain 1/1.15; requested and scored commands remain original. Pure-yaw gain pairs are geometric negative controls.

| Shift / translation gain | Strict passes | Velocity RMSE range, m/s | Maximum tilt, rad | Maximum saturation fraction |
|---|---:|---:|---:|---:|
| .005 / 1.00 | 4/12 | .01206-.01523 | .04325 | .006888 |
| .003 / 1.00 | 0/12 | .00941-.02693 | .06334 | .004401 |
| .005 / 1.15 | 6/12 | .01206-.02080 | .05035 | .004779 |
| .003 / 1.15 | 2/12 | .00954-.02943 | .06566 | .005343 |

Five-millimetre shift with gain 1.15 passes both forward and all four yaw cases. Backward and lateral cases fail velocity despite their improved paths. Three-millimetre shift worsens support and moving-case tracking, even though it reduces the imposed shift motion. This is evidence against another uniform shift reduction as the next step. It does not qualify a walking controller.

For payload .155 kg and gain 1.15, the measured fraction of loaded contact samples in the broad main-stance bin, phase 0-.73, is:

| Command | Shift | FL | FR | RL | RR | Velocity RMSE, m/s |
|---|---:|---:|---:|---:|---:|---:|
| Forward | .005 | .989 | .978 | .988 | .995 | .01330 |
| Backward | .005 | .934 | .925 | .795 | .795 | .01905 |
| Backward | .003 | .867 | .876 | .795 | .794 | .02943 |
| Left | .005 | .988 | .936 | .796 | .992 | .01734 |
| Right | .005 | .942 | .975 | .988 | .796 | .01741 |

The loaded-contact definition is the probe's normal-force threshold above .1 N. These are aggregate measured phase bins, not a frame-by-frame reconstruction. The factorial receipt has no saved trajectories; exact timing of each unexpected stance-contact loss cannot be recovered from this receipt alone.

## Planned support moment check

The original [gait.py](../gait.py) uses FL, RR, FR, RL swing order, .8 stance duty, unload weights from phase .76-.82 and reload weights from .97-1. Body shift begins at .73, peaks at .865 and falls back to zero at 1. Its envelope is `sin(pi*(phase-.73)/.27)^2`. At phase .8 only about .528 of the shift is established; at .97 only about .117 remains. The static support solve assumes horizontal COM at body origin. It clips negative foot forces to zero and renormalizes total weight, explicitly losing moment balance when the planned centre lies outside the triangle.

A separate pure-kinematic check used the existing `TranslationGainClearanceCrawl`, zero attitude, gain 1.15 and 321 equally spaced samples over 6.4-9.6 seconds, excluding the endpoint. During each planned swing phase .82-.97, omit that leg and solve normalized load fractions for the other three feet:

```python
points = body_frame_geometric_feet(q)
A = np.vstack([np.ones(4), points[:, 0], points[:, 1]])
fractions = np.linalg.solve(A[:, stance_indices], [1., 0., 0.])
```

This audits the existing centred-COM model; it is not measured support force or a model of the true moving COM. The pose includes the experimental clearance trajectory and geometric gain. No physics simulation, sensor feedback or simulator truth was supplied to the actor.

At shift .005, forward has no negative planned fractions across those swing samples. Backward has negative planned fractions in 36.8% of samples; left and right each have them in 19.7%. During late swing .94-.97, every backward sample requires a negative force; approximately half the lateral samples do. Worst normalized force fractions are -.02335 backward, -.02428 left and -.02374 right. With shift .003, backward already has negative fractions in two-thirds of samples at .86-.90 and all samples at .90-.97.

As a static counterfactual only, holding the full .005 m shift away from the active swing leg through .82-.97 reduces negative-fraction incidence to 3.1% backward and 3.6% left/right. Worst fractions become -.00120, -.00214 and -.00192 respectively. This counterfactual has no implemented transition or dynamics. It shows that abandoning support displacement before touchdown explains much of the planned moment deficit; it does not prove that a plateau gait would track well.

## One next causal recommendation

Replace the body-shift reference with a planned support-feasibility transfer, while retaining clearance timing, gain 1.15, cycle 3.2 seconds, lift, leg order, sensor contract and motor settings for the first comparison. Derive the required shift from the commanded geometric feet and planned support triangle, establish it before releasing the swing leg, and retain sufficient displacement until planned touchdown. Use planned geometry only. Do not substitute measured contacts or world velocity into the controller.

The one changed behavior is the support-transfer reference. The purpose is to eliminate the planned negative-force/moment deficit rather than increase a uniform shift amplitude. A smooth phase trajectory and the same geometry for the support-load estimate are required. Audit its position and velocity continuity, workspace, planned load feasibility and command-slew demands before running it. A naive late plateau release could create a large velocity pulse because only .03 of the cycle remains; that would merely exchange support loss for velocity RMSE.

First compare the existing .005/gain1.15 reference with this one support-reference change on backward, payload .155, using a fresh receipt with paired development seed, 480 steps and saved traces. Predictions are fewer unexpected main-stance contact losses, lower backward velocity ripple/RMSE, and near-nonnegative planned support fractions without an increased torque/slew excursion. Confirm any signal at 960 steps across all six commands and both payloads before a broader terrain or randomization suite. Gravity moment about the true whole-robot COM remains a separate later hypothesis; changing it in the same first pair would confound the result.

## Reusable lesson and handoff

Finding `MSI-SUPPORT-001`: a lower shift-motion RMSE can hide a support-feasibility failure. Evidence is the paired factorial above and the negative planned three-foot load fractions. The owning behavior is the body-shift/support solve in `gait.py`; that frozen file was not changed. The scoped improvement applied here is this durable causal handoff: check planned force feasibility and actual scheduled-support contact before another gain/shift sweep. The static check was evaluated against the exact development controller files recorded in the factorial receipt, including `experimental_stride_gain.py` hash `afff4bfd2ccaac61ad08542955d4d142102dab8ab8014c9b022e18a9b1f1a744` and factorial wrapper hash `aebf71749d5cbf02da6706da396fc7e071daaa585c7d5a1b3193cc1faf5de4a3`.

Remaining limits: the proposed controller change is unimplemented; the static counterfactual is not runtime evidence; actual manufactured mass/COM, motor timing, support compliance and sensor calibration remain unmeasured. Continue from these development records, preserve the frozen receipt contract, and keep hardware walking gated.
