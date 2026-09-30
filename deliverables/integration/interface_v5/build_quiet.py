"""Second experiment: isolate decoupling and lower sampler bias resistance."""
from pathlib import Path
import re
H=Path(__file__).resolve().parent
for label,rb in [('quiet100','100k'),('quiet10','10k')]:
 for kind in ['noise','timing']:
  s=(H/'tb'/f'{kind}_both.scs').read_text()
  s=s.replace('resistor r=1Meg',f'resistor r={rb}')
  s=s.replace(') tx_divider_bank_v5',') tx_divider_bank_v5 rb_input=50k rb_clock=50k cdec=10p')
  (H/'tb'/f'{kind}_{label}.scs').write_text(s)
print('Built quiet100 (decoupling only) and quiet10 (decoupling + lower sampler R)')
