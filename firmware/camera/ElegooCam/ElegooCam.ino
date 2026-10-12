// ElegooCam - CameraWebServer for the ELEGOO ESP32-WROVER Camera (V1.5)
// Camera pin map = M5STACK_WIDE (verified against ELEGOO's shipped firmware).
// Streams MJPEG in any browser. Falls back to SoftAP if the WiFi won't join.

#include "esp_camera.h"
#include <WiFi.h>
#include "esp_http_server.h"
#include "secrets.h"
#ifdef BENCH_BUILD
#include "soc/soc.h"           // for brownout register
#include "soc/rtc_cntl_reg.h"  // for brownout register
#endif

// ======== ELEGOO ESP32-WROVER camera == M5STACK_WIDE pin map ========
#define PWDN_GPIO_NUM   -1
#define RESET_GPIO_NUM  15
#define XCLK_GPIO_NUM   27
#define SIOD_GPIO_NUM   22
#define SIOC_GPIO_NUM   23
#define Y9_GPIO_NUM     19
#define Y8_GPIO_NUM     36
#define Y7_GPIO_NUM     18
#define Y6_GPIO_NUM     39
#define Y5_GPIO_NUM      5
#define Y4_GPIO_NUM     34
#define Y3_GPIO_NUM     35
#define Y2_GPIO_NUM     32
#define VSYNC_GPIO_NUM  25
#define HREF_GPIO_NUM   26
#define PCLK_GPIO_NUM   21

// ======== WiFi/auth values live in ignored secrets.h (copy the example). ========
const char *ssid     = WIFI_SSID;
const char *password = WIFI_PASSWORD;

#define PART_BOUNDARY "123456789000000000000987654321"
static const char *_STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char *_STREAM_BOUNDARY     = "\r\n--" PART_BOUNDARY "\r\n";
static const char *_STREAM_PART         = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

httpd_handle_t camera_httpd = NULL;
httpd_handle_t stream_httpd = NULL;

static String basicAuthHeader() {
  static const char table[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  String raw = String(CAMERA_HTTP_USER) + ":" + CAMERA_HTTP_PASSWORD;
  String out = "Basic ";
  for (size_t i = 0; i < raw.length(); i += 3) {
    uint32_t n = ((uint8_t)raw[i]) << 16;
    if (i + 1 < raw.length()) n |= ((uint8_t)raw[i + 1]) << 8;
    if (i + 2 < raw.length()) n |= (uint8_t)raw[i + 2];
    out += table[(n >> 18) & 63];
    out += table[(n >> 12) & 63];
    out += i + 1 < raw.length() ? table[(n >> 6) & 63] : '=';
    out += i + 2 < raw.length() ? table[n & 63] : '=';
  }
  return out;
}

static bool authorize(httpd_req_t *req) {
  size_t len = httpd_req_get_hdr_value_len(req, "Authorization");
  bool ok = false;
  if (len > 0 && len < 256) {
    char value[256];
    if (httpd_req_get_hdr_value_str(req, "Authorization", value, sizeof(value)) == ESP_OK) {
      ok = basicAuthHeader().equals(value);
    }
  }
  if (!ok) {
    httpd_resp_set_status(req, "401 Unauthorized");
    httpd_resp_set_hdr(req, "WWW-Authenticate", "Basic realm=\"MIST camera\"");
    httpd_resp_set_type(req, "text/plain");
    httpd_resp_sendstr(req, "Authentication required");
  }
  return ok;
}

static esp_err_t index_handler(httpd_req_t *req) {
  if (!authorize(req)) return ESP_OK;
  httpd_resp_set_type(req, "text/html");
  const char *html =
    "<!DOCTYPE html><html><head><meta name=viewport content='width=device-width,initial-scale=1'>"
    "<title>ELEGOO ESP32-CAM</title></head>"
    "<body style='margin:0;background:#111;text-align:center;font-family:sans-serif'>"
    "<h3 style='color:#eee'>ELEGOO ESP32-WROVER Camera</h3>"
    "<img id=cam style='max-width:100%;height:auto'/>"
    "<p style='color:#888'>port 81 /stream = live MJPEG &middot; <a href='/capture'>/capture</a> = single JPEG</p>"
    "<script>cam.src='http://'+location.hostname+':81/stream'</script>"
    "</body></html>";
  return httpd_resp_send(req, html, HTTPD_RESP_USE_STRLEN);
}

static esp_err_t capture_handler(httpd_req_t *req) {
  if (!authorize(req)) return ESP_OK;
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) { httpd_resp_send_500(req); return ESP_FAIL; }
  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
  esp_err_t res = httpd_resp_send(req, (const char *)fb->buf, fb->len);
  esp_camera_fb_return(fb);
  return res;
}

static esp_err_t stream_handler(httpd_req_t *req) {
  if (!authorize(req)) return ESP_OK;
  camera_fb_t *fb = NULL;
  esp_err_t res = ESP_OK;
  char part_buf[64];

  res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
  if (res != ESP_OK) return res;

  while (true) {
    fb = esp_camera_fb_get();
    if (!fb) { res = ESP_FAIL; break; }

    if (res == ESP_OK)
      res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
    if (res == ESP_OK) {
      size_t hlen = snprintf(part_buf, sizeof(part_buf), _STREAM_PART, fb->len);
      res = httpd_resp_send_chunk(req, part_buf, hlen);
    }
    if (res == ESP_OK)
      res = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);

    esp_camera_fb_return(fb);
    if (res != ESP_OK) break;
  }
  return res;
}

void startCameraServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;
  config.max_uri_handlers = 4;

  httpd_uri_t index_uri   = {}; index_uri.uri = "/";        index_uri.method = HTTP_GET;   index_uri.handler = index_handler;   index_uri.user_ctx = NULL;
  httpd_uri_t capture_uri = {}; capture_uri.uri = "/capture"; capture_uri.method = HTTP_GET; capture_uri.handler = capture_handler; capture_uri.user_ctx = NULL;

  if (httpd_start(&camera_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(camera_httpd, &index_uri);
    httpd_register_uri_handler(camera_httpd, &capture_uri);
    Serial.println("HTTP camera server started on port 80");
  } else {
    Serial.println("Failed to start HTTP server");
  }

  // A streaming handler owns its server task until the client disconnects.
  // Keep it on a second server so / and /capture remain responsive.
  httpd_config_t stream_config = HTTPD_DEFAULT_CONFIG();
  stream_config.server_port = 81;
  stream_config.ctrl_port += 1;
  stream_config.max_uri_handlers = 1;
  httpd_uri_t stream_uri = {}; stream_uri.uri = "/stream"; stream_uri.method = HTTP_GET; stream_uri.handler = stream_handler; stream_uri.user_ctx = NULL;
  if (httpd_start(&stream_httpd, &stream_config) == ESP_OK) {
    httpd_register_uri_handler(stream_httpd, &stream_uri);
    Serial.println("MJPEG stream server started on port 81");
  } else {
    Serial.println("Failed to start stream server");
  }
}

void setup() {
#ifdef BENCH_BUILD
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);  // mask brownout reset (USB power surge)
#endif
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();
  Serial.println("=== ELEGOO ESP32-WROVER CameraWebServer ===");

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.frame_size   = FRAMESIZE_SVGA;
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode    = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location  = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12;
  config.fb_count     = 1;

  if (psramFound()) {
    Serial.println("PSRAM found - using 2 frame buffers in PSRAM");
    config.jpeg_quality = 10;
    config.fb_count     = 2;
    config.grab_mode    = CAMERA_GRAB_LATEST;
  } else {
    Serial.println("PSRAM NOT found - limiting frame size");
    config.frame_size  = FRAMESIZE_VGA;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init FAILED with error 0x%x\n", err);
    Serial.println("If this is 0x105/0x20004, the pin map is wrong for this board.");
    return;
  }
  Serial.println("Camera init OK");

  sensor_t *s = esp_camera_sensor_get();
  if (s) {
    s->set_vflip(s, 1);    // ELEGOO mounts the OV2640 flipped
    s->set_hmirror(s, 1);
    s->set_framesize(s, FRAMESIZE_VGA);  // 640x480 = smooth stream
  }

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);

  // --- Diagnostic: scan the 2.4GHz band so we know what the board can see ---
  Serial.println("Scanning 2.4GHz WiFi networks...");
  int n = WiFi.scanNetworks();
  Serial.printf("Found %d networks (ESP32 only sees 2.4GHz):\n", n);
  bool targetSeen = false;
  for (int i = 0; i < n; i++) {
    bool isTarget = (WiFi.SSID(i) == ssid);
    if (isTarget) targetSeen = true;
    // encryptionType: 0=OPEN 2=WPA 3=WPA2 4=WPA/WPA2 5=ENT 6=WPA3 7=WPA2/WPA3
    Serial.printf("  %2d: %-28s ch%2d  %4d dBm  enc=%d %s\n",
                  i, WiFi.SSID(i).c_str(), WiFi.channel(i), WiFi.RSSI(i),
                  (int)WiFi.encryptionType(i), isTarget ? "<== YOUR NETWORK" : "");
  }
  Serial.printf(">> Target '%s' visible on 2.4GHz: %s\n",
                ssid, targetSeen ? "YES" : "NO  (it is 5GHz-only or out of range)");
  WiFi.scanDelete();

  WiFi.begin(ssid, password);
  WiFi.setSleep(false);
  Serial.printf("Connecting to WiFi '%s'", ssid);
  int tries = 0;
  while (WiFi.status() != WL_CONNECTED && tries < 40) {  // ~20s
    delay(500);
    Serial.print(".");
    tries++;
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("WiFi connected");
    Serial.print("Camera Ready! Use 'http://");
    Serial.print(WiFi.localIP());
    Serial.println("' to connect");
    Serial.print("Stream URL: http://");
    Serial.print(WiFi.localIP());
    Serial.println(":81/stream");
  } else {
    Serial.println("WiFi join FAILED (5GHz SSID? wrong pass? out of range)");
    Serial.printf("Falling back to SoftAP: SSID '%s'\n", CAMERA_AP_SSID);
    WiFi.mode(WIFI_AP);
    WiFi.softAP(CAMERA_AP_SSID, CAMERA_AP_PASSWORD);
    Serial.printf("Camera Ready! Connect to WiFi '%s' then open 'http://", CAMERA_AP_SSID);
    Serial.print(WiFi.softAPIP());
    Serial.println("'");
  }

  startCameraServer();
}

void loop() {
  // Optional heartbeat with current IP every 10s
  static unsigned long last = 0;
  if (millis() - last > 10000) {
    last = millis();
    if (WiFi.getMode() == WIFI_AP) {
      Serial.print("[AP] http://"); Serial.println(WiFi.softAPIP());
    } else if (WiFi.status() == WL_CONNECTED) {
      Serial.print("[STA] http://"); Serial.println(WiFi.localIP());
    }
  }
  delay(100);
}
