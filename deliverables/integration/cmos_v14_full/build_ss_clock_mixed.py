"""Keep measured pulse restoration in first3 buffers, restore final2 balance.

Full5-stage skew restored intermediate swings but overextended CB high to
417ps/514ps, starving final CK high pulse. Hold all stage input-width sums
unchanged and restore only CT3/CT4 to10/20 and24/48um respectively.
"""
from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
src=B/'bank_skewbuf_v14.scs';s=src.read_text().replace('bank_skewbuf_v14','bank_mixskew_v14')
for old,new in [('XCT3 (ct2 cb vdd vss) pll_inv wn=5u wp=25u','XCT3 (ct2 cb vdd vss) pll_inv wn=10u wp=20u'),('XCT4 (cb ck vdd vss) pll_inv wn=36u wp=36u','XCT4 (cb ck vdd vss) pll_inv wn=24u wp=48u')]:
 assert s.count(old)==1;s=s.replace(old,new)
(B/'bank_mixskew_v14.scs').write_text(s)
cases=[]
for m in [6,4,10]:
 case=f'bankmixskew_m{m}_ss';cases.append(case)
 tb=(H/'tb'/f'banktap6_m{m}_ss.scs').read_text().replace('bank_tap6_v14','bank_mixskew_v14')
 tb+='save XD.ct0 XD.ct1 XD.ct2\n';(H/'tb'/(case+'.scs')).write_text(tb)
(H/'results/ss_clock_mixed_protocol.json').write_text(json.dumps(dict(scope=__doc__,cases=cases,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),adopted_in_full_pll=False),indent=2)+'\n')
print(' '.join(cases))
