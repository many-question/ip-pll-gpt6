"""First loaded-VCO low-range candidate, without changing the complete PLL.

Increase only the switched capacitor unit from 4.4 fF to 4.8 fF. Keep its MOS
switch sizes, bias, provisional Q5 RLC and actual interface load. External
coarse/control clamps exclude FLL and control-output impedance/noise.
"""
from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;cases=[];sources={}
for corner in ['ss','tt','ff']:
 for code,ctrl in [(255,'02'),(0,'10')]:
  src=H/'tb'/f'range_c{code}_v{ctrl}_{corner}.scs';s=src.read_text()
  old=') lc_vco_physical_v14 bias_r=2500';assert s.count(old)==1
  s=s.replace(old,old+' unit_c=4.8f')
  case=f'range48_c{code}_v{ctrl}_{corner}';cases.append(case)
  (H/'tb'/(case+'.scs')).write_text(s)
  sources[src.name]=hashlib.sha256(src.read_bytes()).hexdigest()
(H/'results/range_extension_protocol.json').write_text(json.dumps(dict(scope=__doc__,cases=cases,source_tb_sha256=sources,target_rf_mhz=[2688,3936],condition='TT27/SS60/FF0,1.2V,400ns/last60ns,1ps/reltol1e-5,10fF; original bank retained; endpoint oscillator frequency does not establish PLL lock.'),indent=2)+'\n')
print(' '.join(cases))
