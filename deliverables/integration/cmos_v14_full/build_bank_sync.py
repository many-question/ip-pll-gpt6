"""Synchronous initialization eliminates partial first pulse seed corruption."""
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
s=['simulator lang=spectre','include "ff_fbdelay50_v14.scs"',
   'subckt ring_tspc_sync_v14 (d clk load loadb init q vdd vss)',
   'XDATA (d din loadb load vdd vss) pll_tg wn=2u wp=4u',
   'XINIT (init din load loadb vdd vss) pll_tg wn=2u wp=4u',
   'XF (din clk qb vdd vss) pll_tspc_inv','XO (qb q vdd vss) pll_inv wn=1u wp=2.5u',
   'XK (q qb vdd vss) pll_inv wn=0.4u wp=0.8u ln=1u','ends ring_tspc_sync_v14',
   'subckt cmos_even_bank_r10_v14 (clk reset s0 s1 s2 s3 s4 s5 q1 out vdd vss)',
   'XPRE (q0 clk q0 vdd vss) ff_fbdelay50_v14','XPB0 (q0 qb0 vdd vss) pll_inv wn=0.8u wp=0.5u',
   'XPB1 (qb0 q1 vdd vss) pll_inv wn=2u wp=4u',
   'XD4 (d4b q1 d4b vdd vss) pll_tspc_inv','XB4 (d4b d4 vdd vss) pll_inv wn=2u wp=5u',
   # Run ring clock during reset, even for /4. This loads the pattern repeatedly
   # before reset is sampled low. In /4, unneeded ring clock then stops high.
   'XNS (s0 not4 vdd vss) pll_inv','XEN (reset not4 run vdd vss) tx_or',
   'XCI (q1 ci vdd vss) pll_inv wn=0.5u wp=2u',
   'XGN (ci run gn vdd vss) pll_nand2 wn=4u wp=4u',
   'XCB1 (gn cb vdd vss) pll_inv wn=2u wp=4u','XCB2 (cb ck vdd vss) pll_inv wn=8u wp=16u',
   'XRL (reset ck loadb vdd vss) pll_tspc_inv','XRLI (loadb load vdd vss) pll_inv wn=0.8u wp=2u',
   'XRK (load loadb vdd vss) pll_inv wn=0.4u wp=0.8u ln=1u',
   'XST0 (s3 s4 st0 vdd vss) tx_or','XST1 (st0 s5 init2 vdd vss) tx_or']
for i in range(7):
 d='fb' if i==0 else f'r{i-1}'
 init='vdd' if i<2 else 'init2' if i==2 else 's5' if i==3 else 'vss'
 s.append(f'XF{i} ({d} ck load loadb {init} r{i} vdd vss) ring_tspc_sync_v14')
for j in range(1,6):
 s += [f'XSI{j} (s{j} sb{j} vdd vss) pll_inv',f'XT{j} (r{j+1} fb s{j} sb{j} vdd vss) pll_tg wn=2u wp=4u']
s += ['RFB (fb vss) resistor r=10Meg','X4 (d4 s0 o4 vdd vss) tx_and','XR (r0 not4 oring vdd vss) tx_and',
      'XOR (o4 oring preout vdd vss) tx_or','XRI (reset resetb vdd vss) pll_inv',
      'XM (preout resetb out vdd vss) tx_and','ends cmos_even_bank_r10_v14']
(B/'cmos_even_bank_r10_v14.scs').write_text('\n'.join(s)+'\n')
for p in (H/'tb').glob('bank_m*.scs'):
 s=p.read_text().replace('cmos_even_bank_v14','cmos_even_bank_r10_v14')
 s=s[:s.index('save clk')]+'save clk q1 data reset VDD:p XD.q0 XD.qb0 XD.ci XD.gn XD.cb XD.ck XD.run XD.load XD.loadb XD.fb '+' '.join(f'XD.r{i}' for i in range(7))+'\nsaveOptions options save=selected\n'
 (H/'tb'/p.name.replace('bank_m','bank10_m')).write_text(s)
print('Built synchronous initialization bank')
