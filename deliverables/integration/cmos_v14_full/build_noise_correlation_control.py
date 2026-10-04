"""Expose sampling/correlation errors hidden by a white-noise RC calibration."""
from pathlib import Path
import datetime,hashlib,json,math
H=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
freq=[1e6,10e6,82e6,163e6,164e6,165e6,246e6,492e6];rows=[]
for ratio,fund in [(1,984e6),(6,164e6)]:
    case=f'noise_corr_ratio{ratio}'
    body=f'''simulator lang=spectre
global 0
// Linear colored-noise calibration only; no PLL performance claim.
simulatorOptions options temp=27 reltol=1e-5 vabstol=1e-7 iabstol=1e-13
VI (inp 0) vsource type=sine dc=0.6 ampl=0.5 freq=984M
R (inp out) resistor r=1k
C (out 0) capacitor c=2p
pss pss fund={fund:.16g} harms=383 maxacfreq=1T tstab=100n maxstep=250f method=gear2only tstabmethod=gear2only errpreset=conservative maxperiods=10 saveinit=yes
pn pnoise values=[1M 10M 82M 163M 164M 165M 246M 492M] pnoisemethod=fullspectrum noisetype=sampled measurement=[edge] sampleratio={ratio} maxsideband=383
edge jitterevent trigger=[out] triggerthresh=0.6 triggernum=1 triggerdir=rise target=[out] jittercal=[Jee]
save inp out
saveOptions options save=selected
'''
    tb=H/'tb'/(case+'.scs');assert not tb.exists();tb.write_text(body)
    rows.append(dict(case=case,fund_hz=fund,sample_ratio=ratio,tb_sha256=sha(tb)))
p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),status='prepared_not_run',run='noisecorr01',cases=rows,
    offsets_hz=freq,resistance_ohm=1000.,capacitance_f=2e-12,temperature_k=300.15,sample_frequency_hz=984e6,input_amplitude_v=.5,
    analytic_rho=math.exp(-1/(984e6*2e-9)),
    hypothesis='sampleratio may normalize amplitude without reconstructing correlations among all events within a long PSS period. The earlier20fF RC is nearly white and cannot distinguish this from a correct full-rate sampled spectrum. This is a hypothesis, not a Spectre bug claim.',
    analytic='RC voltage covariance kT/C*exp(-abs(t)/(RC)). The exact one-sided full-rate sampled PSD is2*kT/(C*fs)*(1-rho^2)/(1-2*rho*cos(2*pi*f/fs)+rho^2),rho=exp(-1/(fsRC)); divide by analytic output sine slew squared.',
    alternative_prediction='If each selected event is sampled only once per PSS period and sampleratio only rescales normalization, use effective fs=fund then divide that sampled voltage PSD bysampleratio. This would repeat folded spectra aroundfund and differ from the full-rate analytic spectrum.',
    condition='Same1kohm/2pF,27C,noiseless984MHz sine,250fs/1THz/383sidebands,Gear2. Only fund andsampleratio change. FreshPSS for eachcase; eight explicitoffsets, no sparse integral reported.',
    limits=dict(point_psd_error_db=.1,ratio1_to_ratio6_psd_db=.1,period_relative=1e-8,endpoint_v=1e-3,device_sum_relative=1e-7),
    launch_gate='After current rt4c24tune01 completes and is collected, reuse its one-thread shortslot. Prior RC246 white-noise wrapper stopped while idle; no duplicate calibration. Two finite cases only.',
    limitations=['Linear stationary colored-noise diagnostic, not a transistor noise or PLL result.',
        'Even agreement cannot by itself validate a genuinely cyclostationary six-/246-phase MOS circuit.',
        'No numerical RMS is inferred from these eight sparse colored-noise points.',
        'If the sampling interpretation fails, preserve prior local jitter values as provisional and resolve the measurement before circuit acceptance.'],
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/noise_correlation_control_protocol.json').write_text(json.dumps(p,indent=2)+'\n');print(' '.join(x['case'] for x in rows))
