from build import *
P=dict(kind='r',core=120e-6,switch=1.2e-6,l=2e-9,unit=4.4e-15)
codes=[0,7,8,15,16,31,32,63,64,127,128,247,248,255,0,255]
for c in ['tt','ss','ff']:
    name=f'dynamic_{c}';bench(name,corner=c,proxy=140e-15,stop=len(codes)*100e-9,**P)
    p=H/'tb'/f'{name}.scs';s=p.read_text()
    for bit in range(8):
        points=[(0.,1.2 if codes[0]&(1<<bit) else 0.)]
        for j,code in enumerate(codes[1:],1):
            old=points[-1][1];new=1.2 if code&(1<<bit) else 0.
            if old!=new:points.extend([(j*100e-9,old),(j*100e-9+100e-12,new)])
        wave=' '.join(f'{t:.14g} {v:g}' for t,v in points)
        s=s.replace(f'VB{bit} (b{bit} 0) vsource dc=0',f'VB{bit} (b{bit} 0) vsource type=pwl wave=[{wave}]')
    s=s.replace('save vp vn','save b0 b1 b2 b3 b4 b5 b6 b7 vp vn XV.XL.nfilt XV.XBP.x7')
    p.write_text(s)
(H/'results/dynamic_stimulus.json').write_text(json.dumps(dict(codes=codes,stage_s=100e-9,measure_after_s=60e-9,edge_s=100e-12),indent=2)+'\n')
