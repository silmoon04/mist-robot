"""Assembly sheets rendered from exported CAD with vector callouts."""
from pathlib import Path
from types import SimpleNamespace
import sys
import math
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.colors import to_rgb

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'hexapod_phone_quad_r5_20260912/review'))
from render_preview import draw_mesh,camera_basis

BG='#f5f6f2';INK='#203437';MUTED='#53676b'
BLUE='#329ca5';GREY='#7b898b';SERVO='#303a40';METAL='#b7c2c9';GOLD='#ce9a44';DARK='#57626b'
CACHE={}


def piece(key,xyz=(0,0,0),rx=0,color=None):
    if key not in CACHE:CACHE[key]=trimesh.load_mesh(HERE/'assets'/(key+'.stl'),process=True)
    mesh=CACHE[key].copy()
    mesh.apply_transform(trimesh.transformations.rotation_matrix(math.radians(rx),(1,0,0)))
    mesh.apply_translation(xyz)
    default=BLUE if key in ['gauge','main_cheek','aux_cheek'] else GOLD if key in ['bridge','gauge_spacer','washer6','washer7'] else METAL
    return mesh,color or default


def scene(ax,parts,elev=27,az=-55,pad=.12):
    tris=[];normals=[];colors=[]
    for mesh,color in parts:
        tris.append(mesh.triangles);normals.append(mesh.face_normals)
        colors.append(np.tile(to_rgb(color),(len(mesh.faces),1)))
    obj=SimpleNamespace(triangles=np.concatenate(tris),normals=np.concatenate(normals),colors=np.concatenate(colors))
    basis=camera_basis(elev,az)
    proj=draw_mesh(ax,obj,basis);low=proj.min(axis=(0,1));high=proj.max(axis=(0,1));span=high-low
    ax.set_xlim(low[0]-span[0]*pad,high[0]+span[0]*pad)
    ax.set_ylim(low[1]-span[1]*pad,high[1]+span[1]*pad)
    ax.set_aspect('equal');ax.axis('off')
    return basis


def point(v,basis):return (np.asarray(v)@basis)[:2]


def arrow(ax,start,end,basis,color=BLUE):
    ax.annotate('',xy=point(end,basis),xytext=point(start,basis),
        arrowprops=dict(arrowstyle='-|>',lw=1.7,color=color,mutation_scale=14),zorder=5)


def tag(ax,letter,target,where,basis):
    ax.annotate(letter,xy=point(target,basis),xycoords='data',xytext=where,textcoords='axes fraction',
        ha='center',va='center',fontsize=14,weight='bold',color=INK,
        bbox=dict(boxstyle='circle,pad=.32',fc='white',ec=BLUE,lw=1.6),
        arrowprops=dict(arrowstyle='-',color=INK,lw=1),zorder=8)


def sheet(number,title,subtitle):
    fig=plt.figure(figsize=(12,8),facecolor=BG)
    fig.text(.045,.935,f'{number:02d}',fontsize=30,color=BLUE,weight='bold')
    fig.text(.11,.94,title,fontsize=24,color=INK,weight='bold')
    fig.text(.11,.90,subtitle,fontsize=11.5,color=MUTED)
    return fig


def step(fig,y,badge,title,text,x=.69):
    fig.text(x,y,badge,fontsize=13,weight='bold',color=BLUE)
    fig.text(x+.035,y,title,fontsize=13,weight='bold',color=INK)
    fig.text(x+.035,y-.035,text,fontsize=11,color=MUTED,va='top',linespacing=1.5)


def footer(fig,text):
    fig.text(.05,.056,text,fontsize=11,color='#92522f',weight='bold')
    fig.text(.05,.025,'Printed parts: actual CAD geometry. Exploded gaps are illustrative; fasteners are simplified.',fontsize=8.5,color=MUTED)


def save(fig,name):
    fig.savefig(HERE/name,dpi=170,facecolor=BG);plt.close(fig)


def clamp():
    return [piece('saddle',color=GREY),piece('cap',color=GREY),piece('servo',color=SERVO)]


