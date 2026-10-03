"""Restore the proven TSPC stage; keep improvements after the prescaler.

The doubled dynamic output worked only with ideal20ps clock. This experiment
restores that stage without undoing tail isolation and ring-clock repair, and
separately tests static buffer strength. No full-DUT replacement.
"""
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
cases=[]
for tag,boost in [('origpre',False),('staticpre',True)]:
 name=f'bank_{tag}_v14'
 s=(B/'bank_preboost50_v14.scs').read_text().replace('bank_preboost50_v14',name).replace('ff_drive2_r50_v14','ff_fbdelay50_v14')
 if boost:s=s.replace('XPB1 (qb0 q1 vdd vss) pll_inv wn=2u wp=4u','XPB1 (qb0 q1 vdd vss) pll_inv wn=4u wp=8u')
 (B/(name+'.scs')).write_text(s)
 for m in [4,6,10]:
  case=f'bank{tag}_m{m}_ss';cases.append(case)
  s=(H/'tb'/f'bankboostrf_m{m}_ss.scs').read_text().replace('bank_preboost50_v14',name).replace('stop=100n outputstart=60n','stop=60n outputstart=20n')
  s+='save XD.XPRE.a XD.XPRE.b XD.XPRE.dn\n'
  (H/'tb'/(case+'.scs')).write_text(s)
print(' '.join(cases))
