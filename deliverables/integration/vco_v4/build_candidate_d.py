from build import *
P=dict(kind='d',core=120e-6,switch=1.2e-6,l=2e-9,unit=5e-15)
for c in ['tt','ss','ff']:
    for code,m in [(0,4),(230,14)]:
        bench(f'candd_{c}_c{code}_m{m}',code=code,m=m,corner=c,loaded=True,stop=180e-9,**P)
    for code in [0,255]:bench(f'candd_proxy_{c}_c{code}',code=code,corner=c,proxy=140e-15,stop=180e-9,**P)
