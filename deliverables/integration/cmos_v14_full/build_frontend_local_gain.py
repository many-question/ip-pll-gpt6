"""Build a measured-branch local phase triplet; never assume its zero is exact."""
from pathlib import Path
import argparse,datetime,hashlib,json,re

H=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--round',type=int,choices=[1,2,3],default=1)
    ap.add_argument('--half-width-deg',type=float,default=5.);a=ap.parse_args()
    assert 0<a.half_width_deg<=15
    proof=H/'results'/('frontend_gain_validation.json' if a.round==1 else f'frontend_local_gain{a.round-1}_validation.json')
    v=json.loads(proof.read_text());assert v['complete'] and v['periodic_all_passed']
    assert v['unique_negative_feedback_branch'];phase=v['proposed_phase_deg'];assert phase is not None
    # An immutable protocol records the exact previous validation used to pick
    # the centre. Re-evaluation of an old result cannot silently change it.
    source=H/'tb/frontend_gain_p0_tt.scs';body=source.read_text();rows=[]
    for label,offset in [('lo',-a.half_width_deg),('center',0),('hi',a.half_width_deg)]:
        value=phase+offset;case=f'frontend_local{a.round}_{label}_tt';dst=H/'tb'/(case+'.scs')
        assert not dst.exists()
        tb,n=re.subn(r'\bphase_deg=\S+',f'phase_deg={value:.17g}',body);assert n==1
        dst.write_text(tb,encoding='utf-8',newline='\n')
        rows.append(dict(case=case,phase_deg=value,run=f'frontendlocal0{a.round}',tb_sha256=sha(dst)))
    p=dict(scope=__doc__,round=a.round,time=datetime.datetime.now().astimezone().isoformat(),cases=rows,
           source_validation=proof.name,source_validation_sha256=sha(proof),condition=v['condition'],
           control_clamp_v=v['control_clamp_v'],proposed_center_deg=phase,half_width_deg=a.half_width_deg,
           source_tb_sha256=sha(source),
           engineering_gates=dict(local_half_slope_relative_difference=.05,residual_phase_rad=.0005),
           full_pll_acceptance=False,main_dut_modified=False,limitations=v['limitations'])
    dst=H/'results'/f'frontend_local_gain{a.round}_protocol.json';assert not dst.exists()
    dst.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
