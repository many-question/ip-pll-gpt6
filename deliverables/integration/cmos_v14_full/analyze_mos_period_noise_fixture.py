"""Check physical waveform and sparse MOS noise equivalence across PSS periods."""
from pathlib import Path
import argparse,hashlib,json,re
import numpy as np
from noise_utils import parse,header,devices,selected_device_components,cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
R=ROOT/'research/runs/spectre_cmos_v14_full';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--retimer',action='store_true');args=ap.parse_args()
    label='retimer' if args.retimer else 'mos'
    pp=H/'results'/(label+'_period_noise_protocol.json');p=json.loads(pp.read_text());rows=[];spectra=[];waves=[];circuits=[];dependencies=[]
    nodes=p.get('waveform_nodes',['ob','out'])
    for c in p['cases']:
        j=R/c['run']/c['case'];rp=j/'result.json'
        if not rp.exists() or not json.loads(rp.read_text()).get('local_outputs_sha256'):
            print('MOS period comparison pending: '+c['case']);return
        r=json.loads(rp.read_text());log=(j/'spectre.out').read_text();assert r['remote_inputs_match'] and r['ok']
        assert 'The steady-state solution was achieved' in log and 'spectre completes with 0 errors' in log
        assert not r.get('periodic_state') and all(sha(j/'inputs'/k)==v for k,v in r['inputs_sha256'].items())
        tb=(j/'inputs'/(j.name+'.scs')).read_text();circuits.append(tb.split('pss pss ')[0])
        dependencies.append({k:v for k,v in r['inputs_sha256'].items() if k!=j.name+'.scs'})
        raw=j/(j.name+'.raw');path=raw/'pnMedge.0.sample.pnoise';pn=parse(path);f=pn['freq'];sv=pn['out']**2
        slope=header(path,'slew rate event_1');ratio=header(path,'sample ratio factor');assert slope>0 and ratio==c['ratio']
        assert np.allclose(f,p['offsets_hz'],rtol=1e-12,atol=0)
        dev=devices(path,len(f));assert np.all(sv>0) and np.all(np.isfinite(sv))
        closure=float(max(abs(sum(dev.values())/sv-1)));assert closure<1e-7
        td=parse(raw/'pss.td.pss');t=td['time'];T=t[-1]-t[0];edges=cross(t,td['out']);inp=cross(t,td['in'])
        assert abs(T*c['fund_hz']-1)<1e-7 and len(edges)==c['ratio'] and len(inp)==c['ratio']
        endpoint=max(float(abs(td[k][-1]-td[k][0])) for k in ['in']+nodes);assert endpoint<1e-3
        if p.get('clock_node'):assert len(cross(t,td[p['clock_node']]))==c['ratio']*p['clock_ratio']
        fd=parse(raw/'pss.fd.pss');dominant=int(np.argmax(abs(fd['out'][1:]))+1);assert dominant==c['ratio']
        typed=selected_device_components(path,list(dev),len(f))
        row=dict(case=c['case'],source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),ratio=ratio,
            pss_period_s=float(T),rising_edges=len(edges),output_dominant_harmonic=dominant,endpoint_max_v=endpoint,
            slew_v_per_s=slope,timing_psd_s2_per_hz=(sv/slope**2).tolist(),device_sum_relative_error=closure,
            device_timing_psd_s2_per_hz={k:(v/slope**2).tolist() for k,v in dev.items()},
            flicker_timing_psd_s2_per_hz={k:(v.get('fn',np.zeros_like(f))/slope**2).tolist() for k,v in typed.items()},
            exact_harmonic_flicker_warning='SPCRTRF-15037' in log,
            noise_sha256=sha(path),td_sha256=sha(raw/'pss.td.pss'),fd_sha256=sha(raw/'pss.fd.pss'))
        rows.append(row);spectra.append(sv/slope**2);waves.append((td,inp))
    assert circuits[0]==circuits[1] and dependencies[0]==dependencies[1]
    # Compare every output cycle using the input edge as a common phase origin.
    # Periodic extension uses accepted PSS endpoints, never extrapolation.
    T=1/984e6;grid=np.linspace(0,T,10001,endpoint=False);cycle_rows=[]
    td0,inp0=waves[0];x0=td0['time']-inp0[0]
    ref=lambda k:np.interp(grid,np.concatenate([x0-T,x0,x0+T]),np.tile(td0[k],3))
    td1,inp1=waves[1];tt=td1['time'];period=tt[-1]-tt[0]
    for i,e in enumerate(inp1):
        x=tt-e;differences={}
        for k in nodes:
            v=np.interp(grid,np.concatenate([x-period,x,x+period]),np.tile(td1[k],3))
            differences[k]=float(max(abs(v-ref(k))))
        cycle_rows.append(dict(edge=i+1,voltage_peak_difference_v=differences))
    delta=10*np.log10(spectra[1]/spectra[0]);slew=rows[1]['slew_v_per_s']/rows[0]['slew_v_per_s']-1
    peak=max(v for x in cycle_rows for v in x['voltage_peak_difference_v'].values());limits=p['comparison_limits']
    checks=dict(timing_psd=bool(max(abs(delta))<limits['max_timing_psd_delta_db']),
        slew=bool(abs(slew)<limits['max_relative_slew_difference']),waveform=bool(peak<limits['max_waveform_difference_v']))
    out=dict(scope=__doc__,condition=p['condition'],protocol_sha256=sha(pp),physical_inputs_equal=True,cases=rows,
        offsets_hz=p['offsets_hz'],timing_psd_ratio6_minus_ratio1_db=delta.tolist(),relative_slew_change=slew,
        cycle_waveform_comparisons=cycle_rows,max_waveform_difference_v=peak,checks=checks,passed=all(checks.values()),
        sparse_calibration_only=True,integrated_jitter_fs=None,full_pll_acceptance=False,limitations=p['limitations'])
    (H/'results'/(label+'_period_noise_validation.json')).write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['cases','cycle_waveform_comparisons']},indent=2))

if __name__=='__main__':main()
