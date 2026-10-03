"""Measure extracted bias gate charging, not oscillator/PLL power-up."""
from pathlib import Path
import json,hashlib
import numpy as np
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
j=ROOT/'research/runs/spectre_cmos_v14_full/vcobiasstart01/vco_bias_gate_start_tt'
if not (j/'result.json').exists(): print('pending');raise SystemExit(0)
r=json.loads((j/'result.json').read_text())
if not r.get('local_outputs_sha256'):print('collection incomplete');raise SystemExit(0)
assert r['ok'] and r['remote_inputs_match'] and 'spectre completes with 0 errors' in (j/'spectre.out').read_text()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files}
t=d['time'];assert t[0]==0 and abs(t[-1]-400e-6)<1e-12
rows=[]
for cap in [10,40]:
    y=d[f'X{cap}.nfilt'];nb=d[f'X{cap}.nb'];end=float(y[-1]);last=t>t[-1]-1e-6
    assert abs(y[0])<1e-6 and .2<end<1 and np.ptp(y[last])<1e-4
    times={}
    for frac in [.9,.99,.999]:
        i=np.flatnonzero((y[:-1]<end*frac)&(y[1:]>=end*frac))[0]
        times[str(frac)]=float((t[i]+(end*frac-y[i])/(y[i+1]-y[i])*(t[i+1]-t[i])-110e-9)*1e6)
    rows.append(dict(filter_pf=cap,nfilt_final_v=end,nb_final_v=float(nb[-1]),gate_charge_time_after_ramp_us=times,
                     final_1us_gate_drift_v=float(np.ptp(y[last]))))
out=dict(scope=__doc__,source_result=(j/'result.json').relative_to(ROOT).as_posix(),source_sha256=sha(j/'result.json'),
         cases=rows,full_pll_acceptance=False,oscillator_startup_verified=False,
         limitation='Static tail clamp replaces RF drain waveform. Times are relative to each400us terminal gate level; not a lock-time or oscillator-startup result.')
(H/'results/vco_bias_startup_validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
