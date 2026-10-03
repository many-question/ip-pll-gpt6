"""Preserve a narrow clock pulse by redistributing NMOS/PMOS widths.

Keep each inverter's total input gate width fixed, strengthening the device
that propagates the short GN-high pulse through successive polarities. This
isolates rise/fall drive balance from gross upstream gate-capacitance increase.
Variant B also redistributes the first NAND's fixed total input width2+2 to1+3.
These are SS diagnostic candidates, including their changed clock-park level.
"""
from pathlib import Path
import json,re,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full';src=B/'bank_tap6_v14.scs';cases=[]
sizes=[(1.2,1.2),(.8,4),(6,6),(5,25),(36,36)]
for tag,gate in [('skewbuf',False),('skewgate',True)]:
 name='bank_'+tag+'_v14';s=src.read_text().replace('bank_tap6_v14',name)
 for i,(n,p) in enumerate(sizes):
  pat=r'^(XCT'+str(i)+r' .*pll_inv) wn=\S+ wp=\S+$'
  s,count=re.subn(pat,lambda m:m[1]+f' wn={n:g}u wp={p:g}u',s,flags=re.M);assert count==1
 if gate:s=s.replace('XGN (q1 run gn vdd vss) pll_nand2 wn=2u wp=2u','XGN (q1 run gn vdd vss) pll_nand2 wn=1u wp=3u')
 (B/(name+'.scs')).write_text(s)
 case=f'bank{tag}_m6_ss';cases.append(case)
 tb=(H/'tb/banktap6_m6_ss.scs').read_text().replace('bank_tap6_v14',name)
 tb+='save XD.ct0 XD.ct1 XD.ct2\n';(H/'tb'/(case+'.scs')).write_text(tb)
(H/'results/ss_clock_skew_protocol.json').write_text(json.dumps(dict(scope=__doc__,cases=cases,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),adopted_in_full_pll=False),indent=2)+'\n')
print(' '.join(cases))
