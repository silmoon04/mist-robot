"""Build a Cura 5.13 quality profile for the R5 first-fit PLA plate."""
from pathlib import Path
import configparser
import hashlib
import io
import json
import zipfile

HERE=Path(__file__).resolve().parent
CURA=Path('C:/Program Files/UltiMaker Cura 5.13.0')
NAME='HexQuad R5 - First Fit PLA - 0.20mm'
FILE=HERE/'Neptune4Pro_R5_FirstFit_PLA_020.curaprofile'

# All process values are explicit to avoid inheriting fast Elegoo intent values.
VALUES={
    'layer_height':0.2,'layer_height_0':0.2,'adaptive_layer_height_enabled':False,
    'line_width':0.42,'wall_line_width':0.42,'wall_line_width_0':0.42,
    'wall_line_width_x':0.42,'skin_line_width':0.42,'infill_line_width':0.42,
    'support_line_width':0.42,'support_interface_line_width':0.42,
    'support_roof_line_width':0.42,'skirt_brim_line_width':0.42,
    'initial_layer_line_width_factor':100,
    'wall_thickness':2.1,'wall_line_count':5,
    'top_bottom_thickness':1.2,'top_thickness':1.2,'bottom_thickness':1.2,
    'top_layers':6,'bottom_layers':6,'roofing_layer_count':0,
    'infill_sparse_density':35,'infill_pattern':'gyroid','infill_overlap':10,'skin_overlap':10,
    'infill_sparse_thickness':0.2,'infill_before_walls':False,
    'ironing_enabled':False,'magic_spiralize':False,
    'material_print_temperature':210,'material_print_temperature_layer_0':210,
    'material_initial_print_temperature':210,'material_final_print_temperature':210,
    'material_bed_temperature':60,'material_bed_temperature_layer_0':60,
    'material_flow':100,'material_flow_layer_0':100,'material_max_flowrate':8,
    'speed_print':60,'speed_wall':45,'speed_wall_0':35,'speed_wall_x':60,
    'speed_infill':80,'speed_topbottom':35,'speed_roofing':30,
    'speed_support':50,'speed_support_infill':50,'speed_support_interface':30,
    'speed_support_roof':30,'speed_support_bottom':30,
    'speed_layer_0':20,'speed_print_layer_0':20,'speed_travel_layer_0':60,
    'speed_travel':150,'skirt_brim_speed':20,'speed_slowdown_layers':3,
    'acceleration_enabled':True,'acceleration_print':1500,
    'acceleration_wall':1000,'acceleration_wall_0':800,'acceleration_wall_x':1200,
    'acceleration_topbottom':1000,'acceleration_roofing':1000,
    'acceleration_infill':1500,'acceleration_support':1000,
    'acceleration_support_infill':1000,'acceleration_support_interface':800,
    'acceleration_support_roof':800,'acceleration_support_bottom':800,
    'acceleration_travel':2500,'acceleration_layer_0':500,
    'acceleration_print_layer_0':500,'acceleration_travel_layer_0':1000,
    'acceleration_skirt_brim':500,'jerk_enabled':False,
    'retraction_enable':True,'retraction_amount':0.5,'retraction_speed':35,
    'retraction_retract_speed':35,'retraction_prime_speed':35,
    'retract_at_layer_change':False,'retraction_extra_prime_amount':0,
    'retraction_hop_enabled':False,'retraction_combing':'noskin',
    'cool_fan_enabled':True,'cool_fan_speed':100,'cool_fan_speed_min':100,
    'cool_fan_speed_max':100,'cool_fan_speed_0':0,'cool_fan_full_layer':3,
    'cool_fan_full_at_height':0.6,'cool_min_layer_time':10,'cool_min_speed':10,
    'cool_lift_head':False,
    'support_enable':True,'support_type':'everywhere','support_structure':'normal',
    'support_angle':50,'support_pattern':'zigzag','support_infill_rate':15,
    'support_interface_enable':True,'support_roof_enable':True,'support_bottom_enable':False,
    'support_interface_height':0.6,'support_roof_height':0.6,
    'support_interface_density':60,'support_roof_density':60,
    'support_interface_pattern':'lines','support_roof_pattern':'lines',
    'support_z_distance':0.2,'support_top_distance':0.2,'support_bottom_distance':0.2,
    'support_xy_distance':0.5,'support_xy_overrides_z':'z_overrides_xy',
    'support_brim_enable':True,'support_brim_width':3,'support_brim_line_count':8,
    'adhesion_type':'brim','brim_width':4,'brim_line_count':10,'brim_gap':0.1,'brim_location':'outside',
    'print_sequence':'all_at_once','prime_tower_enable':False,
    'meshfix_union_all':True,'meshfix_extensive_stitching':False,
    'meshfix_keep_open_polygons':False,
}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def flatten(nodes,result=None):
    result={} if result is None else result
    for key,value in nodes.items():
        result[key]=value
        flatten(value.get('children',{}),result)
    return result


