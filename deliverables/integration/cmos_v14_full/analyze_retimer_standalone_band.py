"""Integrate standalone RT4 device noise and compare two numerical settings."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from noise_utils import parse,header,devices,cross,selected_device_components
from analyze_vco_bias_band import integral
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
R=ROOT/'research/runs/spectre_cmos_v14_full';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    pp=H/'results/retimer_standalone_band_protocol.json';p=json.loads(pp.read_text());rows=[];spectra=[];deps=[];nets=[]
    assert sha(H/'results/retimer_period_noise_validation.json')==p['source_validation_sha256']
    lo,hi=p['integration_band_hz']
    for c in p['cases']:
        j=R/c['run']/c['case'];rp=j/'result.json'
        if not rp.exists() or not json.loads(rp.read_text()).get('local_outputs_sha256'):
            print('Standalone RT4 full-band result pending: '+c['case']);return
        r=json.loads(rp.read_text());log=(j/'spectre.out').read_text();assert r['ok'] and r['remote_inputs_match']
        assert 'The steady-state solution was achieved' in log and 'spectre completes with 0 errors' in log
        assert not r.get('periodic_state') and all(sha(j/'inputs'/k)==v for k,v in r['inputs_sha256'].items())
        deps.append({k:v for k,v in r['inputs_sha256'].items() if k!=j.name+'.scs'})
        tb=(j/'inputs'/(j.name+'.scs')).read_text()
        if c['grade']=='finer':tb=tb.replace('harms=256','harms=128').replace('maxstep=0.25p','maxstep=0.5p').replace('maxacfreq=1008G','maxacfreq=504G').replace('maxsideband=256','maxsideband=128')
        nets.append(re.sub(r'\b(writefinal|writepss)="[^"]+"',r'\1="RUN_LOCAL_PATH"',tb))
        raw=j/(j.name+'.raw');td=parse(raw/'pss.td.pss');fd=parse(raw/'pss.fd.pss');t=td['time'];T=t[-1]-t[0]
        assert abs(T*984e6-1)<1e-7 and len(cross(t,td['out']))==1 and len(cross(t,td['clk']))==4
        assert 1+np.argmax(abs(fd['out'][1:]))==1 and 1+np.argmax(abs(fd['clk'][1:]))==4
        endpoint=max(float(abs(td[n][-1]-td[n][0])) for n in p['waveform_nodes']);assert endpoint<1e-3
        path=raw/'pnMedge.0.sample.pnoise';pn=parse(path);f=pn['freq'];sv=pn['out']**2;slope=header(path,'slew rate event_1')
        assert slope>0 and header(path,'sample ratio factor')==1 and len(f)>=90
        assert abs(f[0]/lo-1)<1e-9 and abs(f[-1]/hi-1)<1e-9 and np.all(np.diff(f)>0) and np.all(np.isfinite(sv)) and np.all(sv>0)
        st=sv/slope**2;dev=devices(path,len(f));closure=float(max(abs(sum(dev.values())/sv-1)));assert closure<1e-7
        groups={name:np.zeros(len(f)) for name in ['retimer_ff','first_buffer','last_buffer']}
        names=[]
        for n,value in dev.items():
            key='retimer_ff' if n.startswith('XR.XFF.') else 'first_buffer' if n.startswith('XR.X0.') else 'last_buffer' if n.startswith('XR.X1.') else None
            assert key,n;groups[key]+=value/slope**2;names.append(n)
        typed=selected_device_components(path,names,len(f));thermal=np.zeros(len(f));flicker=np.zeros(len(f));other=np.zeros(len(f))
        for n,v in typed.items():
            for key,value in v.items():
                if key=='total':continue
                if key=='fn':flicker+=value/slope**2
                elif key=='id':thermal+=value/slope**2
                else:other+=value/slope**2
        total=integral(f,st,lo,hi);gv={k:integral(f,v,lo,hi) for k,v in groups.items()};assert abs(sum(gv.values())/total-1)<1e-7
        rows.append(dict(case=c['case'],grade=c['grade'],source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),
            frequency_points=len(f),slew_v_per_s=slope,endpoint_max_v=endpoint,device_sum_relative_error=closure,
            rms_fs=float(np.sqrt(total)*1e15),powerlaw_rms_fs=float(np.sqrt(integral(f,st,lo,hi,True))*1e15),
            group_rms_fs={k:float(np.sqrt(v)*1e15) for k,v in gv.items()},group_variance_fraction={k:v/total for k,v in gv.items()},
            named_component_variance_fraction={k:integral(f,v,lo,hi)/total for k,v in dict(fn=flicker,id=thermal,other=other).items()},
            exact_harmonic_flicker_warning='SPCRTRF-15037' in log,
            noise_sha256=sha(path),td_sha256=sha(raw/'pss.td.pss'),fd_sha256=sha(raw/'pss.fd.pss')))
        spectra.append((f,st))
    assert deps[0]==deps[1] and nets[0]==nets[1] and np.allclose(spectra[0][0],spectra[1][0],rtol=1e-12)
    delta=10*np.log10(spectra[1][1]/spectra[0][1]);rms_change=rows[1]['rms_fs']/rows[0]['rms_fs']-1;limits=p['precision_limits']
    checks=dict(pointwise_psd=bool(max(abs(delta))<limits['max_timing_psd_delta_db']),integrated_rms=bool(abs(rms_change)<limits['max_relative_rms_change']))
    out=dict(scope=__doc__,condition=p['condition'],protocol_sha256=sha(pp),integration_band_hz=[lo,hi],cases=rows,
        physical_inputs_equal=True,offsets_hz=spectra[0][0].tolist(),psd_finer_minus_fine_db=delta.tolist(),
        max_absolute_psd_change_db=float(max(abs(delta))),relative_rms_change=rms_change,precision_checks=checks,precision_passed=all(checks.values()),
        full_pll_acceptance=False,full_pll_jitter_fs=None,main_dut_modified=False,limitations=p['limitations'])
    (H/'results/retimer_standalone_band_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['offsets_hz','psd_finer_minus_fine_db']},indent=2))

if __name__=='__main__':main()
