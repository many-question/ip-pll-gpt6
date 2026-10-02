"""Analyze an explicitly listed, hash-matched native reset trajectory.

Usage: analyze_capture.py RUN1 RUN2 ... RUN_LAST
Earlier runs may be intentional checkpoint fragments; last run must complete.
No waveform or progress snapshot is promoted to acceptance while still running.
"""
from pathlib import Path
import json,hashlib,sys,re
import numpy as np
from virtuoso_bridge.spectre.parsers import parse_psf_ascii_directory
from analyze import loop,cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
case='complete_k41_tt';runs=sys.argv[1:];assert runs
jobs=[R/run/case for run in runs];datasets=[];records=[]
for j in jobs:
    rec=json.loads((j/'result.json').read_text());assert rec['remote_inputs_match'];records.append(rec)
    p=j/'waveforms.npz'
    if not p.exists():
        x=parse_psf_ascii_directory(j/(case+'.raw'))
        x={k:np.atleast_1d(v) for k,v in x.items() if k!='units' and np.asarray(v).dtype.kind in 'biufc'}
        np.savez_compressed(p,**x)
    with np.load(p) as z:datasets.append({k:z[k] for k in z.files if k!='units'})
assert records[-1]['ok'] and 'spectre completes with 0 errors' in (jobs[-1]/'spectre.out').read_text()
def inputs(rec):return {k:v for k,v in rec['inputs_sha256'].items() if k!=case+'.scs'}
assert all(inputs(x)==inputs(records[0]) for x in records)
for job in jobs:
    tb=(job/'inputs'/(case+'.scs')).read_text()
    assert re.search(r'\breltol=1e-4\b',tb) and re.search(r'\bmaxstep=4p\b',tb),'Reset trajectory numerical settings changed'
assert 'recover=' not in (jobs[0]/'inputs'/(case+'.scs')).read_text()
assert 'readic=' not in (jobs[0]/'inputs'/(case+'.scs')).read_text()
assert datasets[0]['time'][0]==0
for i in range(1,len(jobs)):
    native=records[i]['native_state'];assert native['remote_hash_match'] and native['source_snapshot']==runs[i-1]
    assert str(Path(native['local'])).startswith(str(jobs[i-1].relative_to(ROOT)))
    assert hashlib.sha256((ROOT/native['local']).read_bytes()).hexdigest()==native['sha256'],'Recovered native state changed'
common=set.intersection(*(set(d) for d in datasets));segments=[];boundaries=[]
for i,d in enumerate(datasets):
    keep=d['time']<datasets[i+1]['time'][0] if i+1<len(datasets) else np.ones(len(d['time']),bool)
    segments.append({k:d[k][keep] for k in common if len(d[k])==len(d['time'])})
    if i+1<len(datasets):
        delta=datasets[i+1]['time'][0]-d['time'][keep][-1];assert 0<delta<2.1e-9
        boundaries.append(dict(from_run=runs[i],to_run=runs[i+1],time_us=float(datasets[i+1]['time'][0]*1e6),gap_ns=float(delta*1e9)))
d={k:np.concatenate([s[k] for s in segments]) for k in segments[0]};assert np.all(np.diff(d['time'])>0)
dest=R/('capture_joined_'+runs[-1]);dest.mkdir(exist_ok=True);np.savez_compressed(dest/'waveforms.npz',**d)
t=d['time'];state=np.zeros(len(t),dtype=int);coarse=state.copy();dac=state.copy()
for target,prefix,n in [(state,'XP.XC.state',3),(coarse,'XP.b',8),(dac,'XP.XC.d',6)]:
    for bit in range(n):target[:]+=((d[prefix+str(bit)]>.6).astype(int)<<bit)
events=[]
# Record settled digital values a full2ns sample after a detected change.
change=np.flatnonzero((np.diff(state)!=0)|(np.diff(coarse)!=0)|(np.diff(dac)!=0))+1
for i in change:
    if i+1<len(t) and state[i]==state[i+1] and coarse[i]==coarse[i+1] and dac[i]==dac[i+1]:
        events.append(dict(time_us=float(t[i]*1e6),state=int(state[i]),coarse=int(coarse[i]),dac=int(dac[i]),rf_cycles_per_ref=float(d['obscycles'][i])))
