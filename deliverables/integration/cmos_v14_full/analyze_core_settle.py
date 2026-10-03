"""Check stationary phase before PSS; this is not a jitter measurement."""
from pathlib import Path
import json,hashlib
import numpy as np
from analyze import loop
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
j=ROOT/'research/runs/spectre_cmos_v14_full/coressettle01/core_register_settle_tt'
if not (j/'result.json').exists():print('pending');raise SystemExit(0)
r=json.loads((j/'result.json').read_text())
assert r['remote_inputs_match'] and r['ok'] and 'spectre completes with 0 errors' in (j/'spectre.out').read_text()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files}
v=loop(d);bits={f'b{i}':[float(min(d[f'XP.b{i}'])),float(max(d[f'XP.b{i}']))] for i in range(8)}
stable=all((min(d[f'XP.b{i}'])>.6 if (23>>i)&1 else max(d[f'XP.b{i}'])<.6) for i in range(8))
out=dict(source_result=(j/'result.json').relative_to(ROOT).as_posix(),source_sha256=sha(j/'result.json'),stationarity=v,coarse_ranges=bits,coarse23_held=stable,preflight_passed=bool(v['passed'] and stable),full_pll_jitter_fs=None,scope='Same-core text terminal restart, not native continuous trajectory. Stationarity screen only; fullDUT equivalence and periodic/noise validation remain.')
(H/'results/core_settle_validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
