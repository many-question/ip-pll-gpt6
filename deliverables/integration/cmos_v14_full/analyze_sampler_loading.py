"""Analyze fixed-control reference/LC loading probes, never call them PLL jitter."""
from pathlib import Path
import hashlib,json
import numpy as np
from noise_utils import cross
from reference_modulation_utils import fit_edges,analytic_control
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
protocol=json.loads((H/'results/sampler_loading_protocol.json').read_text());R=ROOT/'research/runs/spectre_cmos_v14_full'/protocol['run']
fixture=analytic_control();assert fixture['passed'];rows=[]
for case in protocol['cases']:
    j=R/case['case'];p=j/'result.json'
    if not p.exists():continue
    r=json.loads(p.read_text())
    if not r.get('local_outputs_sha256'):continue
    row=dict(case=case['case'],reference=case['reference'],control_v=case['control_v'],valid_for_diagnosis=False,
        source_result=p.relative_to(ROOT).as_posix(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest());rows.append(row)
    if not r['ok'] or 'spectre completes with 0 errors' not in (j/'spectre.out').read_text():continue
    assert r['remote_inputs_match'] and r['inputs_sha256']['pll_noise_pulsetrip_core_v14.scs']==protocol['source_core_sha256']
    assert r['inputs_sha256'][j.name+'.ic']==case['seed_sha256']
    wp=j/'waveforms.npz';assert hashlib.sha256(wp.read_bytes()).hexdigest()==r['local_outputs_sha256']['waveforms.npz']
    with np.load(wp) as z:d={k:z[k] for k in z.files}
    t=d['time'];assert 249.99e-9<t[0]<250.01e-9 and abs(t[-1]-750e-9)<1e-14
    rf=cross(t,d['XP.vp']-d['XP.vn'],0);oe=cross(t,d['out']);fr=float(1/np.mean(np.diff(rf)));fo=float(1/np.mean(np.diff(oe)))
    parts=[]
    for start,end in [(250e-9,500e-9),(500e-9,750e-9)]:
        e=rf[(rf>=start)&(rf<end)];parts.append(float(1/np.mean(np.diff(e))))
    coarse=all(np.all(d[f'XP.b{i}']>.9) if 23&(1<<i) else np.all(d[f'XP.b{i}']<.3) for i in range(8))
    clamp=float(max(abs(d['XP.ctrl']-case['control_v'])));frequency_drift_ppm=float(abs(parts[1]-parts[0])/np.mean(parts)*1e6)
    row.update(rf_hz=fr,output_hz=fo,coarse23_held=bool(coarse),control_clamp_max_error_v=clamp,
        rf_last_two_windows_hz=parts,last_two_window_difference_ppm=frequency_drift_ppm,
        rf_differential_swing_pp_v=float(np.ptp(d['XP.vp']-d['XP.vn'])),rf_fit=fit_edges(rf),output_fit=fit_edges(oe),
        valid_for_diagnosis=bool(coarse and clamp<1e-9 and frequency_drift_ppm<100 and abs(fo*4/fr-1)<.001))
    if case['reference']=='clocked':
        mid=(rf[1:]+rf[:-1])/2;periods=np.diff(rf)
        re=np.sort(np.r_[cross(t,d['XP.refb']),cross(t,1.2-d['XP.refb'])])
        assert len(re)>10
        distance=np.min(abs(mid[:,None]-re[None,:]),axis=1)
        level=np.interp(mid,t,d['XP.refb']);halves={}
        for name,mask in [('holding',level>.9),('tracking',level<.3)]:
            good=mask&(distance>2e-9)&(mid>t[0]+2e-9)&(mid<t[-1]-2e-9)
            halves[name]=dict(cycles=int(sum(good)),rf_hz=float(1/np.mean(periods[good])))
        row['frequency_away_from_reference_edges']=halves
        row['clocked_hold_minus_track_rf_hz']=halves['holding']['rf_hz']-halves['tracking']['rf_hz']
out=dict(scope=__doc__,fixture=fixture,cases=rows,complete=len(rows)==len(protocol['cases']),
    full_pll_acceptance=False,random_jitter_measured=False,main_dut_modified=False)
available={x['case'].replace('samplerload_','').replace('_tt',''):x for x in rows if x.get('valid_for_diagnosis')}
if 'clocked' in available:
    cached=ROOT/'research/runs/spectre_cmos_v14_full/coretripsupply01/core_pulsetrip_supply_noise_tt/tstab_last_two_periods.npz'
    with np.load(cached) as z:original={k:z[k] for k in ['time','XP.vp','XP.vn','out','source_sha256']}
    source=json.loads((H/'results/core_reference_modulation.json').read_text())
    assert str(original['source_sha256'])==source['raw_source_sha256']
    ot=original['time'];start=ot[-1]-500e-9;fits={}
    for name,y,threshold in [('rf',original['XP.vp']-original['XP.vn'],0.),('output',original['out'],.6)]:
        e=cross(ot,y,threshold);e=e[e>=start];fits[name]=fit_edges(e)
    clamped=available['clocked']
    out['clocked_clamp_comparison']=dict(unclamped_raw_sha256=str(original['source_sha256']),
        method='Both500ns windows use the same consecutive-edge7-harmonic fit with quadratic drift; not carrier-FFT versus edge-fit comparison.',
        unclamped_fits=fits,
        rf24_pm_ratio_clamped_to_unclamped=clamped['rf_fit']['harmonics'][0]['pm_peak_rad']/fits['rf']['harmonics'][0]['pm_peak_rad'],
        output24_pm_ratio_clamped_to_unclamped=clamped['output_fit']['harmonics'][0]['pm_peak_rad']/fits['output']['harmonics'][0]['pm_peak_rad'],
        rf_carrier_change_hz=clamped['rf_fit']['carrier_hz']-fits['rf']['carrier_hz'],
        conclusion='Substantial reference-rate PM remaining with idealconstantVCTRL proves a directpath exists in this diagnostic boundary. Static mean frequency changes; this does not isolate one sampling device or quantify every path in the closed loop.',
        limitations='The unclamped data are initialized transient, not validPSS; no circuitstep/PVT/noise or fullPLL acceptance. Residual fit RMS is deterministic modeling residual, never random jitter.')
    for label,key in [('rf','rf_fit'),('output','output_fit')]:
        first=complex(*fits[label]['harmonics'][0]['pm_phasor_absolute_time_rad'])
        second=complex(*clamped[key]['harmonics'][0]['pm_phasor_absolute_time_rad'])
        out['clocked_clamp_comparison'][label+'24_complex_pm_change_fraction']=float(abs(second-first)/abs(first))
        out['clocked_clamp_comparison'][label+'24_pm_phase_change_rad']=float(np.angle(second/first))
    out['clocked_clamp_comparison']['phasor_scope']='Absolute simulator-time reference; both external forcing phases match modulo24MHz. Difference includes changed carrier and loading operating point, not solely the removed control path.'
if all(x in available for x in ['clocked','track','hold']):
    split=available['hold']['rf_hz']-available['track']['rf_hz']
    # Symmetric square frequency modulation is only an approximation, not a model fit.
    beta_pred=2*abs(split)/(np.pi*24e6*4)
    out['comparison']=dict(hold_minus_track_rf_hz=float(split),
        clocked_output24_pm_peak_rad=available['clocked']['output_fit']['harmonics'][0]['pm_peak_rad'],
        square_fm_predicted_output24_pm_peak_rad=float(beta_pred),
        square_fm_predicted_single_sideband_dbc=float(20*np.log10(max(beta_pred/2,1e-300))),
        square_fm_prediction_to_observed_pm_ratio=float(beta_pred/available['clocked']['output_fit']['harmonics'][0]['pm_peak_rad']),
        dc_loading_split_last_two_windows_hz=[float(h-l) for h,l in zip(available['hold']['rf_last_two_windows_hz'],available['track']['rf_last_two_windows_hz'])],
        interpretation='Constantcontrol removes LF modulation. Direct reference/sampling loading is implicated only if measured clocked modulation remains and the DC loading split predicts its scale; other direct reference paths are still included.')
if all(x in available for x in ['clocked','track','hold','track_vm','track_vp']):
    kvco=(available['track_vp']['rf_hz']-available['track_vm']['rf_hz'])/.02
    out['comparison']['track_kvco_hz_per_v']=float(kvco)
    source=H/'results/core_reference_modulation.json'
    if source.exists():
        previous=json.loads(source.read_text())
        ripple=previous['control24_peak_v']
        out['comparison']['linear_control_ripple_estimate']=dict(
            control24_peak_v=ripple,tracking_kvco_hz_per_v=float(kvco),
            output24_pm_peak_rad=float(abs(kvco)*ripple/(24e6*4)),
            source=source.relative_to(ROOT).as_posix(),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            note='Static tracking KVCO times measured closed-loop control ripple, divided by offset frequency and M. A first-order scale estimate, not a measured isolated path; dynamic loading, relative phase, AM and loop coupling remain.')
elif all(x in available for x in ['track','track_vm']):
    dv=available['track']['control_v']-available['track_vm']['control_v']
    out['partial_kvco']=dict(method='One-sided static tracking secant; positive control point is still pending.',
        controls_v=[available['track_vm']['control_v'],available['track']['control_v']],
        hz_per_v=float((available['track']['rf_hz']-available['track_vm']['rf_hz'])/dv),
        limitation='Baseline retimer and DCtracking only; not the RT4 clocked tuning curve, not a measured dynamic loop gain.')
(H/'results/sampler_loading_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
