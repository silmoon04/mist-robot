# DFM update for the overnight leg plate

This changes two coxa pieces and retains the other six overnight parts. No bench base, duplicate yaw cap or duplicate yaw spacers are added.

## Changes

Both flanges now use a regular octagon centred on the shaft, measuring 28 mm across opposite flats. The octagon fully encloses the original round flange, so no mixed curved/polygon outline remains. The upright flange has a separate small trapezoidal print foot with 45-degree sides. A narrow bottom rail and local webs support the post and floating saddle lip. These are permanent part features, not breakaway support.

The horizontal horn screw passages and post holes receive pointed 45-degree roofs. The post nut recesses have sloping roofs while retaining their nut seating flats. The 7 mm central circular clearance is preserved inside a hexagonal opening: its flat ceiling is a short approximately 4 mm bridge. The matching lower arm receives the same centred flange outline and fixing-centre pattern. Its washer counterbores remain circular and face upward when printed. Those large recessed washer seats overlap the central access opening at the outer face, as before; the overlap is symmetric and is required to retain the existing 7.7 mm washer fit and screw pattern. The central hexagon itself remains regular and centred.

The existing roofed servo-clamp holes remain. Flat-printed mating caps and cheeks retain their round vertical holes because those already print without support. Their hole centres and fastener interfaces still match. Making vertical bearing or washer seats hexagonal would not improve their printability.

## Measured result

Support material: 4.72 g before, 4.04 g after, a 14% reduction. Total PLA is 147.9 g. Cura estimates 9 h 48 min, versus approximately 9 h 50 min before. This is an improvement to the coxa's printed features and hole cleanup, not a meaningful speed saving. The permanent webs add material.

The remaining supports are still necessary for the exposed undersides, especially the raised straight tibia. Eliminating those entirely requires changing the structural layout or splitting another part, which is beyond this quick revision. Do not turn all supports off.

## Print

Open R7_DFM_Overnight.3mf as models and import/select DFM_PLA_028.curaprofile in Cura. Keep the existing Neptune 4 Pro machine, 0.4 mm nozzle, 100 percent scale and the supplied orientations. This is a geometry plate, not a saved Cura project, so it does not select the profile automatically. The combined STL is a fallback.

The profile retains 0.28 mm layers, five walls, 25 percent gyroid, slow overhang walls and 15 to 20 mm/s bridges. It uses build-plate tree support with 4.3 mm XY clearance to keep tree tips out of the central hexagon, and a 0.56 mm top gap. The greater clearance leaves more short unsupported edge span and may roughen undersides; inspect the supplied toolpath preview against Cura. The actual updated slice retains broad underside support. Do not substitute the older profile, which placed tips inside that opening.

## Checks and compatibility

All eight meshes are closed and consistently wound. Source and profile hashes match the slice. The new material was checked against all assembly parts at the 39 previously verified poses, with no intersections. Original screw and washer clearance envelopes remain open; the lower post nut's insertion route was checked independently. The updated slice contains no sampled support centre lines inside the checked screw bores, nut entries or central clearance opening. These checks do not prove actual bridge quality, bead-edge clearance or support removal force.

The two updated coxa parts belong together. All other R7 leg pieces, screw sizes and motion limits remain unchanged. Use the included R7 assembly guide, including its washer-thickness assumptions. Editable STEP files for the changed pieces and the assembled CAD are included. The earlier Fusion archive still shows R7 before this local DFM update; use the new STEP for the revised geometry.

The earlier full-leg load limitation remains: begin with restrained unloaded articulation. This update does not certify the bridges for full-body loading or two-foot balance.
