"""Pack the complete third leg and compare two Cura-sliced processes."""
from pathlib import Path
import sys,json,zipfile,hashlib,concurrent.futures
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'print';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT));import compare_speed as c
sys.path.insert(0,str(c.OLD));import prepare_batch as packing
packing.GAP=6

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def profile(s,name):
    pt=c.p.pt;schema=pt.flatten(json.loads((pt.CURA/'share/cura/resources/definitions/fdmprinter.def.json').read_text())['settings']);gv={};ev={}
    for k,v in s.items():
        if k.startswith('machine_'):continue
        f=schema[k]
        if f['type']=='enum':assert v in f['options'],(k,v)
        (ev if f.get('settable_per_extruder',True) else gv)[k]=v
    pt.NAME=name.replace('_',' ')
    dest=OUT/(name+'.curaprofile')
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('third_leg_global',pt.serialize(gv,False));z.writestr('third_leg_extruder_0',pt.serialize(ev,True))
    return dest.name

def main():
    manifest=json.loads((ROOT/'output/manifest.json').read_text());by={p['name']:p for p in manifest['parts']}
    meshes={n:trimesh.load_mesh(ROOT/'output'/p['print_stl']) for n,p in by.items()}
    for n,m in meshes.items():assert m.is_watertight and m.volume>0 and m.is_winding_consistent,n
    layout=packing.pack({n:m.extents[:2] for n,m in meshes.items()});placed=[];rows=[]
    support=trimesh.load_mesh(ROOT/'output/Knee_Saddle_Removable_Combs.stl')
    for n,m in meshes.items():
        x,y,w,h,turn=layout[n];t=np.eye(4);t[:3,:3]=packing.rot([0,0,90 if turn else 0]);v=m.vertices@t[:3,:3].T;t[:3,3]=[x,y,0]-v.min(0)
        m.apply_transform(t);placed.append((n,m));rows.append({'name':n,'source_print_to_plate':t.tolist(),'source_sha256':sha(ROOT/'output'/by[n]['print_stl'])})
        if n=='femur_main_and_knee_saddle':support.apply_transform(t)
    whole=trimesh.util.concatenate([m for n,m in placed]);shift=np.r_[112.5-whole.bounds[:,:2].mean(0),0]
    for (n,m),r in zip(placed,rows):
        m.apply_translation(shift);t=np.array(r['source_print_to_plate']);t[:3,3]+=shift;r['source_print_to_plate']=t.tolist()
    support.apply_translation(shift)
    for i,(n,a) in enumerate(placed):
        for nn,b in placed[i+1:]:assert any(a.bounds[1,k]+5.999<=b.bounds[0,k] or b.bounds[1,k]+5.999<=a.bounds[0,k] for k in (0,1)),(n,nn)
    placed.append(('REMOVE_after_print_knee_saddle_support',support))
    plate=trimesh.util.concatenate([m for n,m in placed]);stl=OUT/'Third_Leg_Complete_With_Supports.stl';plate.export(stl);c.p.three_mf(stl.with_suffix('.3mf'),placed)
    # The STL contains one arranged plate, so import cannot drop individual
    # supports or separate a model from its matching removable comb.
    s=c.settings();s.update(layer_height=.3,infill_sparse_thickness=.3,top_bottom_thickness=1.5,top_thickness=1.5,bottom_thickness=1.5,
        speed_wall_x=85,speed_infill=85,speed_topbottom=60,support_top_distance=.6,support_z_distance=.6,support_interface_height=.6,
        support_roof_height=.6,support_bottom_distance=.3,support_brim_enable=False,skirt_gap=2)
    limits=dict(machine_max_acceleration_x=20000,machine_max_acceleration_y=20000,machine_max_acceleration_e=5000,machine_acceleration=5000)
    fast_name=profile(s,'Neptune4Pro_Third_Leg_Faster_030')
    fallback=c.settings(False);fallback.update(adhesion_type='skirt',skirt_gap=2,skirt_line_count=2,support_brim_enable=False)
    fallback_name=profile(fallback,'Neptune4Pro_Third_Leg_Familiar_028')
    jobs=[('third_leg_fast',s),('third_leg_familiar',fallback)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(c.run,n,stl,dict(v,**limits)) for n,v in jobs]
        results=[f.result() for f in futures]
    for r in results:
        assert r['engine']['motion_inside_build_envelope'] and r['deposition']['unclassified_deposition_is_zero']
        bounds=np.array(r['engine']['motion_bounds_mm']);assert bounds[0,:2].min()>1 and (225-bounds[1,:2]).min()>1
    fig,ax=plt.subplots(figsize=(10,10),facecolor='#f4f5f2');ax.set_facecolor('#f4f5f2');legend=[]
    colors=['#49a9b9','#88b74d','#bd80c9','#eba85c','#70a3df']
    for i,(n,m) in enumerate(placed,1):
        support_part=n.startswith('REMOVE');col='#ee754d' if support_part else colors[(i-1)%len(colors)]
        ax.add_collection(PolyCollection(m.triangles[:,:,:2],facecolors=col,edgecolors='none',alpha=.4))
        if not support_part:
            ax.text(*m.bounds[:,:2].mean(0),str(i),ha='center',va='center',fontsize=11,bbox={'facecolor':'white','alpha':.8,'edgecolor':'none'})
            label=n.replace('_',' ').replace('tibia curved main and foot','straight tibia and foot')
            legend.append(f'{i}. {label}')
    ax.set_xlim(0,225);ax.set_ylim(0,225);ax.set_aspect('equal');ax.set_xlabel('Bed X, mm');ax.set_ylabel('Bed Y, mm');ax.set_title('Third leg: 14 parts on one bed\nOrange comb under the knee saddle is removed after printing')
    fig.text(.1,.02,'\n'.join(legend[:7]),fontsize=9);fig.text(.55,.02,'\n'.join(legend[7:]),fontsize=9);fig.subplots_adjust(bottom=.22);fig.savefig(OUT/'Plate_Map.png',dpi=150);plt.close(fig)
    report={'part_count':14,'removable_support_groups':1,'parts':rows,'model_bbox_gap_mm':6,'bed_size_mm':[225,225],
      'plate_stl_sha256':sha(stl),'plate_3mf_sha256':sha(stl.with_suffix('.3mf')),
      'profiles':[{'file':fast_name,'sha256':sha(OUT/fast_name),'result':results[0]},{'file':fallback_name,'sha256':sha(OUT/fallback_name),'result':results[1]}],
      'time_saved_percent':100*(1-results[0]['engine']['estimated_time_seconds']/results[1]['engine']['estimated_time_seconds']),
      'estimate_basis':'CuraEngine 5.13.0 using acceleration limits from the installed Neptune 4 Pro definition, unchanged moderate requested accelerations, 225 mm conservative bed envelope. Actual printer configuration was not read.',
      'limits':['11 mm3/s flow is a candidate, not a physically validated hotend limit.','0.30 mm layers are new for this part set; the familiar profile retains 0.28 mm.','Assembly and insert retention require physical confirmation.']}
    (OUT/'Print_Check.json').write_text(json.dumps(report,indent=2));print('PLATE_OK',report['time_saved_percent'],flush=True)

if __name__=='__main__':main()

