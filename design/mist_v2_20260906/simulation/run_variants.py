"""Bounded follow-up experiments prompted by analytic overload and model uncertainty."""
import copy
import json
from model import ROOT,load_parameters
from run_sim import run_case
from refresh_summary import refresh

p=load_parameters()
hip=copy.deepcopy(p);hip["transmission"]["ratios"]=[2,3.5,2]
hip["status"]="ratio_experiment_not_selected_CAD"
root=ROOT/"variants"/"hip_3p5"
for case in ["crawl","drive"]:
    r=run_case(hip,case,output_root=root)
    print(json.dumps({k:r[k] for k in ["case","status","max_tilt_deg","joint_tracking_rms_deg","base_displacement_m"]}),flush=True)
refresh(root)
adverse=copy.deepcopy(p)
adverse["servo"]["command_delay_s"]=.060
adverse["servo"]["response_time_constant_s"]=.050
adverse["servo"]["gearbox_backlash_full_width_deg"]=2.0
adverse["environment"]["tire_friction_coefficient"]=.35
adverse["transmission"]["output_stiffness_nm_per_rad"]=[75,60,50]
adverse["status"]="adverse_unmeasured_assumption_sensitivity"
root=ROOT/"variants"/"adverse"
for case in ["drive"]:
    r=run_case(adverse,case,output_root=root)
    print(json.dumps({k:r[k] for k in ["case","status","max_tilt_deg","joint_tracking_rms_deg","base_displacement_m"]}),flush=True)
refresh(root)
