# Hexapod — price sheet & best UK sourcing (June 2026)

> 🔁 **Superseded on power:** a later trade study (`HEXAPOD_SERVO_TRADESTUDY.md`) corrected the servo-rail voltage — regulate to a **flat 7.4 V, NOT 5–6 V** (at 6 V the 19 kg servo only makes ~15.8 kg·cm). It also found the cheap "300 W / 20 A" buck is really **~120–150 W by current limit** — you need a **real ≥40 A regulator** (likely **3S → buck-to-7.4 V**, since a 2 S buck sags under load). Treat the "reuse a cart buck for the servo rail" line below as **insufficient** for the main rail.

Best **landed UK price** (item + delivery to London E11, GBP) for the parts you still need, consolidated from live retailer pages. **Confidence:** High = price seen live · Med = strong UK ballpark · Low = dynamic/estimate. AliExpress exact "ship to UK" totals need your logged-in browser — flagged Low where used (its item prices are real, but final UK postage/VAT only shows at checkout).

## Two corrections worth knowing first

1. **Your B6neo charger is fine — you have two ways to power it.** It takes **USB-C PD (12–20V, up to 80W)** *or* DC (10–28V, up to 200W). If you own a **65–100W USB-C laptop/phone charger** + an **E-marked 5A USB-C cable**, that already runs it (80W charges a 2S 5000mAh pack easily). If not, the purpose-built **SKYRC PSA100 (20V/5A/100W, XT60 output) is £19.99 at Flying Tech UK** — plug-and-play, better than a generic brick. ([B6neo specs](https://www.skyrc.com/b6neo) · [PD note](https://blog.skyrc.com/how-to-achieve-80w-output-power-on-the-b6neo-charger-using-pd-input/))
2. **STS3215 bus cables use a 5264 2.54mm 3-pin connector — NOT JST-XH.** Buy "5264 3-pin" cables specifically (e.g. Waveshare SR-Cable-5264-3PIN). The obvious UK source (Rapid Electronics) is discontinued.

---

## A. Core "make it run" parts (beyond what you already own)

| # | Item | Best buy (confirmed) | £ | Cheapest (patient) | Conf. |
|---|------|----------------------|--:|--------------------|------|
| 1 | **Waveshare Servo Driver w/ ESP32** | [The Pi Hut UK](https://thepihut.com/products/esp32-servo-driver-with-wifi-and-bluetooth) **£15.40** (+~£3, free >£50) | ~18 | AliExpress/Waveshare ~£12 (slow) | High |
| 2 | **Feetech FE-URT-1** (set servo IDs) | [Seeed](https://www.seeedstudio.com/Feetech-FE-URT-1-p-6705.html) **$10 (~£8)** +ship | ~12–16 | AliExpress ~£10–11 | Med |
| 3 | **2S 5000mAh LiPo XT60** — *buy UK, never import* | [Overlander 35C, King's Lynn](https://www.kingslynnmodelshop.co.uk/overlander-lipo-batteries-5000mah-2s-7-4v-35c-supersport-xt60/) **£32.72** in stock | ~37 | (do not AliExpress a battery) | High |
| 4 | Servo-rail buck (2S→5–6V) | **Reuse one from your cart £0** | 0 | AliExpress ~£3–4 / Amazon UK ~£9 | High |
| 5 | 5V logic UBEC (5A) | [Hobbywing 5A, Flying Tech](https://www.flyingtech.co.uk/product/hobbywing-5a-2-8s-ubec-with-5-0v-6-0v-7-4v-output/) **£12.90** / [3DXR £10.99](https://www.3dxr.co.uk/electronics-c78/power-management-c91/voltage-regulators-becs-c101/hobbywing-m23) | ~15 | AliExpress generic ~£3–5 | High |
| 6 | XT60 PDB | [Matek XT60 PDB w/ BEC, Flying Tech](https://www.flyingtech.co.uk/product/matek-xt60-quad-pdb-with-5v-12v-bec-outputs-36x36mm/) **£7.50** | ~10 | eBay UK generic ~£5 | High |
| 7 | XT90-S anti-spark **loop key/switch** | [Unmanned Tech UK](https://www.unmannedtechshop.co.uk/products/high-load-xt90-power-supply-switch-because-unplugging-is-for-amateurs) **£3.49** (real integrated switch) | ~6 | AliExpress Amass pair ~£5 (DIY) | High |
| 8 | RC watt meter (130–150A, XT60) | [Flying Tech 100/150A](https://www.flyingtech.co.uk/product/100-150a-0-60v-high-precision-in-line-watt-meter-power-analyser/) **£14.60–16.99** / [Keenstone Amazon](https://www.amazon.co.uk/Keenstone-Precision-Consumption-Performance-Measurement/dp/B06Y5DDK6N) ~£18 (XT60 incl) | ~15–21 | AliExpress ~£6–9 | High |
| 9 | STS3215 **5264** 3-pin bus cables | [Waveshare SR-Cable-5264-3PIN](https://www.waveshare.com/product/accessories/motors-servos.htm) 5pk **~£10** | ~13–16 | AliExpress 10pk ~£4–8 | High |
| 10 | Charger power source (only if not owned) | **SKYRC PSA100, [Flying Tech £19.99](https://www.flyingtech.co.uk/product/skyrc-psa100-20v-5a-100w-power-supply-adapter-with-xt60/)** — or a 100W USB-C PD charger you own (£0) | 0–24 | — | High |

**Section A (UK, fast, genuine): ~£120–140 landed** (less if you already own a PD charger; less FE-URT-1 if you ID servos via the driver board).

## B. Connect / assemble / debug consumables & tools

| # | Item | Best source | £ | Conf. |
|---|------|-------------|--:|------|
| 14 | Ratcheting crimp tool (IWISS SN-2549) | [Amazon UK](https://www.amazon.co.uk/IWISS-Crimping-0-08-1-0-Ratcheting-Connector/dp/B01N4L8QMW) | ~17 | Low |
| 15 | Dupont/JST connector + pin kit | [Amazon UK](https://www.amazon.co.uk/Connector-Housing-Connectors-Terminal-Assortment/dp/B09NBT7D9P) / AliExpress | ~10 | Low |
| 16 | M3 heat-set inserts ×100 + iron tip | Amazon UK (2 items) | ~14 | Low |
| 17 | M2×6 screws ×100 | Amazon UK / AliExpress | ~6–7 | Low |
| 18 | M3 button-head + nyloc + washers | [Amazon UK 540pc](https://www.amazon.co.uk/Assorted-Nyloc-Washers-A2-70-Stainless/dp/B01CO9S1RI) / Monkeyjams | ~12–16 | Low |
| 19 | Loctite 243 threadlocker (5ml) | [Amazon UK](https://www.amazon.co.uk/Loctite-1831701-1370535-Locking-Medium/dp/B00D1KV23U) **£6.49** | 6.49 | High |
| 20 | 2S LiPo low-voltage alarm | Amazon UK / AliExpress | ~7 | Low |
| 21 | Inline blade-fuse holders (16AWG) + fuse kit | Amazon UK | ~9 | Low |
| 22 | Precision hex drivers + 150mm calipers | Amazon UK (both) | ~21 | Low |

**Section B (Amazon UK, batched for free shipping): ~£105–115** — but much of this you may already own (soldering iron, calipers, drivers).

## C. Recommended add-ons

| Item | Cheapest | Fast UK | Conf. |
|------|----------|---------|------|
| MPU6050 IMU | AliExpress ~£1 | [eBay UK ~£2.70](https://www.ebay.co.uk/itm/183422707701) / Amazon ~£4–5 | Med |
| VL53L0X ToF | AliExpress ~£4.50 | Amazon UK ~£6–8 / [Pi Hut Adafruit ~£15](https://thepihut.com/products/adafruit-vl53l0x-time-of-flight-distance-sensor-30-to-1000mm) | Med |
| Spare STS3215 (1) | AliExpress ~£11–14 | [RobotShop UK £26.30](https://uk.robotshop.com/products/magnetic-encoding-servo-sts3215-74v-19kgcm) / [Seeed $20](https://www.seeedstudio.com/STS3215-19kg-cm-7-4V-Serial-Servo-p-6338.html) | Med |

---

## Where each £ is best spent
- **UK retailers genuinely WIN (price + speed + genuine parts):** PDB (Matek £7.50), UBEC (Hobbywing £12.90), XT90-S loop key (£3.49), ESP32 driver (Pi Hut £15.40), watt meter, **the LiPo (mandatory — never air-freight a battery)**, Loctite. Flying Tech is the standout shop for the power bits.
- **AliExpress worth it only if you consolidate ONE order** (amortise shipping + 2–4wk wait): FE-URT-1, 5264 bus cables, MPU6050, VL53L0X, screws/inserts/connectors. Unit prices £1–3 lower; usually erased by shipping on small separate orders.
- **Never AliExpress:** the LiPo battery.
- **Watch import VAT:** non-UK orders (Seeed/Waveshare from China) over ~£135 can attract 20% VAT + handling on entry — factor into "landed".

## Grand totals (additional spend beyond what you own)
| Scenario | Approx landed £ |
|----------|-----------------|
| **Minimum-viable**, UK-fast (Section A core + essential tools you lack) | **~£130–170** |
| **Recommended** (A + B + MPU6050 + ToF + 1 spare servo) | **~£210–270** |
| **Patient/cheapest** (AliExpress for everything shippable, LiPo + charger still UK) | **~£100–140** + 2–4wk wait |

Biggest single line is the **LiPo (~£37)**. Biggest *optional* swing is tools you may already own (crimp tool, calipers, soldering iron ≈ £55).

*All AliExpress and Amazon figures load dynamically and weren't all fetch-confirmable; Low-confidence rows are market ballparks — verify the live "ship to United Kingdom" total in your browser before buying.*
