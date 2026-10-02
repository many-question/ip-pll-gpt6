"""Complete-DUT constructed-state metrics, kept separate from reset capture."""
from pathlib import Path
import json,re
import numpy as np
from analyze import loop
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
cases=[('completestrict01','complete_strict_tt'),('completess01','complete_near_ss'),('completequal01','complete_qual_tt')]
rows=[]
for run,case in cases:
 job=R/run/case
 if not (job/'result.json').exists():
  rows.append(dict(run=run,case=case,status='not_completed'));continue
 rec=json.loads((job/'result.json').read_text());assert rec['remote_inputs_match']
 log=(job/'spectre.out').read_text(errors='replace')
 completed='spectre completes with 0 errors' in log
 precision='4ps/1e-4' if case=='complete_qual_tt' else '1ps/1e-5'
 row=dict(run=run,case=case,simulator_completed=completed,source_result=str((job/'result.json').relative_to(ROOT)),scope=f'Constructed near-lock physical completeDUT,1.2V,K41/M4,10fF,Q5RLC,{precision}. No reset-capture claim.');rows.append(row)
 if not completed or not (job/'waveforms.npz').exists():continue
 with np.load(job/'waveforms.npz') as z:d={k:z[k] for k in z.files if k!='units'}
 t=d['time'];j=int(np.searchsorted(t,t[-1]-1e-6));sel=t>=t[j];dt=(t[-1]-t[j])*1e6
 row['loop']=loop(d)
 power={'total':float((d['energy_nj'][-1]-d['energy_nj'][j])/dt)}
 for block in ['vco','rx','rt']:
  key='energy_'+block+'_nj';power[block]=float((d[key][-1]-d[key][j])/dt)
 power['other']=power['total']-sum(power[k] for k in ['vco','rx','rt'])
 row['final_window_supply_power_mw']=power
 row['power_window_us']=[float(t[j]*1e6),float(t[-1]*1e6)]
 row['power_boundary']='All supply current including physical bias, dividers, FLL and supervision. Short window only; complete locked-state period is at least32us.'
 row['edges']={}
 for block in ['reference','rfclock','output']:
  stats={}
  for quantity in ['rise_ns','fall_ns','period_ns','duty_percent']:
   v=d[block+'_'+quantity][sel];assert np.all(np.isfinite(v)) and min(v)>0
   stats[quantity]=dict(mean=float(np.mean(v)),minimum=float(min(v)),maximum=float(max(v)))
  row['edges'][block]=stats
 row['edge_boundary']='Validated TB observers measure10-90percent edges at internal solver time steps. Statistics are2ns snapshots of held observations, not a uniformly weighted census of RF cycles or random jitter.'
 row['logic_high_fraction']={k:float(np.mean(d[k][sel]>.6)) for k in ['qualified','frequency_good','XP.XC.phase_held','XP.count_gate','XP.count_reset','XP.en','range_error']}
 row['history_boundary']='TT strict watchdog history inherited from8us warm state; first window is invalid and next watchdog window lies beyond4us. Qualification initialized0; no FLL acquisition proof.' if case=='complete_strict_tt' else 'Watchdog and qualification initialized0, FLL DONE/configuration and analog near-lock state are constructed. No FLL acquisition proof.'
 row['measurement_note']='Supply-energy integration uses endpoint differences. Earlier constructed states retained a TB integrator initial offset, which cancels in these differences; no absolute initial energy is treated as consumed DUT energy.'
 row['near_lock_with_qualification_passed']=bool(row['loop']['passed'] and row['logic_high_fraction']['qualified']==1 and row['logic_high_fraction']['frequency_good']==1 and row['logic_high_fraction']['range_error']==0)
(H/'results/full_metrics.json').write_text(json.dumps(dict(scope=__doc__,cases=rows),indent=2)+'\n')
print(json.dumps(rows,indent=2))
