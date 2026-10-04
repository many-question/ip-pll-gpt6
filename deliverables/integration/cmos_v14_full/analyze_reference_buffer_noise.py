"""Measure standalone reference-buffer transitions and sampled-device edge noise."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from noise_utils import parse,cross,header,devices
from analyze_vco_bias_band import integral
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    pp=H/'results/reference_buffer_noise_protocol.json';p=json.loads(pp.read_text())
    assert sha(H/'results'/p['source_noise_validation'])==p['source_noise_validation_sha256']
    rows=[];lo,hi=p['integration_band_hz']
    for c in p['cases']:
        j=R/c['run']/c['case'];rp=j/'result.json';row=dict(case=c['case'],variant=c['variant'],completed=False)
        if not rp.exists() or not json.loads(rp.read_text()).get('local_outputs_sha256'):rows.append(row);continue
        r=json.loads(rp.read_text());log=(j/'spectre.out').read_text()
        row.update(completed=True,source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),
                   simulator_passed=bool(r['ok'] and 'spectre completes with 0 errors' in log and 'The steady-state solution was achieved' in log))
        if row['simulator_passed']:
            assert r['remote_inputs_match'] and not r.get('periodic_state')
            assert all(sha(j/'inputs'/k)==v for k,v in r['inputs_sha256'].items())
            assert {k:v for k,v in r['inputs_sha256'].items() if k!=j.name+'.scs'}==c['dependencies_sha256']
            raw=j/(j.name+'.raw');td=parse(raw/'pss.td.pss');fd=parse(raw/'pss.fd.pss');t=td['time'];T=t[-1]-t[0]
            assert abs(T*24e6-1)<1e-7
            inputs=cross(t,td['ref']);outputs=cross(t,td['out']);endpoint=max(float(abs(td[n][-1]-td[n][0])) for n in ['out','XR.a','XR.b','XR.c'])
            assert len(inputs)==len(outputs)==1 and int(1+np.argmax(abs(fd['out'][1:])))==1
            assert endpoint<1e-3 and min(td['out'])<.2 and max(td['out'])>1
            delay=float((outputs[0]-inputs[0])%T);assert delay<T/10
            rise=[cross(t,td['out'],v) for v in [.12,1.08]];fall=[cross(t,-td['out'],-v) for v in [1.08,.12]]
            assert all(len(x)==1 for x in rise+fall)
            path=raw/'pnMedge.0.sample.pnoise';pn=parse(path);f=pn['freq'];sv=pn['out']**2;slew=header(path,'slew rate event_1')
            assert len(f)>=60 and np.all(np.diff(f)>0) and np.all(np.isfinite(sv)) and np.all(sv>0)
            assert abs(f[0]/lo-1)<1e-9 and abs(f[-1]/hi-1)<1e-9 and slew>0 and header(path,'sample ratio factor')==1
            dev=devices(path,len(f));closure=float(max(abs(sum(dev.values())/sv-1)));assert closure<1e-7
            groups={k:np.zeros(len(f)) for k in range(4)}
            for name,value in dev.items():
                match=re.fullmatch(r'XR\.X([0-3])\.M[NP]',name);assert match,name
                groups[int(match[1])]+=value/slew**2
            st=sv/slew**2;variance=integral(f,st,lo,hi);parts={str(k):integral(f,x,lo,hi) for k,x in groups.items()}
            assert abs(sum(parts.values())/variance-1)<1e-9
            row.update(periodic_passed=True,noise_valid=True,rms_fs=float(np.sqrt(variance)*1e15),
                       powerlaw_rms_fs=float(np.sqrt(integral(f,st,lo,hi,True))*1e15),
                       stage_rms_fs={k:float(np.sqrt(x)*1e15) for k,x in parts.items()},
                       stage_variance_fraction={k:x/variance for k,x in parts.items()},device_sum_relative_error=closure,
                       output_rise_10_90_ps=float((rise[1][0]-rise[0][0])%T*1e12),
                       output_fall_90_10_ps=float((fall[1][0]-fall[0][0])%T*1e12),
                       delay_ps=delay*1e12,duty=float(np.trapezoid((td['out']>.6).astype(float),t)/T),
                       mean_supply_current_a=float(-np.trapezoid(td['VDD:p'],t)/T),input_peak_current_a=float(max(abs(td['VR:p']))),
                       slew_v_per_s=slew,endpoint_max_v=endpoint,offsets_hz=f.tolist(),timing_psd_s2_per_hz=st.tolist(),
                       noise_sha256=sha(path),td_sha256=sha(raw/'pss.td.pss'),fd_sha256=sha(raw/'pss.fd.pss'))
        rows.append(row)
    out=dict(scope=__doc__,protocol_sha256=sha(pp),condition=p['condition'],integration_band_hz=[lo,hi],cases=rows,
             complete=all(x['completed'] for x in rows),noise_all_valid=all(x.get('noise_valid',False) for x in rows),
             independent_precision_verified=False,full_pll_acceptance=False,main_dut_modified=False,limitations=p['limitations'])
    if out['noise_all_valid']:
        b,c=rows;assert np.allclose(b['offsets_hz'],c['offsets_hz'],rtol=1e-12,atol=0)
        out.update(candidate_relative_rms_change=c['rms_fs']/b['rms_fs']-1,
                   candidate_timing_psd_change_db=(10*np.log10(np.array(c['timing_psd_s2_per_hz'])/b['timing_psd_s2_per_hz'])).tolist())
    (H/'results/reference_buffer_noise_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({**{k:v for k,v in out.items() if k not in ['cases','candidate_timing_psd_change_db']},'cases':[{k:v for k,v in r.items() if k not in ['offsets_hz','timing_psd_s2_per_hz']} for r in rows]},indent=2))

if __name__=='__main__':main()
