# Hexapod STS3215 Build — Full Chat Summary

This document is a chronological summary of the end-to-end chat in which a beginner set out to build an 18x Feetech STS3215 serial-bus, 3D-printed hexapod. The work ran across roughly six phases — from sanity-checking a sprawling AliExpress cart, through servo trade studies and power-path corrections, to building and cleaning a live basket, choosing a battery/charger and 3D printer, and a final deep-research pass. Throughout, the assistant leaned on many ultracode multi-agent workflows (research, synthesis, and reconciliation swarms) paired with GPT-5.5 (codex) cross-model adversarial passes, so that an independent model family could refute the false positives a Claude-only chain would otherwise keep re-confirming.

## Turn-by-turn — what you asked, what I responded

| # | You asked (short) | What I responded (summary) |
|---|---|---|
| 1 | Analyse the 18× STS3215 + cart, research the Tazer video, adversarial ultracode. | Ran a 17-agent swarm and found the cart was built for PWM servos while STS3215 are serial-bus, so PCA9685/horns/MG996R/PWM leads are wrong and the 3S would cook them; you need a Waveshare ESP32 driver + FE-URT-1, ~2kg ceiling, plus a BOM analysis, power diagram, and memory. |
| 2 | You're forgetting connective parts; use a subagent to price like a human with shipping. | Codex surfaced the connective gaps (crimp tool, connectors, B6neo-needs-a-PSU) and top-15 forgotten items; the price-agent crashed so I priced by web and corrected that the B6neo runs on USB-C PD/DC with a 5264 bus connector. |
| 3 | You SURE? rerun calcs; 18-servo cost; 360 vs less; 30kg; cheapest. | A 10-agent trade study where the GPT-5.5 adversary caught my error: 19.5kg is the 7.4V figure, so regulate the rail flat to 7.4V not 5–6V, keep 360°, don't switch to 30kg, spares ~£12–15/unit. |
| 4 | I don't own the servos yet; add the cheapest to the basket and copy all coupons. | Added the cheapest matching 18 (stemedu 12-pack + 6-pack with FE-URT-1) plus the Waveshare driver, dodging an £8.89 bracket and 'max 1 per shopper' traps, and explained coupons auto-apply while new-shopper ones won't apply to you. |
| 5 | Did you add EVERYTHING necessary? | No — the cart was only ~half the electrical BOM and none of the mechanical/print side, so I listed the gaps and asked three setup questions (power path, tools owned, scope). |
| 6 | (3S→7.4V, own no tools, scope=everything) add them and remove non-essentials except mirrors. | Wrote the final basket list and removed the wrong items (PCA9685/bus bar/extra charger/3S battery/25T disc/PWM leads) while keeping the mirrors. |
| 7 | Is everything active in the cart good? battery not available anymore. | Cart is clean and active; flagged the 12-pack 'only 1 left' and Waveshare 'almost sold out' stock risks, and noted the missing battery is intentional since AliExpress won't ship lithium to the UK. |
| 8 | Make sure everything we need is ticked on. | Ticked 'select all' → Checkout, 17 items, ~£359. |
| 9 | What about battery? | A 5-agent study picked the Overlander 3S 3350mAh at £35 (lighter beats the 5000mAh on a mass-marginal walker); C-rating is a non-issue and the regulator is the real risk. |
| 10 | And a charger for the battery? | Your B6neo 2 already charges 3S; it just needs a DC/PD source, and your 100W/120W USB-C PD chargers cover it for £0. |
| 11 | What CAN you add on AliExpress? research UK cheap delivery; I have pricey Prime. | A 6-agent sourcing plan split AliExpress-add vs UK-buy, gave Prime-vs-specialist verdicts, and solved the ≥40A rail as two isolated 20A SBEC banks, never paralleled, bench-tested to 40A. |
| 12 | Aren't they cheaper on AliExpress apart from the LiPo? | Conceded: as one AliExpress order there's no extra shipping, so AliExpress wins on cost for nearly everything, leaving only the LiPo and heavy filament as UK buys. |
| 13 | I'll use my Mi 9 SE + own an MPU6050; buy a battery charger; did you check non-AliExpress prices? | Removed the duplicate MPU6050 (you own one), framed phone = high-level sensing and MPU6050 = fast balance loop, confirmed the charger is already solved by your PD chargers, and yes, UK prices were checked in the sourcing plan. |
| 14 | Add the remaining AliExpress stuff, browse Amazon, run /deep-research, refine the basket, visual test tools. | Added UBEC/VL53L0X/PDB, found Amazon blocks automated add-to-basket (gave one-click links), built an interactive hexapod explorer widget, ran my own 8-agent deep-research swarm after the packaged one errored, and wrote the master basket. |
| 15 | Do we need a breadboard? filament prices? browse cheap/used 3D printers. | Breadboard is optional (skip, never for power); PETG ~£12–16/kg and TPU 95A ~£15–22/kg; a 5-agent study picked the Creality Ender 3 V3 SE at £149 (direct-drive for TPU, auto-level) over the too-small Bambu A1 Mini. |
| 16 | Summarise the entire chat in great detail with docs, using ultracode. | Ran a 7-agent summariser swarm and wrote HEXAPOD_CHAT_SUMMARY.md. |
| 17 | Also include what you responded and the file paths in an md file. | Added this turn-by-turn table plus a full absolute-path index of every document into the summary. |

