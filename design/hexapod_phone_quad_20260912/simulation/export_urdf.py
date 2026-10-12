"""Export a mass-bound URDF. A complete CAD mass manifest is mandatory."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from kinematics import COXA, FEMUR, FOOT_RADIUS, LEGS, LIMITS, PHONE_Z, TIBIA, root_origin

HERE = Path(__file__).resolve().parent
DESIGN = HERE.parent
EXPECTED = ["base"] + [f"{kind}_{leg}" for leg in LEGS for kind in ("coxa", "femur", "tibia")] + ["phone_pan"]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def vector(values):
    return " ".join(f"{float(v):.12g}" for v in values)


def load_manifest(path):
    path = Path(path).resolve()
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if data.get("units") != "mm":
        raise ValueError("CAD manifest must state units mm; inertia must be kg m2 and mass kg")
    links = data.get("links")
    if not isinstance(links, dict) or set(links) != set(EXPECTED):
        raise ValueError(f"CAD links must be exactly {EXPECTED}")
    for name, item in links.items():
        if name.startswith(("coxa_","femur_","tibia_")) and "joint" in item:
            joint_index={"coxa":0,"femur":1,"tibia":2}[name.split("_")[0]]
            if not np.allclose(item["joint"]["limits_rad"],LIMITS[joint_index],atol=1e-9):
                raise ValueError(f"Manifest and shared settings disagree on joint limits for {name}")
        mass = float(item["mass_kg"])
        if not 0 < mass < 10:
            raise ValueError(f"Invalid mass for {name}: {mass}")
        if len(item["com_mm"]) != 3 or not np.all(np.isfinite(item["com_mm"])):
            raise ValueError(f"Invalid COM for {name}")
        terms = item["inertia_kg_m2"]
        inertia = np.array([[terms["ixx"], terms["ixy"], terms["ixz"]], [terms["ixy"], terms["iyy"], terms["iyz"]], [terms["ixz"], terms["iyz"], terms["izz"]]], dtype=float)
        principal = np.linalg.eigvalsh(inertia)
        if not np.all(np.isfinite(principal)) or principal.min() <= 0 or principal.max() > principal.sum()/2 + 1e-9:
            raise ValueError(f"Nonphysical inertia for {name}: {principal}")
        mesh = (path.parent / item["stl"]).resolve()
        if not mesh.is_file() or mesh.stat().st_size < 84:
            raise ValueError(f"Missing CAD mesh for {name}: {mesh}")
        item["resolved_mesh"] = str(mesh)
        item["mesh_sha256"] = digest(mesh)
    return data


def origin(node, xyz=(0, 0, 0), rpy=(0, 0, 0)):
    return ET.SubElement(node, "origin", xyz=vector(xyz), rpy=vector(rpy))


def collision_box(link, size, xyz):
    collision = ET.SubElement(link, "collision")
    origin(collision, xyz)
    ET.SubElement(ET.SubElement(collision, "geometry"), "box", size=vector(size))


def export(manifest, output, effort=0.588):
    manifest = Path(manifest).resolve()
    output = Path(output).resolve()
    data = load_manifest(manifest)
    if "phone_pan_origin_mm" in data and not np.allclose(data["phone_pan_origin_mm"],[0,0,PHONE_Z*1000],atol=1e-6):
        raise ValueError("Manifest and settings disagree on phone pan origin")
    robot = ET.Element("robot", name="video_reference_phone_quadruped")
    for name in EXPECTED:
        item = data["links"][name]
        link = ET.SubElement(robot, "link", name=name)
        inertial = ET.SubElement(link, "inertial")
        origin(inertial, np.asarray(item["com_mm"])/1000)
        ET.SubElement(inertial, "mass", value=str(item["mass_kg"]))
        ET.SubElement(inertial, "inertia", **{k:str(v) for k,v in item["inertia_kg_m2"].items()})
        visual = ET.SubElement(link, "visual")
        origin(visual)
        relative_mesh=Path(os.path.relpath(item["resolved_mesh"],output.parent)).as_posix()
        ET.SubElement(ET.SubElement(visual, "geometry"), "mesh", filename=relative_mesh, scale="0.001 0.001 0.001")
        color = "0.16 0.20 0.24 1" if name == "base" else "0.86 0.57 0.12 1" if name == "phone_pan" else "0.14 0.47 0.53 1"
        ET.SubElement(ET.SubElement(visual, "material", name=f"material_{name}"), "color", rgba=color)
        # Contact proxies intentionally exclude connectors and small fasteners.
        # Actual CAD interference is checked separately; these are floor proxies.
        if name == "base":
            collision_box(link, (0.140, 0.140, 0.050), (0, 0, 0.010))
        elif name == "phone_pan":
            phone_parts=[part for part in data["parts"] if part["link"]==name and part["name"]=="Xiaomi_Mi9SE_bare_phone_envelope"]
            if len(phone_parts)!=1:
                raise ValueError("Exactly one bare Mi 9 SE envelope is required for phone collision geometry")
            bounds=np.asarray(phone_parts[0]["bounds_mm"],dtype=float)/1000
            collision_box(link,bounds[1]-bounds[0],(bounds[1]+bounds[0])/2)
        elif name.startswith("coxa"):
            collision_box(link, (COXA, 0.018, 0.022), (COXA/2, 0, 0))
        elif name.startswith("femur"):
            collision_box(link, (FEMUR, 0.018, 0.018), (FEMUR/2, 0, 0))
        else:
            collision_box(link, (TIBIA-0.012, 0.015, 0.015), ((TIBIA-0.012)/2, 0, 0))
            collision = ET.SubElement(link, "collision")
            origin(collision, (TIBIA, 0, 0), (math.pi/2,0,0))
            ET.SubElement(ET.SubElement(collision, "geometry"), "cylinder", radius=str(FOOT_RADIUS), length="0.014")
    joint_names = []
    for leg, az in LEGS.items():
        for index, (kind, parent, xyz, axis) in enumerate([
            ("yaw", "base", root_origin(leg), (0, 0, 1)),
            ("hip", f"coxa_{leg}", (COXA, 0, 0), (0, 1, 0)),
            ("knee", f"femur_{leg}", (FEMUR, 0, 0), (0, 1, 0)),
        ]):
            name = f"{kind}_{leg}"
            joint_names.append(name)
            joint = ET.SubElement(robot, "joint", name=name, type="revolute")
            ET.SubElement(joint, "parent", link=parent)
            ET.SubElement(joint, "child", link=f"{['coxa','femur','tibia'][index]}_{leg}")
            origin(joint, xyz, (0, 0, math.radians(az)) if index == 0 else (0, 0, 0))
            ET.SubElement(joint, "axis", xyz=vector(axis))
            ET.SubElement(joint, "limit", lower=str(LIMITS[index,0]), upper=str(LIMITS[index,1]), effort=str(effort), velocity="1.0")
            ET.SubElement(joint, "dynamics", damping="0.003", friction="0.0")
    pan = ET.SubElement(robot, "joint", name="phone_pan", type="continuous")
    ET.SubElement(pan, "parent", link="base")
    ET.SubElement(pan, "child", link="phone_pan")
    phone_z = float(data.get("phone_pan_origin_mm", [0,0,PHONE_Z*1000])[2])/1000
    origin(pan, (0, 0, phone_z))
    ET.SubElement(pan, "axis", xyz="0 0 1")
    ET.SubElement(pan, "limit", effort=str(effort), velocity="1.0")
    ET.SubElement(pan, "dynamics", damping="0.003", friction="0.0")
    output.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(robot, space="  ")
    ET.ElementTree(robot).write(output, encoding="utf-8", xml_declaration=True)
    receipt = {
        "manifest_path":str(manifest), "manifest_sha256":digest(manifest),
        "urdf_path":str(output), "urdf_sha256":digest(output),
        "total_mass_kg":sum(x["mass_kg"] for x in data["links"].values()),
        "links":{name:{k:item[k] for k in ("mass_kg","com_mm","inertia_kg_m2","mesh_sha256")} for name,item in data["links"].items()},
        "joint_names":joint_names+["phone_pan"],
        "phone_pan_origin_m":[0,0,phone_z],
        "inertial_source":"CAD manifest physical components; no fallback estimated mass",
        "collision_model":"Simplified floor contact boxes and 14 mm wide, 5 mm radius rocker cylinders. The CAD toe has a 4.8 mm deep neutral flat, so the round proxy differs by at most 0.2 mm. CAD visuals and mass properties are retained. Self collision and cable contact are outside this dynamics check.",
    }
    (output.parent/"urdf_receipt.json").write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DESIGN/"cad/output/assembly_manifest.json")
    parser.add_argument("--output", type=Path, default=HERE/"output/quadruped.urdf")
    args = parser.parse_args()
    receipt = export(args.manifest, args.output)
    print(json.dumps({"mass_kg":receipt["total_mass_kg"], "urdf":str(args.output)}))
