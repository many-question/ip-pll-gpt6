"""Retest original dynamic stage with SS waveform and sufficient settling.

Earlier restoration used a TT waveform and only60ns, so its failures cannot
exclude this topology under the corrected SS stimulus and120ns settling.
"""
from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full';cases=[]
for m in [4,6,10]:
 case=f'bankssorig_m{m}_ss';cases.append(case)
 s=(H/'tb'/f'banksswaveboost_m{m}_ss.scs').read_text().replace('bank_preboost50_v14','bank_origpre_v14')
 s=s.replace('stop=60n outputstart=20n','stop=200n outputstart=120n')
 s+='save XRX.g0 XD.XPRE.a XD.XPRE.b XD.XPRE.dn XD.XD4.a XD.XD4.b XD.d4b\n'
 (H/'tb'/(case+'.scs')).write_text(s)
(H/'results/ss_settled_restore_protocol.json').write_text(json.dumps(dict(scope=__doc__,cases=cases,source_bank_sha256=hashlib.sha256((B/'bank_origpre_v14.scs').read_bytes()).hexdigest()),indent=2)+'\n')
print(' '.join(cases))
