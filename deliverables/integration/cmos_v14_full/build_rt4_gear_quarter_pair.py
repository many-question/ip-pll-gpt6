"""Prepare a method-only RT4 .25 ps quiet/noisy pair; no candidate adoption."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    source=H/'results/full_pll_rt4_quarter_pair_protocol.json'
    validation=H/'results/full_pll_rt4_quarter_pair_validation.json'
    audit=H/'results/full_pll_rt4_quarter_noise_recovery_audit.json'
    p=json.loads(source.read_text());v=json.loads(validation.read_text());a=json.loads(audit.read_text())
    assert v['high_offset_diagnostic_valid'] and a['recovery_audit_passed']
    assert a['validation_sha256']==sha(validation) and v['protocol_sha256']==sha(source)
    assert sha(H/'state_inputs'/p['text_state'])==p['text_state_sha256']
    available={f.name:f for f in (H.parents[1]/'blocks').glob('*/*.scs')}
    assert all(sha(available[k])==value for k,value in p['physical_dependency_hashes'].items())
    assert p['maxstep_s']==2.5e-13 and p['seed']==11 and p['iabstol']==1e-12
    cases=[]
    for old,label in zip(p['cases'],['off','on']):
        src=H/'tb'/(old['case']+'.scs');body=src.read_text();assert sha(src)==old['tb_sha256']
        assert body.count('method=traponly')==1
        case='full_pll_rt4_gear_quarter_'+label+'_tt';dest=H/'tb'/(case+'.scs');assert not dest.exists()
        dest.write_text(body.replace('method=traponly','method=gear2only'),encoding='utf-8',newline='\n')
        assert dest.read_text().replace('method=gear2only','method=traponly')==body
        cases.append(dict(run='pllrt4gearquarter'+label+'ssd01',case=case,noise_enabled=old['noise_enabled'],tb_sha256=sha(dest)))
    p.update(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=cases,method='gear2only',
        parent_protocol_sha256=sha(source),baseline_validation_sha256=sha(validation),baseline_recovery_audit_sha256=sha(audit),
        launch_policy_sha256=sha(H/'single_launch_transport.py'),comparison_parameter='Integration method only: traponly to gear2only.',
        study_purpose='Check method sensitivity of the complete settled RT4 candidate after the timestep/seed studies.',
        convergence_interpretation='Gear can introduce artificial damping. Fewer warnings or a lower RMS do not establish correctness or candidate adoption.',
        deployment_rule='New method-matched quiet must pass unchanged numerical, initialization, actual-status and stationarity gates before noise dispatch; never reuse traponly quiet.',
        quiet_wall_timeout_s=86400,physical_dut_modified=False,full_pll_acceptance=False,
        method_documentation=dict(path='research/spectre_help/pss.txt',sha256=sha(ROOT/'research/spectre_help/pss.txt'),
            interpretation='Installed solver documentation and previously completed transient method controls support gear2only; artificial damping remains a validation risk.'))
    p['limitations']+=['Both method results and any failure are retained. This study does not resolve bandwidth, low-offset coverage or discrete-spur classification.',
        'The current-tolerance original-V14 branch is separate; its result cannot validate this RT4 method change.']
    dest=H/'results/full_pll_rt4_gear_quarter_pair_protocol.json';assert not dest.exists();dest.write_text(json.dumps(p,indent=2)+'\n')
    print(dest)

if __name__=='__main__':main()
