"""Regression coverage for physical lengths shared by R5 IK, statics and URDF."""
import copy
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import numpy as np

import kinematics as k
import statics as s
import export_urdf as e


def fixture(length,mesh_name):
    links={name:{"mass_kg":.1,"com_mm":[0,0,0],"inertia_kg_m2":{"ixx":1e-4,"iyy":1e-4,"izz":1e-4,"ixy":0,"ixz":0,"iyz":0},"stl":mesh_name} for name in e.EXPECTED}
    for leg,az in k.LEGS.items():
        entries=[(f"coxa_{leg}","base",(k.root_origin(leg)*1000).tolist(),[0,0,az],[0,0,1],0),(f"femur_{leg}",f"coxa_{leg}",[length*1000,0,0],[0,0,0],[0,1,0],1),(f"tibia_{leg}",f"femur_{leg}",[k.FEMUR*1000,0,0],[0,0,0],[0,1,0],2)]
        for name,parent,origin,rpy,axis,index in entries:
            links[name]["joint"]={"parent":parent,"origin_mm":origin,"rpy_deg":rpy,"axis":axis,"limits_rad":k.LIMITS[index].tolist()}
    links["phone_pan"]["joint"]={"parent":"base","origin_mm":list(k.SETTINGS["phone_pan_origin_mm"])}
    parameters=copy.deepcopy(k.SETTINGS)
    parameters["coxa_mm"]=length*1000
    return {"units":"mm","parameters":parameters,"links":links,"parts":[{"link":"phone_pan","name":"Xiaomi_Mi9SE_bare_phone_envelope","bounds_mm":[[0,-73.75,18],[7.45,73.75,88.5]]}]}


class R5FrameContract(unittest.TestCase):
    def test_coxa_50_and_70_reach_every_frame_and_collision(self):
        yaw,hip,knee=np.radians([12,25,70])
        for length in (.050,.070):
            with self.subTest(coxa=length),patch.object(k,"COXA",length),patch.object(s,"COXA",length),patch.object(e,"COXA",length),patch.dict(k.SETTINGS,{"coxa_mm":length*1000}):
                q=np.array([yaw,hip,knee])
                np.testing.assert_allclose(k.inverse_local(k.forward_local(q)),q,atol=1e-12)
                # A straight leg has an independently known sum-of-lengths reach.
                np.testing.assert_allclose(k.forward_local([0,0,0]),[length+.195,0,0],atol=1e-12)
                frames,_=s.link_frames(np.zeros(3),{leg:q for leg in k.LEGS})
                for leg in k.LEGS:
                    co,cr=frames[f"coxa_{leg}"]
                    fo,fr=frames[f"femur_{leg}"]
                    to,tr=frames[f"tibia_{leg}"]
                    np.testing.assert_allclose(cr.T@(fo-co),[length,0,0],atol=1e-12)
                    np.testing.assert_allclose(fr.T@(to-fo),[.090,0,0],atol=1e-12)
                    np.testing.assert_allclose(to+tr@np.array([.105,0,0]),k.forward_body(leg,q),atol=1e-12)
                with tempfile.TemporaryDirectory(prefix="r5_frame_contract_") as folder:
                    directory=Path(folder)
                    mesh=directory/"fixture.stl"
                    mesh.write_bytes(bytes(80)+struct.pack('<I',1)+struct.pack('<12fH',0,0,1,0,0,0,1,0,0,0,1,0,0))
                    data=fixture(length,mesh.name)
                    manifest=directory/"manifest.json"
                    manifest.write_text(json.dumps(data))
                    urdf=directory/"robot.urdf"
                    e.export(manifest,urdf)
                    robot=ET.parse(urdf).getroot()
                    for leg in k.LEGS:
                        hip_origin=robot.find(f"joint[@name='hip_{leg}']/origin").attrib["xyz"]
                        np.testing.assert_allclose(list(map(float,hip_origin.split())),[length,0,0],atol=1e-12)
                        collision=robot.find(f"link[@name='coxa_{leg}']/collision")
                        self.assertAlmostEqual(float(collision.find("geometry/box").attrib["size"].split()[0]),length)
                        self.assertAlmostEqual(float(collision.find("origin").attrib["xyz"].split()[0]),length/2)

    def test_stale_50_mm_manifest_is_rejected_for_70_mm_setting(self):
        with patch.object(e,"COXA",.070),patch.dict(k.SETTINGS,{"coxa_mm":70.0}):
            data=fixture(.070,"unused.stl")
            e.validate_joint_contract(data)
            data["links"]["femur_FL"]["joint"]["origin_mm"][0]=50.0
            with self.assertRaisesRegex(ValueError,"origin_mm"):
                e.validate_joint_contract(data)

    def test_mismatched_parameter_or_axis_is_rejected(self):
        data=fixture(k.COXA,"unused.stl")
        data["parameters"]["coxa_mm"]+=1
        with self.assertRaisesRegex(ValueError,"coxa_mm"):
            e.validate_joint_contract(data)
        data=fixture(k.COXA,"unused.stl")
        data["links"]["tibia_FR"]["joint"]["axis"]=[0,-1,0]
        with self.assertRaisesRegex(ValueError,"axis"):
            e.validate_joint_contract(data)


if __name__=="__main__":unittest.main()
