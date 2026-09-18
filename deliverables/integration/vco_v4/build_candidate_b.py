from build import *
for c in ['tt','ss','ff']:
    for code,m in [(0,4),(220,14)]:
        bench(f'candb_{c}_c{code}_m{m}',kind='b',core=120e-6,switch=1.2e-6,l=2e-9,unit=5e-15,
              code=code,m=m,corner=c,loaded=True,stop=200e-9)
