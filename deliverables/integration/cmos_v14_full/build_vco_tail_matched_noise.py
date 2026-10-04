"""Measure actual device noise at the proposed baseline-frequency tail setting."""
from pathlib import Path
import argparse,datetime,hashlib,json
H=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--refine',action='store_true');args=ap.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proof=H/'results/vco_tail_rematch_validation.json';v=json.loads(proof.read_text())
assert v['complete'] and v['frequency_bracketed']
control=v['proposed_control_v'];assert .2<=control<=1.
previous=None
if args.refine:
    previous_path=H/'results/vco_tail_matched_noise_validation.json';previous=json.loads(previous_path.read_text())
    assert not previous['frequency_match_passed']
    points=[(x['rf_hz'],x['control_v']) for x in v['cases']]+[(previous['candidate']['rf_hz'],previous['proposed_control_v'])]
    target=v['target_rf_hz'];lo=max((f,c) for f,c in points if f<target);hi=min((f,c) for f,c in points if f>target)
    control=lo[1]+(target-lo[0])/(hi[0]-lo[0])*(hi[1]-lo[1]);assert .2<=control<=1.
src=H/'tb/vco_bias_cf40_tail560_tt.scs';body=src.read_text()
assert body.count('VB1 (b1 0) vsource dc=1.2')==1 and body.count('VC (ctrl 0) vsource dc=0.679')==1
body=body.replace('VB1 (b1 0) vsource dc=1.2','VB1 (b1 0) vsource dc=0')
body=body.replace('VC (ctrl 0) vsource dc=0.679',f'VC (ctrl 0) vsource dc={control:.17g}')
case='vco_tail560_matched2_tt' if args.refine else 'vco_tail560_matched_tt';dest=H/'tb'/(case+'.scs');assert not dest.exists();dest.write_text(body)
p=dict(scope=__doc__,run='vcotailmatched02' if args.refine else 'vcotailmatched01',case=case,time=datetime.datetime.now().astimezone().isoformat(),
    bracket_validation_sha256=sha(proof),target_rf_hz=v['target_rf_hz'],proposed_control_v=control,coarse_code=21,
    source_tb_sha256=sha(src),tb_sha256=sha(dest),relative_rf_match_limit=1e-4,
    condition='TT27/1.2V/Q5RLC/CF40/MT560um2um/c21/interpolatedctrl/staticreference/fixedM4/10fF;freshPSS .5ps/127harms/255sidebands,onlyXVnoise.',
    offsets_hz=[1e4,1e5,1e6,1e7,1e8,492e6],main_dut_modified=False,full_pll_acceptance=False,
    limitations=['Actual RF match must be verified after fresh PSS; interpolation alone is not a match.',
        'Only six offsets; no integrated RMS.','Coarse code and control differ to compensate loading; improvements cannot be assigned solely to intrinsic MT area.',
        'Static-reference fixedM4 load differs from the complete PLL; no adoption or PVT claim.'])
if previous:p['previous_measured_point_sha256']=sha(previous_path)
name='vco_tail_matched2_noise_protocol.json' if args.refine else 'vco_tail_matched_noise_protocol.json'
(H/'results'/name).write_text(json.dumps(p,indent=2)+'\n');print(case,control)
