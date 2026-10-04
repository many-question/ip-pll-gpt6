"""Compare independent whole-PLL reset captures while keeping functional and precision claims separate."""
from pathlib import Path
import hashlib,json,re
import numpy as np
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=[H/'results/capture_repaircold01.json',H/'results/capture_repaircoldstrict01.json']
if not all(p.exists() for p in paths):print('Waiting for completed strict64us capture analysis.');raise SystemExit(0)
analyses=[json.loads(p.read_text()) for p in paths]
jobs=[R/'repaircold01/repair_capture_tt',R/'repaircoldstrict01/repair_capture_strict_tt']
records=[json.loads((j/'result.json').read_text()) for j in jobs]
def canon(body):
    body=re.sub(r'(reltol|vabstol|iabstol|maxstep)=\S+',r'\1=__NUMERICAL_SETTING__',body)
    return re.sub(r'writefinal="[^"]+"','writefinal="__PATH__"',body)
assert canon((jobs[0]/'inputs'/(jobs[0].name+'.scs')).read_text())==canon((jobs[1]/'inputs'/(jobs[1].name+'.scs')).read_text())
deps=[{k:v for k,v in r['inputs_sha256'].items() if k!=j.name+'.scs'} for j,r in zip(jobs,records)]
assert deps[0]==deps[1]
rows=[]
for job,rec,a,ap in zip(jobs,records,analyses,paths):
    assert rec['ok'] and rec['remote_inputs_match'] and sha(job/'waveforms.npz')==rec['local_outputs_sha256']['waveforms.npz']
    assert a['sources'][str((job/'result.json').relative_to(ROOT))]==sha(job/'result.json')
    log=(job/'spectre.out').read_text();assert 'spectre completes with 0 errors' in log
    with np.load(job/'waveforms.npz') as z:d={k:z[k] for k in z.files}
    assert abs(d['time'][0])<1e-15 and abs(d['time'][-1]-64e-6)<1e-12
    coarse=sum(int(d[f'XP.b{i}'][-1]>.6)<<i for i in range(8));dac=sum(int(d[f'XP.XC.d{i}'][-1]>.6)<<i for i in range(6))
    s=a['stationarity'];obs=[x for x in s['ctrl_range_v']]
    rows.append(dict(run=job.parent.name,source_result=(job/'result.json').relative_to(ROOT).as_posix(),source_result_sha256=sha(job/'result.json'),
        analysis_source=ap.relative_to(ROOT).as_posix(),analysis_sha256=sha(ap),condition=a['condition'],
        functional_capture_passed=a['functional_capture_screen_passed'],handoff_us=a['logic']['XP.XC.acquired']['first_rising_us'],
        first_qualified_us=a['logic']['qualified']['first_rising_us'],final_coarse=coarse,final_dac=dac,
        final_output_mhz=s['mean_output_mhz'],final_phase_pp_rad=s['phase_pp_rad'],final_phase_drift_rad_per_us=s['phase_drift_rad_per_us'],
        sampled_control_range_v=obs,sampled_control_midrange_v=sum(obs)/2,
        final1us_mean_supply_mw=s['final_1us_total_supply_power_mw'],
        locked_observation_us=64-a['logic']['qualified']['first_rising_us'] if a['logic']['qualified']['first_rising_us'] is not None else 0))
a,b=rows
out=dict(scope=__doc__,physical_and_stimulus_dependencies_identical=True,only_solver_precision_changed=True,cases=rows,
    both_functional_capture_passed=all(x['functional_capture_passed'] for x in rows),same_final_codes=a['final_coarse']==b['final_coarse'] and a['final_dac']==b['final_dac'],
    strict_minus_4ps=dict(handoff_us=b['handoff_us']-a['handoff_us'] if b['handoff_us'] is not None and a['handoff_us'] is not None else None,
        qualified_us=b['first_qualified_us']-a['first_qualified_us'] if b['first_qualified_us'] is not None and a['first_qualified_us'] is not None else None,
        output_hz=(b['final_output_mhz']-a['final_output_mhz'])*1e6,sampled_control_midrange_v=b['sampled_control_midrange_v']-a['sampled_control_midrange_v'],
        final1us_supply_mw=b['final1us_mean_supply_mw']-a['final1us_mean_supply_mw']),
    precision_convergence_accepted=False,random_jitter_measured=False,full_requirement_acceptance=False,
    interpretation='Independent reset captures show function at two solver settings. Locked output frequency alone cannot prove operating-point or noise convergence; control voltage, timing,energy and waveforms need separate comparison. The final1us is shorter than the32uswatchdogperiod.',
    limitations=['SingleTT27/1.2V/K41/M4/10fF/24MHz/Q5condition; not33codes,PVT or reference/load range.',
        'Supply alreadyDC1.2V and10uV initialdifferential perturbation; not railramp or stochasticstartup.',
        '2nsstrobe waveforms cannot establishGHz slew,swing,randomjitter or instantaneous power; energy uses continuous source-current integration.',
        'Sameeventobserver used inboth; detailed no-observer periodic/noise analysis is separate.'])
(H/'results/capture_precision_comparison.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
