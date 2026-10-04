"""Compare fresh-PSS sideband trials with a completed 2047-sideband spectrum."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from noise_utils import parse,cross,header,devices,selected_device_components
from analyze_vco_bias_band import integral
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
normal=lambda s:re.sub(r'\b(writefinal|writepss)="[^"]+"',r'\1="STATE"',s).strip()

def main():
    pp=H/'results/reference_sideband_screen_protocol.json';p=json.loads(pp.read_text());b=p['baseline_case']
    assert hashlib.sha256(json.dumps(b,sort_keys=True).encode()).hexdigest()==p['baseline_case_snapshot_sha256']
    baseline=ROOT/b['source_result'];assert sha(baseline)==b['source_sha256']
    br=baseline.parent/(baseline.parent.name+'.raw');assert sha(br/'pnMedge.0.sample.pnoise')==b['noise_sha256']
    assert sha(br/'pss.td.pss')==b['td_sha256']
    btd=parse(br/'pss.td.pss');bp=br/'pnMedge.0.sample.pnoise';bn=devices(bp,len(b['offsets_hz']))
    bc=selected_device_components(bp,list(bn),len(b['offsets_hz']))
    bslope=header(bp,'slew rate event_1')
    base_components={n:sum(c[n] for c in bc.values())/bslope**2 for n in ['fn','id']}
    rows=[];lo,hi=p['integration_band_hz']
    for c in p['cases']:
        j=ROOT/'research/runs/spectre_cmos_v14_full'/c['run']/c['case'];rp=j/'result.json';row=dict(case=c['case'],maxsideband=c['maxsideband'],completed=False)
        if not rp.exists() or not json.loads(rp.read_text()).get('local_outputs_sha256'):rows.append(row);continue
        r=json.loads(rp.read_text());log=(j/'spectre.out').read_text()
        row.update(completed=True,source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),
            simulator_passed=bool(r['ok'] and 'spectre completes with 0 errors' in log and 'The steady-state solution was achieved' in log))
        if row['simulator_passed']:
            assert r['remote_inputs_match'] and not r.get('periodic_state')
            assert {k:v for k,v in r['inputs_sha256'].items() if k!=c['case']+'.scs'}==p['dependencies_sha256']
            body=(j/'inputs'/(c['case']+'.scs')).read_text();tb=H/'tb'/(c['case']+'.scs')
            assert sha(tb)==c['tb_sha256'] and normal(body)==normal(tb.read_text())
            assert body.count('maxsideband='+str(c['maxsideband']))==1
            undone=body.replace('maxsideband='+str(c['maxsideband']),'maxsideband=2047')
            assert normal(undone)==normal((baseline.parent/'inputs'/(b['case']+'.scs')).read_text())
            raw=j/(j.name+'.raw');td=parse(raw/'pss.td.pss');t=td['time']
            assert abs((t[-1]-t[0])*24e6-1)<1e-7
            assert len(cross(t,td['out']))==len(cross(t,td['ref']))==1
            endpoint=max(abs(float(td[n][-1]-td[n][0])) for n in ['out','XR.a','XR.b','XR.c']);assert endpoint<1e-3
            wave_difference={n:float(max(abs(td[n]-np.interp(t,btd['time'],btd[n])))) for n in ['ref','out','XR.a','XR.b','XR.c']}
            assert max(wave_difference.values())<1e-5,'Different periodic trajectory requires review before attributing differences to sidebands.'
            path=raw/'pnMedge.0.sample.pnoise';pn=parse(path);f=pn['freq'];sv=pn['out']**2;slew=header(path,'slew rate event_1')
            assert slew>0 and header(path,'sample ratio factor')==1 and np.allclose(f,b['offsets_hz'],rtol=1e-12,atol=0)
            assert np.all(np.isfinite(sv)) and np.all(sv>0)
            closure=float(max(abs(sum(devices(path,len(f)).values())/sv-1)));assert closure<1e-7
            st=sv/slew**2;rms=float(np.sqrt(integral(f,st,lo,hi))*1e15)
            delta=10*np.log10(st/np.array(b['timing_psd_s2_per_hz']));relative=rms/b['rms_fs']-1
            comps=selected_device_components(path,list(devices(path,len(f))),len(f))
            channels={n:sum(c[n] for c in comps.values())/slew**2 for n in ['fn','id']}
            changes={n:dict(max_relative_psd_change=float(max(abs(channels[n]/base_components[n]-1))),
                           baseline_variance_s2=integral(f,base_components[n],lo,hi),trial_variance_s2=integral(f,channels[n],lo,hi)) for n in ['fn','id']}
            row.update(noise_valid=True,rms_fs=rms,max_absolute_psd_change_db=float(max(abs(delta))),relative_rms_change=relative,
                passed=bool(max(abs(delta))<p['precision_limits']['max_psd_change_db'] and abs(relative)<p['precision_limits']['max_relative_rms_change']),
                offsets_hz=f.tolist(),timing_psd_s2_per_hz=st.tolist(),psd_change_db=delta.tolist(),
                noise_sha256=sha(path),td_sha256=sha(raw/'pss.td.pss'),endpoint_max_v=endpoint,device_sum_relative_error=closure,
                periodic_waveform_max_abs_difference_v=wave_difference,component_changes=changes)
        rows.append(row)
    out=dict(scope=__doc__,protocol_sha256=sha(pp),condition=p['condition'],cases=rows,complete=all(x['completed'] for x in rows),
        full_pll_acceptance=False,main_dut_modified=False,baseline_rms_fs=b['rms_fs'],passed_sideband_counts=[x['maxsideband'] for x in rows if x.get('passed')],limitations=p['limitations'])
    (H/'results/reference_sideband_screen_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({**{k:v for k,v in out.items() if k!='cases'},'cases':[{k:v for k,v in r.items() if k not in ['offsets_hz','timing_psd_s2_per_hz','psd_change_db']} for r in rows]},indent=2))

if __name__=='__main__':main()
