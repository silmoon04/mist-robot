"""One-run calibration with independently scheduled process changes.

This writes real printer G-code. No printer communication or hardware actuation.
"""
from pathlib import Path
import math,json,hashlib,csv
import numpy as np
from shapely.geometry import Polygon,box,LineString
from shapely.ops import unary_union
from shapely.affinity import translate

ROOT=Path(__file__).resolve().parent
LH=.28;WIDTH=.42;AREA=LH*WIDTH;FILAMENT=math.pi*1.75**2/4
BASE=1.12;BAND=5.6;BANDS=6;TOP=BASE+BANDS*BAND
FLOW=[8,12,16,20,24,28]
ACCEL=[1000,2000,3000,5000,8000,10000]
DETAIL=[40,65,90,120,150,180]
RETRACT=[.2,.35,.5,.65,.8,.5]
FONT={'F':['111','100','110','100','100'],'A':['010','101','111','101','101'],
 'R':['110','101','110','101','101'],'C':['111','100','100','100','111'],
 'S':['111','100','111','001','111'],'T':['111','010','010','010','010']}
F=box(20,22,200,42)
A=Polygon([(20,65),(42,65),(42,67),(48,67),(48,65),(95,65),(95,85),(93,85),(93,91),(95,91),(95,115),(20,115)])
S_CENTRES={'T':[(30,154),(60,154)],'S':[(135,154),(165,154)]}
LABELS={'F':(24,46),'A':(24,119),'R':(124,73),'C':(124,93),'T':(27,164),'S':(132,164)}
BASES={'F':unary_union([box(18,20,202,44).difference(box(22,24,198,40)),box(20,42,34,53)]),
 'A':unary_union([box(18,63,97,117).difference(box(22,69,91,111)),box(20,115,34,126)]),
 'R':unary_union([box(118,63,177,71),box(120,69,134,80)]),
 'C':unary_union([box(118,83,177,91),box(120,89,134,100)]),
 'T':unary_union([box(24,148,66,160),box(25,158,39,171)]),
 'S':unary_union([box(129,148,171,160),box(130,158,144,171)])}
# Finish the front flow tower first, for continuous flow per band. All other
# specimens are behind it, clear of the installed Cura head/fan envelope.
A=translate(A,yoff=40)
for n in ('A','R','C'):BASES[n]=translate(BASES[n],yoff=40);LABELS[n]=(LABELS[n][0],LABELS[n][1]+40)
for n in ('S','T'):
    BASES[n]=translate(BASES[n],yoff=35);LABELS[n]=(LABELS[n][0],LABELS[n][1]+35)
    S_CENTRES[n]=[(x,y+35) for x,y in S_CENTRES[n]]

BASES={name: shape.buffer(1,join_style=2) for name,shape in BASES.items()}

def polygons(shape):
    if shape.is_empty:return []
    if shape.geom_type=='Polygon':return [shape]
    return [p for p in shape.geoms if p.geom_type=='Polygon']

class Writer:
    def __init__(self):
        self.lines=[];self.xyz=np.array([0.,0.,10.]);self.height=0;self.rows=[];self.stage='startup';self.band=0;self.accel=500
        self.retract=.5;self.feed=150.;self.raised=True;self.travel_speed=150
    def emit(self,s):self.lines.append(s)
    def stage_set(self,name,band,accel,retract=.5):
        self.stage=name;self.band=band;self.accel=accel;self.retract=retract
        self.emit(f';TEST:{name} BAND:{band}');self.emit(f'M204 S{accel}');self.emit(f'M117 {name} band {band}')
    def move(self,point,speed,e=None,layer_height=0,width=WIDTH):
        point=np.array(point,dtype=float);start=self.xyz.copy();distance=float(np.linalg.norm(point-start));self.xyz=point
        line='G1 '+' '.join(f'{k}{v:.4f}' for k,v in zip('XYZ',point))+f' F{speed*60:.3f}'
        if e is not None:line+=f' E{e:.6f}'
        self.emit(line)
        if distance>1e-8:self.rows.append({'start':start.tolist(),'end':point.tolist(),'feed_mm_s':speed,'e_mm':e or 0,'accel':self.accel,'stage':self.stage,'band':self.band,'layer_height':layer_height,'width':width,'line_number':len(self.lines)})
    def path(self,points,z,speed,layer_height=LH,width=WIDTH,string_transfer=False):
        points=np.array(points,dtype=float)
        if len(points)<2:return
        self.emit(f'G1 E{-self.retract:.4f} F2100')
        if not string_transfer:
            travelz=max(self.height,z)+.6
            self.move([*self.xyz[:2],travelz],10)
        else:travelz=z
        self.move([*points[0],travelz],self.travel_speed if not string_transfer else 180)
        if not string_transfer:self.move([*points[0],z],10)
        self.emit(f'G1 E{self.retract:.4f} F2100')
        for a,b in zip(points,points[1:]):
            distance=float(np.linalg.norm(b-a))
            if distance<.01:continue
            self.move([*b,z],speed,distance*width*layer_height/FILAMENT,layer_height,width)
        self.height=max(self.height,z)
    def shell(self,shape,z,speed,lh=LH,walls=2,fill=False,alternate=False):
        for i in range(walls):
            for poly in polygons(shape.buffer(-WIDTH*(i+.5),join_style=2)):
                self.path(list(poly.exterior.coords),z,speed,lh)
                for ring in poly.interiors:self.path(list(ring.coords),z,speed,lh)
        if not fill:return
        inner=shape.buffer(-WIDTH*walls,join_style=2)
        if inner.is_empty:return
        x0,y0,x1,y1=inner.bounds
        step=WIDTH
        chain=[]
        for index,y in enumerate(np.arange(y0+WIDTH/2,y1,step)):
            line=LineString([(x0-1,y),(x1+1,y)]);cut=inner.intersection(line)
            pieces=[cut] if cut.geom_type=='LineString' else list(cut.geoms) if hasattr(cut,'geoms') else []
            for p in pieces:
                if p.length<.12:continue
                points=list(p.coords)
                if (index+alternate)%2:points.reverse()
                if chain and inner.buffer(.001).covers(LineString([chain[-1],points[0]])):chain.extend(points)
                else:
                    if chain:self.path(chain,z,speed,lh)
                    chain=points
        if chain:self.path(chain,z,speed,lh)

