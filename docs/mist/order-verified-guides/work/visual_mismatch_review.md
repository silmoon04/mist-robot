# Visual mismatch review for the existing MIST group guides

Date: 2026-07-30

## Executive finding

The current seven guide images are useful as category diagrams, but they are not reliable visual-identification guides. Most component pictures are AI-invented catalogue illustrations rather than reproductions of the user's delivered parts. Several components change colour, enclosure, connector count, or physical layout between guides. A few of those changes are structurally important enough that a user could pick up the wrong cable or look for a port that does not exist.

The replacement set should not ask an image model to redraw the products from memory. Use verified AliExpress/Amazon order images and the user's video frames as the actual component assets, then assemble the labelled sheets in code. Image generation, if used at all, should only clean backgrounds or create a neutral backdrop; it should not redraw boards, plugs, wires, labels, or port layouts.

## Evidence audited

- Existing guides:
  - `docs/mist/group-guides/00_master_sorting_map.png`
  - `docs/mist/group-guides/01_charge_and_lipo.png`
  - `docs/mist/group-guides/02_raw_3s_main_trunk.png`
  - `docs/mist/group-guides/03_four_leg_branch_kits.png`
  - `docs/mist/group-guides/04_5v_logic_and_servo_signal.png`
  - `docs/mist/group-guides/05_servo_intake_setup.png`
  - `docs/mist/group-guides/06_mechanical_and_tools.png`
- Inventory source: `docs/mist/MIST_ACTUAL_INVENTORY.md`
- Video-derived evidence:
  - `docs/mist/order-verified-guides/work/video_frames/contact_sheet_0-44s.jpg`
  - `docs/mist/order-verified-guides/work/video_frames/contact_sheet_44-54s.jpg`
  - especially `survey/survey_006.jpg`, `survey_007.jpg`, `survey_012.jpg`, `survey_013.jpg`, and `survey/late_001.jpg`
- Five room photographs under `<LOCAL_HOME>\Downloads\Telegram Desktop`.

The room photographs establish that the parts are dispersed between the bed, desk, drawers, shelf and floor. They are too wide and distant to establish connector or PCB identity. Do not use those wide room images as the visual reference for a specific component when a close video frame or order image is available.

## Highest-priority problems

### 1. The same component is drawn differently in different guides

- FE-URT-1 is a black enclosure in the master sheet and a white enclosure in the intake sheet. The user's video shows an exposed red PCB.
- Bus Servo Adapter A is shown with six white ports in the master and four ports in the logic sheet. The video shows a compact black PCB with two white bus connectors visibly present, a barrel jack, a green terminal and a yellow jumper.
- The smoke stopper has three unrelated invented bodies across the master, trunk and intake images.
- The PDB is a black 2-by-4 block in the master and a black 1-by-8 board in the trunk sheet. The video shows the ordered unit as a narrow in-line XT60-to-eight-XT30 assembly, not either drawing.
- The C018 servo changes from a purple-labelled generic servo to an unlabelled generic PWM-style servo.

Every replacement sheet must reuse one verified asset per SKU. Do not regenerate the same object independently for each page.

### 2. Generic PWM servo leads are visually confused with 5264 bus leads

The video clearly shows a large bag of ordinary red/white/black PWM extension leads with black Futaba/JR-style housings. These are the `25pcs generic RC servo extension leads` recorded in the inventory and must be labelled **NOT FOR THE STS3215 BUS**.

The user has said the ordered 5264 leads cannot currently be found. Therefore:

- do not depict the bagged black PWM leads as the expected 5264 leads;
- do not show 18 physical 5264 leads as confirmed in-room inventory;
- use the exact AliExpress order image for the ordered 5264 cable, with a yellow status badge such as `ORDERED / NOT YET LOCATED`;
- include a side-by-side connector-face comparison between the order image of 5264 and one clear crop of the user's generic PWM lead;
- keep the warning `do not force a plug`.

This distinction should be one of the largest tiles in the new set.

### 3. The boards are not visually faithful

`survey_012.jpg` is the strongest local evidence:

