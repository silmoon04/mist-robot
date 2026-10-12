# Primary evidence for body-mounted actuation

Checked 7 September 2026. The design requirement is twelve joint servos and four wheel motors entirely inside the MIST body. Whether internal motor carriers may move with the hip remains unresolved. The sources below establish parts of the transmission concept; none verifies the complete MIST layout or its packaging.

Stanford Doggo is a useful planar precedent. Its original engineering account specifies four 2DOF five-bar legs with the two upper links driven coaxially. Each leg's two motors mount on a carbon-fiber body panel and drive the nested shafts through separate 6 mm wide, 3 mm pitch GT2 belts, with 16T motor and 48T output pulleys. The builders report pulley/shaft play, a tension-bracket spacing 0.5 mm above the nominal belt calculation, and increased friction as tension rose. [Original project account, Mechanical Design](https://github.com/Nate711/StanfordDoggoProject/blob/master/README.md#mechanical-design).

Kau et al.'s paper confirms two independent 3:1 belt paths and nested inner/outer shafts in Section II.A and Figure 2. The arrangement permits the planar leg to rotate beyond the body. It does not show a physical summing differential, a third leg axis, or a driven wheel. Its force relation is `F_est = J^(-T) tau_m`, with motor torque estimated from current. This supports checking the actual linkage Jacobian rather than inferring load sharing from motor placement. [Stanford Doggo paper, arXiv:1905.04254](https://arxiv.org/pdf/1905.04254).

IEEE document 10891906 is Wang et al., *A Differential-Mechanism-Based Leg Configuration Balances the Load and Dynamic Contribution for All Actuators of the Quadruped Robot*, IEEE Transactions on Robotics 41, 2014–2030 (2025), DOI 10.1109/TRO.2025.3543262. [Publisher record](https://ieeexplore.ieee.org/document/10891906/).

The accessible published paper shows a physical bevel differential at the crotch, with all three leg actuators fixed to the torso. Equations (1–2) give `theta_0 = (phi_a0 - phi_a1)/2` and `theta_1 = (phi_a0 + phi_a1)/2`. These concern abduction–adduction and thigh rotation. Knee transmission uses either nested bevel gears plus a shank pulley, or a perpendicular actuator and universal joint. Equations (6–9) give `theta = R_a theta_a`, `J_a = J R_a`, and `tau_aF = -J_a^T F_f`. The paper reports a 50 kg lift, a 10 cm jump, and 1100 N maximum reaction force in single-leg tests. Adjacent prose reverses the sagittal/transverse description; check Figure 4 and the full ratio-dependent mapping before reuse. This is a stronger precedent for three body-fixed joint actuators, but provides no wheel-drive route. [Published full text, Sections II–IV](https://www.researchgate.net/publication/389126702_A_Differential-Mechanism-Based_Leg_Configuration_Balances_the_Load_and_Dynamic_Contribution_for_All_Actuators_of_the_Quadruped_Robot).

For the proposed pitch differential, MathWorks' own gear-model documentation supplies the ideal physical constraint `(omega_S1 - omega_C)/(omega_S2 - omega_C) = -g_SP2/g_SP1`. Equal side-gear ratios therefore give `omega_C = (omega_S1 + omega_S2)/2`. This is a gear-model reference, not an experimentally validated robot design. It also distinguishes ideal constraints from gear inertia and losses. [MathWorks Differential, Ideal Fundamental Constraints](https://www.mathworks.com/help/sdl/ref/differential.html).

The following is our derivation, not a claim about either robot. Let equal differential side gears have angles `alpha` and `beta`, and connect the carrier rigidly to the femur. With consistent signs and commissioned offsets, `h = (alpha + beta)/2`. If side gear `alpha` also drives the tibia through an open, equal-pulley belt whose centers are carried by the femur, no slip gives `(t - h) = (alpha - h)`, hence absolute tibia angle `t = alpha`. The knee angle relative to the femur is then `k = t - h = (alpha - beta)/2`.

Ideal virtual work gives input shaft efforts `tau_alpha = (tau_h + tau_k)/2` and `tau_beta = (tau_h - tau_k)/2`. Any actuator reductions belong in the full mapping. Losses, inertia, belt compliance and carrier reaction loads must be added separately. The mapping requires the physical differential and specified belt path; a software sum/difference command does not create it. The bevel differential in Wang et al. mixes different physical axes, so its measured results cannot be assigned to this pitch-pair proposal.

The next design evidence must establish the yaw transmission, the continuous wheel-power path, full joint travel, motor envelopes, supported shaft connections, and loads for the actual MIST geometry. These sources do not establish that sixteen actuators and the required transmissions fit inside the present body.

## Appendix: Wang et al. transmission matrix

Type I is readable in Appendix equations (A3–A11), pages 2028–2029. With rows ordered `[ab-ad, thigh, knee]` and columns `[A0, A1, A2]`, its ratio-dependent matrix is:

```text
theta_dot = R_a theta_a_dot

R_a = [ 1/2,                         -1/(2 r_B1),                            0;
        1/(2 r_G1),                  1/(2 r_B1 r_G1),                       0;
        (1/r_G2 - 1/r_G1)/(2 r_B2), -(1/r_G2 + 1/r_G1)/(2 r_B1 r_B2),       1/(r_B2 r_G2) ]
```

The knee path provides an independent transcription check. For actuator velocities `a0, a1, a2`, equations (A3–A9) give:

```text
P0 = (a0 - a1/r_B1)/2
R1 = (a0 + a1/r_B1)/(2 r_G1)
R2 = (a2 + P0)/r_G2
theta_0_dot = P0
theta_1_dot = R1
theta_2_dot = (R2 - R1)/r_B2
```

For the paper's `[r_B1,r_B2,r_G1,r_G2]=[1,1,2,2]`:

```text
R_a = [ 1/2, -1/2, 0;
        1/4,  1/4, 0;
        0,   -1/2, 1/2 ]
```

Types II–IV are printed in Figure 5, page 2018 (PDF page 5), but their matrices were not reliably accessible in this extraction. They are not transcribed or inferred here. Figure 4 identifies carrier revolution with ab-ad and output rotation with thigh motion; adjacent prose reverses those descriptions. Use the appendix's full ratios and axis definitions rather than reassigning the basic half-sum equations to two pitch joints. [Published PDF, Figure 5 and Appendix](https://www.researchgate.net/publication/389126702_A_Differential-Mechanism-Based_Leg_Configuration_Balances_the_Load_and_Dynamic_Contribution_for_All_Actuators_of_the_Quadruped_Robot/fulltext/6a567dc97fcc0765f3eda565/A-Differential-Mechanism-Based-Leg-Configuration-Balances-the-Load-and-Dynamic-Contribution-for-All-Actuators-of-the-Quadruped-Robot.pdf).
