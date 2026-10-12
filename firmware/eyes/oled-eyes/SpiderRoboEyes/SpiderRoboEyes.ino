/**********************************************************************
 * ESP32 + SH1106 128x64 OLED (4-wire HARDWARE SPI) + FluxGarage RoboEyes
 * Animated robot eyes: auto-blink, idle look-around, and a mood.
 *
 * Libraries (Arduino Library Manager):
 *   - FluxGarage RoboEyes   v1.1.1   (>=1.1.0 required: it's a template class)
 *   - Adafruit SH110X       v2.1.x   (pulls in the two below automatically)
 *   - Adafruit GFX Library  v1.12.x
 *   - Adafruit BusIO        v1.17.x
 * Board package: esp32 by Espressif (Arduino-ESP32 core 3.x)
 *
 * WIRING (OLED pin -> ESP32 GPIO):
 *   GND -> GND        VDD -> 3V3 (NOT 5V; ESP32 logic is 3.3V)
 *   SCK -> GPIO18     SDA(MOSI) -> GPIO23   (hardware VSPI; fixed)
 *   RES -> GPIO17     DC -> GPIO16          CS -> GPIO5  (any free GPIO)
 *
 * !!! IMPORTANT - WROVER boards: GPIO16/17 are used by the PSRAM on
 *     ESP32-WROVER modules. If you use a WROVER (e.g. a cam board), change
 *     OLED_DC/OLED_RST below to free pins like 25/26/27. Plain WROOM = 16/17 OK.
 **********************************************************************/

#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h>          // SH1106 driver (NOT Adafruit_SSD1306!)
#include <FluxGarage_RoboEyes.h>      // template class RoboEyes<AdafruitDisplay>

#define SCREEN_WIDTH  128
#define SCREEN_HEIGHT 64

// The 3 control pins you wire yourself (MOSI=23 / SCLK=18 are implicit HW-SPI):
#define OLED_DC   16   // -> OLED "DC"   (use 25 on WROVER)
#define OLED_RST  17   // -> OLED "RES"  (use 26 on WROVER)
#define OLED_CS    5   // -> OLED "CS"

// Hardware-SPI constructor: (w, h, &SPIClass, dc, rst, cs)
Adafruit_SH1106G display = Adafruit_SH1106G(
    SCREEN_WIDTH, SCREEN_HEIGHT, &SPI, OLED_DC, OLED_RST, OLED_CS);

// RoboEyes (v1.1+) is a template; instantiate on our display type.
RoboEyes<Adafruit_SH1106G> roboEyes(display);

void setup() {
  Serial.begin(115200);

  // 1) Init the display FIRST (RoboEyes.begin() draws to it immediately).
  //    For SH110X, begin(addr, reset): addr is ignored on SPI -> pass 0.
  if (!display.begin(0, true)) {
    Serial.println(F("SH1106 init failed - check wiring/pins"));
    for (;;);
  }
  display.clearDisplay();
  display.display();

  // 2) Init RoboEyes: begin(width, height, maxFramerate)
  roboEyes.begin(SCREEN_WIDTH, SCREEN_HEIGHT, 100);

  // 3) Mood + life-like automatic behaviour
  roboEyes.setMood(HAPPY);             // DEFAULT, TIRED, ANGRY, HAPPY
  roboEyes.setAutoblinker(ON, 3, 2);   // blink every ~3s (+/- up to 2s)
  roboEyes.setIdleMode(ON, 2, 2);      // look around every ~2s (+/- 2s)
  // roboEyes.setCuriosity(ON);        // outer eye grows when looking aside
}

void loop() {
  roboEyes.update();                   // redraw (self rate-limited); no delay() here
}
