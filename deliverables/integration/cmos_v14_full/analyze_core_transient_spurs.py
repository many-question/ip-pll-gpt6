"""Diagnostic spectral lines from two saved, nearly repeating core transients.

This is NOT a converged PSS or full-PLL acceptance result. It tests whether
large deterministic reference-related modulation is already visible despite
the small measured drift, using separate windows, interpolation density, and
direct nonuniform quadrature. A detuned pure-tone control illustrates leakage
from the observed mean drift but is not a rigorous bound for every waveform.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from spur_utils import line_metrics,project_lines
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
j=ROOT/'research/runs/spectre_cmos_v14_full/coretripsupply01/core_pulsetrip_supply_noise_tt'
p=j/'tstab_last_two_periods.npz'
with np.load(p) as z:d={k:z[k] for k in z.files}
proof=json.loads((H/'results/core_period_drift.json').read_text())
assert str(d['source_sha256'])==proof['source_sha256']
assert json.loads((H/'results/spur_method_validation.json').read_text())['passed']
T=250e-9;fc=984e6;t=d['time'];finish=float(t[-1]);rows=[]
output=next(x for x in proof['rows'] if x['node']=='out')
dt=output['matched_edge_shift_ps']['mean']*1e-12
df=-fc*dt/T
for label,start in [('earlier',finish-2*T),('later',finish-T)]:
    selection=(t>start)&(t<start+T)
    tw=np.r_[start,t[selection],start+T]
    yw=np.r_[np.interp(start,t,d['out']),d['out'][selection],np.interp(start+T,t,d['out'])]
    assert abs(tw[-1]-tw[0]-T)<1e-18
    metrics=[]
    for n in [2**18,2**19]:
        u=np.arange(n)*T/n
        y=np.interp(start+u,tw,yw)
        spectrum=2*np.fft.rfft(y)/n;f=np.arange(len(spectrum))/T
        m=line_metrics(f,spectrum,fc)
        m['interpolation_step_ps']=T/n*1e12;metrics.append(m)
    m=metrics[-1]
    wanted=[x['frequency_hz'] for x in m['lines'] if abs(abs(x['offset_hz'])/24e6-round(abs(x['offset_hz'])/24e6))<1e-8]
    wanted=sorted(set(wanted+[m['largest_line']['frequency_hz'],fc]))
    v=project_lines(tw,yw,wanted,1/T);carrier=abs(v[wanted.index(fc)])
    direct={fr:float(20*np.log10(max(abs(val)/carrier,1e-300))) for fr,val in zip(wanted,v) if fr!=fc}
    by_frequency={x['frequency_hz']:x for x in m['lines']}
    errors=[abs(db-by_frequency[fr]['dbc']) for fr,db in direct.items() if by_frequency[fr]['dbc']>-90]
    coarse=metrics[0]['lines'];fine=metrics[1]['lines']
    assert [x['frequency_hz'] for x in coarse]==[x['frequency_hz'] for x in fine]
    numerical=[abs(x['dbc']-y['dbc']) for x,y in zip(coarse,fine) if max(x['dbc'],y['dbc'])>-90]
    ctrl=np.interp(start+np.arange(2**18)*T/(2**18),t,d['XP.ctrl'])
    cv=2*np.fft.rfft(ctrl)/(2**18)
    row=dict(window=label,interval_us=[start*1e6,(start+T)*1e6],metric=m,
        reference_lines=[dict(frequency_hz=fr,offset_hz=fr-fc,dbc=db) for fr,db in direct.items() if abs(abs(fr-fc)/24e6-round(abs(fr-fc)/24e6))<1e-8],
        max_strong_line_fft_quadrature_delta_db=float(max(errors)),
        max_strong_line_interpolation_delta_db=float(max(numerical)),
        control_range_v=[float(min(ctrl)),float(max(ctrl))],control_24mhz_peak_amplitude_v=float(abs(cv[6])),
        spectral_checks_passed=bool(max(errors)<.2 and max(numerical)<.2))
    rows.append(row)
u=np.arange(2**19)*T/(2**19);tone=np.sin(2*np.pi*(fc+df)*u)
f=np.arange(len(u)//2+1)/T;v=2*np.fft.rfft(tone)/len(u)
leak=line_metrics(f,v,fc)
out=dict(scope=__doc__,source=p.relative_to(ROOT).as_posix(),raw_source_sha256=str(d['source_sha256']),
    cache_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),cases=rows,
    observed_mean_drift_equivalent_frequency_error_hz=float(df),detuned_sinusoid_control=leak,
    periodic_state_valid=False,random_jitter_measured=False,full_pll_acceptance=False,requirement_met=None,
    condition='TT27/1.2V/984MHz/10fF,actualLCQ5/CF10/baselineRT/continuousclockbank/staticcontrols,1psreltol1e-5traponly.',
    interpretation='A repeatable strong24MHz-offset component can guide a physical feedthrough/modulation diagnosis. Window and quadrature consistency do not replace circuit numerical convergence, exact steady state, or completePLL control activity.')
(H/'results/core_transient_spur_diagnosis.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(cases=[{k:v for k,v in x.items() if k!='metric'}|dict(largest=x['metric']['largest_line']) for x in rows],
    drift_equivalent_hz=df,leakage_largest=leak['largest_line']),indent=2))