- FE-URT-1/URT board: exposed red PCB, white bus connectors along its edges, blue four-way screw terminal, USB connector, switch/header and visible bus markings. It is not an enclosed USB box with front binding posts.
- Bus Servo Adapter A: small black PCB, black barrel jack, green two-way screw terminal, yellow jumper, white bus connectors and a USB connector. It is not a blue four-output distribution board.
- ESP32: long black DevKit board with a USB-C connector and a metal WROOM shield. The current logic image appears to show a different USB connector.
- A separate camera board is present. Its silkscreen appears to include `C018`; this is not evidence of the ST-3215-C018 servo variant. Avoid confusing the camera-board marking with the servo's option code.

For each board, the replacement should have at least a top view and one connector-edge inset. Connector labels should be placed outside the photo with leader lines; do not repaint labels onto the PCB.

### 4. Physical compatibility is oversimplified in the power diagrams

The trunk sheet presents the whole path as if every item plugs directly into the next:

`LiPo -> XT90-S -> fuse -> smoke stopper -> PDB`

That is the architectural order, not proof of a plug-and-play cable chain. The ordered LiPo is XT60, the disconnect listing is an XT90-S extension, the fuse holder has bare leads, and the PDB has its own connector arrangement. Adapters/soldered joints are required unless exact mating cables are verified.

The replacement wiring sheet must distinguish:

- solid connector join: a verified male/female mating pair;
- solder joint: bare wire-to-wire splice that must be fabricated and heat-shrunk;
- unverified transition: dashed line and `VERIFY/FABRICATE`;
- conceptual power flow: a separate simple block diagram, not a fake photo of an already assembled harness.

Never draw a yellow XT60 body directly mating with an XT90-S body.

## Per-image audit

### `00_master_sorting_map.png`

Keep the six-group concept, but replace every invented thumbnail.

Problems:

- The master inherits all object-shape errors from the individual sheets.
- It contains inconsistent assets for FE-URT-1, Bus Servo Adapter A, PDB, smoke stopper and servo.
- The bottom spare strip in Group 3 visually suggests four more 5264 leads, while the detailed branch guide shows two spare leads. The total becomes ambiguous.
- Group 6 makes the M2 stock look like a verified machine-screw assortment even though the order record described a self-tapping/wood-screw assortment and the user only verbally listed lengths. Thread type is still a check, not a proven visual fact.
- Everything appears equally confirmed. Missing/unlocated items need a visibly different status.

Replacement:

- Use only small reused cutouts from the item cards.
- Put a status dot beside every item: green `SEEN`, blue `ORDER VERIFIED`, amber `NOT LOCATED`, red `MISSING`.
- Show counts as text, not by repeating an AI-drawn object.
- Treat the master as an index; no connection arrows here.

### `01_charge_and_lipo.png`

Problems:

- The HOOVO batteries are rendered as generic hard-case blocks. The video shows branded black shrink-wrapped soft packs with HOOVO red/white branding and flexible leads.
- The B6neo is the wrong colour and body. The delivered charger is red/cyan with a colour screen and three black buttons.
- The blue/silver delivered LiPo guard bag is not faithfully shown.
- The charger input supply is omitted. The inventory says the B6neo is powered from the user's Anker 317 100 W USB-C PD charger and a 5 A e-marked cable.
- The drawn main and balance connectors enter an invented face of the charger. Use actual port photos before drawing the connection.
- The low-voltage alarm is shown as confirmed and visually specific although the video evidence is not yet sufficient to identify it confidently.

Replacement layout:

1. `HOOVO PACK A` and `HOOVO PACK B`, both using the same real pack cutout and `3S / 2200mAh / 11.1V / 50C / XT60`.
2. `SKYRC B6neo`, actual red/cyan body, with port-detail insets.
3. `ANKER 317 + 5A USB-C CABLE`, labelled `charger input`.
4. `3S BALANCE LEAD` and `XT60 MAIN LEAD`, separately called out.
5. Delivered LiPo bag image.
6. Low-voltage alarm only if the order or room item is positively matched; otherwise amber.

The charge diagram should show one pack only. The second pack belongs in a separate storage tile, not connected to the charger.