def image1():
    fig=sheet(1,'Place the alignment gauge','Reuse the saddle and flat cap you have already fitted.')
    ax=fig.add_axes([.035,.14,.62,.70])
    parts=clamp()+[piece('main_horn',(0,0,8)),piece('screw6',(0,0,20),color=DARK),piece('gauge',(0,0,34))]
    basis=scene(ax,parts,elev=29,az=-60)
    for y in (-20,20):arrow(ax,(9,y,3),(9,y,-27),basis)
    arrow(ax,(0,0,9),(0,0,3.4),basis,color=METAL)
    tag(ax,'A',(0,0,12.5),(.08,.55),basis)
    tag(ax,'B',(0,0,42.5),(.72,.91),basis)
    tag(ax,'C',(9,-20,-29),(.94,.22),basis)
    step(fig,.77,'A','Seat the metal horn',
        'Fit the supplied main horn onto\nthe shaft. Fit its centre retaining\nscrew before adding the gauge.')
    step(fig,.57,'B','Lower the gauge',
        'The large round end sits on the\nmetal horn. The two tall legs reach\nthe existing clamp feet.')
    step(fig,.37,'C','Use the shaft-end feet',
        'Use the pair of feet nearest the\nshaft. Both feet and the horn face\nshould meet without forcing.')
    fig.text(.08,.115,'Grey: your existing clamp     Blue: the new alignment gauge     Silver: supplied hardware',fontsize=10,color=MUTED)
    footer(fig,'Keep power disconnected. The alignment gauge locks the output to the case.')
    save(fig,'01_place_alignment_gauge.png')


def image2():
    fig=sheet(2,'Fasten the gauge gently','Two long tie bolts hold the feet; four short screws attach the gauge to the horn.')
    parts=clamp()+[piece('main_horn'),piece('gauge'),piece('screw6',(0,0,4.5),color=DARK)]
    for y in (-20,20):
        parts += [piece('screw50',(9,y,21),color=DARK),piece('washer6',(9,y,14)),
            piece('gauge_spacer',(9,y,-46)),piece('washer6',(9,y,-49)),piece('nut',(9,y,-55))]
    for x,y in ((7,0),(-7,0),(0,7),(0,-7)):
        parts += [piece('washer6',(x,y,8.5)),piece('screw6',(x,y,9),color=DARK)]
    ax=fig.add_axes([.035,.13,.57,.70]);basis=scene(ax,parts,elev=24,az=-55)
    for y in (-20,20):arrow(ax,(9,y,-40),(9,y,-32),basis,color=GOLD)
    tag(ax,'A',(9,-20,23),(.80,.9),basis)
    tag(ax,'B',(9,-20,-43),(.88,.14),basis)
    fig.text(.65,.79,'A  Tie-bolt order, repeated twice',fontsize=14,weight='bold',color=INK)
    rows=[('M3x50 screw',DARK),('OD6 washer, 0.5 mm',GOLD),('Gauge, then existing clamp foot',BLUE),
          ('Printed spacer, 5 mm',GOLD),('OD6 washer, 0.5 mm',GOLD),('Plain M3 nut',METAL)]
    for i,(text,color) in enumerate(rows):
        y=.72-i*.059
        fig.patches.append(Rectangle((.66,y-.007),.025,.020,transform=fig.transFigure,facecolor=color,edgecolor='none'))
        fig.text(.701,y,text,fontsize=11,color=INK,va='center')
    fig.text(.65,.32,'Four horn screws',fontsize=13,weight='bold',color=INK)
    fig.text(.65,.285,'M3x6 + ONE OD6 x 0.5 mm washer\nat each of the four holes around the shaft.',fontsize=11,color=MUTED,linespacing=1.6,va='top')
    fig.text(.65,.18,'If using M3x45 tie bolts instead,\nomit the two printed 5 mm spacers.',fontsize=10.5,color=MUTED,linespacing=1.5,va='top')
    fig.text(.07,.105,'B: the printed spacers, lower washers and nuts go underneath the clamp feet.',fontsize=10,color=MUTED)
    footer(fig,'Do not pull a gap closed with the screws. Record a mismatch, then remove the gauge.')
    save(fig,'02_gauge_fastener_order.png')


def fixture(exploded):
    delta=27 if exploded else 0;disc=10 if exploded else 0
    parts=[piece('servo',(0,14.5,0),-90,SERVO),
        piece('main_horn',(0,14.5+disc,0),-90),
        piece('aux_disc',(0,14.5-disc,0),-90),
        piece('main_cheek',(0,delta,0),color=BLUE),
        piece('aux_cheek',(0,-delta,0),color='#4bb7a1'),
        piece('bridge',(18 if exploded else 0,0,0),color=GOLD)]
    parts += [piece('washer7',(0,-19.1-(18 if exploded else 0),0),-90),
        piece('screw5',(0,-19.1-(24 if exploded else 0),0),90,DARK),
        piece('screw6',(0,19+(18 if exploded else 0),0),-90,DARK)]
    return parts


