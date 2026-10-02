"""Separate divider clock candidate; not substituted into capture-test DUT."""
from pathlib import Path
H=Path(__file__).resolve().parent; B=H.parents[1]/'blocks/cmos_v14_full'
name='cmos_even_bank_clkfix_v14'
s=(B/'cmos_even_bank_acq_v14.scs').read_text().replace('cmos_even_bank_acq_v14',name)
changes={
 'XCI (q1 ci vdd vss) pll_inv wn=0.5u wp=2u':
 'XCI (q1 ci vdd vss) pll_inv wn=2u wp=4u',
 'XCB1 (gn cb vdd vss) pll_inv wn=6u wp=12u':
 'XCB1 (gn cb vdd vss) pll_inv wn=8u wp=16u',
}
for old,new in changes.items():
    assert old in s
    s=s.replace(old,new)
(B/(name+'.scs')).write_text(s)
for m in [4,6,8,10,12,14]:
    for c in ['tt','ss','ff']:
        s=(H/'tb'/f'bankrt_m{m}_{c}.scs').read_text().replace('cmos_even_bank_acq_v14',name)
        s=s.replace('stop=100n outputstart=60n','stop=100n')
        s=s.replace('saveOptions options','save XD.ci XD.gn XD.cb XD.run XD.loadb XD.XD6.clkb\nsaveOptions options')
        (H/'tb'/f'bankclk_m{m}_{c}.scs').write_text(s)
