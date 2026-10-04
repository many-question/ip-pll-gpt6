"""Check CF40's own-state warm extension with the unchanged stationarity gate."""
from pathlib import Path
import hashlib,json
import numpy as np
from analyze import loop
H=Path(__file__).resolve().parent;ROOT=H.parents[3];p=json.loads((H/'results/core_cf40_settle_protocol.json').read_text())
j=ROOT/'research/runs/spectre_cmos_v14_full'/p['run']/p['case'];rp=j/'result.json';sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
if not rp.exists():print('pending');raise SystemExit(0)
r=json.loads(rp.read_text())
if not r.get('local_outputs_sha256'):print('collection incomplete');raise SystemExit(0)
assert r['ok'] and r['remote_inputs_match'] and 'spectre completes with 0 errors' in (j/'spectre.out').read_text()
source=json.loads((ROOT/p['source_result']).read_text())
exclude=['core_noisecand_cf40_tt.scs','core_cf40_settle6_tt.scs','core_pulsetrip_supply_seed_tt.ic','core_cf40_own_seed_tt.ic']
assert {k:v for k,v in r['inputs_sha256'].items() if k not in exclude}=={k:v for k,v in source['inputs_sha256'].items() if k not in exclude}
assert r['inputs_sha256']['core_cf40_own_seed_tt.ic']==p['seed_sha256'] and sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files}
t=d['time'];assert abs(t[-1]-6e-6)<1e-12
windows=[]
for end_us in range(1,7):
    part={k:v[t<=end_us*1e-6+1e-15] for k,v in d.items() if v.ndim==1 and len(v)==len(t)};windows.append(loop(part))
coarse=all(np.all(d[f'XP.b{i}']>.9) if 23&(1<<i) else np.all(d[f'XP.b{i}']<.3) for i in range(8))
supplies={k:[float(min(d[k])),float(max(d[k]))] for k in ['XP.vco_vdd','XP.rx_vdd','XP.rt_vdd']};good=all(abs(lo-1.2)<1e-9 and abs(hi-1.2)<1e-9 for lo,hi in supplies.values())
ix=t>5e-6;bias=d['XP.XV.XL.nfilt'][ix]
out=dict(scope=__doc__,source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),source_protocol_sha256=sha(H/'results/core_cf40_settle_protocol.json'),
    windows=windows,coarse23_held=bool(coarse),supply_ranges_v=supplies,bias_last1us_range_v=[float(min(bias)),float(max(bias))],
    bias_last1us_drift_v_per_us=float(np.polyfit((t[ix]-t[ix][0])*1e6,bias,1)[0]),
    preflight_passed=bool(windows[-1]['passed'] and coarse and good),full_pll_acceptance=False,random_jitter_measured=False,
    interpretation='Functional warm stationarity only; no PSS, lowfrequency noise or completePLL acceptance.')
(H/'results/core_cf40_settle_validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
