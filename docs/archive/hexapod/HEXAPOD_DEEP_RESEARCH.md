The definitive reconciled report is written to:

`<LOCAL_HOME>\AppData\Local\Temp\claude\C--Users-hssil-Downloads-03-Programming-Projects-spider-robot\f313858f-1d31-474c-bd62-1acfb3c8ab5e\scratchpad\hexapod_definitive_report.md`

Here it is verbatim:

# Hexapod Build — Definitive Research Report (18× Feetech STS3215, 6×3-DOF, Regulated 7.4V Rail)

*For: a cost-conscious London beginner building an 18× Feetech STS3215 (7.4V variant, **19.5 kg-cm**, serial-bus TTL, 360° magnetic encoder) 3D-printed hexapod (6 legs × 3 DOF), target ~2.3–2.7 kg. Power plan: 3S LiPo → regulated flat 7.4V rail via 2× 20A SBEC as **two isolated banks (common ground only)**, per-leg power injection.*

> **This is the reconciled edition.** Numbers the first pass got wrong (stall current, runtime, torque margin, SBEC paralleling) and tool claims that were too rosy (Fritzing, feetech-sdk, pyhexapod, mithi-sim age) have been corrected against Waveshare's official spec table and the GPT-5.5 adversarial review. Corrections are flagged **[FIXED]**.

---

## 1) Comparable builds — what to copy, what to avoid

