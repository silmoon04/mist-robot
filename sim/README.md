# MIST wheeled-quad simulator

Parametric digital twin of the MIST robot (tall canister + 4 sprawled wheel-legs,
16× STS3215 on raw 3S). Change any dimension/mass with sliders and get live:
CoM, per-servo torque vs rating, ground reaction forces, voltage sag & fuse
margins, tipping angle, ROM/workspace, animated gaits with per-frame feasibility,
and Rapier rigid-body physics (drop / push / drive / slope).

> **CAD compatibility notice (2026-07-12):** `defaultConfig()` is currently a
> generic simulator start state, not the selected Fusion/Layout A baseline. CAD
> authority is `docs/mist/MIST_FUSION_MASTER_DIMENSIONS.md`: d1 32, femur/tibia
> 110/70, mount rays ±25°/±109°, body-bottom height 148, stance radius 176, and
> wheel Ø70. Set or load those values before using simulator screenshots or
> exports as CAD evidence. Also note that changing simulated mount azimuths in a
> “drive stance” cannot rotate fixed physical pods; the conventional fixed-wheel
> heading/scrub decision remains open in the Fusion guide.

## Run it

Any static server works (ES modules don't load from `file://`), but use the
bundled one — it disables caching so edits always show up:

```
python sim/serve.py
```

then open http://localhost:8123/ . Needs internet the first time — Three.js and
Rapier load from pinned CDN URLs (Controlled Folder Access blocks scripted
downloads into this repo; if you want it fully offline, download the three URLs
in `index.html`'s import map into `sim/vendor/` via Explorer and point the
import map at `./vendor/...`).

## Layout

- Left column: SIDE / FRONT / TOP orthographic views. Right: orbitable 3D.
- Top chips: per-check verdicts (torque, fuses, sag, tipping, flex, grip, reach).
- Right panel, top to bottom: **dashboard** (BUILDABLE/MARGINAL/FAILING banner,
  stat cards, worst-servo gauge with continuous/peak zones, voltage gauge with
  sag + brown-out zone, per-leg fuse bars, tip compass — blob shows degrees of
  tilt survivable per direction, needle points where it falls first), **quick
  poses** (including the authoritative CAD Layout A baseline and Drive stance),
  sliders, overlays, torque bars, animation,
  physics, **auto-optimize**, exports.
- The phone face uses the real SVGs from `brain/face_assets/svg` and reacts to
  the verdict: happy when green, annoyed on warnings, angry when failing.

## Wheel drive mount

Mode section has a **Wheel servo** selector: at foot (hub motor), at knee
(belt down the tibia, +1 transmission stage), or at hip (belt down femur+tibia,
+2 stages). Moves the 55 g servo proximally in the mass model, torque
bookkeeping, physics bodies, and render (belt lines shown). Findings: a hip
mount unloads hip swing torque; a **knee mount can RAISE hip-pitch torque in
the sprawl stance** because the knee sits farther out than the foot; at
standstill the GRF term dominates so all three are within ~2%, and remote
mounts add belt mass + raise the CoM slightly. The win is in swing/gait and
unsprung mass, not standing.

## Gait lab (video math)

Panel adapted from the.Amazing PhD's "How To Make Your Robot Work, The First
Time" (Charlotte): actuator torque-speed lines make loaded gait phases slower,
so ground speed vs command bends onto an asymptote instead of the naive line.
Adapted from his DC-motor/cam legs to our position servos: per-phase joint
excursions and torques are measured from the REAL crawl preset, phase time =
worst joint Δq/ω_avail(τ), v = body advance / cycle time. Sliders: battery
charge, dynamic load factor k (from the MIST PDF guide), payload. Plots: speed
curve with asymptote + worst-servo torque through the cycle against the
10 kg·cm hold budget and the stall line. Also checks his stride/leg-interference
rule (fore-aft foot gap vs stride + wheel Ø).

## Auto-optimize

Pick a goal (min torque / max tip / max runtime / min mass / balanced), set the
hard constraints, check which variables it may change, hit Optimize. Every
candidate is scored on a pose battery — stand, low squat, one-leg lift, 10°
slope — so a config can't win by being good at standing still only. ~800
evaluations run in under a second; top-5 distinct results get Apply buttons.

## Trusting the numbers

`Self-tests` button (or `sim.selftest()` in the console) runs invariants:
IK↔FK roundtrip, ΣGRF = weight, symmetric-stance equality, torque vs
finite-difference potential energy, Jacobian check, slope load shift, linkage
ratio. All must pass. The analytic layer (not the physics engine) is the source
of truth for numbers; physics is for "does it fall over".

Verdicts are evaluated against stall torque at brown-out voltage (9.9 V), not
nominal 12 V — green means <30% continuous, the safe long-term zone.

## Using a config IRL

- **Save config** → JSON you can commit next to CAD.
- **Servo table (.h)** → per-joint STS3215 ticks (4096/rev, neutral 2048) with
  ROM limits — paste into the ESP32 firmware; flip `MIST_SIGN[]` per joint after
  checking horn directions on the bench.
- **Spec sheet (.md)** → dimensioned CAD table + mass budget in the style of
  `docs/mist/MIST_MATERIAL_DIMENSIONS_MASS.md`.
- **Bench predictions** → falsifiable numbers for the T9 single-leg/first-stand
  tests: grams per foot on the kitchen scale (±10%), amps/watts at the
  watt-meter. If reality disagrees, fix the model before printing legs 2–4.

## Physics mode notes

- Joints are held by hand-rolled PD servos (Rapier's built-in joint motor was
  ~60× too weak for small links regardless of MotorModel), torque hard-clamped
  at stall — genuinely overloaded poses sag or collapse. World runs at 960 Hz
  (explicit PD on ~1e-4 kg·m² links is unstable at coarser steps).
- Robot self-contacts are disabled in the engine (parts overlap at every joint
  by construction); the analytic collision checker covers self-collision.
- Wheel commands project desired body motion onto each wheel's own rolling
  direction. A historical default-geometry test at ±50°/±130° reported only
  61 mm in 4 s, while a simulated ±28°/±152° arrangement reached 827 mm. That
  comparison is a kinematic hypothesis, not a physical stance change: fixed
  chassis pods cannot rotate because software changes an angle. The current
  ±25°/±109° CAD still needs an explicit low-speed scrub, omni, adjustable-pod,
  or steering decision and real-floor validation before drive commands are
  considered meaningful.
- Physics GRF readout is approximate (contact-event based); trust the analytic
  panel for numbers.

## Console API

`window.sim` — `sim.set('leg.femur', 160)`, `sim.verdicts()`, `sim.scan()`,
`sim.pose('Crawl', 0.4)`, `sim.res` (full pipeline result).
