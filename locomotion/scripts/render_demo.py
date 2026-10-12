#!/usr/bin/env python3
"""Render the measured simulation pipeline; movies are demonstrations, not acceptance."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageDraw
import imageio.v2 as imageio

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from locomotion.mist_env import MistEnv
from locomotion.provenance import source_hashes, check_sources, identity


def caption(frame, text):
    result=Image.fromarray(frame)
    draw=ImageDraw.Draw(result)
    draw.rectangle((0,0,640,42),fill=(20,25,34))
    draw.text((10,8),text,fill='white')
    draw.text((10,26),'CAD visuals / estimated dynamics / IK baseline / simulation only',fill=(210,215,230))
    return np.asarray(result)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    movie=args.output/'cad_walk_demo.mp4'
    if movie.exists():raise FileExistsError(movie)
    frozen=source_hashes()
    results=[]
    commands={'forward':(.012,0,0),'backward':(-.012,0,0),'left':(0,.012,0),'right':(0,-.012,0)}
    with imageio.get_writer(movie,fps=25,codec='libx264',quality=7) as writer:
        for index,(name,cmd) in enumerate(commands.items()):
            env=MistEnv(command=cmd,terrain='flat',randomize=False,payload=.155,
                        pushes=False,max_steps=400,sensor_mode='mpu6050')
            try:
                _,initial=env.reset(seed=830100+index)
                info=initial;steps=0
                for step in range(400):
                    _,_,terminated,truncated,info=env.step(np.zeros(12))
                    steps=step+1
                    if step%2==0:
                        frame=caption(env.render(),f'{name} | command 0.012 m/s | phone 155 g | t={info["time_s"]:.2f} s')
                        writer.append_data(frame)
                        if index==0 and step==100:Image.fromarray(frame).save(args.output/'cad_preview.png')
                    if terminated or truncated:break
                results.append({'command':name,'steps':steps,'initial_position':initial['position'],
                                'final_position':info['position'],'fell':info['fell'],'sensor_fault':info['sensor_fault']})
                print(name,steps,flush=True)
            finally:env.close()
    check_sources(frozen)
    record={'status':'nominal visual demonstration; no acceptance claim','source_hashes':frozen,
            'source_fingerprint':identity(frozen),'renderer':'PyBullet TinyRenderer','fps':25,'results':results}
    (args.output/'cad_demo.json').write_text(json.dumps(record,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
