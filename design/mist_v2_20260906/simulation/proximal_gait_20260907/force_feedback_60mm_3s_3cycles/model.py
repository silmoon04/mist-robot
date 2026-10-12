"""Geometry and URDF for a yaw/pitch/remote-knee wheeled quadruped. SI units."""
from pathlib import Path
import json
import math
import xml.etree.ElementTree as ET
import numpy as np

ROOT = Path(__file__).resolve().parent


def load_parameters(path=None):
    return json.loads(Path(path or ROOT / "parameters.json").read_text(encoding="utf-8"))


def coupling(p):
    ry, rh, rk = p["transmission"]["ratios"]
    if p["transmission"]["topology"] == "proximal_reduction_absolute_tibia":
        return np.array([[ry, 0, 0], [0, rh, 0], [0, rk, rk]], float)
    if p["transmission"]["topology"] == "unequal_remote_pulleys":
        return np.array([[ry, 0, 0], [0, rh, 0], [0, 1, rk]], float)
    if p["transmission"]["topology"] == "proximal_femur_relative_knee":
        if p["transmission"].get("knee_motor_mount") != "femur":
            raise ValueError("Relative knee coupling requires the motor housing to react torque on the femur")
        if "knee_servo_com_m" not in p["mass"]:
            raise ValueError("The moving knee servo needs an explicit femur-frame centre of mass")
        return np.diag([ry, rh, rk])
    if p["transmission"]["topology"] == "joint_relative_ideal":
        return np.diag([ry, rh, rk])
    raise ValueError("Unknown transmission topology: "+str(p["transmission"]["topology"]))


def knee_servo_moves_with_femur(p):
    return p["transmission"]["topology"] == "proximal_femur_relative_knee"


def rotation_z(t):
    return np.array([[np.cos(t), -np.sin(t), 0], [np.sin(t), np.cos(t), 0], [0, 0, 1]])


def mount(p, leg):
    phi = math.radians(p["geometry"]["mount_azimuths_deg"][leg])
    return p["geometry"]["hip_mount_radius_m"] * np.array([np.cos(phi), np.sin(phi), 0.0])


def transverse(p, leg):
    # Rear legs face backwards in drive stance; reverse their local handedness.
    return p["geometry"]["hip_transverse_offset_m"] * [1, -1, -1, 1][leg]


def fk(p, leg, q):
    g = p["geometry"]
    theta = math.radians(g["mount_azimuths_deg"][leg]) + q[0]
    rot = rotation_z(theta)
    hip = mount(p, leg)
    pitch = hip + rot @ [g["hip_radial_offset_m"], transverse(p, leg), 0]
    fem = np.array([g["femur_m"] * np.sin(q[1]), 0, -g["femur_m"] * np.cos(q[1])])
    tib = np.array([g["tibia_m"] * np.sin(q[1] + q[2]), 0, -g["tibia_m"] * np.cos(q[1] + q[2])])
    knee = pitch + rot @ fem
    axle = knee + rot @ tib
    return dict(hip=hip, pitch=pitch, knee=knee, axle=axle,
                wheel_axis=rot @ [0, -1, 0], heading=theta)


def ik(p, leg, target):
    g = p["geometry"]
    v = np.array(target) - mount(p, leg)
    radius = math.hypot(v[0], v[1])
    coxa = transverse(p, leg)
    valid = radius >= abs(coxa)
    radius = max(radius, abs(coxa) + 1e-12)
    theta = math.atan2(v[1], v[0]) - math.asin(coxa / radius)
    phi = math.radians(g["mount_azimuths_deg"][leg])
    yaw = (theta - phi + math.pi) % (2 * math.pi) - math.pi
    radial = math.sqrt(max(0, radius * radius - coxa * coxa)) - g["hip_radial_offset_m"]
    down = -v[2]
    l1, l2 = g["femur_m"], g["tibia_m"]
    d = (radial * radial + down * down - l1*l1 - l2*l2) / (2*l1*l2)
    valid = valid and -1 <= d <= 1
    knee = -math.acos(np.clip(d, -1, 1))
    hip = math.atan2(radial, down) - math.atan2(l2 * math.sin(knee), l1 + l2 * math.cos(knee))
    q = np.array([yaw, hip, knee])
    limits = np.radians(g["joint_limits_deg"])
    valid = valid and bool(np.all(q >= limits[:, 0]) and np.all(q <= limits[:, 1]))
    return q, valid


def neutral(p):
    g = p["geometry"]
    reach, down = g["drive_radial_reach_from_pitch_m"], g["hip_to_wheel_axle_height_m"]
    q = []
    for i in range(4):
        angle = math.radians(g["drive_heading_deg"][i])
        target = mount(p, i) + rotation_z(angle) @ [g["hip_radial_offset_m"] + reach, transverse(p, i), -down]
        qi, ok = ik(p, i, target)
        if not ok:
            raise ValueError(f"Neutral pose outside geometric limits: leg {i}, {np.degrees(qi)}")
        q.append(qi)
    return np.array(q)


