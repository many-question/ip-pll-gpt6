"""Restore prescaler logic levels under the measured SS RF waveform.

Only XPB0 NMOS width varies. Keep its PMOS, the prescaler, the clock tree,
RF feedback and quiet acquisition-counter load unchanged. Candidates are
separate files and are not substituted into the complete PLL.
"""
from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
base=B/'bank_preboost50_v14.scs';cases=[]
for label,wn in [('n12',1.2),('n20',2),('n30',3)]:
 name='bank_level_'+label+'_v14'
 body=base.read_text().replace('bank_preboost50_v14',name)
 old='XPB0 (q0 qb0 vdd vss) pll_inv wn=0.8u wp=0.5u'
 assert body.count(old)==1
 body=body.replace(old,f'XPB0 (q0 qb0 vdd vss) pll_inv wn={wn:g}u wp=0.5u')
 (B/(name+'.scs')).write_text(body)
 for m in [4,6]:
  case=f'banklevel{label}_m{m}_ss';cases.append(case)
  s=(H/'tb'/f'banksswaveboost_m{m}_ss.scs').read_text().replace('bank_preboost50_v14',name)
  s=s.replace('stop=60n outputstart=20n','stop=200n outputstart=120n')
  s+='save XRX.g0 XD.XPRE.a XD.XPRE.b XD.XPRE.dn XD.XD4.a XD.XD4.b XD.d4b\n'
  (H/'tb'/(case+'.scs')).write_text(s)
(H/'results/ss_level_protocol.json').write_text(json.dumps(dict(cases=cases,base_sha256=hashlib.sha256(base.read_bytes()).hexdigest(),scope=__doc__,run='banklevel01'),indent=2)+'\n')
print(' '.join(cases))
