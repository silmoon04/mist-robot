"""Build a gradual-start revision while retaining the original test bands."""
from pathlib import Path
root = Path(__file__).resolve().parents[1] / 'design'
old = root / 'speed_calibration_20260915'
new = root / 'speed_calibration_adhesion_v2_20260915'
new.mkdir(exist_ok=True)
g = (old / 'generate.py').read_text()
g = g.replace('BASE=.56;', 'BASE=1.12;')
g = g.replace('\ndef polygons(shape):', '\nBASES={name: shape.buffer(1,join_style=2) for name,shape in BASES.items()}\n\ndef polygons(shape):')
g = g.replace('self.raised=True', 'self.raised=True;self.travel_speed=150')
g = g.replace('150 if not string_transfer else 180', 'self.travel_speed if not string_transfer else 180')
g = g.replace("'G90','G28','G1 Z10 F300','G1 X20 Y8 F6000'", "'G90','M204 S250','G28','G1 Z10 F300','G1 X20 Y8 F2400'")
g = g.replace("'M204 S500']", "'M204 S250']")
g = g.replace('w.xyz=np.array([20.,8.,10.]);', 'w.accel=250;w.xyz=np.array([20.,8.,10.]);')
start = g.index('    for layer in range(1,3):')
end = g.index('    # Print all identifiers', start)
g = g[:start] + '''    for layer,speed,acceleration,travel,fan in [(1,12,250,40,0),(2,20,400,50,0),(3,25,500,60,64),(4,30,600,70,128)]:
        z=layer*LH;w.stage_set('BASE',0,acceleration);w.travel_speed=travel
        w.emit(f'M106 S{fan}')
        for name,shape in BASES.items():w.shell(shape,z,speed,walls=2,fill=True,alternate=layer%2)
''' + g[end:]
g = g.replace("w.stage_set('LABEL',0,1000)", "w.stage_set('LABEL',0,500);w.travel_speed=60")
g = g.replace('z,25,walls=1,fill=False)', 'z,20,walls=1,fill=False)')
g = g.replace('    schedule=[]', '    w.travel_speed=150\n    schedule=[]')
g = g.replace('EN4Pro_One_Run_Speed_Flow_Accel_Stringing.gcode', 'EN4Pro_Calibration_V2_Slow_Start.gcode')
g = g.replace("w.emit(';NEPTUNE", "w.emit(';V2: Four gradual base layers with wider attached foundations.');w.emit(';NEPTUNE")
(new/'generate.py').write_text(g)
v = (old/'validate.py').read_text().replace("xyz[0]>=17 and xyz[0]<=203 and xyz[1]>=7 and xyz[1]<=207", "xyz[0]>=15 and xyz[0]<=205 and xyz[1]>=7 and xyz[1]<=209")
v = v.replace('    assert temp==0', '''    for row in rows:
        if row['stage']=='BASE':
            if row['e']>0:
                layer=round(row['end'][2]/.28)
                speed_limit,acc_limit,fan_limit=[(12,250,0),(20,400,0),(25,500,64),(30,600,128)][layer-1]
                assert row['speed']<=speed_limit and row['accel']==acc_limit and row['fan']==fan_limit
            else:
                assert row['speed']<=70 and row['accel']<=600
        if row['stage']=='LABEL':assert row['speed']<=60 and row['accel']==500
    assert temp==0''')
v = v.replace("'checks':['ASCII command allowlist'", "'checks':['Four base layers: extrusion, travel, acceleration and fan limits','ASCII command allowlist'")
(new/'validate.py').write_text(v)
(new/'render.py').write_text((old/'render.py').read_text())
print(new)
