"""Reproducible CuraEngine orientation comparison. All emitted G-code is disabled."""
from pathlib import Path
import collections, datetime, gzip, hashlib, json, math, re, subprocess, time
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
SOURCE = PROJECT / 'cad/output/print_stl'
ENGINE = Path('C:/Program Files/UltiMaker Cura 5.13.0/CuraEngine.exe')
DEFS = ENGINE.parent / 'share/cura/resources/definitions'
OUT = HERE / 'ANALYSIS_ONLY'
OUT.mkdir(parents=True, exist_ok=True)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def leaves(data):
    result = {}
    for key, value in data.items():
        if 'children' in value:
            result.update(leaves(value['children']))
        if 'default_value' in value:
            result[key] = {k: value[k] for k in ['default_value', 'type'] if k in value}
    return result

base = leaves(json.loads((DEFS/'fdmprinter.def.json').read_text())['settings'])
extra = leaves(json.loads((DEFS/'fdmextruder.def.json').read_text())['settings'])
base.update(extra)
# CuraEngine does not evaluate Cura frontend formulas. Every input below is
# a concrete value, with unlisted settings using frozen factory defaults.
settings = {
    'machine_width':225, 'machine_depth':225, 'machine_height':265,
    'machine_center_is_zero':False, 'machine_extruder_count':1,
    'machine_name':'Neptune 4 Pro analysis envelope, conservative speeds',
    'machine_gcode_flavor':'RepRap (Marlin/Sprinter)',
    'machine_start_gcode':'', 'machine_end_gcode':'',
    'machine_heated_bed':True, 'machine_nozzle_size':0.4,
    'machine_nozzle_offset_x':0, 'machine_nozzle_offset_y':0,
    'machine_acceleration':1000, 'machine_max_acceleration_x':1000,
    'machine_max_acceleration_y':1000, 'machine_max_acceleration_z':100,
    'machine_max_acceleration_e':1000, 'machine_max_feedrate_x':150,
    'machine_max_feedrate_y':150, 'machine_max_feedrate_z':10,
    'machine_max_feedrate_e':40, 'machine_max_jerk_xy':8,
    'machine_max_jerk_z':0.4, 'machine_max_jerk_e':5,
    'layer_height':0.2, 'layer_height_0':0.2, 'line_width':0.42,
    'initial_layer_line_width_factor':100,
    'wall_line_count':5, 'wall_thickness':2.1,
    'wall_line_width_0':0.42, 'wall_line_width_x':0.42,
    'skin_line_width':0.42, 'infill_line_width':0.42,
    'support_line_width':0.42, 'support_roof_line_width':0.42,
    'support_bottom_line_width':0.42, 'skirt_brim_line_width':0.42,
    'top_layers':6, 'bottom_layers':6, 'top_thickness':1.2,
    'bottom_thickness':1.2, 'top_bottom_thickness':1.2,
    'infill_pattern':'gyroid', 'infill_sparse_density':35,
    'infill_line_distance':0.42/0.35, 'infill_sparse_thickness':0.2,
    'infill_overlap_mm':0.063, 'skin_overlap_mm':0.042,
    'gradual_infill_steps':0, 'infill_before_walls':False,
    'speed_print':60, 'speed_wall':35, 'speed_wall_0':35,
    'speed_wall_x':60, 'speed_infill':80, 'speed_topbottom':35,
    'speed_roofing':35, 'speed_flooring':35,
    'speed_layer_0':20, 'speed_print_layer_0':20,
    'speed_travel_layer_0':50, 'speed_travel':120,
    'speed_support':50, 'speed_support_infill':50,
    'speed_support_roof':30, 'speed_support_bottom':30,
    'skirt_brim_speed':20, 'speed_z_hop':5,
    'acceleration_enabled':True, 'acceleration_print':1000,
    'acceleration_wall':700, 'acceleration_wall_0':700,
    'acceleration_wall_x':1000, 'acceleration_infill':1000,
    'acceleration_topbottom':700, 'acceleration_travel':1000,
    'acceleration_support':1000, 'acceleration_support_infill':1000,
    'acceleration_support_roof':1000, 'acceleration_support_bottom':1000,
    'acceleration_roofing':700, 'acceleration_flooring':700,
    'acceleration_layer_0':500, 'acceleration_print_layer_0':500,
    'acceleration_travel_layer_0':500, 'jerk_enabled':False,
    'material_diameter':1.75, 'material_print_temperature':210,
    'material_print_temperature_layer_0':210,
    'material_initial_print_temperature':210,
    'material_final_print_temperature':210,
    'material_bed_temperature':60, 'material_bed_temperature_layer_0':60,
    'material_max_flowrate':8, 'material_flow':100,
    'material_density':1.24, 'material_type':'PLA',
    'retraction_enable':True, 'retraction_amount':0.5,
    'retraction_speed':35, 'retraction_retract_speed':35,
    'retraction_prime_speed':35, 'retraction_hop_enabled':False,
    'retraction_min_travel':1.5, 'retraction_combing':'noskin',
    'cool_fan_enabled':True, 'cool_fan_speed':100,
    'cool_fan_speed_0':0, 'cool_fan_speed_min':100,
    'cool_fan_speed_max':100, 'cool_fan_full_layer':3,
    'cool_min_layer_time':5, 'cool_min_speed':10,
    'support_enable':True, 'support_structure':'normal',
    'support_type':'everywhere', 'support_angle':50,
    'support_pattern':'zigzag', 'support_infill_rate':15,
    'support_line_distance':0.42/0.15,
    'support_initial_layer_line_distance':0.42/0.15,
    'support_infill_sparse_thickness':0.2, 'support_wall_count':0,
    'support_top_distance':0.2, 'support_bottom_distance':0.2,
    'support_z_distance':0.2, 'support_xy_distance':0.5,
    'support_xy_distance_overhang':0.5,
    'support_interface_enable':True,
    'support_roof_enable':True, 'support_bottom_enable':False,
    'support_roof_height':0.6, 'support_roof_pattern':'lines',
    'support_roof_line_distance':0.42/0.60,
    'support_roof_density':60, 'support_offset':0,
    'support_use_towers':True, 'support_brim_enable':True,
    'support_brim_line_count':3,
    'adhesion_type':'none', 'skirt_line_count':0,
    'prime_blob_enable':False, 'prime_tower_enable':False,
    'center_object':True, 'mesh_position_x':0,
    'mesh_position_y':0, 'mesh_position_z':0,
    'extruder_nr':0, 'wall_0_extruder_nr':0, 'wall_x_extruder_nr':0,
    'infill_extruder_nr':0, 'top_bottom_extruder_nr':0,
    'roofing_extruder_nr':0, 'flooring_extruder_nr':0,
    'support_infill_extruder_nr':0, 'support_extruder_nr_layer_0':0,
    'support_roof_extruder_nr':0, 'support_bottom_extruder_nr':0,
    'adhesion_extruder_nr':0, 'skirt_brim_extruder_nr':0,
}
# Include frontend-only values for a readable audit, but only engine-known
# factory settings are supplied to its concrete definition.
for key, value in settings.items():
    if key in base:
        base[key]['default_value'] = value
