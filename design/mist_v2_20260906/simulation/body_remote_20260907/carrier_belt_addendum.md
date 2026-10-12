# Hip-carrier differential with a side-shaft knee belt

Independent mechanism and virtual-work check, 7 September 2026. This is an ideal planar mechanism analysis. It does not establish packaging, losses, manufacturing tolerances, or the upstream route from fixed torso motors through yaw or roll.

The proposed mechanism is kinematically realizable in principle. A two-input equal-bevel differential can use its carrier as the femur, while one side shaft also drives the knee through an equal-pulley open belt. The extra branch changes the total input-shaft torques without violating the differential's equal-side-gear torque relation.

## Coordinates and actual mechanical connections

All following angles use consistent positive directions about parallel pitch axes. Constant assembly offsets are omitted:

- \(\alpha,\beta\): differential side-shaft angles relative to the planar hip base.
- \(h\): femur/carrier angle relative to that base.
- \(t\): absolute tibia angle relative to the same base.
- \(k=t-h\): knee angle relative to the femur.
- \(\chi\): absolute wheel rotation about its axle, with parallel-axis transport through the ideal wheel transmission.
- \(w=\chi-t\): wheel rotation relative to the tibia.

For equal side gears, the carrier relation is

\[
h=\frac{\alpha+\beta}{2}.
\]

