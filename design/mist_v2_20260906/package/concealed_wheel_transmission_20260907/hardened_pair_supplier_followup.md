# Hardened SM1-20 pair: supplier and shaft-attachment follow-up

Checked 7 September 2026. Requirement: two KHK SM1-20H gears per leg, eight for four legs, with a dependable 6 mm shaft attachment. This note preserves the separate CAD/STEP verification already completed by the main task. No supplier contact or purchase was made.

**Exact UK price and delivered lead time for SM1-20H remain unverified.** The standard SM1-20J6 attachment option is confirmed, but the current SM-specific catalogue excludes its J-series products from Hardened Plus. Do not treat SM1-20HJ6 or SM1-20J6H as an established catalogue solution.

## Supplier result

| Route checked | Verified result | What it does not establish |
| --- | --- | --- |
| [RAR Gears UK, SM1-20](https://www.rargears.com/gears/miter-gears/steel-miter-gears/SM1-20) | £14.13 each for quantities 0–9; 10–14 days subject to manufacturer availability. The page explicitly says no heat treatment and tooth hardness below 194 HB. | This is the plain gear. Neither its price nor its lead time is assigned to SM1-20H. |
| RAR exact H listing search | No functioning exact SM1-20H product page with a current price/delivery commitment was verified. RAR hosts KHK's catalogue and sells the base SM series. | No exact H stock quantity, hardened surcharge, machining charge or UK delivery date. |
| MISUMI UK and RS exact-part searches | No verifiable current SM1-20H listing with UK price/lead was found in this bounded check. | This is a research limit, not evidence that the suppliers cannot quote it. |
| [KHK exact manufacturer SM1-20H page](https://catalog.khkgears.us/item/miter-gears/steel-miter-gears-sm/sm1-20h) | Establishes the H product identity, nominal 6 mm plain bore, S45C material and 50–60 HRC tooth hardness. | The fetched pricing/inventory fields were unexpanded placeholders. They are not zero prices or usable availability data, and this is not a UK quote. |

The [KHK Hardened Plus service information](https://khkgears.net/pdf/2025/front-back.pdf), pages 22–23, describes hardening completed in four working days. That is a factory processing interval, not a delivered UK lead time; base-gear availability, any machining, final inspection and shipping still apply. The [RAR-hosted KHK catalogue](https://www.rarodriguez.co.uk/wp-content/uploads/2023/10/KHK-2023-Final.pdf) also documents the service, but its general J-series statement cannot override the current SM-series exclusion below.

Budget the hardened gear and attachment as an unquoted line. If a supplier confirms a finished unit price P, the gear subtotal is 2P per leg or 8P for four legs. Do not substitute 2 × £14.13 or 8 × £14.13 as the hardened cost. VAT, delivery and any setup/finishing charges need the same quotation.

## Exact model distinctions

| Model | Tooth condition | Bore and shaft attachment | Status |
| --- | --- | --- | --- |
| SM1-20 | Unhardened S45C, below 194 HB | Nominal 6 H7 plain bore; no standard locking feature | Plain catalogue gear |
| SM1-20H | Hardened Plus, tooth induction hardening to 50–60 HRC | Nominal 6 mm plain bore; original H7 tolerance can degrade during hardening | Hardened catalogue service; exact UK price/lead not verified |
| SM1-20J6 | Unhardened S45C | 6 H7 bore; M4 radial set-screw provision; no keyway at this bore | Documented J-series modification |
| SM1-20HJ6 / SM1-20J6H | Not established | Do not assume either suffix order creates a valid combined product | SM catalogue excludes Hardened Plus for its J-series lineup |

The controlling source is the [current KHK SM catalogue](https://khkgears.net/pdf/sm.pdf), pages 330–331; the same series information appears in the [2025 miter catalogue](https://khkgears.net/pdf/2025/miter-gears.pdf). Its specific note excludes Hardened Plus for products in the J-series lineup. A specially quoted factory part might resolve the requirement, but the catalogue does not establish its availability or ordering code.

For SM1-20J6, the J table and B3T drawing show an M4 tapped radial hole at **L = H/2 = 4 mm from the rear hub face**, with hub width H = 8 mm and hub diameter 16 mm. The nominal bore is 6 mm. Some US catalogue metadata calls J6 B2K; that conflicts with the tapped/no-keyway arrangement in the manufacturer's series drawing and should not drive the interface design.

No rated shaft-holding torque or set-screw installation torque was found for J6. The catalogue does not settle the screw point, length, material/grade or the exact delivered screw specification in the inspected table. Obtain those details rather than selecting a tightening torque from the M4 designation alone. Gear-tooth surface-durability values, such as approximately 0.084 N·m plain and 0.37 N·m hardened, do not rate the shaft attachment.

## Factory work and home hand-tool viability

KHK's [miter machining precautions](https://khkgears.net/pdf/miter-tech.pdf), pages 312–313, use the bore as the machining datum, restrict machining in hardened tooth/root areas, and address final machining where heat treatment has disturbed bore tolerances. The [Hardened Plus precautions](https://khkgears.net/pdf/2025/front-back.pdf) warn that gear precision and the original H7 bore tolerance degrade after hardening.

For a plain, unhardened S45C hub, drilling and tapping an M4 radial hole is materially plausible with proper tooling, a drill guide and rigid workholding. That does not harden its teeth or validate the attachment. A hand-held drill cannot be assumed to preserve the required shaft fit and concentricity when enlarging or restoring a bore.

For the H gear, the teeth are hardened but the exact extent of the hardened zone around this small hub is not established by the material label. Do not promise that the radial hole is easy to drill after hardening, and do not machine through the tooth/root region. Achieving a finished concentric bore after heat treatment is a precision machining/inspection task, not a dependable hand-tool-only operation.

The credible purchasing question is a **factory-finished hardened miter gear with the required shaft interface**, with its final dimensions and holding performance confirmed. Ask whether KHK/RAR can make the radial feature before hardening, then inspect or finish the bore afterward; the answer must be specific to this SM geometry. This is a custom-process question, not an assertion that J6 plus H is supported.

## Prepared quotation specification, not sent

Request eight finished gears for four 1:1 right-angle pairs, using SM1-20H tooth geometry and hardened condition. Specify a 6 mm mating shaft and the final bore tolerance/concentricity required by the assembly, not just the pre-hardening H7 label. Ask for a factory M4 radial attachment equivalent in location to the J6 drawing, or a supplier-supported alternative, with screw type, length, point, grade, installation torque and minimum reversing holding torque.

Include the actual shaft material/diameter tolerance/flat geometry, working torque and short-duration overload limit, mounting distance and axial retention arrangement. Ask the supplier to confirm machining/heat-treatment sequence, final bore inspection, unit/setup price, VAT/delivery and the lead time for all eight finished parts. Until that is answered, the hardened tooth choice can remain a CAD/design candidate but its purchasable shaft attachment and cost are unresolved.
