"""Headless R7 rigid-body environment with hardware-available observations."""
from __future__ import annotations
import tempfile
from collections import deque
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import gymnasium as gym
from gymnasium import spaces
import pybullet as p
try:
    from .model import export_models, JOINT_NAMES, LEGS, NEUTRAL, MOUNTS, load_config, validate_config
    from .kinematics import forward
    from .gait import CrawlController
    from .servo import ServoBank
    from .sensor_sim import SimulatedIMU, attitude_from_gravity
except ImportError:
    from model import export_models, JOINT_NAMES, LEGS, NEUTRAL, MOUNTS, load_config, validate_config
    from kinematics import forward
    from gait import CrawlController
    from servo import ServoBank
    from sensor_sim import SimulatedIMU, attitude_from_gravity


class MistEnv(gym.Env):
    metadata = {'render_modes': ['rgb_array'], 'render_fps': 50}
    def __init__(self, command=None, terrain='flat', randomize=True, payload=None,
                 render_mode=None, max_steps=1000, torque_cap=None, pushes=True,
                 sensor_mode='mpu6050', sensor_profile=None, scenario=None, config=None):
        super().__init__()
        from copy import deepcopy
        self.cfg = load_config() if config is None else validate_config(deepcopy(config))
        self.ranges = self.cfg['randomization']
        if terrain not in ('flat', 'low_friction', 'slope', 'rough', 'mixed'):
            raise ValueError('unknown terrain')
        if render_mode not in (None, 'rgb_array'):
            raise ValueError('render_mode must be None or rgb_array')
        self.fixed_command = None if command is None else np.asarray(command, dtype=float)
        self.terrain_spec, self.terrain = terrain, terrain
        self.randomize, self.payload = randomize, payload
        self.render_mode, self.max_steps, self.torque_cap, self.pushes = render_mode, max_steps, torque_cap, pushes
        # Validate before allocating the Bullet client; reset seeds its RNG.
        self.sensor = SimulatedIMU(sensor_mode, sensor_profile)
        self.scenario = validate_scenario(scenario)
        self.action_space = spaces.Box(-1., 1., (12,), dtype=np.float32)
        self.observation_space = spaces.Box(-np.inf, np.inf, (47,), dtype=np.float32)
        self.client = p.connect(p.DIRECT)
        self.temp = tempfile.TemporaryDirectory(prefix='mist-r7-')
        self.gait = CrawlController(config=self.cfg)
        self.dt = 1/self.cfg['simulation']['physics_hz']
        self.substeps = round(self.cfg['simulation']['physics_hz']/self.cfg['simulation']['control_hz'])
        self.previous_action = np.zeros(12)

    def _call(self, fn, *args, **kw):
        return fn(*args, physicsClientId=self.client, **kw)

    def _terrain(self):
        friction = .28 if self.terrain == 'low_friction' else self.cfg['simulation']['foot_friction']
        if self.randomize:
            friction = friction*self.np_random.uniform(.7, 1.3) if self.terrain == 'low_friction' else self.np_random.uniform(*self.ranges['friction'])
        self.friction = float(friction)
        self.friction = self.effective_scenario.get('friction',self.friction)
        if self.terrain == 'rough':
            n = 64
            heights = self.np_random.uniform(*self.ranges['roughness_height_m'], (n,n))
            shape = self._call(p.createCollisionShape, p.GEOM_HEIGHTFIELD, meshScale=[.04,.04,1],
                               heightfieldData=heights.ravel().tolist(), numHeightfieldRows=n, numHeightfieldColumns=n)
            self.floor = self._call(p.createMultiBody, 0, shape)
        else:
            shape = self._call(p.createCollisionShape, p.GEOM_BOX, halfExtents=[3,3,.01])
            slope = self.np_random.uniform(*self.ranges['slope_deg']) if self.randomize else 3.
            orientation = p.getQuaternionFromEuler([0, np.radians(slope) if self.terrain == 'slope' else 0, 0])
            self.floor = self._call(p.createMultiBody, 0, shape, basePosition=[0,0,-.01], baseOrientation=orientation)
        # Bullet multiplies the two contact coefficients. Keep the floor at 1
        # so the reported robot coefficient is the effective pair coefficient.
        self._call(p.changeDynamics, self.floor, -1, lateralFriction=1., restitution=self.cfg['simulation']['contact_restitution'])

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if options is not None and (not isinstance(options,dict) or set(options)-{'scenario'}):
            raise ValueError('reset options support only a scenario object')
        self.effective_scenario = validate_scenario(options['scenario']) if options and 'scenario' in options else self.scenario.copy()
        self._call(p.resetSimulation)
        self._call(p.setTimeStep, self.dt)
        self._call(p.setGravity, 0,0,-9.81)
        self._call(p.setPhysicsEngineParameter, numSolverIterations=80, deterministicOverlappingPairs=1)
        self.terrain = str(self.np_random.choice(['flat','low_friction','slope','rough'],p=[.5,.2,.15,.15])) if self.terrain_spec == 'mixed' else self.terrain_spec
        self._terrain()
        if self.payload is None:
            nominal_phone = self.cfg['body']['phone_mass_kg']
            self.phone_mass = float(nominal_phone if self.np_random.random()<self.ranges['phone_presence_probability'] else 0) if self.randomize else nominal_phone
        else:
            self.phone_mass = float(self.payload)
        if not 0 <= self.phone_mass <= .4:
            raise ValueError('phone payload must be between 0 and .4 kg')
        if self.sensor.mode == 'phone' and self.phone_mass <= 0:
            raise ValueError('phone sensor mode requires a present phone payload; use mpu6050 or explicit none mode')
        models = export_models(phone_mass_kg=self.phone_mass, output_dir=Path(self.temp.name), config=self.cfg)
        urdf = Path(models['quadruped'])
        tree = ET.parse(urdf)
        self.com_shift = np.zeros(3)
        self.phone_shift = np.zeros(3)
        if self.randomize:
            self.com_shift[:2] = self.np_random.uniform(*self.ranges['body_com_xy_m'],2)
            self.phone_shift[:2] = self.np_random.uniform(*self.ranges['phone_offset_xy_m'],2)
        self.com_shift += self.effective_scenario.get('body_com_shift_m',[0.,0.,0.])
        self.phone_shift += self.effective_scenario.get('phone_offset_m',[0.,0.,0.])
        inertial = tree.getroot().find('link/inertial/origin')
        if inertial is None:
            raise ValueError('body inertial origin required for COM variation')
        xyz = np.fromstring(inertial.get('xyz','0 0 0'),sep=' ')
        inertial.set('xyz',' '.join(map(str,xyz+self.com_shift)))
        for joint in tree.findall('joint'):
            child = joint.find('child')
            if child is not None and child.get('link')=='phone':
                origin = joint.find('origin')
                xyz = np.fromstring(origin.get('xyz','0 0 0'),sep=' ')
                origin.set('xyz',' '.join(map(str,xyz+self.phone_shift)))
        tree.write(urdf, encoding='utf-8', xml_declaration=True)
        height = .005 - (MOUNTS['FL']['xyz'][2]+forward(NEUTRAL)[2])
        self.robot = self._call(p.loadURDF, str(urdf), basePosition=[0,0,height+.004],
                              flags=p.URDF_USE_INERTIA_FROM_FILE | p.URDF_USE_SELF_COLLISION | p.URDF_USE_SELF_COLLISION_EXCLUDE_PARENT)
        # Bullet reports the floating base's principal-inertia frame. IMU and
        # command axes belong to the CAD body frame, which can be quite different.
        dynamics = self._call(p.getDynamicsInfo,self.robot,-1)
        self.inertial_to_body = p.invertTransform(dynamics[3],dynamics[4])
        names = {self._call(p.getJointInfo,self.robot,i)[1].decode():i for i in range(self._call(p.getNumJoints,self.robot))}
        self.indices = [names[name] for name in JOINT_NAMES]
        self.links = {self._call(p.getJointInfo,self.robot,i)[12].decode():i for i in range(self._call(p.getNumJoints,self.robot))}
        self.limits = np.array([self._call(p.getJointInfo,self.robot,i)[8:10] for i in self.indices])
        scales = {}
        for i in [-1]+list(range(self._call(p.getNumJoints,self.robot))):
            mass, _, inertia, *_ = self._call(p.getDynamicsInfo,self.robot,i)
            scale = float(self.np_random.uniform(*(self.ranges['body_mass_scale'] if i==-1 else self.ranges['link_mass_scale']))) if self.randomize else 1.
            scale *= self.effective_scenario.get('mass_scale',1.)
            scales[str(i)] = scale
            self._call(p.changeDynamics,self.robot,i,mass=mass*scale,
                       localInertiaDiagonal=(np.array(inertia)*scale).tolist(), lateralFriction=self.friction,
                       restitution=self.cfg['simulation']['contact_restitution'], linearDamping=.02, angularDamping=.02)
        q = np.tile(NEUTRAL,4)
        for i, angle in zip(self.indices,q):
            self._call(p.resetJointState,self.robot,i,float(angle))
        self._call(p.setJointMotorControlArray,self.robot,self.indices,p.VELOCITY_CONTROL,forces=[0.]*12)
        self.servos = ServoBank(q,self.np_random,self.randomize,self.torque_cap,self.dt,config=self.cfg)
        self.servos.strength *= self.effective_scenario.get('motor_strength',1.)
        self.servos.voltage = self.effective_scenario.get('voltage_v',self.servos.voltage)
        if 'motor_delay_s' in self.effective_scenario:
            self.servos.delay_steps = round(self.effective_scenario['motor_delay_s']/self.dt)
            self.servos.queue = deque([q.copy() for _ in range(self.servos.delay_steps+1)],maxlen=self.servos.delay_steps+1)
        self.mass_scales = scales
        self.previous_action = np.zeros(12)
        self.step_count = 0
        self.ik_rejections = 0
        self.command = self.fixed_command.copy() if self.fixed_command is not None else np.r_[self.np_random.uniform(-.012,.012,2), self.np_random.uniform(-.06,.06)]
        if self.command.shape != (3,) or not np.all(np.isfinite(self.command)):
            raise ValueError('command must be three finite numbers')
        self.sensor.rng = np.random.default_rng(self.np_random.integers(0, 2**63))
        self.sensor.reset()
        self.sensor_fault = False
        self.physics_time_s = 0.0
        self._advance_sensor()
        for _ in range(120):
            self._physics(q)
        self.initial_position = self._orientation()[0].copy()
        self.saturation_sum, self.saturation_count = 0., 0
        self.last_target = q.copy()
        return self._obs(), self._info()

    def _joint_state(self):
        states = np.asarray(self._call(p.getJointStates,self.robot,self.indices),dtype=object)
        return np.asarray(states[:,0],float), np.asarray(states[:,1],float)

    def _physics(self, target):
        q, qdot = self._joint_state()
        tau = self.servos.advance(target,q,qdot)
        self._call(p.setJointMotorControlArray,self.robot,self.indices,p.TORQUE_CONTROL,forces=tau.tolist())
        self._call(p.stepSimulation)
        self.physics_time_s += self.dt
        self._advance_sensor()

    def _advance_sensor(self):
        if self.sensor.mode == 'none':
            self.sensor.advance(self.physics_time_s)
        else:
            _, rotation, _ = self._orientation()
            _, omega = self._call(p.getBaseVelocity, self.robot)
            self.sensor.advance(self.physics_time_s, rotation, omega)

    def _orientation(self):
        pos, quat = self._call(p.getBasePositionAndOrientation,self.robot)
        pos, quat = p.multiplyTransforms(pos,quat,*self.inertial_to_body)
        rotation = np.array(p.getMatrixFromQuaternion(quat)).reshape(3,3)
        return np.asarray(pos), rotation, np.asarray(p.getEulerFromQuaternion(quat))

    def _obs(self):
        q,qdot = self._joint_state()
        gravity,gyro = self.sensor.observation()
        if self.randomize:
            q += self.np_random.normal(0,self.ranges['encoder_noise_std_rad'],12)
            qdot += self.np_random.normal(0,self.ranges['encoder_velocity_noise_std_rad_s'],12)
        ticks = self.cfg['actuator']['position_quantization_rad']
        q = np.round(q/ticks)*ticks
        phase = 2*np.pi*(self.step_count*self.dt*self.substeps/self.gait.cycle_s)
        return np.r_[gravity,gyro,q-np.tile(NEUTRAL,4),qdot,self.command,
                     self.previous_action,math_sin_cos(phase)].astype(np.float32)

    def _info(self):
        pos,rotation,rpy = self._orientation()
        velocity,omega = self._call(p.getBaseVelocity,self.robot)
        com_velocity = np.asarray(velocity)
        com_position = np.asarray(self._call(p.getBasePositionAndOrientation,self.robot)[0])
        velocity = com_velocity+np.cross(omega,pos-com_position)
        q,_ = self._joint_state()
        contacts = self._call(p.getContactPoints,bodyA=self.robot,bodyB=self.floor)
        foot_indices = {self.links[f'{leg}_toe'] for leg in LEGS}
        loaded_contacts = [c for c in contacts if c[9]>.1]
        nonfoot_contact = any(c[3] not in foot_indices for c in loaded_contacts)
        body_ground_contact = any(c[3]==-1 for c in loaded_contacts)
        fell = bool(np.any(np.abs(rpy[:2]) > .7) or pos[2] < .035 or not np.all(np.isfinite(q)))
        return {'fell':fell, 'sensor_fault':self.sensor_fault, 'position':pos.tolist(),'velocity':list(velocity),'rpy':rpy.tolist(),
                'body_velocity':(rotation.T@np.asarray(velocity)).tolist(),
                'body_angular_velocity':(rotation.T@np.asarray(omega)).tolist(),
                'com_velocity':com_velocity.tolist(),
                'nonfoot_ground_contact':nonfoot_contact,'body_ground_contact':body_ground_contact,
                'time_s':self.step_count*self.substeps*self.dt,
                'torque_saturation_fraction':self.saturation_sum/max(1,self.saturation_count),
                'tracking_error_rad':float(np.mean(np.abs(q-self.last_target))),
                'phone_mass_kg':self.phone_mass,'command':self.command.tolist(),
                'terrain':self.terrain,
                'sensor':self.sensor.status(),
                'ik_rejections':self.ik_rejections,
                'temperature_c_proxy':self.servos.temperature.tolist(),
                'randomization':{'mass_scales':self.mass_scales,'body_com_shift_m':self.com_shift.tolist(),
                                 'phone_shift_m':self.phone_shift.tolist(),'friction':self.friction,
                                 'scenario':self.effective_scenario,
                                 **self.servos.description()}}

    def step(self, action):
        action = np.asarray(action,dtype=float)
        if action.shape != (12,) or not np.all(np.isfinite(action)):
            raise ValueError('action must be twelve finite residuals')
        action = np.clip(action,-1,1)
        time_s = self.step_count*self.substeps*self.dt
        gravity,_ = self.sensor.observation()
        status = self.sensor.status()
        self.sensor_fault = self.sensor_fault or (self.sensor.mode != 'none' and status['stale'])
        attitude = np.zeros(2) if self.sensor.mode == 'none' or self.sensor_fault else attitude_from_gravity(gravity)
        try:
            target = self.gait.position_targets(time_s,self.command,attitude=attitude,phone_mass_kg=self.phone_mass)
        except ValueError:
            self.ik_rejections += 1
            target = np.tile(NEUTRAL,4)
        target = np.clip(target+.10*action,self.limits[:,0]+.002,self.limits[:,1]-.002)
        if self.sensor_fault:
            target = self.last_target.copy()
        for _ in range(self.substeps):
            if self.randomize and self.pushes and self.step_count > 50 and self.np_random.random()<.0008:
                force = np.r_[self.np_random.uniform(-3,3,2),0.]
                pos = self._call(p.getBasePositionAndOrientation,self.robot)[0]
                self._call(p.applyExternalForce,self.robot,-1,force.tolist(),pos,p.WORLD_FRAME)
            self._physics(target)
            self.saturation_sum += float(np.mean(self.servos.saturation))
            self.saturation_count += 1
        self.last_target = target
        self.step_count += 1
        info = self._info()
        v = np.asarray(info['body_velocity'])[:2]
        yaw_error = info['body_angular_velocity'][2]-self.command[2]
        tracking = np.exp(-np.sum((v-self.command[:2])**2)/.0004-yaw_error**2/.04)
        upright = np.exp(-np.sum(np.asarray(info['rpy'])[:2]**2)/.09)
        reward = float(tracking+.5*upright+.05-.01*np.mean(action**2)
                       -.02*np.mean((action-self.previous_action)**2)-.005*np.mean(self.servos.torque**2))
        if info['fell']:
            reward -= 3.
        self.previous_action = action.copy()
        return self._obs(),reward,info['fell'] or self.sensor_fault,self.step_count>=self.max_steps,info

    def render(self):
        pos = self._call(p.getBasePositionAndOrientation,self.robot)[0]
        view = p.computeViewMatrixFromYawPitchRoll(pos,.75,40,-25,0,2)
        projection = p.computeProjectionMatrixFOV(55,640/480,.02,10.)
        result = self._call(p.getCameraImage,640,480,viewMatrix=view,projectionMatrix=projection,renderer=p.ER_TINY_RENDERER)
        return np.asarray(result[2],dtype=np.uint8).reshape(480,640,4)[:,:,:3]

    def close(self):
        if p.isConnected(self.client):
            p.disconnect(self.client)
        self.temp.cleanup()


def math_sin_cos(phase):
    return [np.sin(phase),np.cos(phase)]


def validate_scenario(value):
    if value is None:return {}
    if not isinstance(value,dict):raise ValueError('scenario must be an object')
    bounds={'mass_scale':(.5,1.5),'motor_strength':(.25,1.5),'voltage_v':(9.,13.),
            'motor_delay_s':(0.,1.),'friction':(0.,2.)}
    vectors={'body_com_shift_m','phone_offset_m'}
    if set(value)-set(bounds)-vectors:raise ValueError('unknown scenario field')
    result={}
    for key,item in value.items():
        if key in vectors:
            vec=np.asarray(item,dtype=float)
            if vec.shape!=(3,) or not np.all(np.isfinite(vec)) or np.any(np.abs(vec)>.05):
                raise ValueError(f'{key} requires three finite offsets within +/- .05 m')
            result[key]=vec.tolist()
        else:
            if isinstance(item,(bool,np.bool_)) or not isinstance(item,(int,float)) or not np.isfinite(item):
                raise ValueError(f'{key} requires a finite number')
            if not bounds[key][0]<=item<=bounds[key][1]:raise ValueError(f'{key} outside supported scenario bounds')
            result[key]=float(item)
    return result
