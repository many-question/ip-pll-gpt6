"""Resettable C2MOS cyclic rings atRF/2; controlled follow-up to static-ring trials."""
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
def m(n,t,d,g,s,b,w):return f'{n} ({d} {g} {s} {b}) {t} w={w} l=180n ad={w}*240n as={w}*240n pd=2*({w}+240n) ps=2*({w}+240n)'
cells=['simulator lang=spectre']
for init in [0,1]:
 cells += [f'subckt ring_c2_r{init}_v14 (d clk clkb reset resetb q vdd vss)',
  'XM (d clk clkb qb vdd vss) pll_clocked_inv wp=2.5u','XS (qb clkb clk q vdd vss) pll_clocked_inv wp=2.5u']
 cells += [m('MC','nch','qb' if init else 'q','reset','vss','vss','0.8u'),m('MP','pch','q' if init else 'qb','resetb','vdd','vdd','1.6u')]
 cells.append(f'ends ring_c2_r{init}_v14')
(B/'ring_c2_v14.scs').write_text('\n'.join(cells)+'\n')
s=(B/'cmos_even_bank_r4_v14.scs').read_text().replace('cmos_even_bank_r4_v14','cmos_even_bank_r5_v14')
s=s.replace('include "ff_fbdelay50_v14.scs"','include "ff_fbdelay50_v14.scs"\ninclude "ring_c2_v14.scs"')
s=s.replace('XCB0 (q1 ckbn vdd vss) pll_inv wn=1u wp=6u','XCB0 (q1 ckbn vdd vss) pll_inv wn=1u wp=4u')
for k,n in enumerate(range(2,8)):
 s=s.replace(f'XSE{k} (s{k} ckb ckbank safe{k} vdd vss) pll_latch',f'XRE{k} (rst{k} allow{k} vdd vss) pll_inv\nXSE{k} (allow{k} ckb ckbank safe{k} vdd vss) pll_latch')
 s=s.replace(f'XGO{k} (gn{k} ck{k} vdd vss) pll_inv wn=8u wp=20u',f'XGO{k} (gn{k} ck{k} vdd vss) pll_inv wn=16u wp=40u\nXCINV{k} (ck{k} ckn{k} vdd vss) pll_inv wn=16u wp=40u')
 for i in range(n):
  init=1 if i<(n+1)//2 else 0
  s=s.replace(f'(r{k}_{(i-1)%n} ck{k} rst{k} r{k}_{i} vdd vss) tx_dff_r{init}',f'(r{k}_{(i-1)%n} ck{k} ckn{k} rst{k} allow{k} r{k}_{i} vdd vss) ring_c2_r{init}_v14')
(B/'cmos_even_bank_r5_v14.scs').write_text(s)
for p in (H/'tb').glob('bank4_m*.scs'):
 (H/'tb'/p.name.replace('bank4_m','bank5_m')).write_text(p.read_text().replace('cmos_even_bank_r4_v14','cmos_even_bank_r5_v14'))
print('Built C2MOS ring bank')
