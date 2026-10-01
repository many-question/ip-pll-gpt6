"""Finite data-edge perturbation at matched physical operating waveforms."""
import json
import numpy as np
from analyze import H,R,cross
T=1/984e6
def phase(e):return float(np.angle(np.mean(np.exp(2j*np.pi*e/T)))*T/(2*np.pi))
def delta(a,b):return float(np.angle(np.exp(2j*np.pi*(a-b)/T))*T/(2*np.pi))
def measure(job):
 with np.load(job/'waveforms.npz') as z:
  mask=(z['time']>=70e-9)&(z['time']<=100e-9);t=z['time'][mask]
  signals={'data':(z['dp'][mask]-z['dn'][mask],0),'retimed':(z['XRT.qp'][mask]-z['XRT.qn'][mask],0),'out':(z['out'][mask],.6)}
  return {k+'_'+edge:phase(cross(t,sgn*v,sgn*lev)) for k,(v,lev) in signals.items() for edge,sgn in [('rise',1),('fall',-1)]}
def main():
 v=json.loads((H/'results/validation.json').read_text());by={r['case']:r for r in v};rows=[]
 pairs=[]
 protocols=[json.loads(p.read_text()) for p in sorted((H/'results').glob('timing_*_protocol.json'))]
 pairs += [(s['tag'],s['case']) for p in protocols for s in p['sources']]
 for tag,base in pairs:
  needed=[f'timing_{tag}_{p}' for p in ['early','zero','late']]+[base]
  if not all(k in by for k in needed):continue
  if not all(by[k]['sim_ok'] and by[k].get('transient',{}).get('pass_function') for k in needed):continue
  m={k:measure(R/by[k]['run']/k) for k in needed};e,z,l=(m[f'timing_{tag}_{p}'] for p in ['early','zero','late'])
  match={k:delta(z[k],m[base][k])*1e12 for k in z};shifts={k:delta(l[k],e[k])*1e12 for k in e}
  gains={k:shifts[k]/shifts['data_'+k.split('_')[-1]] for k in shifts if not k.startswith('data_')}
  qualified=bool(max(abs(match[k]) for k in ['out_rise','out_fall'])<2 and max(abs(shifts[k]-20) for k in ['data_rise','data_fall'])<.2)
  rows.append(dict(phase=tag,zero_replay_minus_physical_ps=match,late_minus_early_ps=shifts,output_to_input_timing_gain=gains,qualified_replay=qualified,
   pass_internal_timing_target=bool(qualified and max(abs(gains[k]) for k in ['out_rise','out_fall'])<.1),scope='Deterministic finite-difference timing response over±10ps at oneTT phase, with measured ideal data replay. Not actual divider noise or universal setup/hold/PVT signoff.'))
 out=dict(protocol=protocols[0] if protocols else None,additional_protocols=protocols,cases=rows)
 (H/'results/timing_validation.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n');print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
