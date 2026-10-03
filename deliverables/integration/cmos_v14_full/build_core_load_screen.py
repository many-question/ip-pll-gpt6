"""Diagnostic reference-load sensitivity, not an accepted physical noise model.

The reduced core has ~60ps reference edges versus ~200ps in the complete DUT.
Bracket an equivalent load to test this boundary change before another PSS run.
Ideal added capacitance cannot replace slow-logic noise in final acceptance.
"""
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
s=(B/'pll_noise_core_v14.scs').read_text().replace('pll_noise_core_v14','pll_noise_loadprobe_v14')
s=s.replace('rlf=100k','rlf=100k ref_load=0',1).replace('CR (refb vss) capacitor c=60f','CR (refb vss) capacitor c=60f\nCREFLOAD (refb vss) capacitor c=ref_load')
(B/'pll_noise_loadprobe_v14.scs').write_text(s)
cases=[]
for cap in [2,5,10]:
 case=f'core_load{cap}p_tt';cases.append(case)
 s=(H/'tb/core_preflight_tt.scs').read_text().replace('pll_noise_core_v14','pll_noise_loadprobe_v14')
 s=s.replace('XP (ref out vdd 0) pll_noise_loadprobe_v14',f'XP (ref out vdd 0) pll_noise_loadprobe_v14 ref_load={cap}p')
 s=s.replace('stop=1u','stop=300n')
 (H/'tb'/(case+'.scs')).write_text(s)
print(' '.join(cases))
