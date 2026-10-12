# Supplier notes for the 375 mm GT3 drive

Checked on 7 September 2026. Design update after supplier intake: the parent CAD now selects a 7 mm input shaft and an 8 mm supported knee shaft. References below to the earlier 4 mm knee describe the superseded comparison only. Scope: one Gates PowerGrip GT3 375 mm × 3 mm pitch × 9 mm belt and two matching 32-tooth GT pulleys. Prices are the supplier's displayed unit prices, excluding delivery unless stated. No purchase or quotation request was submitted.

The belt has two clear UK ordering routes. A matching 7 mm bore pulley can be ordered through MISUMI's UK storefront, which dispatches this configuration from Frankfurt and restricts sales to business customers. No complete kit was verified as immediately available from UK-held stock. Davall is the UK quotation route for the SDP/SI pulley with the clearest explicit GT3-compatible dimension drawing.

## Belt

| Supplier and exact item | Price observed | Availability observed | Assessment |
| --- | --- | --- | --- |
| [BearingBoys GT3 375-3MGT-9, BB-344100](https://www.bearingboys.co.uk/3M-Poly-Chain-PowerGrip-GT3-Timing-Belts-/GT3-3753MGT9-Gates-PowerGrip-GT3-Timing-Belt-344100-p) | £11.92 excluding VAT; £14.30 including VAT | Approximately 8–10 working days; next-day delivery unavailable | Clearest UK retail route. Page confirms 125 teeth, 375 mm pitch length, 9 mm width, and reference 9400-53320 / 375-3MGT3-9. |
| [Rubix UK GT3 375 3MGT 9, 101A6662](https://uk.rubix.com/en/powergrip-gt3-belt/p-G1129009370) | £11.14 excluding VAT; £13.37 including VAT | Usually arrives within 14 working days | Refreshed product page confirms manufacturer 940053320, 3mgt profile, 3 mm pitch, 125 teeth and 9 mm width. |
| [Raptor Supplies UK Gates 375-3MGT-09, BG6HYM](https://www.raptorsupplies.co.uk/pd/gates/375-3mgt-09) | £13.87 including VAT per belt | Limited availability; check availability; quantities must be multiples of 20 | Poor fit for a single prototype. Title incorrectly says 104 teeth, while specifications give 125. Older indexed price was £13.70; refreshed page price above takes precedence. |

Gates' [2024 European catalogue](https://www.gates.com/content/dam/documents-library/catalogs/industrial-power-transmission-catalogue-en.pdf), printed page 190, identifies 375-3MGT3-9 as product 9400-53320, 125 teeth, 375 mm pitch length, 9 mm width. This is the current European ordering code behind the first two listings. The US catalogue uses 375-3MGT-09 / 9400-4125 for the same nominal size. Supplier part numbers should accompany the length/pitch/width description.

[BEP's nominally matching listing](https://bepltd.com/products/375-3mgt-9-gates-powergrip-htd-timing-belt) identifies Gates 9400-53320 but labels the pitch HTD3M and asks customers to contact it for availability. Its live page was returned in euros while an older search result showed pounds. It is not used for a current GBP price or profile decision.

## Pulleys

| Supplier and exact item | Price and supply | Bore implications | Drawing / CAD |
| --- | --- | --- | --- |
| [MISUMI GPA32GT3090-B-P7](https://uk.misumi-ec.com/vona2/detail/110302193560/?HissuCode=GPA32GT3090-B-P7) | Live UK storefront: €27.63 excluding VAT; €32.88 including VAT as displayed. Shipping estimate 18 September 2026, described as 10 working days, from Frankfurt. Two pulleys are €55.26 excluding VAT before delivery. | 32 teeth, 3GT, 9 mm belt, aluminium, B shape, 7 mm round bore with tapped set-screw holes. Current B/P configuration permits 6–10 mm bores in 1 mm increments. Direct for 7 mm; 4 mm requires a reducer or shaft change. | [Official dimension/profile PDF](https://uk.misumi-ec.com/pdf/fa/2014/P1_1383-1384_F19_EN_001.pdf). CAD button opens login/register; exact STEP not obtained. |
| [SDP/SI A 6A53M032DF0906](https://shop.sdp-si.com/a-6a53m032df0906.html), via [Davall UK](https://www.davall.co.uk/distribution/) | Exact UK price and stock not publicly verified. Davall is the official distributor for this route, also supported by [SDP/SI's representative list](https://sdp-si.com/contact-forms/). | Explicit 32-tooth GT2/GT3 pulley for 9 mm belt with 6 mm bore. Bore needs machining for 7 mm or 8 mm, or a reducer for 4 mm. Bore changes remain a machining/fit decision. | [Official SDP/SI drawing, 80502158.pdf](https://shop.sdp-si.com/media/pdf/80502158.pdf), Figure 2. Public exact STEP not obtained. |
| [Ondrives P32-3GT-BLP-9C-8](https://ondrives.com/3gt-blp-9-pulley-3mm-pitch-9mm-belt-width/p32-3gt-blp-9c-8) | Exact UK product listing; live page did not expose price, stock, ordering control or STEP. Treat as a quotation route. | 32 teeth, 3GT, 9 mm belt, 8 mm bore; both existing shafts require adaptation unless changed to 8 mm. | Product listing confirms GT synchronous miniature pulley. |

MISUMI Europe states that it sells to businesses, tradespeople, freelancers and public institutions, excluding private individuals. The UK storefront displayed euro prices and an inclusive-VAT figure consistent with 19% VAT. These figures are recorded as displayed; they are not a UK landed-cost quote. [MISUMI UK storefront](https://uk.misumi-ec.com/vona2/detail/110302193560/?HissuCode=GPA32GT3090-B-P7)

The [indexed SDP/SI manufacturer page](https://shop.sdp-si.com/a-6a53m032df0906.html), last crawled one month before this check, showed $13.56 and 120 units in stock for A 6A53M032DF0906; its quantity-price table also showed a six-week lead time. The live shop lookup was challenged, so those figures are indicative only and are not treated as current stock or a confirmed alternative price. No currency conversion or landed GBP estimate was made.

## Dimensions for CAD packaging

The [MISUMI catalogue](https://uk.misumi-ec.com/pdf/fa/2014/P1_1383-1384_F19_EN_001.pdf) identifies compatibility with Gates Unitta 3GT. For 32 teeth: pitch diameter 30.56 mm, outside diameter 29.80 mm, hub diameter 20 mm and flange diameter 34 mm. For a 9 mm belt: A = 10.3 mm, W = 14 mm, and B-shape overall L = 22 mm. Two M4 set screws apply in this bore range. The catalogue warns that tooth-groove dimensions vary slightly with tooth count.

The [SDP/SI Figure 2 drawing](https://shop.sdp-si.com/media/pdf/80502158.pdf) explicitly specifies GT2/GT3 pulleys. A 6A53M032DF0906 has 32 teeth, 3 mm pitch, 9 mm belt capacity, 6 mm bore (+0.025/0 mm), 30.6 mm pitch diameter, 29.8 mm OD, 33.6 mm flange diameter, 21.6 mm hub diameter, 20.6 mm overall length, 7.8 mm hub projection and two M4 set screws at 90 degrees. These are supplier dimensions rounded as printed, not exact values reconstructed from pitch.

The exact Gates-branded counterpart is 3MR-32S-09, product 7843-6012. Gates' [Light Power and Precision Drive Design Manual](https://www.gates.com/content/dam/documents-library/catalogs/light-power-and-precision-manual.pdf), printed page 32, lists it as an aluminium 3 mm GT sprocket for 9 mm belt, with a 6.35 mm minimum plain bore and 15.875 mm maximum bore. No current exact UK retail price or stock was verified. The minimum bore permits machining to 7 mm; using it on the existing 4 mm shaft requires an adapter or shaft change.

These catalogue drawings support pulley envelope and shaft-interface design. They do not establish a verified exact tooth-groove manufacturing contour. Do not substitute an HTD groove merely because its pitch is 3 mm. For example, [RS OPTIBELT 323M9](https://uk.rs-online.com/web/p/belt-pulleys/2365631) is explicitly HTD and is excluded from this matched-GT selection.

## Saved evidence

- `sources/misumi_3gt_pulleys.pdf`: downloaded official MISUMI catalogue, SHA-256 `E853607B2DEC580449DD44BECCCF0D3ADDFE3244A7DD1778879B35394EE193EF`.
- `sources/misumi_live_20260907.txt`: live MISUMI browser-page evidence for the exact 7 mm configuration.
- SDP/SI drawing remains available by its official URL above. Direct local download encountered the supplier's browser challenge; no local PDF or STEP is claimed.

The proposed 360-2MGT alternative was not pursued after the main selection confirmed the 375 mm / 3MGT route. Exact 360 mm length was not verified as a standard Gates GT3 2MGT belt.
