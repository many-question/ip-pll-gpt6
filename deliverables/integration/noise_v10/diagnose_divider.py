"""Compare actual divider source contributions; do not infer timing suppression."""
import json
from analyze import H,R,parse,cross
import numpy as np

def main():
 n=json.loads((H/'results/noise_validation.json').read_text());rows=[]
 for r in n['cases']:
  if not r['valid_noise']:continue
  if r['case']!='noise_gate_all_coarse' and not r['case'].startswith('noise_opt_div'):continue
  d=parse(R/r['run']/r['case']/(r['case']+'.raw')/'pss.td.pss');t=d['time'];rf=cross(t,d['vp']-d['vn']);data=cross(t,d['dp']-d['dn']);fall=cross(t,d['dn']-d['dp']);trf=1/3936e6
  phase=lambda es:[float(((e-rf[0]+trf/2)%trf-trf/2)*1e12) for e in es]
  slopes=[]
  for e in data:
   i=max(0,min(len(t)-2,np.searchsorted(t,e)-1));v=d['dp']-d['dn'];slopes.append(float((v[i+1]-v[i])/(t[i+1]-t[i])))
  groups={k:x['jitter_fs'] for k,x in r['noise_by_subblock'].items() if k.startswith(('XD.XM2','XD.XS2','XD.XO2','XD.XON2'))}
  rows.append(dict(case=r['case'],divider_jitter_fs=r['noise_by_instance']['XD']['jitter_fs'],selected_source_groups_fs=groups,data_rise_rf_phase_ps=phase(data),data_fall_rf_phase_ps=phase(fall),data_rising_slew_v_per_s=slopes,out_event_slew_v_per_s=r['slew_v_per_s']))
 out=dict(note='Source noise measured at final output includes transfer through the full chain. Phase is modulo one RF cycle relative to differential RF rising zero and does not measure setup/hold or noise-transfer gain. Structural changes affect both source noise and its propagation; attribution alone does not isolate causality.',cases=rows)
 (H/'results/divider_diagnosis.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n');print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
