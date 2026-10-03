"""Physical CMOS candidate: static /3, single-phase ring and three-stage clock.

Ideal-clock isolation showed the static /3 and TSPC ring separately work at SS.
All clocks here come from the actual RF prescaler. No full-PLL adoption yet.
"""
from pathlib import Path
import re
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
base=(B/'cmos_even_bank_acq_v14.scs').read_text()
sp=(B/'cmos_even_bank_singlephase_v14.scs').read_text()
ff=sp[sp.index('subckt ff_static_fast_v14'):sp.index('subckt nor_fast_v14')].replace('ff_static_fast_v14','ff_singlephase_v14')
ring=sp[sp.index('subckt ring_sync_singlephase_v14'):sp.index('subckt cmos_even_bank_singlephase_v14')].replace('ff_static_fast_v14','ff_singlephase_v14')
name='bank_hybrid_clock_v14'
s=base.replace('subckt cmos_even_bank_acq_v14',ff+ring+'subckt cmos_even_bank_acq_v14')
s=s.replace('cmos_even_bank_acq_v14',name).replace('ring_inv_sync_v14','ring_sync_singlephase_v14')
s=re.sub(r'^XCI .*\n','',s,flags=re.M)
s=s.replace('XGN (ci run gn','XGN (q1 run gn')
s=s.replace('XCB1 (gn cb vdd vss) pll_inv wn=6u wp=12u','XCB1 (gn cb vdd vss) pll_inv wn=4u wp=8u')
s=s.replace('XCB2 (cb ck vdd vss) pll_inv wn=24u wp=48u','XCB2 (cb ck vdd vss) pll_inv wn=12u wp=24u')
s=re.sub(r'^XCKB .*\n','',s,flags=re.M)
# The single-phase wrapper retains a legacy unused complementary-clock pin.
s=re.sub(r'^(XF\d+ \([^\n]+?) ck ckb ',r'\1 ck ck ',s,flags=re.M)
(B/(name+'.scs')).write_text(s)
for corner in ['tt','ss','ff']:
 for m in [4,6,8,10,12,14]:
  tb=(H/'tb'/f'bankrt_m{m}_{corner}.scs').read_text().replace('cmos_even_bank_acq_v14',name)
  tb=tb.replace('outputstart=60n','').replace('XD.ck XD.ckb','XD.ck XD.gn XD.cb')
  tb+='save XD.XD6.clkb XD.XD6.X0.qm XD.XD6.X0.XM.x XD.XD6.X0.XS.x XD.XF0.XF.qb XD.XF0.XF.XF.b XD.XF0.XF.XF.a\n'
  (H/'tb'/f'bankclkhybrid_m{m}_{corner}.scs').write_text(tb)
print('Generated physical CMOS clock/storage candidate; capture PLL unchanged.')
