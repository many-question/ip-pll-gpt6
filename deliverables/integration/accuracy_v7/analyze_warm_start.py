"""Audit readic application and dense initial-transient data, even after PSS fails.

The pss.tran.pss file is initialization, never an accepted periodic solution.
"""
import json
import numpy as np
from analyze import H,R,parse,cross

def main():
 rows=[]
 for job in sorted(R.glob('*/*')):
  rp=job/'result.json';p=job/(job.name+'.raw')/'pss.tran.pss'
  if not rp.exists() or not p.exists():continue
  rec=json.loads(rp.read_text())
  if not rec.get('remote_inputs_match'):continue
  if not rec.get('initial_states'):continue # analytic RC fixtures have no readic
  states={}
  state_name=next(iter(rec['initial_states'].values()))['source']
  for line in (job/'inputs'/state_name).read_text().splitlines():
   w=line.split()
   if len(w)<2 or w[0].startswith('#'):continue
   try:states[w[0]]=float(w[1])
   except ValueError:continue
  d=parse(p);t=d['time'];T=1/24e6;a=t[-1]-T
  assert a>=t[0]
  initial={k:abs(float(d[k][0])-v) for k,v in states.items() if k in d}
  grid=np.r_[a,t[t>a]]
  y={k:np.interp(grid,t,v) for k,v in d.items() if k!='time'}
  endpoints={k:float(abs(v[-1]-v[0])) for k,v in y.items() if ':' not in k}
  row=dict(case=job.name,scope='Dense initial transient before PSS shooting, not converged periodic solution or noise result. Last exactly one24MHz reference period; local connected branch only, excludes FLL/fullsupervisor/GHzreceiver/retimer/reference generators.',tstab_end_s=float(t[-1]),window_s=[float(a),float(t[-1])],initial_states_checked=len(initial),max_initial_readic_error=max(initial.values()),pass_initial_readic=bool(len(initial)>=20 and max(initial.values())<1e-10),connected_power_mw=float(-1.2*np.trapezoid(y['VDD:p'],grid)/T*1e3),vco_power_mw=float(-1.2*np.trapezoid(y['VVCO:p'],grid)/T*1e3),tank_diff_pp_v=float(np.ptp(y['vp']-y['vn'])),vco_edges=len(cross(grid,y['vp']-y['vn'])),output_edges=len(cross(grid,y['out'],.6)) if 'out' in y else None,ctrl_range_v=[float(min(y['ctrl'])),float(max(y['ctrl']))],endpoint_voltage_mismatch_v=endpoints)
  ref=cross(t,d['refb'],.6);vco=cross(t,d['vp']-d['vn']);ix=np.searchsorted(vco,ref)-1;keep=(ix>0)&(ix+1<len(vco));ref=ref[keep];ix=ix[keep]
  phase=np.unwrap(2*np.pi*(ref-vco[ix])/(vco[ix]-vco[ix-1]));control=np.interp(ref,t,d['ctrl'])
  row['ref_sample_times_s']=ref.tolist();row['ref_sample_phase_rad']=phase.tolist();row['ref_sample_ctrl_v']=control.tolist()
  row['save_limit']='Output voltage omitted from inherited ablation save list; no independent output-edge count.' if 'out' not in y else None
  assert row['pass_initial_readic']
  rows.append(row)
 (H/'results/warm_start_validation.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('Verified readic and dense initialization for',len(rows),'PSS trials')

if __name__=='__main__':main()
