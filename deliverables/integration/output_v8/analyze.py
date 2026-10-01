"""Functional and power checks for the physically clocked output-chain fixture."""
from pathlib import Path
import json,re
import numpy as np
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
H=Path(__file__).resolve().parent;D=H.parents[2]
ROOT=D.parent if D.name=='share' and (D.parent/'AGENTS.md').exists() else D
R=ROOT/'research/runs/spectre_output_v8'
def parse(p):return {k:np.asarray(v) for k,v in parse_spectre_psf_ascii(p).data.items() if k!='units'}
def cross(t,v,level=.6):
 i=np.flatnonzero((v[:-1]<level)&(v[1:]>=level));return t[i]+(level-v[i])*(t[i+1]-t[i])/(v[i+1]-v[i])
def wavecheck(d,periodic=False):
 t=d['time'];mask=np.ones(len(t),dtype=bool) if periodic else ((t>=70e-9)&(t<=100e-9));t=t[mask];d={k:v[mask] for k,v in d.items() if k not in ('time','units')}
 out=dict(window_s=[float(t[0]),float(t[-1])],signals={})
 ok=True
 for k,f in [('clk',3936e6),('data',984e6),('out',984e6)]:
  e=cross(t,d[k]);dt=np.diff(np.r_[e,e[0]+t[-1]-t[0]]) if periodic and len(e) else np.diff(e)
  avg=len(e)/(t[-1]-t[0]) if periodic else (1/np.mean(dt) if len(e)>2 else 0)
  err=float(max(abs(dt*f-1))) if len(dt) else None
  valid=bool(len(e)>=(1 if periodic else 3) and abs(avg/f-1)<.001 and err is not None and err<.02 and min(d[k])<.2 and max(d[k])>1)
  out['signals'][k]=dict(rising_edges=len(e),frequency_hz=float(avg),max_period_relative=err,range_v=[float(min(d[k])),float(max(d[k]))],pass_signal=valid);ok &=valid
 cf=cross(t,-d['clk'],-.6);de=np.sort(np.r_[cross(t,d['data']),cross(t,-d['data'],-.6)])
 cf=cf[(cf>t[0]+1/984e6)&(cf<t[-1]-1/984e6)];ix=np.searchsorted(de,cf)
 good=(ix>0)&(ix<len(de));cf=cf[good];ix=ix[good]
 if len(cf):
  out['geometric_data_margin_ps']=dict(min_previous_edge=float(min(cf-de[ix-1])*1e12),min_next_edge=float(min(de[ix]-cf)*1e12),note='Distance to actual falling clock; not characterized setup/hold or metastability signoff.')
  guard=20e-12;valid=(cf-de[ix-1]>guard)&(de[ix]-cf>guard)
  expected=np.interp(cf[valid],t,d['data'])>.6;actual=np.interp(cf[valid]+.35/3936e6,t,d['out'])>.6
  out['stable_data_samples']=int(sum(valid));out['stable_data_mismatches']=int(sum(expected!=actual));out['sample_check_note']='Diagnostic: data stable20ps before/after clock fall; output observed0.35RF periods later. Marginal samples excluded and geometric margins reported.'
  out['sample_check_is_acceptance']=False
  out['sample_check_limit']='The arbitrary0.35RF-period observation can precede actual propagation; this early-sample diagnostic is not a valid data oracle. Functional acceptance below uses the predeclared frequency/swing/period criteria only; retiming noise/timing remain unvalidated.'
  delay={}
  for edge,sgn in [('rise',1),('fall',-1)]:
   di=cross(t,sgn*d['data'],sgn*.6);do=cross(t,sgn*d['out'],sgn*.6);j=np.searchsorted(di,do)-1;good=j>=0
   if sum(good)>2:
    delta=do[good]-di[j[good]];delay[edge]=dict(min_ps=float(min(delta)*1e12),max_ps=float(max(delta)*1e12),mean_ps=float(np.mean(delta)*1e12))
  out['data_to_output_delay']=delay
 out['power_mw']={k:float(-1.2*np.trapezoid(d[k],t)/(t[-1]-t[0])*1e3) for k in ['VDD:p','VRX:p','VRT:p']}
 out['power_scope']='Simultaneous supply power for divider+receiver+retimer/output; ideal RF-source energy and actual VCO/mainloop/FLL/bias generators excluded.'
 out['pass_function']=bool(ok and (periodic or out['signals']['out']['rising_edges']>20))
 out['functional_scope']='Predeclared frequency,cycle-period and logic-swing screen. Does not prove data-independent retiming, setup/hold, metastability or noise suppression.'
 if periodic:
  out['period_s']=float(t[-1]-t[0]);out['endpoint_voltage_error']={k:float(abs(v[-1]-v[0])) for k,v in d.items() if ':' not in k}
  # Per-period data has only one output edge; separate periodic screen below.
  out['pass_periodic']=bool(abs((t[-1]-t[0])*984e6-1)<1e-7 and len(cross(t,d['clk']))==4 and len(cross(t,d['out']))==1 and len(cross(t,d['data']))==1 and min(d['clk'])<.2 and max(d['clk'])>1 and min(d['out'])<.2 and max(d['out'])>1 and max(out['endpoint_voltage_error'].values())<1e-3)
 return out
def main():
 rows=[]
 for rp in sorted(R.glob('*/*/result.json')):
  rec=json.loads(rp.read_text());job=rp.parent
  if not rec.get('remote_inputs_match'):continue
  log=(job/'spectre.out').read_text(errors='replace');row=dict(run=job.parent.name,case=job.name,sim_ok=rec['ok'],errors=rec['errors'],warnings=[x.strip() for x in log.splitlines() if 'WARNING (' in x]);rows.append(row)
  if not rec['ok']:continue
  raw=job/(job.name+'.raw');p=raw/'pss.td.pss'
  if p.exists():row['periodic']=wavecheck(parse(p),True)
  else:
   with np.load(job/'waveforms.npz') as z:d={k:z[k] for k in z.files}
   row['transient']=wavecheck(d)
 (H/'results/validation.json').write_text(json.dumps(rows,indent=2)+'\n')
 for row in rows:print(row['case'],row['sim_ok'],row.get('transient',{}).get('pass_function'),row.get('transient',{}).get('power_mw'))
if __name__=='__main__':main()
