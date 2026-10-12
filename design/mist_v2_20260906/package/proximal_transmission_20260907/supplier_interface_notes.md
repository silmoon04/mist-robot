# Pulley attachment, shafts and collars

Supplier check: 7 September 2026. Scope: metal 32-tooth, 3 mm GT-profile pulleys for a 9 mm Gates GT3 belt, with 7 mm input and 8 mm knee interfaces. Earlier belt/pulley supply findings remain in `../belt_selection_20260907/supplier_notes.md`. No purchase, quotation request or external message was sent.

No stock 32T/3GT/9 mm pulley with a directly rated 7 mm or 8 mm clamping attachment was established. Three concrete routes remain: a factory Fairloc pulley with a specified bore; a correct GT pulley with configurable face holes attached to a checked clamp carrier; or a larger-bore GT pulley with a rated miniature locking bush. The last route has a published bush torque rating, but the complete pulley assembly still needs its hub and engagement checks.

## Standard pulley fasteners

| Part | Supplied attachment and geometry | Holding-torque evidence |
| --- | --- | --- |
| [MISUMI GPA32GT3090-B-P7](https://uk.misumi-ec.com/vona2/detail/110302193560/?HissuCode=GPA32GT3090-B-P7); equivalent P8 configuration for an 8 mm bore | Aluminium 2000-series pulley; 32T 3GT; 9 mm belt; H7 bore. Two M4 × 3 set screws for 6–17 mm bores. GPA screws are EN 1.4301-equivalent stainless; the catalogue permits equivalent substitutes. Hub diameter 20 mm, total length 22 mm, width W14 mm, face A10.3 mm, flange diameter 34 mm. Standard set-screw spacing is approximately 120°; KC90 changes it to 90°. | No assembly holding-torque rating found. Screw point shape, drive size and permissible installation torque were not established in the pulley drawing. Do not assign a transmission rating from M4 size alone. |
| [SDP/SI A 6A53M032DF0906](https://shop.sdp-si.com/a-6a53m032df0906.html) | Standard set-screw pulley, 6 mm bore. Two M4 set screws at 90°. Hub diameter 21.6 mm, hub projection 7.8 mm, overall length 20.6 mm, flange diameter 33.6 mm. | Drawing does not establish an assembly slip-torque rating or screw-point/length/installation-torque specification. |
| [SDP/SI A 6D53M032DF0906](https://shop.sdp-si.com/a-6d53m032df0906.html) | Correct GT2/GT3 pulley with integrated Fairloc hub; 6 mm bore (+0.025/0 mm); one M3 cap screw. Hub diameter 19.1 mm, projection 7.5 mm, overall length 20.6 mm, body dimension 12.9 mm, flange 33.6 mm. | No exact-part holding-torque rating found. Fairloc test graphs for other bores/materials are not a rating for this 6 mm aluminium pulley. |

Dimensions and accessory data come from the [MISUMI 3GT drawing](https://uk.misumi-ec.com/pdf/fa/2014/P1_1383-1384_F19_EN_001.pdf), [SDP/SI standard pulley drawing](https://shop.sdp-si.com/media/pdf/80502158.pdf), and [SDP/SI metric catalogue, GT2/GT3 Fairloc table](https://sdp-si.com/D815/D815-Metric-Section2-Belt-and-Chain-Drives.pdf). The [older single-page Fairloc drawing](https://www.sdp-si.com/D265/PDF/D265P3077.pdf) also lists the M3 cap screw and states that other sizes are available by special order.

The Fairloc manufacturer listing, indexed within the previous week, showed $33.69 each, zero units available and a six-week quantity-table lead time. Live shop access was challenged, so these are indicative figures. [Davall](https://www.davall.co.uk/distribution/) remains the UK supplier route. A 7 mm or 8 mm Fairloc version must be quoted as a factory variant with its own holding data; do not assume that reaming a stock integral wedge preserves its performance.

SDP/SI's [Fairloc guidance](https://www.sdp-si.com/products/Fairloc/fairloc-products.php) makes slip torque dependent on screw torque, bore/shaft clearance, material and finish. Its metric stainless-gear test used a bore within +0.0075 mm, shaft within −0.005 mm, 0.4 µm maximum shaft finish, and a lubricated clamping screw. Those are test conditions for that graph, not tolerances or a rating automatically assigned to the aluminium pulley. The [aluminium-pulley test data](https://sdp-si.com/D820/PDFS/Ref-Pages.pdf) covers larger inch bores and different screws.

## Face-mounted clamp carrier

The [MISUMI alteration rules](https://uk.misumi-ec.com/pdf/fa/2014/P1_1377-1378_F19_EN.pdf) allow three, four or six axial tapped holes using QTC, QFC or QSC. M3, M4, M5, M6 and M8 are selectable; the sketch gives tapped depth 2M. For Shape A, the bolt-circle rule is:

`d + M + 4 <= Q#C <= E - (M + 4)`

At 32 teeth E = 25 mm. Therefore a 7 mm or 8 mm plain bore with four M4 holes on a 16 mm pitch circle satisfies the published envelope: for d8, `16 <= PCD <= 17 mm`; for d7, `15 <= PCD <= 17 mm`. Candidate configuration strings are `GPA32GT3090-A-H7-QFC16-M4` and `GPA32GT3090-A-H8-QFC16-M4`. These are configuration proposals derived from the catalogue, not live accepted quotations. Specify Shape A and plain H bore to omit radial grub screws. At Shape B's 20 mm hub, the corresponding M4 inequalities do not leave a feasible pitch circle.

A checkable carrier proposal is a machined steel or aluminium split-clamp hub with a matching 16 mm PCD, four M4 clearance holes, 7 mm or 8 mm shaft bore, and a concentric locating register against the pulley. Set the pulley screw engagement within the 8 mm nominal tapped depth after allowing for entry chamfers and incomplete threads. The clamp screw belongs in a separate axial hub section so it cannot intersect the face bolts. Carrier diameter, hub length, split geometry, clamp bolt and material remain design variables; there is no published rating for this new assembly.

For a 5.5 N·m proof/design torque, the ideal equal-share tangential force is `T/(4r) = 5.5/(4 × 0.008) = 172 N per face bolt`. This is only a bolt-group load estimate. Clamp slip, face friction, bolt preload, tapped-thread stripping, fatigue and centring must still be checked. A collar resting against the pulley face does not provide this torque path.

The [MISUMI pulley overview](https://uk.misumi-ec.com/pdf/fa/2014/P1_1375-1376_F19_EN.pdf) lists no standard keyless/clamping option for its GT series. Its S3M clamp products use a different profile and are excluded here.

## Rated miniature locking-bush route

The [Mädler MSM catalogue](https://smarthost.maedler.de/datenblaetter/K43_379_EN.pdf) gives the following for **MSM 61520800**:

| Property | Catalogue value |
| --- | --- |
| Shaft / hub bore | 8 mm / 15 mm |
| Flange diameter D1 | 27 mm |
| Lengths L / L1 / L2 | 21.5 / 12 / 25.5 mm |
| Material | Mild steel |
| Mass | 0.04 kg |
| Transmissible torque | 20 N·m at zero axial load |
| Axial capacity | 5 kN at zero transmitted torque |
| Fasteners | Two DIN 912 class 12.9 M4 × 8 socket-head cap screws |
| Required screw tightening torque | 4 N·m |
| Mating tolerances | Shaft k6–h10; hub H8 |
| Approximate shaft / hub pressure | 90 / 70 MPa |
| Concentricity | Approximately 0.02 mm |

There is a [MISUMI UK Mädler MSM product family](https://uk.misumi-ec.com/vona2/detail/221304376389/); exact UK price and dispatch were not verified. The rating and mass above apply to the bush, not a completed pulley assembly.

A concrete packaging candidate is the correct-profile **MISUMI GPT32GT3090-A-H15** steel pulley with this bush. GPT is EN 1.1191-equivalent steel, and a 15 mm plain bore lies within the published 32T Shape-A range. An H7 pulley bore is narrower in tolerance than the bush's H8 requirement, but the actual assembly fit needs checking. This proposal has not been checked in CAD or priced.

The manufacturer PDFs were rendered and visually inspected. MISUMI Shape A has W = 14 mm across its central body/bore and A = 10.3 mm between the 1.85 mm end steps around the tooth span. E = 25 mm describes the central end land; F = 34 mm is the outside of the thin, 1 mm swaged retaining flange. Mädler L1 = 12 mm is the sleeve insertion/contact length, L = 21.5 mm is the body length, and L2 = 25.5 mm includes the protruding screw heads. The 12 mm sleeve can nominally enter a 14 mm bore length, leaving only 2 mm total allowance for chamfers, axial setback and end clearance. The bush's 27 mm flange extends 1 mm radially beyond the pulley's 25 mm end land, so its shoulder must be checked against the swaged flange. Do not count that thin retaining flange as structural hub material. At full 12 mm insertion, the bush projects 13.5 mm including screw heads; nominal combined width is therefore at least 27.5 mm before any clearance gap.

A first strength screen models the narrowest hub section as a smooth open-ended cylinder, ID15/OD25 mm, with Mädler's 70 MPa internal contact pressure. Lamé's inner-wall hoop stress is `70 × (25² + 15²)/(25² − 15²) = 148.75 MPa`; radial stress is −70 MPa, giving a plane-stress von Mises value of 193.49 MPa. This calculation assumes uniform pressure and ignores tooth/end-step stress concentrations, local flange loading and finite contact length. A yield margin of 2 in that simplified model already requires at least 387 MPa certified yield strength. MISUMI's EN 1.1191-equivalent material label does not establish its heat-treatment condition or yield strength. The assembly is therefore **not strength-cleared**. The 5.5 N·m design torque being below the bush's 20 N·m rating does not reduce the installation pressure generated at the specified 4 N·m screw torque.

The [exact Mädler manufacturer page for 61520800](https://www.maedler.de/Article/61520800) showed German stock and a displayed unit price of €37.78 during the check. This is not a verified UK delivery quote. A supplier can resolve the remaining assembly question by approving the 15 mm bore, 12 mm engagement, actual shoulder arrangement and certified pulley material against the locking-bush pressure.

To keep 627 bearings at the input while using this 8 mm bush, a machined shaft could retain 7 mm bearing journals with an 8 mm pulley seat between them; the knee uses an 8 mm seat and 608 bearings. The 8 mm seat must cover the bush's complete shaft-clamping interval from its supplied drawing/STEP, not only an assumed tooth-face span. Check shoulder radii, access for installing the pulley/bush and the ability to slide each bearing onto its own end journal. This changes the input shaft and its assembly sequence. It is an alternative for design review, not an approved fit.

[Belting Online's DL50/7](https://www.beltingonline.com/product/drivelock-50-x-7mm-bore/) is a smaller expansion-ring lead: 7 × 10 × 4.5 mm, 3 N·m; its table lists DL50/8 at 8 × 11 × 4.5 mm and 4.7 N·m. The 7 mm product showed £2.26 excluding VAT and stock. These rings need axial compression hardware and are not self-centring. A single ring does not meet a 5.5 N·m design target.

## Shafts available through UK suppliers

| Exact product | Material / tolerance | Price and availability observed |
| --- | --- | --- |
| [Bosch Rexroth R100000800,400mm, RS 724-3392](https://uk.rs-online.com/web/p/linear-shafts/7243392) | Solid 8 × 400 mm steel shaft; h6; surface hardness 60 HRC | £11.91 excluding / £14.29 including VAT; 104 ready to ship, 53 elsewhere |
| [Ewellix LJM8X400ESSC2, RS 341-1532](https://uk.rs-online.com/web/p/linear-shafts/3411532) | 8 × 400 mm induction-hardened and ground steel; h6; listed 64 HRC; material family Cf53/Ck53/Ck60 | £21.62 excluding / £25.94 including VAT; 27 ready to ship |
| [Ondrives.US GSM7000-900, Raptor UK](https://www.raptorsupplies.co.uk/pd/ondrives-us/gsm7000-900) | 7 × 900 mm, 303 stainless, diameter +0/−0.005 mm, length ±0.25 mm, HRB83; [manufacturer drawing](https://www.ondrivesus.com/documents/categories/shafts-303SS-GS-GSM.pdf) | £49.87 including VAT; 26 listed in stock; displayed delivery 10 September. UK-held inventory not established |
| [CTL432-5331H, BearingBoys BB-64866](https://www.bearingboys.co.uk/Silver-Steel/7mm-x-13inches-Long-Silver-Steel-64866-p) | 7 × 330.2 mm silver steel, BS1407:1970; published diameter tolerance ±0.00635 mm; 207–237 HB, max 285 HB | £3.97 excluding / £4.76 including VAT; in stock |

Raw silver steel can be oversize within its published tolerance. It is machining stock, not a guaranteed sliding fit through a 627 bearing. The hardened 8 mm shafts are useful finished stock, but machining shoulders or cross-features in their hardened skin needs the appropriate process. Bearing-seat fits remain a design choice based on load and rotating ring; nominal diameter alone does not settle them.

## Axial locking collars

[Ruland MCL-7-A](https://www.ruland.com/mcl-7-a.html) and [MCL-8-A](https://www.ruland.com/mcl-8-a.html) are one-piece slit clamp collars, both 18 mm OD × 9 mm wide, requiring up to 22.4 mm hardware clearance. They use 2024-T351 aluminium and one M3 × 8 alloy-steel black-oxide socket cap screw, 2.5 mm hex. Manufacturer screw-seating torque is 2.1 N·m. Mass converted from manufacturer pounds is 5.40 g for 7 mm and 5.13 g for 8 mm. Recommended shaft tolerance is +0/−0.013 mm. These slide on from a shaft end; they are not two-piece collars.

- [RS 591-537, MCL-7-A](https://uk.rs-online.com/web/p/shaft-collars/0591537): £6.69 excluding / £8.03 including VAT; manufacturer stock with displayed ready-to-ship date 14 October 2026.
- [RS 435-0933, MCL-8-A](https://uk.rs-online.com/web/p/shaft-collars/4350933): £5.19 excluding / £6.23 including VAT; 354 ready to ship.

The collar's 2.1 N·m specification is the M3 tightening torque, not a shaft-transmission rating. Collars provide axial location in this arrangement; [Ruland describes the application as stops, spacers and alignment](https://www.ruland.com/solution-shaft-collars-for-gearboxes).

## Parameters for a supplier quotation

Request two metal 32T pulleys, explicitly Gates 3MGT/3GT or SDP GT2/GT3 geometry, for a 9 mm Gates PowerGrip GT3 belt; one 7 mm and one 8 mm shaft interface, or both 8 mm if the stepped input shaft is accepted. State 2.75 N·m peak reversing service and a 5.5 N·m attachment design/proof target if retaining service factor 2. Ask for exact material, dimensions/STEP, bore and shaft tolerance, surface finish, clamping fastener grade/length/type, tightening torque and lubrication, rated continuous/reversing holding torque, minimum slip torque, permissible radial/axial loads, and the rating's safety factor and test conditions. Supply bearing span and belt pretension once fixed.

For Fairloc, identify A 6D53M032DF0906 as the base geometry and request factory-made 7/8 mm versions. For the carrier route, identify the proposed MISUMI face-hole configuration and ask for a rated clamp carrier. For MSM, ask Mädler/MISUMI to approve the 15 mm-bore GT pulley hub geometry and engagement under 70 MPa interface pressure. These are prepared quotation parameters; none has been sent.

## Saved drawings

- `sources/misumi_pulley_alterations.pdf`: official face-hole configuration rules.
- `sources/maedler_msm_miniature_locking_bushes.pdf`: official locking-bush dimensions and ratings.
- `sources/misumi_3gt_pulley_drawing.png`: full rendered official pulley drawing; its PDF remains under the earlier belt-selection package.
- `sources/maedler_msm_drawing.png`: rendered locking-bush drawing showing the roles of L, L1 and L2.
