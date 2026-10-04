"""Measure on/off DAC behavior and disturbance of the actual precharge filter."""
from pathlib import Path
import argparse,hashlib,json,re
import numpy as np
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ap=argparse.ArgumentParser();ap.add_argument('--all-nodes',action='store_true');args=ap.parse_args()
label='dac_discharge_all' if args.all_nodes else 'dac_discharge'
pp=H/'results'/(label+'_protocol.json');p=json.loads(pp.read_text());rows=[]
for c in p['cases']:
    j=ROOT/'research/runs/spectre_cmos_v14_full'/p['run']/c['case'];rp=j/'result.json'
    if not rp.exists() or not json.loads(rp.read_text()).get('local_outputs_sha256'):continue
    r=json.loads(rp.read_text());log=(j/'spectre.out').read_text()
    assert r['ok'] and r['remote_inputs_match'] and 'spectre completes with 0 errors' in log
    assert all(sha(j/'inputs'/k)==v for k,v in r['inputs_sha256'].items())
    assert r['inputs_sha256'][p.get('candidate_file','dac_discharge_v14.scs')]==p['candidate_sha256']
    assert r['inputs_sha256']['fll_circuit.scs']==p['source_sha256']
    assert sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
    with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files if k!='units'}
    t=d['time'];assert t[0]==0 and abs(t[-1]-5e-6)<1e-15 and np.all(np.diff(t)>0)
    def mask(a,b):
        m=(t>=a*1e-6)&(t<=b*1e-6);assert m.sum()>10;return m
    pre=mask(.9,.99);off=mask(1.1,3.99);held=mask(1.0001,3.99);post=mask(4.8,4.99)
    phases=[]
    for label,prefix,suffix,out in [('original','XO','o','original'),('candidate','XN','n','candidate')]:
        before=float(np.mean(d['ctrl_'+suffix][pre]));after=float(np.mean(d['ctrl_'+suffix][post]))
        end=float(np.interp(3.99e-6,t,d['ctrl_'+suffix]))
        rail=d[prefix+'.vd'];postedge=t>=1.0001e-6;offtime=t<4e-6
        high=np.flatnonzero(postedge&offtime&(abs(rail)>1e-3))
        settle=float(t[high[-1]]-1.0001e-6) if len(high) else 0.
        phases.append(dict(variant=label,active_output_v=float(np.mean(d[out][pre])),
            initial_ctrl_v=before,recovered_ctrl_v=after,held_final_ctrl_v=end,
            held_ctrl_drift_v=end-before,held_ctrl_peak_change_v=float(max(abs(d['ctrl_'+suffix][held]-before))),
            off_rail_range_v=[float(min(rail[off])),float(max(rail[off]))],
            off_internal_b0_range_v=[float(min(d[prefix+'.b0'][off])),float(max(d[prefix+'.b0'][off]))],
            off_internal_saved_node_peak_v=max(float(max(abs(d[k][off]))) for k in d if re.fullmatch(re.escape(prefix)+r'\.b[0-5]',k)),
            off_rail_last_above_1mv_after_edge_s=settle,
            off_rail_below_1mv_before_reenable=bool(len(high)==0 or t[high[-1]]<3.99e-6)))
    # Compare both held waveforms relative to their own pre-release values;
    # retain the raw absolute differences as well.
    delta=(d['ctrl_n']-phases[1]['initial_ctrl_v'])-(d['ctrl_o']-phases[0]['initial_ctrl_v'])
    active=float(max(abs(d['candidate'][pre]-d['original'][pre])))
    disturbance=float(max(abs(delta[held])));lim=p['working_limits']
    checks=dict(active_dac_unchanged=active<lim['active_output_difference_v'],
        off_rail_discharged=max(abs(x) for x in phases[1]['off_rail_range_v'])<lim['off_rail_max_v'],
        held_control_disturbance=disturbance<lim['additional_held_ctrl_difference_v'])
    if 'off_internal_max_v' in lim:checks['off_internal_discharged']=phases[1]['off_internal_saved_node_peak_v']<lim['off_internal_max_v']
    rows.append(dict(case=c['case'],corner=c['corner'],temp_c=c['temp_c'],source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),
        waveforms_sha256=sha(j/'waveforms.npz'),phases=phases,active_dac_max_difference_v=active,
        additional_held_ctrl_peak_difference_v=disturbance,checks=checks,working_checks_passed=all(checks.values())))
out=dict(scope=__doc__,protocol_sha256=sha(pp),condition=p['conditions'],complete=len(rows)==len(p['cases']),cases=rows,
    all_completed_checks_passed=bool(rows and all(x['working_checks_passed'] for x in rows)),
    core_pss_fix_proven=False,full_pll_acceptance=False,main_dut_modified=False,limitations=p['limitations'])
(H/'results'/('dac_discharge_all_validation.json' if args.all_nodes else 'dac_discharge_validation.json')).write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
