"""Fresh PSS/Pnoise refinement: 1 ps, 127 sidebands and lower numerical gmin.

The original run did not produce the requested writepss binary, so this check
restarts from the same tiny initial voltage seed. No unchecked state is reused.
"""
from analyze import H,R
import json,re

p=R/'r2_loaded_noise/r2_noise_divider'
r=json.loads((p/'result.json').read_text());assert r['ok'] and r['remote_inputs_match']
s=(p/'inputs/r2_noise_divider.scs').read_text()
s=s.replace('gmin=1n','gmin=1p')
s=s.replace('maxstep=2p','maxstep=1p').replace('maxsideband=63','maxsideband=127')
s=s.replace('start=10k stop=500M dec=20','start=100k stop=10M dec=1')
s=re.sub(r' writepss="[^"]+"','',s)
(H/'tb/r2_noise_divider_refined.scs').write_text(s)
(H/'results/loaded_noise_refinement_input.json').write_text(json.dumps(dict(source_run='r2_loaded_noise',source_case='r2_noise_divider',initial_state='Fresh independent PSS from 10 uV differential seed; no readpss',gmin_s=1e-12,maxstep_s=1e-12,maxsideband=127),indent=2)+'\n')
print('Fresh loaded noise refinement prepared')
