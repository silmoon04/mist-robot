"""Verify and package the bounded DFM update."""
from pathlib import Path
import json,hashlib,shutil,zipfile,configparser,subprocess,sys
from types import SimpleNamespace
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from matplotlib.collections import LineCollection
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output';PRINT=ROOT/'print';OLD=ROOT.parent/'overnight_leg_20260914/print'
sys.path.insert(0,str(ROOT.parent/'hexapod_phone_quad_r5_20260912/review'))
from render_preview import draw_mesh,camera_basis
from check_supports import segments
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    check=json.loads((OUT/'DFM_Check.json').read_text());batch=json.loads((PRINT/'Batch_Check.json').read_text());prior=json.loads((OLD/'Batch_Check.json').read_text())
    assert check['status']=='pass' and batch['R7_manifest_sha256']==sha(OUT/'manifest.json')==check['manifest_sha256']
    assert sha(PRINT/'R7_DFM_Overnight.stl')==batch['plate_stl_sha256']
    assert not any(c['support_midpoints_inside'] for c in batch['support_checks'])
    profile=PRINT/'DFM_PLA_028.curaprofile';shutil.copy2(PRINT/'Tree_Undersides_R7_PLA_028.curaprofile',profile)
    merged={}
    with zipfile.ZipFile(profile) as z:
        assert z.testzip() is None
        for n in z.namelist():
            c=configparser.ConfigParser(interpolation=None);c.read_string(z.read(n).decode());merged.update(c['values'])
    assert merged=={k:str(v) for k,v in batch['engine']['settings_overrides'].items()}
    figures=[]
    for name in ['coxa_upper_and_hip_saddle','coxa_lower_auxiliary_arm']:
        mesh=trimesh.load_mesh(OUT/'print_stl'/(name+'.stl'));assert mesh.is_watertight and mesh.is_winding_consistent
        data=SimpleNamespace(triangles=mesh.triangles,normals=mesh.face_normals,colors=np.tile(to_rgb('#38949a'),(len(mesh.faces),1)))
        figures.append(data)
    fig,axes=plt.subplots(1,2,figsize=(12,6),facecolor='#f3f4f0')
    for ax,data,title in zip(axes,figures,['Upright coxa: centred octagon and small foot','Matching lower arm: centred octagon']):
        draw_mesh(ax,data,camera_basis(25,-65));ax.axis('off');ax.set_aspect('equal');ax.set_title(title,fontsize=13);ax.set_facecolor('#f3f4f0')
    fig.suptitle('Centred flanges with a separate print foot',fontsize=18)
    fig.savefig(PRINT/'Changed_Parts.png',dpi=150,bbox_inches='tight');plt.close(fig)
    seg=segments(ROOT/'analysis/overnight_leg.analysis_only.gcode.gz');fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax,idx in zip(axes,[[0,1],[0,2]]):
        for support in (False,True):
            items=[s for s in seg if s[2].startswith('SUPPORT')==support and s[2] not in ('SKIRT','BRIM')]
            lines=np.array([[a[idx],b[idx]] for a,b,_,_ in items[::1 if support else 20]])
            ax.add_collection(LineCollection(lines,colors='#c98730' if support else '#38949a',linewidths=.4 if support else .2,alpha=.8 if support else .2))
        ax.autoscale();ax.set_aspect('equal');ax.set_title('Actual sliced model (teal) and support (amber)');ax.set_xlabel('X mm');ax.set_ylabel('Y mm' if idx==[0,1] else 'Z mm')
    fig.tight_layout();fig.savefig(PRINT/'Remaining_Support.png',dpi=150);plt.close(fig)
    before=prior['deposition']['properties']['support']['mass_g'];after=batch['deposition']['properties']['support']['mass_g'];minutes=round(batch['engine']['estimated_time_seconds']/60)
    text=f'''# DFM update for the overnight leg plate

This changes two coxa pieces and retains the other six overnight parts. No bench base, duplicate yaw cap or duplicate yaw spacers are added.

## Changes

Both flanges now use a regular octagon centred on the shaft, measuring 28 mm across opposite flats. The octagon fully encloses the original round flange, so no mixed curved/polygon outline remains. The upright flange has a separate small trapezoidal print foot with 45-degree sides. A narrow bottom rail and local webs support the post and floating saddle lip. These are permanent part features, not breakaway support.

The horizontal horn screw passages and post holes receive pointed 45-degree roofs. The post nut recesses have sloping roofs while retaining their nut seating flats. The 7 mm central circular clearance is preserved inside a hexagonal opening: its flat ceiling is a short approximately 4 mm bridge. The matching lower arm receives the same centred flange outline and fixing-centre pattern. Its washer counterbores remain circular and face upward when printed. Those large recessed washer seats overlap the central access opening at the outer face, as before; the overlap is symmetric and is required to retain the existing 7.7 mm washer fit and screw pattern. The central hexagon itself remains regular and centred.

The existing roofed servo-clamp holes remain. Flat-printed mating caps and cheeks retain their round vertical holes because those already print without support. Their hole centres and fastener interfaces still match. Making vertical bearing or washer seats hexagonal would not improve their printability.

## Measured result

Support material: {before:.2f} g before, {after:.2f} g after, a {100*(1-after/before):.0f}% reduction. Total PLA is {batch['deposition']['total_deposited_mass_g']:.1f} g. Cura estimates {minutes//60} h {minutes%60:02d} min, versus approximately 9 h 50 min before. This is an improvement to the coxa's printed features and hole cleanup, not a meaningful speed saving. The permanent webs add material.

The remaining supports are still necessary for the exposed undersides, especially the raised straight tibia. Eliminating those entirely requires changing the structural layout or splitting another part, which is beyond this quick revision. Do not turn all supports off.

## Print

Open R7_DFM_Overnight.3mf as models and import/select DFM_PLA_028.curaprofile in Cura. Keep the existing Neptune 4 Pro machine, 0.4 mm nozzle, 100 percent scale and the supplied orientations. This is a geometry plate, not a saved Cura project, so it does not select the profile automatically. The combined STL is a fallback.

The profile retains 0.28 mm layers, five walls, 25 percent gyroid, slow overhang walls and 15 to 20 mm/s bridges. It uses build-plate tree support with 4.3 mm XY clearance to keep tree tips out of the central hexagon, and a 0.56 mm top gap. The greater clearance leaves more short unsupported edge span and may roughen undersides; inspect the supplied toolpath preview against Cura. The actual updated slice retains broad underside support. Do not substitute the older profile, which placed tips inside that opening.

## Checks and compatibility

All eight meshes are closed and consistently wound. Source and profile hashes match the slice. The new material was checked against all assembly parts at the 39 previously verified poses, with no intersections. Original screw and washer clearance envelopes remain open; the lower post nut's insertion route was checked independently. The updated slice contains no sampled support centre lines inside the checked screw bores, nut entries or central clearance opening. These checks do not prove actual bridge quality, bead-edge clearance or support removal force.

The two updated coxa parts belong together. All other R7 leg pieces, screw sizes and motion limits remain unchanged. Use the included R7 assembly guide, including its washer-thickness assumptions. Editable STEP files for the changed pieces and the assembled CAD are included. The earlier Fusion archive still shows R7 before this local DFM update; use the new STEP for the revised geometry.

The earlier full-leg load limitation remains: begin with restrained unloaded articulation. This update does not certify the bridges for full-body loading or two-foot balance.
'''
    (PRINT/'README.md').write_text(text);(PRINT/'README.txt').write_text(text)
    shutil.copy2(OUT/'DFM_Check.json',PRINT/'DFM_Check.json')
    shutil.copy2(ROOT.parent/'single_leg_r7_wide_joints_20260914/output/ASSEMBLY.md',PRINT/'ASSEMBLY.md')
    shutil.copy2(OUT/'Assembly_DFM.step',PRINT/'Assembly_DFM.step')
    for name in ['coxa_upper_and_hip_saddle','coxa_lower_auxiliary_arm']:
        shutil.copy2(OUT/'parts_step'/(name+'.step'),PRINT/(name+'.step'))
    paths=[PRINT/'Batch_Check.json',PRINT/'DFM_Check.json',PRINT/'README.txt']
    subprocess.run([sys.executable,'<LOCAL_HOME>/.codex/hooks/output_punctuation.py','register','--fix',*map(str,paths)],check=True)
    archive=ROOT/'DFM_Centred_Overnight_Print_Set.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for f in PRINT.iterdir():
            if f.is_file() and f.name!='Tree_Undersides_R7_PLA_028.curaprofile':z.write(f,f.name)
        z.write(ROOT/'build_dfm.py','source/build_dfm.py')
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    print('READY',archive,'support grams',after,'minutes',minutes)

if __name__=='__main__':main()
