/**********************************************************************
 * Raspberry Pi Pico W + SH1106 128x64 OLED (I2C) + FluxGarage RoboEyes
 * Auto-detecting version: scans the I2C bus, finds the OLED at 0x3C or
 * 0x3D automatically, and reports status over USB serial (115200).
 *
 * WIRING (OLED 4-pin I2C -> Pico W):
 *   VCC -> 3V3(OUT) pin36   GND -> GND pin38
 *   SDA -> GP4 pin6         SCL -> GP5 pin7
 **********************************************************************/

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h>
#include <FluxGarage_RoboEyes.h>

#define SCREEN_WIDTH  128
#define SCREEN_HEIGHT 64
#define I2C_SDA       4      // GP4 (pin 6)
#define I2C_SCL       5      // GP5 (pin 7)

Adafruit_SH1106G display = Adafruit_SH1106G(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
RoboEyes<Adafruit_SH1106G> roboEyes(display);

bool eyesRunning = false;

uint8_t scanForOled() {
  uint8_t found = 0;
  Serial.print("I2C scan @SDA=GP4 SCL=GP5: ");
  bool any = false;
  for (uint8_t a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      any = true;
      Serial.print("0x"); Serial.print(a, HEX); Serial.print(" ");
      if (a == 0x3C || a == 0x3D) found = a;   // OLED addresses
    }
  }
  if (!any) Serial.print("NOTHING (check SDA/SCL/VCC/GND wires)");
  Serial.println();
  return found;
}

void setup() {
  Serial.begin(115200);
  Wire.setSDA(I2C_SDA);
  Wire.setSCL(I2C_SCL);
  Wire.begin();
}

void loop() {
  if (eyesRunning) { roboEyes.update(); return; }

  // Keep scanning + reporting until the OLED is found and inits.
  uint8_t addr = scanForOled();
  if (addr && display.begin(addr, true)) {
    Serial.print(">>> OLED OK at 0x"); Serial.print(addr, HEX);
    Serial.println(" - starting eyes!");
    display.clearDisplay();
    display.display();
    roboEyes.begin(SCREEN_WIDTH, SCREEN_HEIGHT, 100);
    roboEyes.setMood(HAPPY);
    roboEyes.setAutoblinker(ON, 3, 2);
    roboEyes.setIdleMode(ON, 2, 2);
    eyesRunning = true;
  } else {
    if (addr) Serial.println("Found OLED addr but init failed - retrying...");
    delay(1500);
  }
}
