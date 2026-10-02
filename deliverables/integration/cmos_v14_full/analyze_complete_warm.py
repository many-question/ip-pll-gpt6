"""Join native continuation without disguising the user-requested checkpoint error.

The constructed near-lock initial state is not a reset/capture experiment.
RF/output metrics below are deterministic waveform metrics, never random jitter.
"""
from pathlib import Path
import json, hashlib
import numpy as np
from virtuoso_bridge.spectre.parsers import parse_psf_ascii_directory
from analyze import loop, cross

H=Path(__file__).resolve().parent; ROOT=H.parents[3]
R=ROOT/'research/runs/spectre_cmos_v14_full'
A=R/'completewarm01/complete_warm_tt'; B=R/'completedense01/complete_warm_tt'
O=R/'completewarm_joined'; O.mkdir(exist_ok=True)

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(job):
    p=job/'waveforms.npz'
    if not p.exists():
        d=parse_psf_ascii_directory(job/(job.name+'.raw'))
        d={k:np.atleast_1d(v) for k,v in d.items() if k!='units' and np.asarray(v).dtype.kind in 'biufc'}
        np.savez_compressed(p,**d)
    with np.load(p) as z:return {k:z[k] for k in z.files if k!='units'}

a=load(A); b=load(B)
ra=json.loads((A/'result.json').read_text()); rb=json.loads((B/'result.json').read_text())
assert ra['remote_inputs_match'] and rb['remote_inputs_match'] and rb['ok']
excluded={'complete_warm_tt.scs'}
assert {k:v for k,v in ra['inputs_sha256'].items() if k not in excluded}=={k:v for k,v in rb['inputs_sha256'].items() if k not in excluded}
boundary=float(b['time'][0]); keep=a['time']<boundary
assert 0<boundary-a['time'][keep][-1]<2.1e-9
common=set(a)&set(b)
d={k:np.concatenate([a[k][keep],b[k]]) for k in common if len(a[k])==len(a['time']) and len(b[k])==len(b['time'])}
assert np.all(np.diff(d['time'])>0)
np.savez_compressed(O/'waveforms.npz',**d)

def clock_metrics(t,v):
    rise=cross(t,v); fall=cross(t,1.2-v)
    duty=[]; swing=[]
    for x,y in zip(rise[:-1],rise[1:]):
        f=fall[(fall>x)&(fall<y)]; w=v[(t>=x)&(t<y)]
        if len(f)==1:duty.append((f[0]-x)/(y-x)*100)
        swing.append(float(min(w))<.2 and float(max(w))>1.)
    def slew(x):
        lo=cross(t,x,.12); hi=cross(t,x,1.08); values=[]
        for p in lo:
            q=hi[hi>p]
            if len(q) and q[0]-p<.5*np.mean(np.diff(rise)):values.append((q[0]-p)*1e12)
        return dict(mean_ps=float(np.mean(values)),range_ps=[float(min(values)),float(max(values))]) if values else None
    return dict(frequency_mhz=float(1e-6/np.mean(np.diff(rise))),cycles=len(rise)-1,
        duty_mean_percent=float(np.mean(duty)),duty_range_percent=[float(min(duty)),float(max(duty))],
        voltage_range_v=[float(min(v)),float(max(v))],every_cycle_full_swing=all(swing),
        rise_10_90=slew(v),fall_90_10=slew(1.2-v))

t=b['time']; duration=(t[-1]-t[0])*1e6
power={k:float(-1.2*np.trapezoid(b[p],t)/(t[-1]-t[0])*1e3) for k,p in [('total','VDD:p'),('vco','XP.VVCO:p'),('rx','XP.VRX:p'),('rt','XP.VRT:p')]}
power['other']=power['total']-power['vco']-power['rx']-power['rt']
energy_power=float((b['energy_nj'][-1]-b['energy_nj'][0])/duration)
er=abs(power['total']/energy_power-1)
assert er<.002
windows=[]
for start in np.arange(0,7.9,.25):
    stop=start+.25; en=np.interp([start*1e-6,stop*1e-6],d['time'],d['energy_nj'])
    windows.append(dict(start_us=float(start),stop_us=float(stop),power_mw=float((en[1]-en[0])/.25)))
result=dict(scope=__doc__,condition='TT27C,1.2V,24MHz reference,K41,M4,10fF,Q5 pi-RLC. 4ps/1e-4 functional numerics; strict1ps/1e-5 check separate.',
    sources={str(p.relative_to(ROOT)):sha(p) for p in [A/'result.json',B/'result.json',A/'waveforms.npz',B/'waveforms.npz']},
    join=dict(boundary_us=boundary*1e6,source_end_us=a['time'][-1]*1e6,resumed_end_us=t[-1]*1e6,circuit_hashes_identical=True,reason='Source log records a SIGUSR2 user-requested error at7.45933us although its raw data extend to8us. Only the prefix before checkpoint is used; an independently replayed native continuation completed with0errors. No state forcing at join.'),
    stationarity=loop(d),dense_window_us=[t[0]*1e6,t[-1]*1e6],
    dense_output=clock_metrics(t,b['out']),dense_rfclock=clock_metrics(t,b['XP.clk']),
    dense_rf_frequency_mhz=float(1e-6/np.mean(np.diff(cross(t,b['XP.vp']-b['XP.vn'],0)))),
    dense_power_mw=power,dense_energy_power_mw=energy_power,power_method_relative_difference=er,
    power_windows=windows,limitations=['Constructed near-lock start, not reset acquisition.','No random-noise analysis.','Less than one complete32us state period; power is window-specific, not long-term locked average.','4ps numerics cannot be assumed equal to1ps without the independent check.'])
(H/'results/complete_warm_joined.json').write_text(json.dumps(result,indent=2)+'\n')
marker=dict(reason='Source log records a SIGUSR2 user-requested error at7.45933us, though raw data extend to8us. Only prefix before checkpoint is used with successful native replay; do not treat source final status as0errors.',saved_time_us=7.45933,continuation_run='completedense01',joined_result='share/deliverables/integration/cmos_v14_full/results/complete_warm_joined.json')
(A/'checkpoint_stop.json').write_text(json.dumps(marker,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['sources','power_windows']},indent=2))
