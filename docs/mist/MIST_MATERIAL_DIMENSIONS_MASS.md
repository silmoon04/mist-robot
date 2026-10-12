# MIST material dimensions and mass guide

Generated 2026-07-08 from the actual ordered inventory, local CAD notes, and subagent datasheet/listing research.

Use this for CAD placeholder boxes, weight budgeting, part intake checks, and deciding what must be weighed when it arrives. Dimensions are `L x W x H` in mm unless noted. Estimated values must be replaced with caliper/scale measurements during Phase 1.

Related docs:

- `docs/mist/MIST_ACTUAL_INVENTORY.md` - what was actually ordered.
- `docs/mist/MIST_BUILD_PHASES.md` - build order and hard gates.
- `docs/mist/MIST_CAD_CHECK_PIPELINE.md` - CAD/export/mass-check workflow.

## Mass budget snapshot

| Bucket | Mounted estimate | Notes |
|---|---:|---|
| Printed PETG/TPU kit v1 | ~1740 g | From `MIST_CAD_CHECK_PIPELINE.md`; includes printable chassis/barrel/legs/wheels/phone frame. Needs rerun after CAD v2. |
| 16 installed STS3215 servos | ~880 g | 16 x 55 g. Ordered 18 total = ~990 g stock. |
| One mounted 3S LiPo | ~174 g | One HOOVO pack mounted at a time; second pack is spare/charged swap. |
| Phone payload | 155 g phone only; ~200-210 g with frame/straps | Frame is already inside printed-kit mass if using v1 printed estimate. |
| Mounted electronics and harness | ~480-600 g | PDB, adapter, ESP32, UBEC, fuses, pigtails, caps, wire, solder, heat shrink, ties. Wire/strap mass is still uncertain because raw silicone wire/straps are not proven in orders. |
| Expected all-up robot | ~3.25-3.55 kg | Heavier than the early 2.65 kg concept. Treat mass reduction as a v2 CAD priority. |

Important: do not double-count the printed phone frame if using the printed-kit total. The phone itself is separate.

## Mounted / assembly-critical items

