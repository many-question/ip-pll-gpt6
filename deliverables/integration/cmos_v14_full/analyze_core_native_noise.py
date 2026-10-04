"""Validate fresh PSS and three actual-core noise points; never infer full-band RMS."""
from pathlib import Path
import argparse,hashlib,json,re
import numpy as np
from noise_utils import parse,devices,header,cross,stream_selected
from psf_trace_units import trace_units
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dac-discharge',action='store_true');a=ap.parse_args()
    label='core_dac_discharge_noise' if a.dac_discharge else 'core_native_noise'
    pp=H/'results'/(label+'_protocol.json');p=json.loads(pp.read_text())
    j=ROOT/'research/runs/spectre_cmos_v14_full'/p['run']/p['case'];rp=j/'result.json'
    if not rp.exists() or not json.loads(rp.read_text()).get('local_outputs_sha256'):print('Fresh core PSS/noise pending');return
    r=json.loads(rp.read_text());log=(j/'spectre.out').read_text()
    assert r['remote_inputs_match'] and not r.get('periodic_state')
    assert all(sha(j/'inputs'/k)==v for k,v in r['inputs_sha256'].items())
    physical={k:v for k,v in r['inputs_sha256'].items() if k.endswith(('.scs','.va')) and k!=j.name+'.scs'}
    assert physical==p['physical_dependencies_sha256'] and r['inputs_sha256'][p.get('initial_state_file',j.name+'.ic')]==p['seed_sha256']
    out=dict(scope=__doc__,condition=p['condition'],source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),
        protocol_sha256=sha(pp),log_sha256=sha(j/'spectre.out'),wrapper_errors=r['errors'],
        simulator_completed=bool(r['ok'] and 'spectre completes with 0 errors' in log),
        pss_achieved='The steady-state solution was achieved' in log,
        convergence_norms=[float(x) for x in re.findall(r'Conv norm = ([0-9.eE+-]+)',log)],
        periodic_checks_passed=False,noise_points_valid=False,full_pll_acceptance=False,
        integrated_jitter_fs=None,limitations=p['limitations'])
    if out['simulator_completed'] and out['pss_achieved']:
        raw=j/(j.name+'.raw');tp=raw/'pss.td.pss';units=trace_units(tp)
        td,duplicates=stream_selected(tp,list(units));fd=parse(raw/'pss.fd.pss')
        t=td['time'];T=t[-1]-t[0];assert abs(T*4e6-1)<1e-7
        expected=p['expected_rising_edges_per_period'];branches=[]
        for k,count in expected.items():
            e=cross(t,td[k]);fund=fd['freq'][1];actual=int(round(fd['freq'][1+np.argmax(abs(fd[k][1:]))]/fund))
            branches.append(dict(node=k,rising_edges=len(e),expected=count,dominant_harmonic=actual,passed=len(e)==count and actual==count))
        # The RF differential carrier is harmonic984 of the driven4MHz period.
        rf_harm=int(round(fd['freq'][1+np.argmax(abs((fd['XP.vp']-fd['XP.vn'])[1:]))]/fd['freq'][1]))
        endpoint=max(float(abs(td[k][-1]-td[k][0])) for k,u in units.items() if u=='V')
        coarse23=all(np.all(td[f'XP.b{k}']>.9) if 23&(1<<k) else np.all(td[f'XP.b{k}']<.3) for k in range(8))
        control_range=[float(min(td['XP.ctrl'])),float(max(td['XP.ctrl']))]
        control_valid=.2<=control_range[0]<=control_range[1]<=1.
        out.update(period_s=float(T),branches=branches,rf_dominant_harmonic=rf_harm,endpoint_max_v=endpoint,
            coarse23_held=bool(coarse23),control_range_v=control_range,control_range_valid=bool(control_valid),
            coalesced_repeated_signal_values=duplicates,td_sha256=sha(tp),fd_sha256=sha(raw/'pss.fd.pss'))
        out['periodic_checks_passed']=bool(all(x['passed'] for x in branches) and rf_harm==984 and endpoint<1e-3 and coarse23 and control_valid)
        if out['periodic_checks_passed']:
            npth=raw/'pnMedge.0.sample.pnoise';pn=parse(npth);f=pn['freq'];slope=header(npth,'slew rate event_1')
            assert slope>0 and np.allclose(f,p['noise_offsets_hz'],rtol=1e-9,atol=0)
            sv=pn['out']**2;dev=devices(npth,len(f));assert np.all(np.isfinite(sv)) and np.all(sv>0)
            closure=float(max(abs(sum(dev.values())/sv-1)));assert closure<1e-7
            groups={}
            for name,s in dev.items():
                # Preserve physical hierarchy instead of assigning unexplained
                # contributions to an intended block by guesswork.
                group='.'.join(name.split('.')[:2]) if name.startswith('XP.') else name.split('.')[0]
                groups[group]=groups.get(group,0)+s/slope**2
            out.update(noise_points_valid=True,offsets_hz=f.tolist(),slew_v_per_s=slope,
                timing_psd_s2_per_hz=(sv/slope**2).tolist(),group_timing_psd_s2_per_hz={k:v.tolist() for k,v in groups.items()},
                device_sum_relative_error=closure,noise_sha256=sha(npth),
                exact_harmonic_flicker_warning='SPCRTRF-15037' in log,
                core_period_average_supply_mw=float(-1.2*np.trapezoid(td['VDD:p'],t)/T*1e3))
    (H/'results'/(label+'_validation.json')).write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['branches','group_timing_psd_s2_per_hz']},indent=2))

if __name__=='__main__':main()
