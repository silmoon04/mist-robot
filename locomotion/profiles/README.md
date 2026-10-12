# Direct-drive design profiles

`r7_direct.json` records the current 82/90/105 mm source leg. The profile pins the URDF, CAD manifest and config with SHA-256 hashes. The audit reports joint origins, axes, limits and every source link mass, and rejects mismatches. Source URDF effort and velocity limits appear separately from the configured actuator assumptions. Neither supplies measured actuator performance.

Run from the repository root:

```sh
python locomotion/design_profile.py audit
python locomotion/design_profile.py audit --profile path/to/candidate.json --baseline locomotion/profiles/r7_direct.json
python locomotion/design_profile.py template --output path/to/pending-measurements.json
python locomotion/design_profile.py measurements --record path/to/pending-measurements.json
```

`--output` writes a new JSON file and refuses to overwrite an existing one. Without it, commands print JSON. Paths in a profile are relative to that profile. Raw evidence paths are relative to the measurement record. Config `source_root` tells the audit where its repository-relative source paths begin. If a source changes, inspect the change before updating its pinned hash.

The supported family is a serial direct-drive yaw/hip/knee chain with +Z/+Y/+Y axes, zero joint frame rotations, and lengths along local +X. Other axes, mimic joints, extra moving joints, transmissions and closed loops are rejected. A four-bar leg needs its own solver and model validation.

The R7 source URDF has no toe frame. The audit checks coxa and femur lengths against joint origins and checks all three lengths against the pinned CAD manifest. Its tibia length therefore comes from the manifest rather than an independently encoded URDF toe transform. An alternative profile can use `toe_reference.basis: "urdf_fixed_joint"` and name a fixed toe joint to check that transform directly. A source with fixed frames on the tibia must select its toe joint explicitly. Declared masses must cover every source link, including a zero-mass toe link if present. Source mass includes the bench fixture; it is not the floating quadruped's mass.

Kinematics accept an optional `LegGeometry` or a mapping with `coxa_m`, `femur_m` and `tibia_m`, plus a `(3, 2)` limit array in radians. Existing calls still use R7 values. Dimensions must be finite and positive; limits must be ordered and finite, with yaw inside the principal [-pi, pi] interval. FK and the Jacobian can examine angles outside limits unless `check_limits=True`. IK checks limits by default and solves the outward radial branch. Designs or poses whose signed radial reach crosses the yaw axis need a separate branch policy.

```python
from locomotion.kinematics import LegGeometry, forward, inverse

geometry = LegGeometry(coxa_m=.095, femur_m=.12, tibia_m=.14)
target = forward([0, .4, 1.0], geometry=geometry)
angles = inverse(target, geometry=geometry)
```

This abstraction supports geometry analysis. Another design still requires changes to `model.py`, mounts, collision shapes, inertials, gait and actuator control, followed by model/FK tests and new training. The exporter and current gait still embed R7 geometry assumptions. The exporter now invokes the pinned profile audit and rejects altered R7 source hashes, rotations, topology and coordinated tibia changes before writing output. These guards do not instantiate another design. Loading a profile does not select a new robot, modify config, or enable deployment.

`r7_measurements.template.json` contains empty physical measurements and pending calibration status. Copy it or generate a fresh template, then record geometry, link masses, actuator tests, joint zeros/directions and body centre of mass. Add a UTC timestamp, operator, instruments, procedure, supply voltage, ambient temperature, test duration, load description and paths/hashes for raw evidence. Partial records stay `pending`; `measured` requires all fields and verifiable evidence hashes. Actuator comparisons show measured continuous torque against the configured command cap, plus speed and latency differences. The command cap remains an analysis choice. The tool checks record consistency and reports deltas; it cannot establish whether a test procedure or instrument was adequate. Review differences before explicitly changing the model or config. No performance or hardware readiness claim follows from a successful profile audit.
