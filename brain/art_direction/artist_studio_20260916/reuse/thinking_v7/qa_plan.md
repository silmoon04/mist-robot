# Thinking studies QA

The six studies are a separate preview. The approved v6 activity page and live phone setup must remain unchanged.

Acceptance checks:

- Compare the original face paths and source cels with the verified v5 renderer. Props can move the face as a whole; they cannot replace the eyes, distort proportions, or substitute a mouth for thought.
- Sample all six studies through entrance, notice, work, pause, resume, and exit. Confirm real pose changes rather than changing beat labels on a static cel.
- Cross loop seams and entry/exit boundaries at 15 fps. Review visible registration and abrupt jumps using the contact sheet and numerical placement deltas.
- Run past several loop cycles. No timer may turn pending work into success or end the activity.
- Start voice mid-action, during a pause, and near a loop seam. The action should quiet while audio continues on its unquantized clock. Stop voice and check orderly resumption.
- Preserve immediate mouth closure, interruption, cancellation, and stale owner protection where the public API supports them.
- Check transparency, clipping, nonempty registered cels, source provenance, and both allowed frame counts (16 new, 12 reused).
- Verify that the earlier activity preview and live files retain their starting hashes.

Tests will use deterministic clocks, recorded canvas calls, and supplied saved assets. No microphone, model provider, or paid voice request is needed. Browser feel and final composition remain the root reviewer's responsibility.