| Item | Ordered qty | Expected mounted qty | Size / envelope | Unit mass | Mounted mass | Confidence | Source / evidence | Assembly notes |
|---|---:|---:|---|---:|---:|---|---|---|
| Feetech STS3215 12V 30kg servo, ST-3215-C018 | 18 | 16 | 45.2 x 24.7 x 35 | 55 g | 880 g | High | Feetech listing: `https://www.feetechrc.com/products.html?keyword=STS3215`; Seeed/Kamami ST3215-C047 datasheet lists 45.2 x 24.7 x 35 mm. | Verify every servo is the 12V/30kg variant before raw 3S power. Label IDs before multi-servo wiring. |
| Spare STS3215 servos | 2 | 0 | Same as above | 55 g | 0 g | High | Same as above. | Keep one known-good golden spare after ID/register testing. |
| Bus Servo Adapter A | 1 | 1 | 42 x 33 PCB, height not specified | ~16 g | ~16 g | Medium | Waveshare docs: `https://docs.waveshare.com/Bus_Servo_Adapter_A`; Botland listing for weight. | Signal/common-ground interface only. Do not carry leg servo current through this board. |
| ESP32 DevKitC / WROOM-32 CP2102 Type-C | 1 | 1 | likely 54.8 x 28.6 PCB, height ~10-13 | ~10 g | ~10 g | Medium | Espressif DevKitC overview; generic CP2102 Type-C board listings. | Confirm 30-pin vs 38-pin when it arrives. Power from UBEC 5V or USB, not both unless USB 5V is blocked/isolated. |
| VL53L0X breakout | 1 | 1 | generic breakout varies; Adafruit 21 x 18 x 2.8, Pololu 13 x 18 x 2 | 0.5-1.3 g typical; use 5 g CAD allowance | ~5 g | Medium | Adafruit: `https://www.adafruit.com/product/3317`; Pololu: `https://www.pololu.com/product/2490`; ST datasheet. | Measure actual AliExpress board before designing final mount. Keep sensor window clear. |
| FPV 5V 5A UBEC | likely 4 modules | 1 | typical 43 x 21 x 8 | ~18 g | ~18 g | Medium | Similar RC 5A UBEC listings; actual ordered module must be measured. | Logic 5V only. Verify 4.9-5.2V output with multimeter before ESP32/sensors. |
| XT60-to-8xXT30 PDB, 100A listing | 1 | 1 | ~45 x 45 x 18 | ~24 g | ~24 g | Low/medium | Similar XT60/XT30 PDB listings. | Main raw-3S distributor. Meter polarity on every XT30 output before loads. |
| HOOVO 3S 2200mAh 11.1V 50C XT60 LiPo | 2 packs | 1 removable pack | ~104 x 34.5 x 24.5 | ~174 g | ~174 g | Medium | Amazon HOOVO 3S 2200mAh XT60 listings; verify on arrival. | Mount one pack at a time. Charge/store in LiPo bag. Do not strap with tape only. |
| XT90-S anti-spark extension / loop | 1 | 1 | cable often 300 mm; connector ~25 x 20 x 10 | ~70 g | ~70 g | Low/medium | Similar XT90-S 10AWG extension listings; RS PRO XT90S connector datasheet. | Reachable main disconnect/anti-spark. If the lead is too long, shorten/rebuild after proving polarity. |
| XT30 16AWG pigtail pairs | 10 pairs | ~4 pairs initially | 100 mm lead length typical; XT30 body ~13.5 x 8 x 4.5 | ~10 g/pair | ~40 g | Medium | XT30 pigtail and XT30 connector specs. | Keep XT30 as raw 3S only in this build. Extra pairs are spares/test leads. |
| XT60 14AWG pigtail pairs | 5 pairs | 1-2 pairs | ~100 mm lead length typical; XT60 body ~15.5 x 7.9 | ~18 g/pair | ~18-36 g | Medium | Similar XT60 14AWG pigtail listings. | Good for adapters/spares. Main trunk should stay short and use heavier wire where practical. |
| Inline blade fuse holders | 5 | 5 | body ~45 x 20 x 15; loop lead often ~300 mm | ~35 g | ~175 g | Medium | Similar 12AWG waterproof inline blade fuse holder listings. | Mount 1 main + 4 branch holders. Main fuse close to battery. Verify actual holder wire gauge; actual inventory line showed possible 18AWG mismatch. |
| Standard ATO/ATC blade fuses | 50 pc set plus holder fuses | 5 installed | ~19.1 x 18.7 x 5.1 | ~1.4 g | ~7 g | High | Littelfuse ATOF / Eaton ATC datasheets. | Use 30A main and 15A per-leg branch after verifying holder/fuse size. |
| 4700uF 25V electrolytic capacitors | 10 | 4 | typically 16 dia x 25-30 tall | ~4 g | ~16 g | Medium | Tayda/Sharvi 4700uF 25V listings. | One at each leg root across V+/GND, never inline. Observe polarity. |
| 5264-3PIN ST/SC/CF servo leads | likely 18 | 16-18 | ordered listing says 300/900 mm options; actual length unknown | measure on arrival | TBD | Low | Ordered as 3 packs of 6. | Must fit STS3215 bus ports. Generic PWM servo extensions do not count. Signal path only if V+ is isolated where needed. |
| Heat shrink, solder, wire ties, tape | kits/rolls | cut pieces only | cut to fit | likely 20-40 g total mounted | 20-40 g | Low | Ordered kits. | Count applied pieces only. These matter less than wire/fuse-holder mass but still add up. |
| Raw 12/14/16AWG silicone wire | not proven | needed | route-specific | TBD | TBD | Missing/unproven | `docs/mist/MIST_ACTUAL_INVENTORY.md` still marks this missing. | Pigtails alone are not enough for a clean harness. Buy/confirm raw red/black silicone wire before final harness. |
| M2/M3 machine fasteners and nyloc nuts | not proven | needed | route-specific | TBD | TBD | Missing/partial | Washers/self-tappers ordered, but machine screws/nuts not proven. | Self-tappers are prototype coverage only. Final leg/frame joints likely need M2/M3 machine screws and M3 nylocs. |
| Battery/phone straps | not proven | at least 2-3 | typical useful strap: 20 x 250 | ~3-6 g each | ~6-18 g | Missing/unproven | Strap listed in earlier context but not in actual inventory. | 250 mm works across phone width, not lengthwise. Use two cross-straps or strap plus printed lip. Tape is not enough for LiPo retention. |

## Phone payload and camera/sensor package

