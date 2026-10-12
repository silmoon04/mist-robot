#pragma once

// Copy to secrets.h (ignored by Git) and replace every placeholder.
#define WIFI_SSID "your-2.4GHz-network"
#define WIFI_PASSWORD "replace-with-station-password"

#define CAMERA_AP_SSID "REDACTED_PRIVATE_VALUE"
#define CAMERA_AP_PASSWORD "replace-with-strong-ap-password"

// Browser Basic Auth for /, /capture, and port 81 /stream.
#define CAMERA_HTTP_USER "mist"
#define CAMERA_HTTP_PASSWORD "replace-with-strong-http-password"
