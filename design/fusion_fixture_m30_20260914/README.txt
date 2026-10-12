FUSION FIXTURE DEMONSTRATION AND M3x30 BRIDGE ADAPTATION

WHAT MOVES
The alignment gauge is a temporary measuring tool. It joins the case to the
main horn only to check their relative position. NEVER power or command the
servo while that gauge is installed. Remove it completely after the fit test.

In the working horn fixture, the servo case stays fixed. The powered main
horn, main printed cheek, bridge, opposite printed cheek and auxiliary disc
rotate together. The auxiliary disc turns around the fixed rear stub; it is
not screwed rigidly to the servo case. Its centre washer bears on the stub,
leaving the disc free. The fixture is one output link, not a locked box.

FUSION
The active document is named:
  MOVE THIS - case fixed, cheeks and bridge rotate - M3x30
It contains a grounded base and one actual revolute joint for the output.
Expand Joints in the browser, right-click
  Drive this joint - output only - +/-10deg
and choose Drive Joint to inspect the bounded motion. The joint exists even
though its on-screen glyph is hidden for a clearer view.

Another open document shows the exploded parts:
  ASSEMBLY DEMO - gauge removed before movement - M3x30
The live scripted sequence was played in Fusion and captured from its viewport.
Replay recordings are in fusion/assembly_sequence.mp4 and servo_joint_motion.mp4.
The F3D exports preserve the assemblies and the working native revolute joint.
The explosion is scripted placement animation, not a saved Animation-workspace
storyboard. The replay_fusion.py script can replay both while both documents
remain open through the configured Fusion MCP workflow.

The motion is geometric/kinematic demonstration, not a torque, contact,
thermal or physical servo test. The CAD check samples -10,-5,0,5,10 degrees.
The native one-degree motion probe passed. All 61 recorded motion frames kept
the case transform stationary. The model was restored to its neutral pose.

USING M3x30 INSTEAD OF THE UNAVAILABLE M3x50
The old 46 mm wide through-bolt stack cannot be held by one M3x30 screw.
Print ONLY these three replacement pieces:
  bridge_M3x30.stl: one piece
  bridge_spacer_8mm.stl: two pieces
Or load M3x30_Bridge_Adapter_Plate.3mf, which contains all three.
The existing printed main and auxiliary cheeks do not change.
Use the same R5 Third Fit - Joint Interfaces - 0.20mm no-support Cura profile.
The three-piece slice estimates about 30 minutes, 5.0 g model PLA and zero
support material. Actual Cura/printer times may differ.

ASSEMBLE THE REPLACEMENT BRIDGE
1. Drop one plain M3 nut into each of the two open top slots of the new bridge.
   They occupy separate hex seats near the centre. Use the two separate nuts;
   do not try to join the screws in one nut.
2. Position the bridge between the existing cheek arms, with its nut-loading
   slots upward. Keep the long servo case pointing away from the bridge.
3. Put one printed 8 mm spacer against the OUTSIDE of each cheek at the bridge
   hole. These are additional to the existing printed cheeks, not between them.
4. From each outside end, fit one M3x30 screw with ONE OD7 x0.5 mm head washer.
   Pass it through its 8 mm spacer, 4 mm cheek and into its own captured nut.
5. Tighten gently while observing the two nuts. The nominal screw tips remain
   3 mm apart; check actual screw length and seating before further tightening.
   This is a fit fixture adaptation, not a load-qualified production bridge.

ALIGNMENT GAUGE WITHOUT LONG TIE BOLTS
Do not substitute M3x30 for the original M3x50 tie bolts; they cannot reach.
For the current unpowered dimension check, gently seat the gauge feet by hand
on the already clamped servo. Check that both feet and the horn face meet
without force. Use the specified four short M3x6 horn screws only if their
seating is correct. You may leave the two long mounting bores empty for this
hand-seated test. Do not perform a retention/load test in that arrangement.
Remove the gauge before assembling or moving the horn fixture.

SHORT HORN FASTENERS STILL MATTER
You confirmed that shorter screws are also available; M3x30 is the long-screw
constraint. Keep the short horn fasteners specified below.
Main cheek: M3x6 with one OD6 x0.5 mm washer per screw.
Auxiliary cheek: M3x8 with TWO OD6 x0.5 mm washers per screw and the existing
1.1 mm integral lands. The supplied centre retainers remain unchanged.
An M3x30 screw is NOT a substitute for those short horn screws and can bottom
out or damage the servo. If only M3x30 screws are available, print/check the
new bridge and watch the demo, but leave horn fastening pending the short screws.

The earlier clamp screws were specified as M3x35. The existing physical clamp
has been reported to hold well, but this does not establish a replacement
clamp stack using M3x30. This adaptation changes only the fixture bridge.

Printed bridge and cheek geometry are exact CAD solids. Screws and nuts in
the explanation are nominal simple envelopes; threads and hand tightening
are not simulated. Fusion assemblies omit detailed fastener solids, so use
these written stacks for the exact washer and screw count.