resolved = {key:value['default_value'] for key,value in base.items()}
def_path = HERE/'resolved_analysis.def.json'
def_path.write_text(json.dumps({'version':2,'name':'Frozen analysis inputs',
    'metadata':{'visible':False},'settings':base},indent=2)+'\n')
(HERE/'requested_settings.json').write_text(json.dumps(settings,indent=2)+'\n')
(HERE/'resolved_settings.json').write_text(json.dumps(resolved,indent=2)+'\n')

def metrics(gcode):
    counts=collections.defaultdict(float)
    e=0.0; absolute=True; kind='UNCLASSIFIED'; maxflow=0.0
    motion_min=np.full(3,np.inf); motion_max=np.full(3,-np.inf)
    xyz={'X':0.0,'Y':0.0,'Z':0.0}; feed=0.0
    for line in gcode.splitlines():
        if line.startswith(';TYPE:'): kind=line[6:].strip()
        cmd=line.split(';',1)[0].strip()
        if cmd.startswith('M82'): absolute=True
        if cmd.startswith('M83'): absolute=False
        values={k:float(v) for k,v in re.findall(r'([XYZEFT])(-?\d+(?:\.\d+)?)',cmd)}
        if cmd.startswith('G92') and 'E' in values: e=values['E']; continue
        if not (cmd.startswith('G0 ') or cmd.startswith('G1 ')):continue
        if 'F' in values:feed=values['F']/60
        distance=math.sqrt(sum((values.get(k,xyz[k])-xyz[k])**2 for k in xyz))
        if 'E' in values:
            delta=values['E']-e if absolute else values['E']
            e=values['E'] if absolute else e+values['E']
            if delta>0 and distance>0.0001:
                counts[kind]+=delta*math.pi*(1.75/2)**2
                maxflow=max(maxflow,delta*math.pi*(1.75/2)**2*feed/distance)
        xyz.update({k:values[k] for k in xyz if k in values})
        if any(k in values for k in xyz):
            motion_min=np.minimum(motion_min,list(xyz.values()))
            motion_max=np.maximum(motion_max,list(xyz.values()))
    total=sum(counts.values())
    support=sum(value for key,value in counts.items() if key.startswith('SUPPORT'))
    times=re.findall(r'^;TIME_ELAPSED:(\d+(?:\.\d+)?)',gcode,re.M)
    return {'estimated_time_seconds':float(times[-1]) if times else None,
            'motion_bounds_mm':[motion_min.tolist(),motion_max.tolist()],
            'motion_inside_build_envelope':bool(np.all(motion_min>=0) and np.all(motion_max<=np.array([225,225,265]))),
            'extrusion_volume_mm3_by_type':dict(counts),
            'total_extrusion_volume_mm3':total,'support_extrusion_volume_mm3':support,
            'support_mass_g_at_1_24':support*0.00124,'total_mass_g_at_1_24':total*0.00124,
            'support_share_percent':100*support/total if total else 0,
            'peak_nominal_deposition_flow_mm3_s':maxflow,
            'layer_count':len(re.findall(r'^;LAYER:',gcode,re.M))}