| Item | Qty | Size / envelope | Unit mass | Mounted mass | Confidence | Source / evidence | Assembly notes |
|---|---:|---|---:|---:|---|---|---|
| Xiaomi Mi 9 SE / `grus` phone | 1 | 147.5 x 70.5 x 7.45 | 155 g | 155 g | High | Xiaomi Mi 9 SE specs, DeviceSpecifications, Notebookcheck. | Use naked-phone envelope. Add clearance for case, foam, USB plug, or protective lip. |
| Historical phone-frame placeholder | 1 | reported pocket 71.5 x 148.5 x 8.5; reported frame envelope about 90 x 12 x 170 | unknown | unknown | Low | Missing `mist_3d/tools/build_printable.py` and `mist_3d/printable_v1/phone_frame.stl`; figures survive only in older notes. | Do not reproduce as a final interface. Measure the phone, case/foam, USB plug and removal path, then rebuild the pocket with named clearances. |
| Phone + frame + straps package | 1 | about 90 x 12 x 170 plus phone | ~200-210 g | ~200-210 g | Medium | Local CAD/subagent estimate. | Mount low and on centerline. A ~205 g front phone package shifts CoM forward several mm on a ~3.2 kg robot. |
| Acrylic triangle mirror stickers | 50 pcs | nominal 5 cm triangle; thickness unknown | ~1.3-1.8 g each estimate | optional | Low/medium | Ordered 5 cm triangle mirror stickers; generic acrylic mirror data. | Fine for cosmetic eyes. For camera periscope, bond to a rigid flat plate; seams and flexible adhesive will distort images. |
| Phone cameras and sensors | included | same phone envelope | included | included | High for phone specs | Xiaomi Mi 9 SE specs; `tools/sensors/README.md`. | Phone has IMU/gyro/compass/GPS and cameras. Rigid mount for IMU. Keep compass away from motor currents, magnets, speaker, and power wiring. |

## Bench-only tools and safety gear

These are ordered or owned, but should not be counted in robot mounted mass.

| Item | Qty | Size / envelope | Weight / capacity | Confidence | Assembly notes |
|---|---:|---|---|---|---|
| Feetech FE-URT-1 USB adapter | 1 | 55.8 x 36.6 x 11.5 | 12.5 g | High | Bench tool for servo ID/register/sweep testing. Not mounted. Source: FE-URT-1 manual PDF. |
| SKYRC B6Neo charger | 1 | 70 x 50 x 32 | ~82 g | High | Bench-only LiPo balance charger. Source: SkyRC manual/reviews. |
| VOANZO/Qwinout XT60/XT30 smoke stopper | 1 | ~45 x 30 x 20 estimate | ~30 g | Low/medium | Bench/static-test only. Use for first power-up and ID scan; bypass before motion/load. |
| LiPo guard bag | 1 | 185 x 75 x 60 | ~75-85 g estimate | Medium | Bench-only for charge/storage/transport. Fits one 2200mAh pack comfortably. |
| HANDSKIT soldering iron kit | 1 | kit-specific | tool | Medium | Bench-only. Use separate 63/37 solder for key power joints. |
| ANENG SZ308 multimeter | 1 | handheld | tool | Medium | Bench-only for voltage, polarity, continuity, UBEC checks. |
| Digital caliper | 1 | 150 mm range | tool | Medium | Bench-only. Measure servo ears, horn spline/hole spacing, printed coupons, shipped boards. |
| Kitchen scale | 1 | about 186 x 145 x 15.5 | 10 kg / 1 g | Medium/high | Bench-only. Use for subassemblies and final robot mass. |
| Precision pocket scale | 1 | about 125 x 60 x 20 | 1000 g / 0.1 g ordered | Medium | Bench-only. Use for screws, washers, caps, small printed parts. |
| Wire stripper/cutter | 1 | about 218 x 124 | tool | Medium | Bench-only. Test strip length on scrap wire before touching battery leads. |
| Safety goggles | 1 | product-specific | PPE | Medium | Bench-only. If lenses are too dark for soldering/inspection, get clear glasses. |
| A4 cutting mat | 1 | A4 | tool | Medium | For cutting only. Not a hot soldering surface. |

## Consumables and stock material

