# Hexapod reference to phone quadruped

This is a new design based on Emre Kalem's hexapod: https://www.youtube.com/watch?v=ciE2Z_92T7s . Previous MIST geometry is excluded. Prior work supplies only tool-operation lessons, actual inventory and measured hardware facts.

## Required result

1. Four articulated legs, no wheels, retaining the source robot's central hexagonal body and recognizable open, printed leg structure.
2. Three direct servo joints per leg using owned Feetech STS3215 C018 12 V units and their supplied metal horns. Avoid gears and belts.
3. One additional STS3215 pans an upright Xiaomi Mi 9 SE in landscape orientation above the body, following the user's correction. Preserve camera views, display visibility, retention and side USB access. Use Wi-Fi and the phone battery during rotation; attach charging only while parked.
4. Package owned battery, ESP32, servo bus interface and power distribution with fastener/tool access and removable covers.
5. Generate reviewable CAD, native Fusion evidence where available, STEP and per-part STL, print-fit coupons, and PLA slicing/assembly guidance for the owned Neptune 4 Pro.
6. Generate a consistent URDF and run bounded physical simulation and geometric checks. Report exact failures and assumptions rather than calling an animation verification.
7. Show the resulting assembly and supply an indexed deliverable package.

## Verification gates

| Gate | Required evidence | Current status |
|---|---|---|
| Reference | Creator files or documented visual reconstruction; attribution and source limits | Visual reconstruction documented; original download unavailable |
| Servo | Manufacturer outline, supplied horn, actual clamp and cable interfaces | Drawing-based geometry complete; actual fit and screw seating unmeasured |
| Geometry | Valid solids, printable closed meshes, fastener paths, no unexplained static interference | R3 CAD and 34 production mesh checks pass; real screw heads and tips require assembly checks |
| Movement | Leg ranges and phone sweep checked against nearby parts and wiring reservations | Operating yaw limited to +/-22 degrees; sampled clearances pass and all 13 native joints pass measured motion probes |
| Simulation | Mass/inertia provenance, contact/load assumptions, stable stance and bounded crawl results | Five R3 cases recorded using sliced or solid mass; nominal crawl passes, largest feedback uncertainty fails |
| Fit | Printable representative coupons; physical results kept unverified until measured | Seventeen essential and ten optional specimens on two plates; all physical feedback blank |
| Printing | Each part within bed, assembly quantities, material/orientation/settings and release limits | 34 STL types / 76 pieces sliced for analysis; PLA starting guide and oriented files ready |
| Printed strength | Layer direction, actual sections, load cases, reinforcement and proof-test plan | Local improvements quantified; side-load sharing, 2g limits, preload and creep remain qualification tests |
| Delivery | Source scripts, CAD, print files, preview, checks and open issues agree | Landscape CAD, Fusion export, URDF, viewer and plates bind the same geometry |

Nominal drawings can support a first-fit print. Physical fit, load capacity and reliable walking cannot be certified without the corresponding hardware tests. Keep coupon-ready, candidate full parts and physically validated results distinct.
