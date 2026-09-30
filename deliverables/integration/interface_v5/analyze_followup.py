"""Independent measurements for corner coverage, gain, and fixed-code LC loop."""
import json,re,sys
import numpy as np
from analyze import H,R,measure,load_data
sys.path.insert(0,str(H.parent/'transistor_v2'))
from analyze_noise import parse

def corners(prefix='corner',run='corner_screen'):
 conditions=json.loads((H/'results'/f'{prefix}_conditions.json').read_text());rows=[]
 for c in conditions:
  p=R/run/c['case']
  if not (p/'result.json').exists():continue
  ends=[measure(p,w) for w in [(110e-9,150e-9),(240e-9,280e-9)]]
  target=float(c['target_vco_MHz'])*1e6
  valid=all(x.get('divide_valid',False) for x in ends)
  fs=[x.get('f_ghz',0)*1e9 for x in ends]
  margin=min(target-min(fs),max(fs)-target)
  rows.append(dict(condition=c,endpoints=ends,endpoint_margin_hz=margin,pass_divide=valid,pass_coverage=valid and margin>2e6))
 out=dict(expected=len(conditions),completed=len(rows),all_pass=len(rows)==len(conditions) and all(x['pass_coverage'] for x in rows),rows=rows)
 (H/'results'/f'{prefix}_validation.json').write_text(json.dumps(out,indent=2)+'\n')
 print(prefix,len(rows),'/',len(conditions),[(r['condition']['case'],round(r['endpoint_margin_hz']/1e6,3),r['pass_coverage']) for r in rows])

def gains():
 rows=[]
 for p in R.glob('gain*/*/result.json'):
  rec=json.loads(p.read_text());job=p.parent
  if not rec['ok']:continue
  raw=job/(job.name+'.raw');td=parse(raw/'pss.td.pss');t=td['time'];tb=(job/'inputs'/f'{job.name}.scs').read_text()
  phase=float(re.search(r'phase_deg=([-\d.e]+)',tb)[1])
  mean=float(np.trapezoid(td['VO:p'],t)/(t[-1]-t[0]))
  clamp=float(re.search(r'VO \(cpout 0\) vsource dc=([\d.]+)',tb)[1])
  rows.append(dict(run=job.parent.name,case=job.name,clamp_v=clamp,phase_deg=phase,mean_clamp_current_a=mean,power_mw=float(-1.2*np.trapezoid(td['VDD:p'],t)/(t[-1]-t[0])*1e3),hp_mean_v=float(np.mean(td['hp'])),hn_mean_v=float(np.mean(td['hn']))))
 rows.sort(key=lambda r:r['phase_deg'])
 (H/'results/gain_points.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('Gain points',[(r['phase_deg'],round(r['mean_clamp_current_a']*1e6,6)) for r in rows])

def loops():
 rows=[]
 for p in R.glob('loop*/*/result.json'):
  if not json.loads(p.read_text())['ok']:continue
  job=p.parent;d=load_data(job/'waveforms.npz')
  if 'obsphase' not in d:continue
  t=d['time'];idx=np.flatnonzero(np.diff(d['obsphase'])!=0)+1
  samples={k:d[k][idx] for k in ['time','obsphase','obscycles','obsctrl','obsdivcycles']}
  tail=samples['time']>t[-1]-1e-6;tt=samples['time'][tail];phase=np.unwrap(samples['obsphase'][tail]);nc=samples['obscycles'][tail];nd=samples['obsdivcycles'][tail]
  if len(tt)<10:continue
  drift=float(np.polyfit((tt-tt[0])*1e6,phase,1)[0]);phasepp=float(np.ptp(phase));max_cycles_err=float(max(abs(nc-164)))
  row=dict(run=job.parent.name,case=job.name,end_s=float(t[-1]),window_s=[float(tt[0]),float(tt[-1])],samples=len(tt),phase_pp_rad=phasepp,phase_drift_rad_per_us=drift,max_vco_cycles_error=max_cycles_err,mean_output_mhz=float(np.mean(nd)*24),max_output_cycles_error=float(max(abs(nd-41))),sampled_ctrl_range_v=[float(min(samples['obsctrl'][tail])),float(max(samples['obsctrl'][tail]))],condition='TT27, Q5, fixed code6, real LC VCO + sampler + CP + filter + divider; ideal preset and enable; no FLL, output retimer or full clock receiver')
  row['pass_stationary']=bool(phasepp<.02 and abs(drift)<.01 and max_cycles_err<.001 and row['max_output_cycles_error']<.001 and .2<row['sampled_ctrl_range_v'][0]<row['sampled_ctrl_range_v'][1]<1)
  row['criteria']='Last 1 us: phase pp <0.02 rad, absolute drift <0.01 rad/us, VCO cycles/ref error <0.001, divider cycles/ref error <0.001, control within 0.2..1 V. Functional engineering screen, not jitter.'
  row['interface']='quiet10' if 'quiet10' in job.name else 'both'
  rows.append(row)
  np.savez_compressed(H/'results'/f'{job.parent.name}_{job.name}_samples.npz',**samples)
 (H/'results/loop_validation.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('Loops',rows)

if __name__=='__main__':
 for fn in (corners,gains,loops):fn()
 if (H/'results/q10corner_conditions.json').exists():corners('q10corner','quiet10_corners')
