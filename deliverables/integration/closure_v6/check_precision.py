"""Predeclared functional convergence screen; independent noise checks still needed."""
import json,re
import numpy as np
from analyze import H,R

def norm_tb(p):
 return re.sub(r'writefinal="[^"]+"','writefinal="STATE"',p.read_text()).replace('maxstep=1p','maxstep=2p')

def main():
 rows=json.loads((H/'results/validation.json').read_text());by={r['case']:r for r in rows}
 limits=dict(max_end_phase_delta_rad=.02,max_mean_control_delta_v=.005,max_mean_output_delta_hz=5000,both_pass_original_stationary=True)
 out=dict(scope='Only fixed-code TT27 functional convergence, not jitter/noise or PVT signoff; same cold-start4us run, full logged tolerances, maxstep2ps versus1ps.',limits=limits,status='pending',pass_precision=False)
 if all(k in by for k in ['loop_clamp_strict','loop_clamp_1ps']):
  a=by['loop_clamp_strict'];b=by['loop_clamp_1ps'];assert a['sim_ok'] and b['sim_ok']
  ja=R/'clamp_strict/loop_clamp_strict';jb=R/'clamp_precision/loop_clamp_1ps'
  assert norm_tb(ja/'inputs/loop_clamp_strict.scs')==norm_tb(jb/'inputs/loop_clamp_1ps.scs')
  ra=json.loads((ja/'result.json').read_text());rb=json.loads((jb/'result.json').read_text())
  ha={k:v for k,v in ra['inputs_sha256'].items() if k!='loop_clamp_strict.scs'};hb={k:v for k,v in rb['inputs_sha256'].items() if k!='loop_clamp_1ps.scs'};assert ha==hb
  aa=np.load(H/'results/clamp_strict_loop_clamp_strict_samples.npz');bb=np.load(H/'results/clamp_precision_loop_clamp_1ps_samples.npz')
  phase_delta=float(np.angle(np.exp(1j*(bb['obsphase'][-1]-aa['obsphase'][-1]))))
  ma=aa['time']>3e-6;mb=bb['time']>3e-6
  dc=float(np.mean(bb['obsctrl'][mb])-np.mean(aa['obsctrl'][ma]));df=(b['transient']['mean_output_mhz']-a['transient']['mean_output_mhz'])*1e6
  out.update(status='completed',only_timestep_changed=True,end_phase_delta_rad=phase_delta,mean_control_delta_v=dc,mean_output_delta_hz=df,phase_drift_delta_rad_per_us=b['transient']['phase_drift_rad_per_us']-a['transient']['phase_drift_rad_per_us'])
  out['pass_precision']=bool(a['transient']['pass_stationary'] and b['transient']['pass_stationary'] and abs(phase_delta)<limits['max_end_phase_delta_rad'] and abs(dc)<limits['max_mean_control_delta_v'] and abs(df)<limits['max_mean_output_delta_hz'])
 (H/'results/precision_validation.json').write_text(json.dumps(out,indent=2)+'\n')
 print('Functional precision:',out['status'],out['pass_precision'])

if __name__=='__main__':main()