## Phase 1 — The starting cart and the 17-agent BOM analysis

The user opened by explaining that he had already bought **18x Feetech STS3215** servos (19kg-cm, 7.4V) and then pasted a sprawling AliExpress cart to be sanity-checked. The cart included: a **SKYRC B6neo 2 (300W)** charger *and* a second **B6neo (200W)** charger, an XT60-female-to-4mm-banana charge lead, a fireproof LiPo bag, 50pc acrylic mirror stickers, **2x PCA9685** PWM driver boards, 4700uF 16V capacitors, several silicone-wire reels, a 4-post **250A bus bar**, a 30A inline fuse holder, XT60BE-M connectors, a 25-pc 3-pin servo-extension-lead set, an **MG996R** analog servo, a **BEAT 3S 2200mAh 11.1V** LiPo, **3x 300W-20A buck converters**, a 164pc heat-shrink kit, and **24x 25T servo disc horns**. He asked the assistant to work out EXACTLY what else he still needed, how it would affect price/weight/design, and what ADDITIONS (displays, a Xiaomi Mi 9 SE phone mounted on top, batteries, other chips) could enhance the robot. He specifically asked for research across many articles/guides plus a named YouTube video (**Tazer Technical**) by analysing its transcript and spritesheets with subagents via yt-dlp at ~720p low fps, then to run ADVERSARIAL agents using `/codex-adversary`, `/deep-research` and ultracode workflow swarms.

The assistant first scouted the environment: it updated **yt-dlp to 2026.06.09**, confirmed ffmpeg, codex/GPT-5.5 and python were present, and read the three relevant memory files (ELEGOO ESP32-WROVER camera; Mi 9 SE phone node; SH1106 OLED eyes). It downloaded the video — **"How I Built my First Robot - Hexapod Deep Dive"** by Tazer Technical (**78 min**) — and extracted an **11,494-word transcript** plus its parts list. Crucially, that build used **40kg ANALOG PWM servos** with an **Arduino Mega**, a fundamentally different electronics path from the user's serial-bus servos. It also generated **14 timestamped spritesheets** spanning the whole video.

The assistant then launched a **17-agent ultracode Workflow**: 6 web-research agents, 1 transcript agent, and 4 spritesheet-vision agents (Investigate); a synthesis agent; **3 GPT-5.5 (codex) adversarial refute passes** plus 1 Claude completeness critic (Adversarial); and a final reconciler.

