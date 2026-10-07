"""Prepare an independent seed at 0.25 ps; reuse the identical validated quiet case."""
from pathlib import Path
import datetime, hashlib, json

H = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parent = H/'results/full_pll_main_quarter_pair_protocol.json'
    validation = H/'results/full_pll_main_quarter_pair_validation.json'
    audit = H/'results/full_pll_main_quarter_noise_recovery_audit.json'
    p = json.loads(parent.read_text());v = json.loads(validation.read_text());a = json.loads(audit.read_text())
    assert v['high_offset_diagnostic_valid'] and a['recovery_audit_passed']
    assert v['protocol_sha256'] == sha(parent) and a['validation_sha256'] == sha(validation)
    assert sha(H/'state_inputs'/p['text_state']) == p['text_state_sha256']
    available = {f.name:f for f in (H.parents[1]/'blocks').glob('*/*.scs')}
    assert all(sha(available[k]) == value for k,value in p['physical_dependency_hashes'].items())
    quiet = p['cases'][0]
    assert sha(H/'tb'/(quiet['case']+'.scs')) == quiet['tb_sha256']
    source = H/'tb'/(p['cases'][1]['case']+'.scs');body = source.read_text()
    assert sha(source) == p['cases'][1]['tb_sha256'] and body.count('noiseseed=11 ') == 1
    case = 'full_pll_main_quarter_seed29_on_tt';dest = H/'tb'/(case+'.scs')
    assert not dest.exists()
    dest.write_text(body.replace('noiseseed=11 ', 'noiseseed=29 '),encoding='utf-8',newline='\n')
    assert dest.read_text().replace('noiseseed=29 ', 'noiseseed=11 ') == body
    p['cases'][1] = dict(run='pllmainquarterseed29onssd01',case=case,noise_enabled=True,tb_sha256=sha(dest))
    p.update(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),seed=29,
        parent_protocol_sha256=sha(parent),baseline_validation_sha256=sha(validation),
        baseline_recovery_audit_sha256=sha(audit),comparison_parameter='noise seed only: 11 to 29',
        quiet_reuse_reason='Exact same DUT, initial state, reference phase, stop, solver and noise-off prefix. The retained quiet deck has seed 11 with isnoisy=0 throughout; seed cannot affect that noise-disabled trace.',
        convergence_interpretation='One additional independent realization tests seed sensitivity at fixed 0.25 ps; two seeds alone do not establish statistical or numerical convergence.',
        physical_dut_modified=False,full_pll_acceptance=False)
    p['limitations'] += ['Seed 29 was fixed before observing its output; retain both seeds regardless of which RMS is lower.']
    target = H/'results/full_pll_main_quarter_seed29_pair_protocol.json';assert not target.exists()
    target.write_text(json.dumps(p,indent=2)+'\n')
    print(target)


if __name__ == '__main__': main()
