"""Causality test: isolate unused /7 tail data load during /5 operation.

Clock-window tests show M14 tolerates much slower edges than M10. The M10
feedback tap also drives two unused stages; M14's final tap has no such fanout.
This variant gates the unused data connection without inserting clock skew.
"""
from pathlib import Path
import re
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
for kind in ['window','tapera','taperc','shape']:
 old={'window':'bank_window_v14','tapera':'bank_taper_a_v14','taperc':'bank_taper_c_v14','shape':'bank_hybrid_shape_v14'}[kind]
 name='bank_tail_'+kind+'_v14'
 s=(B/(old+'.scs')).read_text().replace(old,name)
 tail='''subckt ring_tail_singlephase_v14 (d clk clkb load loadb init selected q vdd vss)
XEN (loadb selected dopen vdd vss) tx_and
XI (dopen dclose vdd vss) pll_inv
XDATA (d din dopen dclose vdd vss) pll_tg wn=2u wp=4u
XINIT (init din load loadb vdd vss) pll_tg wn=2u wp=4u
RKEEP (din vss) resistor r=10Meg
XF (din clk clkb q vdd vss) ff_singlephase_v14
ends ring_tail_singlephase_v14
'''
 s=s.replace('subckt '+name,tail+'subckt '+name)
 for i in [5,6]:
  s=re.sub(r'^(XF'+str(i)+r' \([^\n]+ vss) (r'+str(i)+r' vdd vss\)) ring_sync_singlephase_v14',r'\1 s5 \2 ring_tail_singlephase_v14',s,flags=re.M)
 assert s.count('ring_tail_singlephase_v14')==4
 (B/(name+'.scs')).write_text(s)
 if kind=='window':
  for edge in [20,80,140]:
   original=f'bankwindow_m10_e{edge}_d50_ss'
   tb=(H/'tb'/(original+'.scs')).read_text().replace(old,name)
   tb+='save XD.XF4.XF.qb XD.XF4.XF.XF.a XD.XF4.XF.XF.b XD.XF0.din XD.XF5.din\n'
   (H/'tb'/f'banktail_m10_e{edge}_ss.scs').write_text(tb)
 else:
  for m in [6,10,14]:
   prefix={'tapera':'banktapera','taperc':'banktaperc','shape':'bankclkshape'}[kind]
   tb=(H/'tb'/f'{prefix}_m{m}_ss.scs').read_text().replace(old,name)
   tb=tb.replace('stop=100n','stop=60n')
   (H/'tb'/f'banktail{kind}_m{m}_ss.scs').write_text(tb)
print('Unused data-tail isolation fixtures generated; clocks unchanged.')
