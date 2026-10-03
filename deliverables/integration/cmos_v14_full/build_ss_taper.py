"""Reduce prescaler-node loading, then restore clock slew with a tapered tree.

The first inverter is deliberately small; the original failed drive trial put
more capacitance directly on the dynamic prescaler output. All stages here are
physical CMOS; no ideal internal clock and no added per-ring-stage skew.
"""
from pathlib import Path
import re
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
for label,first in [('a','wn=0.22u wp=0.44u'),('b','wn=0.3u wp=0.6u'),('c','wn=0.8u wp=0.5u')]:
 name='bank_taper_'+label+'_v14'
 s=(B/'bank_hybrid_clock_v14.scs').read_text().replace('bank_hybrid_clock_v14',name)
 s=re.sub(r'^XPB0 .*\nXPB1 .*\n',f'XPB0 (q0 qb0 vdd vss) pll_inv {first}\nXPB1 (qb0 qb1 vdd vss) pll_inv wn=0.75u wp=1.5u\nXPB2 (qb1 q1 vdd vss) pll_inv wn=3u wp=6u\n',s,flags=re.M)
 s=s.replace('XGN (q1 run gn vdd vss) pll_nand2 wn=4u wp=4u','XGN (q1 run gn vdd vss) pll_nand2 wn=4u wp=6u')
 s=s.replace('XCB1 (gn cb vdd vss) pll_inv wn=4u wp=8u','XCB1 (gn cb vdd vss) pll_inv wn=8u wp=20u')
 s=s.replace('XCB2 (cb ck vdd vss) pll_inv wn=12u wp=24u','XCB2 (cb ck vdd vss) pll_inv wn=24u wp=60u')
 if label=='c':
  # Preserve the proven dynamic-node input threshold and capacitance. Reduce
  # its next-stage gate load, then add two stages to preserve clock polarity.
  s=re.sub(r'^XPB1 .*\nXPB2 .*\n','XPB1 (qb0 qb1 vdd vss) pll_inv wn=1u wp=2u\nXPB2 (qb1 qb2 vdd vss) pll_inv wn=2.5u wp=5u\nXPB3 (qb2 q1 vdd vss) pll_inv wn=6u wp=12u\n',s,flags=re.M)
  s=s.replace('XGN (q1 run','XCI (q1 ci vdd vss) pll_inv wn=2u wp=4u\nXGN (ci run')
 (B/(name+'.scs')).write_text(s)
 for corner in ['tt','ss','ff']:
  for m in [4,6,8,10,12,14]:
   tb=(H/'tb'/f'bankclkhybrid_m{m}_{corner}.scs').read_text().replace('bank_hybrid_clock_v14',name)
   tb=tb.replace('stop=100n','stop=60n')
   tb+='save XD.q0 XD.qb0 XD.qb1\n'
   (H/'tb'/f'banktaper{label}_m{m}_{corner}.scs').write_text(tb)
print('Prescaler tap/clock-tree candidates prepared for targeted SS tests.')
