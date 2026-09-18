from build import *
# Controlled diagnostic first; adopted implementation will use a MOS-switched
# mirror segment sharing the existing filtered reference, not a new ideal source.
for c in ['tt','ss']:
    for current in [110e-6,130e-6]:
        bench(f'boost_{c}_i{round(current*1e6)}',kind='s',core=120e-6,switch=1.2e-6,l=2e-9,unit=4.4e-15,
              code=255,m=14,corner=c,loaded=True,stop=160e-9,ibias=current)
