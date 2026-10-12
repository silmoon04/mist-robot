"""Local accessible nut seats and screw-roof changes for the single-leg build."""
import math
import geom as g
import servo_contract as sc

NUT_AF=5.6
NUT_SLOT_THICKNESS=2.7
CLAMP_NUT_INNER_Y=-10.0


def hex_y(x,y,z,depth,af=NUT_AF):
    r=af/math.sqrt(3)
    points=[(x+r*math.cos(math.radians(30+i*60)),z-r*math.sin(math.radians(30+i*60))) for i in range(6)]
    return g.prism_xz(points,y,depth)


def roof(x,z,y0,length,r,up=1):
    q=r/math.sqrt(2)
    return g.prism_xz([(x-q,z+up*q),(x,z+up*r*math.sqrt(2)),(x+q,z+up*q)],y0,length)


def nut_roof(x,z,y0,length,up=1):
    h=NUT_AF/2;a=h/math.sqrt(3)
    return g.prism_xz([(x-h,z+up*a),(x,z+up*(h+a)),(x+h,z+up*a)],y0,length)


def revise_clamp(saddle,cap,bolt_xz,up,box):
    """Keep case contact and cap; recess nuts further in end-wall-only regions."""
    for x,z in bolt_xz:
        saddle=g.cut(saddle,hex_y(x,-16.6,z,6.6),nut_roof(x,z,-16.6,6.6,up),roof(x,z,-18,38,1.7,up))
        # Add roof material only outside the case contact region when needed.
        apex=z+up*(NUT_AF/2+NUT_AF/2/math.sqrt(3))
        if up>0 and apex+2>-2:
            saddle=g.fuse(saddle,box(x-3.9,x+3.9,-16.365,-12.365,-2,apex+2))
            saddle=g.cut(saddle,nut_roof(x,z,-16.6,6.6,up),hex_y(x,-16.6,z,6.6),roof(x,z,-18,38,1.7,up))
    return saddle,cap


def bridge_nut(shape,x,z,ztop,box):
    """One M3x30 from the detachable auxiliary cheek into an embedded nut.

    The bridge is integral with the main cheek, so a second opposing screw
    and the outside fixture spacers are unnecessary here.
    """
    return g.cut(shape,hex_y(x,2.5,z,NUT_SLOT_THICKNESS),
                 box(x-NUT_AF/2,x+NUT_AF/2,2.5,2.5+NUT_SLOT_THICKNESS,z,ztop+.1))