def body_mass_properties(p):
    if p.get("link_mass_properties"):
        item=p["link_mass_properties"]["base_link"]
        return item["mass_kg"],np.array(item["com_m"],float),np.array(item["inertia_kg_m2"],float)
    m = p["mass"]
    items = [(m["shell_kg"], m.get("shell_com_m",[0, 0, .095])), (m["battery_kg"], m["battery_com_m"]),
             (m["brain_phone_kg"], m["brain_phone_com_m"]),
             (m["face_phone_with_frame_kg"], m["face_phone_com_m"]),
             (m["electronics_kg"], [0, 0, 0]), (m["harness_kg"], [0, 0, .035])]
    items += [(m["proximal_servo_kg"], mount(p, i)) for i in range(4)]
    total = sum(x[0] for x in items)
    com = sum(w * np.array(pos) for w, pos in items) / total
    inertia = np.zeros(3)
    for w, pos in items:
        v = np.array(pos) - com
        inertia += w * np.array([v[1]**2 + v[2]**2, v[0]**2 + v[2]**2, v[0]**2 + v[1]**2])
    # Intrinsic shell and envelope inertias; remaining point masses lack internal shape.
    r, h = p["geometry"]["body_diameter_m"] / 2, p["geometry"]["body_height_m"]
    inertia += m["shell_kg"] * np.array([(3*r*r+h*h)/12, (3*r*r+h*h)/12, r*r/2])
    return total, com, inertia + .0002


def total_mass(p):
    if p.get("link_mass_properties"):
        validate_link_mass_properties(p)
        return sum(item["mass_kg"] for item in p["link_mass_properties"].values())
    m = p["mass"]
    return body_mass_properties(p)[0] + 4 * (2*m["proximal_servo_kg"] + m["yaw_carriage_without_servos_kg"] +
            m["femur_with_pulleys_kg"] + m["tibia_with_carrier_kg"] + m["wheel_motor_with_mount_kg"] + m["wheel_hub_and_tire_kg"])


def validate_link_mass_properties(p):
    """Optional CAD-derived inertials must describe every moving rigid body."""
    items=p.get("link_mass_properties")
    if not items:
        return
    expected={"base_link"}|{leg+suffix for leg in p["geometry"]["leg_names"] for suffix in ("_yaw","_femur","_tibia","_wheel")}
    if set(items)!=expected:
        raise ValueError("CAD mass properties must contain exactly the 17 URDF links")
    for name,item in items.items():
        mass=float(item["mass_kg"])
        com=np.array(item["com_m"],float)
        inertia=np.array(item["inertia_kg_m2"],float)
        if not np.isfinite(mass) or mass<=0 or com.shape!=(3,) or not np.isfinite(com).all():
            raise ValueError("Invalid CAD mass or centre of mass for "+name)
        if inertia.shape!=(3,3) or not np.isfinite(inertia).all() or not np.allclose(inertia,inertia.T,atol=1e-12,rtol=0):
            raise ValueError("Invalid CAD inertia tensor for "+name)
        eigen=np.linalg.eigvalsh(inertia)
        if min(eigen)<=0 or max(eigen)>sum(eigen)-max(eigen)+1e-10:
            raise ValueError("CAD inertia is not physically realizable for "+name)


