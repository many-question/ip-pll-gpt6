"""Check RC source noise after native recovery against thermal-noise variance."""
from pathlib import Path
import hashlib,json,re
import numpy as np
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def physical(body):
    return '\n'.join(s for s in body.splitlines() if not s.startswith('tran tran ')).strip()

def main():
    pp=H/'results/transient_noise_recovery_protocol.json';p=json.loads(pp.read_text());rows=[]
    seed=p['cases'][0];base=R/seed['run']/seed['case'];rp=base/'result.json'
    if not rp.exists():print('Seed pending');return
    original=(base/'inputs'/(seed['case']+'.scs')).read_text()
    cases=[dict(run=x['run'],case=seed['case'],bandwidth=x['noisefmax'],native=True,noise=x) for x in p['recovery_cases']]
    cases.append(dict(run=p['cases'][1]['run'],case=p['cases'][1]['case'],bandwidth=1e10,native=False))
    for case in cases:
        j=R/case['run']/case['case'];res=j/'result.json';row=dict(run=case['run'],case=case['case'],completed=False);rows.append(row)
        if not res.exists():continue
        v=json.loads(res.read_text())
        if not v.get('local_outputs_sha256'):continue
        row.update(completed=True,source_result=res.relative_to(ROOT).as_posix(),source_sha256=sha(res),valid=False)
        log=(j/'spectre.out').read_text();assert v['ok'] and v['remote_inputs_match'] and 'spectre completes with 0 errors' in log
        assert all(sha(j/'inputs'/k)==value for k,value in v['inputs_sha256'].items())
        body=(j/'inputs'/(j.name+'.scs')).read_text();assert physical(body)==physical(original)
        if case['native']:
            n=v['native_state'];assert n and n['remote_hash_match'] and n['source_snapshot']==seed['run']
            assert v['transient_noise_overrides']=={k:case['noise'][k] for k in ['noisefmax','noisefmin','noiseseed']}
            assert sha(ROOT/n['local'])==n['sha256']
        cache=j/'waveforms.npz';assert sha(cache)==v['local_outputs_sha256'][cache.name]
        with np.load(cache) as z:t=z['time'];y=z['out']
        if case['native']:assert t[0]>=p['saved_time_s']-1e-15 and t[0]<p['saved_time_s']+1e-9
        sel=(t>=p['measurement_start_s'])&(t<=p['measurement_stop_s']+1e-15);x=y[sel];ts=t[sel]
        assert len(x)>70000 and np.allclose(np.diff(ts),1e-10,rtol=1e-5,atol=1e-16)
        mean=float(np.mean(x));variance=float(np.var(x,ddof=1));bw=case['bandwidth'];k=1.380649e-23
        expected=2*k*p['temperature_k']/(np.pi*p['capacitance_f'])*np.arctan(2*np.pi*bw*p['resistance_ohm']*p['capacitance_f'])
        mean_se=np.sqrt(expected*2*p['resistance_ohm']*p['capacitance_f']/(ts[-1]-ts[0])) if bw else 0
        err=variance/expected-1 if bw else None
        passed=bool(abs(err)<p['gates']['variance_relative_error'] and abs(mean-1.2)<5*mean_se) if bw else bool(np.sqrt(variance)<p['gates']['noiseless_rms_v'] and abs(mean-1.2)<1e-9)
        row.update(valid=passed,noise_bandwidth_hz=bw,samples=len(x),mean_v=mean,variance_v2=variance,expected_variance_v2=float(expected),
            relative_variance_error=err,rms_v=float(np.sqrt(variance)),mean_standard_error_estimate_v=float(mean_se),raw_cache_sha256=sha(cache))
    complete=all(x['completed'] for x in rows);passed=complete and all(x.get('valid') for x in rows);comparisons={}
    if passed:
        byrun={x['run']:x for x in rows};direct=byrun[p['cases'][1]['run']]['variance_v2']
        for name in ['noiserecoveron11','noiserecoveron29']:
            delta=byrun[name]['variance_v2']/direct-1;comparisons[name+'_vs_direct']=dict(relative_variance_change=delta,passed=abs(delta)<.1)
        delta=byrun['noiserecover20g']['variance_v2']/byrun['noiserecoveron11']['variance_v2']-1
        comparisons['20g_vs_10g']=dict(relative_variance_change=delta,passed=abs(delta)<.1)
        passed=all(x['passed'] for x in comparisons.values())
    out=dict(scope=__doc__,protocol_sha256=sha(pp),condition=p['condition'],cases=rows,complete=complete,passed=bool(passed),comparisons=comparisons,
        full_pll_acceptance=False,main_dut_modified=False,limitations=p['limitations'])
    (H/'results/transient_noise_recovery_validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))

if __name__=='__main__':main()