def roof_void_radius(dz,r=1.7):
    circle=math.sqrt(max(0,r*r-dz*dz)) if abs(dz)<=r else 0
    triangle=r*math.sqrt(2)-dz if r/math.sqrt(2)<=dz<=r*math.sqrt(2) else 0
    return max(circle,triangle)

def bracket(y,local):
    shape=box(120,y,175,y+4.2)
    for x in (135,160):
        half=roof_void_radius(local-2.4)
        if half>0:shape=shape.difference(box(x-half,y-1,x+half,y+5.2))
    return shape

def glyph(letter,x,y):
    pixels=[]
    for row,bits in enumerate(FONT[letter]):
        for col,bit in enumerate(bits):
            if bit=='1':pixels.append(box(x+col*.9,y+(4-row)*.9,x+(col+1)*.9,y+(5-row)*.9))
    return unary_union(pixels)

def main():
    w=Writer();w.emit(';V2: Four gradual base layers with wider attached foundations.');w.emit(';NEPTUNE 4 PRO 0.4 NOZZLE PLA 210C/60C SINGLE-RUN PROCESS TEST')
    w.emit(';Print this G-code directly. Re-slicing an STL cannot reproduce the tests.')
    w.emit(';No thermal protections, pressure advance, input shaping, motor current or saved configuration changed.')
    w.emit(';Layer heights deliberately mixed: F/R/C/S/T 0.28 mm; A 0.14 mm above the base.')
    for s in ['M220 S100','M221 S100','M107','M104 S140','M140 S60','M190 S60','G90','M204 S250','G28','G1 Z10 F300','G1 X20 Y8 F2400','M109 S210','M83','G92 E0','SET_VELOCITY_LIMIT VELOCITY=300','M204 S250']:
        w.emit(s)
    w.accel=250;w.xyz=np.array([20.,8.,10.]);w.move([20,8,.28],5)
    w.stage='purge';w.move([190,8,.28],15,170*.48*.28/FILAMENT,.28,.48);w.move([190,8.6,.28],15,.6*.48*.28/FILAMENT,.28,.48);w.move([20,8.6,.28],15,170*.48*.28/FILAMENT,.28,.48)
    w.height=.28
    for layer,speed,acceleration,travel,fan in [(1,12,250,40,0),(2,20,400,50,0),(3,25,500,60,64),(4,30,600,70,128)]:
        z=layer*LH;w.stage_set('BASE',0,acceleration);w.travel_speed=travel
        w.emit(f'M106 S{fan}')
        for name,shape in BASES.items():w.shell(shape,z,speed,walls=2,fill=True,alternate=layer%2)
    # Print all identifiers before the vertical test sections, supported by
    # their own base tabs. Their local heights are tracked for travel lifts.
    w.emit('M106 S255')
    for z in (BASE+LH,BASE+2*LH):
        w.stage_set('LABEL',0,500);w.travel_speed=60
        for letter,(x,y) in LABELS.items():w.shell(glyph(letter,x,y),z,20,walls=1,fill=False)
    w.travel_speed=150
    schedule=[]
    for band in range(1,7):
        schedule.append({'band':band,'z_bottom_mm':round(BASE+(band-1)*BAND,2),'z_top_mm':round(BASE+band*BAND,2),'F_flow_mm3_s':FLOW[band-1],'F_speed_mm_s':FLOW[band-1]/AREA,'A_acceleration_mm_s2':ACCEL[band-1],'A_speed_mm_s':120,'A_layer_height_mm':.14,'A_flow_mm3_s':120*WIDTH*.14,'R_speed_mm_s':DETAIL[band-1],'R_flow_mm3_s':DETAIL[band-1]*AREA,'C_speed_mm_s':40,'S_retraction_mm':RETRACT[band-1],'T_retraction_mm':.5})
    for layer in range(1,121):
        z=round(BASE+layer*LH,4);band=min(6,(layer-1)//20+1);within=(layer-1)%20
        w.emit(f';FLOW_LAYER:{layer} Z:{z:.4f}');w.stage_set('F',band,3000)
        marker=.14 if within in (0,19) else 0
        w.shell(F.buffer(marker,join_style=2),z,FLOW[band-1]/AREA,walls=1)
    # A short low-flow recovery rim checks that delivery recovers after F6.
    # It is not a seventh flow band and is excluded from scoring.
    w.stage_set('F_RECOVERY',0,1500)
    for z in (TOP+LH,TOP+2*LH):w.shell(F,z,8/AREA,walls=1)
    w.emit(';FRONT_FLOW_TOWER_COMPLETE')
    w.move([*w.xyz[:2],TOP+1.2],10);w.move([205,105,TOP+1.2],150)
    # Every remaining path stays behind Y=104.86, while the completed front
    # wall ends at Y=42.14. A conservative +/-50 mm head footprint clears it.
    w.height=BASE+2*LH
    for half_layer in range(1,241):
        z=round(BASE+half_layer*.14,4);band=min(6,(half_layer-1)//40+1);within=(half_layer-1)%40
        w.emit(f';GLOBAL_LAYER:{half_layer} Z:{z:.4f}');w.emit(f';BAND:{band}')
        w.stage_set('A',band,ACCEL[band-1]);marker=.14 if within in (0,1,38,39) else 0
        w.shell(A.buffer(marker,join_style=2),z,120,lh=.14,walls=1)
        if half_layer%2:continue
        marker=.14 if within in (1,39) else 0
        local=z-(BASE+(band-1)*BAND)
        for name,y,speed in [('R',105,DETAIL[band-1]),('C',125,40)]:
            w.stage_set(name,band,2000)
            shape=bracket(y,local)
            if marker:shape=shape.buffer(marker,join_style=2)
            w.shell(shape,z,speed,walls=3,fill=False)
        for name in ('T','S'):
            w.stage_set(name,band,1500,.5 if name=='T' else RETRACT[band-1])
            # First visit uses a hop; the four timed transfers inside each
            # pair deliberately use no hop to show ordinary travel stringing.
            for visit in range(4):
                cx,cy=S_CENTRES[name][visit%2];r=3+marker-.21-(visit//2)*.42
                points=[(cx-r,cy-r),(cx+r,cy-r),(cx+r,cy+r),(cx-r,cy+r),(cx-r,cy-r)]
                w.path(points,z,40,string_transfer=visit>0)
    w.stage_set('FINISH',0,2500);w.emit('M400');w.emit('G1 E-1 F2100');w.move([*w.xyz[:2],TOP+5],5);w.move([20,210,TOP+5],100)
    for s in ['M107','M104 S0','M140 S0','M220 S100','M221 S100','M84 X Y E',';END OF SINGLE-RUN TEST'] :w.emit(s)
    target=ROOT/'EN4Pro_Calibration_V2_Slow_Start.gcode';target.write_text('\n'.join(w.lines)+'\n',encoding='ascii')
    (ROOT/'expected_paths.json').write_text(json.dumps(w.rows,separators=(',',':')))
    design={'gcode_file':target.name,'gcode_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'nozzle_mm':.4,'filament_mm':1.75,'nozzle_C':210,'bed_C':60,'line_width_mm':WIDTH,'test_layer_height_mm':LH,'base_height_mm':BASE,'band_height_mm':BAND,'height_mm':TOP+2*LH,'schedule':schedule,
        'phase_order':'Bases and labels first; continuous front flow tower with recovery rim; then all rear specimens together in layers. Front/rear clearance is explicitly checked with a conservative 50 mm head footprint.',
        'zone_footprints':{n:list(p.bounds) for n,p in BASES.items()},'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'startup':'Stock Cura Neptune 4/4 Pro pattern: warm bed, home, warm nozzle, purge. Purge is explicitly volumetric and moved inboard. Existing G28/mesh behaviour is retained; no guessed named bed mesh is loaded.',
        'restore':'Runtime velocity cap is set to 300 mm/s. M204 S2500 at end, then heaters/fan off. These are documented runtime settings, not restoration of unknown prior values. No SAVE_CONFIG command.',
        'scope':'Known printer model and successful material settings, but no measured live firmware configuration. Printer host from Orca settings timed out. Feedrates may be firmware-limited. Pressure advance, shaping and corner settings remain as currently configured.'}
    (ROOT/'test_design.json').write_text(json.dumps(design,indent=2));print('GENERATED',target,'moves',len(w.rows),'lines',len(w.lines))

if __name__=='__main__':main()