jobs=[('femur_main_and_knee_saddle','current',0,50),
      ('tibia_curved_main_and_foot','current',0,50),
      ('coxa_upper_and_hip_saddle','current',0,50),
      ('femur_main_and_knee_saddle','tilt45_about_long_axis',45,50),
      ('femur_main_and_knee_saddle','tilt45_support_angle40',45,40),
      ('coxa_upper_and_hip_saddle','flip_x180',180,50)]
manifest={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'tool':'CuraEngine 5.13.0','engine_path':str(ENGINE),
    'engine_sha256':sha(ENGINE),'source_directory':str(SOURCE),
    'definition_sha256':sha(def_path),
    'purpose':'Support and orientation analysis only. Every G-code command is commented out.',
    'limitations':[
        'This is a frozen numeric engine profile, not the Cura GUI quality profile or a validated machine profile.',
        'Unused settings retain explicit Cura factory defaults. No frontend value expressions are evaluated.',
        'Time estimates are slicer predictions at the recorded conservative acceleration; hardware is unmeasured.',
        'Deposited mass uses 1.24 g/cm3 PLA density and excludes retraction-only moves, purging and startup.',
        'No adhesion brim is used around the model; support brims are enabled.',
        'Support volume is deposited filament, not the empty geometric support envelope.',
        'Slicing predicts support cost, not printed strength or support removability.'
    ],'jobs':[]}
for part,label,angle,support_angle in jobs:
    src=SOURCE/(part+'.stl')
    mesh=trimesh.load_mesh(src)
    source_hash=sha(src)
    source_bounds=mesh.bounds.tolist()
    if angle:
        horizontal=int(np.argmax(mesh.extents[:2]))
        axis=np.eye(3)[horizontal]
        mesh.apply_transform(trimesh.transformations.rotation_matrix(math.radians(angle),axis))
    mesh.apply_translation(-mesh.bounds[0])
    run_name=part+'__'+label
    snapshot=OUT/(run_name+'.stl')
    mesh.export(snapshot)
    raw=OUT/(run_name+'.temporary.gcode')
    args=[str(ENGINE),'slice','-m4','-v','-j',str(def_path),
          '-s','support_angle='+str(support_angle),'-e0',
          '-o',str(raw),'-l',str(snapshot)]
    start=time.monotonic()
    run=subprocess.run(args,capture_output=True,text=True,timeout=150)
    elapsed=time.monotonic()-start
    log=OUT/(run_name+'.log.txt')
    log.write_text(run.stdout+'\n'+run.stderr,encoding='utf-8')
    row={'part':part,'orientation':label,'tilt_deg':angle,
        'support_angle_deg':support_angle,
        'source_sha256':source_hash,'source_bounds_mm':source_bounds,
        'snapshot_sha256':sha(snapshot),'print_extents_mm':mesh.extents.tolist(),
        'watertight':bool(mesh.is_watertight),'return_code':run.returncode,
        'elapsed_seconds':elapsed,'command':args,'log_path':str(log)}
    if run.returncode==0 and raw.exists():
        gcode=raw.read_text(encoding='utf-8')
        # CLI writes placeholder file headers but logs the final header.
        # Replace the placeholder with that exact logged header before saving.
        final_header=re.search(r'Gcode header after slicing: (;FLAVOR:.*?)(?:\n\s*\n)',run.stdout+'\n'+run.stderr,re.S)
        if final_header:
            gcode=re.sub(r'\A;FLAVOR:.*?\n\s*\n',final_header.group(1)+'\n\n',gcode,count=1,flags=re.S)
        row.update(metrics(gcode))
        engine_volume=re.findall(r'Filament \(mm\^3\): (\d+(?:\.\d+)?)',run.stdout+'\n'+run.stderr)
        if engine_volume:
            row['engine_filament_volume_mm3']=float(engine_volume[-1])
            row['extrusion_accounting_difference_percent']=100*(row['total_extrusion_volume_mm3']-row['engine_filament_volume_mm3'])/row['engine_filament_volume_mm3']
        row['raw_gcode_sha256']=hashlib.sha256(gcode.encode()).hexdigest()
        disabled=OUT/(run_name+'.disabled.gcode.gz')
        disabled_text=('; ANALYSIS ONLY. ALL MACHINE COMMANDS DISABLED. DO NOT PRINT.\n'+
            '\n'.join(line if line.startswith(';') else '; DISABLED| '+line
                      for line in gcode.splitlines())+'\n')
        disabled.write_bytes(gzip.compress(disabled_text.encode('utf-8'),mtime=0))
        raw.unlink()
        row['disabled_gcode_path']=str(disabled)
        row['disabled_gcode_sha256']=sha(disabled)
    manifest['jobs'].append(row)
    (HERE/'slice_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:v for k,v in row.items() if k in ['part','orientation',
        'return_code','estimated_time_seconds','support_mass_g_at_1_24',
        'total_mass_g_at_1_24','peak_nominal_deposition_flow_mm3_s']}),flush=True)

