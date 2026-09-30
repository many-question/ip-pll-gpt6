"""Compare raw, immutable interface test waveforms at identical endpoints."""
import json
import numpy as np
from analyze import H,R,measure,load_data

def main():
 rows=[]
 for label in ['base','sampler','divider','both','quiet100','quiet10']:
  run='quiet_timing' if label.startswith('quiet') else 'screen_timing'
  p=R/run/('timing_'+label)
  if not (p/'result.json').exists():continue
  d=load_data(p/'waveforms.npz')
  ends=[]
  for win in [(110e-9,150e-9),(240e-9,280e-9)]:
   x=measure(p,win);t=d['time'];m=(t>=win[0])&(t<=win[1]);tw=t[m]
   for k in ['vmid','XD.cm','XD.cim','sp','sn','hp','hn']:
    x[k+'_mean_v']=float(np.trapezoid(d[k][m],tw)/(tw[-1]-tw[0]))
   ends.append(x)
  rows.append(dict(label=label,endpoints=ends,pass_function=all(x['divide_valid'] for x in ends)))
 out=dict(condition='TT27, Q5, K41/code6; actual periodic sampling, CP clamped',expected=6,completed=len(rows),rows=rows,all_pass=len(rows)==6 and all(x['pass_function'] for x in rows))
 (H/'results/screen_validation.json').write_text(json.dumps(out,indent=2)+'\n')
 for r in rows:print(r['label'],r['pass_function'],[(round(x['f_ghz'],6),round(x['diff_pp_v'],4),round(x['total_mw'],4),round(x['sp_mean_v'],3)) for x in r['endpoints']])

if __name__=='__main__':main()
