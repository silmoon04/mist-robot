"""Explore pitch travel before setting final independent operating limits."""
import itertools,json
import numpy as np
import build,geom as g

def main():
    parts,_=build.load_assembly();cache={};rows=[]
    angles=list(itertools.product((-30,0,30,65),(0,60,90,120)))
    angles += [(-35,0),(-35,125),(70,0),(70,120),(65,125),(70,125)]
    for hip,knee in angles:
        frames={'base_mount':np.eye(4),'coxa':np.eye(4),'femur':build.pose((82,0,0),(0,hip,0))}
        frames['tibia']=frames['femur']@build.pose((90,0,0),(0,knee,0))
        world=[dict(p,shape=build.shape_at(p['shape'],frames[p['link']])) for p in parts];hits=[]
        for i,a in enumerate(world):
            aa=g.bounds(a['shape'])
            for b in world[i+1:]:
                if a['link']==b['link']:continue
                bb=g.bounds(b['shape'])
                if any(aa[1][k]<=bb[0][k]+1e-5 or bb[1][k]<=aa[0][k]+1e-5 for k in range(3)):continue
                key=(a['name'],b['name'],tuple((np.linalg.inv(frames[a['link']])@frames[b['link']]).round(7).ravel()))
                if key not in cache:cache[key]=g.common_volume(a['shape'],b['shape'])
                if cache[key]>.01:hits.append({'a':a['name'],'b':b['name'],'mm3':cache[key]})
        row={'hip_deg':hip,'knee_deg':knee,'intersections':hits};rows.append(row);print(json.dumps(row),flush=True)
        (build.ROOT/'pitch_study.json').write_text(json.dumps(rows,indent=2))

if __name__=='__main__':main()