The core findings were decisive. 18 servos means a **HEXAPOD** (6 legs x 3 DOF). The STS3215 are **TTL serial-bus**, not PWM — so the cart's 2x PCA9685, the 25-pc PWM extension leads, the 24x 25T horns and the MG996R are all **WRONG** (a PCA9685 cannot command a serial-bus servo). The **3S/11.1V LiPo would cook** the 7.4V servos. Instead he needs a **Waveshare "Servo Driver with ESP32"** plus a **Feetech FE-URT-1**. The **250A bus bar** is absurdly heavy — swap for a small XT60 PDB — and only **1 of the 3 buck converters** should be kept. The weight ceiling is ~2kg, with the **phone-on-top being the worst possible CG spot**.

Deliverables: **HEXAPOD_BOM_ANALYSIS.md** and **HEXAPOD_BOM_appendix.md**, an interactive power-architecture SVG diagram, and a saved memory file **hexapod-sts3215-build.md**.

## Phase 2 — The connective-parts sweep and the first price hunt

After the core-component list, the user pushed back. They felt the assistant was, in their words, "forgetting so many other extra things I will probably need to connect" — the unglamorous glue that turns a box of servos and boards into a working robot. They asked for something specific: use ONE subagent to browse the web *like a human*, driving a real connected Chrome, and compare prices across sites to find the best deal WITH shipping folded in, not just the sticker price.

The assistant first attacked the completeness problem head-on. It ran a GPT-5.5 (codex) adversarial pass framed as "what connective parts are still missing," using the cross-model refute panel so a second model family could catch the gaps a Claude-only list would keep re-confirming. That produced **HEXAPOD_CONNECT_EVERYTHING.md**. The sweep surfaced a long tail of easy-to-forget items: a crimp tool; a Dupont/JST connector kit; a USB *data* cable for the ESP32 (not a charge-only cable); a kill switch / XT90-S anti-spark loop key; spare XT60 pigtails; M2/M3 fasteners with heat-set inserts and threadlocker; and the bench tools — soldering iron, calipers, hex drivers. The standout gotcha: the **SKYRC B6neo charger ships with NO mains plug** and needs a separate DC or PD power source to work at all. The document closed with a ranked TOP-15 most-forgotten list.

Then came the price hunt, and it did not go smoothly. The assistant launched ONE human-like pricing subagent to drive the user's connected Chrome ("Browser 1"). It FAILED: the Claude Code process exited mid-run, which killed the background agent AND tore down the Claude-in-Chrome MCP connection with it. A relaunched web-research pricing subagent fared only partly better — its parent returned a deflection, but its child agents did complete with priced tables. Rather than keep fighting the browser automation, the assistant finished the pricing itself using WebSearch and WebFetch.

That produced **HEXAPOD_PRICES.md**, with landed-UK prices and a sourcing strategy. Two corrections surfaced along the way and were folded in. First, the B6neo charger CAN run off USB-C PD (up to 80W) or DC, and the matched supply is the **SKYRC PSA100 at £19.99 from FlyingTech** — softening the earlier "no plug" alarm into an actionable buy. Second, the STS3215 bus cable uses a **5264 2.54mm 3-pin connector, NOT JST-XH** — a correction that matters for anyone buying spare cables or crimping their own.

Verified prices included **The Pi Hut ESP32 servo driver at £15.40** and the **Seeed FE-URT-1 at roughly $10**. The assistant also flagged a logistics constraint: the **LiPo battery should be bought in the UK**, because AliExpress won't air-freight lithium cells — meaning the cheapest line-item source isn't a viable one for that part.

## Phase 3 — The "are you SURE" trade study, and the 7.4V correction

Having already handed over a bill of materials, the user refused to let it rest. The message was blunt: "you SURE SURE SURE i dont need anything else?" — followed by a stack of specific demands. Rerun the calculations: what got missed, what could go wrong. Price out all 18 bus servos *with telemetry* and compare every vendor. Decide whether 360-degree servos were right, or whether a limited-angle part would be better (and cheaper) for a walker. Model the 30kg version — how it changes weight, torque, size, and price. And find the cheapest path through all of it.

