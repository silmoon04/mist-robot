"""Encode exact recorded poses as a short video; never steps the simulation."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import numpy as np
import pybullet as p


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def render(output,ffmpeg):
    started=time.monotonic()
    report_path=output/"simulation_report.json"
    trajectory_path=output/"trajectory.json"
    urdf_path=output/"quadruped.urdf"
    report=json.loads(report_path.read_text())
    trajectory=json.loads(trajectory_path.read_text())
    if sha(urdf_path)!=report["inputs"]["urdf_sha256"]:
        raise ValueError("URDF no longer matches the recorded physics run")
    hashes={"simulation_report_sha256":sha(report_path),"trajectory_sha256":sha(trajectory_path),"urdf_sha256":sha(urdf_path)}
    selected=list(range(4,len(trajectory["frames"]),5))
    if selected[-1]!=len(trajectory["frames"])-1:
        raise ValueError("Expected a complete 64 second, 20 Hz recording")
    width,height,fps=640,480,24
    movie=output/"recorded_motion_6x.mp4"
    font=Path("C:/Windows/Fonts/arial.ttf")
    font_arg=f"fontfile='{str(font).replace(chr(92),'/').replace(':',chr(92)+':')}'" if font.is_file() else "font='Arial'"
    filters=",".join([
        "pad=iw:ih+64:0:64:color=0x122129",
        f"drawtext={font_arg}:text='Recorded simulated motion | 6x speed':fontsize=18:fontcolor=white:x=12:y=10",
        f"drawtext={font_arg}:text='Rigid links | 0.588 N m cap | Hardware walking untested':fontsize=14:fontcolor=white:x=12:y=37",
    ])
    command=[ffmpeg,"-hide_banner","-loglevel","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{width}x{height}","-r",str(fps),"-i","-","-vf",filters,"-an","-c:v","libx264","-preset","fast","-crf","20","-pix_fmt","yuv420p","-movflags","+faststart",str(movie)]
    encoder=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    p.connect(p.DIRECT)
    floor_visual=p.createVisualShape(p.GEOM_BOX,halfExtents=[2,2,.01],rgbaColor=[.91,.92,.91,1])
    p.createMultiBody(baseMass=0,baseVisualShapeIndex=floor_visual,basePosition=[0,0,-.01])
    first=trajectory["frames"][selected[0]]
    robot=p.loadURDF(str(urdf_path),basePosition=first["base_m"],baseOrientation=first["base_quat_xyzw"],useFixedBase=False,flags=p.URDF_USE_INERTIA_FROM_FILE)
    joints={p.getJointInfo(robot,i)[1].decode():i for i in range(p.getNumJoints(robot))}
    local_inertial=p.getDynamicsInfo(robot,-1)[3:5]
    view=p.computeViewMatrixFromYawPitchRoll([.01,0,.14],.58,35,-20,0,2)
    projection=p.computeProjectionMatrixFOV(45,width/height,.01,10)
    try:
        for frame_index in selected:
            frame=trajectory["frames"][frame_index]
            # resetBasePositionAndOrientation expects the world inertial-frame pose.
            com_pose=p.multiplyTransforms(frame["base_m"],frame["base_quat_xyzw"],*local_inertial)
            p.resetBasePositionAndOrientation(robot,*com_pose)
            for name,index in joints.items():p.resetJointState(robot,index,frame["joint_rad"][name])
            pixels=p.getCameraImage(width,height,view,projection,lightDirection=[-3,-2,5],shadow=1,renderer=p.ER_TINY_RENDERER)[2]
            encoder.stdin.write(np.asarray(pixels,dtype=np.uint8).reshape(height,width,4)[:,:,:3].tobytes())
        encoder.stdin.close()
        errors=encoder.stderr.read().decode(errors="replace")
        if encoder.wait()!=0:raise RuntimeError(errors)
    finally:
        p.disconnect()
        if encoder.poll() is None:encoder.kill()
    unchanged=hashes=={"simulation_report_sha256":sha(report_path),"trajectory_sha256":sha(trajectory_path),"urdf_sha256":sha(urdf_path)}
    if not unchanged:raise ValueError("Recorded source changed during video rendering")
    receipt={
        "status":"recorded_pose_render_complete",
        "source_manifest_sha256":report["inputs"]["manifest_sha256"],
        **hashes,
        "renderer_sha256":sha(__file__),
        "video_sha256":sha(movie),
        "frame_count":len(selected),
        "pixel_size":[width,height+64],
        "render_pixel_size":[width,height],
        "playback_fps":fps,
        "playback_duration_s":len(selected)/fps,
        "nominal_acceleration_factor":6,
        "source_frame_indices":selected,
        "source_times_s":[trajectory["frames"][i]["time_s"] for i in selected],
        "pose_method":"Exact saved base and joint poses at 4 Hz. No interpolation, newly synthesized poses or simulation steps.",
        "model_scope":"Rigid links with the declared controller assumptions; physical walking and printed strength remain unvalidated.",
        "inputs_unchanged":True,
        "render_wall_seconds":time.monotonic()-started,
    }
    (output/"recorded_motion_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    (output/"recorded_motion_notes.txt").write_text(f"RECORDED SIMULATED MOTION\n\n{len(selected)} exact trajectory poses, shown at 24 fps.\nPlayback duration: {len(selected)/fps:.3f} seconds. Nominal speed: 6x.\nRigid-link model, 0.588 Nm cap. No new poses or dynamics were generated.\nPhysical walking and printed strength remain unvalidated.\n\nTrajectory SHA256: {hashes['trajectory_sha256']}\nPhysics report SHA256: {hashes['simulation_report_sha256']}\nVideo SHA256: {receipt['video_sha256']}\n",encoding="utf-8")
    print(json.dumps({"video":str(movie),"frames":len(selected),"wall_seconds":receipt["render_wall_seconds"]}))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--ffmpeg",default=shutil.which("ffmpeg"))
    args=parser.parse_args()
    if not args.ffmpeg:raise SystemExit("FFmpeg is required to encode the recorded-pose video")
    render(args.output.resolve(),args.ffmpeg)
