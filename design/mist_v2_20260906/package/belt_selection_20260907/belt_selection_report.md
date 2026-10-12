# Remote knee belt selection, 7 September 2026

Select **Gates PowerGrip GT3 375-3MGT-09, 9 mm wide, with equal 32-tooth matched metal GT pulleys**. This is a conditional engineering selection for the next CAD variant. No hardware was ordered. The belt capacity calculation passes the supplied working loads; the assembled mechanism remains untested.

The geometry is exact for equal circular pulleys: `C = (375 - 32*3)/2 = 139.5 mm`, `pitch radius = 32*3/(2*pi) = 15.278875 mm`, 1:1 transfer and 16 teeth engaged on each pulley. The JSON records the four transmission inputs needed by CAD. Nominal centre distance does not define final installation tension; provide an adjustable, lockable centre setting and determine assembly travel using actual parts.

## Capacity calculation

Gates' [Light Power and Precision manual](https://www.gates.com/content/dam/documents-library/catalogs/light-power-and-precision-manual.pdf), printed pages 12 and 19, gives a 6 mm base rating, width multiplier 1.64 for 9 mm, length multiplier 1.05 for 348-405 mm, and no mesh reduction above six engaged teeth. I use the lower 30-tooth column to bound the unlisted 32-tooth column conservatively. No interpolation uplift is claimed.

`Corrected capacity = base * 1.64 * 1.05 * 1.0`. Working allowance below divides that capacity by a selected service factor of two.

| Pulley rpm relative to femur | 30T / 6 mm base, N m | Corrected 9 mm capacity, N m | Allowance with SF 2, N m |
| ---: | ---: | ---: | ---: |
| 10 | 4.31 | 7.422 | 3.711 |
| 20 | 4.03 | 6.940 | 3.470 |
| 40 | 3.74 | 6.440 | 3.220 |
| 60 | 3.58 | 6.165 | 3.082 |
| 100 | 3.37 | 5.803 | 2.902 |
| 200 | 3.09 | 5.321 | 2.660 |

At 100 rpm, 2.902 N m exceeds the supplied 2.75 N m upper working peak by 5.5% after the service factor. The 1.24-1.67 N m continuous envelope has more margin. The parent design bounds nominal relative pulley speed near 45 rpm; 100 rpm allows for motion and speed uncertainty. At 200 rpm the same conservative screen falls below 2.75 N m, so this is not an unrestricted speed/torque guarantee.

Full servo stall is a separate case. `30 kg cm * 0.0980665 * 2 = 5.884 N m` ideally reaches this stage before losses, voltage variation and servo tolerance. It exceeds the supplied working peak. Gates' servo guidance permits an intermittent-stall check at SF 1 plus a separate running-load service factor (printed page 63). The lowest table row is 10 rpm, not zero. The belt table therefore does not certify a stalled or impacted leg. Retain conditional current/torque limits, detect sustained stall, and validate the combined pulley, hub, shaft and frame response before raising limits. Ground impact can back-drive the belt independently of commanded motor torque.

## Metal pulleys and supply

The exact Gates catalogue counterpart is **3MR-32S-09**. A UK-priced belt is available from [BearingBoys](https://www.bearingboys.co.uk/3M-Poly-Chain-PowerGrip-GT3-Timing-Belts-/GT3-3753MGT9-Gates-PowerGrip-GT3-Timing-Belt-344100-p) at **GBP14.30 including VAT**, approximately 8-10 working days, or [Rubix UK](https://uk.rubix.com/en/powergrip-gt3-belt/p-G1129009370) at **GBP13.37 including VAT**, usually within 14 working days. Delivery is additional. See [supplier notes](supplier_notes.md) for the exact European product code and page evidence.

For the pulley pair, first obtain a quote for Gates 3MR-32S-09 or **SDP/SI A 6A53M032DF0906** from [Davall](https://www.davall.co.uk/distribution/). The [SDP/SI drawing](https://shop.sdp-si.com/media/pdf/80502158.pdf) explicitly identifies GT2/GT3 compatibility. Its supplied 6 mm bore can be machined to the selected 7 mm input and 8 mm knee shafts, subject to runout and hub checks. No verified current GBP pulley price was obtained.

[MISUMI GPA32GT3090-B-P7](https://uk.misumi-ec.com/vona2/detail/110302193560/?HissuCode=GPA32GT3090-B-P7) supplies the input bore directly; the corresponding P8 configuration fits the new knee diameter. P7 was displayed at EUR27.63 excluding VAT, ten working days from Frankfurt. P8 price was not checked. This storefront serves business customers. Its [official catalogue](https://uk.misumi-ec.com/pdf/fa/2014/P1_1383-1384_F19_EN_001.pdf) states Gates Unitta 3GT compatibility. Confirm the exact belt pairing on the quotation; a 3 mm HTD part or anonymous GT2 listing is not a substitute.

The MISUMI 32T version has OD29.8 mm, flange34 mm, 10.3 mm belt face, 14 mm flange assembly width and 22 mm total B-shape length. Its envelope is wider than the belt. Use the actual selected supplier drawing when closing the CAD stack. Retention by two small set screws still needs a holding-torque check; a belt tooth rating does not rate the shaft connection.

## Support and printed prototype limits

Calculated starting preload at 2.75 N m is about **109 N per span**, giving approximately **218 N radial shaft load** in the symmetric two-pulley arrangement. This uses the low-speed term of Gates' tension equation (printed page 65). It is an initial estimate for a measured tension test, not a final installation instruction.

The parent CAD now selects a supported 7 mm input shaft with 627 bearings and an 8 mm knee shaft with 608 bearings. For comparison, ideal solid-shaft torsion at 2.75 N m gives 219 MPa at 4 mm, 40.8 MPa at 7 mm and 27.4 MPa at 8 mm. These calculations exclude bending, notches, material fatigue, bearing fits and fastener loads. They support dropping the earlier 4 mm torque-shaft assumption but do not certify either revised shaft.

Use FDM pulley teeth for a prototype only. No exact 32-tooth manufacturing profile or public STEP was obtained. The saved MISUMI PDF was rendered and inspected; its visible groove sketch supplies a 0.381 mm pitch-line offset and a 1.14 mm depth, and warns of tooth-count dependence. Hidden text extracted from that PDF includes other arc dimensions which are not visible in the relevant sketch and must not be used as profile evidence. A printed contour does not inherit Gates' drive rating. Keep reinforced commercial belts and matched metal teeth for the rated-load build; printed carriers, guards and alignment fixtures remain useful.

## Runner-up

A genuine catalogue **364-2MGT-09 with equal 40-tooth pulleys** gives 142 mm centres and a 12.732 mm pitch radius. At 100 rpm, conservatively using the 38T base gives `2.10 * 1.64 * 1.10 = 3.788 N m`, or **1.894 N m with SF 2**. That covers the stated continuous envelope but fails the 2.75 N m working-peak criterion used here. Exact 360-2MGT was not present in Gates' standard-length table. The 3MGT selection offers the better margin without materially changing the femur length.
