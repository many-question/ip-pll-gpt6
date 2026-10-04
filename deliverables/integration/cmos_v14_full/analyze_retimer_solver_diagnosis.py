"""Compare solver trials on the same RT4/native state; no jitter acceptance."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from analyze_retimer_transient_noise_control import physical,edge_band_power
from analyze_vco_bias_band import integral
from noise_utils import cross,parse,header
from transient_diagnostics import effective,recovery
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    pp=H/'results/retimer_transient_noise_protocol.json';p=json.loads(pp.read_text())
    dp=H/'results/retimer_noise_solver_diagnosis_protocol.json';d=json.loads(dp.read_text())
    source=ROOT/p['source_result'];assert sha(source)==p['source_sha256']
    source_tb=(source.parent/'inputs'/(source.parent.name+'.scs')).read_text()
    pnfile=source.parent/(source.parent.name+'.raw')/'pnMedge.0.sample.pnoise'
    assert sha(pnfile)==p['source_noise_sha256'];pn=parse(pnfile)
    off=R/'rttrannoiseoff025'/d['case'];offr=json.loads((off/'result.json').read_text())
    assert sha(off/'waveforms.npz')==offr['local_outputs_sha256']['waveforms.npz']
    with np.load(off/'waveforms.npz') as z:base=cross(z['time'],z['out'],p['edge_threshold_v'])
    seed=R/p['seed_run']/d['case']
    with np.load(seed/'waveforms.npz') as z:expected_start=float(z['out'][-1])
    n=1024;fs=p['output_hz'];base=base[base>=p['measurement_start_s']][:n]
    grid=edge_band_power(np.zeros(n),fs,*p['comparison_band_hz'])
    expected=integral(pn['freq'],pn['out']**2/header(pnfile,'slew rate event_1')**2,grid['lower'],grid['upper'])
    cases=[dict(run='rttrannoise80g05',algorithm='default',iabstol=1e-15,mode='ax')]+[
        dict(c,mode='ax') for c in d['cases']]+[
        dict(run='rtnoiseclassic01',algorithm='default',iabstol=1e-15,mode='spectre'),
        dict(run='rtnoisegear201',algorithm='default',iabstol=1e-15,mode='ax',method='gear2only'),
        dict(run='rtnoisevabstol01',algorithm='default',iabstol=1e-15,mode='ax',dynamic_vabstol_v=1e-7)]
    rows=[]
    for c in cases:
        j=R/c['run']/d['case'];rp=j/'result.json';row=dict(c,completed=False);rows.append(row)
        if not rp.exists():continue
        r=json.loads(rp.read_text());log=(j/'spectre.out').read_text()
        row.update(source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),simulator_log_sha256=sha(j/'spectre.out'))
        values=effective(log);recov=recovery(log)
        row.update(effective_analysis_parameters=values,recovery=recov,
                   requested_static_iabstol_applied=values.get('abstol(I)')==c['iabstol'])
        if not r['ok'] or not r.get('local_outputs_sha256'):
            row.update(errors=r.get('errors'),numerically_clean=False);continue
        assert r['remote_inputs_match'] and 'spectre completes with 0 errors' in log
        assert all(sha(j/'inputs'/k)==v for k,v in r['inputs_sha256'].items())
        assert {k:v for k,v in r['inputs_sha256'].items() if k!=d['case']+'.scs'}==p['dependencies_sha256']
        body=(j/'inputs'/(d['case']+'.scs')).read_text();assert physical(body)==physical(source_tb)
        opts=next(s for s in body.splitlines() if s.startswith('simulatorOptions '))
        for k,v in dict(reltol=1e-6,vabstol=1e-9,iabstol=c['iabstol']).items():
            assert float(re.search(r'\b'+k+r'=(\S+)',opts)[1])==v
        noise=r['transient_noise_overrides'];assert noise['noisefmax']==80e9 and noise['noisefmin']==1e6 and noise['noiseseed']==11
        assert noise.get('trannoisemethod','default')==c['algorithm']
        step=r['numerical_overrides']['maxstep'];assert step.endswith('p') and float(step[:-1])==.5
        native=r['native_state'];assert native['remote_hash_match'] and native['sha256']==d['native_sha256']==sha(ROOT/native['local'])
        command=r['metadata']['spectre_command'];assert ('+preset=ax' in command)==(c['mode']=='ax')
        cache=j/'waveforms.npz';assert sha(cache)==r['local_outputs_sha256'][cache.name]
        with np.load(cache) as z:t,y=z['time'],z['out']
        boundary_ok=abs(float(y[0])-expected_start)<1e-9
        row['native_boundary']=dict(passed=boundary_ok,expected_output_v=expected_start,observed_output_v=float(y[0]))
        row['valid_continuation']=boundary_ok and recov['numerically_clean'] and row['requested_static_iabstol_applied']
        e=cross(t,y,p['edge_threshold_v']);start=int(np.argmin(abs(e-base[0])));e=e[start:start+n]
        assert len(e)==n and max(abs(e-base))<.25/fs
        residual=e-base;residual-=np.mean(residual)
        m=edge_band_power(residual,fs,*p['comparison_band_hz'])
        row.update(completed=True,numerically_clean=recov['numerically_clean'],
            measurement_edges=n,band_rms_fs=float(np.sqrt(m['variance'])*1e15),
            rms_relative_to_pnoise=float(np.sqrt(m['variance']/expected)-1),raw_cache_sha256=sha(cache),native_sha256=native['sha256'])
    out=dict(scope=__doc__,source_protocol_sha256=sha(pp),solver_protocol_sha256=sha(dp),
        condition=d['fixed'],measurement_start_s=p['measurement_start_s'],
        effective_comparison_band_hz=[grid['lower'],grid['upper']],pnoise_expected_rms_fs=float(np.sqrt(expected)*1e15),
        noiseless_reference_result_sha256=sha(off/'result.json'),cases=rows,
        full_pll_acceptance=False,noise_acceptance=False,
        limitations=['Diagnostic comparison only; 1024 edges do not resolve the 10kHz acceptance lower bound.',
          'A clean solver still requires matched noise-off, bandwidth/step convergence, seed checks and PNoise agreement.',
          'Reported recovery counts are lower bounds when Spectre suppresses repeated messages.',
          'rtnoisediagiabstol01 changed global iabstol but native restore retained analysis abstol(I)=1fA. This is an ineffective override, not a valid tolerance comparison.',
          'The dynamic-vabstol trace cleared its initial output to0V instead of restoring1.226281V. Its clean log is not a successful recovery/tolerance repair; see retimer_restart_diagnosis_validation.json.',
          'Physical circuit, native seed and stimuli are fixed; the off025 reference uses the original AX method.'])
    (H/'results/retimer_noise_solver_diagnosis_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(band=out['effective_comparison_band_hz'],pnoise_fs=out['pnoise_expected_rms_fs'],cases=rows),indent=2))

if __name__=='__main__':main()
