"""Independent state and physical-waveform review of the completed step candidate."""
from pathlib import Path
import datetime, hashlib, json
import numpy as np
H=Path(__file__).resolve().parent; ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    out=H/'results/rt4_rebracket_detail109.json'; assert not out.exists()
    prior=H/'results/rt4_rebracket109_review.json'
    r=json.loads(prior.read_text())['result']; assert r['state']=='completed'
    work=ROOT/Path(r['source_result']).parent
    with np.load(work/'waveforms.npz') as z:d={k:z[k] for k in z.files if k!='units'}
    t=d['time']; assert len(t)==60001 and np.all(np.diff(t)>0)
    assert all(np.isfinite(v).all() for v in d.values())
    bits=lambda pre,n:sum((d[pre+str(i)]>.6).astype(int)*(1<<i) for i in range(n))
    state=bits('XP.XC.state',3); dac=bits('XP.XC.d',6)
    check=r['eval_snapshots'][15:21]
    edges={}
    for name in ['qualified','frequency_good','phase_good','amp_good','range_error','XP.en','XP.restart','XP.XC.acquired']:
        v=d[name]>.6;ix=np.flatnonzero(v[1:]!=v[:-1])+1
        edges[name]=[dict(time_s=float(t[i]),high=bool(v[i])) for i in ix]
    change=np.r_[False,(np.diff(d['obsphase'])!=0)|(np.diff(d['obscycles'])!=0)|(np.diff(d['obsdivcycles'])!=0)]
    def freq_stats(mask):
        f=d['obsdivcycles'][mask&change]*24
        if not len(f):return None
        return dict(observations=len(f),mean_mhz=float(f.mean()),minimum_mhz=float(f.min()),maximum_mhz=float(f.max()),worst_abs_error_ppm=float(np.max(abs(f/984-1))*1e6))
    q=d['qualified']>.6
    sustained_start=(int(np.flatnonzero(~q)[-1])+1 if (~q).any() else 0) if q[-1] else len(t)
    locked=np.arange(len(t))>=sustained_start
    ap=ROOT/'research/heartbeat_rebracket_terminal109.json';a=json.loads(ap.read_text());j=a['jobs'][0]
    assert not j['alive'] and j['exit_marker']=='0' and j['raw_end'] and j['completed_output_hashes'] and j['final_state_sha256']
    result=dict(time=datetime.datetime.now().astimezone().isoformat(),review_sha256=sha(prior),
        remote_audit=ap.relative_to(ROOT).as_posix(),remote_audit_sha256=sha(ap),physical_points=len(t),signals=len(d),finite=True,
        metadata_units_excluded=True,terminal=dict(exit_code='0',errors=0,remote_process_absent=True,raw_end=True,hashes=j['completed_output_hashes'],final_ic_sha256=j['final_state_sha256']),
        recheck_target=5248,recheck_dac=[x['dac'] for x in check],recheck_errors=[x['measured_count']-5248 for x in check],
        recheck_eval_times_s=[x['time_s'] for x in check],state_transitions=edges,
        controller_states=[dict(time_s=float(t[i]),state=int(state[i])) for i in np.r_[0,np.flatnonzero(state[1:]!=state[:-1])+1]],
        handoff_observed=bool(np.any(state==4)),restart_observed=bool(np.any(d['XP.restart']>.6)),final_dac=int(dac[-1]),
        final_state=int(state[-1]),range_error_final=bool(d['range_error'][-1]>.6),
        last_1us=freq_stats(t>=119e-6),
        pll_enabled=freq_stats(d['XP.en']>.6),
        final_1us_before_restart=freq_stats((t>=114.920e-6)&(t<115.920e-6)),sustained_qualified_start_s=float(t[sustained_start]) if sustained_start<len(t) else None,
        sustained_qualified_frequency=freq_stats(locked),fast_capture_passed=r['fast_functional_screen_passed'],
        boundary='Same bisection4.8fF candidate only; final1us is a restarted search, not steady state; finite-period frequency deviations are not jitter; no inherited passes from other physical/controller versions.')
    out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['controller_states','terminal','state_transitions']}))

if __name__=='__main__':main()
