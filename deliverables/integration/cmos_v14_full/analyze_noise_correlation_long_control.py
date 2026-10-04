"""Check the long-period colored-RC PSD against analytic covariance and ratio1."""
from pathlib import Path
import hashlib,json
import numpy as np
from noise_utils import parse,header,devices,cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((H/'results/noise_correlation_long_protocol.json').read_text())
j=ROOT/'research/runs/spectre_cmos_v14_full'/p['run']/p['case'];rp=j/'result.json'
if not rp.exists():print('pending');raise SystemExit(0)
r=json.loads(rp.read_text())
if not r.get('local_outputs_sha256'):print('collection incomplete');raise SystemExit(0)
assert r['ok'] and r['remote_inputs_match']
log=(j/'spectre.out').read_text();assert 'spectre completes with 0 errors' in log and 'The steady-state solution was achieved' in log
tb=H/'tb'/(p['case']+'.scs');assert sha(tb)==p['tb_sha256'] and tb.read_text()==(j/'inputs'/tb.name).read_text()
oldpath=H/'results/noise_correlation_control_validation.json';assert sha(oldpath)==p['prior_validation_sha256']
old=json.loads(oldpath.read_text());one=next(x for x in old['cases'] if x['sample_ratio']==1)
freq=np.asarray(p['offsets_hz']);fs=p['sample_frequency_hz'];tau=p['resistance_ohm']*p['capacitance_f']
variance=1.380649e-23*p['temperature_k']/p['capacitance_f'];rho=np.exp(-1/(fs*tau))
slope_expected=2*np.pi*fs*p['input_amplitude_v']/np.sqrt(1+(2*np.pi*fs*tau)**2)
expected=2*variance/fs*(1-rho*rho)/(1-2*rho*np.cos(2*np.pi*freq/fs)+rho*rho)/slope_expected**2
raw=j/(j.name+'.raw');td=parse(raw/'pss.td.pss');t=td['time'];edges=cross(t,td['out'])
period_ok=bool(abs((t[-1]-t[0])*p['fund_hz']-1)<p['limits']['period_relative'] and len(edges)==246 and abs(td['out'][-1]-td['out'][0])<p['limits']['endpoint_v'])
path=raw/'pnMedge.0.sample.pnoise';pn=parse(path);assert np.allclose(pn['freq'],freq,rtol=1e-10,atol=0)
slope=header(path,'slew rate event_1');assert header(path,'sample ratio factor')==246 and slope>0
sv=pn['out']**2;dev=devices(path,len(freq));closure=float(max(abs(sum(dev.values())/sv-1)))
measured=sv/slope**2;db=10*np.log10(measured/expected)
baseline=np.asarray([one['timing_psd_s2_per_hz'][old['offsets_hz'].index(float(f))] for f in freq]);difference=10*np.log10(measured/baseline)
passed=bool(period_ok and closure<p['limits']['device_sum_relative'] and max(abs(db))<p['limits']['point_psd_error_db'] and max(abs(difference))<p['limits']['ratio1_to_ratio246_psd_db'])
out=dict(scope=__doc__,source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),raw_noise_sha256=sha(path),
    complete=True,passed=passed,periodic_passed=period_ok,rising_edges=len(edges),offsets_hz=freq.tolist(),
    slew_v_per_s=slope,analytic_slew_v_per_s=slope_expected,device_sum_relative_error=closure,
    timing_psd_s2_per_hz=measured.tolist(),analytic_psd_s2_per_hz=expected.tolist(),analytic_error_db=db.tolist(),
    ratio246_minus_ratio1_db=difference.tolist(),max_analytic_error_db=float(max(abs(db))),max_ratio_psd_difference_db=float(max(abs(difference))),
    random_jitter_integral_measured=False,full_pll_acceptance=False,limitations=p['limitations'])
(H/'results/noise_correlation_long_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