This follows from the equal-ratio carrier-relative bevel constraint \((\dot\alpha-\dot h)=-(\dot\beta-\dot h)\). [Official MathWorks differential equations and shaft definitions](https://www.mathworks.com/help/sdl/ref/differential.html). Shaft directions and gear reversals must match this sign convention; it must not be substituted blindly for the sign convention in Wang et al.'s Type I matrix.

The hip belt pulley must be rigidly attached to shaft \(\alpha\), with bearings allowing rotation relative to the femur. Its equal-radius knee pulley must be rigidly attached to the tibia. Their centre spacing is fixed by the femur. In the femur frame, an uncrossed, no-slip belt gives

\[
t-h=\alpha-h\quad\Rightarrow\quad t=\alpha.
\]

Together these impose

\[
h=\frac{\alpha+\beta}{2},\qquad
k=\frac{\alpha-\beta}{2},\qquad
\alpha=h+k,\quad\beta=h-k.
\]

The knee branch therefore uses the side-shaft angle directly. It does not require taking rotation off the transverse planet shaft. This distinction makes the proposed arrangement different from an ordinary differential wrist and from the supplied paper's roll/hip differential.

## Torque and power check without the wheel

Let \(\tau_h,\tau_k\) be the generalized efforts the transmission must deliver to the joint coordinates. They are not the opposite-signed external resisting torques. Let motor angles be

\[
s_A=g_A\alpha,\qquad s_B=g_B\beta,
\]

where positive \(g_A,g_B\) mean motor radians per side-shaft radian. A gear reversal must either be included as a signed ratio or handled by an explicit coordinate reversal.

Lossless virtual work gives

\[
\begin{aligned}
\tau_h\,dh+\tau_k\,dk
&=\frac{\tau_h+\tau_k}{2}\,d\alpha
+\frac{\tau_h-\tau_k}{2}\,d\beta,\\
\tau_A&=\frac{\tau_h+\tau_k}{2g_A},\qquad
\tau_B=\frac{\tau_h-\tau_k}{2g_B}.
\end{aligned}
\]

Thus the requested sum/difference mapping follows from a physical pair of constraints. No software torque cancellation is being substituted for a mechanical load path.

## Adding a separate continuous wheel transmission

Assume a separate continuous shaft/belt channel actually realizes

\[
\chi=h+k+w=\alpha+w,\qquad s_W=g_W\chi.
\]

The complete motor-angle mapping is

\[
s=Aq,\quad q=[h,k,w]^T,\qquad
A=\begin{bmatrix}
g_A&g_A&0\\
g_B&-g_B&0\\
g_W&g_W&g_W
\end{bmatrix}.
\]

The effort relation is \(\tau_q=A^T\tau_s\). Solving it gives exactly the proposed result:

\[
\boxed{\tau_A=\frac{\tau_h+\tau_k-2\tau_w}{2g_A}},\qquad
\boxed{\tau_B=\frac{\tau_h-\tau_k}{2g_B}},\qquad
\boxed{\tau_W=\frac{\tau_w}{g_W}}.
\]

The negative wheel term in \(\tau_A\) is a reaction torque, not a loss of energy. Wheel-only rotation need not rotate motors A and B, but those motors can still need holding torque. The model must include ground-contact forces in \(\tau_h\) and \(\tau_k\); wheel torque alone does not describe the entire loaded leg.

The wheel relation is conditional on the physical route. A gear reversal, unequal pulleys, or a moving support that changes the wheel channel changes its row of \(A\). The wheel channel must remain continuously rotatable rather than depend on a finite-wrap cable sector.

## Loads inside the mechanism

Rewrite the required work in absolute coordinates:

\[
\tau_h\,dh+\tau_k\,d(t-h)+\tau_w\,d(\chi-t)
=(\tau_h-\tau_k)\,dh+(\tau_k-\tau_w)\,dt+\tau_w\,d\chi.
\]

This exposes three separate load paths:

| Component or branch | Ideal signed transmitted effort |
|---|---:|
| Differential carrier/femur | \(H=\tau_h-\tau_k\) |
| Each differential side-gear mesh, summed over its planet contacts | \(D=H/2\) |
| Side-shaft-to-tibia belt branch | \(K=\tau_k-\tau_w\) |
| Total input at shaft \(\alpha\) | \(Q_\alpha=D+K\) |
| Total input at shaft \(\beta\) | \(Q_\beta=D\) |
| Continuous wheel branch | \(Q_\chi=\tau_w\) |

The gear mesh torques on the two side shafts remain equal in the ideal quasistatic differential. Shaft \(\alpha\) has an extra belt load, so its motor supplies the mesh effort plus the belt effort. The belt applies the opposite reaction to that shaft.

An equal open belt contributes zero net generalized moment to \(h\), because its ideal constraint \(t-\alpha=0\) is independent of \(h\). This does **not** mean its bearings or the femur are unloaded. Belt pretension, the tight/slack tension difference, pulley offsets and bearing reactions remain real structural loads.

For pulley pitch radius \(r\), the ideal belt tension difference is \(\Delta F=K/r\). If the mean span tension is \(F_0\), the simplified two-span model gives \(F_{tight/slack}=F_0\pm K/(2r)\). Positive slack-side tension alone requires \(F_0>|K|/(2r)\); that is not an adequate design pretension specification. Dynamic load, tooth engagement, manufacturer's limits and support deflection require separate checks. Bearing force depends on the span directions and their sum, not just \(\Delta F\).

## Cancellation does not unload every part

The following use unit motor ratios and a positive reference effort \(T\):

| Requested joint efforts \((\tau_h,\tau_k,\tau_w)\) | Motor efforts \((\tau_A,\tau_B,\tau_W)\) | Internal consequence |
|---|---|---|
| \((T,0,0)\) | \((T/2,T/2,0)\) | Carrier takes \(T\); knee branch takes zero torque |
| \((0,T,0)\) | \((T/2,-T/2,0)\) | Carrier takes \(-T\); knee belt takes \(T\) |
| \((T,T,0)\) | \((T,0,0)\) | Differential meshes carry zero ideal torque; belt carries \(T\) |
| \((T,-T,0)\) | \((0,T,0)\) | Shaft A has cancelling mesh and belt efforts of magnitude \(T\); carrier takes \(2T\) |
| \((0,0,T)\) | \((-T,0,T)\) | Wheel and knee branches carry opposing efforts; A supplies holding reaction |

The fourth case is the important structural trap. A low or zero servo current does not prove low torque throughout its shaft. Sections between the gear, pulley and motor attachment can carry large opposing branch torques. The carrier, planet pins, tooth contacts and bearing stack must be sized from their own loads.

## Remaining physical requirements

1. The femur must connect to the differential carrier. Both side shafts need independent rotation and positive torque connections. Attaching the hip belt pulley to the carrier instead of \(\alpha\) destroys the intended mapping.
2. Structural bearings must carry foot forces and bevel thrust/radial loads. Servo horns alone do not establish a suitable structural support.
3. Check the complete signed motor speed/torque envelope. Reductions increase motor travel and reflected inertia. Motor internal gearing, external bevel backlash, belt compliance and friction remain additional dynamics.
4. The derivation currently fixes the motor stators to the planar hip base. If that base moves with yaw or roll, it fails the strict torso-fixed requirement. A body-to-first-axis feedthrough must be added, with its coupling terms and first-axis reaction torques derived from the actual shafts and carriers.
5. The fourth wheel channel requires its own pass-through bearings, continuous drive components and clearance. Its shaft speed may be high while the leg joints remain nearly stationary.

## Verification performed

A second agent independently derived the same virtual-work and internal-load relations. A deterministic 200-case arithmetic check used mixed signed efforts, velocities and unequal positive ratios. Maximum power residual was \(3.56\times10^{-15}\) W; maximum reconstructed joint-effort residual was \(1.34\times10^{-15}\) Nm. These are numerical algebra checks, not a physics simulation, efficiency measurement, or hardware test.
