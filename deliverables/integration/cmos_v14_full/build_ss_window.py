"""Isolate SS storage timing by sweeping external clock slew and duty.

The DUT is a diagnostic hybrid: physical /3 and single-phase /5,/7 storage,
but the clock tree is replaced by a voltage source. Not PLL acceptance.
"""
from pathlib import Path
import json,re
H=Path(__file__).resolve().parent; B=H.parents[1]/'blocks/cmos_v14_full'
name='bank_window_v14'
s=(B/'bank_hybrid_clock_v14.scs').read_text().replace('bank_hybrid_clock_v14',name)
s=s.replace('out fllclk vdd vss)','out fllclk ck vdd vss)')
s=re.sub(r'^X(?:GN|CB1|CB2) .*\n','',s,flags=re.M)
(B/(name+'.scs')).write_text(s)
cases=[]
for m,rf in [(6,3888e6),(10,3120e6),(14,3024e6)]:
 for edge,duty in [(20,.5),(80,.5),(140,.5),(20,.65),(80,.65)]:
  case=f'bankwindow_m{m}_e{edge}_d{round(duty*100)}_ss'; cases.append(case)
  s=(H/'tb'/f'bankrt_m{m}_ss.scs').read_text().replace('cmos_even_bank_acq_v14',name)
  s=s.replace('q1 predata acqclk vdd 0)','q1 predata acqclk ck vdd 0)')
  s=s.replace('stop=100n outputstart=60n','stop=60n')
  s=re.sub(r'^save .*\n','',s,flags=re.M)
  period=2/rf; rise=edge*1e-12
  s+=f'VCK (ck 0) vsource type=pulse val0=0 val1=1.2 period={period:.17g} rise={rise:.17g} fall={rise:.17g} width={period*duty-rise:.17g}\n'
  s+='save clk q1 ck predata data reset VDD:p XD.load XD.r0 XD.r1 XD.r2 XD.r3 XD.r4 XD.r5 XD.r6 XD.d6 XD.XD6.clkb XD.XD6.q0 XD.XD6.q1\n'
  (H/'tb'/(case+'.scs')).write_text(s)
(H/'results/ss_window_protocol.json').write_text(json.dumps(dict(scope=__doc__,cases=cases,corner='SS60/1.2V',rf_mhz={6:3888,10:3120,14:3024},duration_ns=60,evaluation_ns=[20,60],precision='1ps/reltol1e-5'),indent=2)+'\n')
print(' '.join(cases))
