"""Target the observed incomplete master-latch settling at SS.

Separate candidate; the captured full PLL remains unchanged. Ideal-clock
diagnostics isolate the data path before physical clock-tree integration.
"""
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
cell='''simulator lang=spectre
// Master input and slave transfer TGs are strengthened; master inverter load
// and feedback loading are reduced. Slave drive serves the next stage/mux.
subckt ring_fast_master_v14 (d ck ckb qb vdd vss)
XT (d x ck ckb vdd vss) pll_tg wn=2u wp=4u
XO (x qb vdd vss) pll_inv wn=0.8u wp=1.6u
XFI (qb fb vdd vss) pll_inv wn=0.25u wp=0.5u
XFB (fb x ckb ck vdd vss) pll_tg wn=0.25u wp=0.5u
ends ring_fast_master_v14
subckt ring_fast_slave_v14 (d ck ckb qb vdd vss)
XT (d x ck ckb vdd vss) pll_tg wn=2u wp=4u
XO (x qb vdd vss) pll_inv wn=4u wp=8u
XFI (qb fb vdd vss) pll_inv wn=0.25u wp=0.5u
XFB (fb x ckb ck vdd vss) pll_tg wn=0.25u wp=0.5u
ends ring_fast_slave_v14
subckt ring_datafast_v14 (d clk clkb load loadb init q vdd vss)
XDATA (d din loadb load vdd vss) pll_tg wn=1u wp=2u
XINIT (init din load loadb vdd vss) pll_tg wn=1u wp=2u
XM (din clkb clk qm vdd vss) ring_fast_master_v14
XS (qm clk clkb q vdd vss) ring_fast_slave_v14
ends ring_datafast_v14
'''
(B/'ring_datafast_v14.scs').write_text(cell)
for base,name in [('bank_clock_isolation_v14','bank_ideal_datafast_v14'),('cmos_even_bank_acq_v14','bank_datafast_v14')]:
 s=(B/(base+'.scs')).read_text().replace(base,name).replace('ring_inv_sync_v14','ring_datafast_v14')
 s=s.replace('include "ring_inv_static_v14.scs"','include "ring_inv_static_v14.scs"\ninclude "ring_datafast_v14.scs"')
 (B/(name+'.scs')).write_text(s)
for m in [10,14]:
 s=(H/'tb'/f'bankclkideal_m{m}_ss.scs').read_text().replace('bank_clock_isolation_v14','bank_ideal_datafast_v14')
 s+='save XD.XF0.din XD.XF0.qm XD.XF0.XM.x XD.XF0.XS.x\n'
 (H/'tb'/f'bankclkidealfast_m{m}_ss.scs').write_text(s)
print('Generated data-path candidate, not integrated into the full PLL.')
