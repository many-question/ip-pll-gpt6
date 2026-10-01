"""Check sampled-noise normalization against an exact LTI thermal-noise fixture."""
import json,re
import numpy as np
from analyze import H,R,parse,cross

def header(path,key):
    return float(re.search('"'+re.escape(key)+'"\\s+([0-9.eE+\\-]+)',path.read_text())[1])

def main():
    protocol=json.loads((H/'results/sampling_fixture_protocol.json').read_text())
    refinement_path=H/'results/sampling_refinement_protocol.json'
    refinement=json.loads(refinement_path.read_text()) if refinement_path.exists() else None
    configs=dict(protocol['cases']);configs.update(refinement['cases'] if refinement else {})
    rows=[];spectra={};kb=1.380649e-23;temp=300.15;cap=20e-15;res=1000.;carrier=984e6
    amplitude=.5/np.sqrt(1+(2*np.pi*carrier*res*cap)**2)
    analytic_slew=2*np.pi*carrier*amplitude
    for rp in sorted(R.glob('sampling_*/*/result.json')):
        rec=json.loads(rp.read_text());job=rp.parent;name=job.name
        if not rec.get('remote_inputs_match'):continue
        row=dict(case=name,simulator_ok=rec['ok'],valid_frequency_band=name!='sampling_24ratio1',scope='RC tool fixture, not PLL noise');rows.append(row)
        if not rec['ok']:continue
        raw=job/(name+'.raw');p=raw/'pnMedge.0.sample.pnoise';d=parse(p);freq=d['freq'];slew=header(p,'slew rate event_1')
        st=d['out']**2/slew**2;num=float(np.sqrt(np.trapezoid(st,freq)))
        jee=float(parse(raw/'pnMedge.0.Jee.pnoise')['Jee'][0])
        cfg=configs[name];fs=cfg['fund_hz']*cfg['sampleratio'];rho=np.exp(-1/(fs*res*cap))
        # Exact alias sum for a sampled first-order RC noise process.
        sv=2*kb*temp/(cap*fs)*(1-rho*rho)/(1-2*rho*np.cos(2*np.pi*freq/fs)+rho*rho)
        expected=float(np.sqrt(np.trapezoid(sv/analytic_slew**2,freq)))
        wave=parse(raw/'pss.td.pss');t=wave['time'];T=t[-1]-t[0]
        edges=cross(t,wave['out'],.6);mismatch=float(abs(wave['out'][-1]-wave['out'][0]))
        period_ok=bool(abs(T*cfg['fund_hz']-1)<1e-8 and len(edges)==round(carrier/cfg['fund_hz']) and mismatch<1e-3)
        row.update(fund_hz=cfg['fund_hz'],sampleratio=cfg['sampleratio'],declared_sample_rate_hz=fs,band_hz=[float(freq[0]),float(freq[-1])],period_s=float(T),rising_edges=len(edges),periodic_pass=period_ok,endpoint_error_v=mismatch,
            slew_v_per_s=slew,analytic_slew_v_per_s=float(analytic_slew),numeric_fs=num*1e15,spectre_jee_fs=jee*1e15,analytic_fs=expected*1e15,
            numeric_vs_spectre_relative=float(num/jee-1),numeric_vs_analytic_relative=float(num/expected-1))
        clip=freq<=cfg['fund_hz']/2;clipped=float(np.sqrt(np.trapezoid(st[clip],freq[clip])))
        row.update(auto_jee_grid_cutoff_hz=float(freq[clip][-1]),grid_clipped_psd_integral_fs=clipped*1e15,clipped_vs_auto_jee_relative=clipped/jee-1,
            sample_ratio_header=header(p,'sample ratio factor'),full_band_upper_limit_hz=fs/2)
        lim=protocol['limits'];row['valid_correct_case']=bool(row['valid_frequency_band'] and period_ok and abs(num/jee-1)<lim['numeric_vs_spectre_jee'] and abs(num/expected-1)<lim['numeric_vs_analytic'])
        spectra[name+'_f']=freq;spectra[name+'_st']=st;spectra[name+'_analytic_st']=sv/analytic_slew**2
    by={x['case']:x for x in rows};comparison=dict(completed=False,pass_normalization=False)
    if all(k in by for k in ['sampling_984','sampling_24ratio41']):
        a,b=by['sampling_984'],by['sampling_24ratio41'];comparison['completed']=True
        if all(x.get('valid_correct_case') for x in [a,b]):
            rel=b['numeric_fs']/a['numeric_fs']-1
            comparison.update(relative_jitter_change=rel,pass_normalization=abs(rel)<protocol['limits']['correct_cases_relative_jitter_difference'])
    bad=by.get('sampling_24ratio1',{})
    if bad.get('numeric_fs') and by.get('sampling_24ratio41',{}).get('numeric_fs'):
        comparison['negative_control_ratio']=bad['numeric_fs']/by['sampling_24ratio41']['numeric_fs'];comparison['expected_negative_control_ratio']=float(np.sqrt(41))
    psd_check=dict(completed=False,pass_psd_and_clip_diagnostic=False)
    finekeys=['sampling_984_fine','sampling_24ratio41_fine']
    if refinement and all(k in by for k in finekeys) and all(by[k].get('simulator_ok') for k in finekeys):
        aa=[by[k] for k in finekeys];lim=refinement['new_diagnostic_limits'];rel=aa[1]['numeric_fs']/aa[0]['numeric_fs']-1
        psd_check.update(completed=True,between_fundamental_relative=rel,
            pass_psd_and_clip_diagnostic=bool(abs(rel)<lim['between_fundamental_psd_integrals'] and all(x['periodic_pass'] and abs(x['numeric_vs_analytic_relative'])<lim['psd_integral_vs_analytic'] and abs(x['clipped_vs_auto_jee_relative'])<lim['auto_jee_vs_actual_grid_clipped_integral'] for x in aa)))
    result=dict(protocol=protocol,refinement_protocol=refinement,cases=rows,comparison=comparison,refined_psd_diagnostic=psd_check,
        interpretation='In this installed Spectre21.1.0.509 fixture, auto Jee matches the spectrum integrated only over saved frequencies <= PSSfund/2, including when sampleratio41. It must not be relabeled as a10kHz-492MHz integral. Original combined check remains failed.',
        limitation='Validates identical-edge LTI normalization only. Real PLL edges can have phase-dependent slopes/noise; this does not sign off PLL multi-phase noise or substitute for PSS convergence.')
    (H/'results/sampling_fixture_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    np.savez_compressed(H/'results/sampling_fixture_spectra.npz',**spectra)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
