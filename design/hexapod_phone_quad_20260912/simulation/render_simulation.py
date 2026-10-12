"""Render a saved measured pose, without rerunning or altering its physics."""
import argparse
import json
from pathlib import Path
import struct
import zlib
import numpy as np
import pybullet as p


def write_png(path,pixels):
    pixels=np.asarray(pixels,dtype=np.uint8)
    height,width,_=pixels.shape
    def chunk(name,payload):
        return struct.pack(">I",len(payload))+name+payload+struct.pack(">I",zlib.crc32(name+payload)&0xffffffff)
    raw=b"".join(b"\x00"+pixels[y,:,:3].tobytes() for y in range(height))
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(raw,6))+chunk(b"IEND",b""))


def render(output):
    trajectory=json.loads((output/"trajectory.json").read_text())
    frame=trajectory["frames"][-1]
    p.connect(p.DIRECT)
    collision=p.createCollisionShape(p.GEOM_BOX,halfExtents=[2,2,.01])
    visual=p.createVisualShape(p.GEOM_BOX,halfExtents=[2,2,.01],rgbaColor=[.91,.92,.91,1])
    p.createMultiBody(baseMass=0,baseCollisionShapeIndex=collision,baseVisualShapeIndex=visual,basePosition=[0,0,-.01])
    robot=p.loadURDF(str(output/"quadruped.urdf"),basePosition=frame["base_m"],baseOrientation=frame["base_quat_xyzw"],useFixedBase=True,flags=p.URDF_USE_INERTIA_FROM_FILE)
    for i in range(p.getNumJoints(robot)):
        name=p.getJointInfo(robot,i)[1].decode()
        p.resetJointState(robot,i,frame["joint_rad"][name])
    view=p.computeViewMatrixFromYawPitchRoll([frame["base_m"][0],frame["base_m"][1],.165],.66,35,-20,0,2)
    proj=p.computeProjectionMatrixFOV(45,1.5,.01,10)
    pixels=p.getCameraImage(1440,960,view,proj,lightDirection=[-3,-2,5],shadow=1,renderer=p.ER_TINY_RENDERER)[2]
    write_png(output/"simulation.png",np.asarray(pixels).reshape(960,1440,4))
    p.disconnect()
    print(str(output/"simulation.png"))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=Path(__file__).resolve().parent/"output")
    render(parser.parse_args().output)
