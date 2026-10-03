"""Compare complementary MOS sampling loads in the fixed-control diagnostic.

Only deterministic reference modulation is measured. No random-jitter result,
accepted spur limit, closed-loop capture or main-DUT adoption is implied.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from noise_utils import cross
from reference_modulation_utils import fit_edges,analytic_control

H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protocol=json.loads((H/'results/sampler_dummy_protocol.json').read_text())
loading=json.loads((H/'results/sampler_loading_validation.json').read_text())
source_protocol=json.loads((H/'results/sampler_loading_protocol.json').read_text())
baseline=next(x for x in loading['cases'] if x['case']=='samplerload_clocked_tt')
assert baseline['valid_for_diagnosis'] and analytic_control()['passed']
bp=ROOT/baseline['source_result'];assert sha(bp)==baseline['source_sha256']
br=json.loads(bp.read_text());vctrl=baseline['control_v']
baseline_deps={k:v for k,v in br['inputs_sha256'].items() if k not in ['samplerload_clocked_tt.scs','pll_noise_pulsetrip_core_v14.scs']}
rows=[]
for item in protocol['cases']:
    j=ROOT/'research/runs/spectre_cmos_v14_full'/protocol['run']/item['case'];rp=j/'result.json'
    if not rp.exists():continue
    r=json.loads(rp.read_text())
    if not r.get('local_outputs_sha256'):continue
    row=dict(case=item['case'],dummy_capacitance_f=item['cdummy_f'],source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),valid_for_diagnosis=False);rows.append(row)
    if not r['ok'] or 'spectre completes with 0 errors' not in (j/'spectre.out').read_text():continue
    assert r['remote_inputs_match']
    deps=r['inputs_sha256']
    assert deps['pll_noise_dummy_core_v14.scs']==protocol['candidate_core_sha256']
    assert deps['sampler_dummy_v14.scs']==protocol['sampler_sha256']
    assert {k:v for k,v in deps.items() if k not in [item['case']+'.scs','pll_noise_dummy_core_v14.scs','sampler_dummy_v14.scs']}==baseline_deps
    wp=j/'waveforms.npz';assert sha(wp)==r['local_outputs_sha256']['waveforms.npz']
    with np.load(wp) as z:d={k:z[k] for k in z.files}
    t=d['time'];assert 249.99e-9<t[0]<250.01e-9 and abs(t[-1]-750e-9)<1e-14
    e=cross(t,d['XP.vp']-d['XP.vn'],0);oe=cross(t,d['out'])
    assert len(e)>100 and len(oe)>100
    fr=float(1/np.mean(np.diff(e)));fo=float(1/np.mean(np.diff(oe)))
    parts=[]
    for start,end in [(250e-9,500e-9),(500e-9,750e-9)]:
        q=e[(e>=start)&(e<end)];parts.append(float(1/np.mean(np.diff(q))))
    drift=float(abs(parts[1]-parts[0])/np.mean(parts)*1e6)
    coarse=all(np.all(d[f'XP.b{i}']>.9) if 23&(1<<i) else np.all(d[f'XP.b{i}']<.3) for i in range(8))
    clamp=float(max(abs(d['XP.ctrl']-vctrl)))
    supply=max(float(max(abs(d[k]-1.2))) for k in ['XP.vco_vdd','XP.rx_vdd','XP.rt_vdd'])
    fits={'rf':fit_edges(e),'output':fit_edges(oe)}
    changes={}
    for label,fit in fits.items():
        old=baseline[label+'_fit'];a=fit['harmonics'][0]['pm_peak_rad'];b=old['harmonics'][0]['pm_peak_rad']
        changes[label]=dict(pm24_amplitude_ratio=a/b,pm24_change_db=float(20*np.log10(max(a/b,1e-300))),
            equivalent_deterministic_time24_peak_ps=fit['harmonics'][0]['equivalent_deterministic_time_peak_ps'],
            # Harmonics are deterministic lines, not uncorrelated device noise.
            seven_harmonic_deterministic_time_rms_ps=float(np.sqrt(sum(x['equivalent_deterministic_time_peak_ps']**2/2 for x in fit['harmonics']))))
    row.update(rf_hz=fr,output_hz=fo,rf_frequency_change_from_baseline_hz=fr-baseline['rf_hz'],
        rf_last_two_windows_hz=parts,last_two_window_difference_ppm=drift,
        coarse23_held=bool(coarse),control_clamp_max_error_v=clamp,supply_max_error_v=supply,
        divider_relative_error=fo*4/fr-1,rf_fit=fits['rf'],output_fit=fits['output'],modulation_comparison=changes,
        rf_differential_swing_pp_v=float(np.ptp(d['XP.vp']-d['XP.vn'])),
        valid_for_diagnosis=bool(coarse and clamp<1e-9 and supply<1e-9 and drift<100 and abs(fo*4/fr-1)<.001))
out=dict(scope=__doc__,run=protocol['run'],baseline_source=baseline['source_result'],baseline_sha256=baseline['source_sha256'],
    cases=rows,complete=len(rows)==len(protocol['cases']),full_pll_acceptance=False,random_jitter_measured=False,
    main_dut_modified=False,condition=source_protocol['condition'],
    interpretation='Rank only valid diagnostic cases by measured reference-PM amplitude. Added load shifts the carrier and reference slew; a reduction is not an isolated mechanism contribution or closed-loop performance proof.',
    pending=['Actual loop retuning/capture and loading effects','Fresh PSS device noise including new MOS switches','Independent timestep, PVT and mismatch','Spur-line spectrum at the confirmed acceptance boundary'])
valid=[x for x in rows if x['valid_for_diagnosis']]
if valid:
    out['lowest_output24_pm_diagnostic_case']=min(valid,key=lambda x:x['output_fit']['harmonics'][0]['pm_peak_rad'])['case']
(H/'results/sampler_dummy_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
