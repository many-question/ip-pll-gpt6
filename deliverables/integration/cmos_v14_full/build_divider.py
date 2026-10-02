"""Physical V14 prescaler plus resettable CMOS ring divide-by-N bank."""
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
lines=['simulator lang=spectre','include "ff_fbdelay50_v14.scs"',
 '// Shared RF /2 retains V14 first stage; downstream rings run at RF/2.',
 '// Ring initial patterns rotate. Odd N has non-50% duty; no duty correction.',
 'subckt cmos_even_bank_v14 (clk reset s0 s1 s2 s3 s4 s5 q1 out vdd vss)',
 'XPRE (q0 clk q0 vdd vss) ff_fbdelay50_v14',
 'XPB0 (q0 qb0 vdd vss) pll_inv wn=0.8u wp=0.5u',
 'XPB1 (qb0 q1 vdd vss) pll_inv wn=2u wp=4u',
 'XCB0 (q1 ckbn vdd vss) pll_inv wn=2u wp=4u',
 'XCB1 (ckbn ckbank vdd vss) pll_inv wn=8u wp=16u',
 'XCI (ckbank ckb vdd vss) pll_inv wn=4u wp=10u']
for k,n in enumerate(range(2,8)):
 lines += [f'XSI{k} (s{k} ns{k} vdd vss) pll_inv',f'XRS{k} (reset ns{k} rst{k} vdd vss) tx_or',
           f'XSE{k} (s{k} ckb ckbank safe{k} vdd vss) pll_latch',
           f'XGC{k} (ckbank safe{k} ck{k} vdd vss) tx_and']
 for i in range(n):
  init=1 if i<(n+1)//2 else 0
  lines.append(f'XF{k}_{i} (r{k}_{(i-1)%n} ck{k} rst{k} r{k}_{i} vdd vss) tx_dff_r{init}')
 lines.append(f'XSEL{k} (r{k}_0 s{k} o{k} vdd vss) tx_and')
for k in range(1,6):lines.append(f'XOR{k} ({"o0" if k==1 else "or"+str(k-1)} o{k} or{k} vdd vss) tx_or')
lines += ['XRSTI (reset resetb vdd vss) pll_inv','XMUTE (or5 resetb out vdd vss) tx_and','ends cmos_even_bank_v14']
(B/'cmos_even_bank_v14.scs').write_text('\n'.join(lines)+'\n')
model='/home/process/tsmc180bcd_gen2_2022/PDK/TSMC180BCD/models/spectre/c018bcd_gen2_v1d6.scs'
for corner,temp in [('tt',27),('ss',60),('ff',0)]:
 for k,(m,f) in enumerate([(4,3936e6),(6,3888e6),(8,3456e6),(10,3120e6),(12,3168e6),(14,3024e6)]):
  s=[f'simulator lang=spectre\nglobal 0\ninclude "{model}" section={corner}',f'include "{model}" section=stat_noise','simulator lang=spectre insensitive=no','include "cells.scs"','include "digital_cells_v2.scs"','include "cmos_even_bank_v14.scs"',f'simulatorOptions options temp={temp} reltol=1e-5 vabstol=1e-7 iabstol=1e-13',
     'VDD (vdd 0) vsource dc=1.2',f'VCLK (clk 0) vsource type=pulse val0=0 val1=1.2 period={1/f:.16g} width={.5/f-20e-12:.16g} rise=20p fall=20p',
     'VRST (reset 0) vsource type=pwl wave=[0 1.2 8n 1.2 8.01n 0]']
  for j in range(6):s.append(f'VS{j} (s{j} 0) vsource dc={1.2 if j==k else 0}')
  s+=['XD (clk reset s0 s1 s2 s3 s4 s5 q1 data vdd 0) cmos_even_bank_v14','CL (data 0) capacitor c=10f',
      'tran tran stop=100n outputstart=60n maxstep=1p method=traponly errpreset=conservative','save clk q1 data reset VDD:p XD.ckbank XD.ck'+str(k)+' '+' '.join(f'XD.r{k}_{i}' for i in range(m//2)),'saveOptions options save=selected']
  (H/'tb'/f'bank_m{m}_{corner}.scs').write_text('\n'.join(s)+'\n')
print('Built bank and18 TBs')
