# MIST order-verified guides v2

## Current deliverables

- `08_battery_path_why.png` — the full battery path and the purpose of XT60, XT90-S, fuses, PDB, leg branches, capacitors and UBEC.
- `09_bench_vs_full_robot.png` — separates charging, one-servo FE-URT commissioning and the finished 16-servo robot.
- `10_safety_layers.png` — maps likely failures to the protection that catches them and explains each protection's limitations.
- `battery_power_explainer.html` — editable source for the three images.

The PNGs are 1536 × 1024 and use real crops from the user's video and close-up photographs. Technical connectors and paths are drawn deterministically; no connector or board appearance has been invented by a generative model.

## Gmail/AliExpress status

On the latest check, the connected Gmail profile still authenticated as the `.18` mailbox rather than the requested `.00` mailbox. The matching AliExpress messages were addressed to `.18`, so they were not used as evidence for the July 2026 robot orders.

The product/group boards will be regenerated from seller/order images once the Gmail connector's profile check returns the intended `.00` mailbox. Until then, the prior photographic boards remain the honest source-faithful set:

- `../order-verified-guides/00_item_atlas.png`
- `../order-verified-guides/01_charge_and_lipo.png`
- `../order-verified-guides/02_raw_3s_trunk.png`
- `../order-verified-guides/03_four_leg_kits.png`
- `../order-verified-guides/04_5v_logic_and_signal.png`
- `../order-verified-guides/05_servo_intake.png`
- `../order-verified-guides/06_mechanical_and_tools.png`
- `../order-verified-guides/07_master_sorting_map.png`

## Design clarification

- The battery already uses XT60. That remains the physical battery interface.
- XT90-S is an additional anti-spark, accessible disconnect/loop-key option for the finished robot. It is not a voltage converter, does not increase the XT60's capacity and is not needed for one-servo intake.
- The main fuse protects the trunk wiring against a high-current short.
- The PDB—or an equivalent correctly built distribution harness—splits the battery feed.
- Four branch fuses isolate the four leg power routes.
- The UBEC creates the regulated 5 V logic rail. The ESP32 and Bus Servo Adapter do not carry servo motor current.
- The smoke stopper is only for static first-power tests. It must be bypassed before motor movement.
- The 4700 µF capacitors reduce brief voltage dips at leg roots; they do not fix sustained overload.

Fuse values are starting values from the project design and must be checked against verified wire gauge, connector quality and measured operating current. Repeated fuse operation is a fault to diagnose, not a reason to fit a larger fuse.