Rather than answer from memory, the assistant spun up a 10-agent trade-study Workflow. The agents split the problem: torque sizing, the Feetech/Feetech-clone servo lineup, 360-vs-limited-angle, 18-servo telemetry pricing, and the 30kg/12V cascade. A synthesis agent pulled the threads together, three GPT-5.5 adversary passes attacked the result, and a final agent wrote it up.

The adversary earned its keep. It caught a real error in the assistant's *own earlier advice*: the 19.5 kg-cm torque figure had been labelled as the 6V number when it is actually the 7.4V number. The correction mattered enormously for a load-bearing walker. Regulate the servo rail to a **flat 7.4V**, not the 5–6V previously suggested — at 6V an STS3215 delivers only ~15.8 kg-cm, roughly 81% of rated torque, which a walking hexapod carrying its own weight cannot spare. The 5V path in the LeRobot reference design is for an *arm*, not a walker, and copying it here would have quietly starved every leg.

On the 30kg question the verdict was: don't switch on spec. The 30kg servo is a 12V part, which forces a 3S battery and a full re-buy of the 18 servos he already owns — a zero-weight, zero-CAD drop-in, but a pure sunk-cost rebuy. The right move is to design the chassis and power path so a future 3S/30kg upgrade is a re-flash, not a rebuild.

On 360-degree: keep them. There is no cheaper limited-angle SKU to downgrade to, and the 360-degree magnetic-encoder STS servos are more precise and reusable later as wheels or in an arm.

On price: the cheapest 18 servos are the ones he was already buying. Spares run ~£12–15/unit on AliExpress, or ~£26 each for fast delivery from RobotShop UK. A torque-sensitivity table (mass × reach × voltage) fenced off a safe build envelope: roughly ≤2.3–2.5 kg total, ≤14 cm leg reach.

Deliverables: `HEXAPOD_SERVO_TRADESTUDY.md` plus an appendix, and a memory update. Correction banners went to the top of both `HEXAPOD_BOM_ANALYSIS.md` and `HEXAPOD_PRICES.md`, flipping the old 5–6V guidance to 7.4V and flagging that the "cheap 300W/20A" buck converter is really only ~120–150W — a genuine ≥40A regulator is required.

## Phase 4 — Building and cleaning the live AliExpress cart

With the design settled, the user turned to procurement, but with an important caveat: "i dont own them yet, add cheapest in basket copying all coupons to then try." Through an AskUserQuestion he had fixed the ground rules — power path would be 3S regulated down to 7.4V, he owned none of the tools, and the scope was "everything." His follow-ups were terse and demanding: "did u add EVERYTHING necessary," "try again," "is everything active in the cart good? battery not available anymore," and "make sure everything we need is ticked on."

Driving the reconnected Chrome session, the assistant priced the 18 STS3215 servos live and hunted for the cheapest *credible* route rather than the cheapest headline number. It settled on a stemedu 12-pack at £162.93 plus a 6-pack that bundled the FE-URT-1 programmer at £95.79 — 18 servos and the serial driver from a single matching seller, landing around £247-259. Along the way it flagged and sidestepped traps it uncovered by inspecting listings directly: an £8.89 "servo" that was in fact just a mounting bracket, and the fact that the tempting cheap singles and 6-packs were all "Max 1 per shopper" welcome deals that couldn't be stacked to 18 units. Both packs went in, followed by the Waveshare ESP32 servo driver at £21.99.

On coupons, the assistant explained the mechanics honestly: these are auto-apply store and select coupons with no typed code, applied at the place-order page, and the eye-catching "new shopper" £73/£20 discounts almost certainly would not apply to his established account.

