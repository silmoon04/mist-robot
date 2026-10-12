"""Pack one longer run of unchanged R7 robot parts, excluding test fixtures."""
from pathlib import Path
import sys,json,math,random,hashlib,gzip,shutil,importlib.util
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
ROOT=Path(__file__).resolve().parent;R7=ROOT;OUT=ROOT/'print';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(R7));import prepare_prints as printing
from check_supports import segments,regions as existing_regions,rot
def regions(p):
    result=existing_regions(p)
    if p['name'] in ('coxa_upper_and_hip_saddle','coxa_lower_auxiliary_arm'):
        z0,z1=(4.5,8.5) if 'upper' in p['name'] else (-53,-44)
        for x,y,r,label in [(0,0,2.4,'central access'),(7,0,1.2,'horn screw'),(-7,0,1.2,'horn screw'),(0,7,1.2,'horn screw'),(0,-7,1.2,'horn screw')]:
            result.append((label,np.array([x-r,y-r,z0]),np.array([x+r,y+r,z1]),np.eye(4)))
    return result
NAMES=['coxa_upper_and_hip_saddle','coxa_lower_auxiliary_arm','femur_main_and_knee_saddle','femur_auxiliary_cheek','tibia_curved_main_and_foot','tibia_auxiliary_cheek','case_cap_hip','case_cap_knee']
GAP=12.;BIN=210.

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def pack(sizes):
    rng=random.Random(716);best=None
    for attempt in range(1500):
        order=list(sizes)
        if attempt==0:order.sort(key=lambda n:-np.prod(sizes[n]))
        elif attempt==1:order.sort(key=lambda n:-max(sizes[n]))
        else:rng.shuffle(order)
        free=[(0.,0.,BIN,BIN)];placed={}
        for name in order:
            choices=[]
            for turn in (False,True):
                w,h=sizes[name][::-1] if turn else sizes[name];w+=GAP;h+=GAP
                for x,y,fw,fh in free:
                    if w<=fw+1e-6 and h<=fh+1e-6:
                        score=(min(fw-w,fh-h),fw*fh-w*h) if attempt%2 else (fw*fh-w*h,min(fw-w,fh-h))
                        choices.append((score,x,y,w,h,turn))
            if not choices:break
            _,x,y,w,h,turn=min(choices);placed[name]=(x,y,w-GAP,h-GAP,turn)
            split=[]
            for fx,fy,fw,fh in free:
                if x>=fx+fw or x+w<=fx or y>=fy+fh or y+h<=fy:split.append((fx,fy,fw,fh));continue
                if x>fx:split.append((fx,fy,x-fx,fh))
                if x+w<fx+fw:split.append((x+w,fy,fx+fw-x-w,fh))
                if y>fy:split.append((fx,fy,fw,y-fy))
                if y+h<fy+fh:split.append((fx,y+h,fw,fy+fh-y-h))
            free=[]
            for i,a in enumerate(split):
                if a[2]<=0 or a[3]<=0:continue
                if any(i!=j and a[0]>=b[0]-1e-7 and a[1]>=b[1]-1e-7 and a[0]+a[2]<=b[0]+b[2]+1e-7 and a[1]+a[3]<=b[1]+b[3]+1e-7 and (a!=b or i>j) for j,b in enumerate(split)):continue
                free.append(a)
        if len(placed)==len(sizes):
            width=max(x+w for x,y,w,h,t in placed.values());height=max(y+h for x,y,w,h,t in placed.values());score=width*height
            if best is None or score<best[0]:best=(score,placed)
    if best is None:raise RuntimeError('Eight parts do not fit with the required spacing')
    return best[1]

