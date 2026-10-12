"""Versioned engineering targets, fixed before policy selection."""
import math
import numpy as np

VERSION='simulation-walking-v2'
COMMANDS={'stop':(0.,0.,0.),'forward':(.01,0.,0.),'backward':(-.01,0.,0.),'left':(0.,.01,0.),'right':(0.,-.01,0.),'clockwise':(0.,0.,-.04),'counterclockwise':(0.,0.,.04),'combined':(.007,.007,.02),'transient':(.01,0.,0.)}
CRITERIA={'min_duration_s':19.2,'min_progress_fraction':.5,'max_sideways_m':.03,'max_yaw_error_rad':.2,'max_tilt_rad':.35,'max_stop_displacement_m':.02,'max_velocity_rmse_m_s':.015,'max_yaw_rate_rmse_rad_s':.06,'max_tracking_error_rad':.25,'max_saturation_fraction':.25,'contact_force_threshold_n':.1}

def command_at(name, initial, step, steps):
    if name!='transient': return initial
    return ((.01,0.,0.),(0.,.01,0.),(0.,0.,.04),(0.,0.,0.))[min(3,4*step//steps)]

def score(initial,rows,command,expected_steps=None):
    if not rows: raise ValueError('episode requires samples')
    duration=rows[-1]['time_s']-initial['time_s']
    yaw=np.unwrap([initial['rpy'][2]]+[r['rpy'][2] for r in rows]); desired=np.asarray(initial['position'][:2],float).copy()
    tracking=[];vel=[];rates=[];deviation=[];dtprev=initial['time_s'];yaw_target=yaw[0];yaw_errors=[]
    for i,r in enumerate(rows):
        dt=r['time_s']-dtprev;dtprev=r['time_s'];cmd=np.asarray(r.get('command',command));c,s=math.cos(yaw[i]),math.sin(yaw[i]);desired+=dt*np.array([c*cmd[0]-s*cmd[1],s*cmd[0]+c*cmd[1]]);yaw_target+=dt*cmd[2]
        deviation.append(np.linalg.norm(np.asarray(r['position'][:2])-desired));vel.append(np.sum((np.asarray(r['body_velocity'][:2])-cmd[:2])**2));rates.append((r.get('body_angular_velocity',[0,0,float('nan')])[2]-cmd[2])**2);yaw_errors.append(abs(yaw[i+1]-yaw_target));tracking.append(r.get('tracking_error_rad',float('nan')))
    displacement=np.asarray(rows[-1]['position'])-initial['position'];speed=np.linalg.norm(command[:2]);heading=np.array([math.cos(yaw[0]),math.sin(yaw[0])]);direction=np.array(command[:2])/speed if speed else np.zeros(2);rot=np.array([[heading[0],-heading[1]],[heading[1],heading[0]]]);progress=float(displacement[:2]@(rot@direction))
    m={'duration_s':duration,'progress_m':progress,'command_distance_m':speed*duration,'body_velocity_rmse_m_s':float(np.sqrt(np.mean(vel))),'yaw_rate_rmse_rad_s':float(np.sqrt(np.mean(rates))),'peak_path_error_m':float(max(deviation)),'peak_yaw_error_rad':float(max(yaw_errors)),'peak_tilt_rad':float(max(abs(v) for r in rows for v in r['rpy'][:2])),'peak_tracking_error_rad':float(max(tracking)),'saturation_fraction':float(rows[-1].get('torque_saturation_fraction',float('nan')))}
    fixed=all(np.allclose(r.get('command',command),command) for r in rows)
    checks={'duration':duration>=CRITERIA['min_duration_s']-1e-9,'complete':expected_steps is None or len(rows)==expected_steps,'finite':all(math.isfinite(v) for v in m.values()) and all(np.isfinite(r[k]).all() for r in rows for k in ('position','rpy','body_velocity')),'no_falls':not any(r['fell'] for r in [initial]+rows),'no_sensor_fault':not any(r.get('sensor_fault',False) for r in [initial]+rows),'no_body_ground_contact':all(r.get('body_ground_contact') is False for r in [initial]+rows),'no_nonfoot_ground_contact':all(r.get('nonfoot_ground_contact') is False for r in [initial]+rows),'progress':not fixed or command[2]!=0 or speed==0 or progress>=.5*speed*duration,'path':m['peak_path_error_m']<= (.02 if speed==0 else .03),'velocity':m['body_velocity_rmse_m_s']<=.015,'yaw_rate':m['yaw_rate_rmse_rad_s']<=.06,'yaw':m['peak_yaw_error_rad']<=.2,'tilt':m['peak_tilt_rad']<=.35,'tracking':m['peak_tracking_error_rad']<=.25,'saturation':m['saturation_fraction']<=.25}
    return {'passed':all(checks.values()),'checks':checks,'metrics':m,'criteria':CRITERIA,'acceptance_version':VERSION}
