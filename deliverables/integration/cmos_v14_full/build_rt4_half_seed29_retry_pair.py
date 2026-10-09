"""Retry only the failed transport; retain identical RT4 seed29 solver inputs."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    source=H/'results/full_pll_rt4_half_seed29_pair_protocol.json';p=json.loads(source.read_text())
    failure=ROOT/'research/rt4_half_seed29_failure84_remote.json';a=json.loads(failure.read_text())
    test=H/'results/console_isolation_validation84.json';t=json.loads(test.read_text())
    assert not a['live'] and a['exit_code']=='141' and a['terminal_errors'] is None
    assert all(t['checks'].values()) and t['implementation_sha256']==sha(H/'single_launch_transport.py')
    for c in p['cases']:assert sha(H/'tb'/(c['case']+'.scs'))==c['tb_sha256']
    assert p['seed']==29 and p['maxstep_s']==5e-13
    assert sha(H/'state_inputs'/p['text_state'])==p['text_state_sha256']
    available={f.name:f for f in (H.parents[1]/'blocks').glob('*/*.scs')}
    assert all(sha(available[n])==v for n,v in p['physical_dependency_hashes'].items())
    p['cases'][1]['run']='pllrt4halfseed29onssd02'
    p.update(time=datetime.datetime.now().astimezone().isoformat(),scope=__doc__,parent_protocol_sha256=sha(source),
        launch_policy_sha256=sha(H/'single_launch_transport.py'),failed_predecessor='pllrt4halfseed29onssd01',
        failed_predecessor_audit_sha256=sha(failure),console_isolation_test_sha256=sha(test),
        retry_reason='Original remote exited 141 with no Spectre terminal footer after an SSH disconnect. Outputs retained as failed evidence. Isolate stdout/stderr from SSH; no circuit or solver change.',
        comparison_parameter='Transport-only retry: same case TB, DUT, initial state, reference phase, method, tolerances, noise bandwidth, stop and seed 29.',
        full_pll_acceptance=False)
    p['limitations']+=['The failed predecessor must not enter the step/seed matrix. Retry completion requires the normal clean terminal log and complete raw/state checks.']
    dest=H/'results/full_pll_rt4_half_seed29_retry_pair_protocol.json';assert not dest.exists();dest.write_text(json.dumps(p,indent=2)+'\n')
    print(dest)
if __name__=='__main__':main()
