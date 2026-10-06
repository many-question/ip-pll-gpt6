"""Prepare an original-V14 0.25 ps matched pair, changing only maximum timestep."""
from pathlib import Path
import datetime, hashlib, json

H = Path(__file__).resolve().parent
ROOT = H.parents[3]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parent = H/'results/full_pll_main_settled_ssd_cwd_pair_protocol.json'
    validation = H/'results/full_pll_main_settled_ssd_cwd_pair_validation.json'
    audit = H/'results/full_pll_main_noise_recovery_audit.json'
    p = json.loads(parent.read_text()); v = json.loads(validation.read_text()); a = json.loads(audit.read_text())
    assert v['complete'] and v['high_offset_diagnostic_valid'] and a['recovery_audit_passed']
    assert v['protocol_sha256'] == sha(parent) and a['validation_sha256'] == sha(validation)
    assert sha(H/'state_inputs'/p['text_state']) == p['text_state_sha256']
    available = {f.name:f for f in (H.parents[1]/'blocks').glob('*/*.scs')}
    assert all(sha(available[k]) == val for k,val in p['physical_dependency_hashes'].items())
    cases = []
    for c, label in zip(p['cases'], ['off','on']):
        source = H/'tb'/(c['case']+'.scs'); assert sha(source) == c['tb_sha256']
        body = source.read_text(); assert body.count('maxstep=.5p ') == 1
        case = 'full_pll_main_quarter_'+label+'_tt'; dest = H/'tb'/(case+'.scs')
        assert not dest.exists()
        dest.write_text(body.replace('maxstep=.5p ','maxstep=.25p '),encoding='utf-8',newline='\n')
        cases.append(dict(run='pllmainquarter'+label+'ssd01',case=case,noise_enabled=c['noise_enabled'],tb_sha256=sha(dest)))
    for k in ['retry_of_protocol','retry_of_protocol_sha256','retry_reason','migration_source_protocol',
              'migration_source_protocol_sha256','migration_reason']:
        p.pop(k,None)
    p.update(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=cases,
        maxstep_s=2.5e-13,parent_protocol_sha256=sha(parent),baseline_validation_sha256=sha(validation),
        baseline_recovery_audit_sha256=sha(audit),comparison_parameter='maxstep only: 0.5 ps to 0.25 ps',
        convergence_interpretation='Compare matched-quiet-subtracted spectra and RMS with finite-record uncertainty; matching random seed does not guarantee identical adaptive noise realization.',
        physical_dut_modified=False,full_pll_acceptance=False)
    p['limitations'] += ['Maximum timestep halving alone does not establish tolerance, method, noise bandwidth, seed or record-length convergence.']
    dst = H/'results/full_pll_main_quarter_pair_protocol.json'; assert not dst.exists()
    dst.write_text(json.dumps(p,indent=2)+'\n')
    print(json.dumps(dict(protocol=str(dst),cases=cases,physical_dut_modified=False),indent=2))


if __name__ == '__main__': main()
