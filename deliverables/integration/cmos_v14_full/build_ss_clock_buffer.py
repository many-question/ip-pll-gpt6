"""Controlled CMOS clock restoration after the actual SS RF receiver.

Keep receiver feedback at its original output; sharpen the clock with two
static inverter stages. Extend runs to separate startup from steady behavior.
No full PLL adoption and no jitter claim.
"""
from pathlib import Path
H=Path(__file__).resolve().parent
cases=[]
for label,sizes in [('base',None),('boost',None),('bufsmall',[(4,10),(8,20)]),('buflarge',[(8,20),(16,40)])]:
 for m in ([4] if sizes is None else [4,6,10]):
  kind='base' if label=='base' else 'boost';case=f'bankck{label}_m{m}_ss';cases.append(case)
  s=(H/'tb'/f'banksswave{kind}_m{m}_ss.scs').read_text().replace('stop=60n outputstart=20n','stop=200n outputstart=120n')
  if sizes:
   s=s.replace('XRX (vp clk vdd 0)','XRX (vp rxclk vdd 0)')
   (n1,p1),(n2,p2)=sizes
   s+=f'XCK0 (rxclk ckb vdd 0) pll_inv wn={n1}u wp={p1}u\nXCK1 (ckb clk vdd 0) pll_inv wn={n2}u wp={p2}u\nsave rxclk ckb\n'
  s+='save XRX.g0 XD.XPRE.a XD.XPRE.b XD.XPRE.dn\n'
  (H/'tb'/(case+'.scs')).write_text(s)
print(' '.join(cases))
