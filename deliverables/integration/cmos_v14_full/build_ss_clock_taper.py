"""Move mode gating to a lightly loaded first stage and taper the clock drive.

The restored prescaler gives full-swing q1 in SS, but the old CI->8/8 NAND
chain suppresses its short low pulse (GN remains above0.77V). Test a direct
NAND followed by3 or5 inverters. The selected clock has the same polarity;
the unselected clock now parks low. Reset enables the clock for initialization.
Mode/reset behavior and all modes still need regression before full adoption.
"""
from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full';cases=[]
src=B/'bank_origpre_v14.scs';s=src.read_text()
old='\n'.join(x for x in s.splitlines() if x.startswith(('XCI ','XGN ','XCB1 ','XCB2 ')))
assert len(old.splitlines())==4
for tag,sizes in [('tap4',[(3,6),(8,16),(24,48)]),('tap6',[(.8,1.6),(1.6,3.2),(4,8),(10,20),(24,48)])]:
 name=f'bank_{tag}_v14';lines=['XGN (q1 run gn vdd vss) pll_nand2 wn=2u wp=2u'];prev='gn'
 for i,(n,p) in enumerate(sizes):
  out='ck' if i==len(sizes)-1 else ('cb' if i==len(sizes)-2 else f'ct{i}')
  lines.append(f'XCT{i} ({prev} {out} vdd vss) pll_inv wn={n:g}u wp={p:g}u');prev=out
 body=s.replace('bank_origpre_v14',name).replace(old,'\n'.join(lines));(B/(name+'.scs')).write_text(body)
 for m in [6,4,10]:
  case=f'bank{tag}_m{m}_ss';cases.append(case)
  tb=(H/'tb'/f'bankssorig_m{m}_ss.scs').read_text().replace('bank_origpre_v14',name)
  (H/'tb'/(case+'.scs')).write_text(tb)
(H/'results/ss_clock_taper_protocol.json').write_text(json.dumps(dict(scope=__doc__,cases=cases,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),run='banktaper02',adopted_in_full_pll=False),indent=2)+'\n')
print(' '.join(cases))
