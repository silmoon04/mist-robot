/**********************************************************************
 * Pico W I2C pin-pair scanner — finds which pins your OLED is wired to.
 * Prints over USB serial @115200. Looks for the OLED at 0x3C / 0x3D on
 * every valid I2C0 (Wire) and I2C1 (Wire1) pin pair.
 **********************************************************************/
#include <Wire.h>

struct Pair { TwoWire* bus; uint8_t sda; uint8_t scl; const char* name; };

Pair pairs[] = {
  { &Wire,   4,  5, "Wire  SDA=GP4  SCL=GP5   (pins 6/7)"   },
  { &Wire,   0,  1, "Wire  SDA=GP0  SCL=GP1   (pins 1/2)"   },
  { &Wire,   8,  9, "Wire  SDA=GP8  SCL=GP9   (pins 11/12)" },
  { &Wire,  12, 13, "Wire  SDA=GP12 SCL=GP13  (pins 16/17)" },
  { &Wire,  16, 17, "Wire  SDA=GP16 SCL=GP17  (pins 21/22)" },
  { &Wire,  20, 21, "Wire  SDA=GP20 SCL=GP21  (pins 26/27)" },
  { &Wire1,  2,  3, "Wire1 SDA=GP2  SCL=GP3   (pins 4/5)"   },
  { &Wire1,  6,  7, "Wire1 SDA=GP6  SCL=GP7   (pins 9/10)"  },
  { &Wire1, 10, 11, "Wire1 SDA=GP10 SCL=GP11  (pins 14/15)" },
  { &Wire1, 14, 15, "Wire1 SDA=GP14 SCL=GP15  (pins 19/20)" },
  { &Wire1, 26, 27, "Wire1 SDA=GP26 SCL=GP27  (pins 31/32)" },
};

void setup() {
  Serial.begin(115200);
  delay(1500);
}

void loop() {
  Serial.println("\n=== I2C pin-pair scan (looking for OLED at 0x3C / 0x3D) ===");
  bool any = false;
  for (auto &p : pairs) {
    p.bus->end();
    p.bus->setSDA(p.sda);
    p.bus->setSCL(p.scl);
    p.bus->begin();
    delay(15);
    String hits = "";
    for (uint8_t a = 1; a < 127; a++) {
      p.bus->beginTransmission(a);
      if (p.bus->endTransmission() == 0) { hits += " 0x"; hits += String(a, HEX); }
    }
    Serial.print(p.name); Serial.print("  -> ");
    if (hits.length()) { Serial.println("FOUND:" + hits); any = true; }
    else Serial.println("(nothing)");
  }
  if (!any) Serial.println(">>> Nothing on ANY pair = check VCC=3V3, GND, and that the 2 data wires are firmly seated.");
  else Serial.println(">>> A line showing 0x3c is your OLED -> those are the pins to use.");
  delay(3000);
}
