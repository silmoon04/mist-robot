"""Local browser controller and CAD preview for the headless simulation."""
from __future__ import annotations
import argparse
import base64
import io
import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import threading
import time
import numpy as np
from PIL import Image
try:
    from .mist_env import MistEnv
    from .kinematics import inverse
except ImportError:
    from mist_env import MistEnv
    from kinematics import inverse

try:
    from .provenance import verify_checkpoint
    from .sensor_sim import SimulatedIMU
except ImportError:
    from provenance import verify_checkpoint
    from sensor_sim import SimulatedIMU


class Simulation:
    def __init__(self):
        self.lock=threading.RLock();self.running=True;self.last_command=0.;self.policy=None
        self.reset({})
        self.thread=threading.Thread(target=self.worker,daemon=True);self.thread.start()

    def reset(self,data):
        with self.lock:
            if not isinstance(data,dict):raise ValueError('request must be an object')
            mode=data.get('controller','ik')
            if mode not in ('ik','ppo','sac'):raise ValueError('unknown controller')
            seed=int(data.get('seed',42))
            if seed<0:raise ValueError('seed must be nonnegative')
            randomize=data.get('randomize',False)
            if not isinstance(randomize,bool):raise ValueError('randomize must be boolean')
            sensor_mode=data.get('sensor_mode','mpu6050')
            sensor=SimulatedIMU(sensor_mode,data.get('sensor_profile'))
            profile=sensor.profile if sensor_mode!='none' else None
            policy=None;policy_status='baseline_unqualified'
            if mode in ('ppo','sac'):
                from stable_baselines3 import PPO,SAC
                checkpoint=Path(data.get('checkpoint','')).expanduser().resolve()
                record=verify_checkpoint(checkpoint,mode,sensor_mode=sensor_mode,sensor_profile=profile)
                policy_status=record['status']
                if not checkpoint.exists():raise ValueError('development checkpoint has not been produced')
                policy=(PPO if mode=='ppo' else SAC).load(checkpoint,device='cpu')
            candidate=MistEnv(command=(0,0,0),terrain=data.get('terrain','flat'),
                             payload=float(data.get('payload',.155)),randomize=randomize,max_steps=100000,sensor_mode=sensor_mode,sensor_profile=profile)
            try:
                obs,info=candidate.reset(seed=seed)
                stream=io.BytesIO();Image.fromarray(candidate.render()).save(stream,format='JPEG',quality=80)
                preview=base64.b64encode(stream.getvalue()).decode()
            except Exception:
                candidate.close();raise
            previous=getattr(self,'env',None)
            self.env,self.obs,self.info,self.image=candidate,obs,info,preview
            self.stopped=False;self.last_command=0.;self.policy=policy;self.error=None
            self.mode=mode;self.seed=seed;self.policy_status=policy_status
            if previous is not None:previous.close()

    def _render(self):
        stream=io.BytesIO();Image.fromarray(self.env.render()).save(stream,format='JPEG',quality=80)
        self.image=base64.b64encode(stream.getvalue()).decode()

    def worker(self):
        while self.running:
            started=time.monotonic()
            with self.lock:
                try:
                    if started-self.last_command>.35:self.env.command=np.zeros(3)
                    if not self.stopped:
                        action=np.zeros(12) if self.policy is None else self.policy.predict(self.obs,deterministic=True)[0]
                        self.obs,_,fell,_,self.info=self.env.step(action)
                        self.stopped=fell
                    if self.env.step_count%5==0 and not self.stopped:self._render()
                except Exception as exc:
                    self.stopped=True;self.error=str(exc)
            time.sleep(max(.001,self.env.dt*self.env.substeps-(time.monotonic()-started)))

    def command(self,data):
        cmd=np.asarray(data.get('command'),dtype=float)
        if cmd.shape!=(3,) or not np.all(np.isfinite(cmd)):raise ValueError('three finite command values required')
        with self.lock:
            self.env.command=np.clip(cmd,[-.012,-.012,-.06],[.012,.012,.06]);self.last_command=time.monotonic()

    def state(self):
        with self.lock:return {'image':self.image,'info':self.info,'fell':self.stopped,'controller':self.mode,
                              'error':self.error,'seed':self.seed,'policy_status':self.policy_status,'sensor':self.env.sensor.status(),
                              'status':'simulation only; walking and real transfer are unqualified'}

    def close(self):
        self.running=False;self.thread.join(timeout=2);self.env.close()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8131);args=ap.parse_args()
    sim=Simulation()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,value,mime='application/json',status=200):
            body=value if isinstance(value,bytes) else json.dumps(value,allow_nan=False).encode()
            self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def do_GET(self):
            if self.path=='/':self.send(Path(__file__).with_name('sim_remote.html').read_bytes(),'text/html; charset=utf-8')
            elif self.path=='/api/state':self.send(sim.state())
            else:self.send({'error':'not found'},status=404)
        def do_POST(self):
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 1<=size<=8192:raise ValueError('request length must be between 1 and 8192 bytes')
                data=json.loads(self.rfile.read(size))
                if not isinstance(data,dict):raise ValueError('request must be an object')
                if self.path=='/api/reset':sim.reset(data)
                elif self.path=='/api/command':sim.command(data)
                elif self.path=='/api/ik':
                    q=inverse(np.asarray(data['foot_mm'],float)/1000)
                    self.send({'q_rad':q.tolist(),'q_deg':np.degrees(q).tolist()});return
                else:raise ValueError('unknown operation')
                self.send({'ok':True})
            except (ValueError,KeyError,TypeError,RuntimeError,OSError) as exc:self.send({'error':str(exc)},status=400)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'Simulation remote: http://127.0.0.1:{args.port}',flush=True)
    try:server.serve_forever()
    finally:server.server_close();sim.close()


if __name__=='__main__':main()