lines=['# CuraEngine orientation comparison','',
       'Analysis only. All saved G-code commands are disabled. Do not send these files to a printer.','',
       '| Part | Orientation | Support angle | Time min | Model and support g | Support g | Support share |',
       '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
for row in manifest['jobs']:
    if row['return_code']==0:
        lines.append(f"| {row['part']} | {row['orientation']} | {row['support_angle_deg']} | {row['estimated_time_seconds']/60:.1f} | {row['total_mass_g_at_1_24']:.2f} | {row['support_mass_g_at_1_24']:.2f} | {row['support_share_percent']:.1f}% |")
lines += ['', 'Settings: 0.4 mm nozzle, 0.20 mm layers, 0.42 mm lines, five walls, six top and bottom layers, 35% gyroid, 210/60 C PLA, 20 mm/s first layer, 35 mm/s outer walls, 60 mm/s inner walls, 80 mm/s infill. Supports are normal zigzag at 15%, with a 0.6 mm roof at 60%, 0.2 mm vertical separation, 0.5 mm XY separation and a 50 degree overhang angle. The nominal build envelope is 225 x 225 x 265 mm.', '',
          'Source hashes and frozen numeric inputs are recorded in slice_manifest.json and resolved_settings.json. The comparison describes the source snapshots only; subsequent CAD revisions need new slicing.', '',
          'Limitations:', '']+['- '+line for line in manifest['limitations']]
first,last=manifest['jobs'][0],manifest['jobs'][3]
if first.get('return_code')==0 and last.get('return_code')==0:
    lines += ['',f"At the 50 degree support threshold, the 45 degree femur variant reduces deposited support by {100*(1-last['support_extrusion_volume_mm3']/first['support_extrusion_volume_mm3']):.1f}% and total deposited material by {100*(1-last['total_extrusion_volume_mm3']/first['total_extrusion_volume_mm3']):.1f}%. Its estimated time is {100*(1-last['estimated_time_seconds']/first['estimated_time_seconds']):.1f}% shorter. This is a candidate orientation, subject to load-direction review and an adhesion test: it has no model brim in this comparison."]
    lines += ['', 'The additional 40 degree threshold slice tests sensitivity: a 50 degree setting deliberately leaves nominal 45 degree planes unsupported. Their ability to print well still depends on cooling, bead overlap and the actual PLA. The long X axis remains parallel to the layer plane under the X rotation, but bracket surfaces change orientation and the small initial contact needs a physical adhesion check.']
    lines += ['', 'The coxa X180 flip changes support from about 3.33 g to 3.24 g and estimated time from 156.8 to 156.5 minutes. This small difference means plate contact and load direction should drive the orientation decision.']
(HERE/'SLICER_COMPARISON.md').write_text('\n'.join(lines)+'\n')
(HERE/'SLICER_COMPARISON.txt').write_text('\n'.join(lines)+'\n')
