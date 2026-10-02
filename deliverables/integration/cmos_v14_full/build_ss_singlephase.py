"""Isolate complementary-clock sensitivity using CMOS single-phase storage."""
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
name='cmos_even_bank_singlephase_v14'
s=(B/'cmos_even_bank_clkfix_v14.scs').read_text().replace('cmos_even_bank_clkfix_v14',name)
old='''XM (d clkb clk qm vdd vss) ring_inv_latch_v14
XS (qm clk clkb q vdd vss) ring_inv_latch_v14'''
new='''XF (d clk qb vdd vss) pll_tspc_inv
XO (qb q vdd vss) pll_inv wn=2u wp=4u
XK (q qb vdd vss) pll_inv wn=0.24u wp=0.48u ln=1u'''
assert old in s;s=s.replace(old,new)
sync='''subckt ring_sync_singlephase_v14 (d clk clkb load loadb init q vdd vss)
XDATA (d din loadb load vdd vss) pll_tg wn=2u wp=4u
XINIT (init din load loadb vdd vss) pll_tg wn=2u wp=4u
XF (din clk clkb q vdd vss) ff_static_fast_v14
ends ring_sync_singlephase_v14
'''
s=s.replace('subckt '+name,sync+'subckt '+name).replace(') ring_inv_sync_v14',') ring_sync_singlephase_v14')
(B/(name+'.scs')).write_text(s)
for p in (H/'tb').glob('bankclk_m*.scs'):
 s=p.read_text().replace('cmos_even_bank_clkfix_v14',name)
 (H/'tb'/p.name.replace('bankclk_','bankclksp_')).write_text(s)
