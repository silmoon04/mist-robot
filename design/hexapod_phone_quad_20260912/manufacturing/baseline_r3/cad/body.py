"""Hexagonal chassis and low battery tray for the reference-derived quadruped."""
import math
import geom as g
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.gp import gp_Pnt

RADIUS = 103.0
COVER_FIXINGS = [(78, 0), (-78, 0), (0, 90), (0, -90)]
PAN_FIXINGS = [(-39, -20), (-39, 20), (19, -20), (19, 20)]


def hexagon(radius, cx=0, cy=0):
    return [(cx + radius * math.cos(math.radians(a)),
             cy + radius * math.sin(math.radians(a))) for a in range(30, 390, 60)]


def hex_loft(r0, z0, r1, z1):
    op = BRepOffsetAPI_ThruSections(True, True)
    for radius, z in [(r0, z0), (r1, z1)]:
        wire = BRepBuilderAPI_MakePolygon()
        for x, y in hexagon(radius):
            wire.Add(gp_Pnt(x, y, z))
        wire.Close()
        op.AddWire(wire.Wire())
    op.Build()
    return op.Shape()


def yz_rib(points, x_center, width):
    return g.translate(g.rotate(g.prism_xz(points, -width/2, width),
                                (0, 0, 1), 90), (x_center, 0, 0))


def zhole(x, y, z=-40, height=150, diameter=3.4):
    return g.cylinder(diameter / 2, height, (x, y, z))


def nut_z(x, y, z, height=2.7):
    return g.prism_xy(hexagon(3.35, x, y), z, height)


def part(name, shape, material='pla', printable=True, **extra):
    return dict(name=name, shape=shape, link='base', material=material,
                printable=printable, **extra)