def main():
    manifest=json.loads((R7/'output/manifest.json').read_text());by={p['name']:p for p in manifest['parts']}
    meshes={n:trimesh.load_mesh(R7/'output'/by[n]['print_stl'],process=True) for n in NAMES}
    for n,m in meshes.items():assert m.is_watertight and m.is_winding_consistent and m.volume>0 and sha(R7/'output'/by[n]['print_stl'])==by[n]['stl_sha256']
    layout=pack({n:m.extents[:2] for n,m in meshes.items()});placed=[];rows=[]
    for n,m in meshes.items():
        x,y,w,h,turn=layout[n];t=np.eye(4);t[:3,:3]=rot([0,0,90 if turn else 0]);v=m.vertices@t[:3,:3].T;t[:3,3]=[x,y,0]-v.min(axis=0)
        m.apply_transform(t);placed.append((n,m));rows.append({'name':n,'source_sha256':by[n]['stl_sha256'],'source_print_to_plate':t.tolist(),'turn_about_print_z_deg':90 if turn else 0})
    combined=trimesh.util.concatenate([m for n,m in placed]);shift=np.r_[112.5-combined.bounds[:,:2].mean(axis=0),0]
    for (n,m),row in zip(placed,rows):m.apply_translation(shift);t=np.array(row['source_print_to_plate']);t[:3,3]+=shift;row['source_print_to_plate']=t.tolist()
    combined=trimesh.util.concatenate([m for n,m in placed]);stl=OUT/'R7_DFM_Overnight.stl';combined.export(stl)
    printing.three_mf(stl.with_suffix('.3mf'),placed)
    for i,(n,a) in enumerate(placed):
        for nn,b in placed[i+1:]:assert any(a.bounds[1,k]+GAP-.001<=b.bounds[0,k] or b.bounds[1,k]+GAP-.001<=a.bounds[0,k] for k in (0,1)),(n,nn)
    settings=printing.profile(True);settings['support_xy_distance']=4.3
    engine=printing.slice_one(stl,ROOT/'analysis','overnight_leg',settings)
    raw=Path(engine['raw_temporary_path']);code=raw.read_text();deposition=printing.parse_gcode(code,engine['gcode_to_source_transform'],layer_height_mm=.28)
    disabled=ROOT/'analysis/overnight_leg.analysis_only.gcode.gz'
    with gzip.open(disabled,'wt') as f:f.writelines(line if line.startswith(';') else '; DISABLED '+line for line in code.splitlines(keepends=True))
    raw.unlink();engine['raw_file_disposition']='Consumed, disabled, compressed and raw temporary file removed.'
    checks=[];seg=segments(disabled);supports=np.array([(a+b)/2 for a,b,kind,_ in seg if kind.startswith('SUPPORT')]).reshape((-1,3));supports[:,2]-=.14
    inv=np.array(engine['gcode_to_source_transform']);supports=supports@inv[:3,:3].T+inv[:3,3]
    for row in rows:
        p=by[row['name']];inv=np.linalg.inv(np.array(row['source_print_to_plate']));points=supports@inv[:3,:3].T+inv[:3,3]
        asm=trimesh.load_mesh(R7/'output'/p['assembly_stl']);r=rot(p['print_rotation']);original=trimesh.load_mesh(R7/'output'/p['print_stl'])
        offset=original.bounds[0]-(asm.vertices@r.T).min(axis=0);points=(points-offset)@r
        for tag,lo,hi,pitch in regions(p):
            q=(points-pitch[:3,3])@pitch[:3,:3];mask=np.all((q>lo)&(q<hi),axis=1);external=0
            if tag.startswith('post nut entry'):
                scallop=(q[:,0]-43.085)**2+(q[:,1]+13)**2<16;external=int((mask&scallop).sum());mask&=~scallop
            checks.append({'part':p['name'],'opening':tag,'support_midpoints_inside':int(mask.sum()),'external_scallop_midpoints':external})
    assert not any(r['support_midpoints_inside'] for r in checks),checks
    assert engine['motion_inside_build_envelope'] and deposition['unclassified_deposition_is_zero']
    lower,upper=np.array(engine['motion_bounds_mm'])
    assert min(lower[:2].min(),(225-upper[:2]).min())>=2,'Leave at least 2 mm to the nominal bed boundary'
    profile=R7/'output/Tree_Undersides_R7_PLA_028.curaprofile';shutil.copy2(profile,OUT/profile.name)
    import zipfile,configparser,io
    target=OUT/profile.name
    with zipfile.ZipFile(target) as z:members={n:z.read(n) for n in z.namelist()}
    for n,payload in members.items():
        if 'extruder' in n:
            c=configparser.ConfigParser(interpolation=None);c.read_string(payload.decode());c['values']['support_xy_distance']='4.3';buffer=io.StringIO();c.write(buffer);members[n]=buffer.getvalue().encode()
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for n,payload in members.items():z.writestr(n,payload)
    fig,ax=plt.subplots(figsize=(9,9),facecolor='#f3f4f0');ax.set_facecolor('#f3f4f0')
    legend=[]
    for index,(n,m) in enumerate(placed,1):
        ax.add_collection(PolyCollection(m.triangles[:,:,:2],facecolors='#55999c',edgecolors='none',alpha=.15))
        centre=m.bounds[:,:2].mean(axis=0);ax.text(*centre,str(index),ha='center',va='center',fontsize=16,color='#172f33',bbox={'facecolor':'white','alpha':.85,'edgecolor':'none'})
        legend.append(f'{index}. '+n.replace('_',' ').replace('tibia curved main and foot','straight tibia and foot'))
    ax.set_xlim(0,225);ax.set_ylim(0,225);ax.set_aspect('equal');ax.set_xlabel('Bed X (mm)');ax.set_ylabel('Bed Y (mm)');ax.set_title('DFM update: self-supporting coxa features',fontsize=17)
    fig.text(.12,.02,'\n'.join(legend),fontsize=10);fig.subplots_adjust(bottom=.24);fig.savefig(OUT/'Plate_Map.png',dpi=140);plt.close(fig)
    result={'status':'pass for printing the existing R7 prototype geometry','R7_manifest_sha256':sha(R7/'output/manifest.json'),'parts':rows,'part_count':len(rows),
        'plate_stl_sha256':sha(stl),'plate_3mf_sha256':sha(stl.with_suffix('.3mf')),'profile_sha256':sha(OUT/profile.name),'minimum_model_bbox_spacing_mm':GAP,
        'engine':engine,'deposition':deposition,'support_checks':checks,
        'excluded':['temporary bench base','existing matching flat cap, assigned to yaw servo','previous nominal yaw spacers','yaw saddle pending existing clamp fastener engagement check'],
        'limits':['R7 remains a prototype with physical load qualification outstanding.','No promise of unattended reliability.','Support midpoint checks are not a proof of bead-edge clearance or removal force.','The historical clamp body has different nut-seat depth; do not approve it from case fit alone.']}
    (OUT/'Batch_Check.json').write_text(json.dumps(result,indent=2));print('HOURS',engine['estimated_time_seconds']/3600,'GRAMS',deposition['total_deposited_mass_g'],flush=True)

if __name__=='__main__':main()
