"""Build measured-current-guided phase brackets for a separate physical CP trial."""
from pathlib import Path
import argparse,datetime,hashlib,json,re
import numpy as np
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
normal=lambda s:re.sub(r'\b(writefinal|writepss)="[^"]+"',r'\1="STATE"',s).strip()

def operating_body(s):
    # Remove diagnostic saves, not devices, forcing, options or the PSS setup.
    assert s.count('\n// Instrumentation only:')==1
    return s.split('\n// Instrumentation only:',1)[0]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=['fasttail','mid70'],required=True)
    ap.add_argument('--round',type=int,choices=[1,2,3],default=1);a=ap.parse_args()
    prefix='cp_'+a.variant;dst=H/'results'/f'{prefix}_balance{a.round}_protocol.json';assert not dst.exists()
    initial=H/'results'/('cp_fasttail_branch_validation.json' if a.variant=='fasttail' else 'cp_mid70_probe_validation.json')
    iv=json.loads(initial.read_text());assert iv['operating_data_valid'] and iv['node_balances_verified'] and iv['probe_voltages_verified'] and iv['periodic']['periodic_passed']
    rp=ROOT/iv['periodic']['source_result'];assert sha(rp)==iv['periodic']['source_sha256']
    r=json.loads(rp.read_text());source=rp.parent/'inputs'/(rp.parent.name+'.scs');assert sha(source)==r['inputs_sha256'][source.name]
    body=operating_body(source.read_text())
    body=re.sub(r'\bwritefinal="[^"]+"','writefinal="__FINAL_STATE__"',body)
    body=re.sub(r'\bwritepss="[^"]+"','writepss="__PERIODIC_STATE__"',body)
    gainproof=H/'results/frontend_local_gain2_validation.json';g=json.loads(gainproof.read_text())
    assert g['local_gain_verified'] and g['balanced_center_verified']
    if a.round==1:
        proof=initial;width=15
        phase=iv['periodic']['phase_deg']+np.rad2deg(iv['periodic']['mean_clamp_current_a']/g['kphi_magnitude_a_per_rf_rad'])
        method='Unverified first estimate from measured candidate current and the previous baseline signed gain. Candidate gain still needs measurement.'
    else:
        proof=H/'results'/f'{prefix}_balance{a.round-1}_validation.json';v=json.loads(proof.read_text())
        assert v['complete'] and v['periodic_all_passed'] and v['unique_negative_feedback_branch']
        phase=v['proposed_phase_deg'];assert phase is not None;width=1 if a.round==2 else .1
        method=v['proposed_phase_method']
    rows=[]
    for label,offset in zip(['lo','center','hi'],[-width,0,width]):
        case=f'{prefix}_r{a.round}_{label}_tt';tb=H/'tb'/(case+'.scs');assert not tb.exists()
        text,n=re.subn(r'\bphase_deg=\S+',f'phase_deg={phase+offset:.17g}',body);assert n==1
        tb.write_text(text,encoding='utf-8',newline='\n')
        rows.append(dict(case=case,run=f'cp{a.variant}balance0{a.round}',phase_deg=phase+offset,tb_sha256=sha(tb)))
    p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),variant=a.variant,round=a.round,cases=rows,
        source_validation=proof.name,source_validation_sha256=sha(proof),operating_validation=initial.name,operating_validation_sha256=sha(initial),
        baseline_gain_validation_sha256=sha(gainproof),source_result=rp.relative_to(ROOT).as_posix(),source_result_sha256=sha(rp),
        source_input_sha256=sha(source),dependencies_sha256={k:v for k,v in r['inputs_sha256'].items() if k!=source.name},
        condition=iv['condition']+' Physical trial: '+iv['physical_change'],control_clamp_v=g['control_clamp_v'],
        proposed_center_deg=float(phase),center_method=method,half_width_deg=width,
        engineering_gates=dict(local_half_slope_relative_difference=.05,residual_phase_rad=.0005),
        main_dut_modified=False,noise_measured=False,full_pll_acceptance=False,
        launch_scope='Three serial fresh PSS cases,1thread each,1200s each; verify a free long slot. No automatic launch.',
        limitations=iv['limitations']+['Initial center extrapolates baseline gain; a measured bracket and local gain are required.',
            'Only extra observations are removed relative to the operating trial; all physical circuits, branch probes and solver parameters remain.',
            'Three DC-average current samples are not a dynamic transfer function or a noise validation.'])
    dst.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps(dict(cases=rows,proposed_center_deg=phase),indent=2))

if __name__=='__main__':main()
