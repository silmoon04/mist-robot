"""Inspect actual roof meshes and toolpath speeds; render the nut-pocket sections."""
from pathlib import Path
import gzip
import json
import hashlib
import math
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from slice_and_check import feed_samples

HERE=Path(__file__).resolve().parent
DESIGN=HERE.parent/'hexapod_phone_quad_r5_20260912'


def main():
    p=HERE/'second_fit_validation.json';d=json.loads(p.read_text(encoding='utf-8'))
    audit=[]
    for part in d['parts']:
        mesh=trimesh.load_mesh(HERE/part['stl'],process=True)
        mask=(mesh.face_normals[:,2]<-math.cos(math.pi/4)-1e-5)&(mesh.triangles[:,:,2].max(axis=1)>.001)
        area=float(mesh.area_faces[mask].sum())
        assert area<.001
        audit.append({'part':part['name'],'non_bed_downward_area_steeper_than45_degrees_mm2':area,
                      'method':'Triangle normal test in the actual supplied print orientation. Bed faces excluded.'})
    raw=gzip.decompress((HERE/'analysis/second_full_clamp.ANALYSIS_ONLY.gcode.gz').read_bytes()).decode()
    text='\n'.join(line.removeprefix('; DISABLED| ') for line in raw.splitlines())
    wall=feed_samples(text)
    run=json.loads((HERE/'analysis/slice_run.json').read_text(encoding='utf-8'))
    transform=np.array(run['gcode_to_source_transform'])
    for row in wall:row['source_mid']=(transform@np.r_[row['mid'],1])[:3]
    # The packed saddle is the left object, translated only in XY.
    xshift=d['plate']['bounds_mm'][0][0]+43.115
    yshift=d['plate']['bounds_mm'][0][1]+26
    roofs=[]
    for index,roof in enumerate(d['bolt_roofs'],1):
        x=roof['x_mm']+xshift;z=roof['z_mm']+32
        rows=[r for r in wall if abs(r['source_mid'][0]-x)<3.0
              and yshift-16.5<r['source_mid'][1]<yshift-13.6
              and z+1.1<r['source_mid'][2]<roof['nut_roof_apex_z_mm']+32+.3]
        slow=[r for r in rows if r['speed_mm_s']<=20.01]
        assert slow,(index,rows[:3])
        roofs.append({'bolt':index,'wall_segments_in_nut_roof_region':len(rows),
            'segments_at_or_below20_mm_s':len(slow),
            'minimum_speed_mm_s':min(r['speed_mm_s'] for r in rows),
            'maximum_speed_mm_s':max(r['speed_mm_s'] for r in rows),
            'note':'This includes roof-adjacent normally supported paths. The whole region is not required to run at overhang speed.'})
    d['mesh_overhang_audit']=audit
    d['roof_toolpath_audit']=roofs
    d['operator_feedback']={'date':'2026-09-13','reported_layer_height_mm':.28,
        'printed_trial':'Previous first saddle-and-cap coupon',
        'case_fit':'Reported very good, almost perfect. Preserve case-contact geometry.',
        'screw_fit':'Not tested successfully because support plastic blocked the holes.',
        'support_removal':'Regular supports stuck to the part and were difficult to remove completely.',
        'cap_clamping':'Expected by the operator to work; not yet demonstrated with screws.',
        'measured_dimensions_mm':None,
        'next_test':'Full-size revised saddle and matching cap, 45-degree hole roofs, no generated supports.'}
    d['status']='CAD, mesh and engine checks pass; awaiting second physical print'
    p.write_text(json.dumps(d,indent=2),encoding='utf-8')
    fig,axes=plt.subplots(2,1,figsize=(10,8))
    fig.subplots_adjust(left=.12,right=.97,top=.86,bottom=.09,hspace=.42)
    meshes=[DESIGN/'cad/output/coupons_stl/r5_case_datum_saddle_0p3.stl',
            HERE/'second_fit_saddle_45deg_roofs.stl']
    for ax,path,title,color in zip(axes,meshes,
        ['First print: original nut-pocket roofs','Second print: 45-degree roofs, same screw axes'],['#6c747b','#16878b']):
        mesh=trimesh.load_mesh(path,process=True)
        section=mesh.section(plane_origin=[0,11,0],plane_normal=[0,1,0])
        for line in section.discrete:ax.plot(line[:,0],line[:,2],color=color,lw=1.5)
        ax.set_aspect('equal');ax.set_xlim(-1,63);ax.set_ylim(-1,35)
        ax.set_title(title,loc='left',fontsize=13);ax.set_ylabel('Print height (mm)')
        ax.grid(alpha=.15);ax.spines[['top','right']].set_visible(False)
        for roof in d['bolt_roofs']:
            ax.plot(roof['x_mm']+43.115,roof['z_mm']+32,'+',color='#bc5144',ms=7)
    axes[1].set_xlabel('Width along the saddle (mm)')
    fig.suptitle('Full-size second fit trial',fontsize=19,x=.12,y=.97,ha='left')
    fig.text(.12,.915,'Section through the actual nut pockets. Red crosses mark unchanged axes.',ha='left',fontsize=10)
    fig.savefig(HERE/'hole_roof_comparison.png',dpi=160,facecolor='white');plt.close(fig)
    print(json.dumps({'mesh_audit':audit,'roof_slowdown_checks':roofs}))


if __name__=='__main__':main()