logic={}
for k in ['cfg_ready','qualified','range_error','frequency_good','XP.XC.acquired','XP.en','XP.restart']:
    e=cross(t,d[k]);logic[k]=dict(first_rising_us=float(e[0]*1e6) if len(e) else None,final_v=float(d[k][-1]),final_1us_all_high=bool(np.all(d[k][t>t[-1]-1e-6]>.6)))
result=dict(scope='Complete physical programmable PLL, independent reset/application sequence; native recovery preserves all states. Initial10uV differential VCO perturbation seeds deterministic oscillation. No constructed near-lock initial state. Supply is alreadyDC1.2V: this is reset acquisition, not a power-rail ramp/startup qualification.',condition='TT27,1.2V,24MHz,10fF,K41/M4,Q5 RLC,4ps/reltol1e-4. Functional result; strict numerics and random noise remain separate.',
    sources={str((j/'result.json').relative_to(ROOT)):hashlib.sha256((j/'result.json').read_bytes()).hexdigest() for j in jobs},
    boundaries=boundaries,circuit_hashes_identical=True,final_simulator_completed=True,stationarity=loop(d),logic=logic,digital_events=events,
    joined_waveform=str((dest/'waveforms.npz').relative_to(ROOT)),joined_waveform_sha256=hashlib.sha256((dest/'waveforms.npz').read_bytes()).hexdigest())
result['functional_capture_screen_passed']=bool(result['stationarity']['passed'] and logic['qualified']['final_1us_all_high'] and logic['frequency_good']['final_1us_all_high'] and abs(logic['range_error']['final_v'])<.2)
measured=np.zeros(len(t),dtype=int)
for bit in range(14):measured+=((d['XP.XC.m'+str(bit)]>.6).astype(int)<<bit)
eval_entries=np.flatnonzero((state[1:]==3)&(state[:-1]!=3))+1
obs=np.flatnonzero((abs(np.diff(d['obsphase']))>1e-9)|(abs(np.diff(d['obscycles']))>1e-9))+1
measurements=[]
for i in eval_entries:
    if i+1>=len(t) or state[i+1]!=3:continue
    window=obs[(t[obs]>t[i]-1.25e-6)&(t[obs]<t[i]-.17e-6)]
    measurements.append(dict(eval_time_us=float(t[i]*1e6),coarse=int(coarse[i]),dac=int(dac[i]),captured_count=int(measured[i+1]),target_count=1312,rf_mhz_before_eval=float(np.mean(d['obscycles'][window])*24) if len(window) else None,frequency_window_note='Reference-cycle observations within late measurement interval, excludingdrain; not a direct count-window timing measurement.'))
result['fll_measurements']=measurements
handoff=logic['XP.XC.acquired']['first_rising_us']
if handoff is not None:
    ix=obs[(t[obs]*1e6>handoff-1.)&(t[obs]*1e6<handoff-.1)]
    result['pre_handoff']=dict(window_us=[handoff-1.,handoff-.1],rf_mean_mhz=float(np.mean(d['obscycles'][ix])*24),rf_error_mhz=float(np.mean(d['obscycles'][ix])*24-3936),coarse=int(coarse[np.searchsorted(t,handoff*1e-6)-1]),dac=int(dac[np.searchsorted(t,handoff*1e-6)-1]))
left=np.arange(t[0],t[-1]-100e-9,100e-9);right=left+100e-9
p100=(np.interp(right,t,d['energy_nj'])-np.interp(left,t,d['energy_nj']))/.1;k=int(np.argmax(p100))
result['reset_trajectory_energy']=dict(total_nj=float(d['energy_nj'][-1]-d['energy_nj'][0]),mean_supply_mw=float((d['energy_nj'][-1]-d['energy_nj'][0])/((t[-1]-t[0])*1e6)),maximum_100ns_average_mw=float(p100[k]),maximum_window_us=[float(left[k]*1e6),float(right[k]*1e6)],boundary='100ns non-overlapping energy averages, not instantaneous peak current/power. Does not include a power-supply ramp.')
(H/'results'/('capture_'+runs[-1]+'.json')).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['digital_events','sources']},indent=2))
