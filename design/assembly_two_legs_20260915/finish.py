"""Write a two-leg inventory and caption the native Fusion assembly recording."""
from pathlib import Path
import json,csv,subprocess,sys,zipfile,hashlib
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'fusion'

def stamp(frame,fps):
    t=frame/fps;hours=int(t//3600);minutes=int(t%3600//60);seconds=t%60
    return f'{hours}:{minutes:02d}:{seconds:05.2f}'

def main():
    report=json.loads((OUT/'animation_report.json').read_text());assert report['status']=='completed'
    head='''[Script Info]
ScriptType: v4.00+
PlayResX: 960
PlayResY: 820
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,Arial,25,&H00FFFFFF,&H00FFFFFF,&H00202020,&H00202020,1,0,0,0,100,100,0,0,1,1,0,8,20,20,12,1
Style: Note,Arial,19,&H00FFFFFF,&H00FFFFFF,&H00202020,&H00202020,0,0,0,0,100,100,0,0,1,1,0,2,24,24,18,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    captions=[]
    for row in report['stages']:
        start,end=stamp(row['first_frame'],8),stamp(row['last_frame']+1,8)
        captions.append(f'Dialogue: 0,{start},{end},Title,,0,0,0,,{row["title"]}')
        captions.append(f'Dialogue: 0,{start},{end},Note,,0,0,0,,{row["note"]}')
    (ROOT/'captions.ass').write_text(head+'\n'.join(captions)+'\n')
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-framerate','8','-i','fusion/frames/%04d.png','-vf','pad=960:820:0:50:color=0x20282c,ass=captions.ass','-c:v','libx264','-pix_fmt','yuv420p','-y','Assembly_9_Steps.mp4'],cwd=ROOT,check=True)
    text='''# Assemble your two overnight leg sets

Yes, printing the same latest overnight plate twice gives two usable sets of eight leg parts. A second leg does not require a mirrored STL set. Both sets must use a matching upper/lower coxa revision; the latest centred DFM set is shown in the animation. Do not mix an older short lower arm with the newer 82 mm coxa.

The overnight plate was deliberately incomplete because the bench fixture and some previously printed pieces were excluded. You printed 16 parts altogether, but two complete leg mechanisms need another 12 printed pieces outside those plates, some of which you already have.

| Printed piece outside the overnight plate | Per leg | Total for two legs | Reuse status |
| --- | ---: | ---: | --- |
| Yaw servo saddle | 1 | 2 | Older clamp case fit was good, but M3x30 nut engagement still needs checking because the old nut seat is shallower. |
| Yaw servo flat cap | 1 | 2 | Earlier matching flat cap is identical to the current one. If you have one, you need one more. |
| Nominal 11.6 mm yaw spacers | 4 | 8 | Reuse a uniform nominal set. If you have four, you need four more. Do not mix the 11.3/11.9 comparison pieces or fixture spacers. |

The large ribbed bench base is optional test equipment and is not part of the final robot. You can assemble the joints without printing it, but restrain the yaw base securely for powered testing. Final body mounting and full-robot load qualification remain separate work.

## Hardware

For two complete legs, excluding any bench/body mounting fasteners: six STS3215 servos, six main metal horns, six auxiliary discs and their matching centre retainers. The ordinary fastener totals are:

| Hardware | Per leg | Two legs |
| --- | ---: | ---: |
| M3x30 screws | 12 | 24 |
| M3x20 screws | 6 | 12 |
| M3x12 screws | 8 | 16 |
| M3x6 screws for peripheral horn holes | 12 | 24 |
| M3 nuts | 14 | 28 |
| Flat washers at the specified thickness | 53 | 106 |

Use the supplied special centre retainers in addition to these screws. No M3x50 screws, heat inserts or belts are required. The specified screw engagement assumes 0.5 mm flat washers. You measured about 7.7 mm outside diameter, but thickness remains unconfirmed. Split lock washers are not substitutes.

## Assembly order

1. Remove the brim and remaining supports. Check that the nut slots are clear and the nuts slide in without hammering. Keep the small integral print foot and the structural ribs: these belong to the part.
2. Prepare the yaw base. Put the servo in its separate saddle, add the flat cap and three M3x30 screws with one washer each and three nuts. Leave the intended cap gap; do not crush it closed.
3. Fit the yaw main and auxiliary discs with their matching centre retainers. Attach the upright coxa to the main horn with four M3x6 screws and one 0.5 mm washer each. The auxiliary centre washer bears against the fixed stub, not against the rotating disc; the disc must remain free.
4. Slide the two post nuts into the coxa's side slots before installing the lower arm. Fit the hip servo with its case extending inward and pivot at the outward end. Attach its cap using three M3x30 screws, three nuts and one washer per screw.
5. Put four nominal 11.6 mm printed spacers between the yaw auxiliary disc and lower arm. Four M3x20 screws pass through the recessed seats, two 0.5 mm washers per screw, the arm and the spacers, into the auxiliary disc. Two additional M3x20 screws with one washer each join the lower arm to the post nuts. Seat the assembly by hand before tightening; do not use screws to force the fork into alignment.
6. Load the femur bridge nut through its slot. Fit the hip discs and centre retainers, then attach the main femur bracket to the main horn with four M3x6 screws and one washer each. Put the knee servo into the integrated saddle and fit its cap with three M3x30 screws, nuts and one washer each.
7. Fit the femur auxiliary cheek with its integral annular stand-off facing inward. Attach it to the auxiliary disc with four M3x12 screws and TWO 0.5 mm washers each. Close the bridge with one M3x30 screw and one washer into the captive nut. Do not add loose pitch spacers under the integral ring.
8. Load both tibia bridge nuts. Fit the knee discs and centre retainers. Attach the straight tibia main piece to the main horn with four M3x6 screws and one washer each. Fit the tibia auxiliary cheek with four M3x12 screws and TWO washers each, then close the bridge with two M3x30 screws and one washer each.
9. Route the bus cables away from the discs and moving gaps, leaving a flexible loop at each joint. Verify unique servo IDs and centres before fixing the final horn orientation. The temporary case-to-horn alignment gauge must be removed before movement. Begin with small slow movements on one restrained, unloaded leg.

Case clamps hold the servo bodies; horns, cheeks and connecting bridges move around the shafts. Never tie a moving cheek to the stationary case with the temporary gauge. The model's angles are not raw servo commands: neutral is yaw0, hip30 and knee81 degrees in model coordinates, and its limits are yaw-55..55, hip-30..65, knee5..115. Servo zero, direction and offset must be calibrated separately.

## What the animation shows

Assembly_9_Steps.mp4 is captured from a new Fusion design containing the exact latest centred CAD pieces. Purple parts are supplied separately from the overnight plate. Teal parts are printed brackets; gold parts are caps; black parts are servos; silver parts are metal discs. Captions identify the fasteners at each step. Screws, nuts, washers and cables are not drawn, so follow their counts and stacking order above.

The exploded translations explain which piece meets which face. They are not a verified collision-free insertion path. The two F3D files preserve exploded and assembled states; the video contains the animation rather than a saved Animation-workspace storyboard. Physical load capacity, actual washer stack, cable motion and full-robot balance are not proven by this assembly demonstration.
'''
    (ROOT/'ASSEMBLY_AND_MISSING_PARTS.md').write_text(text);(ROOT/'ASSEMBLY_AND_MISSING_PARTS.txt').write_text(text)
    subprocess.run([sys.executable,'<LOCAL_HOME>/.codex/hooks/output_punctuation.py','register','--fix',str(ROOT/'ASSEMBLY_AND_MISSING_PARTS.txt'),str(OUT/'animation_report.json')],check=True)
    archive=ROOT/'Two_Legs_Assembly_Guide.zip'
    files=[ROOT/'ASSEMBLY_AND_MISSING_PARTS.md',ROOT/'ASSEMBLY_AND_MISSING_PARTS.txt',ROOT/'Assembly_9_Steps.mp4',OUT/'Exploded_Printed_Leg.f3d',OUT/'Assembled_Printed_Leg.f3d',OUT/'animation_report.json',OUT/'exploded.png',OUT/'assembled.png',*sorted(OUT.glob('step_*.png'))]
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for f in files:z.write(f,f.name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for f in files:assert hashlib.sha256(z.read(f.name)).digest()==hashlib.sha256(f.read_bytes()).digest()
    print('READY',archive)

if __name__=='__main__':main()
