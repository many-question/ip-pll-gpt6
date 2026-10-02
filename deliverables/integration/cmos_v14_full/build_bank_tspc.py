"""Shared seven-stage programmable TSPC ring after V14 RF prescaler.

The validated fixed /4 path is retained. Modes /6..14 select feedback taps
of one ring instead of clocking five parallel rings. Odd N duty is measured,
not assumed50%. Gates/keepers/resets are physical PDK MOS.
"""
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
s=['simulator lang=spectre','include "ff_fbdelay50_v14.scs"','include "ring_tspc_v14.scs"',
   'subckt ring_tspc_set_v14 (d clk reset resetb setval q vdd vss)',
   'XF (d clk qb vdd vss) pll_tspc_inv','XO (qb q vdd vss) pll_inv wn=1u wp=2.5u',
   'XSB (setval setb vdd vss) pll_inv','XN (reset setval nr vdd vss) pll_nand2',
   'XNI (nr rn vdd vss) pll_inv','XP (reset setb rp vdd vss) pll_nand2',
   'MRN (qb rn vss vss) nch w=1.6u l=180n ad=1.6u*240n as=1.6u*240n pd=2*(1.6u+240n) ps=2*(1.6u+240n)',
   'MRP (qb rp vdd vdd) pch w=3.2u l=180n ad=3.2u*240n as=3.2u*240n pd=2*(3.2u+240n) ps=2*(3.2u+240n)',
   'XK (q qb vdd vss) pll_inv wn=0.4u wp=0.8u ln=1u','ends ring_tspc_set_v14',
   'subckt cmos_even_bank_r7_v14 (clk reset s0 s1 s2 s3 s4 s5 q1 out vdd vss)',
   'XPRE (q0 clk q0 vdd vss) ff_fbdelay50_v14',
   'XPB0 (q0 qb0 vdd vss) pll_inv wn=0.8u wp=0.5u','XPB1 (qb0 q1 vdd vss) pll_inv wn=2u wp=4u',
   'XD4 (d4b q1 d4b vdd vss) pll_tspc_inv','XB4 (d4b d4 vdd vss) pll_inv wn=2u wp=5u',
   'XRR (reset s0 rr vdd vss) tx_or','XRA (rr allow vdd vss) pll_inv',
   'XCB0 (q1 ci vdd vss) pll_inv wn=0.5u wp=1u','XCB1 (ci cr vdd vss) pll_inv wn=1u wp=2.5u',
   'XCI (cr crb vdd vss) pll_inv','XL (allow crb cr safe vdd vss) pll_latch',
   'XGN (cr safe gn vdd vss) pll_nand2 wn=2u wp=2.5u',
   'XGC0 (gn g0 vdd vss) pll_inv wn=1u wp=2.5u','XGC1 (g0 g1 vdd vss) pll_inv wn=4u wp=10u',
   'XGC2 (g1 ck vdd vss) pll_inv wn=12u wp=30u',
   'XST0 (s3 s4 st0 vdd vss) tx_or','XST1 (st0 s5 init2 vdd vss) tx_or']
for i in range(7):
 d='fb' if i==0 else f'r{i-1}'
 if i in [2,3]:s.append(f'XF{i} ({d} ck rr allow {"init2" if i==2 else "s5"} r{i} vdd vss) ring_tspc_set_v14')
 else:s.append(f'XF{i} ({d} ck rr allow r{i} vdd vss) ring_tspc_r{1 if i<2 else 0}_v14')
for j in range(1,6):
 s += [f'XSI{j} (s{j} sb{j} vdd vss) pll_inv',f'XT{j} (r{j+1} fb s{j} sb{j} vdd vss) pll_tg wn=2u wp=4u']
s += ['RFB (fb vss) resistor r=10Meg','X4 (d4 s0 o4 vdd vss) tx_and',
      'XOTHER (s0 not4 vdd vss) pll_inv','XR (r0 not4 oring vdd vss) tx_and',
      'XOR (o4 oring preout vdd vss) tx_or','XRI (reset resetb vdd vss) pll_inv',
      'XM (preout resetb out vdd vss) tx_and','ends cmos_even_bank_r7_v14']
(B/'cmos_even_bank_r7_v14.scs').write_text('\n'.join(s)+'\n')
for p in (H/'tb').glob('bank_m*.scs'):
 s=p.read_text().replace('cmos_even_bank_v14','cmos_even_bank_r7_v14')
 s=s[:s.index('save clk')]+ 'save clk q1 data reset VDD:p XD.q0 XD.qb0 XD.cr XD.ck XD.safe XD.rr XD.fb '+' '.join(f'XD.r{i}' for i in range(7))+'\nsaveOptions options save=selected\n'
 (H/'tb'/p.name.replace('bank_m','bank7_m')).write_text(s)
print('Built shared TSPC ring bank and18 TBs')
