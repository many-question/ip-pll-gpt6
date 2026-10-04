"""Select a quieter shooting boundary from the saved physical transient.

This tests sensitivity to the start phase, not a change in period or accuracy.
Only saved logic nodes are screened; hidden state sensitivities remain unknown.
"""
from pathlib import Path
import argparse,hashlib,json,re
import numpy as np
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
parser=argparse.ArgumentParser()
parser.add_argument('--run',default='coretripsupply01')
parser.add_argument('--case',default='core_pulsetrip_supply_noise_tt')
parser.add_argument('--output',default='core_boundary_diagnosis.json')
args=parser.parse_args()
assert all(re.fullmatch(r'[A-Za-z0-9_]+',x) for x in [args.run,args.case])
assert Path(args.output).name==args.output and args.output.endswith('.json')
j=ROOT/'research/runs/spectre_cmos_v14_full'/args.run/args.case
source=j/'tstab_last_two_periods.npz'
with np.load(source) as z:d={k:z[k] for k in z.files}
period=250e-9;t=d['time'];begin=float(t[-1]-period)
keys=[k for k in d if k.startswith('XP.XD.') or k in ['XP.clk','XP.q1','XP.data','XP.acqclk','out','XP.refb','XP.pulse']]
offsets=np.arange(0,period*1e12-3,1.)*1e-12
guard=np.arange(-2.5,2.51,.5)*1e-12
def slopes(at):
    return np.asarray([(np.interp(at+.5e-12,t,d[k])-np.interp(at-.5e-12,t,d[k]))/1e-12 for k in keys])
# Require a quiet5ps neighborhood, avoiding a minimum caused by an isolated sample.
score=np.zeros(len(offsets))
for g in guard:
    score=np.maximum(score,np.max(abs(slopes(begin+offsets+g)),axis=0))
idx=int(np.argmin(score));shift=float(offsets[idx]);old=slopes(begin);new=slopes(begin+shift)
out=dict(scope=__doc__,raw_source_sha256=str(d['source_sha256']),
    analysis_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    original_boundary_us=begin*1e6,candidate_offset_ps=shift*1e12,
    saved_logic_nodes=keys,guard_neighborhood_ps=[-2.5,2.5],selection_step_ps=1.,
    original_guarded_max_slope_v_per_s=float(score[0]),candidate_guarded_max_slope_v_per_s=float(score[idx]),
    original_instant_max_slope_v_per_s=float(max(abs(old))),candidate_instant_max_slope_v_per_s=float(max(abs(new))),
    original_nodes=[dict(node=k,v=float(np.interp(begin,t,d[k])),slope_v_per_s=float(s)) for k,s in zip(keys,old)],
    candidate_nodes=[dict(node=k,v=float(np.interp(begin+shift,t,d[k])),slope_v_per_s=float(s)) for k,s in zip(keys,new)],
    hypothesis='Starting shooting away from simultaneous divider transitions may improve the Newton map. Selection from the initialization trace does not prove convergence or uniqueness.',
    evidence='Local Spectre21.1 pss help: starting during strong nonlinear switching can degrade convergence; choose a settled switching phase.',
    full_pll_acceptance=False,pss_convergence_proven=False)
(H/'results'/args.output).write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['original_nodes','candidate_nodes','saved_logic_nodes']},indent=2))
