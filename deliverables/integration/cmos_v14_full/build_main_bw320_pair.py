"""Prepare a bandwidth-only 160 to 320 GHz original V14 quiet/noisy comparison."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    src=H/'results/full_pll_main_iab100_retry_pair_protocol.json'
    vp=H/'results/full_pll_main_iab100_retry_pair_validation.json'
    ap=H/'results/full_pll_main_iab100_noise_recovery_audit.json'
    cp=H/'results/full_pll_main_noise_current_tolerance_comparison.json'
    p=json.loads(src.read_text());v=json.loads(vp.read_text());a=json.loads(ap.read_text());c=json.loads(cp.read_text())
    assert a['recovery_audit_passed'] and v['high_offset_diagnostic_valid'] and all(v['checks'].values()) and c['comparison_valid']
    assert a['validation_sha256']==sha(vp) and v['protocol_sha256']==sha(src)
    assert p['iabstol']==1e-13 and p['maxstep_s']==2.5e-13 and p['noisefmax_hz']==160e9 and p['seed']==11
    assert sha(H/'state_inputs'/p['text_state'])==p['text_state_sha256']
    available={f.name:f for f in (H.parents[1]/'blocks').glob('*/*.scs')}
    assert all(sha(available[k])==s for k,s in p['physical_dependency_hashes'].items())
    cases=[]
    for old,label in zip(p['cases'],['off','on']):
        f=H/'tb'/(old['case']+'.scs');assert sha(f)==old['tb_sha256'];body=f.read_text();assert body.count('noisefmax=160G')==1
        case='full_pll_main_bw320_'+label+'_tt';dest=H/'tb'/(case+'.scs');assert not dest.exists()
        dest.write_text(body.replace('noisefmax=160G','noisefmax=320G'),encoding='utf-8',newline='\n')
        assert dest.read_text().replace('noisefmax=320G','noisefmax=160G')==body
        cases.append(dict(run='pllmainbw320'+label+'ssd01',case=case,noise_enabled=old['noise_enabled'],tb_sha256=sha(dest)))
    for key in ['failed_predecessor','failed_predecessor_audit_sha256','retry_reason']:
        p.pop(key,None)
    p.update(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=cases,noisefmax_hz=320e9,parent_protocol_sha256=sha(src),baseline_validation_sha256=sha(vp),baseline_recovery_audit_sha256=sha(ap),tolerance_comparison_sha256=sha(cp),comparison_parameter='Noise source bandwidth only: noisefmax 160 GHz to 320 GHz.',study_purpose='Test high-frequency source-noise bandwidth sensitivity before committing to much longer low-offset records.',deployment_rule='New bandwidth-matched quiet must pass the unchanged five gates before noisy dispatch; retain its own quiet template.',convergence_interpretation='A single seed bandwidth doubling is a sensitivity screen, not statistical or full-band convergence.',quiet_wall_timeout_s=86400,launch_policy_sha256=sha(H/'single_launch_transport.py'),physical_dut_modified=False,full_pll_acceptance=False,bandwidth_documentation=dict(path='research/spectre_help/tran.txt',sha256=sha(ROOT/'research/spectre_help/tran.txt'),interpretation='noisefmax controls generated source bandwidth and imposes maximum timestep 0.5/noisefmax; 1.5625 ps at 320 GHz remains above the explicit 0.25 ps ceiling. Adaptive steps and random realizations may still differ.'))
    p['limitations'] += ['Source-noise bandwidth is different from the measured output-offset integration band; doubling noisefmax does not extend the record to 10 kHz.','Same seed with changed source bandwidth is not an identical excitation; retain both spectra, all outcomes and finite-record uncertainty.']
    dest=H/'results/full_pll_main_bw320_pair_protocol.json';assert not dest.exists();dest.write_text(json.dumps(p,indent=2)+'\n')
    print(dest,flush=True)

if __name__=='__main__':main()
