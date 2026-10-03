"""Separate active CMOS clock loads for /6 and /10,/14.

The original shared tree clocks unused ring cells during /6 and all seven ring
stages during /10. Isolated ideal clocks work, while physical edges fail.
This candidate reduces the active clock load and adds no ideal internal source.
"""
from pathlib import Path
import re
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
name='bank_split_clock_v14'
s=(B/'bank_hybrid_clock_v14.scs').read_text().replace('bank_hybrid_clock_v14',name)
begin=s.index('XEN0 (s1');end=s.index('XD6 (ck',begin)
s=s[:begin]+'''XRCI (q1 ci vdd vss) pll_inv wn=2u wp=4u
XREN0 (s3 s5 re0 vdd vss) tx_or
XREN1 (reset re0 rrun vdd vss) tx_or
XMEN (reset s1 mrun vdd vss) tx_or
XRGN (ci rrun rgn vdd vss) pll_nand2 wn=4u wp=4u
XRCB1 (rgn rcb vdd vss) pll_inv wn=4u wp=8u
XRCB2 (rcb ck vdd vss) pll_inv wn=8u wp=16u
XMGN (ci mrun mgn vdd vss) pll_nand2 wn=2u wp=2u
XMCB1 (mgn mcb vdd vss) pll_inv wn=2u wp=4u
XMCB2 (mcb mck vdd vss) pll_inv wn=8u wp=16u
XLG (ck s5 lgn vdd vss) pll_nand2 wn=1u wp=1u
XLC (lgn lck vdd vss) pll_inv wn=4u wp=8u
'''+s[end:]
s=s.replace('XD6 (ck d6','XD6 (mck d6')
s=s.replace('XF5 (r4 ck ck','XF5 (r4 lck lck').replace('XF6 (r5 ck ck','XF6 (r5 lck lck')
(B/(name+'.scs')).write_text(s)
for m in [6,10,14]:
 tb=(H/'tb'/f'bankclkhybrid_m{m}_ss.scs').read_text().replace('bank_hybrid_clock_v14',name).replace('stop=100n','stop=60n')
 tb=tb.replace('XD.ck XD.gn XD.cb','XD.ck XD.ci XD.rgn XD.rcb XD.mck XD.mgn XD.mcb XD.lck')
 tb+='save XD.q0 XD.qb0 XD.rrun XD.mrun\n'
 (H/'tb'/f'bankclksplit_m{m}_ss.scs').write_text(tb)
print('Split clock candidate generated; not substituted into full PLL.')
