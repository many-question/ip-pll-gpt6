"""Check the same-code fine-control bracket, without extrapolation or noise claims."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from noise_utils import cross
from reference_modulation_utils import fit_edges
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((H/'results/rt4_code24_tuning_protocol.json').read_text());j=ROOT/'research/runs/spectre_cmos_v14_full'/p['run']/p['case'];rp=j/'result.json'
if not rp.exists():print('pending');raise SystemExit(0)
r=json.loads(rp.read_text())
if not r.get('local_outputs_sha256'):print('collection incomplete');raise SystemExit(0)
assert r['ok'] and r['remote_inputs_match'] and 'spectre completes with 0 errors' in (j/'spectre.out').read_text()
assert sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
oldp=ROOT/p['baseline_result'];assert sha(oldp)==p['baseline_result_sha256'];old=json.loads(oldp.read_text())
excluded={p['case']+'.scs','rt4program_c24_tt.scs',p['case']+'.ic','rt4load_nominal_tt.ic'}
assert {k:v for k,v in old['inputs_sha256'].items() if k not in excluded}=={k:v for k,v in r['inputs_sha256'].items() if k not in excluded}
assert r['inputs_sha256'][p['case']+'.ic']==p['seed_sha256']
with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files}
t=d['time'];assert abs(t[0]-250e-9)<1e-14 and abs(t[-1]-750e-9)<1e-14
e=cross(t,d['XP.vp']-d['XP.vn'],0);rf=fit_edges(e);of=fit_edges(cross(t,d['out']))
fs=[]
for lo,hi in [(250e-9,500e-9),(500e-9,750e-9)]:
    a=e[(e>=lo)&(e<hi)];fs.append(float(1/np.mean(np.diff(a))))
drift=abs(fs[1]-fs[0])/np.mean(fs)*1e6;clamp=float(max(abs(d['XP.ctrl']-p['control_v'])))
held=all(np.all(d[f'XP.b{i}']>.9) if 24&(1<<i) else np.all(d[f'XP.b{i}']<.3) for i in range(8))
ratio=float(abs(of['carrier_hz']*4/rf['carrier_hz']-1));limits=p['limits']
valid=bool(held and clamp<limits['clamp_error_v'] and drift<limits['window_rf_drift_ppm'] and ratio<limits['divider_relative'])
v=json.loads((H/'results/rt4_coarse_program_validation.json').read_text());assert sha(H/'results/rt4_coarse_program_validation.json')==p['source_validation_sha256']
base=next(x for x in v['cases'] if x['coarse_code']==24)
base_tb=(oldp.parent/'inputs/rt4program_c24_tt.scs').read_text();base_v=float(re.search(r'^VCTRL .*dc=(\S+)',base_tb,re.M)[1])
f0=base['rf_fit']['carrier_hz'];f1=rf['carrier_hz'];bracket=bool(valid and f0<=p['target_rf_hz']<=f1)
out=dict(scope=__doc__,source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),valid=valid,
    control_v=p['control_v'],coarse_held=bool(held),window_rf_drift_ppm=float(drift),clamp_error_v=clamp,divider_relative_error=ratio,
    rf_fit=rf,output_fit=of,rf_swing_pp_v=float(np.ptp(d['XP.vp']-d['XP.vn'])),
    final_c1_minus_control_v=float(d['XP.vc1'][-1]-d['XP.ctrl'][-1]),
    curve=dict(control_v=[base_v,p['control_v']],rf_hz=[f0,f1],target_bracketed=bracket,
        interpolated_control_v=float(base_v+(p['target_rf_hz']-f0)/(f1-f0)*(p['control_v']-base_v)) if bracket else None),
    random_jitter_measured=False,full_pll_acceptance=False,
    interpretation='Clamped same-code frequency only. Any interpolation must be measured, and loop-filter memory must settle physically before release.')
(H/'results/rt4_code24_tuning_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['rf_fit','output_fit']},indent=2))
