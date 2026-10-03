"""Strengthen the dynamic prescaler output, preserving its input buffer load.

Prior buffer-only trials distorted the extracted short pulse. This experiment
changes only the final TSPC drive devices and optionally its existing data-N
delay resistor. The tail-isolated CMOS bank still supplies every internal clock.
"""
from pathlib import Path
import re
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full';OLD=B.parent/'cmos_v14'
for rd in [50,75]:
 cell=f'ff_drive2_r{rd}_v14'
 s=(OLD/'ff_fbdelay50_v14.scs').read_text().replace('ff_fbdelay50_v14',cell)
 for device,old,new in [('MP2','2.0u','4.0u'),('MNC2','1.6u','3.2u'),('MN2','1.6u','3.2u')]:
  s=re.sub(r'^'+device+r' .*$',lambda m:m[0].replace(old,new),s,flags=re.M)
 s=s.replace('r=50000',f'r={rd*1000}')
 (B/(cell+'.scs')).write_text(s)
 name=f'bank_preboost{rd}_v14'
 s=(B/'bank_tail_shape_v14.scs').read_text().replace('bank_tail_shape_v14',name).replace('ff_fbdelay50_v14',cell)
 (B/(name+'.scs')).write_text(s)
 for m in [6,10,14]:
  tb=(H/'tb'/f'banktailshape_m{m}_ss.scs').read_text().replace('bank_tail_shape_v14',name)
  tb+='save XD.q0 XD.qb0 XD.XPRE.dn XD.XPRE.a XD.XPRE.b\n'
  (H/'tb'/f'bankpreboost{rd}_m{m}_ss.scs').write_text(tb)
print('Two output-drive variants prepared; input buffer and clock-tree loads unchanged.')
