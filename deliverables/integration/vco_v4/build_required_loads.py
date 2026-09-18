from build_segmented_tail import P
from build import *
for c in ['tt','ss','ff']:
    for code,m in [(0,4),(255,4),(255,8),(144,14),(192,12),(128,10),(240,6)]:
        bench(f'required_{c}_c{code}_m{m}',code=code,m=m,corner=c,loaded=True,stop=180e-9,**P)
channels=[]
for k in range(9,42):
    m=14 if k==9 else 12 if k<=11 else 10 if k<=13 else 8 if k<=18 else 6 if k<=27 else 4
    channels.append(dict(k=k,m=m,fout_hz=k*24e6,fvco_hz=k*m*24e6))
(H/'results/required_channels.json').write_text(json.dumps(channels,indent=2)+'\n')
