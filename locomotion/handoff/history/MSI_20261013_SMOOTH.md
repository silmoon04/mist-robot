# MSI continuation: smooth remote and optional higher speed

The user reported choppy UI and asked whether 0.025 m/s was the highest speed. Continuation added the versioned `sim_remote_interactive_v2.py`, an offline WebGL CAD viewer, pose interpolation and a bounded timer for throttled embedded-browser callbacks. The running main service is on 8131; the bridge on 8130 remains dry-run. The desktop shortcut launches **Start MIST Remote (Smooth).cmd**.

Two actual HTTP baseline probes recorded about 2 Hz JPEG changes and command P95 267–289 ms. The final main-service probe recorded state P95 8.36 ms, command P95 3.16 ms and 40 observed pose updates/s. The app displayed 23–25 fps. Physics runs fixed 20 ms steps; displayed fps is measured separately.

Eight forward cases at 480 steps each selected an optional 1.0-second, 0.040 m/s **Higher speed preview**. Average progress was 0.02430 m/s bare and 0.02382 m/s with 155 g phone payload, about 40–43% above the default. A 0.8-second cycle regressed progress. Every case avoided falls and floor/sensor faults; strict tracking still fails. The startup default remains Faster crawl at 1.2 s/0.025 m/s. Neither profile establishes loaded motor performance or a physical maximum.

Ten backend, thirty UI/viewer and three v4 gait tests passed. Windows launch/reuse/owned-stop/restart passed. Live main-page testing applied Higher speed, exercised forward movement and Stop, then restored Faster crawl and the user's flat/absent-phone/MPU6050/seed-42 setup. Original frozen sources, helpers and experiment receipts remain byte-exact. No new training or hardware actuation ran.

Continue from [the review](../../reviews/msi_remote_smooth/REVIEW.md), [the remote guide](../../REMOTE_GUIDE.md) and [MSI_CONTINUATION.md](../MSI_CONTINUATION.md). Qualification and the next hardware contract remain open. The user is still building the R7.