def build_body():
    parts = []
    deck = g.prism_xy(hexagon(RADIUS), 0, 4)
    cuts = []
    # Rounded peripheral relief clears the reinforced coxa shoulder at yaw.
    # The nearest fixing-hole ligament remains more than six millimetres.
    for x in (-85,85):
        for y in (-54,54):
            cuts.append(zhole(x,y,diameter=13))
    for angle in (45, -45, 135, -135):
        a = math.radians(angle)
        cuts.append(zhole(75 * math.cos(a), 75 * math.sin(a), diameter=26))
        cable_slot = g.box(22, 26, 7, (56, 0, 2))
        cuts.append(g.rotate(cable_slot, (0, 0, 1), angle))
        for x in (-29, 9):
            for y in (-20, 20):
                a = math.radians(angle)
                px = (75 + x) * math.cos(a) - y * math.sin(a)
                py = (75 + x) * math.sin(a) + y * math.cos(a)
                cuts.append(zhole(px, py))
    for x, y in COVER_FIXINGS:
        cuts.append(zhole(x, y))
    for x in (-43, 43):
        for y in (-27, 27):
            cuts.append(zhole(x, y))
    # Cable-tie slots support measured boards without invented mounting holes.
    for x in (-30, 0, 30):
        for y in (-16, 16):
            cuts.append(g.box(12, 3.6, 7, (x, y, 2)))
    for x in (-65, 65):
        for y in (-15, 15):
            cuts.append(g.box(3.6, 10, 7, (x, y, 2)))
    for x in (-14, 14):
        cuts.append(g.box(3.6, 16, 7, (x, 67, 2)))
    deck = g.cut(deck, *cuts)
    parts.append(part('body_deck', deck, print_axis='z'))

    outer = g.fuse(g.prism_xy(hexagon(103), 4.5, 45.5),
                   hex_loft(103, 50, 97, 62))
    inner = g.fuse(g.prism_xy(hexagon(100.2), 3, 46.3),
                   hex_loft(100.2, 49.3, 94.2, 59.2))
    cover = g.cut(outer, inner)
    # Four broad openings keep the moving coxa and its leads outside the shell.
    for angle in (45, -45, 135, -135):
        opening = g.box(100, 60, 51, (85, 0, 28.5))
        cover = g.cut(cover, g.rotate(opening, (0, 0, 1), angle))
    # Removable cover uses short screws into accessible captured nuts.
    for x, y in COVER_FIXINGS:
        boss = g.cylinder(6.5, 10, (x, y, 4.5))
        if x:
            bridge = g.box(18, 13, 10, (x + math.copysign(5, x), y, 9.5))
        else:
            bridge = g.box(13, 18, 10, (x, y + math.copysign(5, y), 9.5))
        boss = g.fuse(boss, bridge)
        # In the inverted print, a diagonal rib grows from the shell toward
        # each raised fixing boss rather than starting its underside in air.
        if x:
            sign=math.copysign(1,x)
            rib=g.prism_xz([(sign*87,30.5),(sign*87,14.5),
                             (sign*71.5,14.5)],-6.5,13)
        else:
            sign=math.copysign(1,y)
            rib=yz_rib([(sign*99,30.5),(sign*99,14.5),
                         (sign*83.5,14.5)],0,13)
        boss=g.fuse(boss,rib)
        boss = g.cut(boss, zhole(x, y), nut_z(x, y, 7))
        # Open nut loading from the interior.
        if x:
            boss = g.cut(boss, g.box(15, 5.9, 2.7,
                                      (x - math.copysign(6, x), y, 8.35)))
        else:
            boss = g.cut(boss, g.box(5.9, 15, 2.7,
                                      (x, y - math.copysign(6, y), 8.35)))
        cover = g.fuse(cover, boss)
    cover = g.cut(cover, *[zhole(x, y) for x, y in PAN_FIXINGS])
    # Each pan screw takes a nut under a locally thickened top skin.
    for x, y in PAN_FIXINGS:
        pad = g.box(13, 13, 5, (x, y, 59.5))
        pad = g.cut(pad, zhole(x, y), nut_z(x, y, 57))
        cover = g.fuse(cover, pad)
    # Rear cable exit and ventilation are accessible with the cover lifted.
    cover = g.cut(cover, g.box(10, 24, 14, (-88, 0, 32)))
    for y in (-13, -6.5, 0, 6.5, 13):
        cover = g.cut(cover, g.box(18, 2.8, 12, (48, y, 61)))
    cover = g.cut(cover, g.box(18, 33, 16, (61, 0, 64)))
    parts.append(part('hex_faceted_cover', cover, print_axis='negative_z',
                      supports='Build with top face on bed; support only captive-nut recesses if needed.'))
    for i, (x, y) in enumerate(PAN_FIXINGS):
        spacer = g.cut(g.cylinder(4, 4, (x, y, 62)), zhole(x, y))
        parts.append(part(f'pan_cover_spacer_{i+1}', spacer, print_axis='z'))

    # Underslung pack lowers COM and separates the battery from moving joints.
    tray = g.box(112, 43, 3, (0, 0, -30.5))
    tray = g.fuse(tray, g.box(112, 3, 27, (0, -20, -15.5)),
                  g.box(112, 3, 27, (0, 20, -15.5)),
                  g.box(3, 43, 18, (-54.5, 0, -20)))
    # Open front end allows the XT60 lead to leave without a tight bend.
    for x in (-43, 43):
        for y in (-27, 27):
            tab = g.box(13, 17, 4, (x, y, -2))
            tab = g.cut(tab, zhole(x, y), nut_z(x, y, -4))
            tray = g.fuse(tray, tab)
            # Two thin sloping ribs carry the raised tab and leave the nut
            # and strap routes open. They also remove the flat support roof.
            sign=math.copysign(1,y)
            profile=[(sign*20,-20),(sign*20,-4),(sign*35.5,-4)]
            for dx in (-4,4):
                tray=g.fuse(tray,yz_rib(profile,x+dx,2))
    for x in (-30, 30):
        for y in (-20, 20):
            tray = g.cut(tray, g.box(14, 6, 3.8, (x, y, -25)))
    parts.append(part('battery_tray', tray, print_axis='z',
                      note='Two straps through opposed slots; tighten around pack without crushing.'))
    battery = g.box(104, 34.5, 24.5, (0, 0, -16.25))
    parts.append(part('battery_envelope', battery, 'battery', False, mass_kg=0.174))

    # Separate trays with slots accommodate actual board variants and cable ties.
    # Envelope dimensions include board height but not every connector lead.
    modules = [
        ('power_distribution', (45, 45, 18), (0, 0, 17), .024),
        ('servo_bus_adapter', (12, 33, 42), (-61, 0, 29), .016),
        ('esp32', (13, 28.6, 54.8), (61, 0, 33.4), .010),
        ('ubec', (43, 21, 8), (0, 67, 14), .018),
    ]
    for name, dims, center, mass in modules:
        parts.append(part(name + '_envelope', g.box(*dims, center=center),
                          'electronics', False, mass_kg=mass,
                          note='Nominal envelope; confirm actual connector and hole locations.'))
        bottom = center[2] - dims[2]/2
        if name in ('servo_bus_adapter','esp32'):
            pad = g.box(19, dims[1]+5, 2, (center[0],center[1],5))
            if bottom>6.01:
                pad = g.fuse(pad,g.box(dims[0],dims[1]-6,bottom-6,
                              (center[0],center[1],(bottom+6)/2)))
            for side in (-1,1):
                pad=g.fuse(pad,g.box(19,2,20,(center[0],side*(dims[1]/2+1.3),16)))
            pad=g.fuse(pad,g.box(1.5,dims[1]+5,20,
                         (center[0]-dims[0]/2-1.25,0,16)))
            # Chamfered inner corners clear the fixed yaw-clamp feet below Z7.
            inner_x = center[0] - math.copysign(9.5, center[0])
            for sy in (-1,1):
                pad=g.cut(pad,g.box(8,8,4.2,
                    (inner_x,sy*(dims[1]/2+1.0),5.1)))
            for side in (-1,1):
                pad=g.cut(pad,g.box(4,6,3,(center[0]+3,side*(dims[1]/2+1.3),12)))
            parts.append(part(name+'_tray',pad,print_axis='z',
                note='Upright removable board with two cable ties through rail slots.'))
            continue
        pad = g.box(dims[0] + 2, dims[1] + 2, 2, (center[0], center[1], bottom-1))
        # Four low feet leave air below the tray and pass cable ties underneath.
        for sx in (-1, 1):
            for sy in (-1, 1):
                foot = g.box(5, 5, max(.5, bottom-6),
                             (center[0]+sx*(dims[0]/2-3),
                              center[1]+sy*(dims[1]/2-3), (4+bottom-2)/2))
                pad = g.fuse(pad, foot)
        for sy in (-1, 1):
            pad = g.cut(pad, g.box(12, 3.4, 5,
                       (center[0], center[1]+sy*(dims[1]/2-2), bottom-1)))
        parts.append(part(name + '_tray', pad, print_axis='negative_z'))
    return parts


if __name__ == '__main__':
    for p in build_body():
        assert g.valid(p['shape']), p['name']
        print(p['name'], round(g.volume(p['shape']), 2), g.bounds(p['shape']))