**Closest match:** [PCrnjak/3D-printed-Hexapod](https://github.com/PCrnjak/3D-printed-Hexapod) — an 18-DOF (6×3) 3D-printed serial-bus hexapod whose control code is a **port of the classic Phoenix/Phantom (KurtE) IK engine** ([KurtE/Phantom_Phoenix](https://github.com/KurtE/Phantom_Phoenix)). **Copy:** reuse Phoenix/Phantom IK, don't write your own. **Watch:** no explicit power specs (a recurring documentation gap in hobby repos).

**Serial-bus split-bus precedent:** [garciamathias/OpenRoboticDog](https://github.com/garciamathias/OpenRoboticDog) — 12× STS3215 on **two serial-bus boards, 6 motors per bus**. This supports splitting the bus; it does **not** endorse paralleling regulator outputs (see §5 [FIXED]). Electrically under-documented.

**Canonical STS3215 reference:** LeRobot [SO-100](https://huggingface.co/docs/lerobot/en/so100)/[SO-101](https://huggingface.co/docs/lerobot/en/so101) (6× STS3215, 7.4V). Two takeaways:
- **Warning:** feeding a **12V supply into 7.4V motors burns them** — voltage discipline is non-negotiable. The 7.4V variant is rated **4.0–7.4V max**, so also guard against regulator *overshoot* [FIXED].
- **Trap NOT to copy:** LeRobot runs the 7.4V motors from a **5V/4A** supply. Fine for a low-torque arm; **wrong for a load-bearing walker**. Keep your regulated ~7.4V rail.

**Classic PWM archetypes (your code ancestry):**
- **Lynxmotion Phoenix** — 18× HS-645MG, single 6V NiMH pack + SSC-32 ([wiki](https://wiki.lynxmotion.com/info/wiki/lynxmotion/view/ses-v1/ses-v1-robots/ses-v1-3-4-dof-hexapods/phoenix/)). Baseline "beefy pack + dedicated sequencer."
- **CoretechR [ZeroBug](https://github.com/CoretechR/ZeroBug)** — STM32 IK@50Hz + PCA9685, Pi Zero UI. **Documented failure:** Pi *resets during fast moves* on low battery. Fix: **separate logic rail + 1600µF bulk cap** ([Hackaday.io](https://hackaday.io/project/180534-zerobug-diy-hexapod-robot)).
- **[Vorpal Hexapod](https://vorpalrobotics.com/wiki/index.php/Vorpal_The_Hexapod_Battery_Recommendations)** — protected 18650s **mis-trip on servo surge and drop the robot**. Lesson: **low internal resistance / surge tolerance beats capacity** — LiPo over AA/NiMH.

**What worked (reuse):** split servo rail into banks with 20A-class DC-DC; separate logic rail; **common ground mandatory**; bulk capacitance (100s–1000s µF) at each bank; Phoenix/Phantom IK; LiPo.
**What didn't:** shared servo+logic rail → brown-out resets; under-spec batteries → surge trips; wrong/over-voltage into 7.4V motors → burnout; ignoring thermal duty cycle (§3); assuming the data daisy-chain is also a power bus (it isn't).

---

## 2) The calculations — formulas + worked example for OUR robot

### 2.1 Inverse kinematics (coxa L1 / femur L2 / tibia L3)

Coxa yaw decouples the 3D problem into a 2D planar one; law of cosines solves the femur+tibia triangle (~5 trig ops/leg, trivial at 50–200 Hz on ESP32) ([raw.org](https://raw.org/book/robotics/inverse-kinematics-of-a-3-dof-spider-robot-leg/)).

Foot target `(px, py, pz)` in the leg frame (origin at coxa axis):

```
Step 1 — Coxa (hip yaw):   theta1 = atan2(py, px)
Step 2 — Project to leg plane:
  L  = sqrt(px^2 + py^2)          # coxa-axis -> foot, horizontal
  dx = L - L1                     # femur pivot -> foot, horizontal
  dz = pz                         # vertical (neg = foot below hip)
  r  = sqrt(dx^2 + dz^2)          # femur-pivot -> foot, straight-line
  REACHABLE only if |L2 - L3| <= r <= L2 + L3
Step 3 — Tibia (knee):
  gamma  = acos( (L2^2 + L3^2 - r^2) / (2*L2*L3) )   # clamp arg to [-1,1]
  theta3 = 180deg - gamma          # offset by mechanical zero
Step 4 — Femur (thigh):
  a = atan2(dz, dx)
  b = acos( (L2^2 + r^2 - L3^2) / (2*L2*r) )         # clamp arg to [-1,1]
  theta2 = a + b (elbow-up)  OR  a - b (elbow-down)  # pick one, keep fixed
```

**Two clamps, two different purposes [FIXED]:**
1. Clamp every `acos` argument to `[-1,1]` (float rounding → NaN otherwise). *Safety only.*
2. If `r` falls **outside** `[|L2−L3|, L2+L3]`, do **not** silently clamp and pretend — **return a reach-limit flag** and let the gait planner cap the stride. Silently clamping makes IK report a fake foot position and the gait will command the leg somewhere it can't go.

**Worked IK** (raw.org L1=30,L2=100,L3=150; target 50,100,−80 mm): `L=111.8`, `theta1=63.4°`, `dx=81.8`, `r=114.5` (in [50,250] ✓). Knee `gamma=acos(0.646)=49.7°`→tibia≈130.3°. Femur `a=atan2(−80,81.8)=−44.4°`, `b=acos(0.0267)=88.5°`, `theta2=+44.1°` (elbow-up). *(Arithmetic confirmed by adversary.)*
For OUR legs (L1=35,L2=80,L3=100 — §6) the annulus is `20 mm ≤ r ≤ 180 mm`; same four formulas, new constants.

### 2.2 Gait generation

**Duty factor** `beta = ground time / stride period`; higher = more legs down = slower, more stable ([hexyrobot](https://hexyrobot.wordpress.com/2015/11/20/common-walking-gaits-for-hexapods/)):

| Gait | beta | Swinging | Character |
|------|------|----------|-----------|
| Tripod | 1/2 | 3 | Fastest stable; sets {L1,R2,L3}/{R1,L2,R3} at 180° |
| Ripple | 2/3 | 2 | Medium |
| **Wave** | **5/6** | **1** | **Slowest, most stable — best first walk for a heavy/beginner robot** |

Each leg: **stance** (foot down, moves back rel. to body, pushes forward) for fraction `beta` of period `T`, then **swing** (lifted, returns front) for `1−beta`. Body speed `v = stride_length / T`.

**Swing trajectory — cubic Bézier** (robust beginner choice) ([FootTrajectoryPlanner](https://github.com/pat92fr/FootTrajectoryPlanner)): raise the two middle control points to set step height; foot lifts, arcs forward, sets down with near-zero vertical velocity (less impact/slip). **Stance** = straight line back at constant speed so all grounded feet track body velocity (no scrubbing).
**Control loop @ ~50 Hz:** per leg compute foot `(x,y,z)` from stance-line or swing-Bézier → IK → send angles (via **sync/group write**, §3).

### 2.3 Worst-case joint torque vs servo stall  **[FIXED — this is the section the adversary hit hardest]**

Units trick: `torque[kg-cm] = supported_mass[kgf] × horizontal_lever_arm[cm]`. The **femur** is torque-critical (longest horizontal lever under vertical load; coxa yaw only fights friction). Correct load model:

```
T_femur[kg-cm] = vertical_load[kgf] × horizontal_offset(femur-axis→foot)[cm] × dynamic_factor
```

**Static shares (2.5 kg robot):** tripod avg `2.5/3 = 0.83 kg/leg`; one-leg-heavy static `1.25 kg`.

**Static-only (previous pass stopped here — too optimistic):**
| Lever | T (1.25 kg) | % of 19.5 kg-cm |
|-------|-------------|-----------------|
| 9 cm | 11.25 kg-cm | 58% |
| 10 cm | 12.5 kg-cm | 64% |
| 12 cm | 15.0 kg-cm | 77% |

**Add a dynamic factor of 1.3–1.8×** (leg self-weight, distal servo/bracket mass, acceleration, foot-strike impact, foot slip, body roll — none are in the static number):
- **9 cm × 1.25 kg × 1.5 = 16.9 kg-cm → 87% of stall.** Thin, not "healthy."
- Even tripod-average 0.83 kg × 9 cm × 1.5 = **11.2 kg-cm** in a good pose.

**Reality ceiling:** stall (19.5 kg-cm) is a *peak*, not continuous; bench data ([robonine](https://robonine.com/testing-of-feetech-sts3215-servomotor-backlash-repeatability-and-torque/)) shows it runs to ~15 kg-cm but **trips overload near 20 kg-cm**. [RobotShop](https://community.robotshop.com/forum/t/servo-torque-arm-length-calculations-and-estimates-long/20721) rule: design under **~50–60% of stall (SF≥2)**. So target **continuous ≤ ~10 kg-cm**, and treat any pose that needs >12 kg-cm as out of bounds.

**Design consequence:** geometry alone doesn't set torque — **the stance does.** Keep the femur pivot nearly over the foot, legs tucked, **effective horizontal offset 8–9 cm**, and cap stride so a swing/impact spike stays inside SF≥~1.7. "80/100 mm legs" is only safe *with a defined default stance* (§6).

### 2.4 Current / power budget  **[FIXED — 45A, not 48.6A]**

Official Waveshare 7.4V ST3215: **19.5 kg-cm, 4.0–7.4V, ~150 mA no-load, 2.5A locked-rotor** ([Waveshare ST3215](https://www.waveshare.com/st3215-servo.htm)). (The **12V** variant is 30 kg-cm / 6–12.6V / **2.7A** — do not mix its numbers in.)

**Fleet math (18 servos, 7.4V):**
- **Typical walking:** ~18 × 0.3A ≈ **5.4A avg**, spiking **~10–12A** on load transitions.
- **Half-stall worst case:** 9 × 2.5A ≈ **22A**.
- **All-18-stall ceiling:** 18 × **2.5A = 45A** → `7.4V × 45A ≈ 333W` peak [FIXED — prior 48.6A used the 12V figure]. Typical walking ≈ 7.4 × 5.4 ≈ **40W**.

**2× 20A SBEC = 40A** across two banks — good vs the ~22A realistic worst case, below the 45A transient ceiling (SBECs current-limit anyway). But **40A < 45A true simultaneous stall**, so add bulk capacitance and don't rely on the average (§3).

**Runtime [FIXED — 24 min was optimistic]:** a 3S 2200mAh 25C LiPo = 55A burst (>45A) ✓. But after regulator loss, LiPo cutoff, real C-rating, and loaded-gait current, plan **~10–20 min active walking until measured**, not 24. Longer idle.

**Wire:** 14 AWG SBEC trunks / 12 AWG combined main / 16–18 AWG per-leg taps.

### 2.5 Center of mass & static stability margin (SSM)

**Support polygon** = convex hull of grounded feet; the CoM vertical projection must stay **inside** it. **SSM** = shortest perpendicular distance from that projection to the nearest polygon edge (min over edges, must be >0). Tripod's polygon is a triangle (smallest margin); wave's is a pentagon (largest). Research ([mdpi](https://www.mdpi.com/2076-3417/9/7/1508)): SSM peaks the instant a swing leg lifts, shrinks as the body advances; **optimal stride ≈ 2 × SSM**. **Keep the battery centered and low** — the single biggest beginner stability lever.

---

## 3) Problems & mistakes to pre-empt

1. **Power / brownouts (#1 killer).** Many servos moving sag the rail (a board alone drops ~0.5V; "12 servos add another volt"). Fixes: energize servos one-at-a-time on power-up; heavy-gauge wire (14 AWG main, not 22/24); per-leg injection + common ground; **1000–2200µF bulk electrolytic across the rail near the load** ([RobotShop](https://community.robotshop.com/forum/t/hexapod-power-issues/13944), [Arduino](https://forum.arduino.cc/t/buck-converter-drops-voltage-when-powering-hexapod-servos/527490)). SBEC (switcher) holds voltage better than a linear BEC.
2. **The 45A stall case is real — plan for it.** 40A budget is marginal vs 45A; it "never happens" in tripod but the regret pattern is browning out **on first stand-up** when many joints load together. Size headroom + capacitance; don't trust the average.
3. **Overheating — your real ceiling, not current.** Firmware thermal protection trips **~70°C and CUTS TORQUE** (leg goes soft, robot sags — scary but non-destructive). Standing still is a *continuous-torque hold*, and walking is the oscillating regime: bench data → static 15 kg-cm hold ≈48°C/10 min; **oscillating ±90° → 60°C@50 min, 71°C@~110 min → torque cut to ~20%**. Mitigate: a **crouch/rest pose where geometry (not motors) holds weight**, lower holding-torque limit, don't leave it standing energized, airflow, and **poll `Present_Temperature` + hardware-error register `0x2A`** (rate-limited, §"comms"). **Bench one leg's thermal duty cycle before committing all 18.**
4. **Serial-bus ID collisions (the common beginner wall).** Every STS3215 ships **ID=1 @ 1,000,000 baud**; two un-IDed servos both answer → "motor not found" (LeRobot [#1244](https://github.com/huggingface/lerobot/issues/1244), [#1414](https://github.com/huggingface/lerobot/issues/1414)). **Only reliable fix: set IDs one servo at a time BEFORE assembly** (connect one → assign 1..18 → unplug → next) via FT SCServo Debug. **Physically label each servo.**
5. **Half-duplex comms errors.** One shared TX+RX wire. Robustness: 3-retry queue ~100 ms timeout; twisted-pair data; **star grounding (single common point)**; optional 4.7kΩ pull-up on long/noisy buses. **Use sync/group writes and rate-limit telemetry** — polling 18 servos for pos/current/temp every tick eats bandwidth and exposes half-duplex timing bugs [FIXED-add].
6. **Mechanical / PLA failures.** PLA horns/couplers strip teeth, delaminate, and **creep** under constant warm load — fatal for a weight-holder. **Print structural parts in PETG/nylon, use metal servo hubs/horns, prefer dual-shear brackets or bearing support, add heat-set inserts + threadlock, and a screw-retention plan** [FIXED-add]. True 90° at assembly.
7. **Gait instability / tipping.** CoM projection must stay inside the stance polygon. Battery low & central; wide enough stance; don't lift the swing set before stance settles. **Add rubber feet** — printed feet slide and scrub and will lie to your gait tuning [FIXED-add]. Zero/flatten all joints before tuning.
8. **First-power-up mistakes.** Reversed polarity; all 18 slamming to defaults + inrush brownout; uncharged bulk caps pulling ~10× rated inrush. **Staged first power-up:** current-limited bench PSU → one leg at a time → pre-center in software before enabling torque → confirm each ID answers before commanding motion. Add an **anti-spark connector / inrush handling** for the cap bank.

---

## 4) 360° magnetic encoder vs limited-angle (270° pot) — verdict

**Net win for this build.**
- **Precision:** contactless, full 360° absolute, **4096 steps/rev ≈ 0.088°/step** vs a pot's 1–3° deadband.
- **Durability:** no wiper wear, no drift → fewer dead-spot/wear-out failures.
- **Software zeroing:** any angle set as neutral in firmware (**homing offset ±2048 = ±180°**) → **you don't need to spline the horn perfectly**; clock within ±180° and trim (exactly what LeRobot calibration does). A pot forces exact mechanical centering.
- **Reuse:** same motor switches position ↔ continuous-rotation in firmware; SO-ARM100/LeRobot standard, so reusable as wheels/arm/pan-tilt later.

**The one new consideration — the wraparound seam:** absolute position wraps `0 ↔ 4096` at 360°. If a joint's range **crosses the seam**, commanding 4090 → 5 makes it spin the long way. **Fix:** design each joint's travel to sit **within one continuous 0–4096 window** (seam outside travel), homing offset so neutral ≈ **2048**. Easy to design around; it's the only thing the encoder *adds* over a pot.

---

## 5) Wiring best-practice

**Data and power are separate concerns.** The 3-pin bus carries GND / V+ / signal. **Signal genuinely daisy-chains** (one half-duplex TTL UART, up to 253 IDs) — chaining signal leg-to-leg is correct. **Power must NOT run the full chain** at hexapod currents (stock 5264 pigtails ~a few A; FE-URT power port ~6A).

**Hybrid best practice:** daisy-chain the signal, **inject fat power at multiple points (per-leg)** so no thin pigtail carries more than 1–2 servos. Mirrors [Antdroid](https://github.com/antdroid-hexapod/antdroid-hardware) (YEP 20A SBEC).

**Two isolated banks — do NOT parallel the SBEC outputs [FIXED].** Give each 20A SBEC its **own positive trunk to its own set of legs**; tie only the **grounds** at one star point. Paralleling two positive outputs that aren't explicitly current-sharing risks one regulator back-feeding/hogging and thermal runaway. So: split banks (e.g., left 9 / right 9, or 2×9 as you like), **common ground only, separate positives.**

**Star vs chain for power:** star/tree from each SBEC to its per-leg injection points (short heavy taps). Star minimizes common impedance so one leg's stall can't sag the MCU/bus rail.

**Common ground is mandatory (#1 beginner failure).** Signal ground, both servo-power grounds, both SBEC grounds, and controller ground meet at **one bus-bar star point**; run the **signal return as a separate light wire** to that point (not through high-current joints). Otherwise ground bounce shifts the logic reference → dropouts, false reads, resets.

**Fusing & E-stop [FIXED-add]:** **branch fuse per bank/per-leg** (slow-blow ~20–25A per 20A SBEC branch) so one jammed leg blows locally. Add a **real hardware E-stop**: battery-side switch or XT **anti-spark loop** — software stop is not enough. Add a **3S LiPo low-voltage alarm/cutoff**; SBECs will keep running the robot while over-discharging the pack.

**Connectors & strain relief [FIXED-add]:** keep 3-pin 5264 (2.54mm) for **signal + 1–2 servos of power only**; battery→SBEC use **XT30/XT60**; injection taps use JST-VH or soldered/bullet joints. **Strain-relief every pigtail** — moving legs snap JST/5264 connectors long before the CAD fails.

**Bulk caps:** **470–1000µF low-ESR per servo cluster** at each injection point; keep logic/MCU on its own regulator or at least its own local cap. Direct fix for "reboots when it tries to stand."

**Wire gauge / drop:** size the trunk for the **45A case** (at 45A even 0.1V drop matters): ~14 AWG SBEC trunks, 12 AWG combined main, 16–18 AWG taps, short thick silicone runs.

**Voltage:** set the regulator to ~7.4V **measured with a meter under no-load and load** — the 7.4V variant is 7.4V *max*, so avoid overshoot; and never confuse it with the 12V ST3215.

---

## 6) Sizing / geometry recommendation for OUR 19.5 kg-cm servos

Reference real builds (coxa/femur/tibia mm): adammck Dynamixel 100/85; Lynxmotion Phoenix femur ~76; kinematic-paper 25/50/70; medium research 30/85/125; large bio-inspired 53/83/146. Guidance: **coxa short (~30–50), femur:tibia ≈ 1:1–1:1.5.**

**Recommended — a geometry AND a stance (geometry alone is not a torque design) [FIXED]:**

| Parameter | Recommended | Why |
|-----------|-------------|-----|
| Coxa L1 | **~35 mm** | Short yaw offset, low horizontal lever |
| Femur L2 | **~80 mm** | Torque-critical; keep short for margin |
| Tibia L3 | **~100 mm** | ~1:1.25 femur:tibia; enough clearance |
| Body plate | **~180 mm across**, servos 60° apart | Symmetric, proven |
| **Default standing pose** | **body height so femur-axis→foot horizontal offset ≈ 8–9 cm**; foot slightly outboard; **max stride capped so swing/impact spike stays ≤ ~12 kg-cm** | This is what actually sets torque |
| Target mass | **≤ ~2.5 kg**, battery centered & low | Keeps worst static share ~1.25 kg |

**Why short + tucked:** required torque ≈ offset × load × dynamic factor, so every extra cm is a near-linear torque tax. At 8–9 cm offset and ≤2.5 kg, femur load stays ~10–12 kg-cm static and ~15–17 kg-cm on a bad dynamic pose (SF ≈ 1.1–1.7). **Start short and tucked; lengthen/stand taller only after measured joint currents confirm margin.**

---

## 7) Tools — ranked, beginner-friendly, visual, Windows  **[FIXED — rosier claims corrected]**

### ⭐ INSTALL/OPEN FIRST — Mithi's browser hexapod simulator (no install)
**[hexapod.netlify.app](https://hexapod.netlify.app/)** ([source](https://github.com/mithi/hexapod)) — the fastest way to SEE gait + IK for exactly a 6×3-DOF hexapod, 100% in-browser: drag body pose, pick tripod/ripple, walk/turn, watch **all 18 joint angles live**. Zero setup. **Caveat: it is *kinematic*, not physics** — it will not show slipping feet, backlash, sag, or servo limits. Maths is reusable: [hexapod-kinematics-library](https://github.com/mithi/hexapod-kinematics-library).

### Clone-and-run Python sims (Windows)
1. **[mithi/hexapod-robot-simulator](https://github.com/mithi/hexapod-robot-simulator)** — Plotly Dash browser UI at `127.0.0.1:8050`; best "see IK with YOUR leg dims." **Old stack (Python 3.8.1 / Dash 1.18.1 / NumPy 1.19.5) — use a matching venv**; kinematic, not contact-sim [FIXED].
2. **[XuelongSun/HexapodRobotSimulation](https://github.com/XuelongSun/HexapodRobotSimulation)** — numpy+scipy+dash, FK/IK + pose/gait; `python ui.py`.
3. **[resibots/pyhexapod](https://github.com/resibots/pyhexapod)** — true PyBullet physics (gravity, contacts, tip-over, damaged leg). **Not beginner-clean: needs a git submodule, and `simulator.py` defaults to `gui=False` — set `gui=True` or you get no window** [FIXED]. Use it to validate STABILITY.
4. ~~chrismailer/hexapod-sim~~ — tiny, RARL-specific, not beginner-reliable; **de-ranked** [FIXED].

### Physics simulators (easiest first)
1. **PyBullet** — `pip install pybullet`, Python-native, OpenGL GUI, ready hexapod repos above. **Start here for dynamics** ([PyPI](https://pypi.org/project/pybullet/)).
2. **Webots** — free/open-source, one-click Windows installer, drag-and-drop editor, ships a "Mantis" hexapod, Python API. Best if you prefer GUI over code ([cyberbotics](https://cyberbotics.com/)).
3. **MuJoCo** — free, fast/accurate, but you hand-write MJCF XML (the modeling *is* the work); later-stage.
4. **Gazebo** — Windows-installable now but heavy/ROS-centric; skip for now.
5. **NVIDIA Isaac Sim** — RTX-class GPU + 16 GB VRAM, **Windows 10 no longer supported**; not beginner material.

### CAD
1. **[Onshape](https://www.onshape.com/en/pricing)** free — browser, real parametric assemblies; **free docs are PUBLIC / non-commercial**.
2. **[Fusion Personal](https://www.autodesk.com/products/fusion-360/personal)** — polished, great tutorials; Autodesk login, non-commercial, hobby limits.
3. **[FreeCAD](https://github.com/FreeCAD/FreeCAD)** — fully free/offline/no-account; rougher UX (1.0+ improved). Pick this for zero cloud/lock-in.

### Wiring / schematic
1. **[Fritzing](https://fritzing.org/download/)** — easiest to draw the bus daisy-chain + 2-bank split + per-leg injection + common ground. **NOT a free binary: ~€8/€25 paid download (source is free)** [FIXED].
2. **[WireViz](https://github.com/wireviz/WireViz)** — `pip install wireviz`; YAML → harness diagram; document exact gauges/connectors once the design settles. Free.
3. **[KiCad](https://www.kicad.org/download/windows/)** — overkill for pure wiring, right if you later spin a custom 45A power-distribution PCB. Free.

### Servo / IK libraries
- **[feetech-servo-sdk](https://pypi.org/project/feetech-servo-sdk/)** — official, drives STS3215, **but the PyPI build is old and marked POSIX (tested on Raspberry Pi Linux) — not a guaranteed clean Windows path; test it, or drive from the FeeTech Windows GUI / [LeRobot FeetechMotorsBus](https://huggingface.co/docs/lerobot/en/so101) instead** [FIXED]. Alt: [vassar-robotics/feetech-servo-sdk](https://github.com/vassar-robotics/feetech-servo-sdk).
- **[ikpy](https://github.com/Phylliade/ikpy)** — pure-Python IK with 3D matplotlib plotting; great to prototype and SEE one 3-DOF leg solve.
- **placo** (Rhoban) — fast C++/Python whole-body IK; later, for coordinated multi-leg IK.

*No dedicated hexapod/Feetech MCP server exists — automation = plain Python libs from your scripts; visual loop = browser sim + PyBullet GUI.*

**Software cost ≈ £0** (PyBullet, Webots, MuJoCo, FreeCAD, KiCad, WireViz, ikpy, Onshape/Fusion hobby) **except Fritzing (~€8–25)** [FIXED].

---

## 8) Cheap test gear (validate before smoke)

| Gear | Use | ~Cost |
|------|-----|-------|
| **Bench PSU CC-CV ~0–30V/0–10A** | **Essential.** Current-limit LOW first to catch wiring faults; use the real 3S LiPo + SBECs for full-load tests. | £35–60 |
| **RC inline watt-meter (60V/130A)** | Live V/A/Wh on the 7.4V rail — verify real per-leg/total draw, catch brownouts (covers 45A). | £15–25 |
| **USB serial-bus adapter (Waveshare / FE-URT-1)** | **The true STS3215 tester** — set IDs (all ship ID 1!), baud, read the 360° encoder, test torque/limits per servo *before* assembly via FeeTech **FD / FT SCServo Debug** ([setup](https://www.hackster.io/ian-hong/feetech-serial-bus-servo-sts3215-setup-guide-fd16aa)); cross-platform: [dgmz/feetech-servo-tool](https://github.com/dgmz/feetech-servo-tool). | £8–15 |
| **LiPo low-voltage alarm** | Beeps on cell sag; prevents over-discharge behind the SBECs [FIXED-add]. | £3–8 |
| Multi-channel servo tester | **PWM only — NOT serial-bus. Skip for STS3215.** | £5–10 |
| USB/clamp multimeter | Continuity + per-injection current checks; **set/verify 7.4V rail under load.** | £15–30 |

**Realistic added spend ≈ £65–110** (design/sim toolchain ~£0 apart from Fritzing).

---

## 9) Implications for OUR build

**Validated (you got right):**
- Power topology (3S → regulated flat 7.4V, **2× 20A SBEC as two banks**, per-leg injection, common ground) is textbook-correct — **provided you do NOT parallel the positive outputs** [FIXED].
- Regulated 7.4V (not 5–6V) — correct for a load-bearing hexapod.
- 360° encoder — net win (§4).

**Must add / fix:**
1. **THERMAL is the real ceiling.** Walking is the oscillating regime that hit **71°C → 20% torque in ~110 min.** Poll `Present_Temperature` + `0x2A` (rate-limited), cap duty cycle, use a crouch/rest pose, plan cooling/rest, **bench one leg's thermal duty cycle first.**
2. **Torque margin is thinner than it looks.** With dynamic factor, 9 cm × 1.25 kg × 1.5 ≈ **16.9 kg-cm (87% of stall).** Hold effective offset **8–9 cm**, cap stride, target continuous ≤ ~10 kg-cm [FIXED].
3. **40A budget < 45A true stall** → add **470–1000µF/cluster at injection + 1000–2200µF on the rail**; don't rely on the SBEC or the average.
4. **Separate logic rail** (own regulator or local cap) — shared rail resets the controller mid-step.
5. **Star-ground the injection points; separate light signal return.**
6. **Two isolated positive banks, common ground only** — never join SBEC positives [FIXED].
7. **PETG/nylon + metal horns + dual-shear/bearings + heat-set inserts + threadlock + strain relief + rubber feet** [FIXED].
8. **Set + label all 18 IDs one-at-a-time BEFORE assembly.**
9. **Design each joint's travel inside one 0–4096 window; neutral ≈ 2048.**
10. **Hardware E-stop (battery switch / anti-spark) + branch fuses + LiPo LVC alarm** — software stop is not enough [FIXED].
11. **Define calibration artifacts up front:** servo ID map, zero offsets, sign convention, per-joint min/max limits, encoder seam location, recovery pose. Treat servo current/load feedback as **trend data, not calibrated torque** [FIXED].

**Test/validate before building:**
1. Code IK, **round-trip vs forward kinematics** (recover the same point); make sure the reach-limit flag fires.
2. Simulate reach + support polygon (Mithi), then **tip-over under gravity** (PyBullet/pyhexapod, `gui=True`).
3. **Build a one-leg test jig under real load** before printing all six legs — measure lever, mass share, and confirm `T < ~10–12 kg-cm`.
4. **Bench one leg's thermal duty cycle** at the holding pose.
5. First walk on **wave gait + cubic-Bézier swing @ 50 Hz**; **log current feedback** vs §2.4; graduate to tripod.

---

## (a) The ONE thing to install first — and the feedback loop
**Open [hexapod.netlify.app](https://hexapod.netlify.app/) now (zero install).** Drag body pose, pick tripod vs ripple, watch all 18 joint angles update live — this closes the intuition loop *before* any hardware: you *see* how a foot target becomes joint angles and where legs run out of reach. **Then install PyBullet** (`pip install pybullet`) and run `resibots/pyhexapod` with `gui=True` — that closes the *physics* loop (gravity, contacts, tip-over) the browser sim can't show. Order: **Mithi (kinematics, see it) → PyBullet (physics, trust it).** Both £0.

## (b) Concrete geometry + mass for the 19.5 kg-cm servos
**Coxa 35 mm / Femur 80 mm / Tibia 100 mm; body ~180 mm across, servos 60° apart; mass ≤ ~2.5 kg, battery centered & low.** Critically, adopt a **default stance that keeps the femur-axis→foot horizontal offset at 8–9 cm** and **cap stride** so a dynamic/impact spike stays ≤ ~12 kg-cm (≈60% of stall, SF ≥ ~1.7 static / ~1.1 worst-dynamic). Legs short + tucked. Lengthen or stand taller only after measured joint current confirms margin — geometry without a stance is not a torque design.

## (c) Prioritized "what could still bite / add or test"
1. **Torque margin** thinner than static math implies once dynamic load + leg mass + 9–10 cm levers are included → tuck legs, cap stride, one-leg load jig.
2. **SBEC wiring** — never tie the two positives; per-bank fuse; thermal-test the "20A" claim under load.
3. **Brownout / bus corruption** from shared impedance, weak grounds, long leads, no local caps → star ground + per-cluster bulk caps + separate logic rail.
4. **Overvoltage** on the 7.4V variant from regulator overshoot or 12V confusion → set 7.4V by meter under load.
5. **Thermal torque-cut** during standing/walking → temp polling + rest/crouch pose + duty cap.
6. **Servo ID / calibration mess** after assembly → ID + label one-at-a-time first; commit the calibration-artifact set.
7. **Printed brackets/horns** creeping/cracking → PETG/nylon, metal horns, dual-shear, inserts, threadlock, strain relief, rubber feet.
8. **Simulator confidence gap** — kinematic sims won't predict slip, backlash, sag, or real servo limits → validate in PyBullet and on the one-leg jig before scaling to six.
9. **Hardware safety** — add E-stop / anti-spark / branch fuses / LiPo LVC before first full-power test.

### Key sources
PCrnjak 3D-printed-Hexapod; KurtE Phantom_Phoenix; garciamathias OpenRoboticDog; LeRobot SO-100/SO-101; CoretechR ZeroBug; Vorpal Hexapod; Lynxmotion Phoenix; **Waveshare ST3215 spec table**; robonine STS3215 bench test; raw.org 3-DOF IK; pat92fr FootTrajectoryPlanner; mdpi stability-margin; RobotShop torque forum; Antdroid hardware; Mithi hexapod sim + kinematics library; resibots pyhexapod; PyBullet/Webots/MuJoCo/Gazebo/Isaac; Onshape/Fusion/FreeCAD; Fritzing/WireViz/KiCad; feetech-servo-sdk; ikpy; Hackster FE-URT/FD setup. (URLs inline.)