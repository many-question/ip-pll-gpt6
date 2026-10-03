"""Screen prescaler feedback delay against the real RF receiver's edge shape."""
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
cases=[]
for r in [25,35,10]:
 ff=f'ff_drive2_r{r}_v14';bank=f'bank_preboost{r}_v14'
 (B/(ff+'.scs')).write_text((B/'ff_drive2_r50_v14.scs').read_text().replace('ff_drive2_r50_v14',ff).replace('r=50000',f'r={r*1000}'))
 (B/(bank+'.scs')).write_text((B/'bank_preboost50_v14.scs').read_text().replace('ff_drive2_r50_v14',ff).replace('bank_preboost50_v14',bank))
 for m in [4,6]:
  case=f'bankfeed{r}_m{m}_ss';cases.append(case)
  s=(H/'tb'/f'bankboostrf_m{m}_ss.scs').read_text().replace('bank_preboost50_v14',bank)
  s=s.replace('stop=100n outputstart=60n','stop=60n outputstart=20n')
  s+='save XD.XPRE.a XD.XPRE.b XD.XPRE.dn\n'
  (H/'tb'/(case+'.scs')).write_text(s)
print(' '.join(cases))
