"""Validate clean 100nV RT4 transient noise against noise-off and PNoise."""
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
    pp=H/'results/retimer_vab_precision_protocol.json';p=json.loads(pp.read_text())
    src=H/'results'/p['source_protocol'];assert sha(src)==p['source_protocol_sha256'];s=json.loads(src.read_text())
    proof=ROOT/s['source_result'];assert sha(proof)==s['source_sha256']
    reference=(proof.parent/'inputs'/(proof.parent.name+'.scs')).read_text()
    nf=proof.parent/(proof.parent.name+'.raw')/'pnMedge.0.sample.pnoise';assert sha(nf)==s['source_noise_sha256']
    pn=parse(nf);timing_psd=pn['out']**2/header(nf,'slew rate event_1')**2
    seed=R/p['seed_run']/p['case'];seedr=json.loads((seed/'result.json').read_text())
    seedlog=(seed/'spectre.out').read_text();assert seedr['ok'] and recovery(seedlog)['numerically_clean']
    assert effective(seedlog)['abstol(V)']==p['fixed']['vabstol_v']
    rows=[];edge_sets={}
    for c in p['cases']:
        j=R/c['run']/p['case'];rp=j/'result.json';row=dict(c,completed=False);rows.append(row)
        if not rp.exists():continue
        r=json.loads(rp.read_text());log=(j/'spectre.out').read_text()
        if not r.get('local_outputs_sha256'):continue
        row.update(source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),recovery=recovery(log),effective=effective(log))
        if not r['ok']:row['errors']=r['errors'];continue
        assert r['remote_inputs_match'] and 'spectre completes with 0 errors' in log
        assert all(sha(j/'inputs'/k)==v for k,v in r['inputs_sha256'].items())
        assert {k:v for k,v in r['inputs_sha256'].items() if k!=p['case']+'.scs'}==s['dependencies_sha256']
        body=(j/'inputs'/(p['case']+'.scs')).read_text();assert physical(body)==physical(reference)
        eff=effective(log);assert eff['abstol(V)']==1e-7 and eff['abstol(I)']==1e-15 and eff['reltol']==1e-6
        assert eff['maxstep']==float(c['maxstep'][:-1])*1e-12 and eff['method']=='traponly'
        assert r['transient_noise_overrides']==dict(noisefmax=c['noisefmax'],noisefmin=1e6,noiseseed=c['noiseseed'])
        native=r['native_state'];assert native['remote_hash_match'] and native['source_snapshot']==p['seed_run']
        assert sha(ROOT/native['local'])==native['sha256']
        cache=j/'waveforms.npz';assert sha(cache)==r['local_outputs_sha256'][cache.name]
        with np.load(cache) as z:t,y=z['time'],z['out']
        assert abs(t[0]-1e-7)<1e-15 and t[-1]>=p['fixed']['stop_s']-1e-15
        e=cross(t,y,.6);assert np.all(np.diff(e)>.8/984e6) and np.all(np.diff(e)<1.2/984e6)
        edge_sets[c['run']]=e
        row.update(completed=True,numerically_clean=row['recovery']['numerically_clean'],native_sha256=native['sha256'],
                   simulator_log_sha256=sha(j/'spectre.out'),raw_cache_sha256=sha(cache))
    out=dict(scope=__doc__,protocol_sha256=sha(pp),cases=rows,complete=all(x['completed'] for x in rows),passed=False,full_pll_acceptance=False)
    if 'rtvaboff025' in edge_sets:
        n=p['measurement']['edges'];fs=984e6;base=edge_sets['rtvaboff025'];base=base[base>=p['measurement']['start_s']][:n];assert len(base)==n
        grid=edge_band_power(np.zeros(n),fs,*p['measurement']['band_hz'])
        expected=integral(pn['freq'],timing_psd,grid['lower'],grid['upper'])
        out.update(effective_band_hz=[grid['lower'],grid['upper']],pnoise_expected_rms_fs=float(np.sqrt(expected)*1e15))
        for row in rows:
            if not row['completed']:continue
            e=edge_sets[row['run']];i=int(np.argmin(abs(e-base[0])));e=e[i:i+n];assert len(e)==n and max(abs(e-base))<.25/fs
            residual=e-base;residual-=np.mean(residual);m=edge_band_power(residual,fs,*p['measurement']['band_hz'])
            schedule=e-e[0]-np.arange(n)/fs;schedule-=np.mean(schedule)
            blocks=np.mean(m['filtered'].reshape(16,n//16)**2,axis=1)
            row.update(band_rms_fs=float(np.sqrt(m['variance'])*1e15),band_variance_s2=m['variance'],
                variance_block_standard_error_s2=float(np.std(blocks,ddof=1)/4),rms_relative_to_pnoise=float(np.sqrt(m['variance']/expected)-1),
                noise_off_schedule_rms_fs=float(np.std(schedule)*1e15) if row['noisefmax']==0 else None)
        if out['complete']:
            by={r['run']:r for r in rows};rms=lambda name:by[name]['band_rms_fs'];g=p['gates']
            comparisons=dict(bandwidth_160g_vs_80g=rms('rtvabon160g05')/rms('rtvabon80g05')-1,
                step_025_vs_05=rms('rtvabon160g025')/rms('rtvabon160g05')-1,
                seed29_vs11=rms('rtvabon160g025s29')/rms('rtvabon160g025')-1)
            checks=dict(no_recovery=all(r['numerically_clean'] for r in rows),
                noise_off_floor=all(by[n]['noise_off_schedule_rms_fs']<g['off_schedule_rms_fs'] for n in ['rtvaboff05','rtvaboff025']),
                step_floor=rms('rtvaboff05')<g['off_step_rms_fs'],
                pnoise_seed11=abs(by['rtvabon160g025']['rms_relative_to_pnoise'])<g['rms_relative_pnoise'],
                pnoise_seed29=abs(by['rtvabon160g025s29']['rms_relative_to_pnoise'])<g['rms_relative_pnoise'],
                bandwidth=abs(comparisons['bandwidth_160g_vs_80g'])<g['refinement_rms_change'],
                step=abs(comparisons['step_025_vs_05'])<g['refinement_rms_change'])
            out.update(comparisons=comparisons,checks=checks,passed=all(checks.values()))
    out['limitations']=p['limitations']
    (H/'results/retimer_vab_precision_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