Cart cleanup proved fiddly. After coordinate-based clicks kept mis-firing on the wrong rows, the assistant switched to a reliable find-by-reference delete method and removed the clutter: the 3S 2200mAh battery, a redundant 200W charger, both PCA9685 boards, the 250A bus bar, the 25T disc, and the PWM extension leads — while deliberately keeping the mirrors per the user's instruction. When he worried the "battery not available anymore," the assistant confirmed this was intentional: there is no battery in the cart because AliExpress won't ship lithium cells to the UK.

Finally it ticked "select all" and ran Checkout across 17 items at roughly £359. A candid gap analysis followed: the cart covered only about half the electrical BOM and none of the mechanical or 3D-print side of the build, so the £359 was a floor, not the finished bill.

The phase produced a deliverable, `HEXAPOD_FINAL_BASKET_LIST.md` — the 3S-path, everything-scope buy list capturing what was in the cart and what still needed sourcing.

## Phase 5 — Battery, charger, and the UK-vs-AliExpress sourcing plan

With the mechanical and driver questions settled, the user turned to power storage: "what about battery". A 5-agent Workflow worked the question and landed on the **Overlander Supersport Pro 3S 3350mAh 35C XT60** (~£35, UK, in stock) in preference to the obvious 5000mAh pack. The reasoning was mass, not capacity: on a hexapod that walks right at the margin of its torque/weight envelope, the 3350mAh cell saves roughly 115g, and on a mass-marginal walker centre-of-gravity matters more than the ~10 minutes of extra runtime the bigger pack would buy. The C-rating was shown to be a non-issue — 35C on 3350mAh is about 117A continuous against a worst-case stall of only ~45A — so the pack has enormous headroom. The real risk sits downstream in the regulator, not in the battery. This was captured in **HEXAPOD_BATTERY_CHARGER.md**.

The user followed up: "and charger for battery". Here the answer was reassuringly cheap. The **SKYRC B6neo 2** he already owns charges 2S–6S, so it handles the 3S pack without any new purchase — it only needs a DC or USB-C PD source to feed it. Since he later confirmed he owns both **100W and 120W USB-C PD phone chargers**, that requirement is met for £0, and the SkyRC PSA100 mains supply is not strictly needed.

He then asked the sourcing question directly: "what CAN you add on aliexpress? and for rest research elsewhere that do uk delivery relatively cheap? have amazon prime but that might be expensive". A 6-agent Workflow produced **HEXAPOD_SOURCING_PLAN.md**, splitting the bill of materials into an AliExpress-add list and a UK-buy list. UK specialists beat Amazon Prime on several items: **SkyRC PSA100 at £19.99 (FlyingTech)**, an **XT90-S loop key ~£5 (HobbyRC)**, a **soldering iron ~£39 (Kunkune)**, and **PETG/TPU filament from SUNLU**, with calipers, hex keys, a watt-meter and Loctite left to Amazon Prime. The hardest line item — a ≥40A, 7.4V servo-rail regulator — was solved not by finding one part but by **splitting the servo bus into two isolated banks fed by 2× 20A SBECs**, with the firm rule never to parallel their outputs and a **40A bench test** required on each. The plan also corrected a stale Hobbywing price the adversarial agent had flagged.

Finally the user pushed back on the whole geography: "arent they cheaper on aliexpress apart from lipo". The assistant conceded the point. Because he is already placing one AliExpress order, adding the commodity parts there incurs **zero extra shipping**, so AliExpress wins on cost for nearly everything. Only two categories genuinely stay in the UK: the **LiPo pack**, which can't be shipped by air, and heavy **filament**, where weight-based shipping erases the price gap.

Relevant files (all under the project root ``): `HEXAPOD_BATTERY_CHARGER.md` and `HEXAPOD_SOURCING_PLAN.md`.

## Phase 6 — Phone sensors, the 3D printer, the interactive tool, and the deep-research report

