"""Dense matched VCO comparison plus full-grid numerical checks at both designs."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    proof=H/'results/vco_tail_refined_match_validation.json';v=json.loads(proof.read_text())
    assert v['simulation_passed'] and v['frequency_match_passed'] and all(x<0 for x in v['timing_psd_change_db'])
    pp=H/'results/vco_matched_dense_protocol.json';assert not pp.exists();rows=[]
    source_case='vco_tail560_refined_match_tt'
    variants=[('candidate_025','vcotailrefmatch01',source_case,True),
              ('baseline_0125','vcorefine01','vco_cf40_refined_probe_tt',False),
              ('candidate_0125','vcotailrefmatch01',source_case,False)]
    for variant,source_run,src_case,coarser in variants:
        source=H/'tb'/(src_case+'.scs');body=source.read_text();src=R/source_run/src_case
        result=json.loads((src/'result.json').read_text());assert result['ok'] and result['remote_inputs_match']
        old='values=[10k 100k 1M 10M 100M 492M]';assert body.count(old)==1
        body=body.replace(old,'start=10k stop=492M dec=20')
        if coarser:
            assert body.count('maxstep=0.125p')==body.count('maxsideband=1023')==1
            body=body.replace('maxstep=0.125p','maxstep=0.25p').replace('maxsideband=1023','maxsideband=511')
        case='vco_matched_dense_'+variant+'_tt';tb=H/'tb'/(case+'.scs');assert not tb.exists()
        tb.write_text(body,encoding='utf-8',newline='\n')
        rows.append(dict(run='vcomatcheddense01',case=case,variant=variant,source_run=source_run,source_case=src_case,
                         source_result_sha256=sha(src/'result.json'),source_tb_sha256=sha(source),tb_sha256=sha(tb),
                         coarser_numerical_setting=coarser,
                         dependencies_sha256={k:x for k,x in result['inputs_sha256'].items() if k!=src_case+'.scs'}))
    base=R/'vcobiasband01/vco_band_cf40_finer_tt'
    p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=rows,
           source_match_validation=proof.name,source_match_validation_sha256=sha(proof),
           original_baseline=dict(run='vcobiasband01',case=base.name,source_result_sha256=sha(base/'result.json')),
           condition='TT27/1.2V/Q5RLC/CF40/staticreference/fixedM4/10fF/onlyXVnoise. Baseline originaltail/c23/control.679V; candidateMT560um2um/c21/control.7530325672469256V. All freshPSS.',
           precision_limits=dict(max_psd_delta_db=.1,max_relative_rms_change=.01,max_relative_rf_change=1e-4),
           frequency_match_limit=1e-4,grid=dict(start_hz=1e4,stop_hz=492e6,points_per_decade=20),
           integration_lower_bounds_hz=[1e6,2e6,5e6,1e7,1e8],
           main_dut_modified=False,full_pll_acceptance=False,
           launch_scope='One long slot, three serial one-thread cases; no native/periodic reuse and no circuit adoption.',
           limitations=['Full-grid precision is checked at each design and exact control value; no changed-bias run counts as a pure numerical check.',
                        'Only offsets>=1MHz are integrated to the commonminimum fRF/8. Freeoscillator low offsets are not lockedPLL jitter.',
                        'Tail dimensions, coarse code, control, amplitude and current differ; matched-carrier comparison is not a pure area experiment.',
                        'Active reference, programmablebank,RT4,completePLL andPVT remain outside this fixture.'])
    pp.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps([x['case'] for x in rows]))

if __name__=='__main__':main()
