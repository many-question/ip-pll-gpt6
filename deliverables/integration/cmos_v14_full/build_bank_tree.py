"""Use low clock rates where the modulus permits it; physical CMOS throughout.

RF/2: proven RF prescaler, dedicated modulo3 for /6, shared length5/7 ring.
RF/4: /2 gives /8, modulo3 gives /12. All selections are held by config logic.
Odd-modulus duty is measured; no50% assertion is made.
"""
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
s=['simulator lang=spectre','include "ff_fbdelay50_v14.scs"','include "ring_inv_static_v14.scs"',
 'subckt ff_static_fast_v14 (d clk clkb q vdd vss)',
 'XM (d clkb clk qm vdd vss) ring_inv_latch_v14','XS (qm clk clkb q vdd vss) ring_inv_latch_v14','ends ff_static_fast_v14',
 'subckt nor_fast_v14 (a b out vdd vss)',
 'MP0 (p a vdd vdd) pch w=8u l=180n ad=8u*240n as=8u*240n pd=2*(8u+240n) ps=2*(8u+240n)',
 'MP1 (out b p vdd) pch w=8u l=180n ad=8u*240n as=8u*240n pd=2*(8u+240n) ps=2*(8u+240n)',
 'MN0 (out a vss vss) nch w=2u l=180n ad=2u*240n as=2u*240n pd=2*(2u+240n) ps=2*(2u+240n)',
 'MN1 (out b vss vss) nch w=2u l=180n ad=2u*240n as=2u*240n pd=2*(2u+240n) ps=2*(2u+240n)','ends nor_fast_v14',
 '// Self-recovering state cycle00->10->01->00;11 returns to01.',
 'subckt div3_fast_v14 (clk out vdd vss)',
 'XC (clk clkb vdd vss) pll_inv wn=4u wp=8u',
 'XN (q0 q1 d0 vdd vss) nor_fast_v14',
 'X0 (d0 clk clkb q0 vdd vss) ff_static_fast_v14',
 'X1 (q0 clk clkb q1 vdd vss) ff_static_fast_v14',
 'XB0 (q1 ob vdd vss) pll_inv wn=0.5u wp=1u','XB1 (ob out vdd vss) pll_inv wn=2u wp=4u','ends div3_fast_v14',
 'subckt cmos_even_bank_tree_v14 (clk reset s0 s1 s2 s3 s4 s5 q1 out vdd vss)',
 'XPRE (q0 clk q0 vdd vss) ff_fbdelay50_v14','XPB0 (q0 qb0 vdd vss) pll_inv wn=0.8u wp=0.5u',
 'XPB1 (qb0 q1 vdd vss) pll_inv wn=2u wp=4u',
 'XD4 (d4b q1 d4b vdd vss) pll_tspc_inv',
 'XB40 (d4b b40 vdd vss) pll_inv wn=0.8u wp=1.6u',
 'XB41 (b40 b41 vdd vss) pll_inv wn=2u wp=4u','XB42 (b41 d4 vdd vss) pll_inv wn=6u wp=12u',
 'XD8 (d8b d4 d8b vdd vss) pll_tspc_inv','XB8 (d8b d8 vdd vss) pll_inv wn=2u wp=4u',
 'XD12 (d4 d12 vdd vss) div3_fast_v14',
 'XEN0 (s1 s3 er0 vdd vss) tx_or','XEN1 (er0 s5 er1 vdd vss) tx_or','XEN (reset er1 run vdd vss) tx_or',
 'XCI (q1 ci vdd vss) pll_inv wn=0.5u wp=2u',
 'XGN (ci run gn vdd vss) pll_nand2 wn=4u wp=4u',
 'XCB1 (gn cb vdd vss) pll_inv wn=6u wp=12u','XCB2 (cb ck vdd vss) pll_inv wn=24u wp=48u',
 'XCKB (ck ckb vdd vss) pll_inv wn=8u wp=16u',
 'XD6 (ck d6 vdd vss) div3_fast_v14',
 'XRL (reset ck loadb vdd vss) pll_tspc_inv','XRLI (loadb load vdd vss) pll_inv wn=0.8u wp=2u',
 'XRK (load loadb vdd vss) pll_inv wn=0.4u wp=0.8u ln=1u']
for i in range(7):
 d='fb' if i==0 else f'r{i-1}'
 init='vdd' if i<3 else 's5' if i==3 else 'vss'
 s.append(f'XF{i} ({d} ck ckb load loadb {init} r{i} vdd vss) ring_inv_sync_v14')
s += ['XSI3 (s3 sb3 vdd vss) pll_inv','XSI5 (s5 sb5 vdd vss) pll_inv',
      'XT5 (r4 fb s3 sb3 vdd vss) pll_tg wn=2u wp=4u','XT7 (r6 fb s5 sb5 vdd vss) pll_tg wn=2u wp=4u',
      'RFB (fb vss) resistor r=10Meg','XRI (reset resetb vdd vss) pll_inv']
for i,d in enumerate(['d4','d6','d8','r0','d12','r0']):
 s += [f'XSEB{i} (s{i} resetb eb{i} vdd vss) pll_nand2',f'XSE{i} (eb{i} es{i} vdd vss) pll_inv',
       f'XMX{i} ({d} mux es{i} eb{i} vdd vss) pll_tg wn=1u wp=2u']
s += ['MMUTE (mux reset vss vss) nch w=2u l=180n ad=2u*240n as=2u*240n pd=2*(2u+240n) ps=2*(2u+240n)',
      'RKEEP (mux vss) resistor r=10Meg','XO0 (mux ob vdd vss) pll_inv wn=1u wp=2u','XO1 (ob out vdd vss) pll_inv wn=2u wp=4u',
      'ends cmos_even_bank_tree_v14']
(B/'cmos_even_bank_tree_v14.scs').write_text('\n'.join(s)+'\n')
for p in (H/'tb').glob('bank_m*.scs'):
 s=p.read_text().replace('cmos_even_bank_v14','cmos_even_bank_tree_v14')
 s=s[:s.index('save clk')]+'save clk q1 data reset VDD:p XD.d4 XD.d6 XD.d8 XD.d12 XD.ck XD.ckb XD.load XD.fb XD.XD6.q0 XD.XD6.q1 XD.XD6.d0 XD.mux '+' '.join(f'XD.r{i}' for i in range(7))+'\nsaveOptions options save=selected\n'
 (H/'tb'/p.name.replace('bank_m','banktree_m')).write_text(s)
print('Built staged CMOS bank')
