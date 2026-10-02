"""Single-clock TSPC register ring: isolate clock duty/skew from ring function."""
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
def mos(n,t,d,g,s,b,w):
 return f'{n} ({d} {g} {s} {b}) {t} w={w} l=180n ad={w}*240n as={w}*240n pd=2*({w}+240n) ps=2*({w}+240n)'
s=['simulator lang=spectre']
for init in [0,1]:
 s += [f'subckt ring_tspc_r{init}_v14 (d clk reset resetb q vdd vss)',
       'XF (d clk qb vdd vss) pll_tspc_inv',
       'XO (qb q vdd vss) pll_inv wn=1u wp=2.5u',
       mos('MR','nch' if init else 'pch','qb','reset' if init else 'resetb','vss' if init else 'vdd','vss' if init else 'vdd','1.6u' if init else '3.2u'),
       # Weak static keeper on the floating slave output.
       'XK (q qb vdd vss) pll_inv wn=0.4u wp=0.8u ln=1u',
       f'ends ring_tspc_r{init}_v14']
(B/'ring_tspc_v14.scs').write_text('\n'.join(s)+'\n')
for c in ['tt','ss']:
 s=(H/'tb'/f'ringstart_{c}.scs').read_text().replace('ring_c2_v14.scs','ring_tspc_v14.scs').replace('ring_c2_r','ring_tspc_r')
 s=s.replace('clk clkb rst rstb','clk rst rstb')
 s=s.replace('period=666.6666666667p width=313.3333333333p','period=514.4032921811p width=288.6419753087p')
 s=s.replace('save clk clkb rst q0 q1 q2 X0.qb X1.qb X2.qb','save clk rst q0 q1 q2 X0.qb X1.qb X2.qb')
 (H/'tb'/f'ringtspc_{c}.scs').write_text(s)
print('Built TSPC ring unit tests at1.944GHz,60% input duty')
