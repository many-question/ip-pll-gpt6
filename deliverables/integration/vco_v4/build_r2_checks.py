from build import *
P=dict(kind='r',core=120e-6,switch=1.2e-6,l=2e-9,unit=4.4e-15,fixed=10e-15,fine=4.5e-6)
for c in ['tt','ss','ff']:
    for code in [6,243]:
        bench(f'r2_noise_{c}_c{code}',code=code,corner=c,proxy=140e-15,analysis='noise',stop=200e-9,step=2e-12,sidebands=63,fund=3.94e9 if code==6 else 2.69e9,**P)
        name=f'r2_startup_{c}_c{code}'
        bench(name,code=code,corner=c,proxy=140e-15,analysis='ac',**P)
        p=H/'tb'/f'{name}.scs';p.write_text(p.read_text().replace('save vp vn','save XV.XL.MN0:d XV.XL.MN1:d XV.XL.MN0:g XV.XL.MN1:g vp vn'))
for code in [6,243]:
    bench(f'r2_noise_tight_c{code}',code=code,proxy=140e-15,analysis='noise',stop=200e-9,step=1e-12,sidebands=127,fund=3.94e9 if code==6 else 2.69e9,**P)
for q in [3,8]:
    for code in [6,243]:bench(f'r2_sensitivity_q{q}_c{code}',q=q,code=code,corner='ss',proxy=140e-15,stop=180e-9,**P)

codes=[0,7,8,15,16,31,32,63,64,103,104,127,128,247,248,255,0,255]
stage=80e-9
for c in ['tt','ss','ff']:
    name=f'r2_dynamic_{c}';bench(name,corner=c,proxy=140e-15,stop=len(codes)*stage,**P)
    p=H/'tb'/f'{name}.scs';s=p.read_text()
    for bit in range(8):
        points=[(0.,0.)]
        for j,code in enumerate(codes[1:],1):
            old=points[-1][1];new=1.2 if code&(1<<bit) else 0.
            if old!=new:points.extend([(j*stage,old),(j*stage+100e-12,new)])
        wave=' '.join(f'{t:.14g} {v:g}' for t,v in points)
        s=s.replace(f'VB{bit} (b{bit} 0) vsource dc=0',f'VB{bit} (b{bit} 0) vsource type=pwl wave=[{wave}]')
    p.write_text(s)
(H/'results/r2_dynamic_stimulus.json').write_text(json.dumps(dict(codes=codes,stage_s=stage,measure_after_s=50e-9,edge_s=100e-12),indent=2)+'\n')
bench('r2_explicit_defaults',proxy=140e-15,stop=160e-9,**P)
