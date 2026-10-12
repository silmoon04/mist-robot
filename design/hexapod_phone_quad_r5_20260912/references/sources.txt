# Original hexapod reference

Inspected 12 September 2026. This record separates creator statements, observed video geometry and design inferences. The Browser skill supplied the supported browser workflow; the Unslop skill guided the prose.

## Identity and source links

- [3D Printed RC Hexapod Spider Robot](https://www.youtube.com/watch?v=ciE2Z_92T7s), by [Emre Kalem](https://www.youtube.com/@emrekalemtech). YouTube oEmbed verified title and channel. The original description was also retrieved directly.
- [Hexapod Spider Robot with Servo & Arduino, MakerWorld model 1973965, profile 2122819](https://makerworld.com/en/models/1973965-hexapod-spider-robot-with-servo-arduino#profileId-2122819). The working browser page identified Emre Kalem as designer and showed release date 2025-11-08.
- The creator's description links [source code](https://drive.google.com/file/d/1bIMGIhBOq_qt7qGt7REMtUuWCw7WB5hj/view?usp=sharing), [PCB Gerbers](https://drive.google.com/file/d/10F6qPQ1kVP-xbSKdnUb0b_vhInIYOMQE/view?usp=sharing) and [schematic](https://app.cirkitdesigner.com/project/f2cca481-7fbb-4e6d-9743-3ebf409ca84c). These were identified but not downloaded or inspected in this research pass.

## Creator statements

The original uses six legs with three degrees of freedom each, 18 MG996R 180-degree servos, Arduino Mega, NRF24L01 remote control and tripod gait. The parts list includes 18 type-695 bearings, 90 M3x6 screws, 90 M3x10 screws, XL4016 regulator and a 3S 2200 mAh LiPo. The description credits Özgür Toprak Önsoy for contributions. MakerWorld still describes software development as ongoing.

The designer print profile shows PLA, 0.2 mm layers, three walls, 10% infill, 29.4 hours and 1155 g. These are whole-profile figures shown by MakerWorld, not a weighed robot, and the profile may include controller parts. No measured link lengths, complete assembled dimensions or mass distribution were available in the inspected pages.

## Direct visual evidence

Screenshots are captured from ordinary browser playback of the creator's video. The video was sampled at selected assembly moments, not watched end to end. No remote media stream was downloaded.

- `video_00m00.png`: full assembled front silhouette. Faceted central shell with a broad top and sloped shoulders; six radial legs; exposed servo bodies; tapered curved distal legs ending in narrow contact tips.
- `video_04m42.png`: partial overhead view of flat body plate, perimeter bearing seats and servo cable routing.
- `video_07m04.png`: partial assembly close-up at approximately 7:03, showing servo brackets and cable exits. The filename is rounded.
- `video_09m25.png`: overhead assembly at approximately 9:25. Six repeated servo/link units and separate circular horn pieces lie beside the chassis; a handheld servo tester is in use.
- `video_11m46.png`: overhead assembly with exposed electronics. Each radial chain has servo bodies and an open rigid yoke. Separate long distal pieces have a U-shaped proximal fork and a broad blade tapering toward the foot. This is the clearest assembly reference.

The broad open yokes support a pivot on both sides of the servo rather than hanging the entire distal blade from a thin single tab. This is a visual interpretation; bearing fits and load paths were not measured.

## Bounded comment sample

The first loaded YouTube comment batch was inspected, including one expanded build comment. A bounded set of already visible MakerWorld comments was also read. These reports are anecdotes, not verified defects in every build.

- [YouTube comment by @Shadow-wq6rg](https://www.youtube.com/watch?v=ciE2Z_92T7s&lc=UgzJbl0s0XSuul2BbOZ4AaABAg) reports horn/link screws protruding far enough to contact and gouge servo cases. The same builder reports a cramped cable slit around 7:05.
- [YouTube comment by @ThuanDuong-pv3xu](https://www.youtube.com/watch?v=ciE2Z_92T7s&lc=UgwZBqt8JU0rFxK8a7d4AaABAg) questions using small jumper wiring for servo power. Its reference to 12 servos differs from the creator's 18-servo specification, so it is only a prompt for electrical review.
- MakerWorld commenter @deadpohl describes replacing troublesome MG996R servos and changing the controller architecture. An early @lsmelvin comment asked for fuller assembly instructions and a BOM; later creator replies point to the published video and code.

## Implications for the new four-leg build

These are design inferences, not creator specifications: preserve the faceted shell, open supported joints and curved tapered distal legs to keep the reference recognisable. Re-engineer mounting around the actual STS3215 C018 hardware. Reserve clearance behind every fastener and provide accessible cable exits with enough space for moving cable loops. Keep the phone and rotation hardware near the centre, and review their mass separately. Whole-profile print weight does not establish an allowable phone payload.

## Original file access and licence

The MakerWorld UI offered Download 3MF. Clicking it normally reached the creator file CDN, but the browser displayed ERR_BLOCKED_BY_CLIENT and stated that Comet blocked the page. No bypass was attempted. No STEP, STL or 3MF file was acquired, so this record does not claim original geometry was imported or measured. The browser page itself remained available for reference.

The model page's expanded licence panel says Standard Digital File License. It prohibits distributing the object or derivative works in digital or printed form and charging without permission. Retain this attribution with personal reference work; no permission to publish the original or a remix was obtained. This is a record of the displayed terms, not a broader legal determination.
