"""One flat hub and eight requested spacers on one Neptune4Pro build plate."""
from pathlib import Path
import json,hashlib,zipfile,configparser,io
import numpy as np,trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import slicing as s
ROOT=s.ROOT;OUT=ROOT/'corrected_spacers';s.OUT=OUT

def main():
    check=json.loads((OUT/'Hub_Check.json').read_text());assert check['status']=='pass'
    hub=trimesh.load_mesh(OUT/'Main_Hub_4Leg.stl');spacer=trimesh.load_mesh(OUT/'Spacer_13H_5p5OD_M3.stl')
    for m in [hub,spacer]:assert m.is_watertight and m.is_winding_consistent and m.volume>0
    hub.apply_translation([112.5,112.5,0]);placed=[('Main_Hub_4Leg',hub)]
    for x in (11.5,213.5):
        for y in (72,99,126,153):
            m=spacer.copy();m.apply_translation([x,y,0]);placed.append((f'Spacer_13H_5p5OD_M3_{len(placed)}',m))
    for i,(n,a) in enumerate(placed):
        assert a.bounds[0,2]>-1e-6
        assert min(a.bounds[0,:2].min(),(225-a.bounds[1,:2]).min())>=5-.04
        for nn,b in placed[i+1:]:assert any(a.bounds[1,k]+5<=b.bounds[0,k]+.05 or b.bounds[1,k]+5<=a.bounds[0,k]+.05 for k in (0,1)),(n,nn)
    m=trimesh.util.concatenate([mesh for name,mesh in placed]);stl=OUT/'Tonight_Hub_And_8_Spacers.stl';m.export(stl);s.three_mf(stl.with_suffix('.3mf'),placed)
    fig,ax=plt.subplots(figsize=(9,9),facecolor='#f3f4f0');ax.set_facecolor('#f3f4f0')
    for n,m in placed:
        ax.add_collection(PolyCollection(m.triangles[:,:,:2],facecolors='#55999c' if n=='Main_Hub_4Leg' else '#d0a156',edgecolors='none',alpha=.4))
    ax.set_xlim(0,225);ax.set_ylim(0,225);ax.set_aspect('equal');ax.set_title('One hub + eight 13 mm tall / 5.5 mm OD spacers',fontsize=15);ax.set_xlabel('Bed X mm');ax.set_ylabel('Bed Y mm');fig.savefig(OUT/'Tonight_Plate_Map.png',dpi=140,bbox_inches='tight');plt.close(fig)
    # The close side columns need only a2mm external brim; all pieces have
    # broad flat contact. Change both actual analysis and imported profile.
    original=s.settings
    def settings(faster=False):
        v=original(faster);v.update(brim_width=2,brim_line_count=5);return v
    s.settings=settings;s.profile()
    result=s.run_slice(stl,'hub_spacers_13H_5p5OD',True)
    bounds=np.array(result['engine']['motion_bounds_mm']);assert min(bounds[0,:2].min(),(225-bounds[1,:2]).min())>1.5
    result.update(status='pass',plate_stl_sha256=s.sha(stl),plate_3mf_sha256=s.sha(stl.with_suffix('.3mf')),profile_sha256=s.sha(OUT/'Neptune4Pro_Hub_PLA_028.curaprofile'),
        hub_stl_sha256=s.sha(OUT/'Main_Hub_4Leg.stl'),spacer_stl_sha256=s.sha(OUT/'Spacer_13H_5p5OD_M3.stl'),objects=[name for name,mesh in placed],
        units='mm',orientation='Flat underside on bed; ribs up. Spacers stand on their annular ends. No supports.',
        minimum_motion_edge_margin_mm=float(min(bounds[0,:2].min(),(225-bounds[1,:2]).min())))
    (OUT/'Tonight_Print_Check.json').write_text(json.dumps(result,indent=2));print('READY',result['engine']['estimated_time_seconds']/3600,result['deposition']['total_deposited_mass_g'])

if __name__=='__main__':main()
