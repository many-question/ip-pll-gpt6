"""Compare selected-event spectra with full-rate and once-per-PSS analytic covariance."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from noise_utils import parse,header,devices,cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((H/'results/noise_correlation_control_protocol.json').read_text());rows=[];freq=np.asarray(p['offsets_hz'])
fs=p['sample_frequency_hz'];tau=p['resistance_ohm']*p['capacitance_f'];variance=1.380649e-23*p['temperature_k']/p['capacitance_f']
amp=p['input_amplitude_v']/np.sqrt(1+(2*np.pi*fs*tau)**2);slope_expected=2*np.pi*fs*amp
def analytic(fsamp):
    rho=np.exp(-1/(fsamp*tau))
    return 2*variance/fsamp*(1-rho*rho)/(1-2*rho*np.cos(2*np.pi*freq/fsamp)+rho*rho)/slope_expected**2
full=analytic(fs)
for item in p['cases']:
    j=ROOT/'research/runs/spectre_cmos_v14_full'/p['run']/item['case'];rp=j/'result.json'
    if not rp.exists():continue
    r=json.loads(rp.read_text())
    if not r.get('local_outputs_sha256'):continue
    row=dict(case=item['case'],source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),passed=False);rows.append(row)
    if not r['ok']:continue
    log=(j/'spectre.out').read_text();assert r['remote_inputs_match'] and 'spectre completes with 0 errors' in log and 'The steady-state solution was achieved' in log
    tb=H/'tb'/(item['case']+'.scs');assert sha(tb)==item['tb_sha256'] and tb.read_text()==(j/'inputs'/tb.name).read_text()
    raw=j/(j.name+'.raw');td=parse(raw/'pss.td.pss');t=td['time'];edges=cross(t,td['out'])
    period_ok=bool(abs((t[-1]-t[0])*item['fund_hz']-1)<p['limits']['period_relative'] and len(edges)==item['sample_ratio'] and abs(td['out'][-1]-td['out'][0])<p['limits']['endpoint_v'])
    path=raw/'pnMedge.0.sample.pnoise';pn=parse(path);assert np.allclose(pn['freq'],freq,rtol=1e-10,atol=0)
    slope=header(path,'slew rate event_1');ratio=header(path,'sample ratio factor');assert ratio==item['sample_ratio'] and slope>0
    sv=pn['out']**2;dev=devices(path,len(freq));closure=float(max(abs(sum(dev.values())/sv-1)));assert closure<p['limits']['device_sum_relative']
    st=sv/slope**2;alternate=analytic(item['fund_hz'])/item['sample_ratio'];db=10*np.log10(st/full);adb=10*np.log10(st/alternate)
    row.update(periodic_passed=period_ok,sample_ratio=ratio,rising_edges=len(edges),slew_v_per_s=slope,analytic_slew_v_per_s=slope_expected,
        timing_psd_s2_per_hz=st.tolist(),full_rate_analytic_s2_per_hz=full.tolist(),once_per_pss_normalized_analytic_s2_per_hz=alternate.tolist(),
        full_rate_error_db=db.tolist(),once_per_pss_error_db=adb.tolist(),max_full_rate_error_db=float(max(abs(db))),max_once_per_pss_error_db=float(max(abs(adb))),
        device_sum_relative_error=closure,raw_noise_sha256=sha(path),passed=bool(period_ok and max(abs(db))<p['limits']['point_psd_error_db']))
out=dict(scope=__doc__,offsets_hz=freq.tolist(),cases=rows,complete=len(rows)==2,passed=False,
    random_jitter_integral_measured=False,full_pll_acceptance=False,interpretation='Pointwise correlation/alias diagnostic only. No RMS from sparse points; no automatic transplantation to MOS acceptance.')
if out['complete'] and all('timing_psd_s2_per_hz' in r for r in rows):
    a,b=rows;diff=10*np.log10(np.asarray(b['timing_psd_s2_per_hz'])/np.asarray(a['timing_psd_s2_per_hz']))
    out['ratio6_minus_ratio1_db']=diff.tolist();out['max_ratio_psd_difference_db']=float(max(abs(diff)))
    out['passed']=bool(all(r['passed'] for r in rows) and max(abs(diff))<p['limits']['ratio1_to_ratio6_psd_db'])
(H/'results/noise_correlation_control_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='cases'},indent=2))
for r in rows:print(json.dumps({k:v for k,v in r.items() if k not in ['timing_psd_s2_per_hz','full_rate_analytic_s2_per_hz','once_per_pss_normalized_analytic_s2_per_hz']},indent=2))