### `02_raw_3s_main_trunk.png`

Problems:

- The PDB shape and port arrangement do not match the narrow physical assembly visible in `survey_006.jpg`.
- The XT90-S, fuse holder and smoke stopper are generic inventions.
- The direct physical chain implies incompatible connector families mate without adapters.
- It shows a complete harness although the items currently exist as separate products, pigtails and bare wire.
- The loose silicone wire is shown as a finished paired harness.

Replacement:

- Top row: exact individual photos, not connected: LiPo/XT60, XT90-S order item, waterproof inline fuse holder, smoke stopper, PDB, silicone wire.
- Middle row: conceptual flow blocks.
- Bottom row: `FABRICATE THESE JOINS` with verified pigtails and bare-wire splice symbols.
- Put gender labels on connector photographs only after they are confirmed from the order/delivered item.
- Preserve `RAW 3S: 9.9-12.6 V` and `no ESP32/5V devices`.

### `03_four_leg_branch_kits.png`

Problems:

- It depicts sixteen 5264 leads as physically present even though the user cannot locate them.
- All 5264 leads are drawn as one short identical length; the AliExpress listing/selected option may contain a different length or mixed length and must be copied exactly.
- The generic PWM lead bag visible in the video is not called out as the wrong product family.
- Four perfectly finished identical branch sets are implied even though these are loose components that still need fabrication.
- The fuse holder, PDB-side XT30 pigtail and capacitor are not shown as a wiring topology, so the sheet is a shopping grouping rather than an assembly reference.

Replacement:

- One `prototype branch kit` photo row using real loose components.
- Four labelled empty trays/bags: FL 1-4, FR 5-8, RR 9-12, RL 13-16.
- Repeat counts as text: `each tray: 1 XT30 branch pair, 1 15A fuse/holder, required 16AWG red/black, 1 x 4700uF 25V capacitor, 4 x verified 5264 leads`.
- If 5264 remains unlocated, all four tray rows receive amber `WAITING FOR 5264`.
- Separate `2 spare servos: IDs 17-18`; do not imply those two servos require a fifth full leg branch.
- Add a dedicated `PWM LEADS—KEEP SEPARATE` tile using the actual video frame.

### `04_5v_logic_and_servo_signal.png`

Problems:

- The Bus Servo Adapter A is the wrong board, colour and connector count.
- The UBEC is rendered as a sealed black box, while the delivered modules visible in the video appear as small exposed boards with red/black leads. Lock the exact identity to the order page before final labelling.
- The ESP32 connector/body is not faithful to the delivered Type-C CP2102 DevKit.
- The VL53L0X and camera are represented by generic sensor/camera icons. Use the actual camera crop and the exact ordered VL53L0X product image separately.
- The diagram risks implying that USB and UBEC power can be applied to the ESP32 simultaneously. The docs say one ESP32 power source at a time by default.
- The board port labelling is painted onto an invented PCB instead of derived from the physical item.

Replacement:

- Left panel: actual UBEC item -> multimeter measurement -> actual ESP32.
- Right panel: actual ESP32 -> actual Bus Servo Adapter A using a pin-by-pin text table beside the photograph.
- Show `signal/common reference only` separately from the raw-3S servo-current path.
- Put a clear selector: `BENCH USB POWER` **or** `VERIFIED UBEC 5V`, not both by default.
- Camera and VL53L0X should be optional accessory cards, not made to look like required parts of first servo commissioning.

### `05_servo_intake_setup.png`

Problems:

- FE-URT-1 is a fictional enclosed unit and its USB/power/servo port locations are wrong.
- The USB lead is shown entering an invented USB-A socket on the adapter.
- The C018 is a generic PWM servo body. It does not show the exact Feetech STS3215 housing, label, dual bus ports, supplied hardware or connector edge.
- The faux `C018` label used elsewhere can be mistaken for a real delivered label.
- The fuse and smoke-stopper bodies are not the delivered/order-verified products.
- The diagram again makes all connector transitions look plug-and-play.

Replacement:

- Use the red FE-URT-1 board source image, including a connector-edge inset.
- Use the exact AliExpress servo listing image until one box is opened and photographed.
- Title the servo precisely: `Feetech STS3215 — ordered option ST-3215-C018 — 12V / 30kg`.
- Status text: `verify the delivered label and register values; do not rely only on the guide image`.
- Show the real USB connector type from the adapter order/delivered photo.
- Keep `one servo at a time`, `no horn`, `multimeter required`, and `ESP32 later`.
- Show the expected 5264 lead from the order image with amber `NOT YET LOCATED` until it is found and physically fits both parts.

### `06_mechanical_and_tools.png`

Problems:

- The M2 organizer is drawn as a coherent machine-screw kit, but the exact thread/head type is not proven. Length alone is insufficient.
- The video contains a red folding key set/tool kit; the guide says metric Allen keys are absent without first checking whether the existing set contains 1.5/2/2.5/3 mm metric keys.
- A digital caliper appears to be among the delivered tools, so `NEED CALIPERS` is likely stale. Mark `SEEN / VERIFY WORKING` instead.
- PETG and TPU were Amazon orders, not clearly missing AliExpress items. Their arrival status should come from order/video evidence rather than a generic spool drawing.
- The multimeter is one of the closest existing drawings, but the replacement should use the actual red ANENG SZ308 photo. The needed battery should be labelled `1 x 6F22/PP3 9V`, not merely a generic battery.
- The USB cable drawings are generic and do not establish data capability.

Replacement status buckets:

- `PRESENT, CHECK SPEC`: M2 assortment, existing folding key/tool set, caliper, USB cables.
- `MISSING/BUY`: M3 machine screws, M3 nyloc nuts, exact missing metric key sizes, battery straps, PP3/6F22 9V battery.
- `NOT NEEDED YET`: M4.
- Add a close connector/type check for USB-C data, not a generic cable silhouette.

## Verified appearance cues from the video

These cues are safe to use as cross-checks, but order images should remain the reference for exact model options:

| Item | Local appearance cue | Confidence |
|---|---|---:|
| SKYRC B6neo | Compact red body, cyan front/button area, colour display, three black buttons | High |
| HOOVO batteries | Black soft packs/packaging with conspicuous red-and-white HOOVO branding | High |
| ANENG SZ308 | Red protective body, black face, red rotary selector, three top input sockets | High |
| FE-URT-1/URT board | Exposed red PCB with white bus connectors and blue four-way terminal | High |
| Bus Servo Adapter A | Small black PCB with barrel jack, green terminal, yellow jumper, white connectors | High |
| ESP32 CP2102 | Long black DevKit, metal WROOM shield, USB-C connector | High |
| XT60-to-8x-XT30 PDB | Narrow in-line board/assembly with one larger yellow XT60 and a row of smaller yellow outputs | High |
| Generic PWM leads | Red/white/black ribbon, black three-pin servo housings, large bag | High |
| 5264 leads | Not positively identified in the room/video | High that status is unverified |
| C018 servo body | Boxes are visible, but a sufficiently clear unpacked servo is not | Low |
| Smoke stopper | A definitive close product match still needs order-image confirmation | Medium/low |
| UBEC | Several matching small modules are visible, but exact order-image matching is still needed | Medium |
| LiPo alarm | Not confidently matched to one loose item | Low |

## Replacement asset and status rules

Each item record should carry:

- exact order title and selected option;
- quantity ordered;
- quantity seen in the room/video;
- status: `SEEN`, `ORDERED`, `NOT LOCATED`, `MISSING`, or `EXTRA/NOT FOR MIST`;
- one source path or order-page URL;
- one canonical transparent-background cutout;
- connector count, colour order and visible gender;
- confidence and any unresolved identity question.

Do not let `ordered` silently become `present`. In particular, the 5264 cable currently belongs in `ORDERED / NOT LOCATED`.

Do not use package quantity to create that many fake objects. Use one real item photo plus `x18`, `x10 pairs`, and so on.

## Layout specification for the regenerated set

### Separate item sheet

Create a contact-sheet-like inventory atlas before the six groups:

- 4 columns by as many rows as needed;
- one SKU per tile;
- neutral grey background;
- real order/delivered photo centred;
- label beneath, never printed over the object;
- selected option and count on the second line;
- status badge in the top-left;
- source badge in the top-right: `ALIEXPRESS`, `AMAZON`, `VIDEO`, or `USER PHOTO`;
- connector close-up inset in the bottom-right where relevant;
- `NOT TO SCALE` footer.

This sheet is the primary answer to “what should the item look like?”

### Six group sheets

Use the same canonical cutouts from the atlas. Each sheet should contain:

1. `PUT IN THIS GROUP` — real item cards.
2. `KEEP SEPARATE / DO NOT SUBSTITUTE` — only where confusion is likely.
3. `MISSING OR NOT LOCATED` — amber/red cards.
4. `FIRST SAFE ACTION` — one short instruction.

Group sheets should not pretend loose parts have already been soldered into a finished harness.

### Combined master sheet

- 3 columns x 2 rows for the six groups.
- Use small reused cutouts and text counts.
- No wiring arrows.
- No more than six item thumbnails per group; use `+ N small parts` for overflow.
- Preserve status colours.
- Put `5264 NOT LOCATED` and `MULTIMETER NEEDS PP3 9V` in a global gate bar.

### Connection sheets

Create separate technical diagrams after the visual inventory:

- diagram shapes can be simplified blocks;
- each block includes a thumbnail of the exact product;
- connector joins use an explicit legend: mating plug, solder joint, or unverified/fabricate;
- raw 3S, verified 5V and signal/common ground use distinct line colours;
- never alter a source photograph to manufacture a port.

## Prompt templates

### Reference-locked single-item asset

> Use only the attached verified order screenshot and delivered-item photograph as identity references. Create a clean catalogue cutout of this exact item on a light neutral background. Preserve the PCB/enclosure colour, board outline, connector count and positions, connector gender, wire colours and order, cable length proportions, switches, terminals, barrel/USB ports, brand marks and visible silkscreen. Do not add, remove, move, simplify or restyle any connector or component. Do not invent text. If a detail is obscured, leave it obscured instead of guessing. No extra accessories, hands, table or shadows that hide the connector faces.

Even with this prompt, compare the result side-by-side with the source. Prefer a normal crop/background removal over generation.

### Group still-life

> Arrange the supplied canonical product cutouts into a tidy top-down sorting group on a neutral bench. Do not redraw the products. Keep every supplied object unchanged. Do not connect loose wires or imply a finished harness. Leave room beneath each object for labels added later in code. Include no unprovided tools, cables, adapters, fuses or enclosures.

### Combined set

> Arrange only the supplied group-card images in a 3-by-2 grid. Reuse them without changing component appearance. Do not generate new products or alternate views. Leave all titles, status badges, counts and warnings to be added later in code.

### Negative prompt / rejection criteria

Reject output if it:

- changes PCB colour;
- changes the number or placement of ports;
- turns an exposed PCB into an enclosure;
- swaps USB-C, micro-USB or USB-A;
- changes connector family or gender;
- changes red/black/white wire order;
- replaces product branding with invented labels;
- depicts the generic PWM lead as a 5264 lead;
- shows ordered/unlocated parts as physically confirmed;
- directly mates XT60 to XT90-S;
- depicts a complete soldered harness that has not been built;
- draws an ESP32 camera as the C018 servo, or treats the camera-board `C018` marking as servo evidence.

## Recommended production workflow

1. Capture AliExpress order-detail screenshots for every order under the correct account and selected option.
2. Download or screenshot the main product image plus one connector-detail image for every electrical item.
3. Match each order to the delivered video evidence. Record `seen`, `not seen`, or `ambiguous`.
4. Extract/crop canonical assets without generative changes.
5. Build the single-item atlas.
6. Build the six groups by reusing those exact assets.
7. Build the master sheet from the six group cards.
8. Only then build separate wiring diagrams using the docs' architecture.
9. Before publishing, run a port/count/status audit against the order table and the video.

The main principle is simple: product appearance comes from evidence; grouping and labels come from the guide; connection topology comes from the HTML/docs. Those three layers should not be fused into one AI-invented picture.