The user opened this phase by folding his own hardware into the plan: he'd use his Xiaomi Mi 9 SE's accelerometer, GPS, and screen, and noted he already owns an MPU6050. He asked whether anything was needed to charge the battery, and whether non-AliExpress prices had been checked. His instructions then broadened sharply: "add the remaining aliexpress stuff yourself and also browse amazon until you find the right stuff, dw about printer or filament yet," plus a dense research brief — "run in-depth /deep-research on robots with similar components — their calculations, how they built it, problems faced, whether 360 or less matters, rerun calcs, wiring, making models, other people's sizes, search MCPs/tools for wiring/designing/testing (visual so I can learn), install and run them, take advice and understand mistakes, refine the AliExpress basket and write the entire list, think about what's missing and what to test (not too expensive)." A follow-up added: "do we need a breadboard? how much are good filaments? considering a cheap/used 3D printer on Amazon — browse a few and tell me which to consider."

First, a correction: the assistant had added a second MPU6050 to the cart, and removed that duplicate since the user already owns one. It clarified the sensing split — the phone handles high-level 9-DOF IMU, GPS, screen, and camera over WiFi, while the user's own MPU6050 runs the fast on-board balance loop. The battery charging question was resolved: his existing USB-C PD chargers cover it, nothing new needed.

On the 3D printer, a 5-agent Workflow (HEXAPOD_3DPRINTER_PICK.md) recommended the Creality Ender 3 V3 SE (£149 at 123-3D) over the too-small Bambu A1 Mini — chosen for its direct-drive extruder (needed for TPU feet), auto-leveling, and 220x220 bed — with the Bambu A1 (~£234) as a stretch pick. A live Amazon browse confirmed the SE at ~£167 and ELEGOO Rapid PETG at £12.99/kg, and proved Amazon blocks automated add-to-basket (the basket stayed empty across two attempts), so it supplied one-click Amazon links instead.

For the cart, the assistant reliably added a 5V UBEC (2-pack), a VL53L0X ToF sensor, and an XT60 8-channel PDB via direct-URL and modal methods, providing one-click links for the rest. On the smaller questions: a breadboard is optional and best skipped (use Dupont jumpers, never for power); good PETG runs ~£12-16/kg and TPU 95A ~£15-22/kg.

The assistant also built a live hexapod design explorer widget — sliders for mass, reach, and voltage showing joint torque against the 19.5kg servo limit, a safety factor, a tripod-gait animation, and a power budget.

Finally, the research. The packaged /deep-research skill failed on a schema bug, so the assistant relaunched its own 8-agent deep-research Workflow, producing HEXAPOD_DEEP_RESEARCH.md. Comparable builds informed it: PCrnjak/3D-printed-Hexapod reuses the Phoenix/Phantom IK; CoretechR's ZeroBug reset its Pi on low battery; Vorpal's battery surge-tripped; LeRobot demonstrated voltage discipline. A key correction emerged — apply a 1.3-1.8x dynamic factor to the torque math, meaning the explorer had been optimistic and was updated accordingly. Findings also covered wiring (two isolated SBEC banks, common ground only, bulk caps, star ground), geometry (coxa 35 / femur 80 / tibia 100mm, body ~180mm, <=2.5kg, 8-9cm stance offset), a visual toolchain (hexapod.netlify.app browser sim, then PyBullet + resibots/pyhexapod, Onshape/FreeCAD, WireViz, Feetech FD), and cheap test gear (bench PSU, watt-meter, FE-URT-1). The deliverable HEXAPOD_MASTER_BASKET.md consolidated everything.

## Documents produced

Full absolute paths to every file written during this build.

Under ``:

