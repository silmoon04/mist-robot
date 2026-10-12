"""Build the first MIST fit bed in millimetres, with a shared Fusion recipe.

Run with the local .venv Python. This creates fit specimens, not robot release
parts. Geometry is intentionally independent of fonts and slicer profiles.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
import sys
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
BEARINGS = [("693", 3, 8, 4), ("623", 3, 10, 4), ("685", 5, 11, 5),
            ("624", 4, 13, 5), ("687", 7, 14, 5), ("626", 6, 19, 6),
            ("627/608", "7/8", 22, 7)]
OFFSETS = [.25, .40, .55, .70]
SEGMENTS = {"0":"ab cdef".replace(" ",""), "1":"bc", "2":"abdeg",
            "3":"abcdg", "4":"bcfg", "5":"acdfg", "6":"acdefg",
            "7":"abc", "8":"abcdefg", "9":"abcdfg", "-":"g"}


class Part:
    def __init__(self, name):
        self.name, self.adds, self.cuts = name, [], []

    def shape(self, kind, cut=False, **kw):
        op = dict(op="cut" if cut else "add", kind=kind, **kw)
        (self.cuts if cut else self.adds).append(op)

    def box(self, x,y,z,sx,sy,sz,cut=False):
        self.shape("box",cut,x=x,y=y,z=z,sx=sx,sy=sy,sz=sz)

    def cyl(self,x,y,z,d,h,cut=False):
        self.shape("cylinder",cut,x=x,y=y,z=z,diameter=d,height=h)

    def cone(self,x,y,z,d0,d1,h,cut=False):
        self.shape("cone",cut,x=x,y=y,z=z,bottom_diameter=d0,diameter=d1,height=h)

    def poly(self,points,z,h,cut=False):
        self.shape("polygon",cut,points=points,z=z,height=h)

    def label(self, txt, cx, cy, top, height=2.4):
        # Seven-segment engraving. Every stroke is at least 0.4 mm wide.
        w, t, gap = height*.55, .4, .55
        start = cx-(len(txt)*w+(len(txt)-1)*gap)/2
        for j,char in enumerate(txt):
            x,y = start+j*(w+gap), cy-height/2
            spans = {"a":(x,y+height-t,w,t),"g":(x,y+height/2-t/2,w,t),
                     "d":(x,y,w,t),"f":(x,y+height/2,t,height/2),
                     "b":(x+w-t,y+height/2,t,height/2),
                     "e":(x,y,t,height/2),"c":(x+w-t,y,t,height/2)}
            if char == ".":
                self.box(x,y,top-.4,.4,.4,.5,True)
            else:
                for seg in SEGMENTS[char]:
                    xx,yy,ww,hh=spans[seg]
                    self.box(xx,yy,top-.4,ww,hh,.5,True)

    def recipe(self):
        return dict(name=self.name,ops=self.adds+self.cuts)


def make_recipe():
    parts, features, panels = [], [], []

    def feature(id,interface,nominal,cad,x,y,part,**kw):
        features.append(dict(feature_id=id,interface=interface,nominal_mm=nominal,
                             cad_mm=round(cad,3),x_mm=round(x,3),y_mm=round(y,3),part=part.name,**kw))

    # The thin carrier preserves the full radial wall and full bearing depth.
    p=Part("01_bearing_boss_carrier")
    total=sum(od+8 for _,_,od,_ in BEARINGS)+3*(len(BEARINGS)-1)
    p.box(0,0,0,3,total,1.2)
    y0=0
    for code,shaft,od,width in BEARINGS:
        outer=od+8
        row_width=4+4*outer+3*3
        p.box(1.5,y0+1.5,0,row_width-1.5,2.4,1.2)
        cy=y0+outer/2
        for i,off in enumerate(OFFSETS):
            cx=4+outer/2+i*(outer+3)
            seat=od+off
            height=width+1.4
            p.cyl(cx,cy,0,outer,height)
            p.cyl(cx,cy,-.1,od-1.4,height+.2,True)
            p.cyl(cx,cy,1.2,seat,width+.4,True)
            p.cone(cx,cy,height-.6,seat,seat+1.2,.7,True)
            # Three underside ports let a small blunt pin reach the outer race.
            for angle in (30,150,270):
                r=od/2-.3
                px=cx+r*math.cos(math.radians(angle))
                py=cy+r*math.sin(math.radians(angle))
                p.cyl(px,py,-.1,1.6,1.5,True)
            p.label(str(od),cx,cy+outer/2-2.1,height,2.2)
            p.label(f"{round(off*100):03}",cx,cy-outer/2+2.2,height,2.2)
            feature(f"bearing_OD{od}_{round(off*100):03}",f"bearing_OD{od}",od,seat,cx,cy,p,
                    bearing_codes=code,bearing_width_mm=width,boss_outer_mm=outer,
                    seat_depth_mm=width+.2,floor_mm=1.2,print_axis="Z",purpose="hand slip fit; retain separately")
        panels.append(dict(name=f"OD {od} ({code})",bounds=[0,y0,row_width,outer]))
        y0+=outer+3
    parts.append(p)

    # Hardware panel. Narrow rails and isolated full-depth heat bosses keep
    # the plastic volume low and stop thermal tests disturbing adjacent holes.
    p=Part("02_hardware_interface_board")
    x0,y0=141,0
    p.box(x0,y0,0,64,114,2)
    for row,(metric,diameters,height,depth,target) in enumerate([
        ("M3",[4.2,4.4,4.6,4.8,5.0],8,6,4.6),
        ("M4",[5.2,5.4,5.6,5.8,6.0],10,8,5.6)]):
        cy=7+row*12
        for i,d in enumerate(diameters):
            cx=147+i*12
            p.cyl(cx,cy,0,10,height)
            p.cyl(cx,cy,height-depth,d,depth+.1,True)
            p.cone(cx,cy,height-.6,d,d+.8,.7,True)
            p.label(str(i+1),cx,cy-4,height,2)
            feature(f"heat_insert_{metric}_{i+1}",f"heat_insert_{metric}",target,d,cx,cy,p,
                    hole_depth_mm=depth,status="insert OD and length unknown; pilot ladder only")
    # Six metal shaft sizes, three diametral clearances. These are hole gauges.
    for row,nom in enumerate([3,4,5,6,7,8]):
        cy=32+(row//2)*19
        start=146+(row%2)*32
        for col,off in enumerate([.15,.30,.45]):
            cx=start+col*10
            d=nom+off
            p.cyl(cx,cy,-.1,d,2.2,True)
            p.label(str(nom),cx,cy+6.5,2,2)
            feature(f"shaft_ID{nom}_{round(off*100):03}",f"shaft_clearance_ID{nom}",nom,d,cx,cy,p,
                    purpose="clearance hole for a measured metal shaft, not bearing inner-race fit")
    # Bolt through holes in a 4 mm wall, with three normal FDM clearance choices.
    for row,nom in enumerate([3,4]):
        cy=79+row*12
        p.box(143,cy-5,2,28,10,2)
        for i,off in enumerate([.2,.4,.6]):
            cx=148+i*9
            p.cyl(cx,cy,-.1,nom+off,4.2,True)
            feature(f"bolt_M{nom}_{round(off*100):03}",f"bolt_clearance_M{nom}",nom,nom+off,cx,cy,p)
    # Three across-flat nut pockets per size. Floors include screw clearance.
    for row,(nom,af,depth) in enumerate([(3,5.5,2.8),(4,7,3.6)]):
        cy=79+row*12
        p.box(173,cy-5.5,2,30,11,4)
        for i,off in enumerate([.15,.30,.45]):
            cx=178+i*10
            radius=(af+off)/math.sqrt(3)
            pts=[[cx+radius*math.cos(math.pi/6+j*math.pi/3),cy+radius*math.sin(math.pi/6+j*math.pi/3)] for j in range(6)]
            p.poly(pts,6-depth,depth+.1,True)
            p.cyl(cx,cy,-.1,nom+.5,6.2,True)
            feature(f"nut_M{nom}_{round(off*100):03}",f"nut_trap_M{nom}",af,af+off,cx,cy,p,
                    pocket_depth_mm=depth,purpose="test measured nut across-flats and height")
    for i,width in enumerate([4,6,8]):
        cx=153+i*20
        p.box(cx-width/2,102,-.1,width,7,2.2,True)
        feature(f"wire_slot_{width}","wire_slot",width,width,cx,105.5,p,
                purpose="pass actual connector and sleeved loom; deburr before use")
    p.label("3",148,75.5,4,2)
    p.label("4",148,87.5,4,2)
    parts.append(p)

    # Two shallow width gauges form a single rigid part; neither is a servo
    # cavity release because length, ears, cable exit and case revision differ.
    p=Part("03_servo_width_gauge")
    p.box(141,120,0,64,5,8)
    for i,gap in enumerate([25.23,25.43]):
        left=141+i*32.5
        p.box(left,124,0,3,20,8)
        p.box(left+3+gap,124,0,3,20,8)
        p.label(str(i+1),left+16,122.5,8,2.2)
        feature(f"servo_width_{i+1}","servo_body_width",25.23,gap,left+3+gap/2,133,p,
                purpose="case width only; previous 25.23 mm pocket worked on prior part")
    parts.append(p)

    # Two opposed jaws close around a metal shaft. M3 screws pass horizontally
    # through open-top slots, with washers under head and nut. Open slots avoid
    # support damage in a horizontal printed bore; the bottom web joins each jaw.
    p=Part("04_split_clamp_lower")
    x,y=141,149
    p.box(x,y,0,32,10,8)
    p.cyl(x+16,y+10.25,-.1,8.30,8.2,True)
    for xx in [x+5,x+27]:
        p.box(xx-1.7,y-.1,2.5,3.4,10.2,5.6,True)
    p.label("8",x+16,y+3,8,2.4)
    feature("clamp_ID8_030","clamp_ID8",8,8.30,x+16,y+10.25,p,
            purpose="two opposed jaws; starting face gap0.5mm; M3 bolts and washers; stiffness unvalidated")
    parts.append(p)
    p=Part("05_split_clamp_upper")
    p.box(141,164,0,32,10,8)
    p.cyl(157,163.75,-.1,8.3,8.2,True)
    for xx in [146,168]:
        p.box(xx-1.7,163.9,2.5,3.4,10.2,5.6,True)
    p.label("8",157,171,8,2.4)
    # A pitch ruler is part of this jaw's outer tab. It identifies tooth spacing
    # over 10 intervals; rectangular ticks are not belt tooth engagement geometry.
    p.box(170,171,0,35,3,2)
    p.box(177,148,0,28,25,2)
    for pitch,cy,count in [(2,153,11),(3,166,9)]:
        for i in range(count):
            xx=179+i*pitch
            p.box(xx-.25,cy-3,1.6,.5,6,.5,True)
        p.label(str(pitch),202,cy,2,2.2)
    parts.append(p)

    # Axial retention specimen, identical 624 seat + screw lugs. A separate
    # bridge retains only the outer race and leaves the inner race clear.
    p=Part("06_624_retainer_boss")
    cx,cy=153.5,192
    p.box(138,187,0,31,10,6.4)
    p.cyl(cx,cy,0,21,6.4)
    p.cyl(cx,cy,-.1,11.6,6.6,True)
    p.cyl(cx,cy,1.2,13.4,5.4,True)
    p.cone(cx,cy,5.8,13.4,14.6,.7,True)
    for xx in [141,166]:
        p.cyl(xx,cy,-.1,3.4,6.6,True)
    parts.append(p)
    p=Part("07_624_retainer_cap")
    p.box(175,187,0,31,10,2.4)
    p.cyl(190.5,192,0,21,2.4)
    p.cyl(190.5,192,-.1,10,2.6,True)
    for xx in [178,203]:
        p.cyl(xx,192,-.1,3.4,2.6,True)
    p.label("13",190.5,200,2.4,2.2)
    parts.append(p)

    recipe=dict(schema_version=1,units="mm",purpose="first_fit_bed",production_release=False,
                bearing_ladder_offsets_mm=OFFSETS,parts=[q.recipe() for q in parts],features=features,
                notes=["Belt pitch ruler only: 2 mm and 3 mm tick spacing, not a tooth engagement coupon.",
                       "Boss axis Z only; reproduce geometry and print settings in structural parts.",
                       "All shafts for powered movement must be metal."])
    return recipe


def primitive(cq,o):
    if o["kind"]=="box":
        return cq.Solid.makeBox(o["sx"],o["sy"],o["sz"],cq.Vector(o["x"],o["y"],o["z"]))
    if o["kind"]=="cylinder":
        return cq.Solid.makeCylinder(o["diameter"]/2,o["height"],cq.Vector(o["x"],o["y"],o["z"]))
    if o["kind"]=="cone":
        return cq.Solid.makeCone(o["bottom_diameter"]/2,o["diameter"]/2,o["height"],cq.Vector(o["x"],o["y"],o["z"]))
    return cq.Workplane("XY").polyline(o["points"]).close().extrude(o["height"]).translate((0,0,o["z"])).val()


def export_3mf(meshes,output):
    # Core 3MF model, not a machine/slicer project. Millimetres are explicit.
    ns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    ET.register_namespace("",ns)
    model=ET.Element(f"{{{ns}}}model",unit="millimeter",attrib={"{http://www.w3.org/XML/1998/namespace}lang":"en-US"})
    resources=ET.SubElement(model,"resources")
    build=ET.SubElement(model,"build")
    for i,(name,m) in enumerate(meshes.items(),1):
        obj=ET.SubElement(resources,"object",id=str(i),type="model",name=name)
        mesh=ET.SubElement(obj,"mesh")
        vs=ET.SubElement(mesh,"vertices")
        for v in m.vertices:
            ET.SubElement(vs,"vertex",x=f"{v[0]:.6f}",y=f"{v[1]:.6f}",z=f"{v[2]:.6f}")
        ts=ET.SubElement(mesh,"triangles")
        for f in m.faces:
            ET.SubElement(ts,"triangle",v1=str(f[0]),v2=str(f[1]),v3=str(f[2]))
        ET.SubElement(build,"item",objectid=str(i))
    with zipfile.ZipFile(output,"w",zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",'<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr("_rels/.rels",'<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr("3D/3dmodel.model",ET.tostring(model,encoding="utf-8",xml_declaration=True))


def run():
    import cadquery as cq
    import trimesh
    recipe=make_recipe()
    (ROOT/"coupon_recipe.json").write_text(json.dumps(recipe,indent=2)+"\n")
    out=ROOT/"bed1"
    out.mkdir(exist_ok=True)
    parts,meshes,checks=[],{},[]
    for data in recipe["parts"]:
        print("Building",data["name"],flush=True)
        adds=[primitive(cq,o) for o in data["ops"] if o["op"]=="add"]
        body=adds[0].fuse(*adds[1:]).clean() if len(adds)>1 else adds[0]
        cuts=[primitive(cq,o) for o in data["ops"] if o["op"]=="cut"]
        if cuts:
            body=body.cut(*cuts).clean()
        if not body.isValid():
            raise RuntimeError("Invalid BRep "+data["name"])
        if len(body.Solids())!=1:
            raise RuntimeError(f"{data['name']} split into {len(body.Solids())} solids")
        stl=out/(data["name"]+".stl")
        cq.exporters.export(body,str(stl),tolerance=.03,angularTolerance=.08)
        mesh=trimesh.load_mesh(stl,process=True)
        if not mesh.is_watertight or not mesh.is_winding_consistent:
            raise RuntimeError("Invalid mesh "+data["name"])
        parts.append(body)
        meshes[data["name"]]=mesh
        checks.append(dict(part=data["name"],brep_valid=True,solid_count=len(body.Solids()),
                           watertight=bool(mesh.is_watertight),winding_consistent=bool(mesh.is_winding_consistent),
                           volume_mm3=round(body.Volume(),3),mesh_volume_mm3=round(mesh.volume,3),
                           bounds_mm=mesh.bounds.round(4).tolist(),triangles=len(mesh.faces)))
    for i,a in enumerate(parts):
        for j,b in enumerate(parts[:i]):
            overlap=a.intersect(b).Volume()
            if overlap>1e-5:
                raise RuntimeError(f"Parts {j+1}/{i+1} intersect by {overlap} mm3")
    full=cq.Compound.makeCompound(parts)
    cq.exporters.export(full,str(out/"MIST_BED1_ALL_PARTS.step"))
    cq.exporters.export(full,str(out/"MIST_BED1_ALL_PARTS.stl"),tolerance=.03,angularTolerance=.08)
    export_3mf(meshes,out/"MIST_BED1_ALL_PARTS.3mf")
    all_mesh=trimesh.util.concatenate(list(meshes.values()))
    dims=all_mesh.extents
    if any(d>210 for d in dims[:2]) or all_mesh.bounds[0,2]<-1e-5:
        raise RuntimeError(f"Bed bounds violated {all_mesh.bounds}")
    validation=dict(status="geometry_checks_passed_physical_fit_pending",part_count=len(meshes),
                    bounds_mm=all_mesh.bounds.tolist(),extent_mm=dims.tolist(),
                    model_volume_cm3=round(sum(s.Volume() for s in parts)/1000,3),
                    solid_PLA_estimate_g=round(sum(s.Volume() for s in parts)/1000*1.24,2),
                    tessellation_mm=.03,inter_part_intersections_mm3=0,checks=checks,
                    unvalidated=["printer profile", "printed fit", "clamp performance", "heat insert dimensions", "structural loads"])
    (out/"validation.json").write_text(json.dumps(validation,indent=2)+"\n")
    (out/"feature_manifest.json").write_text(json.dumps(recipe["features"],indent=2)+"\n")
    fields=["feature_id","interface","nominal_mm","cad_mm","measured_part_mm","measured_hardware_mm",
            "fit_result","print_material","layer_mm","wall_count","xy_compensation_mm","notes"]
    feedback_template=out/"feedback_template.csv"
    with feedback_template.open("w",newline="") as f:
        writer=csv.DictWriter(f,fields)
        writer.writeheader()
        for feature in recipe["features"]:
            row={key:feature.get(key,"") for key in fields}
            row["fit_result"]="not_tested"
            writer.writerow(row)
    if not (ROOT/"feedback_BED1.csv").exists():
        (ROOT/"feedback_BED1.csv").write_bytes(feedback_template.read_bytes())
    fits={}
    for code,shaft,od,width in BEARINGS:
        fits[f"bearing_OD{od}"]=dict(nominal_mm=od,seat_diameter_mm=od+.4,boss_outer_mm=od+8,
                                    floor_mm=1.2,seat_depth_mm=width+.2,lead_in_mm=.6,
                                    status="unvalidated",print_axis="Z",bearing_codes=code)
    fits["servo_body_width"]=dict(pocket_mm=25.23,status="previous_part_passed_new_part_pending")
    fits["heat_insert_M3"]=dict(pilot_diameter_mm=None,hardware_od_mm=None,hardware_length_mm=None,status="unmeasured")
    fits["heat_insert_M4"]=dict(pilot_diameter_mm=None,hardware_od_mm=None,hardware_length_mm=None,status="unmeasured")
    (ROOT/"fit_parameters.json").write_text(json.dumps(dict(schema_version=1,production_release=False,interfaces=fits),indent=2)+"\n")
    make_preview(meshes,recipe,out)
    print(json.dumps(validation,indent=2),flush=True)


def make_preview(meshes,recipe,out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    fig,ax=plt.subplots(figsize=(11,11))
    colors=["#5e91ad","#e4a963","#6eaa83","#aa809c","#aa809c","#7789c4","#7789c4"]
    for (name,mesh),color in zip(meshes.items(),colors):
        normals=mesh.face_normals
        faces=mesh.faces[normals[:,2]>.5]
        polys=mesh.vertices[faces][:,:,:2]
        ax.add_collection(PolyCollection(polys,facecolors=color,edgecolors="none",antialiaseds=False))
    # Draw the engraved stroke footprints on the plan, matching the mesh cuts.
    for part in recipe["parts"]:
        for op in part["ops"]:
            if op["op"]=="cut" and op["kind"]=="box" and op["sz"]<=.51:
                ax.add_patch(plt.Rectangle((op["x"],op["y"]),op["sx"],op["sy"],color="#38454c",lw=0))
    ax.set(xlim=(-5,215),ylim=(-5,215),aspect="equal",xlabel="X / mm",ylabel="Y / mm")
    ax.set_title("MIST first fit bed | 7 objects | preserve this orientation",loc="left",fontsize=16,pad=20)
    ax.grid(alpha=.15)
    for f in recipe["features"]:
        if f["interface"].startswith("bearing"):
            ax.text(f["x_mm"],f["y_mm"],f'{f["cad_mm"]:.2f}',ha="center",va="center",fontsize=6.5)
    ax.text(143,115,"M3/M4 inserts, shaft holes, bolts, nuts, loom",fontsize=7)
    ax.text(143,146,"25.23 / 25.43 case width",fontsize=7)
    ax.text(143,177,"8 mm shaft clamp pair",fontsize=7)
    ax.text(144,206,"624 retention trial",fontsize=7)
    fig.savefig(out/"BED1_TOP_VIEW.png",dpi=160,bbox_inches="tight")
    plt.close(fig)


if __name__=="__main__":
    if "--recipe-only" in sys.argv:
        (ROOT/"coupon_recipe.json").write_text(json.dumps(make_recipe(),indent=2)+"\n")
    else:
        run()
