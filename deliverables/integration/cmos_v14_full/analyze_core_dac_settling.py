"""Compare measured initialization trajectories before and after DAC discharge.

Both the physical DAC and stabilization duration changed. This checks the
resulting trajectory, not causality, a valid periodic solution, or jitter.
"""
from pathlib import Path
import hashlib,json
import numpy as np
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=H/'results/core_native_initial_period_drift.json';after=H/'results/core_dac_initial_period_drift.json'
b=json.loads(before.read_text());a=json.loads(after.read_text());p=json.loads((H/'results/core_dac_discharge_noise_protocol.json').read_text())
rows={x['node']:x for x in a['rows']}
j=ROOT/'research/runs/spectre_cmos_v14_full'/p['run']/p['case']
with np.load(j/'tstab_live_tstab_last_two_periods.npz') as z:
    assert str(z['source_sha256'])==a['source_sha256']
    coarse=all(np.all(z[f'XP.b{k}']>.9) if 23&(1<<k) else np.all(z[f'XP.b{k}']<.3) for k in range(8))
branches=[dict(node=k,expected=n,first=rows[k]['first_period_edges'],second=rows[k]['second_period_edges'],
    passed=rows[k]['first_period_edges']==n and rows[k]['second_period_edges']==n) for k,n in p['expected_rising_edges_per_period'].items()]
voltage=lambda d:max((x for x in d['rows'] if x['unit']=='V'),key=lambda x:x['difference_peak'])
ctrl=rows['XP.ctrl']['range'];offkeys=['XP.XDAC.vd','XP.XDAC.b0','XP.XDAC.b3','XP.XDAC.b4']
out=dict(scope=__doc__,before_source=before.relative_to(ROOT).as_posix(),before_sha256=sha(before),
    after_source=after.relative_to(ROOT).as_posix(),after_sha256=sha(after),condition=p['condition'],
    intervals_us=a['intervals_us'],missing_boundary_duration_s=a['missing_boundary_duration_s'],
    before_max_voltage_difference=voltage(b),after_max_voltage_difference=voltage(a),
    before_control_period_peak_difference_v=next(x['difference_peak'] for x in b['rows'] if x['node']=='XP.ctrl'),
    after_control_period_peak_difference_v=rows['XP.ctrl']['difference_peak'],
    sampled_off_nodes={k:rows[k] for k in offkeys},off_node_absolute_peak_v=max(abs(v) for k in offkeys for v in rows[k]['range']),
    coarse23_held=bool(coarse),control_range_v=ctrl,branches=branches,
    branch_and_range_checks_passed=bool(coarse and .2<=ctrl[0]<=ctrl[1]<=1 and all(x['passed'] for x in branches)),
    dense_period_gate_v=1e-3,dense_period_gate_passed=bool(voltage(a)['difference_peak']<1e-3),
    periodic_state_valid=False,random_jitter_measured=False,full_pll_acceptance=False,
    limitations=['Seven physical clamps and tstab250ns->2us both changed; improvement is not isolated to either cause.',
        'Only three of six internal DAC b nodes are saved in this core trace; the separate unit bench covers all six.',
        'Missing incomplete boundary record is not extrapolated; initialization is distinct from later Newton corrections.',
        'A small deterministic edge displacement is not random jitter.'])
(H/'results/core_dac_settling_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['sampled_off_nodes','branches','before_max_voltage_difference','after_max_voltage_difference']},indent=2))
