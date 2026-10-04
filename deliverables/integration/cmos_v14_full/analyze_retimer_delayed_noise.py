"""Audit fresh same-analysis delayed noise against actual RT4 sampled PNoise."""
from pathlib import Path
import hashlib,json
import numpy as np
from noise_utils import cross,parse,header
from analyze_vco_bias_band import integral
from analyze_retimer_transient_noise_control import physical,edge_band_power
from transient_diagnostics import recovery,effective
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    pp=H/'results/retimer_delayed_noise_protocol.json';p=json.loads(pp.read_text())
    old=json.loads((H/'results/retimer_transient_noise_protocol.json').read_text());src=ROOT/old['source_result']
    assert sha(src)==old['source_sha256'];pnfile=src.parent/(src.parent.name+'.raw')/'pnMedge.0.sample.pnoise'
    assert sha(pnfile)==old['source_noise_sha256'];pn=parse(pnfile)
    psd=pn['out']**2/header(pnfile,'slew rate event_1')**2
    reference=(H/'tb/retimer_tran_noise_direct_tt.scs').read_text();rows=[];edges={}
    for c in p['cases']:
        row=dict(c,completed=False);rows.append(row);j=R/c['run']/c['case'];rp=j/'result.json'
        if not rp.exists():continue
        r=json.loads(rp.read_text())
        if not r.get('local_outputs_sha256'):continue
        log=(j/'spectre.out').read_text();d=recovery(log)
        row.update(source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),recovery=d)
        if not r['ok']:row['errors']=r['errors'];continue
        assert r['remote_inputs_match'] and not r.get('native_state')
        body=(j/'inputs'/(c['case']+'.scs')).read_text();assert physical(body)==physical(reference)
        assert all(sha(j/'inputs'/k)==v for k,v in r['inputs_sha256'].items())
        assert {k:v for k,v in r['inputs_sha256'].items() if k!=c['case']+'.scs'}==old['dependencies_sha256']
        assert 'tran noise is turning OFF on time 0.000000e+00' in log
        assert ('tran noise is turning ON' in log)==c['noise_enabled']
        eff=effective(log);assert eff['reltol']==1e-6 and eff['abstol(V)']==1e-9 and eff['abstol(I)']==1e-15
        assert eff['maxstep']==float(c['maxstep'][:-1])*1e-12 and eff['noisefmax']==c['noisefmax']
        cache=j/'waveforms.npz';assert sha(cache)==r['local_outputs_sha256'][cache.name]
        with np.load(cache) as z:t,y=z['time'],z['out']
        assert t[0]==0 and t[-1]>=p['stop_s']-1e-15
        e=cross(t,y,.6);e=e[e>=p['measurement_start_s']][:p['edge_count']]
        assert len(e)==p['edge_count'] and np.all(abs(np.diff(e)*p['output_hz']-1)<.2)
        edges[c['run']]=e
        row.update(completed=True,effective=eff,cache_sha256=sha(cache),log_sha256=sha(j/'spectre.out'))
    out=dict(scope=__doc__,protocol_sha256=sha(pp),cases=rows,complete=all(r['completed'] for r in rows),
        deterministic_floor_passed=False,passed=False,full_pll_acceptance=False,limitations=p['limitations'])
    if 'rtdelayoff025' in edges:
        base=edges['rtdelayoff025'];fs=p['output_hz'];grid=edge_band_power(np.zeros(len(base)),fs,*p['band_hz'])
        expected=float(np.sqrt(integral(pn['freq'],psd,grid['lower'],grid['upper']))*1e15)
        out.update(effective_band_hz=[grid['lower'],grid['upper']],pnoise_expected_fs=expected)
        for r in rows:
            if not r['completed']:continue
            e=edges[r['run']];assert max(abs(e-base))<.25/fs
            v=e-base;v-=np.mean(v);m=edge_band_power(v,fs,*p['band_hz'])
            b=np.mean(m['filtered'].reshape(16,-1)**2,axis=1)
            r.update(rms_fs=float(np.sqrt(m['variance'])*1e15),variance_standard_error_s2=float(np.std(b,ddof=1)/4))
            r['relative_pnoise_error']=r['rms_fs']/expected-1
        by={r['run']:r for r in rows}
        out['deterministic_floor_passed']=all(by[n]['recovery']['numerically_clean'] and by[n]['rms_fs']<p['gate']['floor_fs'] for n in ['rtdelayoff05','rtdelayoff025'])
        if out['complete']:
            ratio=lambda a,b:by['rtdelay'+a]['rms_fs']/by['rtdelay'+b]['rms_fs']-1
            changes=dict(bandwidth=ratio('160g05','80g05'),step=ratio('160g025','160g05'),seed=ratio('160g025s29','160g025'))
            checks=dict(no_recovery=all(r['recovery']['numerically_clean'] for r in rows),floor=out['deterministic_floor_passed'],
                bandwidth=abs(changes['bandwidth'])<p['gate']['refinement_change'],step=abs(changes['step'])<p['gate']['refinement_change'],
                pnoise=all(abs(by['rtdelay'+s]['relative_pnoise_error'])<p['gate']['relative_pnoise_error'] for s in ['160g025','160g025s29']))
            out.update(comparisons=changes,checks=checks,passed=all(checks.values()))
    (H/'results/retimer_delayed_noise_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
