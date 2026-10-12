# MIST photographic sorting guides

These boards use real pixels from the user's 8K inventory video and close-up photographs. Components have not been AI-redrawn. Where a delivered item could not be matched confidently, the board uses a labelled order-ledger placeholder instead of inventing its appearance.

## Boards

- `00_item_atlas.png` — delivered-item appearance atlas
- `01_charge_and_lipo.png` — charger, packs and safe charging group
- `02_raw_3s_trunk.png` — raw 3S distribution parts
- `03_four_leg_kits.png` — four servo/leg sorting trays
- `04_5v_logic_and_signal.png` — UBEC, ESP32 and Bus Servo Adapter A
- `05_servo_intake.png` — one-servo FE-URT-1 commissioning tray
- `06_mechanical_and_tools.png` — fasteners, retention and tools
- `07_master_sorting_map.png` — all six groups together

`reference_boards.html` is the editable source.

## Evidence status

- **Seen:** identifiable in the video or close-up photos.
- **Candidate — verify:** visually plausible, but not yet confirmed by connector fit, label or electrical measurement.
- **Order ledger:** recorded in `MIST_ACTUAL_INVENTORY.md`, but not visually confirmed as delivered.
- **Missing:** user-reported absent or not present in the visual evidence.

## Important correction: likely 5264 leads

At about 34 seconds, a white tray contains many long black flat leads with small white keyed housings. These are a strong candidate for the Feetech 5264 servo-bus leads previously thought missing. They are not the bag of generic red/white/black PWM leads.

Before power:

1. Remove one black/white-ended lead from the tray.
2. Compare the key and housing to the C018/FE-URT port; do not force it.
3. Confirm the pin order and continuity with a working multimeter.
4. Only after confirmation, sort four verified leads into each leg tray.

## Remaining gates

- Install the meter's specified PP3/6F22 9 V battery and prove continuity/DC-voltage operation.
- Obtain M3 machine screws and M3 nyloc nuts for final mechanics.
- Verify the received M2 thread type and usable counts.
- M4 hardware and a breadboard are not current blockers.
- The charger close-up shows **LiHV / 3S Charge** selected. For the HOOVO 11.1 V packs, use **LiPo / 3S / Balance Charge**, no more than 2.2 A, with a 12.6 V full voltage.
- Do not power a C018 through the ESP32. First servo commissioning uses one C018, the red FE-URT-1, one positively identified 5264 lead, USB data, and a protected external 3S servo supply.

## AliExpress verification limitation

The signed-in AliExpress Orders page could not be inspected because browser access to the private orders route was blocked by the platform security policy. The connected Gmail account was a different mailbox from the one requested and contained no line-item AliExpress receipts. Therefore, seller listing images and selected variants are not claimed as verified here.

For a seller-image cross-check, export or screenshot each AliExpress order-detail line with the product thumbnail, selected option and quantity visible. Those screenshots can replace the remaining order-ledger placeholders without guessing.

## Audit notes

- `work/docs_inventory.md` — documentation/order-ledger cross-check
- `work/visual_mismatch_review.md` — comparison with the earlier inaccurate generated boards
- `work/video_frames/VIDEO_COMPONENT_AUDIT.md` — timestamped video inventory audit

