from build import *
P=dict(kind='b',core=120e-6,switch=1.2e-6,l=2e-9,unit=4.4e-15)
for c in ['tt','ss','ff']:
    for code,m in [(0,4),(255,14)]:
        bench(f'repair_{c}_c{code}_m{m}',code=code,m=m,corner=c,loaded=True,stop=200e-9,**P)
        bench(f'repair_proxy_{c}_c{code}',code=code,corner=c,proxy=140e-15,stop=160e-9,**P)
