"""Shared static TG register ring with synchronous pattern loading.

Keep RF prescaler and proven /4. Static storage removes TSPC/C2MOS data-hold
dependence in programmable ring; shared complementary clock has explicit drive.
"""
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
cells=['simulator lang=spectre',
       'subckt ring_static_latch_v14 (d ck ckb q vdd vss)',
       'XT (d x ck ckb vdd vss) pll_tg wn=1u wp=2u',
       'XI (x qb vdd vss) pll_inv wn=0.8u wp=1.6u',
       'XO (qb q vdd vss) pll_inv wn=1.6u wp=3.2u',
       'XFB (q x ckb ck vdd vss) pll_tg wn=0.5u wp=1u',
       'ends ring_static_latch_v14',
       'subckt ring_static_sync_v14 (d clk clkb load loadb init q vdd vss)',
       'XDATA (d din loadb load vdd vss) pll_tg wn=2u wp=4u',
       'XINIT (init din load loadb vdd vss) pll_tg wn=2u wp=4u',
       'XM (din clkb clk qm vdd vss) ring_static_latch_v14',
       'XS (qm clk clkb q vdd vss) ring_static_latch_v14','ends ring_static_sync_v14']
(B/'ring_static_v14.scs').write_text('\n'.join(cells)+'\n')
s=(B/'cmos_even_bank_r10_v14.scs').read_text()
a=s.index('subckt ring_tspc_sync_v14');b=s.index('ends ring_tspc_sync_v14')+len('ends ring_tspc_sync_v14')
s=s[:a]+'include "ring_static_v14.scs"'+s[b:]
s=s.replace('cmos_even_bank_r10_v14','cmos_even_bank_r12_v14').replace('ring_tspc_sync_v14','ring_static_sync_v14')
s=s.replace('ck load loadb','ck ckb load loadb')
s=s.replace('XCB1 (gn cb vdd vss) pll_inv wn=2u wp=4u','XCB1 (gn cb vdd vss) pll_inv wn=4u wp=8u')
s=s.replace('XCB2 (cb ck vdd vss) pll_inv wn=8u wp=16u','XCB2 (cb ck vdd vss) pll_inv wn=16u wp=32u\nXCKB (ck ckb vdd vss) pll_inv wn=8u wp=16u')
(B/'cmos_even_bank_r12_v14.scs').write_text(s)
for p in (H/'tb').glob('bank10_m*.scs'):
 s=p.read_text().replace('cmos_even_bank_r10_v14','cmos_even_bank_r12_v14').replace('XD.ck XD.run','XD.ck XD.ckb XD.run')
 (H/'tb'/p.name.replace('bank10_','bank12_')).write_text(s)
print('Built static synchronous ring bank')
