from build import *
P=dict(kind='r',core=120e-6,switch=1.2e-6,l=2e-9,unit=4.4e-15)
for c in ['tt','ss','ff']:
    for code,m in [(12,4),(238,4),(238,8),(148,14)]:
        bench(f'target_{c}_c{code}_m{m}',code=code,m=m,corner=c,loaded=True,stop=160e-9,**P)
