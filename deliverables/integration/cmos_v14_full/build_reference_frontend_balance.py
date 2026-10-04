"""Build a physical-reference replacement triplet, preserving the other frontend blocks.

The first center is only a delay-compensated guess. Subsequent centers must
come from measured bracketing data; none is considered balanced until measured.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
normal=lambda s:re.sub(r'\b(writefinal|writepss)="[^"]+"',r'\1="STATE"',s).strip()

def replacement(body):
    old='XREF (ref refb vdd 0) tx_reference_buffer';new='XREF (ref refb vdd 0) reference_buffer_taper2_v14'
    assert body.count(old)==1 and body.count('include "cells.scs"')==1
    return body.replace(old,new).replace('include "cells.scs"','include "cells.scs"\ninclude "reference_buffer_taper2_v14.scs"')+'\nsave XREF.a XREF.b XREF.c\n'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--round',type=int,choices=[1,2,3],default=1)
    ap.add_argument('--half-width-deg',type=float);args=ap.parse_args()
    width=args.half_width_deg or (15 if args.round==1 else 1)
    assert 0<width<=15
    noise=H/'results/reference_buffer_noise_validation.json';nv=json.loads(noise.read_text())
    precision=H/'results/reference_buffer_precision_protocol.json';pv=json.loads(precision.read_text())
    assert nv['complete'] and nv['noise_all_valid'] and nv['candidate_relative_rms_change']<0
    assert pv['baseline_validation_sha256']==sha(noise)
    oldgain=H/'results/frontend_local_gain2_validation.json';g=json.loads(oldgain.read_text())
    assert g['balanced_center_verified'] and g['local_gain_verified'] and g['periodic_all_passed']
    center=g['cases'][1];rp=ROOT/center['source_result'];assert sha(rp)==center['source_sha256']
    src=rp.parent/'inputs'/(center['case']+'.scs');original=src.read_text()
    block=B/'reference_buffer_taper2_v14.scs';candidate=nv['cases'][1]
    cp=json.loads((H/'results/reference_buffer_noise_protocol.json').read_text())
    assert sha(block)==cp['cases'][1]['dependencies_sha256'][block.name]
    base_deps={k:v for k,v in json.loads(rp.read_text())['inputs_sha256'].items() if k!=src.name}
    assert block.name not in base_deps
    dependencies=dict(base_deps,**{block.name:sha(block)})
    if args.round==1:
        phase=(center['phase_deg']-(candidate['delay_ps']-nv['cases'][0]['delay_ps'])*1e-12*3.936e9*360)%360
        proof=noise;method='Unverified estimate: phi_new=phi_old-2*pi*fRF*(new_reference_delay-old_reference_delay).'
    else:
        proof=H/'results'/f'reference_frontend_balance{args.round-1}_validation.json';v=json.loads(proof.read_text())
        assert v['complete'] and v['periodic_all_passed'] and v['unique_negative_feedback_branch']
        assert v['candidate_block_sha256']==sha(block)
        phase=v['proposed_phase_deg'];assert phase is not None;method=v['proposed_phase_method']
    body=replacement(original)
    body=re.sub(r'\bwritefinal="[^"]+"','writefinal="__FINAL_STATE__"',body)
    body=re.sub(r'\bwritepss="[^"]+"','writepss="__PERIODIC_STATE__"',body)
    rows=[];pp=H/'results'/f'reference_frontend_balance{args.round}_protocol.json'
    cases=[f'reference_frontend_r{args.round}_{label}_tt' for label in ['lo','center','hi']]
    assert not pp.exists() and not any((H/'tb'/(x+'.scs')).exists() for x in cases)
    for case,offset in zip(cases,[-width,0,width]):
        value=phase+offset;tb,n=re.subn(r'\bphase_deg=\S+',f'phase_deg={value:.17g}',body);assert n==1
        dst=H/'tb'/(case+'.scs');dst.write_text(tb,encoding='utf-8',newline='\n')
        rows.append(dict(case=case,run=f'referencebalance0{args.round}',phase_deg=value,tb_sha256=sha(dst)))
    p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),round=args.round,cases=rows,
           source_validation=proof.name,source_validation_sha256=sha(proof),
           baseline_gain_validation=oldgain.name,baseline_gain_validation_sha256=sha(oldgain),
           baseline_result=center['source_result'],baseline_result_sha256=sha(rp),
           baseline_input_sha256=sha(src),candidate_block_sha256=sha(block),dependencies_sha256=dependencies,
           precision_protocol_sha256=sha(precision),launch_gate='reference_buffer_precision_validation complete, noise_all_valid, independent_precision_verified; verify before launch.',
           condition='TT27/1.2V/24MHz ideal10psreference/3.936GHz ideal measured-waveform RF replay; physical taper2 reference + original sampler/CP/pulser/bias/validity, control clamp and1.9pFcontrol-load approximation.',
           control_clamp_v=g['control_clamp_v'],proposed_center_deg=phase,center_method=method,
           center_is_unverified=True,half_width_deg=width,
           engineering_gates=dict(local_half_slope_relative_difference=.05,residual_phase_rad=.0005),
           full_pll_acceptance=False,main_dut_modified=False,
           limitations=['Only the reference buffer is physically changed; idealRF and outputclamp still exclude LC/closed-loop dynamics.',
                        'Actual nonlinear sampler, pulser and detector loading included; control logic approximated as1.9pF.',
                        'First phase guess uses standalone2pF delay; the actual loaded circuit must be measured.',
                        'Initial15degree triplet brackets the branch; a smaller measured-centered triplet may be needed for accurate gain.',
                        'PSS/gain/mean balance alone do not validate noise or complete PLL jitter; no noise run is embedded here.'])
    pp.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps(p,indent=2))

if __name__=='__main__':main()