def image3():
    fig=sheet(3,'Build the two-sided horn fixture','Remove the alignment gauge first. This next test uses the bare servo.')
    ax=fig.add_axes([.025,.18,.64,.64]);basis=scene(ax,fixture(True),elev=29,az=-40,pad=.13)
    arrow(ax,(0,46,0),(0,24,0),basis)
    arrow(ax,(0,-46,0),(0,-25,0),basis,color='#4bb7a1')
    arrow(ax,(47,0,0),(33,0,0),basis,color=GOLD)
    tag(ax,'A',(12,48,0),(.86,.78),basis)
    tag(ax,'B',(12,-48,0),(.12,.25),basis)
    tag(ax,'C',(47,0,0),(.91,.22),basis)
    step(fig,.76,'A','Main-shaft side',
        'Supplied main horn, then the\nprinted main cheek. Its long arm\npoints toward the small bridge.')
    step(fig,.56,'B','Auxiliary side',
        'Fit the auxiliary disc, its centre\nwasher and retainer, then the\nprinted auxiliary cheek.')
    step(fig,.36,'C','Close with the bridge',
        'The 38 mm bridge joins the arms.\nUse one M3x50 screw, two OD7\nwashers and one M3 nut.')
    fig.text(.065,.115,'The long servo case points AWAY from the bridge. Both printed arms point TOWARD it.',fontsize=11,color=INK,weight='bold')
    footer(fig,'Check the loose auxiliary disc first. Tighten in stages and stop if the fixture binds.')
    save(fig,'03_assemble_horn_fixture.png')


def block(ax,x,width,label,color,y=0,height=1.5):
    ax.add_patch(Rectangle((x,y),width,height,facecolor=color,edgecolor=INK,lw=.7))
    return x+width


def stack(ax,aux=False):
    ax.set_xlim(-3,12);ax.set_ylim(-3,4);ax.axis('off')
    ax.plot([-1.5,9],[.75,.75],color='#899899',ls='--',lw=1)
    block(ax,-1.5,1,'',DARK,y=.05,height=1.4)
    # Widen the washer symbols for readability; dimensions are written below.
    x=0
    n=2 if aux else 1
    for i in range(n):block(ax,x,.35,'',GOLD);x+=.5
    cheek_x=x+.2;end=block(ax,cheek_x,3,'',BLUE)
    if aux:end=block(ax,end,.8,'','#4bb7a1',height=1.0,y=.25)
    horn_x=end+.12;block(ax,horn_x,1.7,'',METAL,height=2,y=-.25)
    ax.plot([-.5,horn_x+1.25],[.75,.75],color=DARK,lw=4,solid_capstyle='butt')
    ax.text(.2,2.2,'TWO washers' if aux else 'ONE washer',fontsize=12,weight='bold',color=INK,ha='center')
    ax.annotate('',xy=(.2,1.6),xytext=(.2,2.0),arrowprops=dict(arrowstyle='->',color=GOLD))
    ax.text(cheek_x+1.5,-.8,'Printed cheek\n4 mm',ha='center',va='top',fontsize=10,color=MUTED)
    ax.text(horn_x+.85,2.65,'Auxiliary disc' if aux else 'Main horn',ha='center',fontsize=11,color=MUTED)
    if aux:ax.text(end-.4,-2.2,'Integral 1.1 mm land',ha='center',fontsize=10,color=MUTED)


def image4():
    fig=sheet(4,'Check the washers before tightening','The main and auxiliary sides use different screw lengths and washer counts.')
    fig.text(.075,.79,'MAIN SIDE',fontsize=14,color=INK,weight='bold')
    fig.text(.075,.745,'4 x M3x6 screws',fontsize=19,color=BLUE,weight='bold')
    fig.text(.56,.79,'AUXILIARY SIDE',fontsize=14,color=INK,weight='bold')
    fig.text(.56,.745,'4 x M3x8 screws',fontsize=19,color=BLUE,weight='bold')
    stack(fig.add_axes([.065,.37,.43,.35]),False)
    stack(fig.add_axes([.55,.37,.43,.35]),True)
    fig.text(.08,.365,'ONE OD6 x 0.5 mm washer per screw.\nNominal flange engagement: 1.5 mm.',fontsize=12,color=INK,linespacing=1.6,va='top')
    fig.text(.56,.365,'TWO OD6 x 0.5 mm washers per screw.\nNominal flange engagement: 1.9 mm.',fontsize=12,color=INK,linespacing=1.6,va='top')
    fig.text(.08,.235,'Auxiliary CENTRE retainer is a separate stack',fontsize=14,color=INK,weight='bold')
    fig.text(.08,.195,'Supplied PA3x5 screw + ONE OD7 x 0.5 mm washer. The washer bears on the fixed stub,\nnot on the rotating disc. Nominal gap to the disc: 0.7 mm. Check its freedom before joining the cheeks.',
        fontsize=11.5,color=MUTED,linespacing=1.65,va='top')
    fig.text(.08,.105,'Section diagrams are schematic. OD means outside diameter. Do not substitute OD7 washers for OD6 here.',fontsize=10,color=MUTED)
    footer(fig,'Once joined, the output has gearbox resistance. Do not force it to spin like a loose bearing.')
    save(fig,'04_washer_and_retainer_stacks.png')


if __name__=='__main__':
    for function in [image1,image2,image3,image4]:
        function();print(function.__name__+' rendered',flush=True)