- `/HEXAPOD_BOM_ANALYSIS.md` — Phase 1 core bill-of-materials analysis: what the cart got wrong, what's missing, and the corrected serial-bus component list.
- `/HEXAPOD_BOM_appendix.md` — Appendix to the BOM analysis with the detailed per-line breakdown.
- `/HEXAPOD_CONNECT_EVERYTHING.md` — The connective-parts sweep: crimp tools, connector kits, data cables, kill switch, fasteners, and the ranked TOP-15 most-forgotten items.
- `/HEXAPOD_PRICES.md` — Landed-UK price hunt with sourcing strategy and the 5264-connector and B6neo-PD corrections.
- `/HEXAPOD_SERVO_TRADESTUDY.md` — Torque sizing, 360-vs-limited-angle, 18-servo telemetry pricing, the 30kg/12V cascade, and the 7.4V rail correction.
- `/HEXAPOD_SERVO_TRADESTUDY_appendix.md` — Appendix to the servo trade study with the supporting tables and calculations.
- `/HEXAPOD_FINAL_BASKET_LIST.md` — The 3S-path, everything-scope buy list capturing the live cart and what still needed sourcing.
- `/HEXAPOD_BATTERY_CHARGER.md` — Battery selection (Overlander 3S 3350mAh) and the charger answer (reuse the B6neo 2 with USB-C PD).
- `/HEXAPOD_SOURCING_PLAN.md` — AliExpress-add vs UK-buy split, the two-isolated-SBEC-banks regulator solution, and the vendor list.
- `/HEXAPOD_3DPRINTER_PICK.md` — The 3D printer recommendation (Ender 3 V3 SE over the Bambu A1 Mini) with filament notes.
- `/HEXAPOD_MASTER_BASKET.md` — The consolidated master basket pulling every phase together.
- `/HEXAPOD_DEEP_RESEARCH.md` — The 8-agent deep-research report on comparable builds, wiring, geometry, the dynamic-factor correction, and the visual toolchain.
- `/HEXAPOD_CHAT_SUMMARY.md` — This document: the chronological chat summary, turn-by-turn table, and document index.
- `/FLASHING_LineageOS_grus.md` — LineageOS flashing notes for the Mi 9 SE (grus) sensor node.
- `/README.md` — Project README.

Under `<LOCAL_HOME>/.claude/projects/C--Users-hssil-Downloads-03-Programming-Projects-spider-robot/memory`:

- `<LOCAL_HOME>/.claude/projects/C--Users-hssil-Downloads-03-Programming-Projects-spider-robot/memory/hexapod-sts3215-build.md` — The persistent memory file capturing the build's key facts and corrections across conversations.
- `<LOCAL_HOME>/.claude/projects/C--Users-hssil-Downloads-03-Programming-Projects-spider-robot/memory/MEMORY.md` — The memory index linking every persisted memory file.

Rendered inline in chat (not files): the **two interactive hexapod design-explorer widgets** (mass/reach/voltage sliders vs the 19.5kg servo limit, safety factor, tripod-gait animation, power budget — plus its dynamic-factor-updated revision) and the **power-architecture diagram** (the interactive SVG showing the corrected power path from battery through regulation to the servo rail).

## Key corrections made along the way

> - **Servo rail voltage:** 5–6V rail → **flat 7.4V** (at 6V the STS3215 gives only ~15.8 kg-cm, ~81% of rated; the 5V LeRobot path is for an arm, not a walker).
> - **Torque math:** static torque → **add a 1.3–1.8× dynamic factor** (the first explorer was optimistic and was updated).
> - **Regulator:** the "cheap 300W/20A" buck is really only ~120–150W → **two isolated 20A SBEC banks**, outputs **never** paralleled, each **40A bench-tested**.
> - **PWM parts are wrong:** remove the **PCA9685 boards, 25T disc horns, MG996R, and PWM extension leads** — STS3215 is serial-bus, not PWM.
> - **Battery:** 3S/11.1V raw → **3S regulated down to 7.4V** (or the **3S 3350mAh** pack), never fed raw to the servos.
> - **MPU6050:** the one added to the cart was a **duplicate** — the user already owns one; removed.
> - **Amazon:** blocks automated add-to-basket — one-click links supplied instead of a filled Amazon cart.
