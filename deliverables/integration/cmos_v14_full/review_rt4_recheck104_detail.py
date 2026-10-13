"""Independent finite-record/state-sequence review of the completed one-code candidate."""
from pathlib import Path
import datetime,hashlib,json
import numpy as np
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    out=H/'results/rt4_recheck_detail104.json';assert not out.exists()
    prior=H/'results/rt4_recheck_review104.json';r=json.loads(prior.read_text())['result']
    work=ROOT/Path(r['source_result']).parent
    with np.load(work/'waveforms.npz') as z:d={k:z[k] for k in z.files if k!='units'}
    t=d['time'];assert len(t)==60001 and np.all(np.diff(t)>0)
    assert all(np.isfinite(v).all() for v in d.values())
    bits=lambda pre,n:sum((d[pre+str(i)]>.6).astype(int)*(1<<i) for i in range(n))
    state=bits('XP.XC.state',3);dac=bits('XP.XC.d',6)
    check=r['eval_snapshots'][15:];assert len(check)==8
    errors=[x['measured_count']-5248 for x in check];assert errors==[18,15,15,13,12,11,10,8]
    edges={}
    for name in ['qualified','frequency_good','range_error','XP.en','XP.restart','XP.XC.acquired']:
        v=d[name]>.6;ix=np.flatnonzero(v[1:]!=v[:-1])+1
        edges[name]=[dict(time_s=float(t[i]),high=bool(v[i])) for i in ix]
    assert not any(edges[n] for n in ['qualified','frequency_good','XP.en','XP.restart','XP.XC.acquired'])
    assert len(edges['range_error'])==1 and edges['range_error'][0]['high']
    assert not np.any(state==4) and state[-1]==5 and dac[-1]==37
    change=np.r_[False,(np.diff(d['obsphase'])!=0)|(np.diff(d['obscycles'])!=0)|(np.diff(d['obsdivcycles'])!=0)]
    f=d['obsdivcycles'][(t>=119e-6)&change]*24
    auditp=ROOT/'research/heartbeat_recheck_recovered104.json';audit=json.loads(auditp.read_text());j=audit['jobs'][0]
    assert not j['alive'] and j['exit_marker']=='0' and j['raw_end'] and 'completed_output_hashes' in j
    data=dict(time=datetime.datetime.now().astimezone().isoformat(),review_sha256=sha(prior),
        remote_audit=auditp.relative_to(ROOT).as_posix(),remote_audit_sha256=sha(auditp),
        physical_points=len(t),signals=len(d),finite=True,metadata_units_excluded=True,
        terminal=dict(exit_code=j['exit_marker'],errors=0,remote_process_absent=True,raw_end=True,
                      hashes=j['completed_output_hashes'],final_ic_sha256=j['final_state_sha256']),
        recheck_target=5248,recheck_dac=[x['dac'] for x in check],recheck_errors=errors,recheck_eval_times_s=[x['time_s'] for x in check],
        state_transitions=edges,handoff_observed=False,restart_observed=False,budget_exhausted=True,
        last_1us_output_mhz=dict(mean=float(f.mean()),minimum=float(f.min()),maximum=float(f.max()),worst_abs_error_ppm=float(np.max(abs(f/984-1))*1e6)),
        conclusion='Complete120us but failed capture. Eight one-code corrections reduce the error but exhaust budget; range_error asserted at106.920us and enable remains low. Protection works; lock does not.',
        inference='Verification correction span is insufficient in this observed run. Underlying slow frequency motion during SAR remains unisolated. Variable1..4-code corrections are a new hypothesis, not a proven fix.',
        boundary='No locked window; no jitter measurement or pass. No inherited passes from other physical/controller versions.')
    out.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data['last_1us_output_mhz']))

if __name__=='__main__':main()
