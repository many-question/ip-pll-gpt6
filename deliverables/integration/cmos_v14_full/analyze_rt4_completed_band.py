"""Inspect the completed RT4 main noise sweep without claiming the later sweep finished."""
from pathlib import Path
import hashlib,json
import numpy as np
from noise_utils import parse,header,devices,cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
j=ROOT/'research/runs/spectre_cmos_v14_full/rt4pulsetripband01/chain_rt4_pulsetrip_band_tt'
raw=j/'completed_pn_snapshot';mp=raw/'snapshot.json'
if not mp.exists():print('Completed main-band snapshot pending');raise SystemExit(0)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads(mp.read_text());p=json.loads((H/'results/rt_pulsetrip_noise_protocol.json').read_text())
assert m['completed_analysis_collected'] and m['analysis']=='pn'
assert all(sha(raw/x['name'])==x['sha256'] for x in m['files'])
assert all(sha(j/'inputs'/k)==v for k,v in m['inputs_sha256'].items())
assert m['inputs_sha256']['bank_pulsetrip_v14.scs']==p['current_bank_sha256']
td=parse(raw/'pss.td.pss');fd=parse(raw/'pss.fd.pss');t=td['time'];T=t[-1]-t[0]
expected={'vp':24,'clk':24,'q1':12,'data':6,'out':6,'acqclk':6,'XD.d8':3,'XD.d12':2}
actual={k:int(round(fd['freq'][1+np.argmax(abs(fd[k][1:]))]/164e6)) for k in expected}
edges=cross(t,td['out']);end=max(float(abs(td[k][-1]-td[k][0])) for k in expected)
assert abs(T*164e6-1)<1e-7 and actual==expected and len(edges)==6 and end<1e-3
assert max(abs(np.diff(np.r_[edges,edges[0]+T])*984e6-1))<.02
fp=raw/'pnMedge.0.sample.pnoise';pn=parse(fp);f=pn['freq'];slope=header(fp,'slew rate event_1');sv=pn['out']**2
assert slope>0 and len(f)>=90 and np.all(np.diff(f)>0) and np.all(np.isfinite(sv)) and np.all(sv>0)
assert abs(f[0]/1e4-1)<1e-9 and abs(f[-1]/492e6-1)<1e-9
dev=devices(fp,len(f));closure=float(max(abs(sum(dev.values())/sv-1)));assert closure<1e-7
st=sv/slope**2;groups={}
for name,values in dev.items():
    group='.'.join(name.split('.')[:2]) if name.startswith('XR.') else name.split('.')[0]
    groups[group]=groups.get(group,0)+values/slope**2
out=dict(scope=__doc__,condition=p['condition'],source_snapshot=mp.relative_to(ROOT).as_posix(),source_snapshot_sha256=sha(mp),
    periodic_passed=True,harmonics=actual,output_edges=len(edges),endpoint_max_v=end,slew_v_per_s=slope,
    device_sum_relative_error=closure,offsets_hz=f.tolist(),timing_psd_s2_per_hz=st.tolist(),
    provisional_log_grid_rms_fs=float(np.sqrt(np.trapezoid(st,f))*1e15),
    group_provisional_rms_fs={k:float(np.sqrt(np.trapezoid(v,f))*1e15) for k,v in groups.items()},
    exact_harmonic_flicker_warning='SPCRTRF-15037' in (raw/'spectre_snapshot.out').read_text(),
    physical_pole_integral_closed=False,neighbour_sweep_completion_claimed=False,whole_job_completion_claimed=False,full_pll_acceptance=False,
    limitations=['Completed logarithmic main sweep only; later25nearharmonicpoints remain separately qualified.','Continuousflickernearharmonicscannotbeexcisedasdiscretespurs.','NoisyactualLC/reference/CP/fullPLL interaction excluded.','ProvisionalRMSis not a qualified200fsmeasurement.'])
(H/'results/rt4_completed_band_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['offsets_hz','timing_psd_s2_per_hz']},indent=2))
