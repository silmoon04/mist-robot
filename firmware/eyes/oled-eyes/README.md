# Robot eyes — SH1106 OLED + Raspberry Pi Pico W (FluxGarage RoboEyes)

Animated robot eyes for the spider/hexapod.
**Board: Raspberry Pi Pico W** · **OLED: 4-pin I2C** (GND/VCC/SCL/SDA).
Sketch: [`SpiderRoboEyes_PicoW/SpiderRoboEyes_PicoW.ino`](SpiderRoboEyes_PicoW/SpiderRoboEyes_PicoW.ino)

> Why Pico W and not the ESP32 we had: that ESP32 only exposed VCC/GND/TX/RX (UART/flash pins),
> which can't cleanly run I2C. The Pico W breaks out plenty of GPIO + hardware I2C.

## Wiring (4 wires, direct jumpers — no breadboard)
| OLED | Pico W | Pico physical pin |
|---|---|---|
| VCC | 3V3(OUT) | **pin 36** |
| GND | GND | **pin 38** (or 3/8/13/…) |
| SDA | GP4 | **pin 6** |
| SCL | GP5 | **pin 7** |

I2C address **0x3C** (try 0x3D if blank). GP4/GP5 = I2C0, the arduino-pico `Wire` default.

## ⚠️ SH1106 ≠ SSD1306
Use **Adafruit_SH110X** (`Adafruit_SH1106G`) — it applies the SH1106 +2-px column offset. A plain
SSD1306 driver shifts the image 2 px and wraps. RoboEyes ≥ v1.1.0 is a template → works with
`Adafruit_SH1106G` directly.

## Board package + libraries
- Boards Manager: **"Raspberry Pi Pico/RP2040" by Earle Philhower** (arduino-pico). Index URL:
  `https://github.com/earlephilhower/arduino-pico/releases/download/global/package_rp2040_index.json`
- Library Manager: **FluxGarage RoboEyes** (1.1.x) · **Adafruit SH110X** (pulls Adafruit GFX + BusIO).

## Flash (arduino-cli)
```sh
arduino-cli core update-index --additional-urls https://github.com/earlephilhower/arduino-pico/releases/download/global/package_rp2040_index.json
arduino-cli core install rp2040:rp2040
arduino-cli lib install "FluxGarage RoboEyes"
arduino-cli lib install "Adafruit SH110X"
# Hold the Pico's BOOTSEL button while plugging in USB for the first flash, then:
arduino-cli compile -u --fqbn rp2040:rp2040:rpipicow firmware/eyes/oled-eyes/SpiderRoboEyes_PicoW
```

## Troubleshooting
- **Blank:** check VCC=3V3 + GND; try address **0x3D**; confirm SDA=GP4 (pin6), SCL=GP5 (pin7).
- **Image shifted 2 px / wrapped:** you used an SSD1306 driver — switch to `Adafruit_SH1106G`.
- **Upload fails / no port:** hold **BOOTSEL** while connecting (Pico mounts as RPI-RP2 drive), then upload.

## Alternative: ESP32 + 7-pin SPI OLED
Preserved at [`SpiderRoboEyes/SpiderRoboEyes.ino`](SpiderRoboEyes/SpiderRoboEyes.ino) — wiring
SCK=18, SDA(MOSI)=23, RES=17, DC=16, CS=5 (WROVER boards: use 25/26 for DC/RES).
