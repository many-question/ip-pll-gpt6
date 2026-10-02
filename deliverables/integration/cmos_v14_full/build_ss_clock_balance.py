"""Second isolated clock test: reduce excess buffer fanout and balance polarity."""
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
name='cmos_even_bank_clkbal_v14'
s=(B/'cmos_even_bank_acq_v14.scs').read_text().replace('cmos_even_bank_acq_v14',name)
changes={
 'XCI (q1 ci vdd vss) pll_inv wn=0.5u wp=2u':'XCI (q1 ci vdd vss) pll_inv wn=1u wp=2u',
 'XCB1 (gn cb vdd vss) pll_inv wn=6u wp=12u':'XCB1 (gn cb vdd vss) pll_inv wn=4u wp=8u',
 'XCB2 (cb ck vdd vss) pll_inv wn=24u wp=48u':'XCB2 (cb ck vdd vss) pll_inv wn=8u wp=16u',
 'XCKB (ck ckb vdd vss) pll_inv wn=8u wp=16u':'XCKB (ck ckb vdd vss) pll_inv wn=4u wp=8u',
}
for a,b in changes.items():
 assert a in s;s=s.replace(a,b)
(B/(name+'.scs')).write_text(s)
for p in (H/'tb').glob('bankclk_m*.scs'):
 s=p.read_text().replace('cmos_even_bank_clkfix_v14',name)
 (H/'tb'/p.name.replace('bankclk_','bankclkbal_')).write_text(s)
