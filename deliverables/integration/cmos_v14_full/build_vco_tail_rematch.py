"""Bracket the enlarged-tail candidate at the baseline's measured RF carrier.

Use coarse21 and two physical varactor controls, with unchanged fine PSS
settings. This is a frequency screen; no noise analysis or acceptance claim.
"""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proof=H/'results/vco_tail_adjusted_validation.json';v=json.loads(proof.read_text());assert v['complete']
assert all(x<0 for x in v['cases'][2]['timing_psd_change_db'])
src=H/'tb/vco_bias_cf40_tail560_tt.scs';body=src.read_text()
assert body.count('VB1 (b1 0) vsource dc=1.2')==1 and body.count('VC (ctrl 0) vsource dc=0.679')==1
body=body.replace('VB1 (b1 0) vsource dc=1.2','VB1 (b1 0) vsource dc=0')
body=re.sub(r'^pn .*\n','',body,flags=re.M)
cases=[]
for suffix,ctrl in [('v050',.5),('v080',.8)]:
    name='vco_tail560_c21_'+suffix+'_tt';dest=H/'tb'/(name+'.scs');assert not dest.exists()
    dest.write_text(body.replace('VC (ctrl 0) vsource dc=0.679',f'VC (ctrl 0) vsource dc={ctrl:g}'))
    cases.append(dict(case=name,control_v=ctrl,coarse_code=21,tb_sha256=sha(dest)))
p=dict(scope=__doc__,run='vcotailmatch01',time=datetime.datetime.now().astimezone().isoformat(),cases=cases,
    source_validation_sha256=sha(proof),target_rf_hz=v['cases'][0]['rf_hz'],source_tb_sha256=sha(src),
    condition='TT27/1.2V/Q5RLC/CF40/MT560um2um/staticreference/fixedM4/10fF;freshPSS .5ps maxstep,300ns tstab,harms127. No PNoise.',
    physical_change='Only externally driven coarse code23->21 (b1 low) and varactor control .679->.5 or.8V. Remaining physical circuit unchanged.',
    rationale='The measured tail560 candidate improves six timing PSD points but lowers carrier0.486%. Establish a measured frequency bracket before rerunning noise at a matched carrier.',
    limits=dict(target_relative_rf_error=1e-4,control_v=[.2,1.0]),
    full_pll_acceptance=False,main_dut_modified=False,
    limitations=['Independent static tuning screen, not fullPLL capture.','Changing coarse bits also changes loading; matched frequency does not isolate intrinsic transistor-noise effects.','Two tuning points are only an interpolation proposal; the proposed matched point requires another actual PSS measurement.'])
(H/'results/vco_tail_rematch_protocol.json').write_text(json.dumps(p,indent=2)+'\n');print(' '.join(x['case'] for x in cases))
