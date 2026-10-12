# Body-fixed remote actuation: primary sources

Research date: 7 September 2026. Scope: every motor housing remains rigidly attached to the torso, including a separate continuous wheel motor. Passive shafts, bearings, pulleys and carriers may move with the leg. This note supplies mechanism evidence and coordinate checks, not a CAD release or a validated MIST performance claim.

## The supplied IEEE paper is directly relevant

Verified publication: Zeyu Wang, Wenchuan Jia, Yi Sun, Tianxu Bao, Zihan Ding and Qi Chen, *A Differential-Mechanism-Based Leg Configuration Balances the Load and Dynamic Contribution for All Actuators of the Quadruped Robot*, IEEE Transactions on Robotics 41, 2014–2030 (2025), DOI 10.1109/TRO.2025.3543262, published 18 February 2025. [IEEE record](https://ieeexplore.ieee.org/document/10891906/), [public primary paper](https://www.researchgate.net/publication/389126702_A_Differential-Mechanism-Based_Leg_Configuration_Balances_the_Load_and_Dynamic_Contribution_for_All_Actuators_of_the_Quadruped_Robot).

Section II-A4 fixes all three actuators to the body. Figures 23–24 use nested bevel pairs across the abduction/adduction axis: belt B1 offsets the outer input; inner output G2 drives the shank through B2. The foot has a brakeable passive caster; continuous powered-wheel transmission is not established. Equations (6)–(9) give:

\[
\theta=R_a\theta_a,\quad J_a=JR_a,\quad
\dot p_f=J_a\dot\theta_a,\quad \tau_{aF}=-J_a^T F_f.
\]

Here \(\theta=[\theta_0,\theta_1,\theta_2]^T\) means abduction/adduction, hip and knee; \(\theta_a\) contains actuator angles. \(F_f\) is ground reaction on the foot. Appendix (A11), Type I:

\[
R_a=\begin{bmatrix}
\tfrac12&-\tfrac1{2r_{B1}}&0\\
\tfrac1{2r_{G1}}&\tfrac1{2r_{B1}r_{G1}}&0\\
\tfrac1{2r_{B2}}(\tfrac1{r_{G2}}-\tfrac1{r_{G1}})&
-\tfrac1{2r_{B1}r_{B2}}(\tfrac1{r_{G2}}+\tfrac1{r_{G1}})&
\tfrac1{r_{B2}r_{G2}}
\end{bmatrix}.
\]

The full text and equations were readable. Direct IEEE opening returned a JavaScript challenge; direct public PDF downloads did not resolve. This transcription was checked algebraically against (A3)–(A9), without a visual PDF check. It is not a guessed matrix from the abstract.

## Consequences of that matrix for MIST

These are algebraic deductions from the matrix above, not new measured results from the paper. With all four transmission ratios equal to one,

\[
\begin{bmatrix}q_0\\h\\k\end{bmatrix}=
\begin{bmatrix}.5&-.5&0\\.5&.5&0\\0&-1&1\end{bmatrix}
\begin{bmatrix}a_0\\a_1\\a_2\end{bmatrix},\qquad
\begin{bmatrix}a_0\\a_1\\a_2\end{bmatrix}=
\begin{bmatrix}q_0+h\\h-q_0\\k+h-q_0\end{bmatrix}.
\]

For generalized joint loads \(t=[t_0,t_h,t_k]^T\), with consistent power signs and ideal lossless transmission,

\[
t_a=R_a^Tt=
\begin{bmatrix}
(t_0+t_h)/2\\(-t_0+t_h)/2-t_k\\t_k
\end{bmatrix}.
\]

Thus Type I is a physical differential between the first hip axis and hip pitch, followed by a mechanically coupled knee route. It does not give two independent sums of available motor torque at hip and knee. The suitability of its load distribution must be checked against the signed gait loads and actuator speed limits.

Replacing the first abduction/adduction axis with yaw requires a new spatial kinematic model and shaft-routing check. Merely renaming that coordinate would leave an incorrect foot Jacobian. The published topology is a credible starting point for an all-body mechanism; its dimensions, motor ratings and passive foot do not validate a scaled printed MIST leg.

## A physical hip/knee sum-and-difference transmission exists

Nobili, Salsedo and Filippeschi present two transmission branches using bevel gears and differently routed tendon pulleys, with their driven pulleys attached to the shank. Their equations (1)–(2) are:

\[
\dot q=\frac{1}{2t_r}
\begin{bmatrix}1&1\\1&-1\end{bmatrix}\dot\theta,
\qquad
C=t_r\begin{bmatrix}1&1\\1&-1\end{bmatrix}\tau.
\]

Here \(q=[q_H,q_K]^T\) contains their hip/knee flexion angles, \(\theta\) motor angles, \(C\) joint torques, \(\tau\) motor torques and \(t_r=15.125\). The two motor housings sit on the first link of a remote-centre mechanism near the trunk, so this implementation does **not** satisfy strict torso-fixed housings. Its friction model distinguishes branch motion relative to motor-support and thigh-support frames. [Primary preprint, sections II-C and III](https://arxiv.org/html/2606.15997v1).

A useful ideal deduction is \(\theta_1=t_r(q_H+q_K)\), \(\theta_2=t_r(q_H-q_K)\). Accordingly, \(\tau_1=(C_H+C_K)/(2t_r)\) and \(\tau_2=(C_H-C_K)/(2t_r)\). A lightly loaded joint can leave capacity for the other; simultaneous demands still share a finite motor envelope. Implementing these equations on an ordinary independent-joint leg would not change its physical torque paths.

## The carrier is part of the mechanism

Gonzalez and Asada's XRL prototype uses two chain-driven input shafts and spiral miter gears. Opposed inputs spin a transverse output shaft; same-direction inputs rotate its bearing block about the common input axis. Its bearing structure carries both gear and cantilever loads. This is a concrete two-input, two-axis differential, but XRL places modules at several joints and does not demonstrate every motor fixed to the torso. [Primary paper, section IV-A and figure 11](https://arxiv.org/pdf/2007.00872).

MathWorks states the bevel constraint in carrier-relative speeds:

\[
\frac{\omega_{S1}-\omega_C}{\omega_{S2}-\omega_C}
=-\frac{g_{SP2}}{g_{SP1}}.
\]

For equal ratios this gives \(\omega_C=(\omega_{S1}+\omega_{S2})/2\). The carrier motion and differential motion are separate freedoms; the rigid-gear model omits losses unless configured. [Official differential model and coordinate definitions](https://www.mathworks.com/help/sdl/ref/differential.html).

Engineering implication: an ordinary differential's transverse output is referenced to its moving carrier. If that carrier becomes the yaw or roll member, the shaft axis moves with it. A second remote joint needs a physical path from that shaft to its link. It cannot simultaneously be treated as a second independently supported, body-fixed output without additional gearing or a second differential.

## Crossing yaw or roll, and driving the wheel continuously

The following are candidate routes, not claims of completed design:

| Route | What it can address | Work still required for this robot |
|---|---|---|
| Nested shafts and bevel pairs at the first axis | Separate rotation channels across a turning carrier, following the supplied paper's general architecture | Bearing stack, thrust loads, shaft wall thickness, keys/clamps, gear backlash, full-angle clearance and the actual signed coupling matrix |
| Guided antagonistic tendons across the first axis | Remote finite-angle joint actuation with light moving transmission parts | Cable-length change with yaw/roll, guide geometry, pretension, compliance, friction, retention and bend fatigue |
| Double Cardan or suitable CV shaft | Continuous rotary transmission across changing shaft alignment | Actual angle envelope, phasing/centering, bending loads, backlash and supplier torque/RPM rating |
| Endless belts or gears through both pitch hinges | A continuous powered-wheel channel | Pass-through pulleys coaxial with hinge axes, moving-frame speed terms, tooth engagement, tensioners, total losses and clear assembly access |

SDP/SI documents that a single Cardan joint produces angular-velocity variation twice per revolution. Correctly arranged paired joints can cancel output variation, but their intermediate shaft still has fluctuating speed. Backlash and operating angle need attention. [Manufacturer universal-joint engineering guide](https://sdp-si.com/Catalogs/D757-Couplings-Universal-Joints3.php). Belden documents the required arrangement of multiple joints and equal-angle configurations for constant-velocity operation. [Manufacturer installation guidance](https://www.beldenuniversal.com/resources/technical-information/connecting-multiple-u-joints).

For the wheel, use a separate fourth body-mounted motor and an independently bearing-supported continuous transmission channel. An anchored cable sector that runs out of wrap cannot be assumed to rotate forever. An endless belt or shaft channel avoids that particular travel limit, but still transmits reaction loads into its supporting links. The wheel's angle relative to the shank differs from its absolute angle; hip, knee and first-axis motion can therefore require wheel-motor compensation. Include the wheel column and its reaction torques in the complete transmission model.

## Choice supported by this evidence

Start the next all-body concept with the supplied paper's nested bevel/shaft topology and explicitly model its real carrier references. Compare its signed load distribution against the separately demonstrated hip/knee tendon differential before selecting ratios. Keep the independent wheel channel in the packaging sketch from the beginning. No source found in this bounded search establishes the complete four-motor body-fixed MIST transmission, printable construction, or its stair performance. Those remain design and validation work.