def serialize(values,extruder):
    parser=configparser.ConfigParser(interpolation=None)
    parser['general']={'version':'4','name':NAME,'definition':'elegoo_neptune_4'}
    parser['metadata']={'type':'quality_changes','quality_type':'Elegoo_layer_020','setting_version':'27'}
    if extruder:parser['metadata'].update({'position':'0','intent_category':'default'})
    parser['values']={k:str(v) for k,v in values.items()}
    out=io.StringIO();parser.write(out);return out.getvalue()


def main():
    definition=CURA/'share/cura/resources/definitions/fdmprinter.def.json'
    schema=flatten(json.loads(definition.read_text(encoding='utf-8'))['settings'])
    missing=set(VALUES)-set(schema)
    assert not missing,missing
    global_values={};extruder_values={}
    for key,value in VALUES.items():
        field=schema[key];kind=field['type']
        if kind=='bool':assert type(value)==bool,key
        elif kind in ('int','float'):assert isinstance(value,(int,float)) and not isinstance(value,bool),key
        elif kind=='enum':assert value in field['options'],(key,value)
        else:raise ValueError((key,kind))
        target=extruder_values if field.get('settable_per_extruder',True) else global_values
        target[key]=value
    members={'hexquad_r5_first_fit_global':serialize(global_values,False),
             'hexquad_r5_first_fit_extruder_0':serialize(extruder_values,True)}
    HERE.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(FILE,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,value in members.items():archive.writestr(name,value)
    with zipfile.ZipFile(FILE) as archive:
        assert archive.testzip() is None
        merged={}
        for name in archive.namelist():
            raw=archive.read(name).decode('utf-8')
            parser=configparser.ConfigParser(interpolation=None);parser.read_string(raw)
            assert parser['general']['version']=='4'
            assert parser['general']['definition']=='elegoo_neptune_4'
            assert parser['metadata']['quality_type']=='Elegoo_layer_020'
            assert parser['metadata']['setting_version']=='27'
            merged.update(parser['values'])
        assert merged=={k:str(v) for k,v in VALUES.items()}
    machine=CURA/'share/cura/resources/definitions/elegoo_neptune_4pro.def.json'
    assert json.loads(machine.read_text())['metadata']['quality_definition']=='elegoo_neptune_4'
    quality=CURA/'share/cura/resources/quality/elegoo/neptune_4/elegoo_n4_layer_0.20.inst.cfg'
    parser=configparser.ConfigParser();parser.read(quality)
    assert parser['metadata']['quality_type']=='Elegoo_layer_020'
    # No start/end G-code, machine dimensions, offsets or firmware calibration in this profile.
    assert not any(k.startswith('machine_') or 'gcode' in k for k in VALUES)
    report={'status':'pass','profile':FILE.name,'profile_sha256':sha(FILE),
        'target':'Installed UltiMaker Cura 5.13, ELEGOO NEPTUNE 4 Pro, 0.4 mm nozzle, PLA',
        'settings_count':len(VALUES),'global_settings_count':len(global_values),
        'extruder_settings_count':len(extruder_values),'settings':VALUES,
        'checks':['ZIP CRC and both INI members parse correctly',
                  'Every setting exists and has a valid scalar type or enum in the installed schema',
                  'Machine quality definition, quality type and setting version match installed Cura',
                  'Process settings are separated by the installed per-extruder schema',
                  'No machine geometry, start/end G-code or firmware calibration overrides'],
        'schema_sha256':sha(definition),
        'limits':['Not imported into the live Cura UI during generation.',
                  'Physical printer, filament flow, adhesion and dimensional fit remain untested.',
                  'Cura material_max_flowrate is hidden in this build; explicit speeds keep nominal 0.42 x 0.20 mm deposition below 8 mm3/s.']}
    (HERE/'profile_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['status','profile','settings_count','global_settings_count','extruder_settings_count']}))


if __name__=='__main__':main()
