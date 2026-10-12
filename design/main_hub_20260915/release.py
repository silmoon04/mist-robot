"""Release the exact checked hub/spacer plate with clear assembly limitations."""
from pathlib import Path
import json,hashlib,zipfile,subprocess,sys,configparser,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(n):return json.loads((OUT/n).read_text())

def main():
    plate=load('Tonight_Print_Check.json');hub=load('Hub_Check.json');hardware=load('Mount_Fasteners.json');structure=load('Print_Structure_Check.json');spacer=load('Spacer_Dimensions.json');speed=load('Speed_Comparison.json')
    assert plate['status']==hub['status']==hardware['status']=='pass'
    assert sha(OUT/'Main_Hub_4Leg.stl')==plate['hub_stl_sha256']==hub['hub_stl_sha256']==hardware['hub_stl_sha256']==structure['stl_sha256']
    assert sha(OUT/'Spacer_8H_13OD_M3.stl')==plate['spacer_stl_sha256']==spacer['stl_sha256']
    assert sha(OUT/'Tonight_Hub_And_8_Spacers.stl')==plate['plate_stl_sha256']
    assert sha(OUT/'Tonight_Hub_And_8_Spacers.3mf')==plate['plate_3mf_sha256']
    assert len(plate['objects'])==9 and plate['deposition']['properties']['support']['mass_g']==0
    assert plate['engine']['motion_inside_build_envelope'] and plate['minimum_motion_edge_margin_mm']>1.5
    with zipfile.ZipFile(OUT/'Tonight_Hub_And_8_Spacers.3mf') as z:
        assert z.testzip() is None;doc=ET.fromstring(z.read('3D/3dmodel.model'));assert doc.attrib['unit']=='millimeter'
        assert len(doc.findall('.//{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}object'))==9
    with zipfile.ZipFile(OUT/'Neptune4Pro_Hub_PLA_028.curaprofile') as z:
        assert z.testzip() is None;values={}
        for n in z.namelist():
            c=configparser.ConfigParser(interpolation=None);c.read_string(z.read(n).decode());values.update(c['values'])
        assert values=={k:str(v) for k,v in plate['engine']['settings_overrides'].items()}
    minutes=round(plate['engine']['estimated_time_seconds']/60)
    text=f'''# Tonight: four-leg main hub and eight spacers

Print Tonight_Hub_And_8_Spacers.3mf using Neptune4Pro_Hub_PLA_028.curaprofile. The plate contains one centre hub and eight general M3 spacers, 8 mm tall by 13 mm outside diameter with a 3.4 mm bore. Those dimensions follow the direct reading of your request; verify the filename dimensions before slicing if you intended the 13 mm dimension to mean height. They are not replacements for the 11.6 mm long, OD5.8 yaw spacers or the integral annular pitch stand-offs.

The hub is the robot's four-leg centre deck, not the earlier rectangular bench fixture. It provides all four saddle mounting patterns now, even if you have only two complete legs. Keep the plate for the robot build. It is the first physical hub revision, so full-body load tests and later cover/electronics work can still lead to changes.

## Print settings and time

The complete single-bed estimate is {minutes//60} h {minutes%60:02d} min and {plate['deposition']['total_deposited_mass_g']:.1f} g PLA. The hub measures approximately 178.4 x206 x12 mm, comprising a 6 mm deck with upward ribs. Put its flat underside on the bed and keep the ribs upward. Spacers stand on their flat annular ends. Supports are OFF for the whole plate. All functional holes run vertically, and the checked geometry has no downward overhang faces above the bed.

Use your existing Neptune 4 Pro printer definition and 0.4 mm nozzle. Import the profile through Preferences > Profiles > Import, then open the 3MF as models and select that profile. This 3MF carries geometry and placement only; it does not automatically activate the profile. Keep 100 percent scale and the supplied orientations. A combined STL and individual part STLs are included as alternatives.

The profile uses 0.28 mm layers, five walls, 25 percent gyroid infill, five top/bottom layers, 210 C nozzle, 60 C bed and a 2 mm outside brim. Outer walls and top/bottom surfaces are increased from40 to46 mm/s, a15 percent increase. Travel rises from150 to175 mm/s. Inner walls and infill remain65 mm/s, because increasing these further would exceed the conservative flow envelope used on the previous prints. First-layer speeds, bridge speeds, acceleration and cooling are unchanged.

An actual hub-only A/B slice changed from7 h34 min to7 h16 min, approximately {speed['time_reduction_percent']:.1f} percent less total time. A15 percent increase in selected speeds does not produce a15 percent reduction for the entire job. The complete hub-plus-spacer slice peaks at {plate['deposition']['properties']['model']['peak_nominal_deposition_flow_mm3_s']:.2f} mm3/s commanded deposition flow, below8. The lowest XY travel margin to the nominal bed boundary is {plate['minimum_motion_edge_margin_mm']:.2f} mm. Firmware, heating and filament behaviour can change the elapsed time and finish. No printer start/end G-code or calibration values are overridden.

## Attach the legs

Each leg's stationary yaw servo sits in its separate saddle. The saddle's four feet bolt onto the hub; the moving coxa bracket does not bolt directly to the hub. There are four identical 38 x40 mm fixing patterns, with yaw shafts positioned75 mm from the hub centre at45, -45,135 and-135 degrees. The shaft end of each servo faces outward and its case tail points inward toward the hub centre. Retain the existing eight-part leg assemblies without changing their geometry.

For each attached leg, use four M3x12 screws, four M3 nuts and four flat washers. Insert the screws from the saddle-foot side, with heads directly against the printed feet. Put one washer and one nut underneath the hub. Omit upper washers: the approximately7.7 mm washers would touch the servo clamp. For your two legs this is eight screws, eight nuts and eight washers; four legs require16 of each.

The nominal stack is6 mm hub +3 mm saddle foot +0.5 mm flat washer +2.2 mm nut. A12 mm screw extends approximately0.3 mm beyond that nut, so actual thickness matters. Before tightening or loading, confirm that every screw passes through the full nut. The nut measurement is approximate and washer thickness is still unconfirmed. Do not substitute longer M3x18 screws blindly: their tips can enter the rotating lower-arm region.

The eight large spacers on tonight's plate are general-purpose requested parts. Do not insert them between the saddle and this hub: that would change the checked mounting height and screw stack. The four narrow yaw spacers per leg remain the earlier nominal11.6 mm set.

## What is included and what remains

The deck preserves the existing leg-hole patterns and the four cover fixing locations, but has wider openings for the newer coxa motion and lower hardware. It adds full-width material beneath the outer feet and a central cross of upward ribs. Cable/strap slots remain available. The old battery tray mounting pattern conflicted with the enlarged openings, so that tray is not directly compatible with this hub. Four new central mounting holes are reserved for a later tray; the old cover and electronics mounts also need their vertical clearances adapted to the6 mm ribbed deck. Do not print the older cover or battery tray on the assumption that it has already been fitted to this version.

The yaw saddles, caps, servos, narrow yaw spacers and completed legs are not on this plate. Some may already be in your previous prints. In particular, the older test saddle needs its actual nut engagement checked before loaded reuse.

The two-leg assembly is not a self-balancing robot yet. Support the hub during assembly and initial powered movement. Full-body payload, walking balance and contact forces remain to be qualified.

## Verification

The hub is one valid solid and one closed, consistently wound mesh. All four leg mounting patterns and their material around the screw holes were checked. Exact hub/leg intersection checks passed for140 sampled leg poses across the four positions, including yaw endpoints to60 degrees and representative pitch guard poses. The mounting screw, nut and washer envelopes also passed. The plate's nine meshes, profile import structure, actual no-support slicing and printer travel envelope passed.

These checks establish sampled hub clearance, not unrestricted independent motion of all four legs. Inter-leg collision, full gait dynamics and physical strength are not established. A simple section screen with assumed PLA strength passed its selected1 Nm comparison case, but is not FEA or a guarantee against screw preload, fatigue, thin-tab stress or impact. Commission the printed assembly under restraint before loading it.

Main_Hub_And_Spacers.f3d is the new Fusion print-parts document. Main_Hub_4Leg.step and Spacer_8H_13OD_M3.step are editable solids. Hub_With_Four_Legs.step shows the complete mechanical layout at a neutral pose; the legs in it are for context and are not additional objects in the print plate.
'''
    # Keep units legible in authored prose without changing CAD identifiers.
    import re
    text=re.sub(r'(?<=[A-Za-z])(?=\d)', ' ',text) if False else text
    for a,b in [('from40','from 40'),('to46','to 46'),('a15','a 15'),('from150','from 150'),('to175','to 175'),('remain65','remain 65'),('below8','below 8'),('from7','from 7'),('h34','h 34'),('to7','to 7'),('h16','h 16'),('approximately7.7','approximately 7.7'),('require16','require 16'),('is6','is 6'),('+3','+ 3'),('+0.5','+ 0.5'),('+2.2','+ 2.2'),('A12','A 12'),('approximately0.3','approximately 0.3'),('nominal11.6','nominal 11.6'),('the6','the 6'),('for140','for 140'),('to60','to 60'),('selected1','selected 1'),('positioned75','positioned 75'),('at45','at 45'),('and-135','and -135')]:text=text.replace(a,b)
    (OUT/'PRINT_TONIGHT.md').write_text(text);(OUT/'PRINT_TONIGHT.txt').write_text(text)
    receipt={'status':'pass for first physical hub assembly and restrained testing','plate_objects':9,'spacer_quantity':8,'spacer_height_mm':8,'spacer_OD_mm':13,'spacer_bore_mm':3.4,
        'time_seconds':plate['engine']['estimated_time_seconds'],'PLA_g':plate['deposition']['total_deposited_mass_g'],'support_g':0,
        'source_hashes':{p.name:sha(p) for p in ROOT.glob('*.py')},'outputs':{n:sha(OUT/n) for n in ['Main_Hub_4Leg.stl','Spacer_8H_13OD_M3.stl','Tonight_Hub_And_8_Spacers.3mf','Tonight_Hub_And_8_Spacers.stl','Neptune4Pro_Hub_PLA_028.curaprofile','Hub_Check.json','Mount_Fasteners.json','Print_Structure_Check.json','Tonight_Print_Check.json']}}
    (OUT/'Release_Check.json').write_text(json.dumps(receipt,indent=2))
    paths=sorted([*OUT.glob('*.json'),*OUT.glob('*.txt')])
    subprocess.run([sys.executable,'<LOCAL_HOME>/.codex/hooks/output_punctuation.py','register','--fix',*map(str,paths)],check=True)
    assert all(sha(OUT/n)==value for n,value in receipt['outputs'].items()),'Punctuation edits changed a hash-bound output; regenerate dependent reports'
    archive=ROOT/'Tonight_Main_Hub_And_8_Spacers.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in OUT.iterdir():
            if p.is_file():z.write(p,p.name)
        for p in ROOT.glob('*.py'):z.write(p,'source/'+p.name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for p in OUT.iterdir():
            if p.is_file():assert hashlib.sha256(z.read(p.name)).hexdigest()==sha(p)
    print('READY',archive,'minutes',minutes,'grams',receipt['PLA_g'],'SHA256',sha(archive))

if __name__=='__main__':main()
