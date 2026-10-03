"""Screen real-LC candidate stationarity before attempting periodic noise."""
from pathlib import Path
import hashlib
import json
import numpy as np
from analyze import loop

H=Path(__file__).resolve().parent; ROOT=H.parents[3]
j=ROOT/'research/runs/spectre_cmos_v14_full/coretripsettle01/core_pulsetrip_settle_tt'
if not (j/'result.json').exists(): print('pending'); raise SystemExit(0)
r=json.loads((j/'result.json').read_text())
if not r.get('local_outputs_sha256'): print('collection incomplete'); raise SystemExit(0)
assert r['ok'] and r['remote_inputs_match'] and 'spectre completes with 0 errors' in (j/'spectre.out').read_text()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
with np.load(j/'waveforms.npz') as z: d={k:z[k] for k in z.files}
assert abs(d['time'][-1]-3e-6)<1e-12
v=loop(d)
bits={f'b{i}':[float(min(d[f'XP.b{i}'])),float(max(d[f'XP.b{i}']))] for i in range(8)}
stable=all((lo>.6 if (23>>i)&1 else hi<.6) for i,(lo,hi) in enumerate(bits.values()))
out=dict(scope=__doc__,source_result=(j/'result.json').relative_to(ROOT).as_posix(),
         source_sha256=sha(j/'result.json'),stationarity=v,coarse_ranges=bits,coarse23_held=stable,
         preflight_passed=bool(v['passed'] and stable),full_pll_acceptance=False,
         boundary='Real LC Q5 and sampled loop, continuous-clock divider candidate; static slow-control boundary. Analog-state text seed; not native continuation, cold start or jitter validation.',
         pending='Fresh PSS, dense periodic-node checks, noise; physical main PLL unchanged.')
(H/'results/core_pulsetrip_settle_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
