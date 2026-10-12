"""Quasi-static loads using every CAD link COM and gravity."""
import math
import numpy as np
from kinematics import COXA, FEMUR, LEGS, PHONE_Z, inverse_world, root_origin, rz, support_margin


def ry(t):
    c, s = math.cos(t), math.sin(t)
    return np.array([[c,0,s],[0,1,0],[-s,0,c]])


def link_frames(base, angles):
    frames = {"base":(base, np.eye(3)), "phone_pan":(base+np.array([0,0,PHONE_Z]), np.eye(3))}
    axes = {}
    for leg in LEGS:
        yaw, hip, knee = angles[leg]
        co = base + root_origin(leg)
        cr = rz(math.radians(LEGS[leg])+yaw)
        fo, fr = co+cr@np.array([COXA,0,0]), cr@ry(hip)
        to, tr = fo+fr@np.array([FEMUR,0,0]), fr@ry(knee)
        frames.update({f"coxa_{leg}":(co,cr),f"femur_{leg}":(fo,fr),f"tibia_{leg}":(to,tr)})
        axes[leg] = [(co,np.array([0,0,1])),(fo,cr@np.array([0,1,0])),(to,fr@np.array([0,1,0]))]
    return frames, axes


def center_of_mass(manifest, frames):
    total = sum(v["mass_kg"] for v in manifest["links"].values())
    centers = {k:o+r@(np.array(manifest["links"][k]["com_mm"])/1000) for k,(o,r) in frames.items()}
    com = sum(manifest["links"][k]["mass_kg"]*v for k,v in centers.items())/total
    return com, centers, total


def solve_pose(manifest, desired_com_xy, base_z, feet, correct_com=True):
    base = np.array([*desired_com_xy, base_z], dtype=float)
    for _ in range(20 if correct_com else 1):
        angles = {leg:inverse_world(leg,feet[leg],base) for leg in LEGS}
        frames, axes = link_frames(base, angles)
        com, centers, total = center_of_mass(manifest,frames)
        error = np.asarray(desired_com_xy)-com[:2]
        if not correct_com or np.linalg.norm(error)<1e-7:
            break
        base[:2] += 0.8*error
    angles = {leg:inverse_world(leg,feet[leg],base) for leg in LEGS}
    frames, axes = link_frames(base, angles)
    com, centers, total = center_of_mass(manifest,frames)
    if correct_com and np.linalg.norm(np.asarray(desired_com_xy)-com[:2])>1e-5:
        raise ValueError("Whole robot COM correction did not converge within 0.01 mm")
    return base, angles, frames, axes, com, centers, total


def loads(manifest, base, feet, support, correct_com=True):
    body, angles, frames, axes, com, centers, total = solve_pose(manifest,base[:2],base[2],feet,correct_com)
    matrix = np.array([[1,feet[k][0],feet[k][1]] for k in support]).T
    force = np.linalg.lstsq(matrix,np.array([1,com[0],com[1]])*total*9.81,rcond=None)[0]
    normal = dict(zip(support,force))
    torques = {}
    for leg in LEGS:
        kinds = ["coxa","femur","tibia"]
        for j,(joint_o,axis) in enumerate(axes[leg]):
            moment = np.cross(feet[leg]-joint_o,np.array([0,0,normal.get(leg,0)]))
            for kind in kinds[j:]:
                name=f"{kind}_{leg}"
                moment += np.cross(centers[name]-joint_o,np.array([0,0,-9.81*manifest["links"][name]["mass_kg"]]))
            torques[f"{['yaw','hip','knee'][j]}_{leg}"] = float(-np.dot(moment,axis))
    return {"base":body, "angles":angles, "com":com, "torques":torques, "normal_forces":normal, "support_margin_m":support_margin(com[:2],[feet[k][:2] for k in support]), "total_mass_kg":total}
