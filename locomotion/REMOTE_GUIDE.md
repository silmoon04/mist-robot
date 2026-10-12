# MIST remotes on the MSI

Double-click **Start MIST Remote.cmd** in this directory. It starts the installed WSL CPU runtime and opens the simulation. Both services listen on this laptop's loopback interface:

- [Simulation remote](http://127.0.0.1:8131/): live CAD view, held driving commands, terrain, phone payload, sensors, checkpoint loading and inverse kinematics.
- [Joint preview](http://127.0.0.1:8130/): dry-run joint angles and commissioning controls. The launcher supplies no serial port or physical calibration.

The user reported on 12 October 2026 that the R7 is being built. Loaded motor and telemetry measurements wait until assembly. Walking and physical transfer remain unqualified.

## Using the simulation

Hold a direction to move; release to stop. W/A/S/D drive forward/left/backward/right, Q/E turn, and Space or Escape stop. Shortcuts leave text fields and selectors alone. Motion also stops when the page loses focus, is hidden or loses its connection. The server retains its independent 350 ms command watchdog.

Changing the surface, payload, controller or sensor does not apply until **Apply & reset** succeeds. Advanced settings contain the seed, randomization, sensor profile and checkpoint path. Checkpoint paths refer to the WSL filesystem; loading still requires the matching provenance and sensor contract. An explicit reset refusal preserves the running simulation. If the connection times out during reset, the page reports that the outcome is unknown and reconciles the settings when state returns.

The joint page's **Enable preview** enables dry-run angle controls for a 60-second commissioning window. Hold a crawl direction to preview it; release returns to Stand. **STOP / torque off** disables the preview and latches a stop. Inspect the reason, then use **Clear inspected fault** before enabling it again. Disable preview, the watchdog and intent-generation handling remain active. Dry-run angles are requested poses, not measured servo feedback. Hardware commissioning uses the same guarded backend but requires a deliberately launched serial connection and measured calibration. Physical crawl is disabled.

## Session controls

From PowerShell in this directory:

```powershell
& '.\Start MIST Remote.cmd' -NoBrowser
& '.\scripts\launch_remote.ps1' -Status
& '.\scripts\launch_remote.ps1' -Stop
```

Repeated launch reuses the running session. Stop closes only services created by that session; remotes started separately stay with their original owner. The Linux supervisor uses a process lock and kernel process identity for shutdown.

The default distribution is `Ubuntu`, repository `/home/hssil/mist-locomotion-msi/repo`, and interpreter `.venv-locomotion/bin/python` inside it. A restored installation can select another prepared path:

```powershell
& '.\scripts\launch_remote.ps1' -Distribution Ubuntu -WslRepo '/home/hssil/mist-locomotion-msi/repo'
```

Startup errors name the relevant log. Windows launcher logs are in `locomotion/.remote-session/` in the review checkout; service logs are in that directory in the WSL checkout. Session files are local runtime state and are excluded from Git and portable archives. Runtime installation and source preservation are described in [MSI_SETUP.md](handoff/MSI_SETUP.md); experiment outcomes and the next gait change are in [MSI_CONTINUATION.md](handoff/MSI_CONTINUATION.md).
