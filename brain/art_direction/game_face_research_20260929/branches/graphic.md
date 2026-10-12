# Graphic and cutout face references

Four references are ready for the board: **Night in the Woods** for gaze and high-contrast eye design, **Wandersong** for action-linked expression, **Chicory** for expression and pose studies by a verified character animator, and **Pikuniku** as a minimal-face/body-language limit case. Their different drawing styles matter less than the acting choices we can test in MIST.

The accompanying JSON keeps observation, creator testimony and our proposed adaptations separate. All `motionVerified` fields are false: I inspected source images and sampled GIF frames, but did not continuously perceive the animations. No frame counts or exact timestamps are claimed.

## Night in the Woods

[The official PLAYISM screenshot](https://playism.com/wp-content/uploads/2021/05/nitw_en_03-800x450.jpeg) is the strongest graphic face tile. Its large colored eyes dominate the characters' dark faces; tiny mouths leave the gaze easy to read. This supports a useful MIST experiment: settle the eyes on a target, hold that attention, and let mouth changes punctuate an event.

[Scott Benson's direct interview](https://www.inverse.com/article/13084-this-video-game-creator-proves-late-night-twitter-isn-t-a-waste-of-time) confirms that he did art and animation and that Charles Huettner contributed animation. It does not establish who animated a specific shot. [His PlayStation post](https://blog.playstation.com/?p=133410) independently identifies him as co-designer and art director. [Nuke Possum Springs](https://www.youtube.com/watch?v=Xzhe45Q8780) is the official GDC postmortem linked by GDC's sibling publication; I verified its provenance, not its contents as a facial-animation lesson.

## Wandersong

[The first official GIF](https://wanderso.ng/img/screens/01.gif) gives a small, concrete example: the sampled singing pose has closed eyes and an open mouth while the note wheel surrounds the bard. The face and action communicate the same thing. [The third GIF](https://wanderso.ng/img/screens/03.gif) supplies an additional character-context reference. Both URLs were present in the [official site](https://wanderso.ng/) and returned HTTP 200 with an image/gif content type.

[Lobanov's IGF interview](https://www.gamedeveloper.com/business/road-to-the-igf-greg-lobanov-s-i-wandersong-i-) explains the production reason for the style: easily made assets allowed distinct emotional variations across scenes, while roughness encouraged play. For MIST, the inference is to author expressive event poses before smoothing them. A singing or acknowledgement face should remain readable when frozen.

Credit caution: the official site calls Greg Lobanov the creator. Do not credit Alexis Dean-Jones as Wandersong's animator. The primary sources found here verify her animation work on Chicory instead.

## Chicory

The [dog sketchbook](https://community.wacom.com/en-us/wp-content/uploads/sites/40/2020/01/1473899aad3904e92e7c03e3ec438933_original.png) and [character study sheet](https://community.wacom.com/en-us/wp-content/uploads/sites/40/2020/01/e43be3de2c2c2ebae1488de3e1f8d54d_original.png) are unusually useful moodboard references because they expose expression choices outside polished gameplay. Both were visually inspected. Treat them as pose design, with no implied production timing.

[Dean-Jones's own biography](https://www.alexisdeanjones.com/about) confirms character design and animation on Chicory; the [official game site](https://chicorygame.com/) calls her Artist & Animator. The [Wacom interview](https://community.wacom.com/en-us/designing-chicorys-creatures-with-alexis-dean-jones/) contains her craft discussion and the drawings. The MIST adaptation is ours: coordinate eye aperture, mouth silhouette and orientation around a single feeling, then test transitions between those clear states.

## Pikuniku

[The official press kit](https://pikuniku.net/presskit/sheet.php?p=pikuniku) gives Arnaud De Bock's exact credit as Game Design/Art/Producer and Rémi Forcadell's as Game Developer/Writer. Neither is relabeled Animator here. In a [direct creator interview](https://www.nintendolife.com/news/2017/09/feature_picking_apart_the_mind_behind_the_delightful_dystopia_of_pikuniku), De Bock explains that minimal aesthetics direct attention toward character appearance and body language.

The [official rhythm-game GIF](https://pikuniku.net/presskit/pikuniku/images/rhythmgame.gif) is live (HTTP 200, image/gif). The homepage also supplies a [header GIF](https://pikuniku.net/images/header_60.gif), which fetched but did not render in the image tool. Treat both as media to inspect manually, not verified facial-motion analysis. I inspected [screenshot 5](https://pikuniku.net/presskit/pikuniku/images/pikuniku_screenshot_5.png): the tilted red body, bent legs and two eye dots convey a swimming pose with no visible mouth. Its small face makes it a weak lead tile, despite the useful principle.

[Pictoplasma's conference page](https://conference.pictoplasma.com/uncategorized/pikuniku/) describes De Bock's 2017 talk on procedural animation and empathy. [ZHdK's announcement](https://gamedesign.zhdk.ch/news/arnaud-de-bock-confirmed-speaker-of-the-conference-interactive-experiences-at-ludicious-x/) identifies his later talk on character empathy and accessibility. These establish worthwhile craft leads; their recordings were not inspected.

## Deferred: Donut County

The [official site](https://www.donutcounty.com/) verifies Ben Esposito as creator and embeds [this trailer](https://www.youtube-nocookie.com/embed/er2DMi6NUwE?rel=0&controls=1&showinfo=0). It does not provide a specific animator credit. Its HTML references `images/raccoon_scooter_loop.gif`, but a direct request returned 404. **Do not embed that GIF.**

I inspected the site's [under-hole illustration](https://www.donutcounty.com/images/dc_underhole.png), but it offers less facial information than the three selected references. Donut County remains a useful lead for manually viewing dialogue reactions, not a strong evidence-backed face-animation entry in this pass.

## Verification limits

Official HTML supplied media URLs; none were constructed from guessed filenames. Browser screenshots sampled Wandersong 01/03 and Chicory's puzzle GIF. The two Chicory sheets and the PLAYISM still were also inspected as images. Browser navigation later stalled on a publisher image, so the report does not claim successful video playback or continuous GIF viewing. The board should keep a visible distinction between a supplied animation file and verified motion analysis.