| Item | Ordered / owned qty | Usable material | Density / length | Robot mass rule | Notes |
|---|---:|---:|---|---|---|
| Creality PETG white 1.75mm | 1 kg | 1000 g | PETG ~1.27 g/cm3; about 327-329 m for 1.75 mm filament | Count slicer/CAD part mass only | Main structural material. A historical, currently unreproducible printable-kit report estimated ~1.74 kg, so do not assume one spool is sufficient; use the new slicer total plus coupon/reprint allowance. |
| JAYO TPU 95A black 1.75mm | 0.5 kg | 500 g | TPU ~1.21-1.24 g/cm3; about 168 m for 1.75 mm filament | Count printed tire/pad mass only | Enough to start tires/feet/strain relief. Failed tire iterations may require another spool. |
| PLA already owned | ~3 kg | ~3000 g | PLA ~1.24 g/cm3; about 330-335 m/kg | Prototype only unless deliberately accepted | Use freely for coupons and prototypes. Do not use PLA for final servo pockets or heat/load parts. |
| 63/37 rosin solder 0.8mm | 50 g + 20 g backup | 70 g stock | Sn63Pb37 eutectic, melts ~183 C | Only a few grams mounted | Leaded solder: ventilate, wash hands, no food at bench. |
| Desoldering braid | 1 roll | 3 mm x 1.5 m ordered | copper braid | normally 0 mounted | Rework consumable. |
| Heat shrink kit | 1 kit | cut lengths | sizes vary | count applied sleeves only | Put heat shrink onto wire before soldering connectors. |
| Cable organizer tie roll | 5 m | cut lengths | hook/loop | count applied ties only | Good for serviceable strain relief. |
| Double-sided tape | 5 m x 20 mm x 1 mm ordered | cut strips | adhesive tape | count applied strips only | Temporary/light module mounting only; not for battery retention. |
| Washer assortment M2-M10 | 180 pcs | selected washers | steel | count installed washers | Useful for printed plastic clamp loads. Does not replace screws/nuts. |
| M2 self-tapping screw assortment | 1 kit | selected screws | steel | count installed screws | Prototype/self-tap only. Avoid over-tightening printed plastic. |

## Intake measurement checklist

Measure these as soon as packages arrive and write the real values back into this file or a build log:

1. STS3215 label/variant, body size, ear thickness, ear hole spacing, horn spline, horn screws, included cable length.
2. HOOVO pack actual `L x W x H`, weight, connector polarity, cell voltages.
3. XT90-S cable actual wire gauge, length, connector orientation, weight.
4. PDB dimensions, mounting holes, polarity at each XT30 output.
5. UBEC output voltage under no load and with a small 5V load; actual size/weight.
6. Fuse holder wire gauge and actual blade fuse size. If shipped holders are 18AWG, do not treat them as high-current 12AWG branch wiring.
7. 5264 cable plug fit and length. Mark any cable that is signal-only or has V+ isolated.
8. Phone actual dimensions with any case/foam/protector and the USB cable plugged in.
9. Printed coupon masses from slicer and actual scale weight after printing.

## Open mass risks

- A historical printable-kit report estimated ~1.74 kg printed and ~3.2 kg
  total. The source geometry/tooling is absent, so treat this as a warning to
  control mass, not as a reproduced current estimate.
- One 1 kg PETG spool is likely not enough for the complete v1 printed kit if most parts are final PETG.
- Fuse holders may be heavier than expected and may ship with the wrong wire gauge.
- Raw silicone wire, machine fasteners, nyloc nuts, and real straps are still not proven in the actual orders.
- The phone payload is not huge by itself, but it is high/concentrated mass. Keep it low, centered, and add it only after no-payload floor tests pass.

## Source index

- Feetech STS3215 product info: `https://www.feetechrc.com/products.html?keyword=STS3215`
- Feetech ST3215-C047 datasheet mirror: `https://download.kamami.pl/p1203183-17bcda86-6ebc-4dc5-b704-7e06e8de6af9.pdf`
- Feetech FE-URT-1 manual: `https://d2air1d4eqhwg2.cloudfront.net/media/files/5ad7b845-cc46-431d-8c79-46e9c2c5a1d8.pdf`
- Waveshare Bus Servo Adapter A: `https://docs.waveshare.com/Bus_Servo_Adapter_A`
- SkyRC B6Neo: `https://www.skyrc.com/b6neo-series`
- SkyRC B6Neo manual: `https://www.skyrc.com/download/100198%20B6neo%20Instruction%20Manual%20V1.1_240318.pdf`
- Xiaomi Mi 9 SE specs: `https://www.mi.com/it/mi-9-se/specs/`
- VL53L0X breakout references: `https://www.adafruit.com/product/3317`, `https://www.pololu.com/product/2490`, `https://www.st.com/resource/en/datasheet/vl53l0x.pdf`
- Filament density references: Bitfab density table, Ultimaker TPU 95A TDS, MG Chemicals PETG TDS, Prusament PLA TDS.
- Historical local CAD/mass references named missing scripts under
  `mist_3d/tools/`; their old results are summarized, with provenance warnings,
  in `docs/mist/MIST_CAD_CHECK_PIPELINE.md`.
