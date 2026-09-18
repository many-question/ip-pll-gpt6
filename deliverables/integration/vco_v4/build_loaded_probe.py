from build import *
for code,m in [(0,4),(220,14),(255,14)]:
    bench(f'probe_n80i100_c{code}_m{m}',core=80e-6,ibias=100e-6,code=code,m=m,loaded=True,stop=250e-9)
