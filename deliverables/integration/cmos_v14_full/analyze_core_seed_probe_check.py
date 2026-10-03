"""Isolate three missing supply IC values; no inference of PSS or PLL acceptance."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from noise_utils import cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
R=ROOT/'research/runs/spectre_cmos_v14_full/coreseedcheck01'
rows=[];physical=None;tbs=[];signals={}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for kind in ['original','complete']:
    case=f'core_seed_{kind}_tt';j=R/case
    if not (j/'result.json').exists():continue
    r=json.loads((j/'result.json').read_text())
    if not r.get('local_outputs_sha256'):continue
    assert r['ok'] and r['remote_inputs_match'] and 'spectre completes with 0 errors' in (j/'spectre.out').read_text()
    deps={k:v for k,v in r['inputs_sha256'].items() if k!=case+'.scs' and not k.endswith('.ic')}
    if physical is None:physical=deps
    assert deps==physical
    tb=(j/'inputs'/(case+'.scs')).read_text()
    tbs.append(re.sub(r'readic="[^"]+"','readic="SEED"',tb))
    assert sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
    with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files}
    t=d['time'];assert t[0]==0 and abs(t[-1]-10e-9)<1e-14
    names=['XP.vco_vdd','XP.rx_vdd','XP.rt_vdd']
    v={k:dict(initial_v=float(d[k][0]),minimum_v=float(min(d[k])),maximum_v=float(max(d[k]))) for k in names}
    currents={}
    for k in ['VDD:p','XP.VVCO:p','XP.VRX:p','XP.VRT:p']:
        y=d[k];first=t<=10e-12;late=t>100e-12
        currents[k]=dict(peak_absolute_a=float(max(abs(y))),first10ps_peak_a=float(max(abs(y[first]))),
                          after100ps_peak_a=float(max(abs(y[late]))),first10ps_charge_c=float(np.trapezoid(y[first],t[first])))
    row=dict(kind=kind,source_result=(j/'result.json').relative_to(ROOT).as_posix(),source_sha256=sha(j/'result.json'),
        supply_nodes=v,currents=currents,out_range_v=[float(min(d['out'])),float(max(d['out']))],
        internal_output_stage_range_v={k:[float(min(d[k])),float(max(d[k]))] for k in ['XP.XR.qb','XP.XR.ob']},
        simulator_completed=True)
    rows.append(row); signals[kind+'_time']=t
    for key in ['VDD:p','XP.rt_vdd','out','XP.XR.qb']:
        signals[kind+'_'+key]=d[key]
out=dict(scope=__doc__,cases=rows,complete=len(rows)==2,three_node_ic_correction_verified=False,
         initialization_artifact_removed=None,pss_convergence_proven=False,full_pll_acceptance=False)
if len(rows)==2:
    assert tbs[0]==tbs[1]
    s=H/'state_inputs/core_pulsetrip_settled_tt.ic';c=H/'state_inputs/core_pulsetrip_supply_seed_tt.ic'
    def entries(p):return {x.split()[0]:float(x.split()[1]) for x in p.read_text().splitlines() if x.strip() and not x.startswith('#')}
    old,new=entries(s),entries(c); assert set(new)-set(old)==set(names)
    assert all(new[k]==old[k] for k in old) and all(new[k]==1.2 for k in names)
    out['three_node_ic_correction_verified']=True
    ratio=rows[0]['currents']['VDD:p']['peak_absolute_a']/rows[1]['currents']['VDD:p']['peak_absolute_a']
    out['vdd_peak_reduction_ratio']=ratio
    original_zero=all(abs(rows[0]['supply_nodes'][k]['initial_v'])<1e-9 for k in names)
    corrected_full=all(abs(rows[1]['supply_nodes'][k]['initial_v']-1.2)<1e-9 for k in names)
    out['original_supplies_initially_zero']=original_zero
    out['corrected_supplies_initially_1p2v']=corrected_full
    out['initialization_artifact_removed']=bool(original_zero and corrected_full and ratio>100)
    out['interpretation']='Only three IC values change. This diagnoses restart initialization and the probe-observation topology; it does not establish that this was the only cause of prior shooting divergence.'
(H/'results/core_seed_probe_validation.json').write_text(json.dumps(out,indent=2)+'\n')
if signals:np.savez_compressed(H/'results/core_seed_probe_waveforms.npz',**signals)
print(json.dumps(out,indent=2))
