from build import *
P=dict(kind='r',core=120e-6,switch=1.2e-6,l=2e-9,unit=4.4e-15)
for c in ['tt','ss','ff']:
    for code in [8,248]:
        name=f'startup_{c}_c{code}'
        bench(name,code=code,corner=c,proxy=140e-15,analysis='ac',**P)
        p=H/'tb'/f'{name}.scs';s=p.read_text().replace('save vp vn','save XV.XL.MN0:d XV.XL.MN1:d XV.XL.MN0:g XV.XL.MN1:g vp vn');p.write_text(s)
for q in [3,8]:
    for code in [8,248]:
        bench(f'sensitivity_q{q}_c{code}',q=q,code=code,corner='ss',proxy=140e-15,stop=200e-9,**P)
