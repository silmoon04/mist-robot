# Existing MIST app and the R4 quadruped

The existing MIST voice and face app can supply the conversation interface for this design. It currently runs on the computer, reports simulated motion and has no connection to the new thirteen-servo body. This pass adds an isolated, offline R4 joint preview under `software/`. It does not change the existing app, launch services, read credentials, connect to the phone or command a servo.

## What can be reused

| Existing behavior | Evidence and limits |
|---|---|
| Conversation, memory and background research | The saved console uses Spark for conversation and Astra for background tasks. Notes and recent conversation persist. The September 7 reports record real desktop model and research calls. Current account availability was not queried in this pass. |
| Voice and face animation | The app uses the existing MIST ElevenLabs voice, with Flash v2.5 selected for responsive speech. Forty SVG faces map to twenty expressions; mouth animation follows the playback clock. Actual desktop playback was recorded. The app can keep its providers and renderer. |
| Hands-free Talk | A user click enables capture, local speech detection, streaming Deepgram recognition and automatic submission. Speech can interrupt a reply. Saved virtual microphone tests and a real saved-audio recognition probe passed. Room acoustics and the Mi 9 SE microphone/speaker loop remain untested. |
| Phone sensors | `tools/sensors/README.md` records SensorServer on the Mi 9 SE delivering 148 messages in six seconds to the computer over USB on June 30. That is separate from the brain application. Its ESP32 Wi-Fi consumer remains a TODO. |

## Current connections and missing adapters

The console binds `127.0.0.1:8776`. `POST /api/say` takes text and an optional request ID; `GET /api/events` streams replies and display events. `/api/speech` requires speech protocol 2, a request ID and a reply, preview or manual purpose. `/api/interrupt` cancels conversation and speech; it does not establish a physical stop.

Streaming recognition uses a loopback proxy, normally on port 8788. Its advertised `ws://127.0.0.1:8788/stt` address would point at the phone itself if the page were opened on the phone. The HTTP Host/Origin checks and proxy origin rules also accept only localhost. Therefore entering the computer's Wi-Fi address is not an implemented phone connection. Changing only the bind address would leave these other requirements unresolved. Phone Talk needs an appropriate secure browser context and a reachable speech transport.

The existing UI and capability report still describe wheel feet. `look_at` stores a string in simulated state; it does not compute a camera bearing or rotate a servo. `bus.jsonl` is an audit log of tool results, not a motor queue. `observe` reads a local timestamped report, rejects stale reports and preserves unverified provenance; no camera producer connects it to this phone.

The real bench code is a separate serial controller on localhost port 8124 for one earlier three-servo leg. Its calibration and coupled remote-knee equation belong to that mechanism. The new R4 has direct joints and different coordinate frames. No old dimensions, tick offsets, signs or knee coupling were copied into the new preview. The ordered inventory contains eighteen C018 servos, but the new proposed allocation uses thirteen and still needs individual commissioning.

## New offline R4 contract

`software/r4_preview.py` derives joint ranges, neutral angles, axes and parent links from the current R4 CAD manifest. Its proposed ID map matches `printing/WIRING.md`: FL 1/2/3, FR 4/5/6, RL 7/8/9, RR 10/11/12, phone pan 13. Joint names match the URDF exporter: `yaw_FL`, `hip_FL`, `knee_FL` and the corresponding other legs, plus `phone_pan`.

The preview accepts a complete thirteen-joint pose, one explicit pan angle, capabilities or a preview stop. It checks the current manifest hash, finite radian values, exact joint names and geometric ranges. Calibration fields remain empty. Hardware mode, wheel commands, gait requests, free-text gaze conversion, raw-count assumptions and USB-connected pan are rejected. Pan previews use the principal interval from minus pi to plus pi without inferring a wrap count. The continuous mechanical axis still needs servo-mode and startup-position validation before physical full rotation.

The saved profile, neutral and pan examples are bound to the manifest used by `software/run_checks.py`. Twenty-eight offline tests passed on Python 3.12.7. They cover the map, stale or altered profiles, missing calibration, old command shapes, ranges, malformed numbers, USB state and hardware refusal. The independent review found oversized integer and alternate-source-path cases; both were repaired and added to the tests. No network, provider, serial or app process was used. These checks establish a software preview contract, not gait, collisions, strength or physical control.

## Next integration steps

1. Add a controlled phone access path with HTTPS/WSS, matching origins and the correct reachable STT URL. Keep provider credentials on the backend. Test the actual Mi 9 SE in its landscape cradle: full face visibility, microphone permission, reply playback, Talk interruption and reconnect. The earlier phone viewport attempt remained at desktop dimensions, so it did not validate this layout.
2. Add an explicit R4 body profile to the existing app, including its no-wheel capabilities. Route deterministic joint previews through the new contract before adding motion. A request to look at a person needs actual perception and a frame conversion before it can become a numeric pan target. Account for landscape mounting and measured pan angle in camera/IMU transforms; a rotating phone cannot be treated as a fixed body IMU.
3. Record each delivered servo, unique ID, reference count, direction, safe endpoints and operating mode for this new mechanism. Check startup recovery and multi-turn behavior separately for pan. The proposed map and geometric ranges do not supply these measurements.
4. Implement the real controller and its acknowledged intent interface, sequence/expiry checks, feedback, watchdog, independent stop and joint limits. Use the new kinematics and validated gait controller. Keep language-model latency outside the servo control loop and keep the old audit log out of the actuator path.
5. Follow the print-fit, harness and supported-leg checks in the manufacturing package. Prove an empty pan sweep, dummy-phone retention and phone camera clearance before loaded movement. Use the phone battery and Wi-Fi for moving pan; USB charging remains a parked service operation.

Source files inspected, relative to the repository root: `brain/docs/MIST_CONSOLE.md`; `brain/ui/server.py`; `brain/ui/stt_proxy.py`; `brain/ui/static/index.html`; `brain/ui/static/talk_capture.js`; `brain/extensions/robot-tools.ts`; `brain/extensions/grounding.ts`; `tools/sensors/README.md`; `bench/SINGLE_LEG_CALIBRATION.md`; `bench/leg_calibration.py`; `bench/servo_bench.py`; `docs/mist/MIST_ACTUAL_INVENTORY.md`. Historical software evidence is under `design/mist_v2_20260906/brain_v2_20260907/INTEGRATION_REPORT.md`, `latency_fix_20260907/UPDATE.md` and `talk_mode_20260907/TALK_REPORT.md`. Only software behavior and inventory were reused from those records.
