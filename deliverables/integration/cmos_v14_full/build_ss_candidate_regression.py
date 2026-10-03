"""Build six-mode/three-paired-corner regression for a separate CMOS candidate."""
from pathlib import Path
import json,re
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
candidate='bank_preboost50_v14';cases=[]
for c in ['ss','tt','ff']:
 for m in [4,6,8,10,12,14]:
  case=f'bankboostreg_m{m}_{c}';cases.append(case)
  s=(H/'tb'/f'bankrt_m{m}_{c}.scs').read_text().replace('cmos_even_bank_acq_v14',candidate)
  s=s.replace('XD.ck XD.ckb','XD.ck XD.gn XD.cb')
  s+='save XD.q0 XD.qb0\n'
  (H/'tb'/(case+'.scs')).write_text(s)
(H/'results/ss_candidate_regression_protocol.json').write_text(json.dumps(dict(candidate=candidate,cases=cases,scope='Independent bank plus retimer/10fF; physical internal clocks, ideal20ps RF.1.2V,TT27/SS60/FF0,each mode at its planned maximum RF.100ns,last40ns;maxstep1ps/reltol1e-5. Does not prove PLL capture, noise, fullPVT or other channel frequencies.',adopted_in_pll=False),indent=2)+'\n')
print(' '.join(cases))
