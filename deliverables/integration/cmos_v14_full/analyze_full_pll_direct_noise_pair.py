"""Measure complete-PLL high-offset random edge noise against a matched quiet trace."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from noise_utils import cross
from transient_diagnostics import effective,recovery
from analyze_retimer_transient_noise_control import edge_band_power
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument('--protocol',default='full_pll_direct_noise_pair_protocol.json')
    args=cli.parse_args();assert Path(args.protocol).name==args.protocol and args.protocol.endswith('_protocol.json')
    pp=H/'results'/args.protocol;p=json.loads(pp.read_text());rows=[];datasets={}
    values={}
    for line in (H/'state_inputs'/p['text_state']).read_text().splitlines():
        if line.strip() and not line.startswith('#'):
            z=line.split();values[z[0]]=float(z[1])
    for c in p['cases']:
        row=dict(c,completed=False);rows.append(row);j=R/c['run']/c['case'];rp=j/'result.json'
        if not rp.exists():continue
        r=json.loads(rp.read_text())
        if not r.get('local_outputs_sha256'):continue
        log=(j/'spectre.out').read_text();rec=recovery(log);eff=effective(log)
        row.update(source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),recovery=rec,effective=eff,log_sha256=sha(j/'spectre.out'))
        if not r['ok']:row['errors']=r['errors'];continue
        assert r['remote_inputs_match'] and not r.get('native_state')
        assert all(sha(j/'inputs'/k)==v for k,v in r['inputs_sha256'].items())
        assert eff['reltol']==p['reltol'] and eff['abstol(V)']==p['vabstol'] and eff['abstol(I)']==p['iabstol'] and eff['maxstep']==p['maxstep_s'] and eff['noisefmax']==p['noisefmax_hz']
        assert ('tran noise is turning ON' in log)==c['noise_enabled']
        cache=j/'waveforms.npz';assert sha(cache)==r['local_outputs_sha256'][cache.name]
        with np.load(cache) as z:d={k:z[k] for k in z.files if k!='units'}
        assert d['time'][0]==0 and d['time'][-1]>=p['stop_s']-1e-15
        delta={k:abs(float(d[k][0])-values[k]) for k in d if k in values and ':' not in k}
        sel=d['time']>=p['measurement_start_s'];t=d['time'];good=all(np.min(d[k][sel])>1.0 for k in ['qualified','frequency_good','cfg_ready','amp_good','XP.XC.phase_held','XP.XC.acquired','XP.en']) and max(abs(d['range_error'][sel]))<.2
        row.update(completed=True,cache_sha256=sha(cache),initial_maximum_voltage_difference_v=max(delta.values()),compared_nodes=len(delta),status_stable=bool(good))
        datasets[c['run']]=d
        if not c['noise_enabled']:
            rf=cross(t,d['XP.vp']-d['XP.vn'],0);out=cross(t,d['out'],.6);refs=cross(t,d['XP.refb'],.6)
            refs=refs[(refs>p['stop_s']-1e-6)&(refs<min(rf[-1],out[-1]))]
            urf=np.interp(refs,rf,np.arange(len(rf)));uout=np.interp(refs,out,np.arange(len(out)))
            phase=np.unwrap(2*np.pi*(urf-np.floor(urf)))
            s=dict(samples=len(refs),phase_pp_rad=float(np.ptp(phase)),phase_drift_rad_per_us=float(np.polyfit(refs*1e6,phase,1)[0]),
                maximum_rf_cycles_error=float(max(abs(np.diff(urf)-164))),maximum_out_cycles_error=float(max(abs(np.diff(uout)-41))),
                mean_output_mhz=float(np.mean(np.diff(uout))*24))
            s['passed']=bool(len(refs)>=23 and s['phase_pp_rad']<.02 and abs(s['phase_drift_rad_per_us'])<.01 and s['maximum_rf_cycles_error']<.001 and s['maximum_out_cycles_error']<.001)
            row['stationarity']=s
    result=dict(scope=__doc__,protocol_sha256=sha(pp),condition=p['condition'],cases=rows,complete=all(r['completed'] for r in rows),
        high_offset_diagnostic_valid=False,full_pll_acceptance=False,integrated_10khz_jitter_fs=None,limitations=p['limitations'])
    if result['complete']:
        base=datasets[p['cases'][0]['run']];noisy=datasets[p['cases'][1]['run']];es=[]
        for d in [base,noisy]:
            e=cross(d['time'],d['out'],.6);e=e[e>=p['measurement_start_s']][:p['edge_count']]
            assert len(e)==p['edge_count'] and np.all(abs(np.diff(e)*p['output_hz']-1)<.2);es.append(e)
        assert max(abs(es[1]-es[0]))<.25/p['output_hz']
        residual=es[1]-es[0];residual-=np.mean(residual);m=edge_band_power(residual,p['output_hz'],*p['band_hz'])
        blocks=np.mean(m['filtered'].reshape(16,-1)**2,axis=1)
        q=base['time']<p['noise_start_s']-10e-9
        prefix={k:float(max(abs(base[k][q]-np.interp(base['time'][q],noisy['time'],noisy[k])))) for k in ['XP.ctrl','out','qualified']}
        checks=dict(clean=all(r['recovery']['numerically_clean'] for r in rows),initialization=all(r['initial_maximum_voltage_difference_v']<1e-9 for r in rows),
            quiet_prefix=max(prefix.values())<1e-6,status=all(r['status_stable'] for r in rows),stationary=rows[0]['stationarity']['passed'])
        result.update(diagnostic_band_rms_fs=float(np.sqrt(m['variance'])*1e15),effective_band_hz=[m['lower'],m['upper']],
            block_variance_standard_error_s2=float(np.std(blocks,ddof=1)/4),prefix_max_differences_v=prefix,checks=checks,high_offset_diagnostic_valid=all(checks.values()))
    (H/'results'/args.protocol.replace('_protocol.json','_validation.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
