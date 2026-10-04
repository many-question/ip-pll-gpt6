"""Validate measured RF matching and retained filter memory before a clamp release."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from noise_utils import cross
from reference_modulation_utils import fit_edges
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ap=argparse.ArgumentParser();ap.add_argument('--protocol',default='rt4_matched_point_protocol.json');ap.add_argument('--output',default='rt4_matched_point_validation.json');args=ap.parse_args()
assert all(Path(n).name==n and n.endswith('.json') for n in [args.protocol,args.output])
p=json.loads((H/'results'/args.protocol).read_text());j=ROOT/'research/runs/spectre_cmos_v14_full'/p['run']/p['case'];rp=j/'result.json'
if not rp.exists():print('pending');raise SystemExit(0)
r=json.loads(rp.read_text())
if not r.get('local_outputs_sha256'):print('collection incomplete');raise SystemExit(0)
assert r['ok'] and r['remote_inputs_match'] and 'spectre completes with 0 errors' in (j/'spectre.out').read_text()
source=ROOT/p['source_result'];assert sha(source)==p['source_result_sha256'];old=json.loads(source.read_text())
sourcecase=source.parent.name
excluded={p['case']+'.scs',p['case']+'.ic',sourcecase+'.scs',sourcecase+'.ic'}
assert {k:v for k,v in r['inputs_sha256'].items() if k not in excluded}=={k:v for k,v in old['inputs_sha256'].items() if k not in excluded}
assert r['inputs_sha256'][p['case']+'.ic']==p['seed_sha256'] and sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files}
t=d['time'];start=p.get('dense_start_s',250e-9);stop=p.get('stop_s',750e-9);mid=(start+stop)/2
assert abs(t[0]-start)<1e-14 and abs(t[-1]-stop)<1e-14
e=cross(t,d['XP.vp']-d['XP.vn'],0);rf=fit_edges(e);of=fit_edges(cross(t,d['out']))
fs=[]
for lo,hi in [(start,mid),(mid,stop)]:
    a=e[(e>=lo)&(e<hi)];fs.append(float(1/np.mean(np.diff(a))))
drift=abs(fs[1]-fs[0])/np.mean(fs)*1e6;clamp=float(max(abs(d['XP.ctrl']-p['control_v'])))
held=all(np.all(d[f'XP.b{i}']>.9) if 24&(1<<i) else np.all(d[f'XP.b{i}']<.3) for i in range(8))
ratio=float(abs(of['carrier_hz']*4/rf['carrier_hz']-1));limits=p['limits'];memory=float(d['XP.vc1'][-1]-d['XP.ctrl'][-1]);error=rf['carrier_hz']-p['target_rf_hz']
valid=bool(held and clamp<limits['clamp_error_v'] and drift<limits['window_rf_drift_ppm'] and ratio<limits['divider_relative'])
out=dict(scope=__doc__,source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),valid=valid,
    control_v=p['control_v'],coarse_held=bool(held),window_rf_drift_ppm=float(drift),clamp_error_v=clamp,divider_relative_error=ratio,
    rf_fit=rf,output_fit=of,rf_error_hz=error,final_c1_minus_control_v=memory,
    rf_matching_passed=bool(valid and abs(error)<limits['desired_target_error_hz']),
    filter_memory_screen_passed=bool(valid and abs(memory)<limits['desired_filter_alignment_v']),
    random_jitter_measured=False,full_pll_acceptance=False,clamp_released=False,
    interpretation='Actual in-bracket control point, not a released closed-loop result. Frequency and filter-memory screens must be reviewed separately.')
(H/'results'/args.output).write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['rf_fit','output_fit']},indent=2))
