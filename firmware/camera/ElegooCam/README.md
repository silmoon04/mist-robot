# ELEGOO camera firmware

1. Copy `secrets.example.h` to `secrets.h` and set the station, fallback AP,
   and HTTP credentials. `secrets.h` is ignored by Git.
2. Compile normally for the robot. The ESP32 brownout detector stays enabled.
3. Define `BENCH_BUILD` only for a USB-powered diagnostic build where camera
   startup current is known to cause nuisance brownout resets. Never use that
   flag on the robot power rail.

Open `http://<camera-ip>/` and enter the HTTP credentials. The main page and
single-frame capture use port 80; MJPEG uses `http://<camera-ip>:81/stream` so
a connected stream cannot block the other routes.

All three routes require HTTP Basic Auth. This is access control, not
encryption: credentials and video remain plain HTTP. Keep the camera on a
trusted/private LAN, or put it behind a VPN/reverse proxy before wider network
exposure.