def build_urdf(p, destination=None):
    coupling(p)
    validate_link_mass_properties(p)
    g, m = p["geometry"], p["mass"]
    robot = ET.Element("robot", name="mist_v2_engineering_candidate")
    fmt = lambda x: " ".join(f"{float(v):.10g}" for v in x)
    def link(name, mass, com, inertia, shape, size, origin, color, rpy=(0, 0, 0)):
        if p.get("link_mass_properties"):
            item=p["link_mass_properties"][name]
            mass,com,inertia=item["mass_kg"],item["com_m"],np.array(item["inertia_kg_m2"],float)
        inertia=np.array(inertia,float)
        tensor=np.diag(inertia) if inertia.shape==(3,) else inertia
        part = ET.SubElement(robot, "link", name=name)
        inert = ET.SubElement(part, "inertial")
        ET.SubElement(inert, "origin", xyz=fmt(com))
        ET.SubElement(inert, "mass", value=str(mass))
        ET.SubElement(inert, "inertia", ixx=str(tensor[0,0]), iyy=str(tensor[1,1]), izz=str(tensor[2,2]),
                      ixy=str(tensor[0,1]),ixz=str(tensor[0,2]),iyz=str(tensor[1,2]))
        for tag in ["visual", "collision"]:
            elm = ET.SubElement(part, tag)
            ET.SubElement(elm, "origin", xyz=fmt(origin), rpy=fmt(rpy))
            geo = ET.SubElement(elm, "geometry")
            if shape == "box":
                ET.SubElement(geo, "box", size=fmt(size))
            else:
                ET.SubElement(geo, "cylinder", radius=str(size[0]), length=str(size[1]))
            if tag == "visual":
                mat = ET.SubElement(elm, "material", name=name+"_material")
                ET.SubElement(mat, "color", rgba=fmt(color))
    def box_inertia(mass, size):
        x,y,z = size
        return np.array([y*y+z*z, x*x+z*z, x*x+y*y]) * mass / 12
    def joint(name, parent, child, xyz, axis, kind="revolute", rpy=(0,0,0), limits=None):
        j = ET.SubElement(robot, "joint", name=name, type=kind)
        ET.SubElement(j,"parent",link=parent)
        ET.SubElement(j,"child",link=child)
        ET.SubElement(j,"origin",xyz=fmt(xyz),rpy=fmt(rpy))
        ET.SubElement(j,"axis",xyz=fmt(axis))
        if kind=="revolute":
            ET.SubElement(j,"limit",lower=str(limits[0]),upper=str(limits[1]),effort="20",velocity="20")
        ET.SubElement(j,"dynamics",damping="0",friction="0")
    bm,bc,bi = body_mass_properties(p)
    link("base_link",bm,bc,bi,"cylinder",[g["body_diameter_m"]/2,g["body_height_m"]],
         [0,0,g["body_height_m"]/2-g["hip_mount_height_above_body_bottom_m"]],[.83,.80,.73,1])
    for i,name in enumerate(g["leg_names"]):
        phi=math.radians(g["mount_azimuths_deg"][i]); d1=g["hip_radial_offset_m"]; c=transverse(p,i)
        limits=np.radians(g["joint_limits_deg"])
        knee_moves=knee_servo_moves_with_femur(p)
        mass=(1 if knee_moves else 2)*m["proximal_servo_kg"]+m["yaw_carriage_without_servos_kg"]
        size=[.065,.06,.045]
        link(name+"_yaw",mass,[d1/2,c/2,0],box_inertia(mass,size),"box",size,[d1/2,c/2,0],[.25,.27,.28,1])
        joint(name+"_q1_yaw","base_link",name+"_yaw",mount(p,i),[0,0,1],rpy=(0,0,phi),limits=limits[0])
        for label,length,mass,parent,org,lim in [
            ("femur",g["femur_m"],m["femur_with_pulleys_kg"],name+"_yaw",[d1,c,0],limits[1]),
            ("tibia",g["tibia_m"],m["tibia_with_carrier_kg"]+m["wheel_motor_with_mount_kg"],name+"_femur",[0,0,-g["femur_m"]],limits[2])]:
            size=[g["link_thickness_m"],g["link_width_m"],length]
            # Motor is near wheel, so tibia CoM is weighted towards its distal end.
            zcom=-length/2 if label=="femur" else -length*(.5*m["tibia_with_carrier_kg"]+.90*m["wheel_motor_with_mount_kg"])/mass
            inertia=box_inertia(mass,size)
            com=np.array([0,0,zcom],float)
            if label=="femur" and knee_moves:
                # Add the same physical servo removed from the yaw link. Housing
                # reaction changes the coupling; moving its mass changes dynamics.
                coupling(p)
                servo_mass=m["proximal_servo_kg"]
                servo_com=np.array(m["knee_servo_com_m"],float)
                combined=(mass*com+servo_mass*servo_com)/(mass+servo_mass)
                for weight,position in ((mass,com),(servo_mass,servo_com)):
                    offset=position-combined
                    inertia+=weight*(np.dot(offset,offset)-offset**2)
                # Diagonal approximation; no new fitted housing geometry is implied.
                inertia+=box_inertia(servo_mass,m.get("knee_servo_box_m",[.02473,.035,.04523]))
                mass+=servo_mass
                com=combined
            link(name+"_"+label,mass,com,inertia,"box",size,[0,0,-length/2],[.68,.70,.67,1])
            joint(name+("_q2_hip" if label=="femur" else "_q3_knee"),parent,name+"_"+label,org,[0,-1,0],limits=lim)
        mass=m["wheel_hub_and_tire_kg"]; r=g["wheel_diameter_m"]/2; w=g["wheel_width_m"]
        iner=np.array([mass*(3*r*r+w*w)/12,mass*r*r/2,mass*(3*r*r+w*w)/12])
        link(name+"_wheel",mass,[0,0,0],iner,"cylinder",[r,w],[0,0,0],[.12,.13,.13,1],rpy=(math.pi/2,0,0))
        joint(name+"_wheel_drive",name+"_tibia",name+"_wheel",[0,0,-g["tibia_m"]],[0,-1,0],kind="continuous")
    destination=Path(destination or ROOT/"generated"/"mist_candidate.urdf")
    destination.parent.mkdir(parents=True,exist_ok=True)
    ET.indent(robot)
    ET.ElementTree(robot).write(destination,encoding="utf-8",xml_declaration=True)
    return destination


if __name__=="__main__":
    p=load_parameters()
    print(build_urdf(p))
    print("Mass kg:",total_mass(p),"neutral degrees:",np.degrees(neutral(p)).round(3).tolist())
