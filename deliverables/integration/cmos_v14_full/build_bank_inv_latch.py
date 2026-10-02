"""Two inverting static latches give a noninverting FF with fewer forward stages.

The previous ring used two noninverting latches (four forward inverters per
FF), which failed even with ideal clocks. This topology has one inverter per
phase; feedback inverters only retain storage while that phase is closed.
"""
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
s=['simulator lang=spectre',
   'subckt ring_inv_latch_v14 (d ck ckb qb vdd vss)',
   'XT (d x ck ckb vdd vss) pll_tg wn=1u wp=2u',
   'XO (x qb vdd vss) pll_inv wn=2u wp=4u',
   'XFI (qb fb vdd vss) pll_inv wn=0.5u wp=1u',
   'XFB (fb x ckb ck vdd vss) pll_tg wn=0.5u wp=1u',
   'ends ring_inv_latch_v14',
   'subckt ring_inv_sync_v14 (d clk clkb load loadb init q vdd vss)',
   'XDATA (d din loadb load vdd vss) pll_tg wn=2u wp=4u',
   'XINIT (init din load loadb vdd vss) pll_tg wn=2u wp=4u',
   'XM (din clkb clk qm vdd vss) ring_inv_latch_v14',
   'XS (qm clk clkb q vdd vss) ring_inv_latch_v14','ends ring_inv_sync_v14']
(B/'ring_inv_static_v14.scs').write_text('\n'.join(s)+'\n')
s=(B/'cmos_even_bank_r12_v14.scs').read_text().replace('cmos_even_bank_r12_v14','cmos_even_bank_r13_v14').replace('ring_static_v14.scs','ring_inv_static_v14.scs').replace('ring_static_sync_v14','ring_inv_sync_v14')
(B/'cmos_even_bank_r13_v14.scs').write_text(s)
for p in (H/'tb').glob('bank12_m*.scs'):
 (H/'tb'/p.name.replace('bank12_','bank13_')).write_text(p.read_text().replace('cmos_even_bank_r12_v14','cmos_even_bank_r13_v14'))
s=(H/'tb/ringstatic_load_ss.scs').read_text().replace('ring_static_v14.scs','ring_inv_static_v14.scs').replace('ring_static_sync_v14','ring_inv_sync_v14')
(H/'tb/ringinv_ss.scs').write_text(s)
print('Built one-forward-inverter-per-phase static ring')
