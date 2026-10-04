"""Assess paired-corner functionality and integrated noise of standalone RT4."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from noise_utils import parse,header,devices,cross
from analyze_vco_bias_band import integral
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
normal=lambda b:re.sub(r'\b(writefinal|writepss)="[^"]+"',r'\1="RUN_LOCAL_PATH"',b)

def main():
    pp=H/'results/retimer_standalone_pvt_protocol.json';p=json.loads(pp.read_text());proof=H/'results/retimer_standalone_band_validation.json'
    assert sha(proof)==p['source_validation_sha256'];v=json.loads(proof.read_text());tt=v['cases'][1];base=(ROOT/tt['source_result']).parent
    base_result=json.loads((base/'result.json').read_text());base_tb=normal((base/'inputs'/(base.name+'.scs')).read_text())
    deps={k:x for k,x in base_result['inputs_sha256'].items() if k!=base.name+'.scs'};rows=[]
    lo,hi=p['integration_band_hz'];lim=p['limits']
    for c in p['cases']:
        j=R/c['run']/c['case'];rp=j/'result.json'
        if not rp.exists() or not json.loads(rp.read_text()).get('local_outputs_sha256'):
            print('Standalone RT4 corner pending: '+c['case']);return
        r=json.loads(rp.read_text());log=(j/'spectre.out').read_text();assert r['remote_inputs_match']
        assert all(sha(j/'inputs'/k)==x for k,x in r['inputs_sha256'].items()) and not r.get('periodic_state')
        assert deps=={k:x for k,x in r['inputs_sha256'].items() if k!=j.name+'.scs'}
        tb=normal((j/'inputs'/(j.name+'.scs')).read_text()).replace('section='+c['corner']+'\n','section=tt\n').replace(f"temp={c['temp_c']} ",'temp=27 ')
        assert tb==base_tb
        row=dict(case=c['case'],corner=c['corner'],temp_c=c['temp_c'],source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),
            simulator_completed=bool(r['ok'] and 'spectre completes with 0 errors' in log),
            pss_converged='The steady-state solution was achieved' in log,function_passed=False,noise_valid=False,integrated_jitter_fs=None)
        if row['simulator_completed'] and row['pss_converged']:
            raw=j/(j.name+'.raw');td=parse(raw/'pss.td.pss');fd=parse(raw/'pss.fd.pss');t=td['time'];T=t[-1]-t[0]
            edges=len(cross(t,td['out']));clocks=len(cross(t,td['clk']));endpoint=max(float(abs(td[n][-1]-td[n][0])) for n in ['out','XR.qb','XR.ob','XR.XFF.a','XR.XFF.b'])
            rail=np.quantile(td['out'],[.1,.9]);harmonic=1+np.argmax(abs(fd['out'][1:]));assert abs(T*984e6-1)<1e-7
            row.update(output_rising_edges=edges,rf_clock_rising_edges=clocks,endpoint_peak_v=endpoint,output_10_90_percentile_v=rail.tolist(),dominant_output_harmonic=int(harmonic))
            row['function_passed']=bool(edges==1 and clocks==4 and harmonic==1 and endpoint<lim['endpoint_peak_v'] and rail[0]<=lim['low_max_v'] and rail[1]>=lim['high_min_v'])
            if row['function_passed']:
                path=raw/'pnMedge.0.sample.pnoise';pn=parse(path);f=pn['freq'];sv=pn['out']**2;slope=header(path,'slew rate event_1')
                assert len(f)>=90 and abs(f[0]/lo-1)<1e-9 and abs(f[-1]/hi-1)<1e-9 and slope>0 and header(path,'sample ratio factor')==1
                assert np.all(np.isfinite(sv)) and np.all(sv>0) and np.all(np.diff(f)>0)
                dev=devices(path,len(f));closure=float(max(abs(sum(dev.values())/sv-1)));assert closure<1e-7
                groups={n:np.zeros(len(f)) for n in ['retimer_ff','first_buffer','last_buffer']}
                for name,value in dev.items():
                    group='retimer_ff' if name.startswith('XR.XFF.') else 'first_buffer' if name.startswith('XR.X0.') else 'last_buffer' if name.startswith('XR.X1.') else None
                    assert group,name;groups[group]+=value/slope**2
                total=integral(f,sv/slope**2,lo,hi);parts={k:integral(f,x,lo,hi) for k,x in groups.items()};assert abs(sum(parts.values())/total-1)<1e-7
                row.update(noise_valid=True,integrated_jitter_fs=float(np.sqrt(total)*1e15),powerlaw_rms_fs=float(np.sqrt(integral(f,sv/slope**2,lo,hi,True))*1e15),
                    group_rms_fs={k:float(np.sqrt(x)*1e15) for k,x in parts.items()},slew_v_per_s=slope,device_sum_relative_error=closure,
                    exact_harmonic_flicker_warning='SPCRTRF-15037' in log,noise_sha256=sha(path),td_sha256=sha(raw/'pss.td.pss'),
                    relative_to_tt_rms=float(np.sqrt(total)*1e15/tt['rms_fs']-1))
        rows.append(row)
    out=dict(scope=__doc__,condition=p['condition'],protocol_sha256=sha(pp),source_tt_validation_sha256=sha(proof),integration_band_hz=[lo,hi],
        tt_rms_fs=tt['rms_fs'],cases=rows,function_all_passed=all(x['function_passed'] for x in rows),noise_all_valid=all(x['noise_valid'] for x in rows),
        independent_corner_precision_passed=False,full_pll_acceptance=False,full_pll_jitter_fs=None,limitations=p['limitations'])
    (H/'results/retimer_standalone_pvt_validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))

if __name__=='__main__':main()
