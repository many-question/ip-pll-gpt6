"""Prepare the original V14 0.25 ps pair with only current tolerance tightened to 100 fA."""
from pathlib import Path
import datetime,hashlib,json

H=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parent=H/'results/full_pll_main_quarter_pair_protocol.json'
    validation=H/'results/full_pll_main_quarter_pair_validation.json'
    trigger=H/'results/full_pll_main_half_seed29_noise_recovery_audit.json'
    matrix=H/'results/full_pll_main_step_seed_matrix.json'
    p=json.loads(parent.read_text());v=json.loads(validation.read_text())
    assert v['high_offset_diagnostic_valid'] and v['protocol_sha256']==sha(parent)
    assert json.loads(trigger.read_text())['recovery_audit_passed']
    assert len(json.loads(matrix.read_text())['records'])==4
    assert sha(H/'state_inputs'/p['text_state'])==p['text_state_sha256']
    available={f.name:f for f in (H.parents[1]/'blocks').glob('*/*.scs')}
    assert all(sha(available[k])==val for k,val in p['physical_dependency_hashes'].items())
    assert p['seed']==11 and p['maxstep_s']==2.5e-13 and p['iabstol']==1e-12
    cases=[]
    for old,label in zip(p['cases'],['off','on']):
        src=H/'tb'/(old['case']+'.scs');assert sha(src)==old['tb_sha256']
        body=src.read_text();assert body.count('iabstol=1e-12')==1
        case='full_pll_main_iab100_'+label+'_tt';dest=H/'tb'/(case+'.scs');assert not dest.exists()
        dest.write_text(body.replace('iabstol=1e-12','iabstol=1e-13'),encoding='utf-8',newline='\n')
        assert dest.read_text().replace('iabstol=1e-13','iabstol=1e-12')==body
        cases.append(dict(run='pllmainiab100'+label+'ssd01',case=case,noise_enabled=old['noise_enabled'],tb_sha256=sha(dest)))
    p.update(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=cases,iabstol=1e-13,
        parent_protocol_sha256=sha(parent),baseline_validation_sha256=sha(validation),
        baseline_recovery_audit_sha256=sha(H/'results/full_pll_main_quarter_noise_recovery_audit.json'),
        trigger_half_seed29_audit_sha256=sha(trigger),trigger_step_seed_matrix_sha256=sha(matrix),
        comparison_parameter='iabstol only: 1 pA to 100 fA',physical_dut_modified=False,full_pll_acceptance=False,
        study_purpose='Extend the earlier short current-tolerance screen to the full settled original PLL. Independent quiet gate before noisy run.',
        seed_selection='Retain baseline seed 11 chosen before this tolerance result; no selection based on lower RMS.',
        convergence_interpretation='A clean run is a prerequisite, not convergence. Compare each noisy record with its own quiet; adaptive noise realizations can differ.',
        deployment_rule='Run the new 100 fA quiet first; only completion, clean numerical trace, initialization, actual status and unchanged full-window stationarity gates permit noise dispatch.',
        quiet_wall_timeout_s=86400)
    p['limitations'] += [
        'The earlier 100 fA short screen used a different RT4 initialization and cannot validate this whole original-DUT trace.',
        'A changed settled numerical operating point or failed quiet gate must be diagnosed; do not relax thresholds or reuse the 1 pA quiet.',
        'No convergence or lower-noise conclusion is established by tightening a tolerance alone.',
        'Integration method, noise bandwidth and longer low-offset records remain separate subsequent studies.']
    dest=H/'results/full_pll_main_iab100_pair_protocol.json';assert not dest.exists()
    dest.write_text(json.dumps(p,indent=2)+'\n');print(dest)


if __name__=='__main__':main()
