"""Compact summary; simulation success and functional acceptance stay separate."""
from pathlib import Path
import json,sys,re
H=Path(__file__).resolve().parent
pattern=sys.argv[1] if len(sys.argv)>1 else '.'
for r in json.loads((H/'results/validation.json').read_text()):
    if not re.search(pattern,r['case']):continue
    w=r.get('wave',{});s=w.get('signals',{})
    print(r['case'],r['sim_ok'],w.get('pass_function'),
          ' '.join(f"{k}:{v['frequency_hz']/1e6:.2f}MHz/{v['range_v'][0]:.3f}..{v['range_v'][1]:.3f}V" for k,v in s.items() if k!='rf'),
          'P',round(w.get('power_mw',{}).get('VDD:p',0),4))
