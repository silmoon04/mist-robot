# Video component audit

Source: `<LOCAL_HOME>\Downloads\Telegram Desktop\VID_20260729_234649_8K.mp4`

The source is a 53.9-second HEVC phone video recorded at 7680 × 4320 (with portrait rotation metadata). It was read only. This audit is based only on visible pixels; no browser, order-history, or account data was inspected.

Timestamps are approximate to the nearest second because the survey frames were sampled from a moving camera. Presence can be established visually, but packaged quantities, electrical ratings, connector pinout, and working condition cannot.

## Strongest evidence images

- `crops/00s_servos_xt60_and_mat.jpg` — FEETECH C018 cartons, XT60 pigtails, cutting mat
- `crops/00s_soldering_tools_and_jumpers.jpg` — soldering kit and Dupont jumper ribbon
- `crops/10s_battery_charger_power_and_meter.jpg` — LiPo/power group, B6 Neo, four DC-DC boards, tools and meter
- `crops/10s_four_power_modules_closeup.jpg` — the four matching DC-DC/UBEC-like boards
- `crops/12s_hoovo_lipo_and_b6neo_charger.jpg` — HOOVO LiPo and B6 Neo charger
- `crops/22s_logic_servo_adapters_and_esp32.jpg` — FE-URT board, Bus Servo Adapter A, ESP32 boards and inline fuse holders
- `crops/30s_power_conversion_fusing_and_hardware.jpg` — fusing, power distribution and hardware organisers
- `crops/34s_xt60_heatshrink_and_servo_cables.jpg` — XT60 leads, heat-shrink, braided sleeve and likely 5264 leads
- `crops/53s_all_items_overview.jpg` — widest, sharpest overview of the complete floor layout

The `full_frames/` folder contains seven 8K source-derived JPEG frames. The `survey/` folder contains the sampling frames and two contact sheets.

## Visible inventory

| Time | Visible item | Confidence | Distinctive appearance / limit |
|---:|---|---|---|
| 0–4 s | FEETECH C018 servo cartons | High | Large stack of small white/black cartons with red FEETECH logo and `C018` marking. The cartons are clear; the exact carton count is partly obscured and should not be inferred from this frame. |
| 0–4 s | XT60 power pigtails | High | Multiple clear bags containing yellow XT60 plugs on red/black heavy-gauge leads. |
| 0–4 s | Soldering kit | High | Blue-edged zip case containing an orange-handled iron, spring stand, solder reel, blue-handled cutters/pliers and small consumables. |
| 0–4 s | Dupont jumper-wire ribbon | High | Straight multicolour rainbow ribbon with black individual connector housings at both ends. |
| 10–16 s | HOOVO LiPo battery | High | Black shrink-wrapped rectangular pack with red/white HOOVO label, separate balance lead and yellow XT60 main plug. Label is consistent with the user's 3S/11.1 V pack, but fine-print capacity is not relied on here. |
| 10–16 s | ISDT B6 Neo charger | High | Compact red-and-turquoise charger with colour LCD and three black triangular buttons; screen is powered in the video. |
| 10–30 s | Four matching DC-DC/UBEC-like power boards | Medium-high | Four exposed dark PCBs, each with red/black input/output leads, a large round silver can and two yellow components. Presence and matching form are clear; output voltage/current and exact model are not legible. |
| 10–30 s | Digital multimeter and probes | High | Red `SZ308`-marked meter with rotary selector and red/black test leads. Video cannot establish whether its battery is fitted or whether it works. |
| 10–30 s | Flush cutter / wire tools | High | Red-and-black handled diagonal cutter plus another red/black hand tool in the power group. |
| 10–30 s | Yellow multi-output power distribution board | Medium-high | Narrow black PCB with a large yellow input connector and a row of smaller yellow outputs. Connector family and current rating need checking against the order page or PCB markings. |
| 10–30 s | Automotive blade-fuse assortment | High | Clear compartment box with colour-coded automotive blade fuses. |
| 10–30 s | Silicone power wire | High | Thick loose red and black cable coils/lengths near the LiPo and XT60 pigtails. Gauge is not readable from the video. |
| 21–25 s | FE-URT servo interface board | High | Red rectangular PCB with USB connector, slide switch, multiple white JST-style sockets and blue 4-way screw terminal; `TTL-Bus` and `RS485-Bus` silkscreen is visible. |
| 21–25 s | Bus Servo Adapter A | High | Small black square PCB with barrel jack, green 2-way screw terminal, USB connector and white sockets; `Bus Servo Adapter A` silkscreen is visible. |
| 21–25 s | ESP32 development board | High | Long black DevKit-style PCB with large metal ESP32 RF module and USB connector. |
| 21–25 s | ESP32-CAM board | High | Small black camera PCB with exposed lens and flex connector, beside the ESP32 DevKit. |
| 21–25 s | Pocket scale | High | Black flip-cover scale with rectangular LCD and two buttons. |
| 21–25 s | Inline automotive blade-fuse holders | High | Clear bag containing several black inline holders on red cable loops with green blade fuses visible. Their presence is clear; whether the assembled lead is the intended “smoke stopper” requires wiring/continuity inspection. |
| 28–32 s | Small screw assortment | High for presence; medium for sizes | Clear multi-compartment box of small silver machine screws separated by length. M2 is visually plausible, but exact diameters and lengths cannot be read. |
| 28–32 s | Washer / spacer assortment | High | Clear compartment box with flat white/grey rings and spacers in several diameters. Material and sizes are not confirmed. |
| 28–34 s | Servo-extension leads | High | Large bag of conventional red/white/black three-core servo extensions with black housings. These are visually distinct from the long all-black leads below. |
| 34–36 s | Long black, white-ended servo-bus leads — likely the sought FEETECH 5264 cables | Medium-high | A white tray contains many long black flat leads terminated in small white keyed housings. They strongly match the expected FEETECH-style bus leads. The video cannot prove the housing key or pin order, so compare one physically with a C018/FE-URT socket before power is applied. |
| 34–44 s | Heat-shrink tubing | High | Several clear/anti-static bags of short black tube pieces plus long red/black heat-shrink or wire packs. |
| 34–44 s | Braided cable sleeve | High | Flat black woven sleeve on a large round roll. |
| 34–44 s | Black cable ties | High | Bundled black zip ties in clear bags. |
| 44–53 s | Threadlocker | High | Red/blue LOCTITE threadlocker blister pack. |
| 44–53 s | USB and loose black cables | Medium-high | Multiple coiled black cables are visible in the wide overview; connector ends and counts are not consistently exposed. |
| 44–53 s | Blue cutting mat | High | Small blue gridded craft mat at the edge of the layout. |

## Important findings

1. The long black leads with small white connectors in the white tray at about 34 seconds are very likely the “5264 cables” that were thought missing. Treat that identification as provisional until one connector is compared directly with the keyed socket and its three conductors/pin order are checked.
2. The video clearly supports presence of the FE-URT interface, Bus Servo Adapter A, an ESP32 DevKit, C018-labelled servo cartons, B6 Neo charger, a HOOVO LiPo, inline fuse holders, XT60 leads, silicone wire, hand tools, and small hardware.
3. The video does **not** reliably prove: exact servo count, presence of both LiPos in the same frame, M2/M3/M4 sizes, cable pinout, fuse ratings, DC-DC output voltage, multimeter readiness, or electrical continuity.
4. Do not connect a LiPo or servo from image matching alone. Verify polarity and output voltage with a functioning multimeter, and confirm the FEETECH lead key/pin order before applying power.
