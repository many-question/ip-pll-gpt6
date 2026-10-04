"""Re-match tail560 to the newly measured .125ps CF40 carrier, without relaxing gates."""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    proof=H/'results/vco_refinement_probe_validation.json';v=json.loads(proof.read_text())
    assert v['complete'] and all(x['sparse_precision_passed'] for x in v['cases'])
    assert not v['refined_candidate_comparison']['frequency_match_passed']
    first=H/'results/vco_tail_matched_noise_validation.json';second=H/'results/vco_tail_matched2_noise_validation.json'
    a=json.loads(first.read_text());b=json.loads(second.read_text());slope=(b['candidate']['rf_hz']-a['candidate']['rf_hz'])/(b['proposed_control_v']-a['proposed_control_v']);assert slope>0
    baseline,candidate=[x['refined'] for x in v['cases']]
    ctrl=b['proposed_control_v']+(baseline['rf_hz']-candidate['rf_hz'])/slope;assert .2<ctrl<1
    src=H/'tb/vco_tail560_refined_probe_tt.scs';s=src.read_text();old=float(re.search(r'^VC \(ctrl 0\) vsource dc=(\S+)',s,re.M)[1]);assert abs(old-b['proposed_control_v'])<1e-14
    s,n=re.subn(r'^VC \(ctrl 0\) vsource dc=\S+',f'VC (ctrl 0) vsource dc={ctrl:.17g}',s,flags=re.M);assert n==1
    case='vco_tail560_refined_match_tt';dst=H/'tb'/(case+'.scs');assert not dst.exists();dst.write_text(s,encoding='utf-8',newline='\n')
    p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),run='vcotailrefmatch01',case=case,
           source_run='vcorefine01',source_case='vco_tail560_refined_probe_tt',baseline_case='vco_cf40_refined_probe_tt',
           source_validation=proof.name,source_validation_sha256=sha(proof),target_rf_hz=baseline['rf_hz'],
           proposed_control_v=ctrl,previous_control_v=old,proposal_slope_hz_per_v=slope,
           slope_sources=[dict(path=x.name,sha256=sha(x)) for x in [first,second]],
           source_tb_sha256=sha(src),tb_sha256=sha(dst),relative_rf_match_limit=1e-4,
           condition='TT27/1.2V/Q5RLC/CF40/MT560um2um/c21/fixedM4/10fF/staticreference,onlyXVnoise. FreshPSS .125ps/127harms/1023sidebands.',
           main_dut_modified=False,full_pll_acceptance=False,
           limitations=['Old .5ps local tuning slope only proposes a new control; the frequency match must be measured at .125ps.',
                        'Six offsets cannot establish a complete integrated jitter result or full-grid precision.',
                        'The original154ppm mismatch is preserved; the100ppm gate is unchanged.',
                        'Tail dimensions, coarse code and control differ from the CF40 baseline; not a pure area effect.',
                        'Free VCO with static reference, not a locked complete PLL.'])
    pp=H/'results/vco_tail_refined_match_protocol.json';assert not pp.exists();pp.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps(p,indent=2))

if __name__=='__main__':main()
