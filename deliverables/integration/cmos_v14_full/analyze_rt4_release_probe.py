"""Measure actual warm RT4 closed-loop capture after the external clamp is removed."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from noise_utils import cross
from reference_modulation_utils import fit_edges
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((H/'results/rt4_release_protocol.json').read_text())
j=ROOT/'research/runs/spectre_cmos_v14_full'/p['run']/p['case'];rp=j/'result.json'
if not rp.exists():print('pending');raise SystemExit(0)
r=json.loads(rp.read_text())
if not r.get('local_outputs_sha256'):print('collection incomplete');raise SystemExit(0)
assert r['ok'] and r['remote_inputs_match'] and 'spectre completes with 0 errors' in (j/'spectre.out').read_text()
source=ROOT/p['source_result'];old=json.loads(source.read_text());assert sha(source)==p['source_result_sha256']
ex={j.name+'.scs',j.name+'.ic',source.parent.name+'.scs',source.parent.name+'.ic'}
assert {k:v for k,v in r['inputs_sha256'].items() if k not in ex}=={k:v for k,v in old['inputs_sha256'].items() if k not in ex}
assert r['inputs_sha256'][j.name+'.ic']==p['seed_sha256']
assert sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
body=(j/'inputs'/(j.name+'.scs')).read_text();assert 'VCTRL' not in body and 'lc_loop_observer' not in body
with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files}
t=d['time'];assert abs(t[0]-2e-6)<1e-14 and abs(t[-1]-3e-6)<1e-14
rf=cross(t,d['XP.vp']-d['XP.vn'],0);oe=cross(t,d['out']);ref=cross(t,d['XP.refb'])
def phases_at(edges,refs):
    i=np.searchsorted(edges,refs,side='right')-1
    ok=(i>=1)&(i<len(edges));i=i[ok];refs=refs[ok]
    phases=i+(refs-edges[i])/(edges[i]-edges[i-1])
    return refs,phases
tr,cycles=phases_at(rf,ref);to,oc=phases_at(oe,ref)
assert len(tr)>=20 and np.array_equal(tr,to)
phase=np.unwrap(2*np.pi*np.remainder(cycles,1.));drift=float(np.polyfit((tr-tr[0])*1e6,phase,1)[0])
lim=p['limits'];rfe=float(max(abs(np.diff(cycles)-164)));oute=float(max(abs(np.diff(oc)-41)))
held=all(np.all(d[f'XP.b{i}']>.9) if 24&(1<<i) else np.all(d[f'XP.b{i}']<.3) for i in range(8))
cr=[float(min(d['XP.ctrl'])),float(max(d['XP.ctrl']))]
passed=bool(np.ptp(phase)<lim['phase_pp_rad'] and abs(drift)<lim['phase_drift_rad_per_us'] and rfe<lim['rf_cycles_error'] and oute<lim['out_cycles_error'] and lim['control_v'][0]<=cr[0]<=cr[1]<=lim['control_v'][1] and held)
out=dict(scope=__doc__,source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),
    clamp_released=True,coarse24_held=bool(held),phase_pp_rad=float(np.ptp(phase)),phase_drift_rad_per_us=drift,
    rf_cycles_error=rfe,out_cycles_error=oute,control_range_v=cr,observed_phase_window_us=float((tr[-1]-tr[0])*1e6),
    rf_fit=fit_edges(rf),output_fit=fit_edges(oe),functional_warm_capture_passed=passed,
    reference_edge_times_s=tr.tolist(),rf_phase_unwrapped_rad=phase.tolist(),
    source_open_loop_matching_screen_remains_failed=True,random_jitter_measured=False,full_pll_acceptance=False,
    interpretation='Last dense1us functional phase/count check of the released physical loop. This does not retroactively pass the prior100kHzclamped screen or establish PSS/noise/PVT.',limitations=p['limitations'])
(H/'results/rt4_release_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['rf_fit','output_fit','reference_edge_times_s','rf_phase_unwrapped_rad']},indent=2))
